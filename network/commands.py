"""
network/commands.py
───────────────────
Central registry of device commands.
"""

# IOS/IOS-XE commands keyed by platform
COMMANDS: dict[str, dict[str, str]] = {
    "cisco_ios": {
        "running_config":  "show running-config",
        "version":         "show version",
        "interfaces":      "show ip interface brief",
        "vlans":           "show vlan brief",
        "mac_table":       "show mac address-table",
        "routing":         "show ip route",
        "ospf_neighbors":  "show ip ospf neighbor",
        "cpu":             "show processes cpu sorted",
        "memory":          "show processes memory sorted",
    }
}

def get_commands(device_type: str = "cisco_ios") -> dict[str, str]:
    """
    Retrieve the set of commands for a specific device type.
    
    Args:
        device_type (str): The platform type (e.g. 'cisco_ios').
        
    Returns:
        dict[str, str]: A dictionary of command names and their CLI strings.
    """
    return COMMANDS.get(device_type, COMMANDS["cisco_ios"])
