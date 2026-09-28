---
id: skill-9-lsp-the-change-that-mattered-7f98230fe6
purpose: 9 lsp the change that mattered
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-architecture-and-the-protocol-layer/SKILL.md
requires: ["skill-8-remote-development-a120d18a0e"]
links: ["skill-10-dap-3e74b8b457"]
---

## §9. ⚠️ LSP — The Change That Mattered

**⚠️ Before LSP: every editor implemented language intelligence for every language —
M editors × N languages.** ⚠️ **After LSP: M + N.** **This is the single most important
structural change in developer tooling in the last decade.**
```
⚠️ JSON-RPC over stdio (or sockets). Editor = CLIENT, language tool = SERVER
INITIALIZE handshake  ⚠️ capabilities negotiated BOTH ways — the client says
   what it supports, the server says what it provides
DOCUMENT SYNC  full or incremental
⚠️ REQUESTS  completion · hover · definition · references · rename ·
   formatting · code actions · signature help · document/workspace symbols ·
   semantic tokens · inlay hints · call hierarchy
⚠️ NOTIFICATIONS  publishDiagnostics (⚠️ server → client, unsolicited —
   this is how squiggles appear without being asked for)
```
**⚠️ Practical implementation notes:**
- ⚠️ **Positions are (line, character) with UTF-16 code units by default** — **a genuine
  and recurring source of off-by-N bugs with emoji and non-BMP characters.** **Newer spec
  versions allow negotiating UTF-8.**
- ⚠️ **Servers must be resilient to invalid intermediate states** — **the user types
  constantly, so the document is syntactically broken most of the time.** **Error-tolerant
  parsing is the requirement, not a nicety** (§11).
- ⚠️ **Debounce and cancel.** **Requests arrive per keystroke; honour cancellation tokens.**
**⚠️ Notable servers**: **rust-analyzer, gopls, clangd, pyright/pylance, typescript-language-server,
jdtls.** ⚠️ **Server quality varies enormously and is the real determinant of "how good is
editor X for language Y" — not the editor.**

---
