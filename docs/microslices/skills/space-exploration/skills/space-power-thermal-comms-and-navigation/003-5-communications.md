---
id: skill-5-communications-95cae00d64
purpose: 5 communications
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-power-thermal-comms-and-navigation/SKILL.md
requires: ["skill-4-thermal-control-f8b3d24d90"]
links: ["skill-6-navigation-and-autonomy-3c0bd6faa0"]
---

## §5. Communications

### 5.1 The link budget

**[DURABLE] The equation that governs every deep space mission:**
```
P_r = P_t + G_t + G_r − L_fs − L_other
L_fs = 20 log₁₀(4πd/λ)          free-space path loss
G = η (πD/λ)²                    dish gain
```
**⚠️ Path loss scales as `d²`, so data rate falls as `1/d²`** for fixed everything else.
**Mars at opposition vs. conjunction varies by ~7× in distance — about 17 dB.**

**The `C/N₀` and achievable rate**:
```
C/N₀ = EIRP + G/T − L_fs − k       (k = −228.6 dBW/K/Hz)
R_max ≈ (C/N₀) / (E_b/N₀ required)
```
**⚠️ `G/T` — receive gain over system noise temperature — is the single figure of merit for
a ground station**, and it's why cryogenically-cooled LNAs matter.

### 5.2 What that means in practice

**Coding buys enormous margin.** ⚠️ **Turbo and LDPC codes operate within ~1 dB of the
Shannon limit**, versus the ~9 dB gap of uncoded BPSK — **an order of magnitude in
effective data rate for free, and the reason deep space missions return anything at all.**
Concatenated Reed–Solomon + convolutional was the older standard (Voyager).

**Bands**: **S** (2 GHz, robust, low rate), **X** (8 GHz, the workhorse), **Ka** (32 GHz,
⚠️ **~4× the gain of X for the same dish, but rain-attenuated and pointing-critical**),
**optical** (⚠️ **1550 nm; orders of magnitude more gain from the tiny wavelength, at the
cost of needing near-arcsecond pointing and cloud-free ground sites**).

**⚠️ The numbers that show the problem**: Voyager 1 at ~24 billion km returns **~160 bit/s**
on a 3.7 m dish with 23 W. New Horizons at Pluto returned **~1–2 kbit/s** and took
**16 months** to downlink the encounter data. **Data volume, not instrument capability, is
frequently the limiting factor for outer-planet science.**

### 5.3 Light-time and its consequences

```
Moon        1.3 s one-way       ⚠️ teleoperation marginal but possible
Mars        3–22 min            ⚠️ teleoperation impossible
Jupiter     33–53 min
Saturn      68–84 min
Voyager 1   ~23 hours
```
**⚠️ Round-trip light time to Mars exceeds 40 minutes at conjunction.** **This is the
single reason surface robots must be autonomous** (§6.2) and why EDL must be entirely
self-contained — the spacecraft has landed or crashed before Earth knows it entered.

### 5.4 Relay architecture
**⚠️ Mars surface missions overwhelmingly return data via orbiters** (MRO, MAVEN, TGO)
rather than direct-to-Earth: an orbiter passes overhead at ~400 km instead of 200 million,
and the `1/d²` advantage is astronomical. **Surface assets carry small UHF radios; the
orbiter carries the big X/Ka link.** **The Deep Space Network** (Goldstone, Madrid,
Canberra — 120° apart for continuous coverage) is the ground segment, ⚠️ **and it is
oversubscribed, which is a real and under-appreciated constraint on mission planning.**

---
