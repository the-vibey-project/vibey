---
id: skill-18-text-buffer-data-structures-47a1c4ed3f
purpose: 18 text buffer data structures
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-internals-buffers-rendering-and-performance/SKILL.md
requires: []
links: ["skill-19-rendering-9c43e9314b"]
---

## §18. ⚠️ Text Buffer Data Structures

**⚠️ The classic interview question that is also a real engineering decision. A naive
string is O(n) per edit and unusable at scale.**
```
⚠️ GAP BUFFER      a gap at the cursor; insertion at the gap is O(1),
   moving the gap is O(distance). ⚠️ Excellent for typing (edits cluster),
   poor for scattered edits. Emacs uses this
⚠️ PIECE TABLE     original buffer + append-only add buffer + a list of
   PIECES describing the current document as spans of each.
   ⚠️ Edits never mutate existing text — which gives cheap undo and
   natural change tracking. ⚠️ VS Code uses a piece table variant
⚠️ ROPE            balanced tree of string chunks. O(log n) insert, delete,
   index. ⚠️ Excellent for very large files and concurrent editing.
   Used by Zed (and its ancestors), xi, and several Rust editors
LINE ARRAY         simple, and O(n) for line insertion in the middle
```
> **⚠️ GOTCHA — the operations that decide the structure are not the ones people
> optimize.** ⚠️ **You need fast line-number ↔ offset conversion (for every LSP message,
> every diagnostic, every jump), fast slicing for rendering the visible region, and cheap
> snapshots for background work.** **⚠️ A structure with fast insert but O(n) line lookup
> will feel slow in ways profiling attributes to the wrong place.**

**⚠️ Encoding is a persistent trap**: ⚠️ **UTF-8 storage, UTF-16 offsets in LSP (§9 → `editor-vscode-architecture-and-the-protocol-layer`),
grapheme clusters for cursor movement, and code points for regex** — **four different
notions of "position," and mixing them produces bugs that only appear with emoji, CJK
text or combining characters.**

---
