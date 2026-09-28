---
id: skill-9-cloud-fleet-and-lifecycle-63d7208431
purpose: 9 cloud fleet and lifecycle
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-industrial-control-connectivity-and-cloud/SKILL.md
requires: ["skill-8-connectivity-3055df089c"]
links: []
---

## §9. Cloud, Fleet, and Lifecycle

### 9.1 Platform landscape (2026)

- **AWS IoT Core** — MQTT broker + device registry, **Device Shadow** (desired/reported
  state), **Jobs** (fleet operations), **Fleet Provisioning**, **Device Defender**
  (behaviour anomaly detection), **SiteWise** (industrial asset models), **Greengrass v2**
  (edge runtime with components). **⚠️ Greengrass V1 support ends 7 October 2026** —
  migrate to V2.
- **Azure IoT** — **IoT Hub** for device-to-cloud at scale (MQTT/AMQP/HTTPS), **DPS** for
  zero-touch provisioning, **Azure Digital Twins**, and **Azure IoT Operations** as the
  newer Arc-enabled, Kubernetes-native edge platform for industrial/OT: an edge-native
  MQTT broker, OPC UA / ONVIF / media / REST / MQTT connectors, dataflows into Event
  Hubs / Event Grid / Microsoft Fabric, and up to **72 hours of offline operation**.
  Recent releases (2510, 2603) added MQTT data persistence, X.509 auth via Device
  Registry, no-code dataflow graphs, cloud-to-edge management actions, and unified health
  reporting. **Note on IoT Central**: a February 2024 console message announcing
  retirement on 31 March 2027 was **retracted by Microsoft as erroneous**; the current
  Azure IoT portfolio is documented as IoT Hub + IoT Operations. Verify status directly
  before making a platform bet.
- **Google Cloud IoT Core is gone** (retired 16 August 2023). There is no managed device
  connectivity service on GCP; users moved to partners (ClearBlade, Litmus) or to AWS/Azure.
  This is the industry's standing reminder that **your device-side protocol should be
  standard MQTT/TLS so the broker is replaceable.**
- **Self-hosted / independent**: **EMQX**, **HiveMQ**, **Mosquitto** (brokers);
  **ThingsBoard** (full platform); **ChirpStack** (LoRaWAN); **Balena** (fleet + container
  OS); **Golioth**, **Memfault** (device management/observability, MCU-focused);
  **Particle** (vertically integrated); **Home Assistant / ESPHome** (prosumer).

**[UNIVERSAL, learned the hard way] Architect so the cloud is replaceable.** Standard MQTT
over TLS with X.509, a documented topic schema, and a payload format you own. Every
proprietary device-side SDK you adopt is a migration cost you're pre-paying.

### 9.2 Identity and provisioning

**The chain of trust:**
```
Silicon root of trust (immutable ROM / fuses)
  └─ verifies bootloader signature (MCUboot, ESP secure boot, TF-M)
       └─ verifies application signature
            └─ application uses a device identity key that NEVER leaves the secure element
                 └─ TLS mutual auth to the cloud presents a device certificate
```

**Where the private key lives** determines your whole security posture:
- **Secure element** (ATECC608, NXP SE050, Infineon OPTIGA): key generated on-chip, never
  extractable, hardware ECDSA. ~$0.50–1.50 BOM. **The right answer for most products.**
- **TrustZone-M + Trusted Firmware-M (TF-M)**: key in the secure partition, PSA Crypto API
  from the non-secure app. No extra BOM; requires an M33/M23-class part and real
  engineering effort.
- **Flash with readout protection**: cheapest, weakest. RDP levels are bypassable with
  fault injection on many parts. Acceptable only when the threat model genuinely tolerates
  a cloned device.
- **PSA Certified** (Level 1/2/3) and **SESIP** are the certification schemes that let you
  make a defensible claim about which of the above you did.

**Provisioning patterns:**
- **Factory-injected certificate**: device gets a unique cert at manufacture from your PKI.
  Most control; requires a secure manufacturing process and an HSM-backed CA.
- **Just-in-time registration / provisioning (JITR/JITP)**: device presents a cert signed
  by your CA; the cloud auto-registers it on first connect. Scales well.
- **Claim-based / fleet provisioning**: device ships with a *shared* bootstrap credential,
  exchanges it for a unique one on first connect. Convenient; the shared credential is the
  weak link — rotate it and bound its privileges hard.
- **DICE** (Device Identifier Composition Engine): derives a layered identity from an
  immutable UDS and the measurement of each boot stage, so identity is cryptographically
  bound to the firmware actually running.

