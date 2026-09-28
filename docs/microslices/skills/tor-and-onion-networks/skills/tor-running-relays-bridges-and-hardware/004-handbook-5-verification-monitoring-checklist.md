---
id: skill-handbook-5-verification-monitoring-checklist-6c2221b818
purpose: handbook 5 verification monitoring checklist
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-running-relays-bridges-and-hardware/SKILL.md
requires: ["skill-handbook-4-hardware-builds-e0052f71ac"]
links: ["skill-handbook-6-legal-ethical-abuse-handling-box-f4499e049b"]
---

## Handbook §5. Verification & monitoring checklist

1. **Egress identity**: `https://check.torproject.org/api/ip` from every path you claim is
   Tor-routed; confirm the reported IP is a current exit on Relay Search / ExoneraTor.
2. **DNS**: tcpdump the physical interface while the app resolves — you should see *no*
   upstream queries except the tor process's own.
3. **Relay health**: nyx locally; Relay Search + MetricsPort/Prometheus externally; first flags
   within days, Guard eligibility after ~weeks of stability, HSDir after Fast+Stable.
4. **Onion service**: fetch the descriptor via a second tor instance
   (`torsocks curl http://<addr>.onion`), watch `hs_pow_*` metrics under load-test, confirm
   offline-master rotation procedure on a staging service first.
5. **Time**: anonymity systems are clock-sensitive (consensus validity, blinded-key periods).
   Disciplined NTP on everything. (Over Tor? NTP is UDP — use chrony over clearnet on gateway
   boxes; the risk model allows it.)

---
