---
id: skill-6-industrial-control-and-ot-946a86375a
purpose: 6 industrial control and ot
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-industrial-control-connectivity-and-cloud/SKILL.md
requires: []
links: ["skill-7-control-theory-as-practiced-in-firmware-cc2f185320"]
---

## §6. Industrial Control and OT

### 6.1 The PLC scan cycle [UNIVERSAL]

```
┌──> 1. INPUT SCAN     — snapshot ALL physical inputs into the input image table
│    2. PROGRAM EXEC   — logic runs against the SNAPSHOT, writes to output image
│    3. OUTPUT SCAN    — write output image to physical outputs, atomically
│    4. HOUSEKEEPING   — comms, diagnostics, watchdog
└────┘  repeat; scan time typically 1–50 ms
```
**Why the image tables matter**: within one scan, an input cannot change. This gives
deterministic, race-free logic and is the reason ladder logic is safely writable by people
who are not software engineers. It also means **your effective input latency is up to 2
scan times**, and that a fast physical event shorter than one scan is *invisible* unless
you use a high-speed counter or interrupt-driven I/O module.

**Scan-time discipline**: the scan watchdog trips if a scan exceeds its limit. Long `FOR`
loops, blocking communications, and unbounded string operations in Structured Text are the
usual culprits.

### 6.2 IEC 61131-3 languages

| Language | Form | Best for | Notes |
|---|---|---|---|
| **LD** Ladder Diagram | Relay-logic rungs | Discrete/interlock logic, plant-maintainable | Universal in North America |
| **FBD** Function Block Diagram | Wired blocks | Signal flow, process control, analog chains | Dominant in process industry |
| **ST** Structured Text | Pascal-like text | Math, algorithms, loops, string handling | Where real software engineering happens |
| **SFC** Sequential Function Chart | Steps + transitions | Batch, sequence, start/stop procedures | Maps to Grafcet; great for sequences |
| **IL** Instruction List | Assembly-like | — | **Deprecated in IEC 61131-3 3rd edition** |

**IEC 61499** is the distributed-control successor (event-driven function blocks across
devices), academically influential, commercially niche. **PLCopen** publishes the
motion-control function block standard (`MC_MoveAbsolute`, `MC_Power`, …) and the safety
function block set — these matter because they make motion code portable across vendors.

**Structured Text idioms worth knowing:**
```pascal
(* Edge detection — R_TRIG/F_TRIG are standard function blocks *)
VAR
    rStart   : R_TRIG;
    tonDelay : TON;
END_VAR

rStart(CLK := xStartButton);
IF rStart.Q THEN                      (* rising edge only, once per press *)
    eState := STARTING;
END_IF

(* Timers are function block INSTANCES with state — never re-declare inside a loop *)
tonDelay(IN := (eState = STARTING), PT := T#3S);
IF tonDelay.Q THEN
    eState := RUNNING;
END_IF
```
> **⚠️ GOTCHA — retentive vs non-retentive variables.** `VAR RETAIN` survives a warm
> restart; `VAR PERSISTENT` survives a cold restart/download (vendor semantics vary!).
> Getting this wrong means a machine restarts mid-cycle in an unsafe state after a power
> blip. It is one of the most consequential and least-documented distinctions in PLC work.

### 6.3 Fieldbus and industrial protocols

