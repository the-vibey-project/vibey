---
id: skill-27-misconceptions-4eac353a50
purpose: 27 misconceptions
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-reference/SKILL.md
requires: ["skill-26-what-s-live-checked-august-2026-3425a6a385"]
links: ["skill-28-numbers-1ea9d4e624"]
---

## §27. Misconceptions

| Misconception | Correction |
|---|---|
| AND and OR are the basic gates | ⚠️ **NAND and NOR are natural in CMOS; AND costs more** (§5 → `logic-devices-transistors-cmos-gates-and-power`) |
| A gate amplifies its input | ⚠️ **It connects the output to a rail. Two switch networks** (§5 → `logic-devices-transistors-cmos-gates-and-power`) |
| NOR and NAND are equivalent in cost | ⚠️ **NOR stacks weak pMOS in series. NAND preferred** (§5 → `logic-devices-transistors-cmos-gates-and-power`, §6 → `logic-devices-transistors-cmos-gates-and-power`) |
| nMOS and pMOS are mirror images | ⚠️ **Mobility differs 2-3×; pMOS must be wider** (§6 → `logic-devices-transistors-cmos-gates-and-power`) |
| A pass transistor passes the signal | ⚠️ **nMOS loses a threshold on a high. Use a transmission gate** (§3 → `logic-devices-transistors-cmos-gates-and-power`, §7 → `logic-devices-transistors-cmos-gates-and-power`) |
| CMOS uses no static power | ⚠️ **Was true. Leakage is now major** (§8 → `logic-devices-transistors-cmos-gates-and-power`) |
| Minimal gate count is the goal | ⚠️ **Synthesis optimizes timing, area and power together** (§11 → `logic-standard-cells-boolean-minimization-and-arithmetic`) |
| Hand-minimize before synthesis | ⚠️ **Usually makes results worse** (§11 → `logic-standard-cells-boolean-minimization-and-arithmetic`) |
| Redundant terms are always waste | ⚠️ **They eliminate hazards** (§11 → `logic-standard-cells-boolean-minimization-and-arithmetic`) |
| Latch and flip-flop are synonyms | ⚠️ **Level-sensitive vs edge-triggered. Different things** (§14 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| An incomplete if is harmless | ⚠️ **It infers a latch. Heed the warning** (§14 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Slowing the clock fixes timing | ⚠️ **Setup yes. HOLD violations are broken at any speed** (§15 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Metastability can be designed out | ⚠️ **Only made arbitrarily unlikely. No circuit eliminates it** (§15 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Two flops synchronize any signal | ⚠️ **Single-bit level only. Multi-bit needs Gray/handshake/FIFO** (§17 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| It works on the bench, so CDC is fine | ⚠️ **CDC bugs are probabilistic. Run static CDC analysis** (§17 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| HDL is a programming language | ⚠️ **It describes hardware. Concurrent by default** (§18 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Simulation passing means it works | ⚠️ **Blocking/non-blocking mismatch is silent** (§18 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Verification and test are the same | ⚠️ **Is the design right vs was this die made right** (§19 → `logic-sequential-timing-metastability-cdc-and-hdl`) |
| Ripple carry is fine | ⚠️ **Linear delay. The carry chain is the problem** (§13 → `logic-standard-cells-boolean-minimization-and-arithmetic`) |
| Two's complement is a convention | ⚠️ **It lets one adder handle signed and unsigned** (§13 → `logic-standard-cells-boolean-minimization-and-arithmetic`) |
| BIOS is a small program | ⚠️ **UEFI is effectively an OS with drivers and a shell** (§21 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Firmware stops once the OS loads | ⚠️ **Runtime services persist and are callable** (§21 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Secure boot and measured boot are one thing | ⚠️ **One enforces, one records** (§22 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| A valid signature means safe code | ⚠️ **Signed vulnerable bootloaders pass. Hence rollback protection** (§22 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Reinstalling the OS clears an infection | ⚠️ **Not a firmware one** (§25 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Firmware has little attack surface | ⚠️ **LogoFAIL: image parsers in firmware were exploitable** (§25 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`) |
| Secure Boot certs expiring stops boot | ⚠️ **Existing systems keep booting. You lose signing and revocation** (§26.1) |
| Only Windows is affected | ⚠️ **The UEFI CA 2011 signs the Linux shim too** (§26.1) |
| Open-source RoT means you control it | ⚠️ **Auditable design, vendor-controlled keys** (§26.2) |

---
