// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Running a vibey command on the repository's GitHub-hosted runners from a device: what
 * `vibey -w <command>` does on the host, through the hub's workflows routes (ADR-0085).
 */
import type { HubClientInterface, WorkflowRun } from './hub-client-interface';
import type { StatusRole } from './presenters-interface';

/** A typed command line, split into the argv the hub takes. */
export type CommandLineParse = { readonly ok: true; readonly argv: readonly string[] } | { readonly ok: false; readonly reason: string };

/** How long to wait between reads, how long before giving up, and the clock to measure both by. */
export interface WorkflowRunsTiming {
  readonly sleep?: (ms: number) => Promise<void>;
  /** Milliseconds; `Date.now` unless a test brings its own. */
  readonly now?: () => number;
  /** 10 seconds by default, as `vibey -w` polls. */
  readonly everyMs?: number;
  /** 60 minutes by default, as `vibey -w` waits. */
  readonly giveUpMs?: number;
}

/** What a screen hears while a run is followed. */
export interface WorkflowFollowHooks {
  /** Every state the hub reports, the first one included. */
  readonly onUpdate?: (run: WorkflowRun) => void;
  /** True once nobody is watching any more, so no further request is sent. */
  readonly cancelled?: () => boolean;
}

/** How following a run ended: it finished, or the wait stopped while it carries on. */
export type WorkflowOutcome =
  | { readonly kind: 'finished'; readonly run: WorkflowRun }
  | { readonly kind: 'still-running'; readonly run: WorkflowRun; readonly message: string };

/** A run's state, as a screen shows it. */
export interface WorkflowRunView {
  /** "Queued", "Running", "Done · exit 0", "Failed". */
  readonly label: string;
  readonly role: StatusRole;
  readonly finished: boolean;
}

export interface WorkflowRunsInterface {
  /** Splits on white space; double quotes keep a phrase as one word. A leading `vibey` and `-w` are dropped. */
  split(line: string): CommandLineParse;
  /** Starts the command and reads its state until it finishes or the wait gives up. HTTP refusals reject. */
  follow(
    client: Pick<HubClientInterface, 'startWorkflowRun' | 'workflowRun'>,
    argv: readonly string[],
    hooks?: WorkflowFollowHooks,
  ): Promise<WorkflowOutcome>;
  present(run: WorkflowRun): WorkflowRunView;
}
