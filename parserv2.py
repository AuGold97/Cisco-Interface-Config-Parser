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
    