---
id: skill-handbook-6-legal-ethical-abuse-handling-box-f4499e049b
purpose: handbook 6 legal ethical abuse handling box
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-running-relays-bridges-and-hardware/SKILL.md
requires: ["skill-handbook-5-verification-monitoring-checklist-6c2221b818"]
links: ["skill-where-to-go-next-5e9ccbc7cc"]
---

## Handbook §6. Legal, ethical & abuse-handling box

- Running relays, bridges, exits, and onion services is legal in the US, EU, and most
  democracies; *usage of them* is regulated like any internet use. A handful of states block or
  restrict Tor — that's censorship of users, not generally criminalization of operators. The
  EFF's *Tor Legal FAQ* and the Tor Project's abuse templates are the two documents to read
  before plugging anything in.
- **Middle relays** and **bridges** attract essentially no complaints; their IPs never touch
  destination servers. **Exits** attract automated abuse mail regularly — answer it with the
  standard response (point to ExoneraTor + exit docs, confirm no logging), and keep
  `ReducedExitPolicy` unless you know why you're widening it.
- Don't run exits from home or work IPs; **don't log user traffic** (it adds liability, not
  protection); don't run services whose purpose is harm — the volunteer network's social
  license is the thin thing standing between this infrastructure and legislated blocking, and
  operators are its custodians.
- Censorship-circumvention tooling (bridges, Snowflake, PTs) exists for the users the Tor
  Project names: dissidents, journalists, abuse survivors, ordinary people behind hostile
  networks. Build accordingly.

---
