# Cisco Interface Configuration Parser

## Project Overview

In enterprise network environments, switch port configuration requests are a routine part of NOC operations. These requests may involve a single interface or dozens of interfaces across a production floor. While Cisco running-config files are readable by engineers, reviewing them manually becomes inefficient when dealing with many ports at once.

This project parses raw Cisco switch running-config output and extracts key attributes from each interface block: interface name, description, switchport mode, VLAN assignment, port security (MAC sticky or 802.1X), and administrative state. The parsed data is displayed in a structured format and used to generate CLI command sequences for common operations such as VLAN changes, MAC sticky resets, and port security conversions. Rollback commands are automatically generated from the original parsed configuration so that changes can be reversed if needed.

The complexity point of this project is the parsing and validation logic. The parser walks each interface block once, extracts six key fields using explicit string matching, and detects security conflicts (where both MAC sticky and 802.1X are configured on the same port) at parse time. This means every downstream section; display, command generation, and rollback, can trust the parsed data without re-inspecting the raw configuration. The command generator supports batch operations using Cisco's interface range syntax, and the rollback engine groups ports by their original configuration to produce compact, accurate restoration commands.

## Requirements

- Python 3
- ciscoconfparse

## Installation

Using pip:
pip install ciscoconfparse 

OR

pip3 install ciscoconfparse 

## Usage

python parserv3.py <"config file">

OR

python3 parserv3.py <"config file">


For example: python3 parserv3.py sample.txt

The program will:

1. Parse the config file and display all discovered interfaces.
2. Prompt you to select one or more interfaces (e.g. `1,3,5` or `1-10` or `1,3,6-10`).
3. Display the parsed details for each selected interface.
4. Present available actions (VLAN change, MAC sticky reset, security conversions, etc.).
5. Generate the CLI commands for the chosen action and corresponding rollback commands.
6. Ask if you want to select more interfaces or exit.

## Glossary

**Running-Config** — The active configuration currently running on a Cisco switch. Viewed with the `show running-config` command.

**Interface** — A physical port on a switch (e.g., GigabitEthernet1/0/1). Each interface has its own configuration block in the running-config.

**VLAN (Virtual Local Area Network)** — A logical network segment. Devices on the same VLAN can communicate with each other. Ports are assigned to VLANs to control which network segment a connected device belongs to.

**Access Mode** — A switchport mode where the port belongs to a single VLAN. Typically used for end devices like PCs and printers.

**Trunk Mode** — A switchport mode that carries traffic for multiple VLANs. Typically used for switch-to-switch or switch-to-router connections.

**MAC Sticky (Port Security)** — A security feature that learns and remembers the MAC address of the device connected to a port. If a different device is plugged in, the port can restrict or shut down access.

**802.1X / dot1x** — A network authentication protocol that requires a device to authenticate (usually through a RADIUS server) before being granted network access on a port.

**Interface Range** — A Cisco CLI feature that allows the same configuration commands to be applied to multiple ports at once (e.g., `interface range GigabitEthernet1/0/1, GigabitEthernet1/0/3, GigabitEthernet1/0/5`).

**Admin State** — Whether a port is administratively enabled (up) or disabled (shutdown). A shutdown port does not pass traffic regardless of its other configuration.

**Rollback** — A set of commands that restores a port to its original configuration. Used to reverse changes if something goes wrong.

**conf t / end / wr** — Standard Cisco CLI sequence. `conf t` enters configuration mode, `end` exits configuration mode, and `wr` saves the configuration to memory.

## Sample Data

The included `sample.txt` contains 20 interface blocks representing a realistic switch configuration with a mix of access ports, trunk ports, MAC sticky security, 802.1X security, shutdown ports, ports with no security, and two ports with intentional security conflicts for testing.