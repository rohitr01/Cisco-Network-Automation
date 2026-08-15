"""
collector/info_collector.py
────────────────────────────
v2 — Network Information Collector

Usage:
    python collector/info_collector.py [--prompt] [--dry-run]

Workflow:
    devices.csv
         ↓
    SSH / mock
         ↓
    Run 10 commands
         ↓
    Parse each output (via parsers.py)
         ↓
    Analyse health (via health_check.py)
         ↓
    Save data/<hostname>.json
         ↓
    Trigger report_generator → network_report.html
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from network.commands import COMMANDS
from config.settings import (
    DATA_DIR,
    INVENTORY_FILE,
    LOGS_DIR,
    MAX_RETRIES,
    RETRY_DELAY,
    SSH_TIMEOUT,
    AUTH_TIMEOUT,
    get_credentials,
)
from collector.parsers import (
    parse_cpu,
    parse_hostname,
    parse_interfaces,
    parse_mac_table,
    parse_memory,
    parse_ospf_neighbors,
    parse_routing,
    parse_version,
    parse_vlans,
    count_interface_status,
)
from analysis.health_check import compute_health


# ── Logging ────────────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    log_file = LOGS_DIR / f"collector_{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("info_collector")


logger = _setup_logging()


# ── Inventory ──────────────────────────────────────────────────────────────

def load_inventory(csv_path: Path) -> list[dict]:
    devices = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            row.setdefault("device_type", "cisco_ios")
            devices.append(row)
    logger.info("Loaded %d devices from inventory", len(devices))
    return devices


# ── SSH collection (real devices) ─────────────────────────────────────────

def _collect_real(device: dict, credentials: dict) -> dict | None:
    """
    SSH into device, run all commands, return {command_name: raw_output}.
    Returns None on connection failure after all retries.
    """
    try:
        from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
    except ImportError:
        logger.error("netmiko not installed — run: pip install netmiko")
        return None

    device_type = device.get("device_type", "cisco_ios")
    commands    = COMMANDS.get(device_type, COMMANDS["cisco_ios"])

    conn_params = {
        "device_type":  device_type,
        "host":         device["ip"],
        "username":     credentials["username"],
        "password":     credentials["password"],
        "secret":       credentials.get("secret", ""),
        "timeout":      SSH_TIMEOUT,
        "auth_timeout": AUTH_TIMEOUT,
        "fast_cli":     False,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("[%s] SSH attempt %d/%d", device["hostname"], attempt, MAX_RETRIES)
            raw_outputs: dict[str, str] = {}
            with ConnectHandler(**conn_params) as conn:
                conn.enable()
                for cmd_name, cmd_str in commands.items():
                    logger.info("[%s] Running: %s", device["hostname"], cmd_str)
                    raw_outputs[cmd_name] = conn.send_command(cmd_str)
            return raw_outputs

        except NetmikoAuthenticationException:
            logger.error("[%s] Authentication failed", device["hostname"])
            return None

        except NetmikoTimeoutException:
            logger.warning("[%s] Timeout on attempt %d", device["hostname"], attempt)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        except Exception as exc:
            logger.error("[%s] Error: %s", device["hostname"], exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    logger.error("[%s] All %d attempts failed", device["hostname"], MAX_RETRIES)
    return None


# ── Dry-run collection (mock data) ─────────────────────────────────────────

def _collect_dry(device: dict) -> dict | None:
    from mock.mock_devices import MOCK_OUTPUT
    hostname = device["hostname"]
    data     = MOCK_OUTPUT.get(hostname, MOCK_OUTPUT["DEFAULT"])
    if data is None:
        logger.warning("[%s] (dry-run) Simulating connection failure", hostname)
        return None
    logger.info("[%s] (dry-run) Using mock data", hostname)
    return data


# ── Parse + normalise ──────────────────────────────────────────────────────

def _parse_all(hostname: str, raw: dict) -> dict:
    """Convert raw CLI strings into structured data."""
    interfaces = parse_interfaces(raw.get("interfaces", ""))
    return {
        "hostname_config": parse_hostname(raw.get("running_config", "")),
        "version":         parse_version(raw.get("version", "")),
        "interfaces":      interfaces,
        "interface_stats": count_interface_status(interfaces),
        "vlans":           parse_vlans(raw.get("vlans", "")),
        "mac_table":       parse_mac_table(raw.get("mac_table", "")),
        "routing":         parse_routing(raw.get("routing", "")),
        "ospf_neighbors":  parse_ospf_neighbors(raw.get("ospf_neighbors", "")),
        "cpu":             parse_cpu(raw.get("cpu", "")),
        "memory":          parse_memory(raw.get("memory", "")),
    }


# ── Collect one device ─────────────────────────────────────────────────────

def collect_device(device: dict, credentials: dict, dry_run: bool) -> dict:
    hostname = device["hostname"]
    ip       = device["ip"]

    # Collect raw output
    raw = _collect_dry(device) if dry_run else _collect_real(device, credentials)

    if raw is None:
        unreachable_data = {
            "hostname":     hostname,
            "ip":           ip,
            "reachable":    False,
            "collected_at": datetime.now().isoformat(),
        }
        unreachable_data["health"] = compute_health(unreachable_data)
        return unreachable_data

    # Parse
    parsed = _parse_all(hostname, raw)

    device_data = {
        "hostname":     hostname,
        "ip":           ip,
        "reachable":    True,
        "collected_at": datetime.now().isoformat(),
        **parsed,
    }

    # Health analysis
    device_data["health"] = compute_health(device_data)

    return device_data


# ── Save JSON ──────────────────────────────────────────────────────────────

def save_device_json(device_data: dict) -> Path:
    path = DATA_DIR / f"{device_data['hostname']}.json"
    path.write_text(json.dumps(device_data, indent=2), encoding="utf-8")
    return path


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Cisco Network Information Collector")
    parser.add_argument("--prompt",    action="store_true", help="Prompt for SSH credentials")
    parser.add_argument("--dry-run",   action="store_true", help="Use mock device data")
    parser.add_argument("--no-report", action="store_true", help="Skip HTML report generation")
    parser.add_argument(
        "--inventory", default=str(INVENTORY_FILE),
        help="Path to devices CSV",
    )
    args = parser.parse_args()

    logger.info("=== Cisco Network Information Collector started ===")
    logger.info("Mode: %s", "DRY-RUN" if args.dry_run else "LIVE")

    inventory   = load_inventory(Path(args.inventory))
    credentials: dict = {}

    if not args.dry_run:
        try:
            credentials = get_credentials(prompt=args.prompt)
        except EnvironmentError as exc:
            logger.error(str(exc))
            sys.exit(1)

    all_data: list[dict] = []

    for device in inventory:
        logger.info("─── Collecting: %s (%s) ───", device["hostname"], device["ip"])
        data = collect_device(device, credentials, dry_run=args.dry_run)
        saved = save_device_json(data)
        logger.info("[%s] Data saved → %s", device["hostname"], saved)
        all_data.append(data)

    logger.info("Collection complete. %d devices processed.", len(all_data))

    # Generate HTML report
    if not args.no_report:
        try:
            from reports.report_generator import generate_report
            report_path = generate_report(all_data)
            logger.info("HTML report generated -> %s", report_path)
            print(f"\n[OK] Report ready: {report_path}")
        except Exception as exc:
            logger.error("Report generation failed: %s", exc)


if __name__ == "__main__":
    main()
