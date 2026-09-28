---
id: skill-6-architecture-e022c8b192
purpose: 6 architecture
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-architecture-and-the-protocol-layer/SKILL.md
requires: []
links: ["skill-7-configuration-and-workspaces-a321bfcd88"]
---

## §6. Architecture

**⚠️ Understanding the process model explains nearly every extension constraint:**
```
⚠️ MAIN PROCESS       Electron main; window and lifecycle management
⚠️ RENDERER           the UI. ⚠️ Extensions CANNOT touch the DOM
⚠️ EXTENSION HOST     ⚠️ a SEPARATE Node.js process where extensions run.
   ⚠️ This isolation is why a bad extension can't crash the UI, and why
   there is no direct DOM access — everything is an RPC away
LANGUAGE SERVERS      ⚠️ further separate processes (§9)
SHARED PROCESS        long-running background work
```
> **⚠️ GOTCHA — extensions cannot manipulate the editor's DOM, and this surprises every
> web developer starting extension work.** ⚠️ **You contribute through declared extension
> points and APIs; for custom UI you use a WEBVIEW, which is an isolated iframe with a
> message-passing bridge** (§15 → `editor-vscode-extension-development`). **⚠️ If your design requires arbitrary DOM control of the
> editor chrome, redesign it.**

**⚠️ Monaco is the editor component** — **the same one that runs in the browser** —
**and it is available standalone, ⚠️ though it is NOT the same as embedding VS Code:
Monaco gives you the text editing widget without the workbench, extensions or LSP client.**

---
