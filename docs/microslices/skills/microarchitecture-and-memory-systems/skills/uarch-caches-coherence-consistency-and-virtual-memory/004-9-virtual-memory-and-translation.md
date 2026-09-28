---
id: skill-9-virtual-memory-and-translation-e74ba766dd
purpose: 9 virtual memory and translation
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-caches-coherence-consistency-and-virtual-memory/SKILL.md
requires: ["skill-8-memory-consistency-models-70d54fc854"]
links: ["skill-10-prefetching-f2d157a49c"]
---

## §9. Virtual Memory and Translation

**⚠️ Multi-level page tables** (⚠️ four or five levels on x86-64), ⚠️ **so a TLB miss can
cost several memory accesses — a "page walk."**
**⚠️ The TLB** caches translations, ⚠️ **and TLB reach — entries × page size — is frequently
the hidden limit on large working sets.**
**⚠️ HUGE PAGES** (2 MB, 1 GB) ⚠️ **multiply TLB reach and are one of the highest-value and
least-used tunings for memory-intensive server workloads;** ⚠️ **the costs are internal
fragmentation and allocation difficulty.**
**⚠️ Cache indexing interaction**: ⚠️ **VIPT (virtually indexed, physically tagged) caches
let translation and lookup proceed in parallel, which constrains L1 size to page size ×
associativity — a genuine architectural reason L1 caches are small.**
**⚠️ ASIDs/PCIDs** avoid flushing the whole TLB on context switch, ⚠️ **which became much
more important after §19 → `uarch-dram-memory-controllers-power-and-security`'s mitigations increased switching costs.**

---
