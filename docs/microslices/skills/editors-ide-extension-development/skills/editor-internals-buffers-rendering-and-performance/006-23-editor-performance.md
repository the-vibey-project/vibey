---
id: skill-23-editor-performance-4200f50b38
purpose: 23 editor performance
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-internals-buffers-rendering-and-performance/SKILL.md
requires: ["skill-22-terminal-ui-programming-722196a390"]
links: []
---

## §23. Editor Performance

```
⚠️ STARTUP        lazy-load everything; measure with extension profiling
⚠️ INPUT LATENCY  the metric users feel. Budget ~one frame
⚠️ LARGE FILES    virtualize (§19); many editors degrade or disable
   features past a size threshold — that's a deliberate choice, not a bug
⚠️ EXTENSION COST  one badly-activated extension taxes every startup (§13)
⚠️ FILE WATCHERS  ⚠️ watching node_modules is the classic resource fire.
   Configure files.watcherExclude and search.exclude
⚠️ LANGUAGE SERVERS  usually the biggest memory consumer in a VS Code session
```
**⚠️ Diagnosing**: **"Developer: Show Running Extensions" and the startup performance view;
`--disable-extensions` to bisect; ⚠️ and process-level inspection, because the extension
host and each language server are separate processes and the memory attribution is not
where people look.**
