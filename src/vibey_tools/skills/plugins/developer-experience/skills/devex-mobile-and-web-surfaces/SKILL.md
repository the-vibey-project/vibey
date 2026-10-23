---
name: devex-mobile-and-web-surfaces
description: "Use when designing the mobile or web surface of a developer product: iOS (touch targets, Dynamic Type, sheets, widgets, App Shortcuts, push; evidence flagged unverified against Apple), Android (widget quality tiers, core app quality, notification channels, Sharesheet, WorkManager, Material 3 Expressive), and web or PWA (manifest, installability, beforeinstallprompt on iOS, responsive conventions, cross-platform identity versus native interaction). Triggers on iOS widget, Android widget quality, PWA installable, cross-platform trade-off, what a phone is for. Companion to the other developer-experience skills."
---

# Developer Experience: iOS, Android, and Web/PWA Surfaces

> **Part 7 of 9** of the *Developer Experience Blueprint* (plugin `developer-experience`), covering: iOS; Android; Web and PWA, and the cross-platform trade-off. Sibling skills: `devex-principles-and-feedback-loops`, `devex-cli-and-errors`, `devex-api-sdk-and-docs`, `devex-interfaces-onboarding-and-agents`, `devex-surface-placement`, `devex-editor-and-desktop-surfaces`, `devex-non-developers-and-visual-design`, `devex-reference`. A reference into a sibling is written *Section name → `skill`*.
>
> **Currency:** the blueprint is dated Oct 23, 2026; its evidence base and the AI-tooling claims age fastest, so re-check those first.
>
> Evidence grades used throughout: **A** = peer-reviewed or large study, **B** = credible practitioner or single study, **C** = vendor or opinion. Thin evidence is flagged where it occurs, and collected under *Where the evidence is weak or conflicting* in `devex-reference`.

## iOS

**Evidence status: unverified against Apple.** Apple's Human Interface Guidelines pages returned only metadata when fetched, so nothing below is cited to Apple directly. It comes from a mobile-development reference and a UI/UX reference loaded in this session (secondary sources). Treat it as a checklist to confirm against the current HIG before building.

**Baseline rules (secondary sources):**

- Touch targets are at least 44 x 44 pt.
- Support Dynamic Type, so text grows with the user's system setting.
- Use sheets for focused sub-tasks and alerts sparingly; modality is a strong statement.
- Back is the top-left control plus an edge swipe; do not invent your own.
- Respect dark mode, Reduce Motion and Reduce Transparency.
- The reference notes that iOS 26 Liquid Glass applies to framework chrome automatically on recompile, but not to custom components, and that it has drawn legibility criticism.

**Where features belong on a phone** (placement is my recommendation, not a finding):

| Feature | Place |
| --- | --- |
| Glanceable status | Home or Lock Screen widget |
| One-tap action | App shortcut or system action, so it works from Siri, Spotlight and Shortcuts |
| Needs attention | Push notification (APNs) with a clear action, and a badge only for real counts |
| Review and approve | Full-screen detail with a primary button and a sheet for the confirmation |
| Browse history | Tab or list with search |
| Settings | One screen, few options, sensible defaults |

**What a phone is for in a developer product.** Monitoring, approving, triggering a known action and reading results. It is a poor place to author code. Say so honestly in the design: a mobile app that tries to be an editor tends to be a worse editor; one that is a good remote control and reader is useful.

**For non-developers.** Sign in with the system's passkey or provider flow, no API keys to paste, and results shown as cards rather than logs. Offer "Share" so a result can leave the app as a link or file.

**Gaps to close before building:** the current HIG on widgets, notifications and App Intents; App Store review rules for apps that run code; and background execution limits.

## Android

Android has the best first-party evidence of the mobile platforms, because Google publishes quality tiers. Sources: the Android developer pages on [widget quality](https://developer.android.com/design/ui/mobile/guides/widgets/widget-quality), [widget design](https://developer.android.com/design/ui/mobile/guides/widgets) and [core app quality](https://developer.android.com/docs/quality-guidelines/core-app-quality), plus a mobile-development reference loaded in this session.

**What is verified from Google's pages:**

- Widgets are graded by quality tiers, so "has a widget" is not the bar; a widget should resize sensibly, follow the system theme and show current content.
- Core app quality sets baseline expectations for visual design, behavior, performance, stability and security, and navigation (including the system Back).

**From secondary sources (verify before relying on them):**

- Touch targets are at least 48 x 48 dp.
- Notifications belong in channels the user can mute individually; Sharesheet is the way to receive and send content to other apps.
- Material 3 Expressive (announced May 2025) is an enhancement to Material 3. Google reports 46 studies with over 18,000 participants and says key elements were spotted up to 4 times faster. These are Google's own figures reported through the press and the UI reference, not independently reproduced; do not quote the multipliers as universal.

**Where features belong on Android** (placement is my recommendation):

| Feature | Place |
| --- | --- |
| Glanceable status | Home screen widget at the quality tier Google describes |
| Quick action | App shortcut (long-press) and a Quick Settings tile if the action is a toggle |
| Needs attention | Notification in its own channel, with action buttons |
| Receive content | Share target, so a user can send a file or link straight in |
| Main workflow | Single-activity app with a navigation bar (phones) and a rail (tablets, foldables) |
| Background work | WorkManager for guaranteed, deferrable work |

**Android-specific traps** (secondary source): the older Jetpack Security Crypto library is deprecated in favor of using Android Keystore directly, so do not start new secure-storage work on it.

**For non-developers.** The same rules as iOS: no key pasting, results as cards, a Share action. Android's share sheet and widgets make a "one tap, then see the result" loop easier than on most platforms.

## Web and PWA, and the cross-platform trade-off

The web is the one surface that reaches every device without an app-store gate, and it is the natural home for anything a non-developer should be able to open from a link. Sources: [MDN on installable PWAs](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable) and the [web.dev PWA checklist](https://web.dev/articles/pwa-checklist).

**What is verified:**

- A web app becomes installable with a web app manifest and HTTPS. A service worker is not required for installability in current browsers, though it is needed for offline use.
- Browsers differ in how installation is offered. The `beforeinstallprompt` event is not supported on iOS; there, users install from the Share menu, so the product should show a short instruction instead of waiting for a prompt.

**Web conventions to keep** (from the UI/UX platform reference): links are real links, Back works, forms submit on Enter, autofill works, zoom is never disabled, and the page respects `prefers-color-scheme`, `prefers-reduced-motion` and `prefers-contrast`.

**Where features belong on the web:**

| Feature | Place |
| --- | --- |
| First run and try-it | The public page itself, no install and no account for the first result |
| Sharing a result | A stable URL |
| Main workflow | Responsive app with the same task model as the other surfaces |
| Repeat use | Installable PWA, with push only if the user opts in |
| Heavy authoring | Link out to the editor extension or desktop app |

**Cross-platform trade-off.** The UI/UX reference gives the defensible split: be consistent in identity (color, type, tone, icons, illustration) and native in interaction (navigation, gestures, controls, system integration). Users forgive different-looking more readily than different-behaving. Native components also carry accessibility, localization and dark mode for free; a custom look has to rebuild each of those.

**One command core.** Every surface should call the same underlying command or API the CLI uses, so a button in the editor, a widget on a phone and an agent in a terminal all do the same thing and produce the same result.
