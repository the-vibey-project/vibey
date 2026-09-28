---
id: skill-15-webviews-0948050610
purpose: 15 webviews
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-extension-development/SKILL.md
requires: ["skill-14-api-surfaces-9a67059403"]
links: ["skill-16-writing-a-language-server-a9b3bdb62a"]
---

## §15. Webviews

**⚠️ An isolated iframe for custom UI, with a `postMessage` bridge.**
```
⚠️ SECURITY  set a Content-Security-Policy; use a nonce for scripts;
   ⚠️ use webview.asWebviewUri() for local resources — plain file paths
   will not load
STATE        ⚠️ getState/setState, or retainContextWhenHidden (expensive)
   — webviews are DISPOSED when hidden by default
THEMING      ⚠️ use the CSS variables VS Code injects (--vscode-*) so your
   UI follows the user's theme. Hardcoded colours look broken in half of them
```
**⚠️ The judgement call**: ⚠️ **webviews are heavy and step outside the native UI, so
prefer native contributions (tree views, quick picks, status bar) where they'll do.**
**⚠️ Custom editors and notebook APIs exist for document-shaped and cell-shaped UI
respectively, and are usually better than a hand-rolled webview for those cases.**

---
