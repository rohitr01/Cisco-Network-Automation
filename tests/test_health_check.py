import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.health_check import (
    check_interfaces,
    check_ospf,
    check_cpu,
    check_memory,
    check_vlans,
    check_routing,
    compute_health,
    Severity,
)
from config.settings import HEALTH_WEIGHTS

class TestCheckInterfaces(unittest.TestCase):
    def test_all_up(self):
        interfaces = [
            {"name": "GigabitEthernet0/0", "protocol": "up", "status": "up"},
            {"name": "GigabitEthernet0/1", "protocol": "up", "status": "up"}
        ]
        score, alerts = check_interfaces(interfaces)
        self.assertEqual(score, HEALTH_WEIGHTS["interfaces_healthy"])
        self.assertEqual(len(alerts), 0)

    def test_mix_up_down(self):
        interfaces = [
            {"name": "GigabitEthernet0/0", "protocol": "up", "status": "up"},
            {"name": "GigabitEthernet0/1", "protocol": "down", "status": "down"}
        ]
        score, alerts = check_interfaces(interfaces)
        expected_score = max(0, HEALTH_WEIGHTS["interfaces_healthy"] - 5)
        self.assertEqual(score, expected_score)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.WARNING)

    def test_admin_down(self):
        interfaces = [
            {"name": "GigabitEthernet0/0", "protocol": "up", "status": "up"},
            {"name": "GigabitEthernet0/1", "protocol": "down", "status": "administratively down"}
        ]
        score, alerts = check_interfaces(interfaces)
        self.assertEqual(score, HEALTH_WEIGHTS["interfaces_healthy"])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.INFO)

    def test_unexpected_down_score_reduction(self):
        interfaces = [
            {"name": f"Gi0/{i}", "protocol": "down", "status": "down"}
            for i in range(5)
        ]
        score, alerts = check_interfaces(interfaces)
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 5)
        self.assertTrue(all(a["severity"] == Severity.WARNING for a in alerts))

    def test_empty_list(self):
        score, alerts = check_interfaces([])
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.WARNING)
        self.assertIn("No interface data", alerts[0]["message"])


class TestCheckOspf(unittest.TestCase):
    def test_two_full_neighbors(self):
        neighbors = [
            {"neighbor_id": "1.1.1.1", "state": "FULL/DR"},
            {"neighbor_id": "2.2.2.2", "state": "FULL/BDR"}
        ]
        score, alerts = check_ospf(neighbors)
        self.assertEqual(score, HEALTH_WEIGHTS["ospf_neighbors"])
        self.assertEqual(len(alerts), 0)

    def test_one_full_one_init(self):
        neighbors = [
            {"neighbor_id": "1.1.1.1", "state": "FULL/DR"},
            {"neighbor_id": "2.2.2.2", "state": "INIT/DROTHER"}
        ]
        score, alerts = check_ospf(neighbors)
        expected_score = max(0, HEALTH_WEIGHTS["ospf_neighbors"] - 5)
        self.assertEqual(score, expected_score)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.CRITICAL)

    def test_empty_list(self):
        score, alerts = check_ospf([])
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.WARNING)
        self.assertIn("no established neighbors", alerts[0]["message"])

    def test_non_full_state_detection(self):
        neighbors = [
            {"neighbor_id": "1.1.1.1", "state": "EXSTART/-"}
        ]
        score, alerts = check_ospf(neighbors)
        self.assertEqual(score, max(0, HEALTH_WEIGHTS["ospf_neighbors"] - 5))
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.CRITICAL)
        self.assertIn("EXSTART/-", alerts[0]["message"])


