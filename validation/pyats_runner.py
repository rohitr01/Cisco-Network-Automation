#!/usr/bin/env python3
"""pyATS/Genie validation runner.

Runs network validation tests against a pyATS testbed.
Tests check connectivity, interfaces, VLANs, routing, and OSPF state.

Usage:
    python validation/pyats_runner.py [--testbed testbed.yaml]
    python main.py --validate [--testbed testbed.yaml]
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path

def run_validation(testbed_path: str) -> None:
    """Run all validation tests against the given testbed."""
    try:
        from genie.testbed import load as load_testbed
    except ImportError:
        print("\n  ERROR: pyATS/Genie is not installed.")
        print("  Install with: pip install -r requirements-pyats.txt")
        print("  Requires Linux or WSL. See validation/README.md\n")
        sys.exit(1)

    print("\nCisco Network Validation")
    print("-" * 40)
    print(f"Testbed: {testbed_path}")
    print()

    testbed = load_testbed(testbed_path)
    results = {}
    all_passed = True

    # Test 1: Connectivity
    print("Connectivity       ", end="", flush=True)
    connectivity_ok = True
    for device_name, device in testbed.devices.items():
        try:
            device.connect(log_stdout=False)
            device.disconnect()
        except Exception as e:
            connectivity_ok = False
            results[f"connectivity_{device_name}"] = str(e)
    if connectivity_ok:
        print("PASS")
    else:
        print("FAIL")
        all_passed = False
        for k, v in results.items():
            if k.startswith("connectivity_"):
                print(f"  {k}: {v}")

    # Test 2: Interfaces
    print("Interfaces         ", end="", flush=True)
    intf_ok = True
    for device_name, device in testbed.devices.items():
        try:
            device.connect(log_stdout=False)
            output = device.parse('show ip interface brief')
            for intf_name, intf_data in output.get('interface', {}).items():
                status = intf_data.get('status', 'unknown')
                if status == 'down' and 'administratively' not in str(intf_data.get('status', '')):
                    intf_ok = False
                    results[f"interface_{device_name}_{intf_name}"] = f"operationally down"
            device.disconnect()
        except Exception as e:
            intf_ok = False
            results[f"interface_{device_name}"] = str(e)
    if intf_ok:
        print("PASS")
    else:
        print("FAIL")
        all_passed = False
        for k, v in results.items():
            if k.startswith("interface_"):
                print(f"  {k}: {v}")

    # Test 3: VLANs (switches only)
    print("VLANs              ", end="", flush=True)
    vlan_ok = True
    for device_name, device in testbed.devices.items():
        if device.type != 'switch':
            continue
        try:
            device.connect(log_stdout=False)
            output = device.parse('show vlan brief')
            if not output.get('vlans'):
                vlan_ok = False
                results[f"vlan_{device_name}"] = "No VLANs found"
            device.disconnect()
        except Exception as e:
            vlan_ok = False
            results[f"vlan_{device_name}"] = str(e)
    if vlan_ok:
        print("PASS")
    else:
        print("FAIL")
        all_passed = False
        for k, v in results.items():
            if k.startswith("vlan_"):
                print(f"  {k}: {v}")

    # Test 4: Routing
    print("Routing            ", end="", flush=True)
    routing_ok = True
    for device_name, device in testbed.devices.items():
        try:
            device.connect(log_stdout=False)
            output = device.parse('show ip route')
            routes = output.get('vrf', {}).get('default', {}).get('address_family', {}).get('ipv4', {}).get('routes', {})
            if not routes:
                routing_ok = False
                results[f"routing_{device_name}"] = "Routing table is empty"
            device.disconnect()
        except Exception as e:
            routing_ok = False
            results[f"routing_{device_name}"] = str(e)
    if routing_ok:
        print("PASS")
    else:
        print("FAIL")
        all_passed = False
        for k, v in results.items():
            if k.startswith("routing_"):
                print(f"  {k}: {v}")

    # Test 5: OSPF
    print("OSPF               ", end="", flush=True)
    ospf_ok = True
    ospf_tested = False
    for device_name, device in testbed.devices.items():
        if device.type == 'switch':
            continue  # Skip switches without OSPF
        try:
            device.connect(log_stdout=False)
            output = device.parse('show ip ospf neighbor')
            neighbors = []
            for intf_data in output.get('interfaces', {}).values():
                neighbors.extend(intf_data.get('neighbors', {}).keys())
            if not neighbors:
                ospf_ok = False
                results[f"ospf_{device_name}"] = "No OSPF neighbors"
            else:
                ospf_tested = True
                for intf_name, intf_data in output.get('interfaces', {}).items():
                    for nbr_id, nbr_info in intf_data.get('neighbors', {}).items():
                        state = nbr_info.get('state', '').upper()
                        primary = state.split('/')[0] if '/' in state else state
                        if primary not in ('FULL', '2WAY'):
                            ospf_ok = False
                            results[f"ospf_{device_name}_{nbr_id}"] = (
                                f"State: {state} (expected FULL or 2WAY)"
                            )
            device.disconnect()
        except Exception as e:
            if 'Invalid input' not in str(e):
                ospf_ok = False
                results[f"ospf_{device_name}"] = str(e)
    if not ospf_tested:
        print("SKIP (no OSPF devices)")
    elif ospf_ok:
        print("PASS")
    else:
        print("FAIL")
        all_passed = False
        for k, v in results.items():
            if k.startswith("ospf_"):
                print(f"  {k}: {v}")

    # Summary
    print()
    if all_passed:
        print("Overall: PASS")
    else:
        print("Overall: FAIL")
        print("\nFailed checks:")
        for k, v in results.items():
            print(f"  {k}: {v}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="pyATS Network Validation")
    parser.add_argument(
        "--testbed", default=str(Path(__file__).parent / "testbed.yaml"),
        help="Path to pyATS testbed YAML",
    )
    args = parser.parse_args()
    run_validation(args.testbed)
