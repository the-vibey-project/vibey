---
id: skill-17-testing-and-publishing-d9bc6d2654
purpose: 17 testing and publishing
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-extension-development/SKILL.md
requires: ["skill-16-writing-a-language-server-a9b3bdb62a"]
links: []
---

## §17. Testing and Publishing

**⚠️ Testing**: **`@vscode/test-electron` runs integration tests in a real VS Code
instance; unit-test pure logic separately.** ⚠️ **Keep as much logic as possible OUT of
the `vscode` API surface so it's testable without launching an editor** — **this is the
single best structural decision in extension code.**
**⚠️ Packaging and publishing**: **`vsce package` → `.vsix`; `vsce publish` to the VS Code
Marketplace via an Azure DevOps PAT.** ⚠️ **Open VSX is the separate, vendor-neutral
registry that VSCodium, Zed-adjacent forks and other non-Microsoft builds use** —
**publish to both if you want reach beyond Microsoft's distribution.**
**⚠️ Note the licensing constraint**: ⚠️ **the Microsoft Marketplace's terms restrict use to
Microsoft's own products**, **which is precisely why Open VSX exists and why forks can't
simply point at it.**

---

# PART V — BUILDING AN EDITOR
