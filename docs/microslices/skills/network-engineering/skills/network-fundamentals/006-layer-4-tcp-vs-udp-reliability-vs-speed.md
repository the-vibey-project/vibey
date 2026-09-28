---
id: skill-layer-4-tcp-vs-udp-reliability-vs-speed-7f7ba1edb6
purpose: layer 4 tcp vs udp reliability vs speed
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-layer-3-ip-addressing-subnetting-routing-nat-3ad0b83185"]
links: ["skill-the-tcp-three-way-handshake-129c809616"]
---

## Layer 4: TCP vs UDP — reliability vs speed

**TCP (RFC 793)** is connection-oriented: establishes a session before data transfer, guarantees every byte arrives in order, retransmits lost data. Uses acknowledgments, sequence numbers, sliding window for flow control, and congestion control algorithms (slow start, congestion avoidance, fast retransmit). Header: 20-60 bytes. Use for: HTTP/HTTPS, SSH, FTP, email — anything where data integrity matters.

**UDP (RFC 768)** is connectionless: fires packets with no handshake, no ACKs, no ordering, no congestion control. Header: 8 bytes (source port, destination port, length, checksum). Use for: DNS queries, video streaming, VoIP, gaming — anything where speed matters more than perfection. A dropped video frame causes a brief glitch; retransmitting it would introduce unacceptable delay.

**QUIC** (RFC 9000, developed by Google) runs over UDP but implements TCP's reliability at the application layer, eliminating head-of-line blocking. HTTP/3 uses QUIC. As of 2025, over 25% of Internet traffic runs on it.
