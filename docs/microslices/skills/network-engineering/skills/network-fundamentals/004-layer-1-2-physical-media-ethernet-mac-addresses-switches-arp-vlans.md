---
id: skill-layer-1-2-physical-media-ethernet-mac-addresses-switches-arp-vlans-6927395337
purpose: layer 1 2 physical media ethernet mac addresses switches arp vlans
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-osi-model-networking-s-periodic-table-5da2fd4257"]
links: ["skill-layer-3-ip-addressing-subnetting-routing-nat-3ad0b83185"]
---

## Layer 1-2: Physical media, Ethernet, MAC addresses, switches, ARP, VLANs

**Layer 1 — Physical**: raw bits on a wire. Electrical signals, fiber optics, Wi-Fi radio. Devices: hubs (dumb repeaters that blast traffic to every port — effectively extinct), cables, repeaters.

**MAC addresses** are 48-bit identifiers burned into every NIC at the factory: `00:1A:2B:3C:4D:5E`. The first 24 bits identify the manufacturer (OUI). The broadcast address `FF:FF:FF:FF:FF:FF` reaches every device on the local network. MAC addresses are physical and permanent; they enable delivery within a single network segment.

**Switches** read MAC addresses and forward frames only to the correct port. A switch builds a MAC address table by inspecting incoming traffic — it learns which MAC is on which port. Think of a mailroom clerk who reads the name on each envelope and places it in the correct mailbox. Switches operate at Layer 2 and create separate collision domains per port.

**ARP (Address Resolution Protocol, RFC 826)** bridges Layer 2 and Layer 3. Your computer knows the destination IP but Ethernet frames require a MAC address. ARP broadcasts: "Who has `192.168.1.20`? Tell `192.168.1.10`." Only the device with that IP responds with its MAC. Your computer caches this mapping (1-5 minutes). ARP has no authentication — a critical weakness enabling ARP spoofing (man-in-the-middle attacks). Defenses: Dynamic ARP Inspection on managed switches. IPv6 replaces ARP with NDP (Neighbor Discovery Protocol, RFC 4861).

**VLANs (IEEE 802.1Q)** create isolated broadcast domains within a single physical switch. Without VLANs, every port shares one broadcast domain — every ARP request reaches every device. VLANs insert a 4-byte tag into the Ethernet frame containing a 12-bit VLAN ID (supporting 4,094 usable VLANs). Access ports connect to end devices (one VLAN). Trunk ports carry multiple VLANs between switches. Inter-VLAN routing requires Layer 3: either a Layer 3 switch with SVIs or the older router-on-a-stick approach.
