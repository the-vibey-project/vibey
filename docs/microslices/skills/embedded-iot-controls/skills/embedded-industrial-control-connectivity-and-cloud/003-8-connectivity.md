---
id: skill-8-connectivity-3055df089c
purpose: 8 connectivity
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-industrial-control-connectivity-and-cloud/SKILL.md
requires: ["skill-7-control-theory-as-practiced-in-firmware-cc2f185320"]
links: ["skill-9-cloud-fleet-and-lifecycle-63d7208431"]
---

## §8. Connectivity

### 8.1 Choosing a radio — the decision table

| Tech | Range | Data rate | Power | Topology | Infra needed | Best for |
|---|---|---|---|---|---|---|
| **BLE** | 10–100 m | 0.125–2 Mbps | very low | star / mesh | phone or gateway | Wearables, sensors, commissioning, local UI |
| **Thread** | 10–30 m/hop, mesh | 250 kbps | low | **mesh, IPv6** | border router | Home/building sensors; Matter's preferred transport |
| **Zigbee** | similar | 250 kbps | low | mesh | coordinator | Legacy lighting/building; Zigbee 4.0 recently released |
| **Wi-Fi (2.4/5)** | 30–100 m | 10s–100s Mbps | **high** | star | AP | Mains-powered, high bandwidth, camera |
| **Wi-Fi HaLow (802.11ah)** | ~1 km | 150 kbps–8 Mbps | medium | star | AP | Sub-GHz IP, long range, moderate rate |
| **LoRaWAN** | 2–15 km | 0.3–50 kbps | **very low** | star-of-stars | gateway + network server | Utility metering, agriculture, private LPWAN |
| **NB-IoT** | cellular | ~30–100 kbps | very low | cellular | carrier | Deep-indoor static meters — **but check carrier support** |
| **LTE-M (Cat-M1)** | cellular | ~300 kbps–1 Mbps | low | cellular | carrier | Mobile assets, voice-capable, best roaming |
| **LTE Cat-1 / Cat-1bis** | cellular | ~10 Mbps | medium | cellular | carrier | The safe global default in 2026 |
| **5G RedCap / eRedCap** | cellular | 10s Mbps | medium | cellular (SA) | carrier | Mid-tier 5G; ~30 operators in 21 countries as of early 2026 |
| **UWB** | 10–50 m | — | medium | — | anchors | Centimetre ranging, secure access |
| **Satellite NTN** | global | very low | medium | — | constellation | Remote assets; store-and-forward with small constellations |

**Cellular reality check for 2026:**
- **2G and 3G are sunset in most markets**; devices still on them need a migration path.
- **NB-IoT has been a commercial underperformer outside China** and carrier support is
  uneven — **AT&T shut down its NB-IoT network**; T-Mobile and Verizon have continued to
  support theirs. Do not design a US product around NB-IoT without written carrier
  confirmation.
- **LTE-M leads on roaming**, which matters for anything that moves across borders.
- **5G RedCap** module pricing and SA network coverage are still the gating factors;
  broader availability is expected through 2027–28.
- **eSIM/eUICC, and specifically SGP.32** (the IoT-focused remote SIM provisioning spec
  finalized in 2024), is now the default expectation for any fleet with a >5-year life or
  multi-country deployment. Design it in; retrofitting carrier flexibility is impossible.

**[UNIVERSAL] Battery-life reality**: the radio dominates. A BLE sensor advertising every
1 s versus every 10 s is roughly a 10× difference in battery life, and no amount of MCU
sleep optimization compensates for a badly chosen connection interval.

### 8.2 BLE — the concepts you actually need

- **GAP** = discovery and connection roles (Peripheral/Central, Broadcaster/Observer).
- **GATT** = the data model: Services contain Characteristics contain Values +
  Descriptors, all addressed by 16-bit (SIG-assigned) or 128-bit (custom) UUIDs.
- **Advertising interval** (20 ms–10.24 s) drives discovery latency and advertiser power.
- **Connection interval** (7.5 ms–4 s, in 1.25 ms units) drives throughput and connected
  power. **Slave latency** lets a peripheral skip N connection events when it has nothing
  to say — this is the single most important BLE power parameter.
- **PHYs**: 1M (default), 2M (double rate, shorter range), Coded S=2/S=8 (long range, 4×
  the airtime).
