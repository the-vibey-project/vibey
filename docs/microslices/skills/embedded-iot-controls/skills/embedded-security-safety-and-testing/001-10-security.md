---
id: skill-10-security-e8b2a6af03
purpose: 10 security
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-security-safety-and-testing/SKILL.md
requires: []
links: ["skill-11-functional-safety-37c9804c6f"]
---

## §10. Security

### 10.1 Threat model for a connected device

Attack surfaces, roughly in order of how often they're actually used:
1. **Default/shared credentials** — the Mirai lesson. Still the #1 real-world IoT
   compromise vector.
2. **Unauthenticated or downgradeable firmware update** — full device takeover, fleet-wide.
3. **Cloud API / companion app** — often weaker than the device; horizontal authorization
   bugs let you control someone else's device by changing an ID.
4. **Exposed debug interfaces** — JTAG/SWD unlocked, UART console with a root shell, test
   pads on the PCB.
5. **Network-facing stack bugs** — Ripple20/URGENT-11-class vulnerabilities in third-party
   TCP/IP stacks that ship inside thousands of products with no SBOM to find them.
6. **Firmware extraction** → hard-coded secrets, shared keys, API endpoints.
7. **Physical/fault injection** — voltage/clock glitching to bypass secure boot, side
   channels to extract keys. Real, and demonstrated against mainstream MCUs.
8. **Supply chain** — a compromised dependency, a malicious contract manufacturer flashing
   extra firmware.

### 10.2 Cryptography on constrained devices

