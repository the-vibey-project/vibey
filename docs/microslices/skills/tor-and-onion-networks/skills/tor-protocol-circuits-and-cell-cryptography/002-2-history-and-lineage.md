---
id: skill-2-history-and-lineage-c8a8e66c92
purpose: 2 history and lineage
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-protocol-circuits-and-cell-cryptography/SKILL.md
requires: ["skill-1-what-tor-is-what-it-promises-and-what-it-does-not-5471d94b00"]
links: ["skill-3-the-core-protocol-cells-circuits-and-the-telescoping-handshake-a8a916a770"]
---

## §2. History and lineage

| Era | Development |
|---|---|
| Mid-1990s | Onion routing invented at the U.S. Naval Research Laboratory (Paul Syverson, David Goldschlag, Michael Reed). The insight: separate *identification* from *routing* by nesting encrypted hops. |
| 2002 | First-generation onion routing prototype deployed at NRL. |
| 2003–2004 | Roger Dingledine, Nick Mathewson, and Paul Syverson build the second-generation system — "Tor" — fixing the first gen's problems (no directory system, replay/integrity weaknesses, usability). The USENIX Security 2004 paper *Tor: The Second-Generation Onion Router* remains the canonical design document. |
| 2004–2006 | EFF funds early development; the network opens to the public. |
| Dec 2006 | The Tor Project, Inc. founded as a U.S. 501(c)(3) nonprofit. |
| 2008–2011 | Tor Browser Bundle (originally "Torbutton") makes the system usable by non-experts; bridges introduced to counter blocking in Iran and China. |
| 2013–2014 | Snowden-era scrutiny and usage spike; ntor replaces the old RSA/TAP handshakes for circuit extension; hidden-service deanonymization research (and at least one real-world attack campaign that surfaced in 2014) catalyzes the v3 redesign. |
| 2015–2018 | `.onion` registered as a special-use domain (RFC 7686); v3 onion service spec written (224/225 proposals era); ed25519 relay identities roll out. |
| 2017 | Directory authority diversity pushed; Tor Browser 7 based on Firefox ESR 52 brings multiprocess. |
| Oct 2021 | v2 onion services (16-char, RSA-1024, SHA-1-derived) **removed from the network**. All onion services are now v3 (56-char). |
| 2022–2023 | Congestion control (proposal 324) ships in C tor 0.4.7 and is tuned through 0.4.8; Conflux traffic-splitting (proposal 329) developed. |
| 2023 | Onion-service proof-of-work DoS defense (proposal 327) ships in tor 0.4.8 (Aug 2023). |
| 2024 | Conflux enabled network-wide in C tor (controlled by consensus parameter); Arti (the Rust rewrite) reaches **client-side feature parity** and gets native vanguards. Tor Project and Tails merge organizations. WebTunnel transport introduced. |
| 2025 | Tor 0.4.9 alphas introduce **CGO cell crypto** and **happy families**; Tor Browser 15 (Firefox ESR 140); Arti 2.x series begins; Tor VPN beta (Arti-based Android VPN); Conflux hardening continues; Tails 7 (Debian 13) and Qubes 4.3 ship. |
| 2026 (as of Sept) | C tor 0.4.9.5 is the first stable 0.4.9 (12 Feb 2026); the 0.4.8 series is on the deprecation path. Arti 2.6.0 (1 Sept 2026) makes CGO and congestion control always-on, and pushes toward **Arti-as-relay** (directory mirror, DNS streams, channel auth). |

**⚠️ The pattern to internalize:** **C tor is in managed decline, Arti is the future.** In
2026 the frontier work is relay/directory-authority support in Arti + post-SHA-1 cell crypto
(CGO) + congestion/flow-control modernization.

---
