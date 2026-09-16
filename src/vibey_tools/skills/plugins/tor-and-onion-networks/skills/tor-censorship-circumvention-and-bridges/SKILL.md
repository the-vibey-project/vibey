---
name: tor-censorship-circumvention-and-bridges
description: "Use when reasoning about Tor under censorship — bridges, pluggable transports (obfs4, Snowflake, WebTunnel, meek, Conjure), how bridges are distributed, and how blocking actually works — or when reading a blocking-event report. Includes the 2026 Snowflake DTLS fingerprinting campaign and Iran's 2025 stealth blackout as worked cases. Covers §10. Companion to the other Tor and onion-network skills."
---

# Tor Under Censorship: Bridges, Pluggable Transports, and the Fingerprint Arms Race

> **Part 4 of 8** of the *Tor and Onion Networks* reference (plugin `tor-and-onion-networks`),
> covering §10. Sibling skills:
> `tor-protocol-circuits-and-cell-cryptography` (§1–§5),
> `tor-network-consensus-guards-and-paths` (§6–§7),
> `tor-onion-services-and-hardening` (§8–§9),
> `tor-attack-literature-and-threat-model` (§11),
> `tor-ecosystem-alternatives-and-governance` (§12, §14–§16),
> `tor-building-on-tor-software-patterns` (§13.1–§13.4, handbook §1),
> `tor-running-relays-bridges-and-hardware` (§13.5, handbook §2–§6).
> Section numbers are shared across the set; a reference written as §N → `skill` points into
> that sibling skill.
>
> **⚠️ Currency: this is the fastest-rotting section of the whole reference.** Compiled
> 16 September 2026. Transport *architecture* is stable; **which transport currently works in
> which country is a weekly-moving target.** Check
> [net4people/bbs](https://github.com/net4people/bbs) and the
> [Tor forum](https://forum.torproject.org/) before advising anyone operationally.

> **⚠️ Tor hides your destination by default. Hiding the *fact that you use Tor* is a
> separate, opt-in, and permanently contested problem.**
>
> **⚠️ GOTCHA** boxes mark where the mental model people carry is wrong in ways that get
> users blocked or exposed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ TWO DISTINCT PROBLEMS: FINGERPRINTING AND ENUMERATION** (§10.1, §10.2). **A censor
>    can block you by recognizing your *traffic* (fingerprinting) or by discovering your
>    *bridges* (enumeration). Transports fight the first; distribution channels fight the
>    second. A transport that solves one and not the other fails.**
> 2. **⚠️ "RANDOM-LOOKING" IS NOW A FINGERPRINT** (§10.1). **obfs4's design goal — bytes
>    with no structure — is itself detectable in an allowlist environment where everything
>    legitimate has recognizable structure. This is why the frontier moved to *mimicry*
>    (WebTunnel, Conjure) rather than *obfuscation*.**
> 3. **⚠️ THE ARMS RACE IS NOW AT THE HANDSHAKE LAYER** (§10.3). **The 2026 Snowflake
>    campaign blocked on a DTLS ClientHello signature, not on IPs. This is JA3/JA4
>    cat-and-mouse applied to circumvention, and it means library-level TLS/DTLS fingerprints
>    are a security property of your tooling.**

---

## §10. Censorship circumvention: bridges and pluggable transports

Tor's front-line war in 2025–2026 is fingerprinting and enumeration, and this is the area
where "current state" rots fastest.

**Architecture first:** **pluggable transports (PTs)** are out-of-process proxies that
masquerade Tor traffic as something else. The client tor talks to a local PT shim
(`ClientTransportPlugin`), which carries an obfuscated stream to a **bridge** — an unlisted
entry node that does not appear in the public consensus (§6.1 →
`tor-network-consensus-guards-and-paths`). Snowflake adds volunteer proxies in front of the
bridge.

### §10.1 The transports

| Transport | Camouflage | Status (Sept 2026) |
|---|---|---|
| **obfs4** | Random-looking encrypted bytes; passive content + active-probing resistance (bridge secret required) | Workhorse, default in Tor Browser. **Degrading** vs. China's GFW (behavioral classification, probing-driven enumeration) and vs. protocol-allowlist environments, which block "random-looking" by default. |
| **Snowflake** | WebRTC (DTLS) to ephemeral volunteer proxies; rendezvous via broker over domain-front/AMP-cache | Most-used transport in Iran and Russia; see §10.3 for the 2026 DTLS fingerprint war. |
| **WebTunnel** | Genuine HTTPS/WebSocket-like upgrade, co-resident with a real website on the bridge host | Deployed 2024-on; key transport for Russia; but **June 2025** saw mass bridge enumeration + blocking there — distribution moved to the Telegram bridge bot. Integrated into Tor VPN beta ≥ 1.4.0. |
| **meek** | Domain fronting through CDN | Effectively vestigial since the 2018–2019 CDN fronting shutdowns (Google/AWS/Azure); fronting survives only inside Snowflake's broker rendezvous. |
| **Conjure** | Refraction networking: connect to *unused* ISP address space, partner routers detour you | In staging/pre-rollout integration with Tor as of the Dec 2025 anti-censorship roadmap post; new DNS/AMP-cache registration paths. |

### §10.2 Bridge distribution channels

BridgeDB (HTTPS + email), the in-browser **moat** API (fronted, inside Tor Browser's
connection assist), and since 2024–2025 the **Telegram distribution bot**, which became
crucial when Russia enumerated WebTunnel bridges in June 2025.

> **⚠️ GOTCHA:** bridge *secrecy* is the resource under attack, not bridge *capacity*. A
> distribution channel that hands out bridges efficiently to real users also hands them out
> efficiently to a censor who enrolls as a user. Every distribution design is a rate-limiting
> and identity-cost trade, which is why they keep changing.

### §10.3 Case study: the Snowflake DTLS war (Dec 2025 – Apr 2026)

Russia's TSPU began **fingerprint-based blocking of Snowflake on 30 March 2026** — detecting
the `pion/dtls` ClientHello by JA3/JA4 signature after a short delay, rather than blocking IPs.
Connection success collapsed overnight; broker domains stayed reachable.

Mitigations: the **covert-dtls** library (randomized/mimicked ClientHellos) shipped by default
in standalone snowflake-proxy v2.13.1; browser-extension proxies on DTLS 1.3 survived; and
work continued to push covert-dtls into IPtProxy (the transport stack used by Orbot). By late
April 2026 censors were expanding fingerprint coverage (adding a Firefox-DTLS-1.2-mimic
signature) — an explicit arms race in *handshake fingerprinting*, paralleling the web's
JA3/JA4 cat-and-mouse.

*(Sources: net4people/bbs #603; Tor Forum Snowflake Daily Operations threads, March & July
2026.)*

### §10.4 Case study: Iran's "stealth blackout" (June 2025)

During the June 13–25, 2025 Iran–Israel war, Iran ran a DPI/DNS-poisoning/protocol-allowlist
shutdown **without fully withdrawing BGP**. Direct Tor died June 13; **bridge usage surged**;
Snowflake proxies were overwhelmed and users shifted to obfs4; during the total-blackout days
(June 18–21) nearly nothing worked. Usage rebounded *above* pre-war levels after June 25.

Lessons absorbed: keep multiple transports warm, expect TCP-kill/UDP-pass asymmetry, and
expect proxy-pool exhaustion — Snowflake's volunteer pool is now a scaling priority
(Manifest-V3 extension update, NAT-check improvements, staging stress-test infrastructure). A
further multi-day Iranian shutdown began **28 Feb 2026** per the Tor Metrics events feed.

---

## Where to go next

- Bridges as network actors, and how they differ from listed relays: §6.1 →
  `tor-network-consensus-guards-and-paths`.
- Website fingerprinting — the *other* fingerprinting problem, at the guard rather than the
  censor: §11.2 → `tor-attack-literature-and-threat-model`.
- Running a bridge, and the `ClientTransportPlugin` configuration: §13.5 →
  `tor-running-relays-bridges-and-hardware`.
- Tor VPN, Orbot and the transports' place in the 2026 client stack: §12.2 →
  `tor-ecosystem-alternatives-and-governance`.
