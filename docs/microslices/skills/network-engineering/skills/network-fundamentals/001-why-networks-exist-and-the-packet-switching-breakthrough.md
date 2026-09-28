---
id: skill-why-networks-exist-and-the-packet-switching-breakthrough-d1bed3caaa
purpose: why networks exist and the packet switching breakthrough
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: []
links: ["skill-packets-the-unit-of-network-communication-1c3bd97085"]
---

## Why networks exist and the packet-switching breakthrough

A computer network is two or more devices connected to exchange data. Every protocol, device, and standard exists to make that exchange reliable, fast, and scalable.

The origin story matters. In the mid-1960s Bob Taylor at ARPA noticed he needed three separate terminals to connect to three different research computers. On October 29, 1969, UCLA sent "LOGIN" to Stanford Research Institute — the system crashed after "LO," but the full message went through within an hour. ARPANET was alive.

The key innovation was **packet switching**, independently conceived by Paul Baran (for nuclear-survivable military communications) and Donald Davies (who coined the term). Instead of dedicating a physical wire between two parties — how telephone calls worked — data is chopped into small pieces and routed independently through a shared network. Packet switching is a highway system shared by everyone, not a private road built just for you. It is why billions of people can use the Internet simultaneously.

**The postal system analogy** is the single most useful mental model. Data is a letter. The IP address is the mailing address. Packets are individual envelopes. Routers are postal sorting centers that read the address and forward the envelope toward its destination. This analogy scales surprisingly well into advanced topics.