| Protocol | Layer | Determinism | Typical cycle | Notes |
|---|---|---|---|---|
| **Modbus RTU** | RS-485 serial | poll-only | 10–100 ms | Trivial, ubiquitous, no security, no timestamps |
| **Modbus TCP** | Ethernet | poll-only | 5–50 ms | Same data model over TCP/502 |
| **PROFIBUS DP** | RS-485 | token/master-slave | 1–10 ms | Legacy but enormous installed base |
| **PROFINET RT / IRT** | Ethernet | RT: soft; IRT: hard (µs) | 1–10 ms / <1 ms | Siemens-dominant |
| **EtherNet/IP (CIP)** | Ethernet | implicit I/O w/ RPI | 1–10 ms | Rockwell-dominant |
| **EtherCAT** | Ethernet (special) | **hard, <100 µs, jitter <1 µs** | 50 µs–1 ms | Frame processed **on the fly** by each slave; distributed clocks |
| **CANopen** | CAN | event + sync | 1–10 ms | Object dictionary, PDO/SDO, NMT state machine |
| **IO-Link** | Point-to-point 3-wire | ~2.3 ms cycle | — | Sensor-level; carries parameters + diagnostics, not just a signal |
| **BACnet** | IP/MSTP | none | seconds | Building automation |
| **DNP3 / IEC 61850** | IP/serial | GOOSE: <4 ms | — | Utilities/substation; 61850 GOOSE is multicast, safety-relevant |
| **OPC UA** | TCP/HTTPS/MQTT | not RT (except over TSN) | 50 ms+ | **Information model**, security, discovery |

**EtherCAT's trick, because it explains why it's fast**: the master sends one frame that
travels the ring; each slave reads its output data and writes its input data **into the
passing frame in hardware** as it goes by, with ~1 µs of propagation delay per node. There
is no per-node packet, no switching latency, and no software stack in the loop.
Distributed Clocks then synchronize all nodes to <1 µs, which is what makes coordinated
multi-axis motion possible.

**Modbus register model — the endianness trap [VENDOR chaos, UNIVERSAL pain]:**
```
Data model (all 16-bit addressed, 0-based on the wire, 1-based in docs — the classic
off-by-one):
  Coils              (FC 01 read / 05,15 write)   1-bit  R/W   4x0001-style: 0xxxx
  Discrete Inputs    (FC 02 read)                 1-bit  R     1xxxx
  Input Registers    (FC 04 read)                16-bit  R     3xxxx
  Holding Registers  (FC 03 read / 06,16 write)  16-bit  R/W   4xxxx

A 32-bit float spans TWO registers. There is NO standard for the order. In the wild:
  ABCD  big-endian           (most common, "big-endian word, big-endian byte")
  CDAB  big-endian byte swap ("word-swapped" — extremely common on legacy drives)
  BADC  little-endian byte swap
  DCBA  little-endian
```
**⚠️ GOTCHA:** if a value reads as a plausible-but-wrong number (e.g. 3.6e-38 instead of
25.4), you have a word-order mismatch. Always make word order a *configuration* item in
your Modbus client, never a hard-coded assumption. Document your device's choice in the
register map and publish it — the vendors who don't are the reason integrators hate them.

**A register map convention that saves integrators' lives:**
```
| Addr | Type | Fmt   | Access | Scale | Unit  | Name              | Notes                |
|------|------|-------|--------|-------|-------|-------------------|----------------------|
| 4001 | u16  | -     | R      | 1     | -     | device_id         | 0x1234 constant      |
| 4002 | u16  | -     | R      | 1     | -     | fw_version        | BCD major.minor      |
| 4010 | i32  | ABCD  | R      | 0.001 | °C    | temperature       | -40..125             |
| 4012 | f32  | ABCD  | R      | 1     | kPa   | pressure          | NaN = sensor fault   |
| 4100 | u16  | bits  | R/W    | 1     | -     | control_word      | b0=run, b1=reset     |
| 4200 | u16  | -     | R      | 1     | -     | fault_code        | see appendix         |
```
Publish the scale, the unit, the invalid-value sentinel, and the word format for every
point. That table is the actual product for anyone integrating your device.

### 6.4 OPC UA vs MQTT/Sparkplug — the live architectural debate

**[CONTESTED]** and the most consequential IIoT architecture question right now.

- **OPC UA** is an *information model* first: address space, typed nodes, methods,
  historical access, alarms & conditions, built-in security (X.509, signing, encryption),
  and **companion specifications** that standardize semantics per industry (machine tools,
  robotics, pumps, packaging). Client/server is the mature, widely-implemented mode.
  **OPC UA PubSub (Part 14)** exists in the spec but adoption remains limited relative to
  client/server as of 2026; treat claims of ubiquitous PubSub with scepticism.
