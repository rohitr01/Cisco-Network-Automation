import sys
import unittest
from pathlib import Path
import tempfile
import json
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.info_collector import load_inventory, collect_device, save_device_json
from mock.mock_devices import get_mock_devices, MOCK_OUTPUT
from reports.report_generator import generate_report
from backup.backup_tool import _backup_one_dry
from config import settings

class TestInventoryLoading(unittest.TestCase):
    def setUp(self):
        self.inventory_path = Path(__file__).parent.parent / "inventory" / "devices.csv"

    def test_load_valid_devices(self):
        devices = load_inventory(self.inventory_path)
        self.assertEqual(len(devices), 5)

    def test_device_fields(self):
        devices = load_inventory(self.inventory_path)
        for dev in devices:
            self.assertIn("hostname", dev)
            self.assertIn("ip", dev)
            self.assertIn("device_type", dev)

    def test_default_device_type(self):
        devices = load_inventory(self.inventory_path)
        for dev in devices:
            self.assertEqual(dev["device_type"], "cisco_ios")
            
    def test_invalid_csv_path(self):
        with self.assertRaises(FileNotFoundError):
            load_inventory(Path("invalid_path.csv"))

class TestMockDeviceData(unittest.TestCase):
    def setUp(self):
        self.inventory_path = Path(__file__).parent.parent / "inventory" / "devices.csv"
        self.inventory = load_inventory(self.inventory_path)

    def test_all_devices_mock_data(self):
        mock_data = get_mock_devices(self.inventory)
        self.assertEqual(len(mock_data), 5)
        hostnames = [d["hostname"] for d in mock_data]
        expected_hostnames = ["R1", "R2", "R3", "SW1", "SW2"]
        self.assertCountEqual(hostnames, expected_hostnames)

    def test_sw2_unreachable(self):
        mock_data = get_mock_devices(self.inventory)
        sw2 = next(d for d in mock_data if d["hostname"] == "SW2")
        self.assertIsNone(sw2["output"])

    def test_r1_all_outputs(self):
        mock_data = get_mock_devices(self.inventory)
        r1 = next(d for d in mock_data if d["hostname"] == "R1")
        commands = ["running_config", "version", "interfaces", "vlans", "mac_table", "routing", "ospf_neighbors", "cpu", "memory"]
        for cmd in commands:
            self.assertIn(cmd, r1["output"])

    def test_default_fallback(self):
        from mock.mock_devices import _make_device
        dev = _make_device("UNKNOWN_ROUTER", "1.1.1.1")
        self.assertEqual(dev["output"], MOCK_OUTPUT["DEFAULT"])

    def test_mock_data_not_empty(self):
        mock_data = get_mock_devices(self.inventory)
        r1 = next(d for d in mock_data if d["hostname"] == "R1")
        for key, value in r1["output"].items():
            self.assertTrue(len(value) > 0)
        
        r3 = next(d for d in mock_data if d["hostname"] == "R3")
        self.assertEqual(r3["output"]["ospf_neighbors"], "") # Intentional empty string

class TestDryRunCollection(unittest.TestCase):
    def setUp(self):
        self.inventory_path = Path(__file__).parent.parent / "inventory" / "devices.csv"
        self.inventory = load_inventory(self.inventory_path)
        self.r1 = next(d for d in self.inventory if d["hostname"] == "R1")
        self.r2 = next(d for d in self.inventory if d["hostname"] == "R2")
        self.sw2 = next(d for d in self.inventory if d["hostname"] == "SW2")

    def test_r1_reachable(self):
        data = collect_device(self.r1, {}, dry_run=True)
        self.assertTrue(data["reachable"])

    def test_sw2_unreachable(self):
        data = collect_device(self.sw2, {}, dry_run=True)
        self.assertFalse(data["reachable"])

    def test_r1_parsed_interfaces(self):
        data = collect_device(self.r1, {}, dry_run=True)
        self.assertIsInstance(data["interfaces"], list)
        self.assertTrue(len(data["interfaces"]) > 0)

    def test_r1_health_dict(self):
        data = collect_device(self.r1, {}, dry_run=True)
        self.assertIn("health", data)
        health = data["health"]
        for key in ["score", "grade", "status", "alerts", "breakdown"]:
            self.assertIn(key, health)

    def test_r2_health_lower_than_r1(self):
        data_r1 = collect_device(self.r1, {}, dry_run=True)
        data_r2 = collect_device(self.r2, {}, dry_run=True)
        self.assertTrue(data_r2["health"]["score"] < data_r1["health"]["score"])

