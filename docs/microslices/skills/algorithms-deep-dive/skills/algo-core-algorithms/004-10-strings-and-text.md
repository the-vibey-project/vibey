---
id: skill-10-strings-and-text-3706ed1403
purpose: 10 strings and text
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-core-algorithms/SKILL.md
requires: ["skill-9-graphs-501de76684"]
links: ["skill-11-dynamic-programming-greedy-and-amortization-931fdeef9d"]
---

## §10. Strings and Text

**Exact search**: **Boyer-Moore** and variants skip ahead and are sublinear in practice;
**KMP** is linear with no worst case; **Rabin-Karp** uses rolling hashes and generalizes
to multiple patterns; **Aho-Corasick** matches many patterns in one pass and is **the right
answer for keyword/blocklist scanning**. **⚠️ In practice, `memmem`/`std::string::find`
with SIMD beats naive implementations of all of these** — measure before implementing.

**Structures**: **suffix arrays** (+ LCP) — practical, compact, and the usual choice over
**suffix trees** (asymptotically nice, memory-hungry). **FM-index / BWT** for compressed
full-text search (the basis of genomic aligners). **Tries and ARTs** (§5.3 → `algo-data-structures`).

**Edit distance and similarity**: Levenshtein is O(mn) DP — **and §9 of a
theory-of-computation reference explains why that's conditionally optimal under SETH, so
don't try to beat it asymptotically**. Practical answers: bound the edit distance
(banded DP), use **Myers' bit-parallel algorithm**, or switch measures — **SimHash/MinHash
for near-duplicate detection at scale**, n-gram similarity, or trigram indexes.

**⚠️ Unicode will hurt you.** Normalization forms (NFC/NFD/NFKC/NFKD), grapheme clusters vs.
code points vs. bytes, case folding that isn't symmetric, collation that's
locale-dependent. **"Reverse a string" and "uppercase a string" are not simple operations**
and treating them as such is a recurring source of bugs in international products.

---
