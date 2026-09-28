---
id: skill-12-anatomy-of-a-vs-code-extension-aa2f33b204
purpose: 12 anatomy of a vs code extension
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-vscode-extension-development/SKILL.md
requires: []
links: ["skill-13-contribution-points-and-activation-409a216508"]
---

## §12. ⚠️ Anatomy of a VS Code Extension

```
my-extension/
├── package.json        ⚠️ THE MANIFEST — contributions, activation, engines
├── src/extension.ts    activate() and deactivate()
├── tsconfig.json
└── .vscodeignore       ⚠️ what to exclude from the package
```
```typescript
export function activate(context: vscode.ExtensionContext) {
  const d = vscode.commands.registerCommand('ext.hello', () => {
    vscode.window.showInformationMessage('Hello');
  });
  // ⚠️ ALWAYS push disposables — this is the leak everyone creates
  context.subscriptions.push(d);
}
export function deactivate() {}
```
**⚠️ Scaffold with `yo code`; develop by pressing F5, which launches an Extension
Development Host window with your extension loaded.**
**⚠️ The disposable pattern is not optional**: ⚠️ **every registration, listener, and
watcher returns a Disposable, and anything not pushed onto `context.subscriptions` leaks
across reloads** — **which shows up as duplicate handlers firing, not as a memory warning.**

---
