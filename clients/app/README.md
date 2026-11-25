---
description: "Reference for krypton on iOS, Android and the web: the Expo app over the vibey hub, how to install and build it, what each screen does, and what is not built yet."
---

<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# krypton for iOS, Android and the web

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** krypton mobile and web is one Expo app (SDK 57) that talks to a
> vibey hub running on your computer. It opens on **Chat**, shows your projects and the gates
> waiting on you, and can start, pause and unwind a project. Install the Android `.apk` from
> GitHub Releases, or run it on an iPhone with Expo Go; a signed iOS `.ipa` is built only when
> `EXPO_TOKEN` is set and is not on TestFlight or the App Store. Pairing by QR code is not wired
> yet: the app connects with the hub's host token.

> [!IMPORTANT]
> **Work in progress — not a final product:** `krypton` for mobile and web is in active development and is not a finished product. Builds, features, and screen flows are actively evolving. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.

## How to read this page

Daniel had the `.apk` on his phone and a question on his face.

**Daniel:** Professor, where does the work happen, on the phone?

**Professor Feynman:** On your computer. The phone is a window onto it, like a remote for a
television that sits in another room. So step one is always the hub on the computer. The install
steps come first below; the screen table and the "not built yet" list are for looking up what the
remote's buttons do, and which ones are painted on.

## Install and open it

First, on your computer, install vibey and start its hub:

```bash
curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
vibey hub start
```

The hub reads vibey's database, so PostgreSQL and `VIBEY_PG_URL` must be set up first; the
[install guide](../../docs/guides/install.md) walks through it.

Then install the app on your device:

