# Cisco Network Automation — Validation Review

## Command Correctness

All commands in `network/commands.py` are standard Cisco IOS/IOS-XE commands:
- `show version` — works on all IOS/IOS-XE platforms
- `show ip interface brief` — works on all platforms
- `show interfaces` — works on all platforms
- `show vlan brief` — switch-only; returns error on routers (handled gracefully)
- `show mac address-table` — switch-only; handled gracefully
- `show ip route` — works on all Layer 3 devices
- `show ip ospf neighbor` — works where OSPF is configured
- `show processes cpu sorted` — works on all IOS/IOS-XE
- `show processes memory sorted` — works on all IOS/IOS-XE
- `show running-config` — works on all platforms (requires privilege 15)

## Netmiko Usage

- `device_type: cisco_ios` covers both classic IOS and IOS-XE
- Netmiko handles `terminal length 0` automatically
- SSH timeout (30s) and auth timeout (20s) are reasonable
- 3 retries with 5s delay is professional practice
- Auth failures do NOT retry (correct — wrong password won't become right)

## Parser Accuracy

- OSPF routes: Fixed to match O, O IA, O E1, O E2, O*E2, O N1, O N2
- Interface protocol: Fixed to handle `up (spoofing)` on Loopbacks
- CPU regex: Handles whitespace variants between number and % sign
- Memory parser: Handles zero-division edge case

## Platform Compatibility

| Platform | Supported | Notes |
|---|---|---|
| Cisco IOS 15.x | Yes | Full support |
| Cisco IOS-XE 16.x/17.x | Yes | Full support |
| Cisco NX-OS (Nexus) | No | Different output format, requires cisco_nxos |
| Cisco IOS-XR | No | Different format, requires cisco_xr |
| Cisco ASA | No | Different format, requires cisco_asa |
| Packet Tracer | No | Does not support Netmiko SSH automation |

## Minimum Test Environment

- Cisco Modeling Labs (CML) with vIOS or CSR1000v
- GNS3 with dynamips or IOU images
- EVE-NG with vIOS/CSR1000v images
- Real hardware (ISR 4000, Catalyst 2960/9200/9300)