- **MTU negotiation**: default ATT MTU is 23 bytes (20 bytes of payload). Negotiate up
  (247 is common) or your throughput will be terrible for reasons that look like a bug.
- **Notifications** (no ack, fast) vs **Indications** (acked, one outstanding, slow). Use
  notifications for streaming.

**Bluetooth Core versions [current as of 2026]**: 6.0 (Sept 2024) introduced **Channel
Sounding** — phase-based ranging + round-trip time giving decimetre-level secure ranging,
using 72×1 MHz channels, with ambiguity-free operation to ~150 m. 6.1 (May 2025) added
randomized RPA for privacy. 6.2 (Nov 2025) cut the minimum connection interval from
**7.5 ms to 375 µs** (a big deal for HID and latency-sensitive sensors) and added
amplitude-attack resilience for Channel Sounding. **6.3 was released 6 May 2026**;
the SIG is on a twice-yearly cadence.

### 8.3 Thread and Matter

**Thread**: IPv6 mesh over 802.15.4, with Routers, End Devices, and Sleepy End Devices; a
**Border Router** bridges to the local IP network. Self-healing, no single point of
failure, ~250 kbps.

**Matter**: an *application layer* over IP (Thread, Wi-Fi, or Ethernet) with a Data Model
of Endpoints → Clusters → Attributes/Commands, commissioning via BLE, and a **Fabric**
security model with per-fabric operational certificates (a device can be on several
ecosystems' fabrics simultaneously).

**Current spec state**: **Matter 1.5** (Nov 2025) was the big functional expansion —
**cameras** (WebRTC live A/V, PTZ, detection/privacy zones, STUN/TURN remote access),
**closures**, **soil sensors**, and expanded energy management; **1.5.1** (Mar 2026)
refined cameras/doorbells; **1.6 is reported as the current release as of mid-2026**.
1.4.1/1.4.2 were quality/tooling releases.

**[CONTESTED] Matter's real-world state.** The specification consistently runs ahead of
shipping product and ecosystem app support — a device type can be in the spec for a year
before Apple Home / Google Home / SmartThings expose it usefully. Plan for the
ecosystem-support matrix, not the spec version, and expect commissioning UX to be the
hardest part of your product.

### 8.4 LoRaWAN

- **Classes**: A (uplink-initiated, two short RX windows — lowest power, the default),
  B (scheduled ping slots via beacons — bounded downlink latency), C (continuous RX —
  mains-powered only).
- **Spreading factor** SF7–SF12: higher SF = longer range, exponentially longer airtime,
  lower rate. SF12 packets can be >1 s on air.
- **Duty cycle limits are legal, not advisory** — in EU868, typically 1% per sub-band.
  This *hard-caps* how often you can transmit and how much downlink the network can send.
  Design your telemetry budget around it or your device will be silently throttled.
- **ADR (Adaptive Data Rate)**: the network server tunes SF/power for static devices. Do
  not enable ADR on mobile devices.
- **Join**: **OTAA** (over-the-air activation, derives session keys, supports rejoin —
  always use this) vs **ABP** (hard-coded session keys — a security and frame-counter
  liability; avoid).
- Stack: device → gateway (packet forwarder) → **network server** (ChirpStack, TTN/TTS)
  → application server. Running your own ChirpStack is very achievable and gives you
  data sovereignty.

### 8.5 Application protocols

| Protocol | Transport | Payload | Best for | Watch out for |
|---|---|---|---|---|
| **MQTT 3.1.1 / 5.0** | TCP + TLS | any | Cloud telemetry, UNS, fleet | Broker is a single point of failure; topic design is forever |
| **MQTT-SN** | UDP | any | Sensor networks without TCP | Needs a gateway |
| **CoAP** | UDP + DTLS | CBOR | Very constrained, REST-like | NAT traversal; use Observe for pub/sub-ish |
| **LwM2M** | CoAP | TLV/CBOR/SenML | **Standardized device management** | Fewer cloud integrations than MQTT |
| **HTTP/REST** | TCP + TLS | JSON | Simple, firewall-friendly | Header overhead brutal on cellular/LPWAN |
| **AMQP** | TCP + TLS | any | Enterprise messaging, Azure IoT Hub | Heavy for MCUs |
| **DDS / ROS 2** | UDP multicast | CDR | Robotics, rich QoS policies | Complex; micro-ROS for MCUs |
| **Sparkplug B** | MQTT | Protobuf | Industrial UNS | QoS 0 for DDATA; no retained messages by design |

**MQTT 5 features worth adopting** (and now reachable on MCUs — FreeRTOS's coreMQTT
gained v5 support in the 202604 LTS): **topic aliases** (send the long topic once, then a
2-byte alias — a real win on cellular), **request/response** with correlation data,
**session expiry** and **message expiry intervals**, **shared subscriptions** (load-balance
consumers across a group), and **reason codes** on every ack (so failures are diagnosable
instead of just "disconnected").

**MQTT design rules that prevent regret:**
1. **Design the topic hierarchy once, with one owner.** `{env}/{site}/{area}/{line}/{device}/{signal}`.
   Never put changing values in topics.
2. Use **Last Will and Testament** on every device so "offline" is a first-class state.
3. Publish **retained** messages for state (the current setpoint), non-retained for events.
4. **QoS 1 is almost always right.** QoS 2 costs four round-trips and is rarely justified;
   design your consumers to be idempotent and use QoS 1.
5. Set a **keepalive** appropriate to your network (cellular NAT timeouts often force
   ≤ 240 s) and implement reconnect with **exponential backoff plus jitter** — otherwise
   a broker restart triggers a synchronized thundering herd from your whole fleet.

**Payload encoding on constrained links:**

| Format | Size (typical sensor msg) | Self-describing | Schema needed | Notes |
|---|---|---|---|---|
| JSON | 120 B | yes | no | Debuggable; wasteful |
| **CBOR** (RFC 8949) | ~45 B | yes | no | JSON's data model, binary. Default for CoAP/SUIT |
| MessagePack | ~45 B | yes | no | Similar to CBOR, less standardized |
| **Protobuf** | ~25 B | no | yes | Sparkplug's choice; nanopb for MCUs |
| FlatBuffers | ~30 B | no | yes | Zero-copy read; good for large structures |
| Custom packed struct | ~12 B | no | implicit | Smallest; brittle — version it explicitly |

**[UNIVERSAL] If you roll your own binary format, put a version byte first, and never
reuse a field's meaning.** Field-deployed devices will be on old firmware for years and
your parser must handle every version you ever shipped.

### 8.6 Edge computing and TinyML

**Gateway responsibilities** in a real deployment: protocol translation (Modbus/OPC UA →
MQTT), **store-and-forward** during upstream outage (this is non-negotiable — buffer to
flash with a bounded ring), local rule evaluation for latency-critical reactions,
aggregation/downsampling to control cloud cost, and being the security boundary.

**On-device ML in 2026:**
- **LiteRT for Microcontrollers** (formerly TensorFlow Lite Micro) remains the most
  widely used MCU runtime — the core runtime fits in ~16 KB on a Cortex-M3.
- **ExecuTorch** is the PyTorch-native path, growing fast, strongest where an NPU exists.
- **Arm Ethos-U** micro-NPUs (U55, U65, **U85**) sit beside Cortex-M cores; the **Vela**
  compiler converts LiteRT models to NPU form. U85 adds **transformer operator support**
  and native TOSA, which is what makes small language models on MCU-class hardware
  plausible rather than a stunt.
- **Vendor SDKs**: STM32Cube.AI, NXP eIQ, Renesas e-AI — best per-family performance and
  IDE integration, at the cost of portability.
- **Edge Impulse** and similar: excellent end-to-end tooling for data collection →
  training → deployment; the right choice for prototyping and for teams without ML
  engineers; constraining when you need custom architectures.
- The ecosystem has converged on **ONNX as the interchange format and INT8 quantization
  as the default precision.**
- **The metric that matters is energy per inference**, not inference latency, for anything
  battery-powered. Benchmark with **MLPerf Tiny**, which includes energy measurement.

**Practical TinyML advice**: quantization-aware training beats post-training quantization
when accuracy is marginal; the model is rarely the bottleneck — **feature extraction (FFT,
MFCC, windowing) often dominates both compute and RAM**; and always compute peak RAM as
`max over layers of (input tensor + output tensor + workspace)`, because that number, not
model size, is what fails to fit.

---
