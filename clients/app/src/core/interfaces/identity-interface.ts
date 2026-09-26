// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The two channels every Krypton GUI ships (plan, Lane K): stable from `main`, nightly from
 * `develop`. They install side by side, so each has its own name, identifiers and scheme.
 * Stable is always the default.
 */
export type Channel = 'stable' | 'nightly';

export interface AppIdentity {
  readonly channel: Channel;
  /** What a person sees under the icon. */
  readonly name: string;
  readonly slug: string;
  /** The URL scheme pairing links open. */
  readonly scheme: string;
  readonly iosBundleIdentifier: string;
  readonly androidPackage: string;
  /** The EAS Update channel. */
  readonly updateChannel: string;
}

export interface AppIdentitiesInterface {
  readonly defaultChannel: Channel;
  /** The channel an `APP_VARIANT` value names; anything else is the default. */
  channel(variant: string | undefined): Channel;
  identity(channel: Channel): AppIdentity;
}
