#!/usr/bin/env python3
"""
main.py — Unified CLI for Cisco Network Automation Toolkit
═══════════════════════════════════════════════════════════

Usage:
    python main.py --help
    python main.py --demo              # Demo mode (mock data, no Cisco required)
    python main.py --demo --backup     # Demo backup with mock data
    python main.py --collect           # Real device collection via SSH
    python main.py --backup            # Real device config backup via SSH
    python main.py --validate          # pyATS/Genie validation (requires testbed)
    python main.py --report            # Re-generate HTML report from existing data/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── Project root on sys.path ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import DATA_DIR, REPORTS_DIR


# ── CLI argument parsing ──────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cisco-net-auto",
        description="Cisco Network Automation Toolkit — Collect, Backup, Analyse, Validate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python main.py --demo                  Run with mock data (no Cisco hardware)
  python main.py --demo --backup         Backup using mock data
  python main.py --collect --prompt      Collect from real devices, prompt for creds
  python main.py --backup --prompt       Backup real devices, prompt for creds
  python main.py --validate              Run pyATS validation against testbed
  python main.py --report                Re-generate HTML report from data/ files
""",
    )

    mode = parser.add_argument_group("Mode")
    mode.add_argument(
        "--demo", action="store_true",
        help="Demo mode: use mock device data (no real Cisco hardware required)",
    )
    mode.add_argument(
        "--collect", action="store_true",
        help="Collect device information via SSH (real mode)",
    )
    mode.add_argument(
        "--backup", action="store_true",
        help="Backup running-config from devices",
    )
    mode.add_argument(
        "--validate", action="store_true",
        help="Run pyATS/Genie validation against a testbed",
    )
    mode.add_argument(
        "--report", action="store_true",
        help="Re-generate HTML report from existing data/ JSON files",
    )

    opts = parser.add_argument_group("Options")
    opts.add_argument(
        "--prompt", action="store_true",
        help="Prompt for SSH credentials interactively",
    )
    opts.add_argument(
        "--inventory", default=None,
        help="Path to devices CSV (default: inventory/devices.csv)",
    )
    opts.add_argument(
        "--testbed", default=None,
        help="Path to pyATS testbed YAML (for --validate)",
    )

    return parser


# ── Mode handlers ──────────────────────────────────────────────────────────

def run_demo(args: argparse.Namespace) -> None:
    """Run the full collect + parse + health + report pipeline using mock data."""
    from core.inventory import load_inventory
    from core.logger import setup_logging
    from collector.info_collector import collect_device, save_device_json

    logger = setup_logging("demo")
    logger.info("=== DEMO MODE — Using mock device data ===")

    csv_path = Path(args.inventory) if args.inventory else None
    inventory = load_inventory(csv_path)

    all_data: list[dict] = []
    for device in inventory:
        logger.info("--- Collecting: %s (%s) ---", device["hostname"], device["ip"])
        data = collect_device(device, credentials={}, dry_run=True)
        save_device_json(data)
        all_data.append(data)

    logger.info("Collection complete. %d devices processed.", len(all_data))

    # Generate HTML report
    _generate_report(all_data, logger)

    # Show health summary
    _show_health_summary(all_data)


def run_collect(args: argparse.Namespace) -> None:
    """Collect device information from real Cisco devices via SSH."""
    from core.inventory import load_inventory
    from core.credentials import load_credentials
    from core.logger import setup_logging
    from collector.info_collector import collect_device, save_device_json

    logger = setup_logging("collector")
    logger.info("=== REAL MODE — Collecting from live devices ===")

    csv_path = Path(args.inventory) if args.inventory else None
    inventory = load_inventory(csv_path)

    try:
        credentials = load_credentials(prompt=args.prompt)
    except EnvironmentError as exc:
        logger.error(str(exc))
        sys.exit(1)

    all_data: list[dict] = []
    for device in inventory:
        logger.info("--- Collecting: %s (%s) ---", device["hostname"], device["ip"])
        data = collect_device(device, credentials, dry_run=False)
        save_device_json(data)
        all_data.append(data)

    logger.info("Collection complete. %d devices processed.", len(all_data))
    _generate_report(all_data, logger)
    _show_health_summary(all_data)


