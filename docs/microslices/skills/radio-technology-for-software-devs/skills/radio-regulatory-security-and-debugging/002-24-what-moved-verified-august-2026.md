---
id: skill-24-what-moved-verified-august-2026-4179363e5a
purpose: 24 what moved verified august 2026
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-regulatory-security-and-debugging/SKILL.md
requires: ["skill-23-regulatory-63ff32a0bb"]
links: ["skill-25-security-4e22411d6b"]
---

## §24. What Moved — verified August 2026

### 24.1 ⚠️ Wi-Fi 7, 6 GHz, and the Wi-Fi 8 question
**⚠️ Wi-Fi 7 is real and shipping; the interesting facts are about regulation and about
whether it's worth deploying.**

- **⚠️ Wi-Fi Alliance certification began January 2024; as of 2026 enterprise APs are
  widely available and consumer routers start under $100.**
- **⚠️ MLO (Multi-Link Operation) is the genuinely new capability** — **a client uses
  multiple bands SIMULTANEOUSLY for one connection, giving aggregation and, more
  importantly, failover when one band is congested or interfered.** ⚠️ **Implementations
  vary substantially: most clients implement EMLSR or MLMR-STR, and the more complex modes
  are not adopted.** **"Wi-Fi 7 certified" does not tell you which MLO mode you get.**
- **⚠️ Wi-Fi 7 mandates WPA3 and Protected Management Frames** for devices to use 11be
  rates and MLO — **so it forces a security upgrade whether you planned one or not.**
- **Preamble puncturing is mandatory for certification** — ⚠️ **the AP carves an
  interfered portion out of a wide channel and uses the rest, which is a real robustness
  improvement in messy spectrum.**

> **⚠️ GOTCHA — 6 GHz availability is NOT global, and this breaks product plans.**
> ⚠️ **The Wi-Fi Alliance reports 97 countries have adopted the full 6 GHz band or a
> portion of it** — **up from 62 in a prior count** — **but allocations differ: some
> countries have the full 1200 MHz, others only a lower slice.** ⚠️ **Claims that 6 GHz
> harmonization has been achieved are contested, and disparities remain.**
> **⚠️ A device designed around 320 MHz channels in 6 GHz may have nowhere to put them in
> a given market.** **Also note standard-power outdoor 6 GHz requires AFC (Automated
> Frequency Coordination) with GNSS position reporting — an operational dependency that
> did not previously exist in Wi-Fi.**

**⚠️ The honest deployment answer for 2026**: **one analysis puts the AP refresh at
$30,000–50,000 per 100 units while the switch infrastructure to support 802.3bt PoE and
multi-gig uplinks runs $150,000–300,000** — ⚠️ **the APs are the cheap part** — **and
concludes that for most enterprises the ROI isn't there yet in 2026, strengthening in
2027–28 as clients refresh. **Design guidance that recurs: 6 GHz becomes the capacity
layer, 5 GHz becomes the compatibility layer, and 2.4 GHz is for IoT and range.**

**⚠️ Wi-Fi 8 (802.11bn, "Ultra High Reliability")**: **pre-standard silicon sampling from
2026 and prototypes shown at CES 2026**, ⚠️ **but ratification is expected around 2028
and consumer devices toward the end of the decade.** **The notable shift is in the goal:
⚠️ Wi-Fi 8 targets reliability, latency consistency and multi-AP coordination rather than
peak throughput** — **an acknowledgement that the binding constraint is now density and
determinism, not headline speed.** ⚠️ **Do not delay projects for it.**

### 24.2 ⚠️ The IoT connectivity landscape after the 2G/3G sunset
**⚠️ If you are choosing a cellular radio in 2026, the ground has shifted and several
common defaults are now wrong.**

- **⚠️ The 2G/3G sunset is the forcing function.** **Reporting indicates roughly 37
  operators phasing out 2G and 39 retiring 3G across 2025–26**, **stranding millions of
  legacy modules.** ⚠️ **Any new design built around 2G will face forced migration well
  inside its intended service life.**
- **⚠️ The surprise default is LTE Cat-1 / Cat-1 bis, not the LPWAN technologies.**
  **Guidance from operators is that Cat-1 and Cat-1 bis have become strong default choices
  for international fleets** — ⚠️ **because availability and roaming maturity beat
  theoretical efficiency when your devices cross borders.** **Cat-1 bis needs only a
  single antenna, which removes much of the hardware penalty.**
- **⚠️ 5G RedCap is real but not yet the answer.** ⚠️ **It is commercially available in
  only a few markets, module costs remain higher, and operator guidance frames it as "a
  future consideration rather than a universal near-term replacement."** **Plan an upgrade
  path; don't design around it today unless your market has it.**
- **⚠️ Satellite NTN crossed into practicality, and the mechanism matters**: **NTN is
  NB-IoT and LTE-M run over satellite rather than a tower.** ⚠️ **In some cases an
  existing module can gain satellite capability via FIRMWARE UPDATE rather than a hardware
  swap** — **which is why this moved fast.** **Treat it as a complementary resilience
  layer for remote assets, not a primary path** — **and note it needs clear line of sight
  to the satellite, so it does not solve indoor coverage.**
- **⚠️ eSIM/eUICC (SGP.32) is now a mainstream part of the design**, **allowing remote
  operator switching and multi-IMSI — which matters because permanent roaming is
  restricted in a growing number of countries.**

**⚠️ Rough capability bands, reported for 2026 — theoretical maxima, treat as ordering
rather than as achievable throughput:**
```
NB-IoT      ⚠️ ~26 kbps down / ~17 kbps up. Best deep-indoor penetration
            (operators typically allocate it good spectrum). ⚠️ Poor mobility
LoRaWAN     ⚠️ roughly comparable to NB-IoT in data terms; unlicensed, self-run
LTE-M       ⚠️ ~1 Mbps both directions. Mobility, roaming, viable FOTA
LTE Cat-1   ⚠️ ~10 Mbps down / 5 Mbps up. Enough for video
RedCap      higher again; §24.2 caveats apply
```
**⚠️ Indicative connectivity costs cited for 2026**: **LoRaWAN cheapest at scale (no
recurring network fee if you run the gateways), NB-IoT SIM plans from roughly £0.50/month,
LTE-M typically £1–3/month.** ⚠️ **Verify against current quotes; these vary hugely by
volume and region.**
**⚠️ And a design pattern worth stealing**: **combining technologies — NB-IoT for routine
telemetry with LTE-M fallback specifically for firmware updates — is a reported real-world
approach that resolves the NB-IoT FOTA problem without paying LTE-M rates for every
message.**

---
