<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# krypton for iOS, Android and the web

> [!IMPORTANT]
> **Work in progress — not a final product:** `krypton` for mobile and web is in active development and is not a finished product. Builds, features, and screen flows are actively evolving. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.
>
> **Bottom Line Up Front (BLUF) — How to install and open krypton on Android, iOS, and the Web (no coding experience needed):**
>
> Make sure a vibey hub is running on your computer (`curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton && vibey hub start`). Then install the app on your device:
>
> - **Web Browser (any computer or phone browser — Safari, Chrome, Firefox, Edge):**
>   1. Download **`krypton-web-<version>.tar.gz`** from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) (or [krypton-nightly](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly)).
>   2. In Terminal, unpack and serve it:
>      ```bash
>      mkdir -p ~/krypton-web && tar -xzf ~/Downloads/krypton-web-*.tar.gz -C ~/krypton-web && python3 -m http.server 8000 -d ~/krypton-web
>      ```
>   3. Open **[http://localhost:8000](http://localhost:8000)** in your browser. It opens directly into the **Chat** tab.
> - **Android Phone or Tablet (`.apk`):**
>   1. On your Android device, open [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and tap **`krypton-android-<version>.apk`** to download it.
>   2. Tap the downloaded file, allow **Install unknown apps** if Android asks, and tap **Install** (or from a computer with USB debugging: `adb install krypton-android-<version>.apk`).
> - **iOS (iPhone or iPad):**
>   - **Release build (`.ipa`):** When `EXPO_TOKEN` is configured, each release builds the signed `krypton-ios-<version>.ipa` for Apple **TestFlight / App Store** distribution.
>   - **Instant run with Expo Go (no Apple Developer account needed):** Install **Expo Go** from the App Store on your iPhone, then on your computer in `clients/app` run `npm ci && npx expo start` and scan the QR code with your iPhone Camera.
> - **Want the other krypton interfaces too (Desktop on macOS & Linux, VS Code extension, or `vibey connect` for Claude Code / Codex)?** See [docs/guides/install.md](../../docs/guides/install.md) and [docs/guides/downloads.md](../../docs/guides/downloads.md).

One Expo (SDK 57, Expo Router, TypeScript strict) app over the vibey hub (`vibey serve`,
[hub API](../../docs/reference/hub-api.md), ADR-0068). It reads `@vibey/core` and the design
tokens from source, and keeps its own lockfile outside the npm workspace.

```bash
npm ci
npm test            # core and screens
npm run coverage    # src/core held to 100%
npx expo start --web
```

- `src/core/` — pure logic, each class with its interface beside it: the hub client, the chat
  model (`/` slash-command table, completion, `POST /api/v1/chat/messages` turn parser and
  spend-gate badges, ADR-0100), pairing offers, the device policy (a device never declares paid
  use, lifts a cap or picks ULTRA without one), settings, the stable/nightly identities,
  presenters and the screen table.
- `src/screens/`, `src/ui/` — the screens (with **Chat** as the landing tab), the Kr-84 atom
  mark and the kit.
- `app/` — the routes only.

## The hub on your computer

The app is a client of a hub on another computer (reached over your network once paired). It
never runs `vibey`, and the hub API has no route that starts or stops the hub (list them in
[hub-api.json](../../docs/reference/hub-api.json): only a project's own `work/start` and
`work/pause` exist), so **this app can never start a second hub**: one hub per user holds
without any code here. Nor does it add a remote way to start or stop one; that would give a
paired device authority it was not granted (ADR-0067/0068, SD-01).

What it does when the hub does not answer (#1186):

- Says that the hub on your computer is not running, and shows `vibey hub start` with a
  Copy button, to run on that computer. It does nothing if a hub already runs there. Closing
  a krypton app, on any device, never stops the hub.
- Asks `GET /health/live` again by itself, after 2, 4, 8 ... up to 60 seconds (30 seconds
  while the hub answers), and loads the screen again the moment it answers. It asks only
  while the app is in front, never in the background.
- Shows the status on Home and Doctor: reachable or not, the address, and since when.

Channels: `APP_VARIANT=nightly` builds "krypton nightly" (`org.vibey.krypton.nightly`);
anything else is the stable "krypton" (`org.vibey.krypton`). Each identity is its own EAS
project, owned by the Expo organisation `the-vibey-project` (`easOwner` and `easProjectId`
in `src/core/identities.json`), and EAS keeps the build number (`appVersionSource: "remote"`).
The `stable` profile is built from `main` and is the default; `nightly` from `develop` with
`APP_VARIANT=nightly`. A release builds the stable iOS app on a macOS runner with
`eas build --local` while the `EXPO_TOKEN` secret is set, signed for the App Store with the
Apple credentials EAS holds, and attaches the `.ipa` (see the
[downloads page](../../docs/guides/downloads.md)); nothing submits it to TestFlight or the
App Store yet. Keep notes like this one here, not in `eas.json`: EAS validates that file
strictly and refuses any key it does not know (a `"$comment"` key stopped `eas init`).

Not built yet: pairing by QR or code (the hub's pairing routes exist, ADR-0071, but the app
does not call them yet; the host token connects today), mDNS discovery, lane stop/prompt and run start, push notifications and sounds, the
nightly icon badge, Reanimated/Skia motion, Maestro flows.

Screen readers: what the app does, what a test proves about it, and the VoiceOver and TalkBack
checks nobody has run yet are in [ACCESSIBILITY.md](ACCESSIBILITY.md).