def run_backup(args: argparse.Namespace, demo: bool = False) -> None:
    """Run configuration backup (demo or real mode)."""
    from backup.backup_tool import main as backup_main

    # Build argv for the backup tool's own argparse
    backup_argv = []
    if demo:
        backup_argv.append("--dry-run")
    if args.prompt:
        backup_argv.append("--prompt")
    if args.inventory:
        backup_argv.extend(["--inventory", args.inventory])

    # Temporarily replace sys.argv for the backup tool
    original_argv = sys.argv
    sys.argv = ["backup_tool"] + backup_argv
    try:
        backup_main()
    finally:
        sys.argv = original_argv


def run_validate(args: argparse.Namespace) -> None:
    """Run pyATS/Genie validation against a testbed."""
    try:
        from validation.pyats_runner import run_validation
    except ImportError:
        print(
            "\n"
            "  pyATS/Genie is not installed.\n"
            "\n"
            "  To install (Linux/WSL recommended):\n"
            "    pip install -r requirements-pyats.txt\n"
            "\n"
            "  Note: pyATS requires Python 3.9-3.12 on Linux.\n"
            "  On Windows, use WSL (Windows Subsystem for Linux).\n"
            "\n"
            "  For more details, see: validation/README.md\n",
        )
        sys.exit(1)

    testbed_path = args.testbed
    if testbed_path is None:
        testbed_path = str(Path(__file__).parent / "validation" / "testbed.yaml")

    if not Path(testbed_path).exists():
        print(
            f"\n  Testbed file not found: {testbed_path}\n"
            f"\n  Copy the example and edit:\n"
            f"    cp validation/testbed.yaml.example validation/testbed.yaml\n"
            f"\n  See validation/README.md for setup instructions.\n"
        )
        sys.exit(1)

    run_validation(testbed_path)


def run_report_only(args: argparse.Namespace) -> None:
    """Re-generate HTML report from existing data/ JSON files."""
    from core.logger import setup_logging

    logger = setup_logging("report")

    # Load all JSON files from data/
    json_files = sorted(DATA_DIR.glob("*.json"))
    if not json_files:
        print(f"\n  No data files found in {DATA_DIR}/")
        print("  Run --demo or --collect first to generate device data.\n")
        sys.exit(1)

    all_data = []
    for jf in json_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        all_data.append(data)

    logger.info("Loaded %d device data files from %s", len(all_data), DATA_DIR)
    _generate_report(all_data, logger)
    _show_health_summary(all_data)


# ── Shared helpers ─────────────────────────────────────────────────────────

def _generate_report(all_data: list[dict], logger) -> None:
    """Generate HTML report from collected device data."""
    try:
        from reports.report_generator import generate_report
        report_path = generate_report(all_data)
        logger.info("HTML report generated -> %s", report_path)
        print(f"\n[OK] Report ready: {report_path}")
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)


def _show_health_summary(all_data: list[dict]) -> None:
    """Print a compact health score summary to the console."""
    print()
    print("=" * 70)
    print("  NETWORK HEALTH SCORE SUMMARY")
    print("=" * 70)
    print(f"{'Device':<12}{'Score':>8}  {'Grade':<6} {'Status':<14} {'Top Alert'}")
    print("-" * 70)

    for d in all_data:
        health = d.get("health", {})
        score = health.get("score", "?")
        grade = health.get("grade", "?")
        status = health.get("status", "UNKNOWN")
        alerts = health.get("alerts", [])
        top_alert = alerts[0]["message"][:40] if alerts else "-"
        print(f"{d['hostname']:<12}{score:>4}/100  {grade:<6} {status:<14} {top_alert}")

    print("-" * 70)
    print()


# ── Entrypoint ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # If no mode specified, show help
    if not any([args.demo, args.collect, args.backup, args.validate, args.report]):
        parser.print_help()
        sys.exit(0)

    # Demo mode
    if args.demo and not args.backup:
        run_demo(args)
    elif args.demo and args.backup:
        run_backup(args, demo=True)

    # Real modes
    elif args.collect:
        run_collect(args)
    elif args.backup:
        run_backup(args, demo=False)

    # Validation
    elif args.validate:
        run_validate(args)

    # Report only
    elif args.report:
        run_report_only(args)


if __name__ == "__main__":
    main()
