"""
core/inventory.py
─────────────────
Shared inventory loader for cisco-network-automation.
"""

import csv
import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import INVENTORY_FILE

logger = logging.getLogger(__name__)

def load_inventory(csv_path: Path | None = None) -> list[dict]:
    """
    Load device inventory from a CSV file.
    
    Args:
        csv_path: Path to the CSV file. Defaults to INVENTORY_FILE from settings.
        
    Returns:
        List of dictionaries containing device information.
    """
    if csv_path is None:
        csv_path = INVENTORY_FILE
        
    if not csv_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {csv_path}")

    devices = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            
            enabled_str = row.get("enabled", "").lower()
            if enabled_str == "false":
                continue
                
            if "host" in row and "ip" not in row:
                row["ip"] = row.pop("host")
                
            if not row.get("hostname") or not row.get("ip"):
                logger.warning("Skipping invalid inventory row: %s", row)
                continue
                
            row.setdefault("device_type", "cisco_ios")
            row.setdefault("role", "")
            
            devices.append({
                "hostname": row["hostname"],
                "ip": row["ip"],
                "device_type": row["device_type"],
                "role": row["role"]
            })
            
    logger.info("Loaded %d devices from %s", len(devices), csv_path)
    return devices
