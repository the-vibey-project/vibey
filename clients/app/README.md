<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# krypton for iOS, Android and the web

One Expo (SDK 57, Expo Router, TypeScript strict) app over the vibey hub (`vibey serve`,
[hub API](../../docs/reference/hub-api.md), ADR-0068). It reads `@vibey/core` and the design
tokens from source, and keeps its own lockfile outside the npm workspace.

```bash
npm ci
npm test            # core and screens
npm run coverage    # src/core held to 100%
npx expo start --web
```

- `src/core/` — pure logic, each class with its interface beside it: the hub client, pairing
  offers, the device policy (a device never declares paid use, lifts a cap or picks ULTRA
  without one), settings, the stable/nightly identities, presenters and the screen table.
- `src/screens/`, `src/ui/` — the screens, the Kr-84 atom mark and the kit.
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
