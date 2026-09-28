---
id: skill-31-quick-reference-f09b0dbc77
purpose: 31 quick reference
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-reference/SKILL.md
requires: ["skill-30-books-and-resources-0d4b737530"]
links: ["skill-32-method-b77b9aacd4"]
---

## §31. Quick Reference

### 31.1 Picker
| Question | Answer |
|---|---|
| Will this link work? | ⚠️ **Compute the link budget. Want 10–20 dB margin** (§3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`) |
| Range is bad — what first? | ⚠️ **Antenna, placement, orientation. Not TX power** (§3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`, §5 → `radio-antennas-propagation-noise-and-modulation`) |
| Works on bench, fails in field | ⚠️ **§1 → `radio-intuitions-spectrum-link-budget-and-tradeoffs` checklist: budget, multipath, interference, duty cycle** |
| Intermittent, moves when I move | ⚠️ **Multipath fading. Try antenna diversity** (§6 → `radio-antennas-propagation-noise-and-modulation`) |
| Strong signal, bad throughput | ⚠️ **Interference. Check SNR, look at the spectrum** (§7 → `radio-antennas-propagation-noise-and-modulation`, §26 → `radio-regulatory-security-and-debugging`) |
| Battery life is terrible | ⚠️ **Duty cycle and connection interval, not TX power** (§4 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`, §19 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Long range, tiny data, own the site | ⚠️ **LoRaWAN** (§20 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Long range, tiny data, devices roam | ⚠️ **LTE-M** (§20 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`, §24.2 → `radio-regulatory-security-and-debugging`) |
| Deep indoors, stationary, 10-yr battery | ⚠️ **NB-IoT** (§20 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Global fleet, mixed markets, 2026 | ⚠️ **LTE Cat-1 / Cat-1 bis** (§24.2 → `radio-regulatory-security-and-debugging`) |
| Need reliable firmware updates | ⚠️ **LTE-M, or LTE-M as a fallback layer** (§24.2 → `radio-regulatory-security-and-debugging`) |
| Phone accessory | ⚠️ **BLE** (§19 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Home automation mesh | ⚠️ **Thread + Matter** (§21 → `radio-protocol-stacks-wifi-ble-lpwan-and-gnss`) |
| Want to see what's actually on the air | ⚠️ **RTL-SDR, $30** (§16 → `radio-spread-spectrum-ofdm-access-and-sdr`, §26 → `radio-regulatory-security-and-debugging`) |

### 31.2 Before design freeze
- [ ] ⚠️ **Link budget computed with realistic (not free-space) path loss** (§3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`)
- [ ] ⚠️ **10–20 dB margin at worst-case range and orientation** (§3 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`)
- [ ] Antenna keep-out respected; tuned **in the final enclosure** (§5 → `radio-antennas-propagation-noise-and-modulation`)
- [ ] ⚠️ **Regional band allocations checked for every target market** (§23 → `radio-regulatory-security-and-debugging`, §24.1 → `radio-regulatory-security-and-debugging`)
- [ ] ⚠️ **Duty cycle budget computed against message rate** (§23 → `radio-regulatory-security-and-debugging`)
- [ ] Pre-certified module, or a certification budget and schedule (§23 → `radio-regulatory-security-and-debugging`)
- [ ] ⚠️ **Self-interference tested with all subsystems running** (§7 → `radio-antennas-propagation-noise-and-modulation`)
- [ ] Application-layer retry, idempotency, and backoff (§1 → `radio-intuitions-spectrum-link-budget-and-tradeoffs`)
- [ ] ⚠️ **Per-device keys; replay protection; signed firmware** (§25 → `radio-regulatory-security-and-debugging`)
- [ ] ⚠️ **RSSI/SNR/retry telemetry shipped to production** (§26 → `radio-regulatory-security-and-debugging`)
- [ ] Chosen radio still supported over the product's service life (§24.2 → `radio-regulatory-security-and-debugging`)

---
