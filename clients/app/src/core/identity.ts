// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Stable and nightly, side by side; stable by default. Declared by `interfaces/identity-interface.ts`. */
import IDENTITIES from './identities.json';
import type { AppIdentitiesInterface, AppIdentity, Channel } from './interfaces/identity-interface';

export class AppIdentities implements AppIdentitiesInterface {
  readonly defaultChannel: Channel = 'stable';

  /** One JSON file, so `app.config.ts` (which cannot import TypeScript) reads the same identities. */
  private static readonly IDENTITIES = IDENTITIES as Readonly<Record<Channel, AppIdentity>>;

  channel(variant: string | undefined): Channel {
    return variant?.trim().toLowerCase() === 'nightly' ? 'nightly' : this.defaultChannel;
  }

  identity(channel: Channel): AppIdentity {
    return AppIdentities.IDENTITIES[channel];
  }
}
