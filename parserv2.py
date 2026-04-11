"""
Cisco Interface Configuration Parser and Command Generator
 
Parses Cisco switch running-config files to extract interface details
and generates CLI commands for common operations such as VLAN changes,
MAC sticky resets, and security mode conversions.
"""

from ciscoconfparse import CiscoConfParse

def parse_interfaces(config_file):
    parse = CiscoConfParse(config_file)
    interfaces = []

    for intf_obj in parse.find_objects(r"^interface"):
        # Start with defaults; if a field isn't found, these stand
        intf = {
            "name": intf_obj.text.split()[1],
            "description": None,
            "mode": None,
            "vlan": None,
            "security": None,
            "admin_state": "up",
        }

        # Walk through every child line once and extract what we need 
        for child in intf_obj.children:
            line = child.text.strip()

            if line.startswith("description "):
                intf["description"] = line[len("description "):]
            
            elif line.startswith("switchport mode "):
                intf["mode"] = line.split()[-1]
            
            elif line.startswith("switchport access vlan "):
                intf["vlan"] = line.split()[-1]

            elif line == "switchport port-security mac-address sticky":
                if intf["security"] == "dot1x":
                    intf["security"] = "conflict"
                else:
                    intf["security"] = "mac_sticky"

            elif line == "dot1x pae authenticator":
                if intf["security"] == "mac_sticky":
                    intf["security"] = "conflict"
                else:
                    intf["security"] = "dot1x"
            
            elif line == "shutdown":
                intf["admin_state"] = "shutdown"
            
        interfaces.append(intf)
    
    return interfaces


# --- Section 2: Display ---


SECURITY_DISPLAY = {
    "mac_sticky": "MAC Sticky Enabled",
    "dot1x": "802.1X enabled",
    "conflict": "CONFLICT - both MAC Sticky and 802.1X detected",
    None: "No port security configured",
}

def display_interface_list(interfaces):
    """Prints a numbered list of parsed interfaces."""
    print("\nDiscovered Interfaces")
    print("---------------------")
    for idx, intf in enumerate(interfaces, start=1):
        print(f" {idx}. {intf['name']}")

def display_interface_detail(intf):
    """Prints the key fields of a single parsed interface."""
    print(f"\n Interface Port : {intf['name']}")
    print(f" Description : {intf['description'] or 'N/A'}")
    print(f" Mode : {intf['mode'] or 'N/A'}")
    print(f" VLAN : {intf['vlan'] or 'N/A'}")
    print(f" Security : {SECURITY_DISPLAY.get(intf['security'], intf['security'])}")
    print(f" Admin State : {intf['admin_state']}")


# --- Section 3: Command Generation ---


def build_commands(interface_name, action_lines):
    """
    Wraps action-specific lines in the standard conf t / shutdown / end / wr skeleton.
    Returns the full command sequence as a string.
    """

    commands = [
        "conf t",
        f"interface {interface_name}",
        " shutdown",
    ]
    for line in action_lines:
        commands.append(f" {line}")
    commands.extend([
        " no shutdown",
        "end",
        "wr",
    ])
    return "\n".join(commands)

def generate_vlan_change(intf, new_vlan):
    """Changes the VLAN on an access port."""
    return build_commands(intf["name"], [
        f"switchport access vlan {new_vlan}",
    ])

def generate_mac_sticky_reset(intf):
    """Removes and re-applies MAC sticky port security."""
    return build_commands(intf["nanme"],[
        "no switchport port-security mac-address sticky",
        "no switchport port-security",
        "switchport port-security",
        "switchport port-security mac-address sticky",
    ])

def generate_mac_sticky_to_dot1x(intf):
    """Converts from MAC sticky to 802.1X."""
    return build_commands(intf["name"], [
        "no switchport port-security mac-address sticky",
        "no switchport port-security",
        "authentication port-control auto",
        "dot1x pae authenticator",
    ])

def generate_dot1x_to_mac_sticky(intf):
    """Converts from 802.1X to MAC sticky."""
    return build_commands(intf["name"], [
        "no authentication port-control auto",
        "no dot1x pae authenticator",
        "switchport port-security",
        "switchport port-security mac-address sticky",
    ])

def generate_vlan_change_with_conversion(intf, new_vlan, target_security):
    """Changes the VLAN and converts the port security in one pass."""
    action_lines = [f"switchport access vlan {new_vlan}"]

    if intf["security"] == "mac_sticky" and target_security == "dot1x":
        action_lines.extend([
            "no switchport port-security mac-address sticky",
            "no switchport port-security",
            "authentication port-control auto",
            "dot1x pae authenticator",
        ])
    elif intf["security"] == "dot1x" and target_security == "nac_sticky":
        action_lines.extend([
            "no authentication port-control auto",
            "no dot1x pae authenticator",
            "switchport port-security",
            "switchport port-security mac-address sticky",
        ])
    
    return build_commands(intf["name"], action_lines)

def generate_rollback(intf):
    """Rebuilds the original configuration from parsed data."""
    action_lines[]

    if intf["mode"]:
        action_lines.append(f"switchport mode {intf['mode']}")

    if intf["vlan"]:
        action_lines.append(f"switchport access vlan {intf['vlan']}")

    if intf["security"] == "mac_sticky":
        action_lines.extend([
            "switchport port-security",
            "switchport port-security mac-address sticky",
        ])
    elif intf["security"] == "dot1x":
        action_lines.extend([
            "authentication port-control auto",
            "dot1x pae authenticator",
        ])
    
    return build_commands(intf["name"], action_lines)






if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser.py <config_file>")
        sys.exit(1)

    interfaces = parse_interfaces(sys.argv[1])

    if not interfaces:
        print("No interfaces found.")
        sys.exit(1)

    display_interface_list(interfaces)

    choice = int(input("\nSelect interface number: ")) - 1
    display_interface_detail(interfaces[choice])

    