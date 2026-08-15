# Cisco Network Automation Toolkit

**Automated network device management, health analysis, and validation for Cisco IOS/IOS-XE environments.**

---

## What Is This Project?

In a real network environment, a network engineer might manage **50–500+ Cisco routers and switches**. Manually SSH-ing into each device to check health, collect configs, and verify OSPF is **slow, error-prone, and doesn't scale**.

This project replaces that manual process with Python automation:

```
BEFORE (Manual)                    AFTER (Automated)
──────────────────                 ──────────────────
SSH into R1                        python main.py --demo
  show version                         ↓
  show ip interface brief          Connects to ALL devices
  show ip route                        ↓
  show ip ospf neighbor            Runs ALL commands
  show running-config                  ↓
  ... repeat for R2, R3...         Parses output
                                       ↓
Time: 30+ minutes                  Analyses health (0-100 score)
Output: Notes on paper                 ↓
                                   Generates HTML dashboard
                                       ↓
                                   Time: < 5 seconds
                                   Output: JSON + HTML report
```

---

## Why This Project Matters (For Your Resume)

| Skill Demonstrated | How |
|---|---|
| **Python automation** | Entire pipeline written in Python |
| **Cisco CLI knowledge** | Uses real IOS commands (`show version`, `show ip ospf neighbor`, etc.) |
| **Network protocols** | OSPF state analysis (FULL vs 2WAY vs INIT), routing table parsing |
| **SSH automation** | Netmiko for device connectivity with retry logic |
| **Security awareness** | Credential handling, config scrubbing, no hardcoded passwords |
| **Testing** | 151 unit + integration tests using `unittest` |
| **Clean architecture** | Separated modules: core, network, security, collector, analysis |
| **pyATS/Genie** | Industry-standard Cisco validation framework (optional) |
| **Git/GitHub** | Proper .gitignore, .env.example, documentation |

---

## How to Install

### Step 1: Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/cisco-network-automation.git
cd cisco-network-automation
```

### Step 2: Install Python dependencies

```bash
pip install -r requirements.txt
```

**What gets installed and why:**

| Package | Version | Why It's Used |
|---|---|---|
| `netmiko` | ≥ 4.3.0 | SSH connection to Cisco devices — sends commands, receives output |
| `paramiko` | ≥ 3.4.0 | Low-level SSH protocol library that Netmiko uses internally |
| `jinja2` | ≥ 3.1.0 | Template engine — generates the HTML dashboard report |
| `rich` | ≥ 13.7.0 | Pretty CLI output — coloured tables in the terminal |
| `python-dotenv` | ≥ 1.0.0 | Loads credentials from `.env` file instead of hardcoding |

### Step 3 (Optional): Install pyATS for validation

```bash
# Only works on Linux or WSL (Windows Subsystem for Linux)
pip install -r requirements-pyats.txt
```

**Why separate?** pyATS is Cisco's official test framework but only runs on Linux. The main application works fine on Windows without it.

---

## How to Run — Every Mode Explained

### Mode 1: `--demo` (Start Here)

```bash
python main.py --demo
```

**What it does:**
1. Loads 5 mock devices from `inventory/devices.csv`
2. Uses fake Cisco output from `mock/mock_devices.py` (no real hardware needed)
3. Parses all outputs through 9 parsers
4. Scores each device's health (0–100)
5. Saves structured JSON to `data/`
6. Generates HTML dashboard to `reports_output/network_report.html`
7. Prints health summary table to terminal

**Why use it:** Proves the entire pipeline works without any Cisco hardware. Recruiters and interviewers can clone the repo and see it work immediately.

**What you'll see:**
```
======================================================================
  NETWORK HEALTH SCORE SUMMARY
