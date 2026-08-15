"""
mock/mock_devices.py
────────────────────
Realistic Cisco IOS CLI output for every supported command.

Used by --dry-run mode so the entire pipeline
(Collect → Parse → Analyze → Report) can be demonstrated
without a real device or network connection.

Each device returns slightly different data so the dashboard
shows a mix of healthy, warning, and degraded states.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_device(hostname: str, ip: str) -> dict:
    """
    Return a dict that mirrors what info_collector.py collects over SSH.
    Keys match COMMANDS keys in config/settings.py.
    """
    return {
        "hostname": hostname,
        "ip":       ip,
        "output":   MOCK_OUTPUT.get(hostname, MOCK_OUTPUT["DEFAULT"]),
    }


def get_mock_devices(inventory: list[dict]) -> list[dict]:
    """Return mock device data for every entry in the inventory."""
    return [_make_device(row["hostname"], row["ip"]) for row in inventory]


# ---------------------------------------------------------------------------
# Realistic IOS output per device
# ---------------------------------------------------------------------------

MOCK_OUTPUT: dict[str, dict[str, str]] = {

    # ── R1 — healthy router ─────────────────────────────────────────────
    "R1": {
        "running_config": """\
Current configuration : 3142 bytes
!
hostname R1
!
interface GigabitEthernet0/0
 ip address 192.168.1.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 ip address 10.10.10.1 255.255.255.252
 no shutdown
!
interface GigabitEthernet0/2
 no ip address
 shutdown
!
router ospf 1
 network 192.168.1.0 0.0.0.255 area 0
 network 10.10.10.0 0.0.0.3 area 0
!
end""",

        "version": """\
Cisco IOS Software, Version 15.9(3)M2, RELEASE SOFTWARE (fc2)
Technical Support: http://www.cisco.com/techsupport
ROM: System Bootstrap, Version 15.9(3r)M2
uptime is 14 days, 3 hours, 22 minutes
cisco ISR4321/K9 (1RU) processor with 1795999K/6147K bytes of memory.
Processor board ID FLM2024W0LT
2 Gigabit Ethernet interfaces
32768K bytes of non-volatile configuration memory.
4194304K bytes of physical memory.
""",

        "interfaces": """\
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.1.1     YES NVRAM  up                    up
GigabitEthernet0/1     10.10.10.1      YES NVRAM  up                    up
GigabitEthernet0/2     unassigned      YES NVRAM  administratively down down
Loopback0              1.1.1.1         YES NVRAM  up                    up
""",

        "vlans": """\
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Gi0/0
10   ADMIN                            active    Gi0/0, Gi0/1
20   HR                               active    Gi0/1
30   IT                               active    Gi0/1
""",

        "mac_table": """\
          Mac Address Table
-------------------------------------------
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    aabb.cc00.0100    DYNAMIC     Gi0/0
  20    aabb.cc00.0200    DYNAMIC     Gi0/1
  30    aabb.cc00.0300    DYNAMIC     Gi0/1
Total Mac Addresses for this criterion: 3
""",

        "routing": """\
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       O - OSPF

Gateway of last resort is not set

      1.0.0.0/32 is subnetted, 1 subnets
C        1.1.1.1 is directly connected, Loopback0
      10.0.0.0/30 is subnetted, 1 subnets
C        10.10.10.0 is directly connected, GigabitEthernet0/1
C     192.168.1.0/24 is directly connected, GigabitEthernet0/0
O     192.168.2.0/24 [110/2] via 10.10.10.2, 00:03:14, GigabitEthernet0/1
O     192.168.3.0/24 [110/3] via 10.10.10.2, 00:03:14, GigabitEthernet0/1
""",

        "ospf_neighbors": """\
Neighbor ID     Pri   State           Dead Time   Address         Interface
10.10.10.2        1   FULL/DR         00:00:37    10.10.10.2      GigabitEthernet0/1
10.10.10.3        1   FULL/BDR        00:00:39    10.10.10.3      GigabitEthernet0/1
""",

        "cpu": """\
CPU utilization for five seconds: 18%/4%; one minute: 16%; five minutes: 15%
 PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process
   1       18280       20381        897  0.00%  0.00%  0.00%   0 Chunk Manager
   2      113760      432111        263  0.00%  0.00%  0.00%   0 Load Meter
 112     1024563     4032901        254  0.23%  0.20%  0.19%   0 IP Input
""",

        "memory": """\
                Head    Total(b)     Used(b)     Free(b) Lowest(b) Largest(b)
Processor    6620BC0   429496320   180355072   249141248  249074320   248918112
I/O         3C800000    67108864    24576000    42532864   42532864    42532864

 PID TTY  Allocated      Freed    Holding    Getbufs    Retbufs Process
   0   0    3706392   16497352     916012          0          0 *Init*
   1   0      10920       8200       2720          0          0 Chunk Manager
""",
    },

    # ── R2 — high CPU warning ───────────────────────────────────────────
    "R2": {
        "running_config": """\
hostname R2
!
interface GigabitEthernet0/0
 ip address 192.168.2.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 ip address 10.10.10.2 255.255.255.252
 no shutdown
!
router ospf 1
 network 192.168.2.0 0.0.0.255 area 0
 network 10.10.10.0 0.0.0.3 area 0
!
end""",

        "version": """\
Cisco IOS Software, Version 15.7(3)M5, RELEASE SOFTWARE (fc1)
uptime is 2 days, 11 hours, 5 minutes
cisco ISR4321/K9 processor with 1795999K bytes of memory.
""",

        "interfaces": """\
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.2.1     YES NVRAM  up                    up
GigabitEthernet0/1     10.10.10.2      YES NVRAM  up                    up
""",

        "vlans": """\
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active
10   ADMIN                            active    Gi0/0
20   HR                               active    Gi0/0
""",

        "mac_table": """\
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    aabb.cc00.0400    DYNAMIC     Gi0/0
Total Mac Addresses for this criterion: 1
""",

        "routing": """\
