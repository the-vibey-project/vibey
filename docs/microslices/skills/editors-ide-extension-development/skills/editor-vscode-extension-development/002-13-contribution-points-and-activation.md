---
id: skill-13-contribution-points-and-activation-409a216508
purpose: 13 contribution points and activation
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-extension-development/SKILL.md
requires: ["skill-12-anatomy-of-a-vs-code-extension-aa2f33b204"]
links: ["skill-14-api-surfaces-9a67059403"]
---

## §13. Contribution Points and Activation

**⚠️ Contributions are DECLARATIVE — declared in `package.json`, not registered in code:**
```
commands · menus · keybindings · configuration · languages · grammars ·
snippets · themes · views / viewsContainers · problemMatchers ·
debuggers · taskDefinitions · customEditors · walkthroughs
```
> **⚠️ GOTCHA — activation events are the #1 extension performance mistake, and users feel
> it as "VS Code is slow to start."** ⚠️ **`"activationEvents": ["*"]` activates your
> extension on every startup regardless of relevance.** **⚠️ Use the narrowest trigger:
> `onLanguage:python`, `onCommand:...`, `workspaceContains:**/pyproject.toml`,
> `onView:...`.**
> **⚠️ Modern VS Code infers many activation events automatically from your contributions**
> — **a declared command implies `onCommand` — so the explicit list is often unnecessary.**
> **⚠️ Check your startup cost with the built-in "Developer: Show Running Extensions."**

**⚠️ `when` clauses** control menu and keybinding visibility (`editorLangId == python &&
editorHasSelection`), ⚠️ **and custom context keys via `setContext` let you drive UI state
from your own logic.**

---