- **MQTT** is a *transport*: publish/subscribe, tiny, offline-tolerant, brokered, with no
  opinion whatsoever about payload or topic structure. That freedom becomes topic-tree
  chaos at scale.
- **Sparkplug B** layers the missing OT semantics onto MQTT: a mandated topic namespace
  `spBv1.0/{group}/{msg_type}/{edge_node}/{device}`, Protobuf payloads with typed metrics
  and timestamps, and **birth/death certificates** (NBIRTH/DBIRTH announce the full metric
  set; NDEATH via MQTT Last Will marks a node offline) giving stateful,
  report-by-exception operation without polling.
- **The mainstream 2026 architecture** is not either/or: **OPC UA at the machine (the PLC
  exposes companion-spec-modelled data) → edge gateway translates → MQTT/Sparkplug B to a
  broker → Unified Namespace consumed by MES, historian, analytics, and cloud.** OPC UA
  supplies meaning; MQTT supplies distribution.
- **Sparkplug's real trade-off**: it deliberately forgoes MQTT retained messages and uses
  QoS 0 for DDATA in favour of deterministic state via birth/death. That is a *feature*
  for OT state management and a *limitation* if you need guaranteed delivery of every
  sample. Know which you need.

**Unified Namespace (UNS)** is the architectural idea that there should be exactly one
real-time, hierarchically-organized, event-driven source of truth for the whole
enterprise's current state — typically an MQTT broker with an ISA-95-shaped topic tree
(`enterprise/site/area/line/cell/...`) — that every system publishes to and subscribes
from, replacing point-to-point integrations. It is genuinely transformative when done
well and a mess when the topic namespace isn't designed up front by one owner.

### 6.5 Purdue model / ISA-95 and the IT/OT boundary

```
Level 5  Enterprise (ERP)                        ─┐
Level 4  Site business planning (MES/ERP edge)    │ IT
─────────────────────── DMZ ──────────────────────┤ ← the boundary that matters
Level 3  Site operations (historian, MES, OPC)   ─┤
Level 2  Supervisory (SCADA, HMI)                 │ OT
Level 1  Control (PLC, DCS, safety PLC)           │
Level 0  Process (sensors, actuators)            ─┘
```
**[UNIVERSAL] OT inverts the CIA triad.** IT prioritizes Confidentiality → Integrity →
Availability. OT prioritizes **Safety → Availability → Integrity → Confidentiality**. A
control that "fails secure" by locking out an operator during a process upset can turn a
deviation into an incident. This single inversion explains most IT/OT friction.

**Practical boundary controls**: an industrial DMZ with no direct L3→L4 protocol
traversal, replicated historians rather than direct database access, **unidirectional
gateways / data diodes** where the risk justifies it, and jump hosts with session
recording for vendor access. Colonial Pipeline is the reference lesson on why the *billing
side* being compromised can stop the *operational* side (§16 → `embedded-reference`).

### 6.6 Time-Sensitive Networking (TSN)

Standard Ethernet is non-deterministic (queuing, bursts). TSN is a set of IEEE 802.1
amendments that make it deterministic while keeping standard hardware:
- **802.1AS** — generalized PTP time synchronization (sub-µs across the network).
- **802.1Qbv** — time-aware shaper: gated transmission windows per traffic class. This is
  the core scheduling mechanism.
- **802.1Qbu / 802.3br** — frame preemption: a high-priority frame interrupts a
  best-effort frame mid-transmission.
- **802.1Qci** — per-stream filtering and policing (protects against a babbling node).
- **802.1CB** — frame replication and elimination for reliability (seamless redundancy).

**OPC UA over TSN** is the "converged network" vision: one Ethernet infrastructure
carrying deterministic control traffic and IT traffic. Real, deployed in automotive and
some machine builders; still expensive and integration-heavy for general industry.

---
