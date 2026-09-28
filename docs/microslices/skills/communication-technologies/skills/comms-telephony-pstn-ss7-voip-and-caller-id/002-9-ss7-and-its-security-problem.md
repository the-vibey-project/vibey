---
id: skill-9-ss7-and-its-security-problem-814eaa106d
purpose: 9 ss7 and its security problem
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-telephony-pstn-ss7-voip-and-caller-id/SKILL.md
requires: ["skill-8-the-pstn-1dbd7e1790"]
links: ["skill-10-voip-and-sip-6a0d7b8a6f"]
---

## §9. ⚠️ SS7 and Its Security Problem

```
⚠️ WHAT IT IS  ⚠️ the out-of-band signalling network that sets up
   calls, routes SMS, handles roaming and queries subscriber
   location. ⚠️ Designed in the 1970s-80s
⚠️ ⚠️ THE DESIGN ASSUMPTION WAS A CLOSED CLUB OF TRUSTED STATE
   MONOPOLY CARRIERS. ⚠️ There is essentially NO AUTHENTICATION
   between network elements
⚠️ ⚠️ WHEN DEREGULATION AND ROAMING OPENED IT UP, that
   assumption failed — ⚠️ and access can be obtained through
   small carriers, leased connections or compromised equipment
⚠️ ⚠️ WHAT SS7 ACCESS PERMITS  ⚠️ locating a subscriber ·
   ⚠️ INTERCEPTING SMS (⚠️ which defeats SMS-based two-factor
   authentication, §13) · intercepting or redirecting calls ·
   denial of service
⚠️ ⚠️ THIS IS NOT THEORETICAL. ⚠️ It has been demonstrated
   publicly, documented by regulators, and used in the wild
⚠️ DIAMETER  ⚠️ the LTE-era successor, with better authentication
   in principle and ⚠️ comparable classes of vulnerability in
   practice, partly because interworking with SS7 is required
⚠️ MITIGATIONS  ⚠️ SS7 firewalls, home routing, filtering — but
   ⚠️ THE STRUCTURAL PROBLEM PERSISTS because the network must
   interoperate globally with participants of varying integrity
   (§1's federated trade, in its most consequential form)
```

---