======================================================================
Device         Score  Grade  Status         Top Alert
----------------------------------------------------------------------
R1           100/100  A      HEALTHY        GigabitEthernet0/2 is administratively d
R2            90/100  A      HEALTHY        High CPU utilisation: 85.0% (1-min avg)
R3            80/100  B      GOOD           OSPF has no established neighbors
SW1           70/100  C      DEGRADED       OSPF has no established neighbors
SW2            0/100  F      UNREACHABLE    Device is unreachable
----------------------------------------------------------------------
```

**Output files created:**
```
data/R1.json                          ← Structured device data
data/R2.json
data/R3.json
data/SW1.json
data/SW2.json
reports_output/network_report.html    ← Open in browser
```

---

### Mode 2: `--demo --backup`

```bash
python main.py --demo --backup
```

**What it does:**
1. Loads inventory
2. Retrieves mock `show running-config` for each device
3. **Scrubs credentials** (passwords, SNMP communities, keys → `<REDACTED>`)
4. Saves cleaned configs to `backups/<hostname>_<date>.txt`
5. Generates summary report

**Why use it:** Shows you can automate config backups — a daily task in real network operations. The credential scrubbing demonstrates security awareness.

**What you'll see:**
```
┌──────────┬──────────────┬────────┬────────────────────┐
│ Hostname │ IP           │ Status │ File               │
├──────────┼──────────────┼────────┼────────────────────┤
│ R1       │ 192.168.1.1  │   OK   │ R1_2026-08-15.txt  │
│ R2       │ 192.168.1.2  │   OK   │ R2_2026-08-15.txt  │
│ SW2      │ 192.168.1.11 │ FAILED │ -                  │
└──────────┴──────────────┴────────┴────────────────────┘
```

**What scrubbing does:**
```
BEFORE (raw from device):
  enable secret 5 $1$abc$XYZPASSWORDHASH
  username admin password 0 cisco123
  snmp-server community PUBLIC RO

AFTER (saved to disk):
  enable secret 5 <REDACTED>
  username admin password 0 <REDACTED>
  snmp-server community <REDACTED> RO
```

---

### Mode 3: `--collect` (Real Devices)

```bash
python main.py --collect --prompt
```

**What it does:**
1. Loads `inventory/devices.csv`
2. Asks you for SSH username/password interactively
3. SSH-es into each real Cisco device using Netmiko
4. Runs 9 `show` commands on each device
5. Parses, analyses, saves JSON, generates report

**Why use it:** This is the **production mode**. When you have real Cisco routers in GNS3/CML/EVE-NG or real hardware, this is what you run.

**Prerequisites:**
- A reachable Cisco IOS/IOS-XE device with SSH enabled
- Valid SSH credentials
- One of: GNS3, EVE-NG, Cisco CML, or real hardware
- ⚠️ **Packet Tracer does NOT work** (doesn't support Netmiko SSH)

**Three ways to provide credentials:**

```bash
# Option 1: Interactive prompt (safest)
python main.py --collect --prompt

# Option 2: Environment variables
export NET_USERNAME=admin
export NET_PASSWORD=cisco123
export NET_SECRET=enable_secret
python main.py --collect

# Option 3: .env file
cp .env.example .env
# Edit .env with your credentials
python main.py --collect
```

---

### Mode 4: `--backup` (Real Device Backup)

```bash
python main.py --backup --prompt
```

**What it does:**
1. SSH-es into each device
2. Runs `show running-config`
3. Scrubs credentials from the config
4. Saves to `backups/<hostname>_<date>.txt`

**Why use it:** Config backup is one of the most common network automation tasks. Cisco DevNet specifically recommends automating this.

---

### Mode 5: `--validate` (pyATS/Genie)

```bash
python main.py --validate
```

**What it does:**
1. Uses Cisco's official pyATS/Genie framework (not Netmiko)
2. Connects to devices via the testbed YAML
3. Runs structured validation tests:
   - Can we reach each device? (Connectivity)
   - Are interfaces up? (Interfaces)
   - Do switches have VLANs? (VLANs)
   - Is routing populated? (Routing)
   - Are OSPF neighbors healthy? (OSPF)

**Why use it:** pyATS is the **industry standard** at Cisco for network testing. Having it in your project shows you know professional-grade tools.

**Setup:**
```bash
# 1. Install (Linux/WSL only)
pip install -r requirements-pyats.txt

# 2. Create testbed
cp validation/testbed.yaml.example validation/testbed.yaml
# Edit with your device IPs and credentials

