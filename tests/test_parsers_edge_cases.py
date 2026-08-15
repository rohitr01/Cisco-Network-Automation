import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.parsers import (
    parse_version,
    parse_interfaces,
    parse_vlans,
    parse_routing,
    parse_cpu,
    parse_memory,
    parse_ospf_neighbors,
    parse_mac_table,
    parse_hostname,
)

class TestParseVersionEdgeCases(unittest.TestCase):
    def test_xe_version(self):
        raw = "Cisco IOS XE Software, Version 17.3.4a\n"
        res = parse_version(raw)
        self.assertEqual(res["ios_version"], "17.3.4a")

    def test_short_output(self):
        raw = "Cisco IOS Software, Version 15.2(4)M1\n"
        res = parse_version(raw)
        self.assertEqual(res["ios_version"], "15.2(4)M1")
        self.assertEqual(res["uptime"], "Unknown")
        self.assertEqual(res["platform"], "Unknown")
        self.assertIsNone(res["memory_total_kb"])

    def test_uptime_only_hours(self):
        raw = "uptime is 3 hours, 22 minutes\n"
        res = parse_version(raw)
        self.assertEqual(res["uptime"], "3 hours, 22 minutes")

    def test_platform_no_processor(self):
        raw = "cisco ISR4321/K9 (1RU) with 1795999K bytes of memory.\n"
        res = parse_version(raw)
        self.assertEqual(res["platform"], "Unknown")

class TestParseInterfacesEdgeCases(unittest.TestCase):
    def test_vlan_interface(self):
        raw = "Vlan10                 192.168.10.1    YES NVRAM  up                    up\n"
        res = parse_interfaces(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "Vlan10")

    def test_loopback_interface(self):
        raw = "Loopback0              1.1.1.1         YES NVRAM  up                    up\n"
        res = parse_interfaces(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "Loopback0")

    def test_header_only(self):
        raw = "Interface              IP-Address      OK? Method Status                Protocol\n"
        res = parse_interfaces(raw)
        self.assertEqual(res, [])

    def test_many_interfaces(self):
        raw = ""
        for i in range(15):
            raw += f"GigabitEthernet0/{i}     192.168.{i}.1     YES NVRAM  up                    up\n"
        res = parse_interfaces(raw)
        self.assertEqual(len(res), 15)

    def test_serial_interface(self):
        raw = "Serial0/0/0            10.0.0.1        YES NVRAM  up                    up\n"
        res = parse_interfaces(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["name"], "Serial0/0/0")

class TestParseVlansEdgeCases(unittest.TestCase):
    def test_act_unsup(self):
        raw = "100  VLAN0100                         act/unsup Gi0/1\n"
        res = parse_vlans(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["status"], "act/unsup")

    def test_vlan_id_1(self):
        raw = "1    default                          active    Gi0/0\n"
        res = parse_vlans(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], 1)

    def test_invalid_input(self):
        raw = "% Invalid input detected at '^' marker.\n"
        res = parse_vlans(raw)
        self.assertEqual(res, [])

class TestParseRoutingEdgeCases(unittest.TestCase):
    def test_gateway_last_resort(self):
        raw = "Gateway of last resort is 192.168.1.1 to network 0.0.0.0\n"
        res = parse_routing(raw)
        self.assertEqual(res["default_route"], "192.168.1.1")

    def test_only_connected(self):
        raw = "C     192.168.1.0/24 is directly connected, GigabitEthernet0/0\n"
        res = parse_routing(raw)
        self.assertEqual(res["total_routes"], 1)
        self.assertEqual(res["connected"], 1)
        self.assertEqual(res["ospf_routes"], 0)
        self.assertEqual(res["static"], 0)

    def test_bgp_routes(self):
        raw = "B     10.0.0.0/8 [20/0] via 192.168.1.254, 00:00:10\n"
        res = parse_routing(raw)
        self.assertEqual(res["total_routes"], 1)
        self.assertEqual(res["ospf_routes"], 0)
        self.assertEqual(res["connected"], 0)
        self.assertEqual(res["static"], 0)

    def test_local_routes(self):
        raw = "L     192.168.1.1/32 is directly connected, GigabitEthernet0/0\n"
        res = parse_routing(raw)
        self.assertEqual(res["total_routes"], 1)

class TestParseCpuEdgeCases(unittest.TestCase):
    def test_cpu_100_percent(self):
        raw = "CPU utilization for five seconds: 100%/100%; one minute: 100%; five minutes: 100%\n"
        res = parse_cpu(raw)
        self.assertEqual(res["five_sec_pct"], 100.0)
        self.assertEqual(res["one_min_pct"], 100.0)
        self.assertEqual(res["five_min_pct"], 100.0)

    def test_cpu_0_percent(self):
        raw = "CPU utilization for five seconds: 0%/0%; one minute: 0%; five minutes: 0%\n"
        res = parse_cpu(raw)
        self.assertEqual(res["five_sec_pct"], 0.0)
        self.assertEqual(res["one_min_pct"], 0.0)
        self.assertEqual(res["five_min_pct"], 0.0)

    def test_different_whitespace(self):
        raw = "CPU utilization for five seconds:   5 %/ 1 %; one minute:  4 %; five minutes:  3 %\n"
        res = parse_cpu(raw)
        self.assertEqual(res["five_sec_pct"], 5.0)
        self.assertEqual(res["one_min_pct"], 4.0)
        self.assertEqual(res["five_min_pct"], 3.0)

