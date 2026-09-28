---
id: skill-1-why-wireless-breaks-software-intuitions-7dda61c5b5
purpose: 1 why wireless breaks software intuitions
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-intuitions-spectrum-link-budget-and-tradeoffs/SKILL.md
requires: ["skill-0-routing-fa08d539b9"]
links: ["skill-2-spectrum-and-bands-9563eb026a"]
---

## §1. ⚠️ Why Wireless Breaks Software Intuitions

```
WIRED assumption              ⚠️ RF reality
─────────────────────────────────────────────────────────────────────
The link is up or down        ⚠️ Continuously variable quality. "Up" is a
                              threshold you chose
Bandwidth is provisioned      ⚠️ SHARED medium. Your neighbour's microwave
                              is on your network
Errors are rare              ⚠️ Errors are CONSTANT and being corrected
                              below you. Raw BER may be 1e-3
Latency is stable            ⚠️ Retries, backoff and contention make it
                              heavy-tailed. The p99 is nothing like the mean
It works here → works there   ⚠️ Move it 30 cm and it may not (§6 multipath)
Reproducible                  ⚠️ RF bugs are famously intermittent, weather-
                              dependent, orientation-dependent and
                              time-of-day dependent
Add capacity by adding nodes  ⚠️ More radios in a band = LESS total capacity
```
> **⚠️ GOTCHA — the single most common failure pattern: it works perfectly on the bench,
> then fails in deployment.** ⚠️ **The bench has short range, line of sight, no
> interference, and a fresh battery.** **The field has none of those.** **Almost every
> field failure traces to §3 (budget), §6 → `radio-antennas-propagation-noise-and-modulation` (multipath/fading), §7 → `radio-antennas-propagation-noise-and-modulation` (interference), or §23 → `radio-regulatory-security-and-debugging`
> (duty cycle limits you didn't know applied).**

**⚠️ The mental shift**: **stop thinking of the radio as a pipe and start thinking of it
as a statistical channel.** ⚠️ **Design for packet loss, design for variable latency,
design for the link disappearing entirely for seconds at a time — and make your protocol
idempotent, because you will retransmit.**

---