class TestJsonSerialization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir_patcher = patch("collector.info_collector.DATA_DIR", Path(self.temp_dir.name))
        self.data_dir_patcher.start()
        
        self.inventory_path = Path(__file__).parent.parent / "inventory" / "devices.csv"
        self.inventory = load_inventory(self.inventory_path)
        self.r1 = next(d for d in self.inventory if d["hostname"] == "R1")

    def tearDown(self):
        self.data_dir_patcher.stop()
        self.temp_dir.cleanup()

    def test_save_json_exists(self):
        data = collect_device(self.r1, {}, dry_run=True)
        path = save_device_json(data)
        self.assertTrue(path.exists())

    def test_load_json_matches(self):
        data = collect_device(self.r1, {}, dry_run=True)
        path = save_device_json(data)
        with open(path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data, data)

    def test_json_required_keys(self):
        data = collect_device(self.r1, {}, dry_run=True)
        path = save_device_json(data)
        with open(path, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        for key in ["hostname", "ip", "reachable", "collected_at", "health"]:
            self.assertIn(key, loaded_data)

class TestReportGeneration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.reports_dir_patcher = patch("reports.report_generator.REPORTS_DIR", Path(self.temp_dir.name))
        self.reports_dir_patcher.start()
        
        self.inventory_path = Path(__file__).parent.parent / "inventory" / "devices.csv"
        self.inventory = load_inventory(self.inventory_path)
        self.device_data = [collect_device(d, {}, dry_run=True) for d in self.inventory]

    def tearDown(self):
        self.reports_dir_patcher.stop()
        self.temp_dir.cleanup()

    def test_generate_report_exists_not_empty(self):
        report_path = generate_report(self.device_data)
        self.assertTrue(report_path.exists())
        self.assertTrue(report_path.stat().st_size > 0)

    def test_html_contains_hostnames(self):
        report_path = generate_report(self.device_data)
        content = report_path.read_text(encoding="utf-8")
        for hostname in ["R1", "R2", "R3", "SW1", "SW2"]:
            self.assertIn(hostname, content)

    def test_html_contains_title(self):
        report_path = generate_report(self.device_data)
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("Network Health Report", content)

    def test_html_contains_health_scores(self):
        report_path = generate_report(self.device_data)
        content = report_path.read_text(encoding="utf-8")
        self.assertIn(str(self.device_data[0]["health"]["score"]), content)

class TestBackupDryRun(unittest.TestCase):
    def setUp(self):
        self.inventory_path = Path(__file__).parent.parent / "inventory" / "devices.csv"
        self.inventory = load_inventory(self.inventory_path)

    def test_backup_r1_dry(self):
        r1 = next(d for d in self.inventory if d["hostname"] == "R1")
        success, config = _backup_one_dry(r1)
        self.assertTrue(success)
        self.assertIn("hostname R1", config)

    def test_backup_sw2_dry(self):
        sw2 = next(d for d in self.inventory if d["hostname"] == "SW2")
        success, output = _backup_one_dry(sw2)
        self.assertFalse(success)
        self.assertEqual(output, "SIMULATED TIMEOUT")

    def test_backup_config_contains_hostname(self):
        r1 = next(d for d in self.inventory if d["hostname"] == "R1")
        success, config = _backup_one_dry(r1)
        self.assertIn("hostname R1", config)

class TestEndToEndPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir_data = tempfile.TemporaryDirectory()
        self.temp_dir_reports = tempfile.TemporaryDirectory()
        
        self.data_dir_patcher = patch("collector.info_collector.DATA_DIR", Path(self.temp_dir_data.name))
        self.reports_dir_patcher = patch("reports.report_generator.REPORTS_DIR", Path(self.temp_dir_reports.name))
        
        self.data_dir_patcher.start()
        self.reports_dir_patcher.start()
        
        self.inventory_path = Path(__file__).parent.parent / "inventory" / "devices.csv"

    def tearDown(self):
        self.data_dir_patcher.stop()
        self.reports_dir_patcher.stop()
        self.temp_dir_data.cleanup()
        self.temp_dir_reports.cleanup()

    def test_full_pipeline_data_dicts(self):
        inventory = load_inventory(self.inventory_path)
        all_data = []
        for device in inventory:
            data = collect_device(device, {}, dry_run=True)
            save_device_json(data)
            all_data.append(data)
            
        self.assertEqual(len(all_data), 5)
        
        scores = [d.get("health", {}).get("score", 0) for d in all_data]
        self.assertTrue(any(score > 0 for score in scores))
        self.assertTrue(any(score == 0 for score in scores))

    def test_full_pipeline_report(self):
        inventory = load_inventory(self.inventory_path)
        all_data = []
        for device in inventory:
            data = collect_device(device, {}, dry_run=True)
            save_device_json(data)
            all_data.append(data)
            
        report_path = generate_report(all_data)
        self.assertTrue(report_path.exists())
        self.assertTrue(report_path.stat().st_size > 0)

if __name__ == '__main__':
    unittest.main()
