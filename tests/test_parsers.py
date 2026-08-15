"""
tests/test_parsers.py
──────────────────────
Unit tests for collector/parsers.py

Run with:  python -m pytest tests/ -v
       or: python -m unittest discover tests/
"""

from __future__ import annotations
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.parsers import (
    parse_version,
    parse_interfaces,
    count_interface_status,
    parse_vlans,
    parse_mac_table,
    parse_routing,
    parse_ospf_neighbors,
    parse_cpu,
    parse_memory,
    parse_hostname,
)


# ── parse_version ──────────────────────────────────────────────────────────

class TestParseVersion(unittest.TestCase):
    SAMPLE = (
        "Cisco IOS Software, Version 15.9(3)M2, RELEASE SOFTWARE (fc2)\n"
        "uptime is 14 days, 3 hours, 22 minutes\n"
        "cisco ISR4321/K9 (1RU) processor with 1795999K bytes of memory.\n"
        "4194304K bytes of physical memory.\n"
    )

    def test_ios_version_extracted(self):
        result = parse_version(self.SAMPLE)
        self.assertEqual(result["ios_version"], "15.9(3)M2")

    def test_uptime_extracted(self):
        result = parse_version(self.SAMPLE)
        self.assertIn("14 days", result["uptime"])

    def test_platform_extracted(self):
        result = parse_version(self.SAMPLE)
        self.assertIn("ISR4321", result["platform"])

    def test_empty_input_returns_defaults(self):
        result = parse_version("")
        self.assertEqual(result["ios_version"], "Unknown")
        self.assertEqual(result["uptime"], "Unknown")


# ── parse_interfaces ───────────────────────────────────────────────────────

class TestParseInterfaces(unittest.TestCase):
    SAMPLE = (
        "Interface              IP-Address      OK? Method Status                Protocol\n"
        "GigabitEthernet0/0     192.168.1.1     YES NVRAM  up                    up\n"
        "GigabitEthernet0/1     10.10.10.1      YES NVRAM  up                    up\n"
        "GigabitEthernet0/2     unassigned      YES NVRAM  administratively down down\n"
        "Loopback0              1.1.1.1         YES NVRAM  up                    up\n"
    )

    def test_correct_count(self):
        result = parse_interfaces(self.SAMPLE)
        self.assertEqual(len(result), 4)

    def test_first_interface_up(self):
        result = parse_interfaces(self.SAMPLE)
        gi0 = next(r for r in result if r["name"] == "GigabitEthernet0/0")
        self.assertEqual(gi0["protocol"], "up")
        self.assertEqual(gi0["ip"], "192.168.1.1")

    def test_admin_down_detected(self):
        result = parse_interfaces(self.SAMPLE)
        gi2 = next(r for r in result if r["name"] == "GigabitEthernet0/2")
        self.assertEqual(gi2["protocol"], "down")
        self.assertIn("administratively", gi2["status"])

    def test_empty_input_returns_empty_list(self):
        self.assertEqual(parse_interfaces(""), [])

    def test_count_interface_status(self):
        interfaces = parse_interfaces(self.SAMPLE)
        counts = count_interface_status(interfaces)
        self.assertEqual(counts["up"], 3)
        self.assertEqual(counts["down"], 1)


# ── parse_vlans ────────────────────────────────────────────────────────────

class TestParseVlans(unittest.TestCase):
    SAMPLE = (
        "VLAN Name                             Status    Ports\n"
        "---- -------------------------------- --------- ------\n"
        "1    default                          active    Gi0/0\n"
        "10   ADMIN                            active    Gi0/0\n"
        "20   HR                               active    Gi0/1\n"
    )

    def test_vlan_count(self):
        self.assertEqual(len(parse_vlans(self.SAMPLE)), 3)

    def test_vlan_fields(self):
        vlans = parse_vlans(self.SAMPLE)
        admin = next(v for v in vlans if v["id"] == 10)
        self.assertEqual(admin["name"], "ADMIN")
        self.assertEqual(admin["status"], "active")

    def test_unsupported_platform(self):
        self.assertEqual(parse_vlans("% Command not supported on this platform"), [])


# ── parse_mac_table ────────────────────────────────────────────────────────

