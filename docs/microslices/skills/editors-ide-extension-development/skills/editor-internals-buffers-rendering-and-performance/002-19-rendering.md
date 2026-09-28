---
id: skill-19-rendering-9c43e9314b
purpose: 19 rendering
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-internals-buffers-rendering-and-performance/SKILL.md
requires: ["skill-18-text-buffer-data-structures-47a1c4ed3f"]
links: ["skill-20-indexing-and-code-intelligence-a3836f583c"]
---

## §19. Rendering

**⚠️ Virtualization is mandatory**: ⚠️ **render only the visible lines plus a small
overscan.** **A 100k-line file must not create 100k DOM nodes or draw calls.**
**⚠️ The hard parts**: **variable-width glyphs and font metrics, ligatures, bidirectional
text, tabs vs spaces alignment, soft wrapping (⚠️ which breaks the clean line-number ↔
visual-row mapping and complicates everything downstream), and cursor/selection geometry.**
**⚠️ DOM vs GPU**: ⚠️ **VS Code renders in the DOM (with a canvas-based minimap); Zed
renders on the GPU with a custom framework, which is where its frame-rate claims come
from** (§24.2 → `editor-reference`). **⚠️ The tradeoff is accessibility and platform text-input integration —
DOM gets screen readers, IME and selection semantics largely for free, and a custom GPU
renderer must reimplement all of it.**
**⚠️ Input latency is the metric users actually feel** — **not throughput** — **and the
budget is roughly a frame.**

---
