---
id: skill-20-sources-and-method-bacb2281b4
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/assembly-programming/skills/assembly-reference/SKILL.md
requires: ["skill-19-quick-reference-216f2446b3"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. The durable material — §1 → `assembly-fundamentals-and-isas` (machine model),
§6 → `assembly-toolchain-performance-and-simd` (ABIs), §8 → `assembly-toolchain-performance-and-simd` (reading disassembly), §9 → `assembly-toolchain-performance-and-simd` (performance fundamentals), §10.4 → `assembly-toolchain-performance-and-simd`, §11 → `assembly-systems-crypto-and-inline`, §12.1 → `assembly-systems-crypto-and-inline`,
§13.2 → `assembly-systems-crypto-and-inline`, §14 → `assembly-systems-crypto-and-inline`, §15 — is synthesized from the vendor architecture manuals, the optimization
references in §18, and long-established practice. Every **time-sensitive** claim (ISA
extension status, profile contents, constant-time guarantees, silicon deployment) was
verified against a primary or near-primary source in **August 2026** and is flagged in
§17 with a decay-risk rating. Where practitioners genuinely disagree — mostly about how
much hand-written assembly is justified — §16 presents both cases.

**Search log** (August 2026): Intel APX and AVX10/AVX10.2 status and Nova Lake support ·
RISC-V RVA23 profile ratification and mandatory extensions · constant-time programming,
Intel DOIT and Arm DIT · Armv9, SVE2, SME/SME2 and Apple Silicon deployment.

**Primary and near-primary sources consulted (selected):**
- **Intel** — *Architecture Instruction Set Extensions and Future Features* programming
  reference (rev 060, November 2025), the AVX10 architecture specification, and the
  *Data Operand Independent Timing ISA Guidance* and timing-side-channel guidance articles
- **RISC-V International** — RVA23 ratification announcement (21 Oct 2024), the **Ratified
  Specifications Library** (`docs.riscv.org/reference/rva23`), and **riscv/riscv-profiles**
  `rva23-profile.adoc` for the mandatory/optional extension lists
- **Arm** — the Armv9-A architecture page; DIT register documentation
- **TechInsights** on APX's register and load/store impact; **Phoronix**, **TechPowerUp**,
  **VideoCardz**, and **igor'sLAB** on the Nova Lake ISA confirmation; the LKVM/KVM
  AVX10.2 CPUID patch series for the AVX10/512 policy change
- **Academic and practitioner security work** — "Let's DOIT: Using Intel's Extended HW/SW
  Contract for Secure Compilation of Crypto Code" (TCHES 2025), "Constant-Time Code: The
  Pessimist Case" (IACR ePrint 2025/435), "Constant-Time Wasmtime, for Real This Time",
  **LWN.net**'s "Constant-time instructions and processor optimizations", and the oss-sec
  thread on data-operand-dependent timing
- **Trail of Bits** on LLVM constant-time intrinsics; academic SME benchmarking work on
  Apple M4 confirming Armv9.2-A, SME and SME2

**Confidence statement.** **High confidence** in §1–§14 → `assembly-fundamentals-and-isas`, `assembly-systems-crypto-and-inline` and §19 — these rest on vendor
architecture manuals, ABI specifications, and long-established optimization literature.
**High confidence** in §17's RISC-V RVA23 contents and the DOIT/DIT descriptions, which
come from the ratified specification and vendor documentation respectively. **Moderate
confidence** in the Nova Lake and AVX10/APX shipping details: they come from Intel's own
ISA reference manual (a primary source) but describe **unreleased hardware**, and this
specific question had contradictory reporting through late 2025 before the manual settled
it — treat ship dates and final feature lists as subject to change. **Moderate confidence**
in §10.3 → `assembly-toolchain-performance-and-simd`'s SME deployment picture, which is assembled from vendor announcements,
academic benchmarking, and trade reporting rather than a single authoritative source;
the direction (uneven, runtime-detect) is reliable, the per-vendor specifics less so.
Cycle-count figures throughout §9 → `assembly-toolchain-performance-and-simd` and §19.1 are **order-of-magnitude guidance across
typical modern cores**, not measurements for any specific microarchitecture — use Agner
Fog's tables or uops.info for real numbers.