C     192.168.2.0/24 is directly connected, GigabitEthernet0/0
C     10.10.10.0/30  is directly connected, GigabitEthernet0/1
O     192.168.1.0/24 [110/2] via 10.10.10.1, 00:01:44, GigabitEthernet0/1
""",

        "ospf_neighbors": """\
Neighbor ID     Pri   State           Dead Time   Address         Interface
10.10.10.1        1   FULL/BDR        00:00:38    10.10.10.1      GigabitEthernet0/1
""",

        "cpu": """\
CPU utilization for five seconds: 87%/62%; one minute: 85%; five minutes: 84%
 PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process
 112     9024563     4032901        254  62.00%  61.0%  60.0%   0 IP Input
   2      213760      432111        263  3.00%  2.50%  2.00%   0 Load Meter
""",

        "memory": """\
                Head    Total(b)     Used(b)     Free(b) Lowest(b) Largest(b)
Processor    6620BC0   429496320   200000000   229496320  229400000   229396000
""",
    },

    # ── R3 — OSPF down ──────────────────────────────────────────────────
    "R3": {
        "running_config": """\
hostname R3
!
interface GigabitEthernet0/0
 ip address 192.168.3.1 255.255.255.0
 no shutdown
!
interface GigabitEthernet0/1
 ip address 10.10.10.3 255.255.255.252
 no shutdown
!
end""",

        "version": """\
Cisco IOS Software, Version 15.9(3)M2, RELEASE SOFTWARE (fc2)
uptime is 0 days, 4 hours, 12 minutes
cisco ISR4321/K9 processor with 1795999K bytes of memory.
""",

        "interfaces": """\
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     192.168.3.1     YES NVRAM  up                    up
GigabitEthernet0/1     10.10.10.3      YES NVRAM  up                    up
""",

        "vlans": "% Command not supported on this platform",

        "mac_table": "% Command not supported on this platform",

        "routing": """\
C     192.168.3.0/24 is directly connected, GigabitEthernet0/0
C     10.10.10.0/30  is directly connected, GigabitEthernet0/1
""",

        "ospf_neighbors": "",  # No OSPF neighbors — triggers alert

        "cpu": """\
CPU utilization for five seconds: 22%/5%; one minute: 21%; five minutes: 20%
""",

        "memory": """\
                Head    Total(b)     Used(b)     Free(b) Lowest(b) Largest(b)
Processor    6620BC0   429496320   100000000   329496320  329400000   329000000
""",
    },

    # ── SW1 — switch, high memory ────────────────────────────────────────
    "SW1": {
        "running_config": """\
hostname SW1
!
interface GigabitEthernet0/0
 switchport mode access
 switchport access vlan 10
!
interface GigabitEthernet0/1
 switchport mode trunk
!
interface Vlan10
 ip address 192.168.1.10 255.255.255.0
 no shutdown
!
end""",

        "version": """\
Cisco IOS Software, Version 15.2(7)E3, RELEASE SOFTWARE (fc2)
uptime is 30 days, 6 hours, 0 minutes
cisco WS-C2960X-48FPD-L processor with 524288K bytes of memory.
""",

        "interfaces": """\
Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet0/0     unassigned      YES unset  up                    up
GigabitEthernet0/1     unassigned      YES unset  up                    up
GigabitEthernet0/2     unassigned      YES unset  up                    up
Vlan10                 192.168.1.10    YES NVRAM  up                    up
""",

        "vlans": """\
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Gi0/2
10   ADMIN                            active    Gi0/0
20   HR                               active    Gi0/1
30   IT                               active    Gi0/1
40   SERVERS                          active    Gi0/2
""",

        "mac_table": """\
Vlan    Mac Address       Type        Ports
----    -----------       --------    -----
  10    aabb.cc00.0101    DYNAMIC     Gi0/0
  10    aabb.cc00.0102    DYNAMIC     Gi0/0
  20    aabb.cc00.0201    DYNAMIC     Gi0/1
  30    aabb.cc00.0301    DYNAMIC     Gi0/1
  40    aabb.cc00.0401    DYNAMIC     Gi0/2
Total Mac Addresses for this criterion: 5
""",

        "routing": """\
Gateway of last resort is 192.168.1.1 to network 0.0.0.0
S*    0.0.0.0/0 [1/0] via 192.168.1.1
C     192.168.1.0/24 is directly connected, Vlan10
""",

        "ospf_neighbors": "",  # Switch — no OSPF expected

        "cpu": """\
CPU utilization for five seconds: 9%/2%; one minute: 8%; five minutes: 8%
""",

        "memory": """\
                Head    Total(b)     Used(b)     Free(b) Lowest(b) Largest(b)
Processor    6620BC0   524288000   448000000    76288000   76000000   75900000
""",
    },

    # ── SW2 — unreachable (simulated) ───────────────────────────────────
    "SW2": None,  # None signals connection failure in dry-run mode

    # ── Fallback for unknown hostnames ──────────────────────────────────
    "DEFAULT": {
        "running_config": "hostname UNKNOWN\n!",
        "version":        "Cisco IOS Software, Version 15.0\n",
        "interfaces":     "",
        "vlans":          "",
        "mac_table":      "",
        "routing":        "",
        "ospf_neighbors": "",
        "cpu":            "CPU utilization for five seconds: 5%/1%;\n",
        "memory":         "Processor    6620BC0   429496320   100000000   329496320\n",
    },
}
