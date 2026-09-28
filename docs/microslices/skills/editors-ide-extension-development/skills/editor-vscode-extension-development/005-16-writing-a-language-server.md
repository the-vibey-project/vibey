---
id: skill-16-writing-a-language-server-a9b3bdb62a
purpose: 16 writing a language server
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-extension-development/SKILL.md
requires: ["skill-15-webviews-0948050610"]
links: ["skill-17-testing-and-publishing-d9bc6d2654"]
---

## §16. Writing a Language Server

**⚠️ The practical path — use the SDK for your language:**
```
Node/TS   vscode-languageserver / vscode-languageclient
Rust      tower-lsp
Python    pygls
Go        go.lsp / gopls internals as reference
```
**⚠️ Minimum viable server**: **initialize handshake declaring capabilities → document
sync → publish diagnostics on change → completion → hover.** ⚠️ **Diagnostics first: it's
the highest-value feature and doesn't require the user to ask for anything.**
**⚠️ Architecture that works** (§11 → `editor-vscode-architecture-and-the-protocol-layer`): ⚠️ **parse incrementally and error-tolerantly, keep a
document store keyed by URI, debounce analysis, honour cancellation, and separate the
syntactic layer (fast, per-file) from the semantic layer (slow, project-wide).**
**⚠️ The hardest parts, in order**: ⚠️ **incremental re-analysis without re-doing the whole
project, resolving imports and building a project model, cancellation and concurrency, and
graceful degradation when the project doesn't build.**
**⚠️ rust-analyzer is the best-documented modern reference implementation** — **its
architecture notes on salsa-style incremental computation are worth reading regardless of
language.**

---
