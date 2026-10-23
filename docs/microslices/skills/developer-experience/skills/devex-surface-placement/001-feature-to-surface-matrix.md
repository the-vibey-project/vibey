---
id: skill-feature-to-surface-matrix-4f63950f04
purpose: feature to surface matrix
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-surface-placement/SKILL.md
requires: []
links: []
---

## Feature-to-surface matrix

This table is my synthesis of the sections above. It is a recommendation for where each capability should live first, not a finding. "Primary" means design it here first; "Supporting" means offer a smaller version; "Link out" means send the user to another surface; a dash means do not build it there.

| Capability | VS Code | Desktop | iOS | Android | Web/PWA | CLI |
| --- | --- | --- | --- | --- | --- | --- |
| Install and first run | Walkthrough, ends in a running result | Signed installer opens a sample project | Store install, passkey sign-in | Store install, passkey sign-in | Primary: try it with no install | Single install command |
| Quick action | Command Palette, context menu | Menu-bar extra, menu item | App shortcut, Siri | Shortcut, Quick Settings tile | Button, URL | Primary: one command |
| Status and monitoring | Status bar, tree view | Menu-bar extra, window | Primary: widget | Primary: widget | Dashboard page | Status command |
| Notifications | Rare, actionable only | Notification on completion | Push, with action | Channel with actions | Opt-in push | Exit code, hook |
| Authoring and editing | Primary: editor, language server | Primary: document window | Link out | Link out | Supporting: simple forms | Supporting: files and flags |
| Debug and logs | Primary: panel, output channel | Supporting: log window | Read-only summary | Read-only summary | Supporting: log viewer | Primary: stdout, verbose flag |
| Sharing results | Supporting: copy link | Share sheet, export | Primary: share sheet | Primary: Sharesheet | Primary: stable URL | Output to file or pipe |
| Settings | Settings UI, defaults work | Settings window (standard shortcut) | One short screen | One short screen | Account page | Config file, flags |
| Docs and help | Walkthrough, hover docs | Help menu search | In-context hints | In-context hints | Primary: searchable docs | `--help`, man page |
| AI chat and agents | Sidebar chat view, inline edits | Side panel | Supporting: ask a question | Supporting: ask a question | Chat panel | Agent mode, scripts |

**How to use it.** Pick the single primary surface for each capability, build that one well, and give the others a thin version that calls the same core command. Fill in cells by user research with real non-developers, not by this table alone.
