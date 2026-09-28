---
id: skill-25-what-s-live-checked-august-2026-feff1b3f24
purpose: 25 what s live checked august 2026
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-reference/SKILL.md
requires: []
links: ["skill-26-misconceptions-600f2d2076"]
---

## §25. What's Live — checked August 2026

### 25.1 ⚠️ Wi-Fi 8: reliability instead of speed, and hardware ahead of the standard
**⚠️ §6 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`'s next generation, and it represents a genuine change of philosophy.**

- **⚠️ THE SHIFT.** ⚠️ **IEEE 802.11bn, marketed as Wi-Fi 8 and named Ultra High Reliability
  (UHR), is the first generation NOT primarily chasing peak throughput.** ⚠️ **Samsung
  Research summarizes the trajectory bluntly: from 2 Mbps in legacy 802.11 to 36 Gbps in
  Wi-Fi 7 by adding bandwidth, higher modulation and spatial streams — and 802.11bn shifts
  focus beyond peak performance in ideal conditions to stable performance at coverage
  edges.**
- **⚠️ THE PAR TARGETS, which are the honest specification of ambition**: ⚠️ **at least 25%
  higher throughput in CHALLENGING signal conditions, 25% lower latency at the 95th
  PERCENTILE, and 25% fewer dropped packets — all relative to Wi-Fi 7.**
  ⚠️ **Note these are percentile and edge-case targets, not peak-rate targets. Peak
  bandwidth is reported as broadly unchanged.**
- **⚠️ THE NEW MECHANISMS** are mostly about APs cooperating rather than competing:
  ⚠️ **Multi-AP Coordination (MAPC), Coordinated Spatial Reuse (Co-SR — APs adjusting
  transmit power so they can share a channel simultaneously), Dynamic Sub-Channel Operation
  (splitting wide channels into narrower ones to serve more devices), Enhanced Long Range,
  and Distributed Resource Units.** ⚠️ **MediaTek trials are reported suggesting Co-SR could
  raise system throughput 15–25%.**
- **⚠️ It retains** 2.4/5/6 GHz, 320 MHz channels and Multi-Link Operation from Wi-Fi 7.

> **⚠️ GOTCHA — products are arriving YEARS before the standard, and this matters for buying
> decisions.** ⚠️ **IEEE final approval is targeted for 2028, with certification reported
> around January 2028; meanwhile draft-based hardware was shown at CES 2026 by multiple
> chipmakers and router brands, with retail products reported as possible from summer or
> late 2026.**
> ⚠️ **Draft progress through 2026 is publicly tracked and is genuinely incremental — Draft
> 1.3 approved in January, Draft 1.4 in March, and Draft 2.0 reported slipping from May to
> July 2026.**
> **⚠️ The consistent advice across sources, including ones with no product to sell, is that
> Wi-Fi 7 is the mature standard for this cycle and deferring a refresh to wait for Wi-Fi 8
> means waiting through a draft-hardware period into a 2028 certification window and then
> again for clients.**
> ⚠️ **The stated exceptions are exactly the environments UHR targets: very high AP density,
> heavy roaming, deterministic latency requirements, and large fleets of low-power uplink
> devices — those operators should track it and treat draft hardware as evaluation, not
> production.**

**⚠️ My reading**: ⚠️ **this is the most honest generational pitch Wi-Fi has made in years,
because §1 → `wireless-propagation-link-budget-modulation-antennas-and-spectrum`'s core complaint — that advertised rates never resemble real experience — is
finally what the standard is targeting.** ⚠️ **One source puts it well: Wi-Fi 8 will not
make every client faster, it is designed to make Wi-Fi less fragile.**

### 25.2 ⚠️ Bluetooth Channel Sounding: ranging without UWB hardware
**⚠️ §14 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`'s capability arriving on the radio everything already has — and §22 → `wireless-security-coexistence-and-positioning`'s relay-attack
problem being addressed properly.**

- **⚠️ WHAT IT IS.** ⚠️ **Channel Sounding is the flagship feature of Bluetooth Core 6.0,
  adopted August 2024.** ⚠️ **The SIG describes it as enabling SECURE FINE RANGING between
  two devices, designed to meet the accuracy and security requirements of applications like
  digital keys and Find My networks.**
- **⚠️ HOW, and the two methods are complementary.** ⚠️ **Phase-Based Ranging and
  Round-Trip Timing, usable independently or together — RTT for coarse range, phase for
  precision.** ⚠️ **One technical description explains the mechanism as synthesizing a wide
  effective bandwidth from many narrow 1 MHz channels using super-resolution techniques,
  which is how a narrowband radio achieves fine ranging at all.**
- **⚠️ ACCURACY CLAIMS VARY BY SOURCE AND SHOULD BE READ CAREFULLY.** ⚠️ **Reported figures
  range from "tens of centimetre-level" to "±10 cm at 10 m" to "centimetre-level over
  distances up to roughly 150 metres."** ⚠️ **The conservative reading is sub-metre
  reliably, with centimetre-class accuracy under good conditions — and independent research
  on performance in complex indoor environments is active, which itself indicates the
  hard cases are not solved.**
- **⚠️ THE SECURITY PROPERTY IS THE POINT, and it is §22 → `wireless-security-coexistence-and-positioning`'s problem directly.** ⚠️ **RSSI
  proximity is an educated guess that relay attacks defeat trivially; Channel Sounding
  provides distance bounding described as relay-attack-resistant via cryptographic
  frequency hopping.** ⚠️ **Core 6.2 is reported to add anomaly detection against
  amplitude-based spoofing.**

> **⚠️ GOTCHA — the strategic significance is that this challenges UWB on UWB's home
> ground.** ⚠️ **One description states it plainly: centimetre-accurate measurement using
> the standard BLE 2.4 GHz radio, WITHOUT requiring UWB hardware.**
> ⚠️ **For product designers that changes the §14 → `wireless-thread-matter-lora-cellular-uwb-and-choosing` versus §8 → `wireless-wifi-bluetooth-ble-nfc-and-rfid` decision materially — if the
> radio you already fitted for connectivity can also do secure ranging, the case for a
> second dedicated radio narrows considerably.** **⚠️ I would not assume it fully matches
> UWB's accuracy or multipath resilience; the honest position is that it is good enough for
> a large set of applications that previously needed UWB.**

**⚠️ Deployment status**: ⚠️ **silicon vendors have shipped native Channel Sounding
hardware, with adoption reported reaching flagship and high-end smartphones; Nordic
Semiconductor expects expansion into commercial and industrial use in 2026 for sub-metre
asset tracking and worker-safety geofencing; Samsung anticipates digital key and precise
device discovery use cases.**
**⚠️ Note the SIG's cadence**: ⚠️ **Core 6.0 (Aug 2024), 6.1 (May 2025), 6.2 (late 2025),
6.3 (May 2026) — roughly twice yearly, refining rather than replacing.** ⚠️ **And §8 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`'s
point recurs: features have decoupled from version numbers, which is why the SIG encourages
advertising "supports Auracast" rather than a core version.**
**⚠️ Sourcing note: the Bluetooth SIG is describing its own specification, and several
sources are silicon vendors and paywalled market-research summaries.** ⚠️ **The
specification facts and the mechanism are solid; the accuracy figures and adoption
percentages are vendor and analyst claims, and I have reported the range rather than
picking the most flattering number.**

---
