---
id: skill-3-buses-and-networking-a343fc18a6
purpose: 3 buses and networking
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-architecture-buses-and-autosar/SKILL.md
requires: ["skill-2-e-e-architecture-71d8441289"]
links: ["skill-4-autosar-c351c3177b"]
---

## §3. Buses and Networking

| Bus | Rate | Use | ⚠️ Notes |
|---|---|---|---|
| **LIN** | 20 kbit/s | Cheap sensors, mirrors, seats | Single wire, master-slave, ⚠️ **very cheap** |
| **CAN** | 1 Mbit/s | ⚠️ **The workhorse for 30 years** | Broadcast, arbitrated, robust |
| **CAN FD** | ⚠️ **~8 Mbit/s** payload | Modern powertrain/chassis | 64-byte payload vs CAN's 8 |
| **CAN XL** | ~10+ Mbit/s | Emerging | 2048-byte payload |
| **FlexRay** | 10 Mbit/s | ⚠️ **Time-triggered, deterministic** | X-by-wire; largely superseded by Ethernet |
| **MOST** | — | Legacy infotainment | ⚠️ **Effectively dead** |
| **Automotive Ethernet** | 100 Mbit/s – multi-gig | ⚠️ **The backbone** | 100BASE-T1, 1000BASE-T1, 10BASE-T1S |
| **SENT / PSI5** | — | Sensor interfaces | Point-to-point |
| **A2B / I2S** | — | Audio | |

### 3.1 CAN — the details that matter
**⚠️ CAN is a broadcast bus with content-based addressing.** There is no destination
address; **the 11-bit (standard) or 29-bit (extended) identifier names the *message*, not
a node.** Every node sees every frame and filters.

**⚠️ Arbitration is non-destructive and priority is the ID**: nodes transmit
simultaneously; dominant (0) beats recessive (1); **the lower ID wins and continues
without corruption.** **Consequences**: **lower ID = higher priority** and
⚠️ **a flood of high-priority traffic can starve low-priority messages** — worst-case
response time analysis is a real design activity (§5 → `auto-real-time-safety-and-cybersecurity`).

**⚠️ CAN has no authentication and no encryption.** Any node on the bus can transmit any
ID. **This is the root of most vehicle attack research**, and the reason for gateways,
network segmentation, and **SecOC** (Secure Onboard Communication — MAC-authenticated
frames with freshness counters, §7 → `auto-real-time-safety-and-cybersecurity`).

**Higher layers**: **J1939** (commercial vehicles — ⚠️ **standardized PGNs and SPNs, unlike
passenger cars where the mapping is proprietary**), **CANopen** (industrial),
**UDS on CAN via ISO-TP** (§8 → `auto-diagnostics-ota-and-adas`).

**⚠️ Bus load** should stay under ~40–50% for latency headroom. **Termination is 120 Ω at
each end of the bus, and exactly two of them** — ⚠️ **wrong termination is a classic
intermittent-failure cause.**

### 3.2 Automotive Ethernet and service-oriented communication
**⚠️ Single twisted pair** (100BASE-T1 / 1000BASE-T1) rather than the four pairs of office
Ethernet — chosen for weight, cost and EMC. **10BASE-T1S** brings a multidrop segment for
low-speed edge devices.

**⚠️ TSN (Time-Sensitive Networking) is what makes Ethernet acceptable for control
traffic**: time synchronization (802.1AS/gPTP), **traffic shaping and scheduled traffic**
(802.1Qbv), frame preemption (802.1Qbu), and redundancy (802.1CB). **Without TSN,
Ethernet is best-effort and you cannot bound latency.**

**⚠️ The paradigm shift is signal-based → service-based.** Classic CAN broadcasts signals
on a fixed schedule defined in a DBC file. **SOME/IP** (and **DDS** in some stacks) offers
**service discovery, request/response, and publish/subscribe** — ⚠️ **which is what lets
you add or change a function without touching every other ECU's communication matrix.**
**This is the enabling change for OTA-updatable features**, and it brings all the
distributed-systems concerns that come with it.

---
