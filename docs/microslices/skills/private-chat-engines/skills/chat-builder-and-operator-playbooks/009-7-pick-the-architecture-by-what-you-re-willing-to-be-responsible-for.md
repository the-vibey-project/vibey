---
id: skill-7-pick-the-architecture-by-what-you-re-willing-to-be-responsible-for-6a0db3a1e9
purpose: 7 pick the architecture by what you re willing to be responsible for
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-6-libraries-and-starting-points-all-actively-maintained-as-of-2026-c6f821b674"]
links: ["skill-8-the-operations-checklist-matrix-flavoured-mostly-transferable-40fbd873bc"]
---

## 7. Pick the architecture by what you're willing to be responsible for

| You want… | Run… | You'll own… |
|---|---|---|
| A zero-ops private chat for family/team | Signal (or Threema paid) | device posture & user training only |
| Sovereign org comms with admin controls | **Element/Synapse or Continuwuity** (Matrix 2.0; or Wire enterprise, self-hosted variants) | infra, keys, GDPR/DSA duties, moderation |
| Public square with scale + bots | Telegram communities | platform policy risk; nothing infra-side |
| Metadata-resistant small group comms | SimpleX (your own relays) | relay uptime, link distribution |
| Censored-population comms | Signal TLS proxies, Session nodes, Delta Chat chatmail, Tor pluggable transports | volunteer infra, rotation discipline |
| Offline/mesh contingencies | Briar (maintenance mode; know it) | pairing logistics |