class TestParseMacTable(unittest.TestCase):
    SAMPLE = (
        "Vlan    Mac Address       Type        Ports\n"
        "----    -----------       --------    -----\n"
        "  10    aabb.cc00.0100    DYNAMIC     Gi0/0\n"
        "  20    aabb.cc00.0200    DYNAMIC     Gi0/1\n"
    )

    def test_entry_count(self):
        self.assertEqual(len(parse_mac_table(self.SAMPLE)), 2)

    def test_entry_fields(self):
        entries = parse_mac_table(self.SAMPLE)
        self.assertEqual(entries[0]["vlan"], 10)
        self.assertEqual(entries[0]["mac"],  "aabb.cc00.0100")
        self.assertEqual(entries[0]["type"], "Dynamic")
        self.assertEqual(entries[0]["port"], "Gi0/0")

    def test_unsupported_platform(self):
        self.assertEqual(parse_mac_table("% Command not supported on this platform"), [])


# ── parse_routing ──────────────────────────────────────────────────────────

class TestParseRouting(unittest.TestCase):
    SAMPLE = (
        "C     192.168.1.0/24 is directly connected, GigabitEthernet0/0\n"
        "C     10.10.10.0/30  is directly connected, GigabitEthernet0/1\n"
        "O     192.168.2.0/24 [110/2] via 10.10.10.2, GigabitEthernet0/1\n"
        "S*    0.0.0.0/0 [1/0] via 10.10.10.1\n"
    )

    def test_route_counts(self):
        result = parse_routing(self.SAMPLE)
        self.assertEqual(result["connected"],   2)
        self.assertEqual(result["ospf_routes"], 1)
        self.assertEqual(result["static"],      1)
        self.assertEqual(result["total_routes"], 4)

    def test_empty_routing_table(self):
        result = parse_routing("")
        self.assertEqual(result["total_routes"], 0)


# ── parse_ospf_neighbors ───────────────────────────────────────────────────

class TestParseOspfNeighbors(unittest.TestCase):
    SAMPLE = (
        "Neighbor ID     Pri   State           Dead Time   Address         Interface\n"
        "10.10.10.2        1   FULL/DR         00:00:37    10.10.10.2      GigabitEthernet0/1\n"
        "10.10.10.3        1   FULL/BDR        00:00:39    10.10.10.3      GigabitEthernet0/1\n"
    )

    def test_neighbor_count(self):
        self.assertEqual(len(parse_ospf_neighbors(self.SAMPLE)), 2)

    def test_neighbor_state(self):
        neighbors = parse_ospf_neighbors(self.SAMPLE)
        self.assertIn("FULL", neighbors[0]["state"])

    def test_no_neighbors(self):
        self.assertEqual(parse_ospf_neighbors(""), [])


# ── parse_cpu ──────────────────────────────────────────────────────────────

class TestParseCpu(unittest.TestCase):
    SAMPLE = "CPU utilization for five seconds: 87%/62%; one minute: 85%; five minutes: 84%\n"

    def test_five_sec(self):
        self.assertEqual(parse_cpu(self.SAMPLE)["five_sec_pct"], 87.0)

    def test_one_min(self):
        self.assertEqual(parse_cpu(self.SAMPLE)["one_min_pct"], 85.0)

    def test_empty_input(self):
        result = parse_cpu("")
        self.assertEqual(result["five_sec_pct"], 0.0)


# ── parse_memory ───────────────────────────────────────────────────────────

class TestParseMemory(unittest.TestCase):
    SAMPLE = "Processor    6620BC0   429496320   180355072   249141248  249074320   248918112\n"

    def test_total_bytes(self):
        self.assertEqual(parse_memory(self.SAMPLE)["total_bytes"], 429496320)

    def test_used_bytes(self):
        self.assertEqual(parse_memory(self.SAMPLE)["used_bytes"], 180355072)

    def test_used_pct_calculated(self):
        result = parse_memory(self.SAMPLE)
        expected = round(180355072 / 429496320 * 100, 1)
        self.assertAlmostEqual(result["used_pct"], expected, places=1)

    def test_empty_input(self):
        result = parse_memory("")
        self.assertEqual(result["total_bytes"], 0)


# ── parse_hostname ─────────────────────────────────────────────────────────

class TestParseHostname(unittest.TestCase):
    def test_hostname_extracted(self):
        raw = "!\nhostname R1\n!\ninterface Gi0/0\n"
        self.assertEqual(parse_hostname(raw), "R1")

    def test_missing_hostname(self):
        self.assertEqual(parse_hostname(""), "Unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
