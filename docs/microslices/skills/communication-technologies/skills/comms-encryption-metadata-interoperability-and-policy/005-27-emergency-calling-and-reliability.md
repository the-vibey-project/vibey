---
id: skill-27-emergency-calling-and-reliability-1ce1cb25b1
purpose: 27 emergency calling and reliability
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-encryption-metadata-interoperability-and-policy/SKILL.md
requires: ["skill-26-the-encryption-policy-debate-8e1bc72fc6"]
links: []
---

## §27. Emergency Calling and Reliability

**⚠️ Emergency calling carries obligations that ordinary services do not**: ⚠️ **location
delivery (E911 Phase II, AML on mobile), priority routing, and — historically — a
guarantee of service without payment or SIM.**
**⚠️ VoIP and VoWiFi break the location assumption** (§11 → `comms-telephony-pstn-ss7-voip-and-caller-id`) — ⚠️ **a nomadic IP endpoint has
no fixed address, which is why registered-address requirements and dynamic location
mechanisms exist, and why they fail in edge cases.**
**⚠️ The power problem** is the underrated one: ⚠️ **the copper PSTN powered the handset from
the exchange, so phones worked in a blackout.** ⚠️ **All-IP does not, which is a genuine
resilience regression that copper retirement (§8 → `comms-telephony-pstn-ss7-voip-and-caller-id`) has to plan around.**
**⚠️ Text-to-emergency and RTT** matter for accessibility (see a speaking reference §23).
**⚠️ Public warning systems** (cell broadcast) reach every handset in an area without
knowing who they are, ⚠️ **which is a nice property — and false alerts have real
consequences.**
