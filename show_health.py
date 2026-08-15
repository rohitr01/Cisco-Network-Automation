"""Quick health summary viewer — shows all device scores and breakdowns."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

data_dir = pathlib.Path(__file__).parent / "data"

print("=" * 70)
print("  NETWORK HEALTH SCORE SUMMARY")
print("=" * 70)
print(f"{'Device':<10} {'Score':>6}  {'Grade':>5}  {'Status':<12}  Top Alert")
print("-" * 70)

for f in sorted(data_dir.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    h = d.get("health", {})
    alerts = h.get("alerts", [])
    alert_str = alerts[0]["message"][:40] if alerts else "--"
    score = h.get("score", 0)
    grade = h.get("grade", "?")
    status = h.get("status", "?")
    hostname = d["hostname"]
    print(f"{hostname:<10} {score:>5}/100  {grade:>5}  {status:<12}  {alert_str}")

print("-" * 70)
print()

# Detailed breakdowns
weight_map = {
    "reachable": 20,
    "interfaces_healthy": 20,
    "ospf_neighbors": 20,
    "cpu_ok": 10,
    "memory_ok": 10,
    "vlans_present": 10,
    "routing_ok": 10,
}

for hostname in ["R1", "R2", "SW1", "SW2"]:
    fpath = data_dir / f"{hostname}.json"
    if not fpath.exists():
        continue
    d = json.loads(fpath.read_text(encoding="utf-8"))
    h = d.get("health", {})
    breakdown = h.get("breakdown", {})

    label = hostname
    if hostname == "R1":
        label += " (Healthy)"
    elif hostname == "R2":
        label += " (High CPU)"
    elif hostname == "SW1":
        label += " (High Memory)"
    elif hostname == "SW2":
        label += " (Unreachable)"

    print(f"BREAKDOWN: {label}  --  Score: {h.get('score', 0)}/100  Grade: {h.get('grade', '?')}")
    for k, v in breakdown.items():
        max_w = weight_map.get(k, 10)
        filled = int(v / max_w * 20) if max_w else 0
        bar = "#" * filled + "." * (20 - filled)
        print(f"  {k:<22} [{bar}] {v:>2}/{max_w}")

    alerts = h.get("alerts", [])
    if alerts:
        print(f"  ALERTS:")
        for a in alerts:
            icon = {"critical": "CRIT", "warning": "WARN", "info": "INFO"}.get(
                a["severity"], "?"
            )
            print(f"    [{icon}] {a['message']}")
    print()
