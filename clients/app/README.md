<!-- Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)). -->
# Krypton for iOS, Android and the web

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

Channels: `APP_VARIANT=nightly` builds "Krypton Nightly" (`org.vibey.krypton.nightly`);
anything else is the stable "Krypton" (`org.vibey.krypton`). EAS (`eas.json`) is declared only.

Not built yet: pairing by QR or code (the hub has no pairing routes; the host token connects
today), mDNS discovery, lane stop/prompt and run start, push notifications and sounds, the
nightly icon badge, Reanimated/Skia motion, Maestro flows.
