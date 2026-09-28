---
id: skill-20-indexing-and-code-intelligence-a3836f583c
purpose: 20 indexing and code intelligence
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-internals-buffers-rendering-and-performance/SKILL.md
requires: ["skill-19-rendering-9c43e9314b"]
links: ["skill-21-the-jetbrains-platform-f753c8d65a"]
---

## §20. Indexing and Code Intelligence

**⚠️ How an IDE answers "find all references" across a million lines instantly.**
```
⚠️ SYMBOL INDEX     built on open/change, persisted across sessions
⚠️ INCREMENTAL      recompute only what a change invalidates — this is the
   whole ballgame. ⚠️ Salsa-style demand-driven computation with memoized
   queries and dependency tracking is the modern approach (rust-analyzer)
⚠️ LAZY / ON-DEMAND  don't fully analyze what nobody has asked about
FUZZY MATCHING      ⚠️ the scoring function is what makes a file-picker
   feel good or bad; consecutive-match and word-boundary bonuses matter
```
**⚠️ The JetBrains difference** (§21): ⚠️ **it builds and persists its own full semantic
model rather than delegating to a language server**, **which is why its refactorings and
cross-language analysis go deeper — and why indexing a large project takes visible time
and memory.** **That's the tradeoff, stated plainly.**

---
