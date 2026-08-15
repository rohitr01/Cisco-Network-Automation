"""
collector/parsers.py
────────────────────
Parse raw Cisco IOS CLI output into structured Python dicts/lists.

Each parser is a pure function:
    parse_<command>(raw: str) -> dict | list

No SSH logic lives here — these functions are independently testable.
"""

from __future__ import annotations
import re


# ── Version / Hostname ─────────────────────────────────────────────────────

def parse_version(raw: str) -> dict:
    """
    Extract hostname, IOS version, uptime, platform and memory from
    'show version' output.
    """
    result = {
        "ios_version": "Unknown",
        "uptime":      "Unknown",
        "platform":    "Unknown",
        "memory_total_kb": None,
    }

    # IOS version line
    m = re.search(r"Version\s+([\d().a-zA-Z]+)", raw)
    if m:
        result["ios_version"] = m.group(1)

    # Uptime
    m = re.search(r"uptime is (.+)", raw)
    if m:
        result["uptime"] = m.group(1).strip()

    # Platform — "cisco ISR4321/K9 ... processor" line, not "Cisco IOS Software"
    m = re.search(r"^cisco\s+(\S+)\s+.*processor", raw, re.IGNORECASE | re.MULTILINE)
    if m:
        result["platform"] = m.group(1)

    # Memory (bytes → KB)
    m = re.search(r"(\d+)K? bytes of physical memory", raw)
    if m:
        result["memory_total_kb"] = int(m.group(1))

    return result


# ── Interfaces ────────────────────────────────────────────────────────────

def parse_interfaces(raw: str) -> list[dict]:
    """
    Parse 'show ip interface brief' output.

    Returns a list of dicts:
        {name, ip, ok, method, status, protocol}
    """
    interfaces = []
    # Skip header lines
    for line in raw.splitlines():
        # Match data rows: starts with a letter (interface name)
        # Protocol field may include parenthetical text, e.g. "up (spoofing)"
        m = re.match(
            r"^(\S+)\s+([\d.]+|unassigned)\s+(\S+)\s+(\S+)\s+(.+?)\s+(up|down)(?:\s.*)?$",
            line,
        )
        if m:
            interfaces.append({
                "name":     m.group(1),
                "ip":       m.group(2),
                "ok":       m.group(3),
                "method":   m.group(4),
                "status":   m.group(5).strip(),
                "protocol": m.group(6),
            })
    return interfaces


def count_interface_status(interfaces: list[dict]) -> dict:
    """Return counts of up/down interfaces."""
    up   = sum(1 for i in interfaces if i["protocol"] == "up")
    down = len(interfaces) - up
    return {"up": up, "down": down, "total": len(interfaces)}


# ── VLANs ─────────────────────────────────────────────────────────────────

def parse_vlans(raw: str) -> list[dict]:
    """
    Parse 'show vlan brief' output.

    Returns a list of dicts: {id, name, status}
    Returns empty list for unsupported platforms.
    """
    if "not supported" in raw.lower() or "invalid" in raw.lower():
        return []

    vlans = []
    for line in raw.splitlines():
        m = re.match(r"^(\d+)\s+(\S+)\s+(active|act\/unsup|suspended)\s*", line)
        if m:
            vlans.append({
                "id":     int(m.group(1)),
                "name":   m.group(2),
                "status": m.group(3),
            })
    return vlans


# ── MAC Address Table ──────────────────────────────────────────────────────

def parse_mac_table(raw: str) -> list[dict]:
    """
    Parse 'show mac address-table' output.

    Returns a list of dicts: {vlan, mac, type, port}
    """
    if "not supported" in raw.lower():
        return []

    entries = []
    for line in raw.splitlines():
        m = re.match(
            r"^\s*(\d+)\s+([\da-f.]+)\s+(DYNAMIC|STATIC)\s+(\S+)\s*$",
            line,
            re.IGNORECASE,
        )
        if m:
            entries.append({
                "vlan": int(m.group(1)),
                "mac":  m.group(2),
                "type": m.group(3).capitalize(),
                "port": m.group(4),
            })
    return entries


# ── Routing Table ──────────────────────────────────────────────────────────

