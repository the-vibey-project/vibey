---
id: skill-web-and-pwa-and-the-cross-platform-trade-off-052eea5de2
purpose: web and pwa and the cross platform trade off
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-mobile-and-web-surfaces/SKILL.md
requires: ["skill-android-52462dbf9d"]
links: []
---

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
