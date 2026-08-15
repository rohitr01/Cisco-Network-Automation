"""
config/settings.py
──────────────────
Central configuration for cisco-network-automation.

Credentials are NEVER stored here.
Load order:
  1. Environment variables (NET_USERNAME, NET_PASSWORD, NET_SECRET)
  2. .env file (via python-dotenv)
  3. Runtime prompt  (--prompt flag handled in each tool)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
INVENTORY_FILE  = BASE_DIR / "inventory" / "devices.csv"
BACKUP_DIR      = BASE_DIR / "backups"
DATA_DIR        = BASE_DIR / "data"
LOGS_DIR        = BASE_DIR / "logs"
REPORTS_DIR     = BASE_DIR / "reports_output"
TEMPLATES_DIR   = BASE_DIR / "templates"

# Create output directories if they don't exist
for _d in (BACKUP_DIR, DATA_DIR, LOGS_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Load .env (silently ignored if file doesn't exist) ────────────────────
load_dotenv(BASE_DIR / ".env")


def get_credentials(prompt: bool = False) -> dict:
    """
    Return SSH credentials using the safest available source.

    Priority:
      1. Runtime prompt  (prompt=True)
      2. Environment variables
      3. .env file (already loaded above)

    Never falls back to hardcoded values.
    """
    if prompt:
        import getpass
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")
        secret   = getpass.getpass("Enable secret (press Enter to skip): ")
    else:
        username = os.environ.get("NET_USERNAME", "")
        password = os.environ.get("NET_PASSWORD", "")
        secret   = os.environ.get("NET_SECRET", "")

    if not username or not password:
        raise EnvironmentError(
            "Credentials not found.\n"
            "Options:\n"
            "  1. Run with --prompt flag for interactive entry\n"
            "  2. Set NET_USERNAME and NET_PASSWORD environment variables\n"
            "  3. Copy .env.example → .env and fill in your credentials\n"
            "  4. Use --dry-run for a demo without real devices"
        )

    return {"username": username, "password": password, "secret": secret}


# ── SSH Settings ───────────────────────────────────────────────────────────
SSH_TIMEOUT   = 30   # seconds
AUTH_TIMEOUT  = 20   # seconds
MAX_RETRIES   = 3
RETRY_DELAY   = 5    # seconds between retries

# ── Commands per platform ──────────────────────────────────────────────────
# Commands have been moved to network/commands.py

# ── Health score weights (must sum to 100) ─────────────────────────────────
HEALTH_WEIGHTS = {
    "reachable":           20,
    "interfaces_healthy":  20,
    "ospf_neighbors":      20,
    "cpu_ok":              10,
    "memory_ok":           10,
    "vlans_present":       10,
    "routing_ok":          10,
}

# ── Alert thresholds ───────────────────────────────────────────────────────
CPU_WARNING_THRESHOLD    = 80   # percent
MEMORY_WARNING_THRESHOLD = 80   # percent
