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

Channels: `APP_VARIANT=nightly` builds "krypton nightly" (`org.vibey.krypton.nightly`);
anything else is the stable "krypton" (`org.vibey.krypton`). EAS (`eas.json`) is declared only:
nothing builds or submits until the `EXPO_TOKEN` secret and the store credentials exist. The
`stable` profile is built from `main` and is the default; `nightly` from `develop` with
`APP_VARIANT=nightly`. Keep notes like this one here, not in `eas.json`: EAS validates that file
strictly and refuses any key it does not know (a `"$comment"` key stopped `eas init`).

Not built yet: pairing by QR or code (the hub has no pairing routes; the host token connects
today), mDNS discovery, lane stop/prompt and run start, push notifications and sounds, the
nightly icon badge, Reanimated/Skia motion, Maestro flows.