class TestParseMemoryEdgeCases(unittest.TestCase):
    def test_malformed_used_greater_than_total(self):
        raw = "Processor    6620BC0   1000   2000   0\n"
        res = parse_memory(raw)
        self.assertEqual(res["total_bytes"], 1000)
        self.assertEqual(res["used_bytes"], 2000)
        self.assertEqual(res["used_pct"], 200.0)

    def test_zero_total_bytes(self):
        raw = "Processor    6620BC0   0   0   0\n"
        res = parse_memory(raw)
        self.assertEqual(res["total_bytes"], 0)
        self.assertEqual(res["used_pct"], 0.0)

    def test_large_memory_values(self):
        raw = "Processor    6620BC0   8589934592   4294967296   4294967296\n"
        res = parse_memory(raw)
        self.assertEqual(res["total_bytes"], 8589934592)
        self.assertEqual(res["used_bytes"], 4294967296)
        self.assertEqual(res["used_pct"], 50.0)

class TestParseOspfNeighborsEdgeCases(unittest.TestCase):
    def test_2way_drother(self):
        raw = "10.10.10.4        1   2WAY/DROTHER    00:00:35    10.10.10.4      GigabitEthernet0/1\n"
        res = parse_ospf_neighbors(raw)
        self.assertEqual(res[0]["state"], "2WAY/DROTHER")

    def test_init_state(self):
        raw = "10.10.10.5        1   INIT/DROTHER    00:00:35    10.10.10.5      GigabitEthernet0/1\n"
        res = parse_ospf_neighbors(raw)
        self.assertEqual(res[0]["state"], "INIT/DROTHER")

    def test_header_only(self):
        raw = "Neighbor ID     Pri   State           Dead Time   Address         Interface\n"
        res = parse_ospf_neighbors(raw)
        self.assertEqual(res, [])

class TestParseMacTableEdgeCases(unittest.TestCase):
    def test_static_mac(self):
        raw = "  10    aabb.cc00.0100    STATIC      Gi0/0\n"
        res = parse_mac_table(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["type"], "Static")

    def test_summary_line(self):
        raw = "Total Mac Addresses for this criterion: 1\n"
        res = parse_mac_table(raw)
        self.assertEqual(res, [])

class TestParseHostnameEdgeCases(unittest.TestCase):
    def test_special_characters(self):
        raw = "!\nhostname R1-CORE-01\n!\n"
        res = parse_hostname(raw)
        self.assertEqual(res, "R1-CORE-01")

    def test_multiple_hostname_lines(self):
        raw = "!\nhostname R1\n!\n! this is a comment about hostname R2\nhostname R2\n!\n"
        res = parse_hostname(raw)
        self.assertEqual(res, "R1")

class TestOspfRouteTypes(unittest.TestCase):
    def test_ospf_ia_route(self):
        raw = 'O IA  10.1.0.0/24 [110/20] via 192.168.1.2, 00:05:00, GigabitEthernet0/0\n'
        res = parse_routing(raw)
        self.assertEqual(res['ospf_routes'], 1)

    def test_ospf_e2_route(self):
        raw = 'O E2  172.16.0.0/16 [110/20] via 192.168.1.2, 00:05:00, GigabitEthernet0/0\n'
        res = parse_routing(raw)
        self.assertEqual(res['ospf_routes'], 1)

    def test_ospf_e1_route(self):
        raw = 'O E1  172.17.0.0/16 [110/30] via 192.168.1.2, 00:05:00, GigabitEthernet0/0\n'
        res = parse_routing(raw)
        self.assertEqual(res['ospf_routes'], 1)

    def test_ospf_star_e2_route(self):
        raw = 'O*E2  0.0.0.0/0 [110/1] via 192.168.1.1, 00:10:00, GigabitEthernet0/0\n'
        res = parse_routing(raw)
        self.assertEqual(res['ospf_routes'], 1)
        self.assertEqual(res['default_route'], '192.168.1.1')

    def test_ospf_n2_route(self):
        raw = 'O N2  10.99.0.0/24 [110/20] via 192.168.1.2, 00:05:00, GigabitEthernet0/0\n'
        res = parse_routing(raw)
        self.assertEqual(res['ospf_routes'], 1)

    def test_eigrp_not_counted_as_ospf(self):
        raw = 'D     10.2.0.0/24 [90/2560] via 192.168.1.3\n'
        res = parse_routing(raw)
        self.assertEqual(res['ospf_routes'], 0)
        self.assertEqual(res['total_routes'], 0)

    def test_mixed_ospf_routes(self):
        raw = '''O     10.0.1.0/24 [110/2] via 192.168.1.2
O IA  10.0.2.0/24 [110/3] via 192.168.1.2
O E2  10.0.3.0/24 [110/20] via 192.168.1.2
C     192.168.1.0/24 is directly connected
S     10.0.4.0/24 [1/0] via 192.168.1.1
'''
        res = parse_routing(raw)
        self.assertEqual(res['ospf_routes'], 3)
        self.assertEqual(res['connected'], 1)
        self.assertEqual(res['static'], 1)
        self.assertEqual(res['total_routes'], 5)


class TestInterfaceProtocolVariants(unittest.TestCase):
    def test_up_spoofing(self):
        """Loopback interfaces may show 'up (spoofing)' in protocol column."""
        raw = 'Loopback0                  10.0.0.1        YES manual up                    up (spoofing)\n'
        res = parse_interfaces(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['name'], 'Loopback0')
        self.assertEqual(res[0]['protocol'], 'up')

    def test_up_connected(self):
        """Some IOS-XE show 'up (connected)' for interfaces."""
        raw = 'GigabitEthernet0/0         192.168.1.1     YES manual up                    up (connected)\n'
        res = parse_interfaces(raw)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['protocol'], 'up')

if __name__ == "__main__":
    unittest.main(verbosity=2)
