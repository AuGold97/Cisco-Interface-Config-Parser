from ciscoconfparse import CiscoConfParse
import sys


def parse_interfaces(config_file):
    parse = CiscoConfParse(config_file)
    interfaces = []

    for intf in parse.find_objects(r"^interface"):
        interface_data = {
            "interface": intf.text.split()[1],
            "description": None,
            "mode": None,
            "vlan": None,
            "security": "none",
            "admin_state": "up"
        }

        desc = intf.re_search_children(r"^\s+description\s+")
        if desc:
            interface_data["description"] = desc[0].text.strip().replace("description ", "", 1)

        mode = intf.re_search_children(r"^\s+switchport mode\s+")
        if mode:
            interface_data["mode"] = mode[0].text.strip().split()[-1]

        vlan = intf.re_search_children(r"^\s+switchport access vlan\s+")
        if vlan:
            interface_data["vlan"] = vlan[0].text.strip().split()[-1]

        if intf.re_search_children(r"^\s+switchport port-security mac-address sticky$"):
            interface_data["security"] = "mac_sticky"
        elif intf.re_search_children(r"^\s+dot1x pae authenticator$"):
            interface_data["security"] = "dot1x"

        if intf.re_search_children(r"^\s+shutdown$"):
            interface_data["admin_state"] = "shutdown"

        interfaces.append(interface_data)

    return interfaces


def generate_vlan_change(interface_name, new_vlan):
    return "\n".join([
        "conf t",
        f"interface {interface_name}",
        " shutdown",
        f" switchport access vlan {new_vlan}",
        " no shutdown",
        "end",
        "wr"
    ])


def generate_mac_sticky_reset(interface_name):
    return "\n".join([
        "conf t",
        f"interface {interface_name}",
        " shutdown",
        " no switchport port-security mac-address sticky",
        " no switchport port-security",
        " switchport port-security",
        " switchport port-security mac-address sticky",
        " no shutdown",
        "end",
        "wr"
    ])


def generate_mac_sticky_to_dot1x(interface_name):
    return "\n".join([
        "conf t",
        f"interface {interface_name}",
        " shutdown",
        " no switchport port-security mac-address sticky",
        " no switchport port-security",
        " authentication port-control auto",
        " dot1x pae authenticator",
        " no shutdown",
        "end",
        "wr"
    ])


def generate_dot1x_to_mac_sticky(interface_name):
    return "\n".join([
        "conf t",
        f"interface {interface_name}",
        " shutdown",
        " no authentication port-control auto",
        " no dot1x pae authenticator",
        " switchport port-security",
        " switchport port-security mac-address sticky",
        " no shutdown",
        "end",
        "wr"
    ])


def generate_vlan_change_with_conversion(interface_name, new_vlan, current_security, target_security):
    commands = [
        "conf t",
        f"interface {interface_name}",
        " shutdown",
        f" switchport access vlan {new_vlan}"
    ]

    if current_security == "dot1x" and target_security == "mac_sticky":
        commands.extend([
            " no authentication port-control auto",
            " no dot1x pae authenticator",
            " switchport port-security",
            " switchport port-security mac-address sticky"
        ])
    elif current_security == "mac_sticky" and target_security == "dot1x":
        commands.extend([
            " no switchport port-security mac-address sticky",
            " no switchport port-security",
            " authentication port-control auto",
            " dot1x pae authenticator"
        ])

    commands.extend([
        " no shutdown",
        "end",
        "wr"
    ])

    return "\n".join(commands)


def generate_rollback(interface_data):
    commands = [
        "conf t",
        f"interface {interface_data['interface']}",
        " shutdown"
    ]

    if interface_data["mode"]:
        commands.append(f" switchport mode {interface_data['mode']}")

    if interface_data["vlan"]:
        commands.append(f" switchport access vlan {interface_data['vlan']}")

    if interface_data["security"] == "mac_sticky":
        commands.extend([
            " switchport port-security",
            " switchport port-security mac-address sticky"
        ])
    elif interface_data["security"] == "dot1x":
        commands.extend([
            " authentication port-control auto",
            " dot1x pae authenticator"
        ])

    if interface_data["admin_state"] == "shutdown":
        commands.append(" shutdown")
    else:
        commands.append(" no shutdown")

    commands.extend([
        "end",
        "wr"
    ])

    return "\n".join(commands)


def display_interface(interface_data):
    security_display = {
        "mac_sticky": "MAC sticky enabled",
        "dot1x": "802.1X enabled",
        "none": "No security configured"
    }

    print("\nParsed Interface Details")
    print("------------------------")
    print(f"Interface Port: {interface_data['interface']}")
    print(f"Description: {interface_data['description']}")
    print(f"Mode: {interface_data['mode']}")
    print(f"VLAN: {interface_data['vlan']}")
    print(f"Security Mode: {security_display.get(interface_data['security'], interface_data['security'])}")
    print(f"Admin State: {interface_data['admin_state']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python parser_with_commands.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]
    interfaces = parse_interfaces(config_file)

    if not interfaces:
        print("No interfaces found.")
        sys.exit(1)

    for idx, intf in enumerate(interfaces, start=1):
        print(f"{idx}. {intf['interface']}")

    choice = int(input("\nSelect interface number: ")) - 1
    selected = interfaces[choice]

    display_interface(selected)

    print("\nAvailable Actions")
    print("-----------------")
    print("1. VLAN change")
    print("2. MAC sticky reset")
    print("3. MAC sticky to dot1x")
    print("4. Dot1x to MAC sticky")
    print("5. VLAN change with security conversion")
    print("6. Generate rollback only")

    action = input("\nSelect action number: ").strip()

    print("\nGenerated Commands")
    print("------------------")

    if action == "1":
        new_vlan = input("Enter new VLAN: ").strip()
        print(generate_vlan_change(selected["interface"], new_vlan))

    elif action == "2":
        print(generate_mac_sticky_reset(selected["interface"]))

    elif action == "3":
        print(generate_mac_sticky_to_dot1x(selected["interface"]))

    elif action == "4":
        print(generate_dot1x_to_mac_sticky(selected["interface"]))

    elif action == "5":
        new_vlan = input("Enter new VLAN: ").strip()
        target_security = input("Enter target security (mac_sticky/dot1x): ").strip()
        print(generate_vlan_change_with_conversion(
            selected["interface"],
            new_vlan,
            selected["security"],
            target_security
        ))

    elif action == "6":
        print(generate_rollback(selected))

    else:
        print("Invalid action.")

    print("\nRollback Commands")
    print("-----------------")
    print(generate_rollback(selected))


if __name__ == "__main__":
    main()