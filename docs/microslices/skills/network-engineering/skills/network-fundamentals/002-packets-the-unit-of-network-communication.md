---
id: skill-packets-the-unit-of-network-communication-1c3bd97085
purpose: packets the unit of network communication
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-why-networks-exist-and-the-packet-switching-breakthrough-d1bed3caaa"]
links: ["skill-osi-model-networking-s-periodic-table-5da2fd4257"]
---

## Packets: the unit of network communication

When you send a photo, it travels as packets — small, independently addressed chunks, each routed separately.

Each packet has three parts:
- **Header**: addressing and control information — source/destination addresses, sequence numbers, protocol identifiers. The envelope with addresses and postage.
- **Payload**: the actual data — a fragment of your photo.
- **Trailer**: CRC checksum for error detection. The receiver verifies the data was not corrupted.

Why packets instead of one big chunk? Three reasons: efficiency (statistical multiplexing lets multiple conversations share wires simultaneously), resilience (only the corrupt packet needs retransmission), and fairness (no single transfer monopolizes the link).

Key units: network speeds are measured in **bits** per second (Mbps, Gbps), while storage is measured in **bytes** (MB, GB). A 100 Mbps connection transfers about 12.5 MB/s. The standard maximum packet size — the **MTU (Maximum Transmission Unit)** — is **1,500 bytes**, a historical artifact of early Ethernet design that persists today.
