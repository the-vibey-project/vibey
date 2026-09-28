---
id: skill-2-the-namespace-c69b07636b
purpose: 2 the namespace
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-namespace-resolution-records-and-zones/SKILL.md
requires: ["skill-1-what-dns-is-for-e0585e14c4"]
links: ["skill-3-resolution-31f0d7a086"]
---

## §2. The Namespace

**⚠️ An inverted tree**: ⚠️ **the root (written as a bare dot), then top-level domains, then
second level, and downward.**
**⚠️ A fully qualified domain name ends in that dot** — ⚠️ **`www.example.com.` — and
software that omits it relies on search-list behaviour that causes surprising resolution
differences between machines.**
**⚠️ Labels** are up to 63 octets, ⚠️ **the whole name up to 255, and the practical
character set is letters, digits and hyphens (LDH).**
**⚠️ Internationalized domain names (IDN)** are encoded to ASCII via Punycode —
⚠️ **`xn--` prefixed — and ⚠️ HOMOGRAPH ATTACKS exploiting visually identical characters
across scripts are the security consequence, which is why browsers apply display rules
rather than showing Unicode unconditionally.**
**⚠️ DNS is case-insensitive** for matching, ⚠️ **and 0x20 encoding exploits case
randomization as an anti-spoofing measure** (§7 → `dns-attacks-dnssec-encrypted-dns-and-operations`).
**⚠️ Reserved and special-use names** — ⚠️ **`.local` for mDNS, `.onion` for Tor (§25 → `dns-blockchain-naming-alternatives-assessed`),
`.invalid`, `.test`, and `.internal` reserved for private use precisely so organizations
stop squatting names that might later be delegated.**

---
