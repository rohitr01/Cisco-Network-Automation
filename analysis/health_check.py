"""
analysis/health_check.py
─────────────────────────
Analyse parsed device data.

Produces:
  - A health score 0–100 per device
  - A list of human-readable problem alerts

No SSH, no file I/O — pure analysis functions.
"""

from __future__ import annotations
from config.settings import (
    HEALTH_WEIGHTS,
    CPU_WARNING_THRESHOLD,
    MEMORY_WARNING_THRESHOLD,
)


# ── Problem severity levels ────────────────────────────────────────────────

class Severity:
    CRITICAL = "critical"   # 🔴
    WARNING  = "warning"    # ⚠️
    INFO     = "info"       # ℹ️


def _alert(severity: str, message: str) -> dict:
    return {"severity": severity, "message": message}


# ── Individual checks ──────────────────────────────────────────────────────

def check_interfaces(interfaces: list[dict]) -> tuple[int, list[dict]]:
    """
    Score interfaces (0–HEALTH_WEIGHTS['interfaces_healthy']).
    Deduct for down interfaces; flag admin-down vs protocol-down.
    """
    alerts   = []
    weight   = HEALTH_WEIGHTS["interfaces_healthy"]

    if not interfaces:
        return 0, [_alert(Severity.WARNING, "No interface data collected")]

    down_count = sum(1 for i in interfaces if i["protocol"] == "down")
    total      = len(interfaces)

    for iface in interfaces:
        if iface["protocol"] == "down":
            if "administratively" in iface["status"]:
                alerts.append(_alert(
                    Severity.INFO,
                    f"{iface['name']} is administratively down",
                ))
            else:
                alerts.append(_alert(
                    Severity.WARNING,
                    f"{iface['name']} is down (line protocol down)",
                ))

    # Score: full marks if no unexpected downs
    admin_downs = sum(
        1 for i in interfaces
        if i["protocol"] == "down" and "administratively" in i["status"]
    )
    unexpected_downs = down_count - admin_downs
    score = weight if unexpected_downs == 0 else max(0, weight - unexpected_downs * 5)
    return score, alerts


def check_ospf(neighbors: list[dict]) -> tuple[int, list[dict]]:
    """Score OSPF neighbor state with context-aware 2WAY handling.

    State classification:
        FULL       — Healthy: adjacency fully established.
        2WAY       — Acceptable: normal DROTHER-to-DROTHER on broadcast/NBMA
                     networks. On multi-access segments, only the DR and BDR
                     form FULL adjacencies with all neighbors; DROTHERs form
                     2WAY relationships with each other, which is expected.
        INIT/DOWN  — Problem: adjacency not forming correctly.
    """
    alerts = []
    weight = HEALTH_WEIGHTS["ospf_neighbors"]

    if not neighbors:
        # May be a switch without OSPF — flagged as warning, not critical
        alerts.append(_alert(
            Severity.WARNING,
            "OSPF has no established neighbors",
        ))
        return 0, alerts

    # Classify each neighbor by its primary state (before the slash)
    healthy_states = {"FULL", "2WAY"}
    problematic = []

    for n in neighbors:
        # State field is e.g. "FULL/DR", "2WAY/DROTHER", "INIT/ -"
        primary_state = n["state"].split("/")[0].strip()

        if primary_state in healthy_states:
            if primary_state == "2WAY":
                alerts.append(_alert(
                    Severity.INFO,
                    f"OSPF neighbor {n['neighbor_id']} is 2WAY/DROTHER "
                    f"(normal on broadcast networks)",
                ))
        else:
            problematic.append(n)
            alerts.append(_alert(
                Severity.CRITICAL,
                f"OSPF neighbor {n['neighbor_id']} is in state {n['state']} "
                f"(expected FULL or 2WAY)",
            ))

    score = weight if not problematic else max(0, weight - len(problematic) * 5)
    return score, alerts


def check_cpu(cpu: dict) -> tuple[int, list[dict]]:
    """Score CPU utilisation."""
    alerts = []
    weight = HEALTH_WEIGHTS["cpu_ok"]
    pct    = cpu.get("one_min_pct", 0)

    if pct >= CPU_WARNING_THRESHOLD:
        alerts.append(_alert(
            Severity.CRITICAL,
            f"High CPU utilisation: {pct}% (1-min avg) — threshold {CPU_WARNING_THRESHOLD}%",
        ))
        return 0, alerts

    if pct >= CPU_WARNING_THRESHOLD * 0.75:
        alerts.append(_alert(
            Severity.WARNING,
            f"Elevated CPU utilisation: {pct}% (1-min avg)",
        ))
        return weight // 2, alerts

    return weight, alerts