- **Symmetric**: **AES-GCM** or **ChaCha20-Poly1305** (better when there's no AES
  accelerator — it's fast in software on 32-bit cores). Always AEAD; never
  encrypt-without-authenticate.
- **Asymmetric**: **ECC P-256 (secp256r1)** or **Curve25519/Ed25519**. RSA-2048+ is
  painfully slow and large on MCUs; avoid for new designs.
- **Hashing**: SHA-256. SHA-1 and MD5 are dead for security purposes (fine as
  non-security checksums, but use CRC for that).
- **Integrity without security**: **CRC-32** for storage/transport error detection.
  ⚠️ A CRC is **not** a security control — it's trivially forgeable. Philip Koopman's work
  on checksum/CRC selection is the reference for choosing a polynomial with adequate
  Hamming distance for your message length; the default polynomial is often *not* the best
  one for short messages.
- **Hardware accelerators**: use them, but verify constant-time behaviour and that the
  driver doesn't leak keys into general RAM.

**TLS/DTLS on MCUs**: **mbedTLS** (widely integrated, PSA Crypto API), **wolfSSL** (small,
commercially supported, FIPS options), **TinyDTLS** (minimal CoAP use). Footprint reality:
a trimmed TLS 1.2/1.3 client with ECDHE-ECDSA-AES128-GCM needs roughly **20–40 KB flash
and 15–30 KB RAM** — the RAM is dominated by the record buffer (16 KB max record; use
`MBEDTLS_SSL_MAX_CONTENT_LEN` and the max-fragment-length extension to cut it).

> **⚠️ GOTCHA — the certificate validation triad.** Devices routinely fail at one of:
> (a) not validating the chain at all, (b) validating the chain but not the hostname,
> (c) having no reliable clock, so expiry checks pass anything. All three are common.
> Fix (c) by getting time from a trusted source before the first TLS handshake, or by
> using a boot-time-anchored monotonic check plus certificate pinning.

### 10.3 Secure boot and debug lockdown

**Secure boot chain**: immutable ROM verifies the bootloader signature against a public
key hash burned into **eFuses**; the bootloader verifies the application. The root of trust
must be **immutable** — a "secure boot" whose key can be changed by software isn't one.

**Debug port lockdown** is a lifecycle decision:
- Development: open SWD/JTAG.
- Production: **permanently disable** or require authenticated debug (ADAC / Arm Debug
  Authentication, or vendor equivalents like STM32 RDP Level 2).
- **⚠️ GOTCHA**: RDP Level 2 on many STM32 parts is **irreversible** — you cannot ever
  re-open the part, which means you cannot do failure analysis on returns. Plan a
  deliberate policy: a small number of "engineering" units at RDP1, production at RDP2, or
  use authenticated debug unlock where the silicon supports it.
- Remember the **UART console**. A locked JTAG next to an unauthenticated shell on a test
  header is theatre.

**TrustZone-M / TF-M**: partitions the MCU into Secure and Non-Secure worlds with
hardware-enforced boundaries (SAU/IDAU). **Trusted Firmware-M** provides the reference
secure-side implementation with PSA services: Crypto, Internal Trusted Storage, Protected
Storage, Initial Attestation. This is the standards-track answer for "keys and secrets
isolated from application bugs" on M33/M23.

### 10.4 Regulation — the 2026 compliance landscape

This section is time-sensitive. Verify before relying on it.

**EU Cyber Resilience Act (CRA), Regulation (EU) 2024/2847** — horizontal, applies to
essentially every "product with digital elements" placed on the EU market, from any
manufacturer worldwide.
- Entered into force **10/11 December 2024**.
- **11 June 2026** — conformity assessment body notification provisions apply.
- **11 September 2026** — ⚠️ **vulnerability and incident reporting obligations apply.**
  Manufacturers must report **actively exploited vulnerabilities** and **severe incidents**
  via the ENISA **CRA Single Reporting Platform**: **early warning within 24 hours**, full
  notification within 72 hours, final report within 14 days (vulnerabilities, once a fix
  exists) or one month (severe incidents). **This applies to products already on the
  market**, including ones shipped years ago.
- **11 December 2027** — full application: essential cybersecurity requirements, secure-
  by-default configuration, security update provision across the support period,
  **SBOM**, technical documentation, conformity assessment, CE marking.
- The Commission published practical guidance on 27 July 2026.
- **Practical implication for August 2026**: the reporting clock starts in three weeks.
  If a product doesn't have an SBOM, a monitored vulnerability intake channel, a CVE
  triage process, and a named responsible person, that is an *immediate* gap, not a 2027
  gap.

**EU Radio Equipment Directive (RED) Article 3(3)(d)(e)(f)** via Delegated Regulation
2022/30 — **mandatory since 1 August 2025** for internet-connectable radio equipment.
Harmonised standards **EN 18031-1** (network protection → 3.3(d)), **EN 18031-2** (privacy
and personal data → 3.3(e)), **EN 18031-3** (financial fraud → 3.3(f)) were cited in the
OJ in January 2025 **with restrictions** (Implementing Decision (EU) 2025/138).
⚠️ Those restrictions matter: certain clauses (notably around user ability to skip
password setup and some parental-control provisions) **do not confer presumption of
conformity**, so products touching them still need a **Notified Body**. There is **no
grace period** — products non-compliant in August 2025 remain non-compliant now.
EN 18031 maps onto **ETSI EN 303 645** (the consumer IoT baseline) provisions, and is
also the foundation for future CRA harmonised standards.

**Other regimes worth knowing:**
- **ETSI EN 303 645** — the consumer IoT security baseline (no universal default
  passwords, vulnerability disclosure, keep software updated, securely store credentials…).
- **NIST IR 8259 / NISTIR 8425** — US device manufacturer capability guidance; underpins
  the **US Cyber Trust Mark** consumer labelling scheme.
- **UK PSTI Act** — in force; bans default passwords, mandates a disclosure policy and a
  published support period.
- **IEC 62443** — the industrial series. **62443-4-1** = secure development lifecycle for
  product suppliers; **62443-4-2** = component technical requirements (seven Foundational
  Requirements: IAC, UC, SI, DC, RDF, TRE, RA); **62443-3-2** = risk assessment and
  zones/conduits design; **62443-3-3** = system requirements; **62443-2-1** = asset owner
  programme (2nd edition Aug 2024). Security Levels **SL 1–4** are assigned per
  zone/conduit, not per plant. It is referenced by NIS2, TSA pipeline directives, and
  increasingly written directly into procurement contracts — and it is the natural
  technical framework onto which CRA obligations map for industrial products.
- **UNECE R155/R156** — automotive cybersecurity management system and software update
  management system; type-approval prerequisites.
- **FDA premarket cybersecurity guidance / FD&C §524B** — US medical devices must ship an
  SBOM and a vulnerability management plan.
- **SBOM formats**: **SPDX** and **CycloneDX**. **VEX** documents let you state
  "component X contains CVE-Y but this product is not affected because…" — essential once
  you have an SBOM, or you'll drown in irrelevant CVEs.

### 10.5 A practical security baseline

Minimum bar for a connected product in 2026:
- [ ] Unique per-device credentials; **no shared or default passwords, ever**
- [ ] Secure boot with an immutable root of trust
- [ ] Signed OTA with rollback protection and an anti-rollback counter
- [ ] Private keys in a secure element or TrustZone-isolated storage
- [ ] TLS 1.2+ with full chain **and hostname** validation, and a trustworthy clock
- [ ] Debug interfaces locked in production (including UART); documented policy
- [ ] SBOM generated at build time, stored per release, monitored against CVE feeds
- [ ] Published vulnerability disclosure policy + a monitored intake address
- [ ] Documented support period and a working path to ship a patch to every unit
- [ ] Threat model written down and reviewed when the architecture changes
- [ ] Reporting runbook ready for the CRA 24/72-hour clocks

---
