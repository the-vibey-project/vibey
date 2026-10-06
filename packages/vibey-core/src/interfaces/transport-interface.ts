// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** How a client reaches vibey: one interface, whichever way the calls travel. */
import type { VibeyCliInterface } from './vibey-cli-interface';
import type { WorkflowsRunnerInterface } from './workflows-interface';

/**
 * `local-process` runs the `vibey` command line on this machine (the extension, the headless
 * CLI); `workflows` runs that same command line, but every call as `vibey --workflows …`, on the
 * repository's GitHub-hosted runners (ADR-0085); `hub` talks to a vibey hub over the network
 * (mobile, web, and optionally the extension).
 */
export type TransportKind = 'local-process' | 'workflows' | 'hub';

/** Every call a client makes to vibey. Every transport answers the same calls with the same shapes. */
export interface VibeyTransportInterface extends VibeyCliInterface {
  readonly kind: TransportKind;
}

/**
 * A transport that can also send any one vibey command line to the workflows and hand back
 * what it printed. Kept beside `VibeyTransportInterface` rather than inside it, so a client
 * whose transport does not offer it yet still satisfies the one interface.
 */
export interface VibeyWorkflowsTransportInterface extends VibeyTransportInterface, WorkflowsRunnerInterface {}
