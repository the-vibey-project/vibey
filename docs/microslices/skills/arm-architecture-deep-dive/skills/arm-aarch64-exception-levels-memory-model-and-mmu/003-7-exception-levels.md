---
id: skill-7-exception-levels-901f596968
purpose: 7 exception levels
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-aarch64-exception-levels-memory-model-and-mmu/SKILL.md
requires: ["skill-6-instruction-set-characteristics-7455ae0ad0"]
links: ["skill-8-the-memory-model-c7464a05fc"]
---

## §7. ⚠️ Exception Levels

> **⚠️ The privilege model, and it is cleaner than x86's rings.**
```
⚠️ THE LEVELS  ⚠️ EL0 (applications) · EL1 (OS kernel) ·
   ⚠️ EL2 (HYPERVISOR) · ⚠️ EL3 (SECURE MONITOR — the highest,
   and where the world switch happens, §13)
⚠️ ⚠️ EL2 EXISTING AS AN ARCHITECTED LEVEL is the key difference
   from x86, where virtualization was retrofitted. ⚠️ The
   hypervisor has its own level, its own registers and its own
   translation regime by design (§20)
⚠️ ⚠️ ORTHOGONAL TO THIS: SECURITY STATE (§13). ⚠️ Secure and
   Non-secure worlds each have their own EL0/EL1, so the
   privilege model is TWO-DIMENSIONAL. ⚠️ ARMv9's CCA adds a
   third dimension with Realm state (§15)
⚠️ EXCEPTION HANDLING  ⚠️ a VECTOR TABLE indexed by exception
   type AND by the level/state the exception came from ·
   ⚠️ ELR (return address), SPSR (saved state), ESR (⚠️ the
   syndrome register, which tells you WHY — enormously useful
   for debugging)
⚠️ ⚠️ EXCEPTIONS ROUTE UPWARD, and where they route is
   CONFIGURABLE via HCR_EL2 and SCR_EL3 — ⚠️ which is what lets
   a hypervisor trap and emulate specific guest operations
⚠️ SYNCHRONOUS vs asynchronous (IRQ, FIQ, SError) ·
   ⚠️ FIQ historically the fast interrupt, now largely used for
   secure-world interrupts
```

---
