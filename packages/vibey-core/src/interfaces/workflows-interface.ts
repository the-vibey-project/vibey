// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * One vibey command line run on the repository's GitHub-hosted runners instead of here:
 * `vibey -w <command>` on the command line, `POST /api/v1/workflows/runs` on a hub (ADR-0085).
 */
import type { CompletedProcess } from './process-runner-interface';
import type { ClockInterface } from './support-interface';

/** Where a command sent to the workflows is, as the hub reports it. */
export type WorkflowsState = 'queued' | 'running' | 'done' | 'failed';

/** What a command run on the workflows handed back, read the same whichever transport sent it. */
export interface WorkflowsRunResult {
  /**
   * The remote command's own exit code once it ran; otherwise `vibey -w`'s: 2 when the command
   * line or the settings were refused, 1 when GitHub refused or the run handed back no report,
   * 124 when the wait ran out.
   */
  readonly exitCode: number;
  readonly stdout: string;
  readonly stderr: string;
  /** The run on GitHub, once GitHub showed it; '' when it never did. */
  readonly url: string;
}

/** Where a command is while it is waited for: its state, and its run's address once known. */
export interface WorkflowsUpdate {
  readonly state: string;
  readonly url: string;
}

export interface WorkflowsRunOptions {
  /** How often to look again. Default 10 seconds, as `vibey -w` looks. */
  readonly pollMs?: number;
  /** How long to wait for the run's report. Default 60 minutes, as `vibey -w` waits. */
  readonly timeoutMs?: number;
  /**
   * The folder the command line is run from: `vibey -w` sends to that folder's GitHub
   * repository unless VIBEY_WORKFLOWS_REPOSITORY names one. A hub reads its own settings.
   */
  readonly cwd?: string;
  /** Told each state the hub reports while the command waits; the command line reports none. */
  readonly onUpdate?: (update: WorkflowsUpdate) => void;
}

/** Runs one vibey command line on the workflows and hands back what it printed. */
export interface WorkflowsRunnerInterface {
  /** `argv` without `vibey` or `-w`: `["status", "--json"]`. Rejects when it is refused before it is sent. */
  runOnWorkflows(argv: readonly string[], options?: WorkflowsRunOptions): Promise<WorkflowsRunResult>;
}

/** How long waits are measured: the part of a clock a poll loop needs, injected so tests do not wait. */
export type TimerInterface = Pick<ClockInterface, 'sleep' | 'monotonic'>;

/** A command line for the workflows, read and checked once, and its report as words. */
export interface WorkflowsCommandLineInterface {
  /**
   * What a person typed, as argv: double or single quotes group words, a backslash escapes,
   * and a leading `vibey` and `-w`/`--workflows` are dropped. A string is why it cannot run.
   */
  parse(text: string): readonly string[] | string;
  /** Why `argv` cannot be sent (empty, over 200 words, or still naming `vibey` or `-w`); undefined when it can. */
  check(argv: readonly string[]): string | undefined;
  /** What `vibey --workflows …` printed, with its `ran on GitHub` line read out of stderr as the run's address. */
  fromProcess(completed: Pick<CompletedProcess, 'code' | 'stdout' | 'stderr'>): WorkflowsRunResult;
  /** One hub status document: the result once the command is over, and where it is in any case. */
  fromHub(status: unknown): { readonly update: WorkflowsUpdate; readonly result?: WorkflowsRunResult };
  /** What a wait that ran out reads as: 124, as `vibey -w` exits. */
  timedOut(url: string, timeoutMs: number): WorkflowsRunResult;
  /** The result as lines for an output view: the command, its run, its exit code, and what it printed. */
  report(argv: readonly string[], result: WorkflowsRunResult): readonly string[];
  /** One sentence for a notification or a chat reply. */
  summary(argv: readonly string[], result: WorkflowsRunResult): string;
}
