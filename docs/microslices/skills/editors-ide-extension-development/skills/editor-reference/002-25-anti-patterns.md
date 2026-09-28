---
id: skill-25-anti-patterns-22c488f5de
purpose: 25 anti patterns
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-reference/SKILL.md
requires: ["skill-24-what-s-live-verified-august-2026-101a9c6926"]
links: ["skill-26-misconceptions-8ceca638ab"]
---

## §25. Anti-Patterns

```
⚠️ "activationEvents": ["*"] — taxing every user's startup (§13)
⚠️ Not pushing disposables onto context.subscriptions (§12)
⚠️ Building custom UI in a webview when a tree view or quick pick would do (§15)
⚠️ Hardcoded colours in a webview instead of --vscode-* variables (§15)
⚠️ Writing files directly instead of a WorkspaceEdit — breaks undo (§14)
⚠️ Assuming the extension host is local — it isn't over SSH/containers (§8)
⚠️ Putting all logic behind the vscode API, making it untestable (§17)
⚠️ Ignoring cancellation tokens in a language server (§9, §16)
⚠️ Assuming byte offsets where LSP specifies UTF-16 code units (§9, §18)
⚠️ A parser that fails on incomplete code — code is broken while typed (§11, §16)
⚠️ Regex where Tree-sitter queries or ast-grep would be structural (§11)
⚠️ Naive string buffer; O(n) line lookup (§18)
⚠️ Rendering all lines instead of virtualizing (§19)
⚠️ Watching node_modules (§23)
⚠️ Publishing only to the Microsoft Marketplace if you want reach (§17)
⚠️ Memorizing vim keybindings instead of learning the grammar (§3)
⚠️ Infinite editor-config tinkering as a substitute for work (§4)
```

---
