import unittest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.inventory import load_inventory

class TestInventory(unittest.TestCase):
    def test_valid_csv(self):
        from config.settings import INVENTORY_FILE
        if INVENTORY_FILE.exists():
            devices = load_inventory(INVENTORY_FILE)
            self.assertEqual(len(devices), 5)
            for device in devices:
                self.assertIn('hostname', device)
                self.assertIn('ip', device)
                self.assertIn('device_type', device)
                self.assertIn('role', device)
        else:
            self.skipTest("Real inventory file not found")

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_inventory(Path("non_existent_file.csv"))

    def test_disabled_device(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("hostname,ip,enabled\n")
            f.write("router1,10.0.0.1,true\n")
            f.write("router2,10.0.0.2,false\n")
            temp_path = Path(f.name)
            
        try:
            devices = load_inventory(temp_path)
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['hostname'], 'router1')
        finally:
            os.unlink(temp_path)

    def test_missing_hostname(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("hostname,ip\n")
            f.write(",10.0.0.1\n")
            f.write("router2,10.0.0.2\n")
            temp_path = Path(f.name)
            
        try:
            devices = load_inventory(temp_path)
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['hostname'], 'router2')
        finally:
            os.unlink(temp_path)

    def test_host_column(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("hostname,host\n")
            f.write("router1,10.0.0.1\n")
            temp_path = Path(f.name)
            
        try:
            devices = load_inventory(temp_path)
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]['ip'], '10.0.0.1')
        finally:
            os.unlink(temp_path)

if __name__ == '__main__':
    unittest.main()
