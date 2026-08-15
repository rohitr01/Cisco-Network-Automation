"""
core/credentials.py
───────────────────
Credential loading logic extracted from settings.py.
"""

import os
import getpass
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_credentials(prompt: bool = False) -> dict:
    """
    Return SSH credentials using the safest available source.

    Priority:
      1. Runtime prompt  (prompt=True)
      2. Environment variables
      3. .env file
      
    Never falls back to hardcoded values.
    """
    if prompt:
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