> **⚠️ GOTCHA — RNG entropy.** Key generation and TLS both need a real TRNG. Many MCUs'
> "RNG" is a PRNG seeded from something weak, and some vendor implementations have shipped
> with broken entropy. If keys are generated on-device, use the hardware TRNG, verify it
> exists (not all part variants have it), and run at least a smoke test (NIST SP 800-90B
> health tests) at boot. Duplicate keys across a fleet is a catastrophic, unrecoverable,
> and historically common failure.

### 9.3 OTA update

**[UNIVERSAL] Non-negotiable properties of a firmware update system:**
1. **Authenticated** — signature verified before execution, key in immutable storage.
2. **Atomic** — the device is never left in a half-updated, unbootable state.
3. **Rollback-capable** — automatic revert if the new image fails to confirm health.
4. **Anti-rollback** — a monotonic security counter prevents an attacker re-flashing an
   old, vulnerable-but-validly-signed image.
5. **Power-fail-safe** — losing power at any instant leaves a bootable device.
6. **Staged** — canary → percentage rollout → full fleet, with automatic halt on error-rate
   regression.

**Mechanisms:**
- **A/B (dual bank)**: two full slots; write inactive, swap the boot pointer, confirm.
  Needs 2× flash. Simplest to reason about. **MCUboot** implements swap, overwrite-only,
  and **DirectXIP** (execute from either slot, no copy) modes.
- **Delta / differential**: ship only the binary diff. 10–50× smaller, essential on LPWAN
  and cellular-metered links. Costs the device RAM/CPU for patching and requires exact
  knowledge of the currently-installed version.
- **Bootloader OTA**: updating the bootloader itself is the riskiest operation you can
  perform. Some silicon now provides ROM-level recovery — **ESP-IDF v6.0 added recovery
  bootloader support on ESP32-C5/C61**, where the ROM falls back to a recovery partition
  if the primary bootloader fails to load. Without such a fallback, bootloader OTA has no
  safety net; treat it accordingly.

**Standards**: **RFC 9019** (SUIT firmware update architecture for IoT) and **RFC 9124**
(information model) define a CBOR-based manifest approach; **Uptane** is the
automotive-grade framework (derived from TUF) designed to survive a compromised update
server.

**Post-quantum firmware signing — start planning now.** Firmware signed today may need to
be verified by a device in 2040. **NIST SP 800-208** standardizes the stateful hash-based
signature schemes **LMS** (RFC 8554) and **XMSS** (RFC 8391); NSA's **CNSA 2.0** names
**software/firmware signing as the highest-priority post-quantum transition**, advising
adoption preferentially by 2025 and exclusively by 2030. Note the operational catch:
stateful HBS schemes **must never reuse a one-time key**, so SP 800-208 requires key
generation and signing inside a FIPS 140 Level 3 HSM that cannot export the private key —
meaning "restore the signing key from backup" is a security incident, not a recovery
procedure. **SLH-DSA (FIPS 205)** is the stateless alternative; **ML-DSA (FIPS 204)** is
the general-purpose lattice signature. RFC 9019 itself recommends post-quantum signatures
for immutable ROM bootloader code.

### 9.4 Fleet observability

**[UNIVERSAL] You cannot debug what you cannot see, and you cannot reproduce field
conditions on your desk.** The four things every shipped device should report:
1. **Reset reason** on every boot (§1.3 → `embedded-silicon-and-firmware-models`) — the earliest regression signal you have.
2. **Crash captures**: the fault registers and stacked frame from §5.8 → `embedded-languages-realtime-and-patterns`, plus ideally a
   coredump, symbolicated server-side against the exact build's ELF.
3. **Heartbeat metrics**: uptime, free heap / stack high-water marks, RSSI, battery,
   error counters, task deadline misses.
4. **Structured events**, not free-text logs — a numeric event ID plus binary arguments,
   decoded server-side (the `defmt` / Memfault / trace-recorder approach). This is 10–50×
   cheaper in flash, bandwidth, and CPU than `printf` strings.

**Metrics to alert on**: crash-free-hours per device, watchdog reset rate, OTA success
rate by cohort, connection churn, and battery depletion slope. A firmware regression shows
up in crash-free-hours long before it shows up in support tickets.

**Digital twin / shadow pattern**: cloud holds `desired` and `reported` state; the device
reconciles toward `desired` and publishes `reported`. This makes configuration
eventually-consistent and survivable across offline periods, which naive command-push does
not. Implement it even if you're not on a platform that gives it to you.
