---
id: skill-8-remote-development-a120d18a0e
purpose: 8 remote development
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-architecture-and-the-protocol-layer/SKILL.md
requires: ["skill-7-configuration-and-workspaces-a321bfcd88"]
links: ["skill-9-lsp-the-change-that-mattered-7f98230fe6"]
---

## §8. Remote Development

**⚠️ Architecturally the most interesting VS Code feature: the extension host runs on the
REMOTE, with only the UI local.**
```
REMOTE-SSH · DEV CONTAINERS (⚠️ devcontainer.json — reproducible toolchain
   per repo, and genuinely excellent onboarding infrastructure) · WSL ·
   CODESPACES (hosted dev containers) · ⚠️ TUNNELS
```
**⚠️ The consequence extension authors must internalize**: ⚠️ **your extension may run on a
different machine from the UI**, **so file paths, environment variables and available
binaries are the REMOTE's.** **⚠️ Extensions declare `extensionKind` as `ui` or
`workspace` to control where they run, and getting this wrong produces extensions that
work locally and break over SSH.**

---

# PART III — THE PROTOCOL LAYER
