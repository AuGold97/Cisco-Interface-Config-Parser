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

## Sample Data

The included `sample.txt` contains 20 interface blocks representing a realistic switch configuration with a mix of access ports, trunk ports, MAC sticky security, 802.1X security, shutdown ports, ports with no security, and two ports with intentional security conflicts for testing.