class TestCheckCpu(unittest.TestCase):
    def test_normal_cpu(self):
        score, alerts = check_cpu({"one_min_pct": 18})
        self.assertEqual(score, HEALTH_WEIGHTS["cpu_ok"])
        self.assertEqual(len(alerts), 0)

    def test_high_cpu(self):
        score, alerts = check_cpu({"one_min_pct": 87})
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.CRITICAL)
        self.assertIn("High CPU", alerts[0]["message"])

    def test_elevated_cpu(self):
        score, alerts = check_cpu({"one_min_pct": 65})
        self.assertEqual(score, HEALTH_WEIGHTS["cpu_ok"] // 2)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.WARNING)
        self.assertIn("Elevated CPU", alerts[0]["message"])

    def test_empty_dict(self):
        score, alerts = check_cpu({})
        self.assertEqual(score, HEALTH_WEIGHTS["cpu_ok"])
        self.assertEqual(len(alerts), 0)


class TestCheckMemory(unittest.TestCase):
    def test_normal_memory(self):
        score, alerts = check_memory({"used_pct": 42})
        self.assertEqual(score, HEALTH_WEIGHTS["memory_ok"])
        self.assertEqual(len(alerts), 0)

    def test_high_memory(self):
        score, alerts = check_memory({"used_pct": 85})
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.CRITICAL)
        self.assertIn("High memory", alerts[0]["message"])

    def test_elevated_memory(self):
        score, alerts = check_memory({"used_pct": 65})
        self.assertEqual(score, HEALTH_WEIGHTS["memory_ok"] // 2)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.WARNING)
        self.assertIn("Elevated memory", alerts[0]["message"])

    def test_empty_dict(self):
        score, alerts = check_memory({})
        self.assertEqual(score, HEALTH_WEIGHTS["memory_ok"])
        self.assertEqual(len(alerts), 0)


class TestCheckVlans(unittest.TestCase):
    def test_active_vlans(self):
        vlans = [
            {"id": "1", "status": "active"},
            {"id": "10", "status": "active"}
        ]
        score, alerts = check_vlans(vlans)
        self.assertEqual(score, HEALTH_WEIGHTS["vlans_present"])
        self.assertEqual(len(alerts), 0)

    def test_empty_list_router(self):
        score, alerts = check_vlans([])
        self.assertEqual(score, HEALTH_WEIGHTS["vlans_present"])
        self.assertEqual(len(alerts), 0)

    def test_all_inactive(self):
        vlans = [
            {"id": "1", "status": "suspend"},
            {"id": "10", "status": "shutdown"}
        ]
        score, alerts = check_vlans(vlans)
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.WARNING)
        self.assertIn("No active VLANs", alerts[0]["message"])


class TestCheckRouting(unittest.TestCase):
    def test_populated_routing_table(self):
        routing = {"total_routes": 10}
        score, alerts = check_routing(routing)
        self.assertEqual(score, HEALTH_WEIGHTS["routing_ok"])
        self.assertEqual(len(alerts), 0)

    def test_empty_routing_table(self):
        routing = {"total_routes": 0}
        score, alerts = check_routing(routing)
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], Severity.WARNING)

    def test_empty_dict(self):
        routing = {}
        score, alerts = check_routing(routing)
        self.assertEqual(score, 0)
        self.assertEqual(len(alerts), 1)


class TestComputeHealth(unittest.TestCase):
    def test_healthy_device(self):
        device_data = {
            "reachable": True,
            "interfaces": [{"name": "Gi0/0", "protocol": "up", "status": "up"}],
            "ospf_neighbors": [{"neighbor_id": "1.1.1.1", "state": "FULL"}],
            "cpu": {"one_min_pct": 10},
            "memory": {"used_pct": 20},
            "vlans": [{"id": "1", "status": "active"}],
            "routing": {"total_routes": 5}
        }
        res = compute_health(device_data)
        self.assertGreaterEqual(res["score"], 90)
        self.assertEqual(res["grade"], "A")
        self.assertEqual(res["status"], "HEALTHY")
        self.assertEqual(len(res["alerts"]), 0)

    def test_unreachable_device(self):
        device_data = {"reachable": False}
        res = compute_health(device_data)
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["grade"], "F")
        self.assertEqual(res["status"], "UNREACHABLE")
        self.assertEqual(len(res["alerts"]), 1)
        self.assertEqual(res["alerts"][0]["severity"], Severity.CRITICAL)

    def test_high_cpu_degraded_device(self):
        device_data = {
            "reachable": True,
            "interfaces": [{"name": "Gi0/0", "protocol": "down", "status": "down"}],
            "ospf_neighbors": [],
            "cpu": {"one_min_pct": 99},
            "memory": {"used_pct": 20},
            "vlans": [{"id": "1", "status": "active"}],
            "routing": {"total_routes": 5}
        }
        res = compute_health(device_data)
        self.assertEqual(res["grade"], "C")
        self.assertEqual(res["status"], "DEGRADED")
        self.assertTrue(any("High CPU" in a["message"] for a in res["alerts"]))

    def test_device_no_ospf(self):
        device_data = {
            "reachable": True,
            "interfaces": [{"name": "Gi0/0", "protocol": "up", "status": "up"}],
            "cpu": {"one_min_pct": 10},
            "memory": {"used_pct": 20},
            "vlans": [{"id": "1", "status": "active"}],
            "routing": {"total_routes": 5}
        }
        res = compute_health(device_data)
        self.assertEqual(res["breakdown"]["ospf_neighbors"], 0)
        self.assertTrue(any("no established neighbors" in a["message"] for a in res["alerts"]))
        self.assertEqual(res["score"], 80)

    def test_alerts_list_populated_and_breakdown_keys(self):
        device_data = {
            "reachable": True,
            "interfaces": [{"name": "Gi0/0", "protocol": "down", "status": "administratively down"}],
            "ospf_neighbors": [{"neighbor_id": "1.1.1.1", "state": "INIT"}],
            "cpu": {"one_min_pct": 65},
            "memory": {"used_pct": 90},
            "vlans": [],
            "routing": {}
        }
        res = compute_health(device_data)
        expected_keys = {
            "reachable", "interfaces_healthy", "ospf_neighbors", 
            "cpu_ok", "memory_ok", "vlans_present", "routing_ok"
        }
        self.assertEqual(set(res["breakdown"].keys()), expected_keys)
        
        alerts_text = [a["message"] for a in res["alerts"]]
        self.assertTrue(any("administratively down" in msg for msg in alerts_text))
        self.assertTrue(any("expected FULL" in msg for msg in alerts_text))
        self.assertTrue(any("Elevated CPU" in msg for msg in alerts_text))
        self.assertTrue(any("High memory" in msg for msg in alerts_text))
        self.assertTrue(any("Routing table is empty" in msg for msg in alerts_text))

