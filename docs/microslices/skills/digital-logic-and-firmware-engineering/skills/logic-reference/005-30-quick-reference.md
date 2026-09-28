---
id: skill-30-quick-reference-b696dfabf0
purpose: 30 quick reference
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-reference/SKILL.md
requires: ["skill-29-sources-940bdb0e3f"]
links: ["skill-31-method-4a8ab76477"]
---

## §30. Quick Reference

### 30.1 Picker
| Question | Where |
|---|---|
| How do I build gate X in CMOS? | ⚠️ **PDN from the expression, PUN is its dual** (§5 → `logic-devices-transistors-cmos-gates-and-power`) |
| Why is my path slow? | ⚠️ **Load capacitance and drive. Logical effort** (§6 → `logic-devices-transistors-cmos-gates-and-power`) |
| Where is the power going? | ⚠️ **Clock network, then leakage, then glitches** (§8 → `logic-devices-transistors-cmos-gates-and-power`) |
| Design won't meet timing | ⚠️ **Setup: pipeline or resize. Hold: add delay** (§15 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Intermittent failure in the field | ⚠️ **Suspect CDC and metastability first** (§15 → `logic-sequential-timing-metastability-cdc-and-hdl`, §17 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Synthesis inferred a latch | ⚠️ **Incomplete if/case in combinational logic** (§14 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Simulation passes, hardware fails | ⚠️ **Blocking vs non-blocking, or CDC** (§17 → `logic-sequential-timing-metastability-cdc-and-hdl`, §18 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Board is dead at power-on | ⚠️ **Rails, reset, then the boot stages in order** (§21 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Never reaches main() | ⚠️ **Vector table, stack, BSS/data init** (§24 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Sleep or wake broken | ⚠️ **ACPI tables and D/C/S states** (§23 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Is my machine's boot chain trusted? | ⚠️ **PK/KEK/DB/DBX state, and TPM PCRs** (§22 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Do I need to act before June 2026? | ⚠️ **Check KEK/DB for 2023 certs. Enterprise: audit the fleet** (§26.1) |

### 30.2 Design checks
- [ ] ⚠️ **Every combinational block fully specified — no inferred latches** (§14 → `logic-sequential-timing-metastability-cdc-and-hdl`)
- [ ] ⚠️ **All CDC paths identified and correctly synchronized by TYPE** (§17 → `logic-sequential-timing-metastability-cdc-and-hdl`)
- [ ] ⚠️ **Static CDC analysis run, not just simulation** (§17 → `logic-sequential-timing-metastability-cdc-and-hdl`)
- [ ] Reset strategy defined; async de-assertion synchronized (§14 → `logic-sequential-timing-metastability-cdc-and-hdl`)
- [ ] ⚠️ **Timing closed at all PVT corners, setup AND hold** (§4 → `logic-devices-transistors-cmos-gates-and-power`, §15 → `logic-sequential-timing-metastability-cdc-and-hdl`)
- [ ] Clock gating applied; activity factors considered (§8 → `logic-devices-transistors-cmos-gates-and-power`)
- [ ] FSMs have a safe default for illegal states (§16 → `logic-sequential-timing-metastability-cdc-and-hdl`)
- [ ] ⚠️ **DFT inserted and coverage measured** (§19 → `logic-sequential-timing-metastability-cdc-and-hdl`)
- [ ] **Firmware side:**
- [ ] ⚠️ **Root of trust is genuinely immutable** (§22 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`)
- [ ] ⚠️ **Rollback protection present — signatures alone are insufficient** (§22 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`)
- [ ] ⚠️ **Update is atomic, power-fail safe, with a recovery path** (§24 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`)
- [ ] ⚠️ **SPI write protection configured** (§25 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`)
- [ ] Watchdog fed from proof of correct operation, not a bare timer (§24 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`)
- [ ] ⚠️ **Secure Boot certificate state audited ahead of June 2026** (§26.1)

---
