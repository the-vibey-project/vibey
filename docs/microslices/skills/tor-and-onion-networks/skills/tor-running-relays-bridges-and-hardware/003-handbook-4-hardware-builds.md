---
id: skill-handbook-4-hardware-builds-e0052f71ac
purpose: handbook 4 hardware builds
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-running-relays-bridges-and-hardware/SKILL.md
requires: ["skill-handbook-3-networking-patterns-048535e438"]
links: ["skill-handbook-5-verification-monitoring-checklist-6c2221b818"]
---

## Handbook §4. Hardware builds

### §4.1 Raspberry Pi middle relay (the classic)

**BOM**: Pi 4/5 (2–4 GB), decent SD or USB SSD, 5 V/3 A PSU. All-in ≈ $75; ~5 W always-on.

- 64-bit Raspberry Pi OS Lite; the Cortex-A72/A76 have ARMv8 crypto extensions, so AES/POLYVAL
  paths are hardware-assisted (§4.2 → `tor-protocol-circuits-and-cell-cryptography`) — expect
  tens of Mbps of relayed throughput, uplink-willing.
- Use deb.torproject.org apt; set `MaxAdvertisedBandwidth` to ~70% of your real uplink; add
  `AvoidDiskWrites 1` or move to SSD — **SD cards die of log+descriptor churn**.
- Do **not** make it an exit (your home IP takes the abuse mail) — middle or obfs4 bridge.

### §4.2 Travel-router Tor gateway

GL.iNet Mango/Slate/Beryl-class OpenWrt boxes: install `tor` + the §3.3 transparent-proxy
config, or use models/3rd-party firmware with built-in Tor modes (InvizBox sells this
pre-canned).

> **⚠️ GOTCHA:** MIPS/ARM SoCs without crypto extensions cap out in the low tens of Mbps.
> Treat these as *convenience* devices for untrusted Wi-Fi, not high-assurance rigs — the
> network layer is enforced, but endpoint hygiene still lives on your laptop (§11.8 →
> `tor-attack-literature-and-threat-model`).

### §4.3 The Snowflake/bridge headless mini-box

Any idle SBC or old laptop + §2.4 (Snowflake) or §2.2 (obfs4 bridge). This is the cheapest real
help you can give censored users; bridges want residential-looking, stable IPs, so a quiet home
box is *better* than a datacenter for this role.

### §4.4 Two-box isolation gateway (physical Whonix)

Pattern (Whonix's model, in hardware): **Box A** (gateway) — tor + TransPort/DNSPort +
fail-closed nftables; it is the *only* device with a route to the internet. **Box B**
(workstation) — single ethernet link to A, no Wi-Fi, no other interfaces; all its traffic
transits Tor **by physics, not by configuration discipline**. A root-level compromise of B
still can't learn the public IP. Qubes 4.3 + Whonix 18 virtualizes the same topology on one
well-supported machine (§12.2 → `tor-ecosystem-alternatives-and-governance`).

### §4.5 Vault-grade: the SecureDrop architecture (study this even if you never run one)

The reference "serious hardware" onion deployment (docs.securedrop.org):

- **App + Monitor servers** behind dedicated firewall, FDE (LUKS), onion service only — no
  clearnet exposure at all.
- **Air-gapped Secure Viewing Station**: Tails on a machine that *never* networks; submissions
  cross the air gap on dedicated transfer media after decryption on the SVS.
- Admin/journalist Tails sticks with persistence isolated per role; v3 client auth on the onion
  interfaces so the services are invisible without keys.

The transferable lessons for any high-stakes build: **separate the *viewing* environment from
the *receiving* environment by an air gap; authenticate the service itself, not just its users;
FDE + offline identity keys; and assume the box will eventually be seized or rooted — design so
that's survivable.**

---
