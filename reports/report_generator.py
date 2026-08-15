"""
reports/report_generator.py
────────────────────────────
Render network_report.html from collected device data.

Input:  list of device dicts (from info_collector or loaded from data/ JSON files)
Output: reports_output/network_report.html
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DATA_DIR, REPORTS_DIR, TEMPLATES_DIR


def load_all_json() -> list[dict]:
    """Load all device JSON files from data/ directory."""
    devices = []
    for json_file in sorted(DATA_DIR.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            devices.append(data)
        except (json.JSONDecodeError, IOError) as exc:
            print(f"Warning: could not read {json_file}: {exc}")
    return devices


def generate_report(devices: list[dict] | None = None) -> Path:
    """
    Render the Jinja2 HTML template and write network_report.html.

    Args:
        devices: pre-loaded device list, or None to load from data/ directory.

    Returns:
        Path to the generated HTML file.
    """
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
    except ImportError:
        raise ImportError("Jinja2 not installed — run: pip install jinja2")

    if devices is None:
        devices = load_all_json()

    if not devices:
        raise ValueError("No device data found. Run info_collector.py first.")

    # ── Summary statistics ─────────────────────────────────────────────────
    total     = len(devices)
    online    = sum(1 for d in devices if d.get("reachable"))
    offline   = total - online
    avg_score = (
        round(
            sum(d.get("health", {}).get("score", 0) for d in devices) / total, 1
        )
        if total else 0
    )
    critical_alerts = sum(
        1
        for d in devices
        for a in d.get("health", {}).get("alerts", [])
        if a.get("severity") == "critical"
    )

    context = {
        "generated_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "devices":        devices,
        "total":          total,
        "online":         online,
        "offline":        offline,
        "avg_score":      avg_score,
        "critical_alerts": critical_alerts,
    }

    # ── Render ─────────────────────────────────────────────────────────────
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template    = env.get_template("report.html.j2")
    html_output = template.render(**context)

    output_path = REPORTS_DIR / "network_report.html"
    output_path.write_text(html_output, encoding="utf-8")
    return output_path


# ── CLI entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    path = generate_report()
    print(f"✅  Report written to: {path}")
