---
id: skill-31-method-4a8ab76477
purpose: 31 method
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-reference/SKILL.md
requires: ["skill-30-quick-reference-b696dfabf0"]
links: []
---

## §31. Method

**§1–§25 → `logic-devices-transistors-cmos-gates-and-power`, `logic-standard-cells-boolean-minimization-and-arithmetic`, `logic-sequential-timing-metastability-cdc-and-hdl`, `logic-firmware-boot-root-of-trust-embedded-practice-and-security` rests on settled material** — **Boolean algebra, static CMOS construction, the
setup/hold constraint, metastability, the CDC techniques, the UEFI phase model and the
verified-boot key hierarchy.** ⚠️ **None needed verification; De Morgan published in 1847
and the complementary-network construction has been the basis of digital design since the
1960s.**

**⚠️ On scope: I deliberately did not re-derive device physics or fabrication (a
semiconductor reference), nor how gates compose into processors (a microarchitecture
reference).** ⚠️ **What is here is the gate level and the boot level — the two layers those
files assume rather than explain.**

**Two searches were run in August 2026**, on **the Secure Boot certificate expiry** and
**open-source firmware and roots of trust** — ⚠️ **the first because it is a hard-dated
event affecting essentially every PC sold since 2012 and the consequences are widely
misreported, the second because §20 → `logic-firmware-boot-root-of-trust-embedded-practice-and-security`'s uncomfortable truth about unexaminable privileged
code is finally being addressed.**

**Confidence.** **High** in §5 → `logic-devices-transistors-cmos-gates-and-power` and §15 → `logic-sequential-timing-metastability-cdc-and-hdl`, which are the sections I'd most want read.
⚠️ **The complementary-network construction is the most useful single idea here: once you
see that a gate is two mutually exclusive switch networks and that the PUN is the dual of
the PDN, you can draw any gate mechanically — and it immediately explains why NAND and NOR
are the natural primitives and why AND costs more than NAND, which is backwards from how
Boolean algebra is taught.**
⚠️ **§15 → `logic-sequential-timing-metastability-cdc-and-hdl`'s setup-versus-hold asymmetry is the second and it has real consequences: a setup
violation is fixed by slowing the clock, a hold violation is a broken chip at ANY frequency.
Knowing which you have determines whether you have a tuning problem or a respin.**
**⚠️ §17 → `logic-sequential-timing-metastability-cdc-and-hdl`'s warning that a two-flop synchronizer is for single-bit level signals ONLY is the
correction that prevents the worst class of intermittent field failure.**

**High** on §26.1, which is unusually well-sourced because Microsoft, Red Hat and Google all
publish on it and agree on the dates and mechanics. ⚠️ **The correction I'd most want
carried is Red Hat's: systems keep booting — what expires is the ability to SIGN new
binaries and, via the KEK, to UPDATE the allow and deny lists.** ⚠️ **That is a serious loss,
because it removes the revocation path that blocks newly discovered bootkits, but it is not
the "your PC won't start" framing that circulates.** **⚠️ The most urgent-sounding analysis
comes from a firmware-security vendor selling fleet visibility; the KEK point it makes is
correct regardless.**

**Moderate-to-high** on §26.2. ⚠️ **Caliptra's architecture, minimalist scope and gate
counts come from the project's own specifications and repository, which are public and
checkable.** ⚠️ **AMD's stated 2026+ integration plan is from AMD directly.** **⚠️ The claim
that hyperscalers will REQUIRE Caliptra of their chip suppliers is from a paid analyst
newsletter reporting OCP conversations, and I have marked it as reported rather than
treating it as established.** ⚠️ **The framing I'd defend is the gotcha: open RTL means the
design is auditable, not that you control the keys — and one motherboard being the first
consumer AM5 board with open firmware in 2026 is the honest measure of how far this is from
mainstream.**
