"""
Cisco Interface Configuration Parser and Command Generator
 
Parses Cisco switch running-config files to extract interface details
and generates CLI commands for common operations such as VLAN changes,
MAC sticky resets, and security mode conversions.
"""

from ciscoconfparse import CiscoConfParse
import sys

HELP_TEXT = """
Cisco Interface Config Parser and Command Generator

Usage: python parser.py <config_file>

Description:
  Parses Cisco switch running-config files to extract interface details
  and generates CLI commands for common NOC operations.

Arguments:
  config_file    Path to a Cisco running-config text file

Examples:
  python parser.py sample.txt

Selection:
  Single ports:  1,3,5
  Ranges:        1-10
  Mixed:         1,3,6-10,15-20

Available Actions:
  1. VLAN change
  2. MAC sticky reset
  3. MAC sticky to dot1x
  4. Dot1x to MAC sticky
  5. VLAN change with port security conversion
  6. Generate rollback only
"""

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


def format_interface_line(names):
    """
    Returns 'interface <name>' for a single port,
    or 'interface range <name>, <name>, ...' for multiple.
    """
    if len(names) == 1:
        return f"interface {names[0]}"
    return f"interface range {', '.join(names)}"

def build_commands(names, action_lines):
    """
    Wraps action-specific lines in the standard conf t / shutdown / end / wr skeleton.
    Accepts a list of names for interface range support.
    """
    commands = [
        "conf t",
        format_interface_line(names),
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

def generate_rollback(selected):
    """
    Generates rollback commands for a batch of interfaces.
    Groups ports with identical original configs into interface range blocks.
    Ports with unique configs get individual blocks.
    All wrapped in a single conf t / end / wr.
    """
    groups = {}
    for intf in selected:
        key = (intf["mode"], intf["vlan"], intf["security"], intf["admin_state"])
        if key not in groups:
            groups[key] = []
        groups[key].append(intf["name"])

    commands = ["conf t"]

    group_list = list(groups.items())
    for i, (key, names) in enumerate(group_list):
        commands.append(format_interface_line(names))
        commands.append(" shutdown")

        mode, vlan, security, admin_state = key

        if mode:
            commands.append(f" switchport mode {mode}")
        if vlan:
            commands.append(f" switchport access vlan {vlan}")
        if security == "mac_sticky":
            commands.extend([
                " switchport port-security",
                " switchport port-security mac-address sticky",
            ])
        elif security == "dot1x":
            commands.extend([
                " authentication port-control auto",
                " dot1x pae authenticator",
            ])

        if admin_state == "shutdown":
            commands.append(" shutdown")
        else:
            commands.append(" no shutdown")

        # Use 'exit' between groups, 'end/wr' after the last one
        if i < len(group_list) - 1:
            commands.append("exit")
            commands.append("!")
        else:
            commands.extend(["end", "wr"])

    return "\n".join(commands)


# --- Section 4: Main Flow ---


ACTIONS = {
    "1": "VLAN change",
    "2": "MAC sticky reset",
    "3": "MAC sticky to dot1x",
    "4": "Dot1x to MAC sticky",
    "5": "VLAN change with port security conversion",
    "6": "Generate rollback only",
}

def display_actions():
    """Prints the available actions menu."""
    print("\nAvailable Actions")
    print("-----------------")
    for key, label in ACTIONS.items():
        print(f"  {key}. {label}")

def get_interface_selections(interfaces):
    """
    Prompts the user to select one or more interfaces by number.
    Supports single numbers, ranges, and mixed input.
    Examples: '1,3,5' or '1-10' or '1,3,6-10'
    Returns a list of selected interface dictionaries.
    """
    raw = input("\nSelect interface(s) (e.g. 1,3,5 or 1-10 or 1,3,6-10): ").strip()
    selected = []
    seen = set()

    for part in raw.split(","):
        part = part.strip()

        if "-" in part:
            start, end = part.split("-", 1)
            start = int(start.strip())
            end = int(end.strip())
            for num in range(start, end + 1):
                idx = num - 1
                if 0 <= idx < len(interfaces) and idx not in seen:
                    selected.append(interfaces[idx])
                    seen.add(idx)
        else:
            idx = int(part) - 1
            if 0 <= idx < len(interfaces) and idx not in seen:
                selected.append(interfaces[idx])
                seen.add(idx)
            else:
                print(f"  Skipping invalid selection: {part}")

    return selected

def handle_action(action, selected):
    """
    Runs the chosen action against the selected batch.
    Generates one command block and one rollback block.
    """
    names = [intf["name"] for intf in selected]

    # Filter out conflict ports
    conflict_ports = [intf for intf in selected if intf["security"] == "conflict"]
    if conflict_ports:
        print("\n  The following ports have security conflicts and will be skipped:")
        for intf in conflict_ports:
            print(f"    - {intf['name']}")
        selected = [intf for intf in selected if intf["security"] != "conflict"]
        names = [intf["name"] for intf in selected]
        if not selected:
            print("  No valid ports remaining.")
            return

    print("\nGenerated Commands")
    print("------------------")

    if action == "1":
        new_vlan = input("  Enter new VLAN: ").strip()
        print(build_commands(names, [
            f"switchport access vlan {new_vlan}",
        ]))

    elif action == "2":
        print(build_commands(names, [
            "no switchport port-security mac-address sticky",
            "no switchport port-security",
            "switchport port-security",
            "switchport port-security mac-address sticky",
        ]))

    elif action == "3":
        print(build_commands(names, [
            "no switchport port-security mac-address sticky",
            "no switchport port-security",
            "authentication port-control auto",
            "dot1x pae authenticator",
        ]))

    elif action == "4":
        print(build_commands(names, [
            "no authentication port-control auto",
            "no dot1x pae authenticator",
            "switchport port-security",
            "switchport port-security mac-address sticky",
        ]))

    elif action == "5":
        new_vlan = input("  Enter new VLAN: ").strip()
        target = input("  Enter target security (mac_sticky/dot1x): ").strip()
        action_lines = [f"switchport access vlan {new_vlan}"]
        if target == "dot1x":
            action_lines.extend([
                "no switchport port-security mac-address sticky",
                "no switchport port-security",
                "authentication port-control auto",
                "dot1x pae authenticator",
            ])
        elif target == "mac_sticky":
            action_lines.extend([
                "no authentication port-control auto",
                "no dot1x pae authenticator",
                "switchport port-security",
                "switchport port-security mac-address sticky",
            ])
        print(build_commands(names, action_lines))

    elif action == "6":
        pass  # Rollback prints below

    else:
        print("  Invalid action.")
        return

    print("\nRollback Commands")
    print("-----------------")
    print(generate_rollback(selected))

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(HELP_TEXT)
        sys.exit(0)

    interfaces = parse_interfaces(sys.argv[1])

    if not interfaces:
        print("No interfaces found.")
        sys.exit(1)

    while True:
        display_interface_list(interfaces)
        selected = get_interface_selections(interfaces)

        if not selected:
            print("No valid interfaces selected.")
            continue

        print(f"\n  Selected {len(selected)} interface(s):")
        for intf in selected:
            display_interface_detail(intf)

        display_actions()
        action = input("\nSelect action number: ").strip()

        handle_action(action, selected)

        again = input("\nSelect more interfaces? (y/n): ").strip().lower()
        if again != "y":
            break

if __name__ == "__main__":
    main()
    
