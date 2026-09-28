---
id: skill-21-the-jetbrains-platform-f753c8d65a
purpose: 21 the jetbrains platform
source: src/vibey_tools/skills/plugins/editors-ide-extension-development/skills/editor-internals-buffers-rendering-and-performance/SKILL.md
requires: ["skill-20-indexing-and-code-intelligence-a3836f583c"]
links: ["skill-22-terminal-ui-programming-722196a390"]
---

## §21. The JetBrains Platform

**⚠️ Plugin development targets the IntelliJ Platform, shared across IDEA, PyCharm,
WebStorm, GoLand, Rider and the rest.**
**Core concepts**: **PSI (Program Structure Interface — ⚠️ the semantic tree, richer than a
syntax tree), VFS (virtual file system), actions, inspections (⚠️ with quick-fixes),
intentions, run configurations, and extension points declared in `plugin.xml`.**
**⚠️ Built with Gradle via the IntelliJ Platform Gradle Plugin; distributed through the
JetBrains Marketplace.**
**⚠️ Honest comparison**: ⚠️ **the IntelliJ Platform is substantially more complex to learn
than the VS Code API and gives you access to a far richer semantic model.** **If your
plugin needs deep type-aware analysis or refactoring, that's the tradeoff you're buying.**

---
