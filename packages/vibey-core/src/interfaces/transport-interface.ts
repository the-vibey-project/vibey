// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** How a client reaches vibey: one interface, whichever way the calls travel. */
import type { VibeyCliInterface } from './vibey-cli-interface';

/**
 * `local-process` runs the `vibey` command line on this machine (the extension, the headless
 * CLI); `hub` talks to a vibey hub over the network (mobile, web, and optionally the extension).
 */
export type TransportKind = 'local-process' | 'hub';

/** Every call a client makes to vibey. Both transports answer the same calls with the same shapes. */
export interface VibeyTransportInterface extends VibeyCliInterface {
  readonly kind: TransportKind;
}