# 3. Run
python main.py --validate
```

**Expected output:**
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

**Why separate from `--collect`?**

| Feature | `--collect` (Netmiko) | `--validate` (pyATS) |
|---|---|---|
| Purpose | Collect data + health score | Structured PASS/FAIL testing |
| Library | Netmiko (raw SSH) | pyATS/Genie (structured parsing) |
| OS support | Windows, Linux, Mac | Linux/WSL only |
| Output | JSON + HTML report | PASS/FAIL per test |
| Install | `requirements.txt` | `requirements-pyats.txt` |

---

### Mode 6: `--report`

```bash
python main.py --report
```

**What it does:** Re-generates the HTML dashboard from existing `data/*.json` files without re-collecting from devices.

**Why use it:** If you already collected data but want to regenerate the report (maybe the template changed), you don't need to SSH into devices again.

---

## How to Run Tests

```bash
python -m unittest discover tests/ -v
```

**What it does:** Runs all 151 automated tests. No Cisco hardware required.

**Why it matters:** Tests prove the code actually works. Recruiters look for tested code.

```
Ran 151 tests in 0.7s
OK
```

### What Each Test File Tests

| Test File | Tests | What It Verifies | Why It Exists |
|---|---:|---|---|
| `test_parsers.py` | 29 | All 9 parser functions parse real Cisco output correctly | Core correctness — if parsers break, everything breaks |
| `test_parsers_edge_cases.py` | 38 | OSPF route types (IA, E1, E2), interface spoofing, BGP routes, zero-division | Edge cases that would fail on real devices |
| `test_health_check.py` | 32 | Health scoring, OSPF 2WAY handling, CPU/memory thresholds | Ensures health scores are accurate |
| `test_integration.py` | 26 | Full pipeline: collect → parse → analyse → save JSON → generate HTML | End-to-end correctness |
| `test_config_scrubber.py` | 13 | All 8 credential patterns are scrubbed from configs | Security — passwords must never leak |
| `test_connection.py` | 8 | SSH success, timeout retry, auth failure, disconnect | Connection layer works without real devices |
| `test_inventory.py` | 5 | CSV loading, disabled devices, missing fields | Inventory edge cases |

---

## How the Device Inventory Works

### File: `inventory/devices.csv`

```csv
hostname,ip,device_type,role,enabled
R1,192.168.1.1,cisco_ios,router,true
R2,192.168.1.2,cisco_ios,router,true
R3,192.168.1.3,cisco_ios,router,true
SW1,192.168.1.10,cisco_ios,switch,true
SW2,192.168.1.11,cisco_ios,switch,true
```

| Column | Required | Purpose |
|---|---|---|
| `hostname` | Yes | Device name (used in filenames, reports) |
| `ip` | Yes | Management IP address |
| `device_type` | No | Netmiko device type (default: `cisco_ios`) |
| `role` | No | `router` or `switch` (informational) |
| `enabled` | No | Set to `false` to skip a device without deleting it |

**Why CSV?** Simple, human-readable, easy to edit. No complex YAML or database needed.

---

## How Health Scoring Works

Every device gets a **0–100 health score** across 7 weighted dimensions:

| Dimension | Weight | What It Checks | Example |
|---|---:|---|---|
| Reachable | 20 | Can we SSH to the device? | SW2 is down → score 0 |
| Interfaces | 20 | Are interfaces unexpectedly down? | Gi0/1 down → score reduced |
| OSPF Neighbors | 20 | Are OSPF adjacencies healthy? | Neighbor in INIT → critical |
| CPU | 10 | Is CPU below 80%? | R2 CPU at 85% → warning |
| Memory | 10 | Is memory below 80%? | Memory at 92% → critical |
| VLANs | 10 | Are VLANs active? (switches) | No VLANs → warning |
| Routing | 10 | Is routing table populated? | Empty table → warning |

### OSPF State Handling (Why This Matters)

On a Cisco broadcast network (like Ethernet), OSPF has specific roles:
- **DR** (Designated Router) — forms FULL adjacency with everyone
- **BDR** (Backup DR) — forms FULL adjacency with everyone
- **DROTHER** — forms FULL with DR/BDR, but only **2WAY** with other DROTHERs

Many automation tools incorrectly flag 2WAY as a failure. This project handles it correctly:

| State | Classification | Action |
|---|---|---|
| FULL/DR | ✅ Healthy | Full score |
| FULL/BDR | ✅ Healthy | Full score |
| 2WAY/DROTHER | ✅ Acceptable | INFO alert (not penalised) |
| INIT | ❌ Problem | CRITICAL alert, score reduced |
| DOWN | ❌ Problem | CRITICAL alert, score reduced |

---

## How Security Works

### Why Security Matters

A `show running-config` output contains passwords in plaintext:
```
enable secret 5 $1$abc$XYZPASSWORDHASH
username admin password 0 cisco123
snmp-server community PUBLIC RO
ip ospf authentication-key mypass
```

If you push these to GitHub, **anyone can see your passwords**.

### What This Project Does

1. **Config scrubbing** — `security/config_scrubber.py` replaces all credential lines with `<REDACTED>` before saving to disk
2. **No hardcoded credentials** — uses `.env` file or environment variables
3. **`.env` is gitignored** — never committed to Git
4. **`--prompt` flag** — enter credentials interactively (nothing saved)
5. **`validation/testbed.yaml` is gitignored** — pyATS credentials excluded

### Patterns Scrubbed

| Cisco Config Line | After Scrubbing |
|---|---|
| `enable secret 5 $1$hash` | `enable secret 5 <REDACTED>` |
| `username admin password 0 cisco` | `username admin password 0 <REDACTED>` |
| `snmp-server community PUBLIC RO` | `snmp-server community <REDACTED> RO` |
| `crypto isakmp key MyKey123` | `crypto isakmp key <REDACTED>` |
| `ip ospf authentication-key pass` | `ip ospf authentication-key <REDACTED>` |
| `tacacs-server key 7 abc` | `tacacs-server key 7 <REDACTED>` |
| `radius-server key secret` | `radius-server key <REDACTED>` |
| `key-string MyChainKey` | `key-string <REDACTED>` |

---

## How Each Module Works (Why It Exists)

### `core/` — Shared Utilities

**Problem:** Before this module, the backup tool and collector each had their own copy of inventory loading, logging setup, and credential loading. Changes to one didn't update the other.

**Solution:** Extract shared logic into reusable modules:

| File | What It Does | Why It Exists |
|---|---|---|
| `inventory.py` | Loads `devices.csv`, validates rows, skips disabled devices | Single source of truth for device loading |
| `credentials.py` | Loads SSH credentials from env vars, `.env`, or interactive prompt | Centralised credential management |
| `logger.py` | Sets up file + console logging with timestamps | Consistent logging across all tools |

---

### `network/` — SSH Connection Layer

**Problem:** Raw Netmiko code was duplicated in backup_tool.py and info_collector.py. Each had its own retry logic, timeout handling, and error catching.

**Solution:** A `DeviceConnector` class that wraps Netmiko:

| File | What It Does | Why It Exists |
|---|---|---|
| `connection.py` | `DeviceConnector` class with connect/execute/disconnect | One place for all SSH logic |
| `commands.py` | Dictionary of IOS commands per platform | Centralised command definitions |
| `exceptions.py` | `DeviceUnreachableError`, `DeviceAuthenticationError`, `CommandExecutionError` | Clean error handling without broad `except Exception` |

**Key design decisions:**
- **Lazy Netmiko import**: `netmiko` is only imported when `connect()` is called, so demo mode works without installing it
- **No retry on auth failure**: Wrong password won't become right — fail immediately
- **Retry on timeout**: Network issues are transient — retry up to 3 times with 5s delay
- **Context manager support**: `with DeviceConnector(...) as conn:` auto-disconnects

---

### `security/` — Config Scrubbing

| File | What It Does | Why It Exists |
|---|---|---|
| `config_scrubber.py` | Regex-based credential redaction | Prevents password leakage in backups |

---

### `validation/` — pyATS/Genie

| File | What It Does | Why It Exists |
|---|---|---|
| `pyats_runner.py` | Runs 5 structured validation tests | Industry-standard Cisco testing |
| `testbed.yaml.example` | Template for pyATS device definitions | Users copy and edit |
| `README.md` | Setup guide for pyATS | pyATS has complex setup |

---

## Data Collected — 9 Commands

| # | Command | What It Collects | Why |
|---|---|---|---|
| 1 | `show version` | IOS version, uptime, platform | Know what's running |
| 2 | `show ip interface brief` | Interface IPs and status | Find down interfaces |
| 3 | `show vlan brief` | VLAN IDs and names | Verify VLAN config (switches) |
| 4 | `show mac address-table` | MAC-to-port mappings | Track connected devices |
| 5 | `show ip route` | Routing table | Verify reachability |
| 6 | `show ip ospf neighbor` | OSPF adjacency states | Verify OSPF health |
| 7 | `show processes cpu sorted` | CPU utilisation | Detect overloaded devices |
| 8 | `show processes memory sorted` | Memory utilisation | Detect memory pressure |
| 9 | `show running-config` | Full configuration | Backup + hostname extraction |

---

## Complete CLI Reference

```bash
# ── DEMO (No Cisco hardware needed) ──────────────────────────
python main.py --demo                # Full collection + health + report
python main.py --demo --backup       # Config backup with mock data

# ── REAL DEVICES (SSH via Netmiko) ────────────────────────────
python main.py --collect             # Collect using env vars/.env
python main.py --collect --prompt    # Collect with interactive creds
python main.py --backup              # Backup using env vars/.env
python main.py --backup --prompt     # Backup with interactive creds

# ── VALIDATION (pyATS — Linux/WSL only) ──────────────────────
python main.py --validate                           # Default testbed
python main.py --validate --testbed my_testbed.yaml # Custom testbed

# ── UTILITIES ─────────────────────────────────────────────────
python main.py --report              # Re-generate HTML from existing data/
python main.py --help                # Show all options

# ── STANDALONE SCRIPTS (backward compatibility) ──────────────
python backup/backup_tool.py --dry-run
python collector/info_collector.py --dry-run
python show_health.py

# ── TESTS ─────────────────────────────────────────────────────
python -m unittest discover tests/ -v              # Run all 151 tests
python -m unittest tests/test_parsers.py -v        # Run one test file
```

---

## Architecture Diagram

```
                    ┌──────────────────────────┐
                    │       main.py             │
                    │    (Unified CLI)          │
                    │                          │
                    │  --demo  --collect       │
                    │  --backup --validate     │
                    │  --report               │
                    └──────────┬───────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌────────────┐   ┌──────────────┐   ┌──────────────┐
     │  core/     │   │  network/    │   │  security/   │
     │            │   │              │   │              │
     │ inventory  │   │ connection   │   │ config_      │
     │ credentials│   │ commands     │   │ scrubber     │
     │ logger     │   │ exceptions   │   │              │
     └─────┬──────┘   └──────┬───────┘   └──────┬───────┘
           │                 │                   │
           ▼                 ▼                   ▼
     ┌───────────────────────────────────────────────┐
     │              collector/                       │
     │                                               │
     │  info_collector.py ─→ parsers.py             │
     │       │                   │                   │
     │       ▼                   ▼                   │
     │  Raw CLI output     Structured data           │
     └───────────────────────┬───────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   analysis/    │
                    │                │
                    │ health_check   │
                    │ (0-100 score)  │
                    └────────┬───────┘
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
          ┌──────────┐ ┌──────────┐ ┌──────────────┐
          │ data/    │ │ reports/ │ │ validation/  │
          │ *.json   │ │ *.html   │ │ pyATS/Genie  │
          └──────────┘ └──────────┘ └──────────────┘
```

---

## Platform Compatibility

| Platform | Supported | Notes |
|---|---|---|
| Cisco IOS 15.x | ✅ Yes | Full support |
| Cisco IOS-XE 16.x/17.x | ✅ Yes | Full support |
| Cisco NX-OS (Nexus) | ❌ No | Different output format |
| Cisco IOS-XR | ❌ No | Different format |
| Cisco ASA | ❌ No | Different format |
| Packet Tracer | ❌ No | Does not support SSH/Netmiko |
| GNS3 | ✅ Yes | Recommended for testing |
| EVE-NG | ✅ Yes | Recommended for testing |
| Cisco CML | ✅ Yes | Recommended for testing |
| Real hardware | ✅ Yes | ISR, Catalyst, etc. |

---

## Verification Status

| What | Status | How to Reproduce |
|---|---|---|
| Demo mode | ✅ VERIFIED | `python main.py --demo` |
| Demo backup | ✅ VERIFIED | `python main.py --demo --backup` |
| 151 unit tests | ✅ VERIFIED | `python -m unittest discover tests/ -v` |
| Config scrubbing | ✅ VERIFIED | 13 scrubber tests pass |
| HTML report | ✅ VERIFIED | Open `reports_output/network_report.html` |
| Real device SSH | ⬜ NOT PERFORMED | Requires Cisco lab |
| pyATS validation | ⬜ NOT PERFORMED | Requires Linux + Cisco lab |
| Failure tests | ⬜ NOT PERFORMED | Requires Cisco lab |

> Real device and failure tests require a dedicated Cisco lab environment (GNS3, CML, EVE-NG, or hardware). Test procedures are documented in `docs/failure-testing.md`.

---

## Technologies Explained

| Technology | What It Is | Why This Project Uses It |
|---|---|---|
| **Python** | Programming language | Cisco DevNet's primary automation language |
| **Netmiko** | SSH library for network devices | Simplifies SSH to Cisco — handles prompts, `terminal length 0`, enable mode |
| **Paramiko** | Low-level SSH library | Netmiko uses it internally for the SSH protocol |
| **Jinja2** | HTML template engine | Generates the dashboard HTML from data — separates logic from presentation |
| **Rich** | CLI formatting library | Makes terminal output look professional with coloured tables |
| **python-dotenv** | Environment variable loader | Reads `.env` file for credentials — keeps secrets out of code |
| **pyATS/Genie** | Cisco test framework | Industry-standard network state validation — structured PASS/FAIL testing |
| **unittest** | Python test framework | Built-in, no extra install needed — runs all 151 tests |
| **CSV** | Inventory format | Simple, human-readable device list — no complex config files |
| **JSON** | Data storage format | Structured output for each device — easy to process programmatically |
| **HTML** | Report format | Visual dashboard — open in any browser, no install needed |