def check_memory(memory: dict) -> tuple[int, list[dict]]:
    """Score memory utilisation."""
    alerts = []
    weight = HEALTH_WEIGHTS["memory_ok"]
    pct    = memory.get("used_pct", 0)

    if pct >= MEMORY_WARNING_THRESHOLD:
        alerts.append(_alert(
            Severity.CRITICAL,
            f"High memory utilisation: {pct}% — threshold {MEMORY_WARNING_THRESHOLD}%",
        ))
        return 0, alerts

    if pct >= MEMORY_WARNING_THRESHOLD * 0.75:
        alerts.append(_alert(
            Severity.WARNING,
            f"Elevated memory utilisation: {pct}%",
        ))
        return weight // 2, alerts

    return weight, alerts


def check_vlans(vlans: list[dict]) -> tuple[int, list[dict]]:
    """Score VLAN presence."""
    weight = HEALTH_WEIGHTS["vlans_present"]
    if not vlans:
        return weight, []  # Not penalised — may be a router
    active = [v for v in vlans if v["status"] == "active"]
    if not active:
        return 0, [_alert(Severity.WARNING, "No active VLANs found")]
    return weight, []


def check_routing(routing: dict) -> tuple[int, list[dict]]:
    """Score routing table health."""
    alerts = []
    weight = HEALTH_WEIGHTS["routing_ok"]
    if routing.get("total_routes", 0) == 0:
        alerts.append(_alert(Severity.WARNING, "Routing table is empty"))
        return 0, alerts
    return weight, alerts


# ── Master scorer ──────────────────────────────────────────────────────────

def compute_health(device_data: dict) -> dict:
    """
    Compute overall health score and collect all alerts for one device.

    Args:
        device_data: fully parsed device dict (output of info_collector)

    Returns:
        {
          score: int,          # 0–100
          grade: str,          # A / B / C / D / F
          status: str,         # HEALTHY / DEGRADED / CRITICAL / UNREACHABLE
          alerts: list[dict],  # [{severity, message}, ...]
          breakdown: dict,     # individual component scores
        }
    """
    alerts    : list[dict] = []
    breakdown : dict[str, int] = {}

    if not device_data.get("reachable", False):
        return {
            "score":     0,
            "grade":     "F",
            "status":    "UNREACHABLE",
            "alerts":    [_alert(Severity.CRITICAL, "Device is unreachable")],
            "breakdown": {k: 0 for k in HEALTH_WEIGHTS},
        }

    # Reachability score
    breakdown["reachable"] = HEALTH_WEIGHTS["reachable"]

    # Interfaces
    s, a = check_interfaces(device_data.get("interfaces", []))
    breakdown["interfaces_healthy"] = s
    alerts.extend(a)

    # OSPF (skip penalty for devices that are switches and have no OSPF config)
    s, a = check_ospf(device_data.get("ospf_neighbors", []))
    breakdown["ospf_neighbors"] = s
    alerts.extend(a)

    # CPU
    s, a = check_cpu(device_data.get("cpu", {}))
    breakdown["cpu_ok"] = s
    alerts.extend(a)

    # Memory
    s, a = check_memory(device_data.get("memory", {}))
    breakdown["memory_ok"] = s
    alerts.extend(a)

    # VLANs
    s, a = check_vlans(device_data.get("vlans", []))
    breakdown["vlans_present"] = s
    alerts.extend(a)

    # Routing
    s, a = check_routing(device_data.get("routing", {}))
    breakdown["routing_ok"] = s
    alerts.extend(a)

    total = sum(breakdown.values())

    if total >= 90:
        grade, status = "A", "HEALTHY"
    elif total >= 75:
        grade, status = "B", "GOOD"
    elif total >= 60:
        grade, status = "C", "DEGRADED"
    elif total >= 40:
        grade, status = "D", "DEGRADED"
    else:
        grade, status = "F", "CRITICAL"

    return {
        "score":     total,
        "grade":     grade,
        "status":    status,
        "alerts":    alerts,
        "breakdown": breakdown,
    }
