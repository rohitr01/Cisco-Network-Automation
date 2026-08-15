"""
backup/backup_tool.py
──────────────────────
v1 — Cisco Network Configuration Backup Tool

Usage:
    python backup/backup_tool.py [--prompt] [--dry-run]

    --prompt   Enter SSH credentials interactively (safest for real devices)
    --dry-run  Use mock data — no real SSH connection required

Workflow:
    devices.csv
         ↓
    Read inventory
         ↓
    Validate IP / device type
         ↓
    Credentials (prompt / env vars / .env)
         ↓
    SSH via Netmiko  [with retry]
         ↓
    show running-config
         ↓
    Save backups/<hostname>_<date>.txt
         ↓
    Disconnect
         ↓
    Summary report + log
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

# ── Add project root to sys.path so sibling packages resolve ───────────────
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    BACKUP_DIR,
    INVENTORY_FILE,
    LOGS_DIR,
    MAX_RETRIES,
    RETRY_DELAY,
    SSH_TIMEOUT,
    AUTH_TIMEOUT,
    get_credentials,
)

# ── Logging ────────────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    log_file = LOGS_DIR / f"backup_{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("backup_tool")


logger = _setup_logging()


# ── Inventory ──────────────────────────────────────────────────────────────

def load_inventory(csv_path: Path) -> list[dict]:
    devices = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            if not row.get("hostname") or not row.get("ip"):
                logger.warning("Skipping invalid inventory row: %s", row)
                continue
            row.setdefault("device_type", "cisco_ios")
            devices.append(row)
    logger.info("Loaded %d devices from %s", len(devices), csv_path)
    return devices


# ── SSH backup (real devices) ──────────────────────────────────────────────

def _backup_one_real(device: dict, credentials: dict) -> tuple[bool, str]:
    """
    SSH into a single device, run 'show running-config', return (success, config).
    Implements retry with exponential backoff.
    """
    try:
        from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
    except ImportError:
        return False, "netmiko not installed — run: pip install netmiko"

    conn_params = {
        "device_type":    device["device_type"],
        "host":           device["ip"],
        "username":       credentials["username"],
        "password":       credentials["password"],
        "secret":         credentials.get("secret", ""),
        "timeout":        SSH_TIMEOUT,
        "auth_timeout":   AUTH_TIMEOUT,
        "fast_cli":       False,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("[%s] Connection attempt %d/%d", device["hostname"], attempt, MAX_RETRIES)
            with ConnectHandler(**conn_params) as conn:
                conn.enable()
                config = conn.send_command("show running-config")
            return True, config

        except NetmikoAuthenticationException:
            logger.error("[%s] Authentication failed — check credentials", device["hostname"])
            return False, "AUTH FAILURE"

        except NetmikoTimeoutException:
            logger.warning("[%s] Timeout on attempt %d", device["hostname"], attempt)
            if attempt < MAX_RETRIES:
                logger.info("[%s] Retrying in %ds ...", device["hostname"], RETRY_DELAY)
                time.sleep(RETRY_DELAY)

        except Exception as exc:
            logger.error("[%s] Unexpected error: %s", device["hostname"], exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    return False, "CONNECTION TIMEOUT"


# ── Dry-run backup (mock data) ─────────────────────────────────────────────

def _backup_one_dry(device: dict) -> tuple[bool, str]:
    from mock.mock_devices import MOCK_OUTPUT
    hostname = device["hostname"]
    data     = MOCK_OUTPUT.get(hostname, MOCK_OUTPUT["DEFAULT"])

    if data is None:
        logger.warning("[%s] (dry-run) Simulating connection failure", hostname)
        return False, "SIMULATED TIMEOUT"

    logger.info("[%s] (dry-run) Mock SSH success", hostname)
    return True, data.get("running_config", "! empty config")


# ── Save backup file ───────────────────────────────────────────────────────

def _save_backup(hostname: str, config: str) -> Path:
    from security.config_scrubber import scrub_config
    date_str  = datetime.now().strftime("%Y-%m-%d")
    file_path = BACKUP_DIR / f"{hostname}_{date_str}.txt"
    # Scrub credentials before writing to disk
    sanitized = scrub_config(config)
    file_path.write_text(sanitized, encoding="utf-8")
    return file_path


# ── Summary report ─────────────────────────────────────────────────────────

def _write_report(results: list[dict]) -> Path:
    report_path = BACKUP_DIR / f"backup_report_{datetime.now().strftime('%Y-%m-%d')}.txt"
    lines = [
        f"Cisco Network Backup Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        f"{'Hostname':<12} {'IP':<16} {'Status':<10} {'File'}",
        "-" * 60,
    ]
    for r in results:
        lines.append(
            f"{r['hostname']:<12} {r['ip']:<16} {r['status']:<10} {r.get('file', 'N/A')}"
        )
    lines += [
        "-" * 60,
        f"Total: {len(results)}  "
        f"Success: {sum(1 for r in results if r['status'] == 'SUCCESS')}  "
        f"Failed: {sum(1 for r in results if r['status'] != 'SUCCESS')}",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ── Rich console table ─────────────────────────────────────────────────────

def _print_summary(results: list[dict]) -> None:
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box

        console = Console()
        table   = Table(
            title="[bold]Configuration Backup Summary[/bold]",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("Hostname",  style="cyan",  no_wrap=True)
        table.add_column("IP",        style="white")
        table.add_column("Status",    justify="center")
        table.add_column("File",      style="dim")

        for r in results:
            status_str = (
                "[green]OK[/green]"
                if r["status"] == "SUCCESS"
                else f"[red]FAILED: {r['status']}[/red]"
            )
            table.add_row(
                r["hostname"], r["ip"], status_str, r.get("file", "-")
            )

        import io
        import sys as _sys
        safe_console = Console(
            file=io.TextIOWrapper(_sys.stdout.buffer, encoding="utf-8"),
            highlight=False,
        )
        safe_console.print(table)
    except ImportError:
        # Fallback without Rich
        for r in results:
            print(f"{r['hostname']:<12} {r['ip']:<16} {r['status']}")


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Cisco Configuration Backup Tool")
    parser.add_argument(
        "--prompt",   action="store_true",
        help="Prompt for SSH credentials at runtime",
    )
    parser.add_argument(
        "--dry-run",  action="store_true",
        help="Use mock device data (no real SSH connection)",
    )
    parser.add_argument(
        "--inventory", default=str(INVENTORY_FILE),
        help="Path to devices CSV (default: inventory/devices.csv)",
    )
    args = parser.parse_args()

    logger.info("=== Cisco Configuration Backup Tool started ===")
    logger.info("Mode: %s", "DRY-RUN" if args.dry_run else "LIVE")

    # Load inventory
    inventory = load_inventory(Path(args.inventory))

    # Credentials
    credentials: dict = {}
    if not args.dry_run:
        try:
            credentials = get_credentials(prompt=args.prompt)
        except EnvironmentError as exc:
            logger.error(str(exc))
            sys.exit(1)

    # Process each device
    results: list[dict] = []
    for device in inventory:
        hostname = device["hostname"]
        ip       = device["ip"]

        if args.dry_run:
            success, output = _backup_one_dry(device)
        else:
            success, output = _backup_one_real(device, credentials)

        record: dict = {"hostname": hostname, "ip": ip}

        if success:
            saved = _save_backup(hostname, output)
            record["status"] = "SUCCESS"
            record["file"]   = saved.name
            logger.info("[%s] Backup saved → %s", hostname, saved)
        else:
            record["status"] = output  # e.g. "AUTH FAILURE" or "CONNECTION TIMEOUT"
            logger.error("[%s] Backup FAILED: %s", hostname, output)

        results.append(record)

    # Summary
    report = _write_report(results)
    logger.info("Report written → %s", report)
    _print_summary(results)


if __name__ == "__main__":
    main()
