---
id: skill-11-tree-sitter-875860f7df
purpose: 11 tree sitter
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-architecture-and-the-protocol-layer/SKILL.md
requires: ["skill-10-dap-3e74b8b457"]
links: []
---

## §11. Tree-sitter

**⚠️ The other half of the modern stack: an incremental parsing library that produces a
real syntax tree, fast enough to re-parse on every keystroke, and ERROR-TOLERANT.**
```
⚠️ INCREMENTAL   re-parses only what changed
⚠️ ERROR-TOLERANT  produces a usable tree from broken code — essential,
   because code is broken while you type it
⚠️ QUERIES       S-expression patterns over the tree, used for highlighting,
   folding, indentation, and structural selection
GRAMMARS         per-language, generated from a JS grammar definition
```
**⚠️ Why it replaced regex highlighting**: ⚠️ **regex-based highlighting (TextMate grammars)
cannot see structure, degrades on large files, and produces the familiar wrong-colours
artifacts in nested or unusual constructs.** **Tree-sitter knows a token is a function name
because it's in the function-name position.**
**⚠️ The ecosystem built on it is significant**: **Neovim, Helix and Zed use it natively;
GitHub code search and semantic highlighting use it; and ⚠️ tools like `ast-grep` do
structural search-and-replace over the tree, which is a categorically better way to do
large mechanical refactors than regex.**
**⚠️ The division of labour worth internalizing**: ⚠️ **Tree-sitter gives you SYNTAX
cheaply and locally; LSP gives you SEMANTICS expensively and project-wide.** **You need
both, and confusing them leads to trying to do type resolution with a parser.**

---

# PART IV — EXTENSION DEVELOPMENT
