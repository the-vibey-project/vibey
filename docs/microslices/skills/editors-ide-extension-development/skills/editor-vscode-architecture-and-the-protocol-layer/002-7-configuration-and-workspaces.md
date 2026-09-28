---
id: skill-7-configuration-and-workspaces-a321bfcd88
purpose: 7 configuration and workspaces
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-architecture-and-the-protocol-layer/SKILL.md
requires: ["skill-6-architecture-e022c8b192"]
links: ["skill-8-remote-development-a120d18a0e"]
---

## §7. Configuration and Workspaces

```
SETTINGS PRECEDENCE  ⚠️ default → user → remote → workspace → folder →
   language-specific. ⚠️ Later wins, and this ordering explains most
   "why isn't my setting applying" confusion
settings.json · keybindings.json · tasks.json · launch.json · extensions.json
⚠️ .vscode/ in the repo  team-shared settings, recommended extensions,
   debug configs. ⚠️ Commit these — they're onboarding infrastructure
MULTI-ROOT WORKSPACES  ⚠️ .code-workspace file; several folders, one window
PROFILES  ⚠️ isolated sets of extensions and settings — the clean answer to
   "my Python setup is fighting my TypeScript setup"
```
**⚠️ Language-specific settings** (`"[python]": { ... }`) **are underused and solve most
formatter conflicts.**
**⚠️ Workspace Trust**: ⚠️ **untrusted workspaces run in Restricted Mode with tasks and
many extensions disabled** — **a real security feature, and a real source of "why doesn't
anything work" when someone dismisses the prompt.**

---