def parse_routing(raw: str) -> dict:
    """
    Summarise 'show ip route' output.

    Returns:
        {
          total_routes: int,
          ospf_routes:  int,
          connected:    int,
          static:       int,
          default_route: str | None,
        }
    """
    result = {
        "total_routes":  0,
        "ospf_routes":   0,
        "connected":     0,
        "static":        0,
        "default_route": None,
    }

    for line in raw.splitlines():
        # OSPF routes: O, O IA, O E1, O E2, O*E2, O N1, O N2
        if re.match(r"^O(?:\s|\*)", line):
            result["ospf_routes"] += 1
            result["total_routes"] += 1
        elif re.match(r"^C\s", line):
            result["connected"] += 1
            result["total_routes"] += 1
        elif re.match(r"^S\s", line) or re.match(r"^S\*", line):
            result["static"] += 1
            result["total_routes"] += 1
        elif re.match(r"^L\s", line) or re.match(r"^B\s", line):
            result["total_routes"] += 1

        if "0.0.0.0/0" in line or "Gateway of last resort" in line:
            # Match 'via 10.0.0.1' or 'is 192.168.1.1 to'
            m = re.search(r"via\s+([\d.]+)", line)
            if m:
                result["default_route"] = m.group(1)
            else:
                m = re.search(r"is\s+([\d.]+)\s+to", line)
                if m:
                    result["default_route"] = m.group(1)

    return result


# ── OSPF Neighbors ────────────────────────────────────────────────────────

def parse_ospf_neighbors(raw: str) -> list[dict]:
    """
    Parse 'show ip ospf neighbor' output.

    Returns a list of dicts:
        {neighbor_id, state, dead_time, address, interface}
    """
    neighbors = []
    for line in raw.splitlines():
        m = re.match(
            r"^([\d.]+)\s+\d+\s+(\S+)\s+(\S+)\s+([\d.]+)\s+(\S+)\s*$",
            line,
        )
        if m:
            neighbors.append({
                "neighbor_id": m.group(1),
                "state":       m.group(2),
                "dead_time":   m.group(3),
                "address":     m.group(4),
                "interface":   m.group(5),
            })
    return neighbors


# ── CPU ───────────────────────────────────────────────────────────────────

def parse_cpu(raw: str) -> dict:
    """
    Parse 'show processes cpu sorted' output.

    Returns:
        {five_sec_pct: float, one_min_pct: float, five_min_pct: float}
    """
    result = {"five_sec_pct": 0.0, "one_min_pct": 0.0, "five_min_pct": 0.0}

    # "CPU utilization for five seconds: 18%/4%; one minute: 16%; five minutes: 15%"
    # Accept optional whitespace between number and % sign for IOS format variants
    m = re.search(
        r"five seconds:\s*([\d.]+)\s*%.*?one minute:\s*([\d.]+)\s*%.*?five minutes:\s*([\d.]+)\s*%",
        raw,
        re.DOTALL,
    )
    if m:
        result["five_sec_pct"] = float(m.group(1))
        result["one_min_pct"]  = float(m.group(2))
        result["five_min_pct"] = float(m.group(3))

    return result


# ── Memory ────────────────────────────────────────────────────────────────

def parse_memory(raw: str) -> dict:
    """
    Parse 'show processes memory sorted' output.

    Returns:
        {total_bytes: int, used_bytes: int, free_bytes: int, used_pct: float}
    """
    result = {
        "total_bytes": 0,
        "used_bytes":  0,
        "free_bytes":  0,
        "used_pct":    0.0,
    }

    # "Processor  6620BC0  429496320  180355072  249141248 ..."
    m = re.search(
        r"Processor\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)",
        raw,
    )
    if m:
        result["total_bytes"] = int(m.group(1))
        result["used_bytes"]  = int(m.group(2))
        result["free_bytes"]  = int(m.group(3))
        if result["total_bytes"] > 0:
            result["used_pct"] = round(
                result["used_bytes"] / result["total_bytes"] * 100, 1
            )

    return result


# ── Hostname from running-config ───────────────────────────────────────────

def parse_hostname(raw: str) -> str:
    """Extract 'hostname' from show running-config output."""
    m = re.search(r"^hostname\s+(\S+)", raw, re.MULTILINE)
    return m.group(1) if m else "Unknown"
