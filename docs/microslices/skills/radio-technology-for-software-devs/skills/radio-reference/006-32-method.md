---
id: skill-32-method-b77b9aacd4
purpose: 32 method
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-reference/SKILL.md
requires: ["skill-31-quick-reference-f09b0dbc77"]
links: []
---

## §32. Method

**§1–§23 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`, `radio-antennas-propagation-noise-and-modulation`, `radio-spread-spectrum-ofdm-access-and-sdr`, `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`, `radio-regulatory-security-and-debugging` and §25–§27 → `radio-regulatory-security-and-debugging` rest on physics, information theory and mature protocol
specifications** — ⚠️ **Friis, Shannon, Nyquist and the dB arithmetic are not going to
change** — sourced from §30. **No verification needed.**

**Two searches were run in August 2026**, on **Wi-Fi 7/8 and 6 GHz status** and **the IoT
connectivity landscape** — ⚠️ **the two areas where a software developer's radio choice
turns on facts that changed recently and where a 2024 answer would produce a bad design.**

**Confidence.** **High** in §3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`, §4 → `radio-intuitions-spectrum-link-budget-and-tradeoffs` and §6 → `radio-antennas-propagation-noise-and-modulation`, which are the sections I'd most want read.
⚠️ **The link budget and the "double the range needs 4× the power" consequence are the
single highest-leverage things a software developer can learn here** — **they turn most
range arguments into arithmetic** — **and the λ/2 multipath null spacing (~6 cm at
2.4 GHz) explains more otherwise-inexplicable field bugs than anything else in the
document.**

**High** in §24.1 → `radio-regulatory-security-and-debugging`'s facts. ⚠️ **The 6 GHz fragmentation point is the one I'd emphasise:
97 countries with full or partial allocation is real progress AND means a design assuming
320 MHz channels may have nowhere to put them.** **The claim that harmonization has been
achieved is explicitly contested in the reporting, and I've said so rather than picking a
side.** **The Wi-Fi 8 timeline (~2028 ratification, pre-standard silicon sampling 2026) is
consistent across sources.** ⚠️ **The enterprise cost figures come from a single vendor
analysis and I've attributed them as such — the ratio (switch infrastructure costing
several times the APs) is the durable insight, not the specific dollar amounts.**

**High** in §24.2 → `radio-regulatory-security-and-debugging`'s direction. ⚠️ **The most decision-relevant and least expected finding
is that LTE Cat-1/Cat-1 bis has become the pragmatic default for international fleets
rather than the LPWAN technologies** — **operator guidance says this directly** — **and
that 5G RedCap is explicitly framed as "a future consideration rather than a universal
near-term replacement."** **The NTN-as-firmware-update point is the mechanism that explains
why satellite IoT moved so fast, and it's worth knowing.**

⚠️ **Sourcing caution, stated plainly**: **much of the IoT connectivity material online is
published by connectivity providers, eSIM platforms and module vendors, all of whom have a
position.** **The throughput figures and the decision-tree logic recur consistently across
independent sources including operator technical documentation, so I've reported those.**
⚠️ **The cost figures (£0.50/month NB-IoT, £1–3/month LTE-M) come from a single vendor and
should be treated as indicative only.** **Where a claim came from one interested source,
I've said so in the text rather than laundering it into the numbers table.**
