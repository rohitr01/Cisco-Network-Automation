# Failure Testing Guide

This document describes controlled failure scenarios for validating the
tool's failure detection capabilities. These tests require a dedicated
Cisco lab environment.

> **WARNING**: Only perform these tests in an isolated lab.
> NEVER run failure tests against production equipment.

## Test A: OSPF Neighbor Failure

### Procedure
1. Verify baseline: `python main.py --validate` → OSPF: PASS
2. On R2: `router ospf 1` → `shutdown`
3. Wait 40 seconds for dead timer expiry
4. Run: `python main.py --validate`

### Expected Result
```
OSPF               FAIL
  ospf_R1: Expected neighbors: 2, Actual: 1
```

### Restore
1. On R2: `router ospf 1` → `no shutdown`
2. Wait for adjacency (30-60 seconds)
3. Run: `python main.py --validate` → OSPF: PASS

---

## Test B: Interface Shutdown

### Procedure
1. Verify baseline: Interfaces: PASS
2. On R1: `interface GigabitEthernet0/1` → `shutdown`
3. Run: `python main.py --collect --prompt`

### Expected Result
```
R1 HEALTH SCORE: 95/100
  [WARNING] GigabitEthernet0/1 is down (line protocol down)
```

### Restore
1. On R1: `interface GigabitEthernet0/1` → `no shutdown`
2. Run: `python main.py --collect --prompt` → Interface: PASS

---

## Test C: VLAN Removal

### Procedure
1. Verify baseline: VLANs: PASS
2. On SW1: `no vlan 10`
3. Run: `python main.py --collect --prompt`

### Expected Result
```
SW1: VLAN 10 no longer present
```

### Restore
1. On SW1: `vlan 10` → `name DATA`
2. Verify: VLANs: PASS

---

## Test D: Device Unreachable

### Procedure
1. Verify baseline: All devices reachable
2. Disconnect R3 from network (or apply ACL blocking SSH)
3. Run: `python main.py --collect --prompt`

### Expected Result
```
R3   0/100  F  UNREACHABLE  Device is unreachable
```

### Restore
1. Reconnect R3 (or remove ACL)
2. Run: `python main.py --collect --prompt` → R3: HEALTHY

---

## Test Status

| Test | Status |
|---|---|
| Test A: OSPF failure | NOT PERFORMED |
| Test B: Interface shutdown | NOT PERFORMED |
| Test C: VLAN removal | NOT PERFORMED |
| Test D: Device unreachable | NOT PERFORMED |

> These tests require a Cisco lab environment (GNS3, CML, EVE-NG, or real hardware).
> Packet Tracer does not support the required Netmiko/SSH automation.
