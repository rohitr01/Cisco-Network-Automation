# pyATS/Genie Network Validation

This module provides automated network state validation using Cisco pyATS and Genie.

## Purpose

| Tool | Purpose |
|---|---|
| `main.py --demo` | Mock data collection and health analysis |
| `main.py --collect` | Real SSH collection via Netmiko |
| **`main.py --validate`** | **Structured validation via pyATS/Genie** |

## Requirements

- **Python 3.9–3.12** (pyATS requirement)
- **Linux or WSL** (pyATS does not fully support native Windows)
- A reachable Cisco IOS/IOS-XE device

### Install

```bash
# From project root
pip install -r requirements-pyats.txt
```

### On Windows

pyATS runs best under WSL:

```bash
# In WSL
sudo apt update && sudo apt install python3-pip
pip install -r requirements-pyats.txt
```

## Setup

1. Copy the example testbed:
   ```bash
   cp validation/testbed.yaml.example validation/testbed.yaml
   ```

2. Edit `testbed.yaml` with your device IPs and credentials.

3. **Option A**: Set environment variables:
   ```bash
   export PYATS_USERNAME=admin
   export PYATS_PASSWORD=cisco123
   ```

4. **Option B**: Edit credentials directly in testbed.yaml (lab only).

## Inventory Formats

| Format | Tool | Purpose |
|---|---|---|
| `inventory/devices.csv` | Netmiko (Python SSH) | Application inventory for --collect and --backup |
| `validation/testbed.yaml` | pyATS/Genie (Unicon) | Validation testbed for --validate |

These are intentionally separate. The CSV serves the Python application; the YAML serves pyATS.

## Validation Tests

| Test | What it checks |
|---|---|
| Connectivity | Can we SSH to each device? |
| Interfaces | Are expected interfaces operationally up? |
| VLANs | Do switches have configured VLANs? |
| Routing | Is the routing table populated? |
| OSPF | Are OSPF neighbors in FULL or 2WAY state? |

## Running

```bash
python main.py --validate
python main.py --validate --testbed path/to/testbed.yaml
```

## Expected Output

```
Cisco Network Validation
────────────────────────

Connectivity       PASS
Interfaces         PASS
VLANs              PASS
Routing            PASS
OSPF               PASS

Overall: PASS
```

## Limitations

- pyATS requires Linux or WSL (does not work natively on Windows)
- Requires real Cisco IOS/IOS-XE devices (not Packet Tracer)
- Supported environments: GNS3, EVE-NG, Cisco CML, real hardware
- REAL DEVICE TEST: NOT PERFORMED unless verified against actual equipment
