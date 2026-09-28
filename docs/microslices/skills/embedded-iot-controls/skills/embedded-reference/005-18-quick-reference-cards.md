---
id: skill-18-quick-reference-cards-65d850090c
purpose: 18 quick reference cards
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-7b577945d8"]
links: ["skill-19-sources-and-method-7160b9248c"]
---

## §18. Quick Reference Cards

### 18.1 "Why doesn't my peripheral work?" — in diagnostic order
1. Is the **peripheral clock enabled**? (+ dummy read-back after enabling)
2. Is the **pin muxed** to the right alternate function, at the right speed/pull?
3. Is the peripheral **out of reset** and **enabled**?
4. For SPI: **right mode** (try all four). For I²C: **pull-ups sized**, right 7-bit address
   (shifted or not — datasheets disagree).
5. Is the **interrupt enabled** in both the peripheral **and** the NVIC?
6. Is the **ISR name** exactly the weak symbol from the startup file? (A typo silently
   leaves the default infinite-loop handler in the vector table.)
7. Is **DMA** configured with the right stream/channel/request, direction, and increment
   modes — and is the buffer **32-byte aligned and cache-maintained** on an M7?
8. Scope it. The bus either has edges or it doesn't.

### 18.2 "Why does it crash randomly?"
Stack overflow → interrupt priority misconfiguration (FreeRTOS `configMAX_SYSCALL...`) →
race on a shared variable → buffer overrun → uninitialized pointer/variable → cache
coherency with DMA → power supply droop/brown-out → flash corruption from an unsafe write
→ hardware errata. Enable the specific fault handlers (§5.8 → `embedded-languages-realtime-and-patterns`) and MPU stack guards before
guessing.

### 18.3 "Why is battery life bad?"
Measure first, with a current probe, at µs resolution. Then check: never actually entering
deep sleep (a peripheral or debugger holds a clock domain); tickless idle not enabled;
floating GPIOs; regulator/pull-up quiescent current; radio interval too aggressive;
retries because of poor RF; a chatty logging path; wake-up sources firing more often than
you think.

### 18.4 Numbers worth memorizing
- Cortex-M exception entry: **~12 cycles** (16 with FP stacking); tail-chained: **~6**.
- 32-bit ms counter rolls over at **49.7 days**; 32-bit µs at **71.6 minutes**.
- I²C standard/fast/fast+/high-speed: **100 k / 400 k / 1 M / 3.4 M**.
- CAN classic max **1 Mbps**; CAN-FD data phase up to **8 Mbps**.
- BLE connection interval range **7.5 ms – 4 s** (1.25 ms units); **375 µs** minimum from
  Bluetooth 6.2.
- Default BLE ATT MTU **23 bytes** (20 payload) until negotiated.
- LoRaWAN EU868 duty cycle typically **1%** per sub-band — a legal limit.
- MQTT QoS 1 = 2 messages; QoS 2 = 4 messages.
- Rate-monotonic utilization bound: **69.3%** as N→∞.
- Control loop sampling: **10–20×** the desired closed-loop bandwidth.
- Cascade loops: each inner loop **5–10×** faster than the one enclosing it.
- Cache line on Cortex-M7: **32 bytes** — align every DMA buffer to it.
- TLS 1.2/1.3 client on an MCU: roughly **20–40 KB flash, 15–30 KB RAM**.
- LiteRT-Micro core runtime: **~16 KB** on Cortex-M3.
- UART at 115200: **~87 µs per character**. Never in an ISR.

### 18.5 Review checklist for someone else's firmware
- [ ] Is there a hardware seam that makes logic host-testable? (§5.1 → `embedded-languages-realtime-and-patterns`)
- [ ] Any `delay()`, blocking call, or `malloc` in a real-time path? (§5.10 → `embedded-languages-realtime-and-patterns`)
- [ ] Every `while(!flag)` bounded by a timeout?
- [ ] Every return code checked?
- [ ] Time comparisons rollover-safe? (§5.5 → `embedded-languages-realtime-and-patterns`)
- [ ] ISRs short, non-blocking, correct `FromISR` APIs, correct priorities? (§5.7 → `embedded-languages-realtime-and-patterns`)
- [ ] Shared variables `volatile` **and** atomic/locked? (§4.3 → `embedded-languages-realtime-and-patterns`)
- [ ] Mutexes (with PI) for locking, not binary semaphores? (§2.4 → `embedded-silicon-and-firmware-models`)
- [ ] Watchdog supervised, not blindly kicked? (§5.9 → `embedded-languages-realtime-and-patterns`)
- [ ] Fault handler captures PC/LR/CFSR and persists it? (§5.8 → `embedded-languages-realtime-and-patterns`)
- [ ] Stack sizes justified by high-water marks + MPU guards? (§1.2 → `embedded-silicon-and-firmware-models`)
- [ ] DMA buffers aligned and cache-maintained (M7)? (§1.2 → `embedded-silicon-and-firmware-models`)
- [ ] Secrets not in flash; OTA signed with rollback protection? (§9.3 → `embedded-industrial-control-connectivity-and-cloud`, §10 → `embedded-security-safety-and-testing`)
- [ ] Build reproducible, versioned, SBOM emitted? (§12.6 → `embedded-security-safety-and-testing`)

---
