---
id: skill-the-tcp-three-way-handshake-129c809616
purpose: the tcp three way handshake
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-layer-4-tcp-vs-udp-reliability-vs-speed-7f7ba1edb6"]
links: ["skill-layers-5-7-tls-http-dns-d019076848"]
---

## The TCP three-way handshake

Before any data flows, both sides synchronize state:

1. **SYN**: Client → `Seq=1000, SYN`. "I want to talk. My sequences start at 1000."
2. **SYN-ACK**: Server → `Seq=5000, Ack=1001, SYN+ACK`. "I hear you. My sequences start at 5000."
3. **ACK**: Client → `Seq=1001, Ack=5001`. Both enter ESTABLISHED. Data flows.

Why three steps? Both directions need to synchronize sequence numbers. Logically four exchanges, compressed to three because the server combines SYN+ACK. Connection teardown uses four-way FIN→ACK→FIN→ACK because each direction closes independently.
