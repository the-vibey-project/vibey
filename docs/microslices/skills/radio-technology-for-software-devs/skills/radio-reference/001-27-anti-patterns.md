---
id: skill-27-anti-patterns-5c699a83fa
purpose: 27 anti patterns
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-reference/SKILL.md
requires: []
links: ["skill-28-misconceptions-e9944ffe13"]
---

## §27. Anti-Patterns

```
⚠️ Cranking TX power instead of fixing the antenna or placement (§3, §5)
⚠️ Testing only at short range, line of sight, on the bench (§1)
⚠️ Designing the enclosure before the antenna (§5)
⚠️ Assuming datasheet range figures. They're free-space, ideal, and marketing
⚠️ Treating RSSI as SNR (§7)
⚠️ Ignoring duty-cycle limits until certification (§23)
⚠️ Using max LoRa spreading factor "for range" and killing network capacity (§10)
⚠️ No retry/idempotency at the application layer (§1)
⚠️ Trusting negotiated BLE connection parameters without reading them back (§19)
⚠️ Forgetting ATT MTU negotiation and wondering why BLE throughput is awful (§19)
⚠️ Designing a global product around one region's sub-GHz band (§23)
⚠️ Designing around 2G in 2026 (§24.2), or around 6 GHz 320 MHz channels
   without checking regional allocation (§24.1)
⚠️ Shipping a shared network-wide key (§25)
⚠️ Proximity security based on signal strength (§25)
⚠️ Downsampling without an anti-alias filter (§15)
⚠️ No production RF telemetry, then trying to debug from user reports (§26)
```

---
