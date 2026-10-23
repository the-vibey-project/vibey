---
name: devex-surface-placement
description: "Use when deciding which surface a feature of a developer product belongs on (VS Code, desktop, iOS, Android, web or PWA, CLI), applying the eight placement rules (one verb per surface, adapt do not port, two-level progressive disclosure, pull help not push tutorials, undo over confirmation, first run succeeds, private by default, one command core with many skins), or filling in a feature-to-surface matrix. Triggers on where should this feature live, which platform first, surface placement, cross-surface consistency, one command core. Companion to the other developer-experience skills."
---

# Developer Experience: Device-Specific Interfaces and the Feature-to-Surface Matrix

> **Part 5 of 9** of the *Developer Experience Blueprint* (plugin `developer-experience`), covering: Part 2: Device-specific interfaces; Feature-to-surface matrix. Sibling skills: `devex-principles-and-feedback-loops`, `devex-cli-and-errors`, `devex-api-sdk-and-docs`, `devex-interfaces-onboarding-and-agents`, `devex-editor-and-desktop-surfaces`, `devex-mobile-and-web-surfaces`, `devex-non-developers-and-visual-design`, `devex-reference`. A reference into a sibling is written *Section name → `skill`*.
>
> **Currency:** the blueprint is dated Oct 23, 2026; its evidence base and the AI-tooling claims age fastest, so re-check those first.
>
> Evidence grades used throughout: **A** = peer-reviewed or large study, **B** = credible practitioner or single study, **C** = vendor or opinion. Thin evidence is flagged where it occurs, and collected under *Where the evidence is weak or conflicting* in `devex-reference`.

# Part 2: Device-specific interfaces

Give each surface the one job it does best, keep the vocabulary identical across all of them, and let a non-developer reach a running result before they ever see code. Part 1 covered the developer's experience; this part covers where each feature should live and how to make a developer product usable by people who are not developers.

**Eight placement rules** (evidence behind each is in the sections that follow):

1. **One verb per surface.** Android's widget guidance starts with "focus on one primary use case"; the same logic applies to a status-bar item, a menu-bar extra or a notification.
2. **Adapt, do not port.** Each platform has its own navigation model, input method and system integration. Keep identity (color, type, tone) consistent and behavior native.
3. **Show the common path first, reveal the rest on request, and stop at two levels.** Nielsen Norman Group's progressive-disclosure guidance says designs deeper than two levels usually perform poorly.
4. **Pull help, not push tutorials.** NN/g (2023) reports that tutorials interrupt users, do not reliably improve task performance and are quickly forgotten; contextual help and teaching empty states work better.
5. **Prefer undo to confirmation dialogs.** Reserve a specific, verb-labelled confirmation for serious irreversible actions.
6. **Make the first run succeed.** Start from a template or sample, show a running result, then let people change one thing. GitHub's move to prebuilt cloud environments cut setup from about 45 minutes to about 10 seconds.
7. **Default to private and safe.** A 2026 scan found thousands of AI-built apps public by default, with sensitive data exposed.
8. **One command core, many skins.** Every button in every interface should call the same underlying command or API that the CLI and AI agents use, so behavior never drifts.

**What this part could and could not verify.** Official pages for VS Code, Android, Windows, MDN, web.dev and NN/g were opened. Apple's Human Interface Guidelines and Google's Material 3 pages did not render for my fetch tool, so iOS-specific advice below is labelled as unverified, and Material 3 research claims come from press coverage of Google's own announcement.

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