class TestOspf2Way(unittest.TestCase):
    def test_2way_drother_not_penalised(self):
        """2WAY/DROTHER on broadcast networks is normal, not a failure."""
        neighbors = [
            {'neighbor_id': '1.1.1.1', 'state': 'FULL/DR', 'dead_time': '00:00:35', 'address': '10.0.0.1', 'interface': 'Gi0/0'},
            {'neighbor_id': '2.2.2.2', 'state': '2WAY/DROTHER', 'dead_time': '00:00:35', 'address': '10.0.0.2', 'interface': 'Gi0/0'},
        ]
        score, alerts = check_ospf(neighbors)
        self.assertEqual(score, HEALTH_WEIGHTS['ospf_neighbors'])
        severities = [a['severity'] for a in alerts]
        self.assertNotIn('critical', severities)
        self.assertIn('info', severities)  # 2WAY noted as info

    def test_init_state_penalised(self):
        """INIT state means adjacency is not forming — this is a problem."""
        neighbors = [
            {'neighbor_id': '1.1.1.1', 'state': 'INIT/DROTHER', 'dead_time': '00:00:35', 'address': '10.0.0.1', 'interface': 'Gi0/0'},
        ]
        score, alerts = check_ospf(neighbors)
        self.assertLess(score, HEALTH_WEIGHTS['ospf_neighbors'])
        severities = [a['severity'] for a in alerts]
        self.assertIn('critical', severities)

    def test_down_state_penalised(self):
        """DOWN state is clearly a problem."""
        neighbors = [
            {'neighbor_id': '1.1.1.1', 'state': 'DOWN/ -', 'dead_time': '-', 'address': '10.0.0.1', 'interface': 'Gi0/0'},
        ]
        score, alerts = check_ospf(neighbors)
        self.assertLess(score, 20)
        severities = [a['severity'] for a in alerts]
        self.assertIn('critical', severities)

    def test_all_2way_full_score(self):
        """All 2WAY neighbors should still get full score."""
        neighbors = [
            {'neighbor_id': '1.1.1.1', 'state': '2WAY/DROTHER', 'dead_time': '00:00:35', 'address': '10.0.0.1', 'interface': 'Gi0/0'},
            {'neighbor_id': '2.2.2.2', 'state': '2WAY/DROTHER', 'dead_time': '00:00:35', 'address': '10.0.0.2', 'interface': 'Gi0/0'},
        ]
        score, alerts = check_ospf(neighbors)
        self.assertEqual(score, HEALTH_WEIGHTS['ospf_neighbors'])

if __name__ == '__main__':
    unittest.main()
