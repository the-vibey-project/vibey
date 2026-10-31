// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The one hub on this computer, started and stopped from a UI (#1186). */

export type HubAction = 'status' | 'start' | 'stop';

/** What `vibey hub status | start | stop` said, and whether a hub runs now. */
export interface HubReport {
  readonly action: HubAction;
  /** Whether the hub runs after the action. */
  readonly running: boolean;
  /** vibey's own sentence, for the user. */
  readonly message: string;
}

export interface HubEngineInterface {
  /** Runs one action against the hub on this computer. Throws `VibeyCliError` when vibey cannot say. */
  run(action: HubAction): Promise<HubReport>;
  /** Starts the hub unless one already runs: what a UI does when it opens. */
  ensure(): Promise<HubReport>;
}