- **Android phone or tablet (`.apk`):**
  1. On your Android device, open [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and tap **`krypton-android-<version>.apk`** to download it.
  2. Tap the downloaded file, allow **Install unknown apps** if Android asks, and tap **Install** (or from a computer with USB debugging: `adb install krypton-android-<version>.apk`).
- **iPhone or iPad:**
  - **Expo Go (no Apple Developer account needed):** install **Expo Go** from the App Store, then on your computer, in `clients/app`, run `npm ci && npx expo start` and scan the QR code with your iPhone camera.
  - **Release build (`.ipa`):** while the `EXPO_TOKEN` secret is set, each release builds a signed `krypton-ios-<version>.ipa` and attaches it to the GitHub Release. Nothing submits it to TestFlight or the App Store yet.
- **Web browser:** download **`krypton-web-<version>.tar.gz`** from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) (or [krypton-nightly](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly)) and serve the unpacked folder:

  ```bash
  mkdir -p ~/krypton-web && tar -xzf ~/Downloads/krypton-web-*.tar.gz -C ~/krypton-web && python3 -m http.server 8000 -d ~/krypton-web
  ```

  Then open [http://localhost:8000](http://localhost:8000). It opens on the **Chat** tab.

  Not verified: the hub sends no CORS headers by design (`src/vibey/infrastructure/hub/app.py`),
  so a browser page served from another origin, such as `localhost:8000`, may be unable to read
  the hub's answers. The hub itself serves only its front door at `http://127.0.0.1:8765/`, not
  this web app.

Want the other krypton interfaces (desktop on macOS and Linux, the VS Code extension, or
`vibey connect` for Claude Code and Codex)? See [docs/guides/install.md](../../docs/guides/install.md)
and [docs/guides/downloads.md](../../docs/guides/downloads.md).

## Build and test

One Expo (SDK 57, Expo Router, TypeScript strict) app over the vibey hub (`vibey serve`,
[hub API](../../docs/reference/hub-api.md), ADR-0068). It reads `@vibey/core` and the design
tokens from source, and keeps its own lockfile outside the npm workspace. Node 20.19.4 or newer.

```bash
npm ci
npm test            # core and screens
npm run coverage    # src/core held to 100%
npx expo start --web
```

`npm run typecheck` runs `tsc --noEmit`; `npm run export:web` builds the web bundle;
`npm run android` and `npm run ios` start Expo for a device. CI runs this app as the `app` job.

- `src/core/` — pure logic, each class with its interface beside it: the hub client, the chat
  model (`/` slash-command table, completion, `POST /api/v1/chat/messages` turn parser and
  spend-gate badges, ADR-0100), pairing offers, the device policy (a device never declares paid
  use, lifts a cap or picks ULTRA without one), the notification planner, settings, the
  stable/nightly identities, presenters, the workflow runs, and the screen table.
- `src/screens/`, `src/ui/` — the screens (with **Chat** as the landing tab), the Kr-84 atom
  mark and the kit.
- `app/` — the routes only.

## Screens

From the screen table in `src/core/screens.ts`:

| Screen | Route | Tab | What it does | Gap the table records |
|---|---|---|---|---|
| Chat | `/` | yes | The landing tab: talk to the hub, `/` commands, gates as cards. | |
| Home | `/projects` | yes | Projects and their phases; start, pause and unwind a project (ADR-0091). | |
| Gates | `/gates` | yes | Every gate waiting on you. | |
| Lanes | `/lanes` | yes | Lanes running on the hub's computer. | Stop, wind down and prompt wait for hub routes; the list refreshes rather than streams. |
| Loops & Effort | `/effort` | yes | The loops, engines and effort ladder. | The choice is shown and checked; the hub has no route to start a run yet. |
| Settings | `/settings` | yes | Theme, sounds, and which notifications to show. | |
| Budgets | `/budgets` | no | Spend against caps. | |
| Devices | `/devices` | no | This device and its pairing. | Listing and revoking other devices waits for the hub pairing routes. |
| Doctor | `/doctor` | no | The checks the hub runs itself. | |
| Run on GitHub | `/workflows` | no | A vibey command run on the repository's GitHub-hosted runners, as `vibey -w` runs it (ADR-0085). | The output arrives when the run ends; it is not streamed. |
| Welcome | `/pair` | no | First run and connecting to a hub. | Pairing by QR or code waits for the hub pairing routes; the host token connects today. |

Two more routes exist outside the table: `/start` (say what to build; the host makes the folder
and starts the project and its worker) and `/usage`, which shows fixed placeholder figures and
reads nothing from the hub.

A project's controls go through the hub's routes `work/start`, `work/pause` and `abandon`
(`src/core/hub-client.ts`). Notifications are local: the app plans them (a new gate, a spending
gate as its own class, a project that finished or was unwound) and shows them through
`expo-notifications`, with sound when sounds are on.

## The hub on your computer

The app is a client of a hub on another computer (reached over your network once paired). It
never runs `vibey`, and the hub API has no route that starts or stops the hub (list them in
[hub-api.json](../../docs/reference/hub-api.json): only a project's own `work/start`,
`work/pause` and `abandon` exist), so **this app can never start a second hub**: one hub per user
holds without any code here. Nor does it add a remote way to start or stop one; that would give a
paired device authority it was not granted (ADR-0067/0068, SD-01).

What it does when the hub does not answer (#1186):

- Says that the hub on your computer is not running, and shows `vibey hub start` with a
  Copy button, to run on that computer. It does nothing if a hub already runs there. Closing
  a krypton app, on any device, never stops the hub.
- Asks `GET /health/live` again by itself, after 2, 4, 8 ... up to 60 seconds (30 seconds
  while the hub answers), and loads the screen again the moment it answers. It asks only
  while the app is in front, never in the background.
- Shows the status on Home and Doctor: reachable or not, the address, and since when.

## Channels and release builds

`APP_VARIANT=nightly` builds "krypton nightly" (`org.vibey.krypton.nightly`); anything else is the
stable "krypton" (`org.vibey.krypton`). Each identity is its own EAS project, owned by the Expo
organisation `the-vibey-project` (`easOwner` and `easProjectId` in `src/core/identities.json`),
and EAS keeps the build number (`appVersionSource: "remote"`). The `stable` profile is built from
`main` and is the default; `nightly` from `develop` with `APP_VARIANT=nightly`. A release builds
the stable iOS app on a macOS runner with `eas build --local` while the `EXPO_TOKEN` secret is set,
signed for the App Store with the Apple credentials EAS holds, and attaches the `.ipa` (see the
[downloads page](../../docs/guides/downloads.md)); nothing submits it to TestFlight or the App
Store yet. Keep notes like this one here, not in `eas.json`: EAS validates that file strictly and
refuses any key it does not know (a `"$comment"` key stopped `eas init`).

## Not built yet

- Pairing by QR or code. The hub's pairing routes exist (ADR-0071), but the app does not call
  them yet; the host token connects today. The app's QR reader also expects `krypton:` and
  `krypton-nightly:` links, while the hub and the desktop app use `vibey-pair://`
  (`src/core/pairing.ts`), so the two do not match yet.
- mDNS discovery of hubs on the network.
- Lane stop, wind-down and prompt, and starting a run from Loops & Effort.
- Remote push notifications (local notifications are built), the nightly icon badge,
  Reanimated/Skia motion, and Maestro flows.
- A Usage screen backed by real figures.

Screen readers: what the app does, what a test proves about it, and the VoiceOver and TalkBack
checks nobody has run yet are in [ACCESSIBILITY.md](ACCESSIBILITY.md).

## Where next

- [The hub API](../../docs/reference/hub-api.md): every route the app calls.
- [krypton desktop](../desktop/README.md): the desktop client, which already pairs by code.
- [@vibey/core](../../packages/vibey-core/README.md): the shared TypeScript the app reads from
  source.

## Say it in one line

krypton mobile and web is a remote for the vibey hub on your computer: chat, projects and gates
on your phone or browser, with pairing still to come.
