---
id: skill-14-tor-vs-the-alternatives-i2p-mixnets-vpns-9309c7745e
purpose: 14 tor vs the alternatives i2p mixnets vpns
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-ecosystem-alternatives-and-governance/SKILL.md
requires: ["skill-12-the-software-ecosystem-in-2026-cd28e53516"]
links: ["skill-15-governance-funding-and-the-human-network-9585c31b09"]
---

## §14. Tor vs. the alternatives: I2P, mixnets, VPNs

| System | Model | Latency | What it's for | Key difference from Tor |
|---|---|---|---|---|
| **I2P** | Garlic routing; destination-centric overlay (eepsites) | ~similar | Hidden services *inside* a closed net; torrenting tolerated | Everyone routes for everyone (no exits by design); different threat model for browsing out. |
| **Mix networks** (Nym, Katzenpost/PQ mixes; designs from Loopix) | Batched/mixed packets, cover traffic | **seconds–minutes** | Metadata resistance vs. global adversaries (messaging, not browsing) | Trades latency for statistical unlinkability — the defense Tor explicitly doesn't attempt. |
| **VPN** | One trusted proxy | lowest | Geo-shifting, untrusted-Wi-Fi, policy compliance | Single point that sees everything; no unlinkability claim at all. |

Layering patterns, honestly assessed:

- **Tor over VPN** (you → VPN → Tor): hides Tor use from your ISP, shifts the "knows who you
  are" trust to the VPN. Sensible if Tor itself is flagged in your environment. Bridges/PTs
  are the *stronger* version of this (§10 → `tor-censorship-circumvention-and-bridges`).
- **VPN over Tor** (you → Tor → VPN → site): rare, hard to do safely, and the VPN exit can
  correlate your Tor usage. Almost never recommended.
- **Tor Browser over Tails/Whonix**: not layering proxies — layering *failure domains*. This
  is the pattern with real evidence behind it.

---
