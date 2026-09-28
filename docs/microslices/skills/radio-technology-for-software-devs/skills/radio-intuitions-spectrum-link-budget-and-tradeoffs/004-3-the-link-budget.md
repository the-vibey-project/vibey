---
id: skill-3-the-link-budget-0834845d0c
purpose: 3 the link budget
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-intuitions-spectrum-link-budget-and-tradeoffs/SKILL.md
requires: ["skill-2-spectrum-and-bands-9563eb026a"]
links: ["skill-4-the-range-rate-power-triangle-171fbe90d9"]
---

## §3. ⚠️ The Link Budget

**⚠️ This is the tool. Learn it and most wireless design becomes arithmetic.**

```
⚠️ Received power (dBm) = TX power (dBm)
                        + TX antenna gain (dBi)
                        − path loss (dB)
                        − cable/connector/body losses (dB)
                        + RX antenna gain (dBi)

⚠️ LINK MARGIN = received power − receiver sensitivity
   ⚠️ Want AT LEAST 10–20 dB margin for a real deployment. Zero margin
   means it works on a good day, in one orientation, and nowhere else
```

**⚠️ Decibels — get comfortable, because everything is in dB and it's all multiplication
turned into addition:**
```
⚠️ +3 dB  ≈ 2×  power      ⚠️ −3 dB  ≈ half power
⚠️ +10 dB = 10× power      ⚠️ +20 dB = 100×
dBm = dB relative to 1 milliwatt.  ⚠️ 0 dBm = 1 mW.  20 dBm = 100 mW
dBi = antenna gain vs an isotropic radiator
⚠️ Typical numbers: BLE TX 0–10 dBm · Wi-Fi 15–20 dBm · LoRa 14 dBm (EU)
⚠️ Receiver sensitivity: Wi-Fi ~−90 dBm · BLE ~−95 dBm · LoRa ~−137 dBm
```

**⚠️ Free-space path loss (Friis)** — **the optimistic case, and reality is always worse:**
```
FSPL(dB) = 20·log₁₀(d) + 20·log₁₀(f) + 32.44   (d in km, f in MHz)

⚠️ CONSEQUENCE 1: doubling distance costs 6 dB. Every time
⚠️ CONSEQUENCE 2: doubling FREQUENCY also costs 6 dB — which is why the
   same power gets you less range at 5 GHz than 2.4 GHz
⚠️ CONSEQUENCE 3: to DOUBLE your range you need 4× the power (+6 dB).
   To 10× your range you need 100× the power
```
> **⚠️ GOTCHA — "just turn up the transmit power" is almost always the wrong answer, and
> the arithmetic above is why.** ⚠️ **6 dB of extra TX power (4× the battery drain, and
> possibly illegal — §23 → `radio-regulatory-security-and-debugging`) buys you double the range in free space and much less
> indoors.** **Meanwhile 6 dB of antenna improvement is free at runtime, and moving the
> antenna away from a ground plane or a battery can be worth 10 dB.**
> **⚠️ Sensitivity, antenna and placement beat power almost every time.**

**⚠️ Real-world loss is far worse than free space**: **indoor path loss exponents run
roughly 3–5 rather than 2**; ⚠️ **a wall costs perhaps 3–15 dB, concrete or foil-backed
insulation far more, and a human body 3–10 dB and moving.**

---
