---
id: skill-12-cryptographic-and-constant-time-assembly-d972d30722
purpose: 12 cryptographic and constant time assembly
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-systems-crypto-and-inline/SKILL.md
requires: ["skill-11-systems-assembly-f80b040c87"]
links: ["skill-13-inline-assembly-and-intrinsics-ead05708cd"]
---

## §12. Cryptographic and Constant-Time Assembly

**[DURABLE] This is the strongest remaining justification for hand-written assembly, and
the reason is that the compiler is actively working against you.** An optimizing compiler
is free to turn your carefully branchless code back into a branch, and there is no
standard way in C to say "don't."

### 12.1 The three rules

1. **Never branch on secret data.**
2. **Never index memory at a secret-dependent address** (cache-timing attacks — Bernstein's
   AES cache-timing work is the canonical demonstration).
3. **Never use variable-latency instructions on secret data** — historically division, and
   on some hardware multiplication.

Tools: `cmov`/`csel` (§2.3 → `assembly-fundamentals-and-isas`, §3.2 → `assembly-fundamentals-and-isas`), masking (`mask = -(cond & 1)` then
`r = (a & mask) | (b & ~mask)`), and constant-time comparison that accumulates differences
with OR rather than returning early.

### 12.2 The hardware contract — and why it changed

**[VERSIONED, and this is genuinely important and under-known.]** For decades rule 3 rested
on documentation and microbenchmarks with **no guarantee for future microarchitectures**.
That changed with explicit vendor contracts:

- **Arm DIT** (`PSTATE.DIT`, since Armv8.4) — when set, the architecture requires that the
  timing of instructions in the DIT subset is insensitive to the *data values* in their
  registers, and that load/store timing is insensitive to the data being loaded or stored.
- **Intel DOIT** (`IA32_UARCH_MISC_CTL` bit 0, "data operand independent timing") — the
  same idea for a documented instruction subset. **Intel explicitly does not recommend
  enabling it globally** because of the performance cost; it's meant to be enabled only for
  code already written to be constant-time.
- **RISC-V has this in the ISA itself**: **`Zkt`** (scalar) and **`Zvkt`** (vector) attest
  that their instruction subsets have data-independent execution latency — and **Zvkt is
  mandatory in RVA23**.

**The part that catches people out:** on **Intel, the guarantees held by default only for
microarchitectures earlier than Ice Lake (Core) and Gracemont (Atom)**. On Ice Lake,
Gracemont, and later, they are **not provided by default** and must be explicitly enabled
via DOIT. Meanwhile the DOIT bit is an **MSR — kernel-only**, whereas Arm's DIT is a cheap
*unprivileged* `msr` a user-space program can set itself. Linux enabled DIT for arm64 in
**v6.2 but only in the kernel**, leaving user space to opt in.

> **⚠️ GOTCHA — read Arm's DIT guarantee precisely.** It requires timing to be independent
> of *the registers the instruction explicitly uses*. Researchers have pointed out it does
> **not** obviously cover values in registers the instruction doesn't reference, and it
> makes no statement about **data memory-dependent prefetchers (DMPs)** — the mechanism
> behind attacks like GoFetch. **Intel's DOIT, by contrast, explicitly does cover
> data-dependent prefetchers.** These are not equivalent guarantees, and the difference
> matters for real attacks.

### 12.3 Beyond hand-writing

The state of the art is moving toward **verified** rather than merely careful:
**Jasmin** (a language and verification framework for high-assurance crypto, extended to
prove that only DOIT-subset instructions touch secret data — *including under speculative
execution*), **Serberus**, **Vale**, and formally-verified libraries like
**HACL\*** and **fiat-crypto**. **[VERSIONED]** LLVM is also gaining **constant-time
intrinsics** (lowering to `CSEL` on AArch64, masked arithmetic where no constant-time
instruction exists), which maintainers of Rust Crypto, BearSSL, and PuTTY have expressed
interest in adopting **to replace their current inline-assembly workarounds** — which, if
it lands broadly, removes one of assembly's last unavoidable use cases.

**Also use the hardware crypto instructions**: AES-NI, ARMv8 Crypto Extensions, RISC-V
Zvk*. They are faster *and* constant-time by construction, which is the rare case where
the fast path and the safe path coincide.

---
