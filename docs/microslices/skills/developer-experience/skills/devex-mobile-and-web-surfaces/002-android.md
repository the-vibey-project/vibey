---
id: skill-android-52462dbf9d
purpose: android
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-mobile-and-web-surfaces/SKILL.md
requires: ["skill-ios-0effb8cd0f"]
links: ["skill-web-and-pwa-and-the-cross-platform-trade-off-052eea5de2"]
---

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
