// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** One task, run by qwenloop on the local model, from request to recorded result. */
import type { ChangedFile, GitClientInterface } from './git-interface';
import type { JsonlTailInterface } from './jsonl-interface';
import type { ModelSlotLockInterface } from './model-lock-interface';
import type { ProcessRunnerInterface } from './process-runner-interface';
import type { QwenloopCommandInterface, QwenloopRunConfigInterface } from './qwenloop-interface';
import type { RunFailure, RunItem, RunPatch } from './run-events-interface';
import type { ResolvedSettings } from './settings-interface';
import type { DurabilityGateInterface } from './storage-interface';
import type { SourceEnvironment } from './environment-interface';
import type {
  ClockInterface,
  Disposable,
  IdSourceInterface,
  TaskNamingInterface,
} from './support-interface';

export interface RunRequest {
  /** The plan qwenloop is given, verbatim. */
  readonly task: string;
  readonly title: string;
  /** A directory inside the git repository the task works on. */
  readonly directory: string;
  readonly inPlace: boolean;
  /** The branch or commit the task's copy starts from; empty means HEAD. */
  readonly baseRef: string;
  /** A base already resolved (a batch resolves it once); wins over `baseRef`. */
  readonly baseSha?: string;
  readonly contextWindow: number;
  readonly maxTurns?: number;
  readonly effort: string;
  /** What the finished work is committed as, on the task's own branch. */
  readonly commitMessage: string;
  /** What the branch and worktree are named after: the title, or a task file's stem. */
  readonly slugSource: string;
  readonly origin: 'ask' | 'batch';
  /** The task file a batch run came from. */
  readonly source?: string;
}

export interface RunWorkspace {
  readonly mode: 'worktree' | 'in-place';
  /** The top of the person's repository. */
  readonly repository: string;
  /** Where qwenloop runs: the worktree, or the repository itself when in place. */
  readonly cwd: string;
  /** The task's own branch (worktree), or whatever was checked out (in place). */
  readonly branch?: string;
  readonly baseRef: string;
  readonly baseSha: string;
}

export type RunStatus = 'queued' | 'preparing' | 'waiting' | 'running' | 'stopping' | 'finishing' | 'finished';

export type RunOutcome =
  | 'completed'
  | 'completed-no-change'
  | 'completed-commit-refused'
  | 'failed'
  | 'wound-down'
  | 'error';

/** A finished run as the journals keep it: snake_case, JSON-safe, one line. */
export interface RunRecord {
  readonly run_id: string;
  readonly title: string;
  readonly origin: 'ask' | 'batch';
  readonly source?: string;
  readonly outcome: RunOutcome;
  readonly exit_code: number | null;
  readonly signal: string | null;
  readonly model: string;
  readonly context_window: number;
  readonly max_turns?: number;
  readonly mode?: 'worktree' | 'in-place';
  readonly repository?: string;
  readonly cwd?: string;
  readonly branch?: string;
  readonly base_ref?: string;
  readonly base_sha?: string;
  readonly head_sha?: string;
  readonly diff_stat: string;
  readonly changed_files: readonly ChangedFile[];
  readonly uncommitted: readonly string[];
  readonly verdict?: string;
  readonly marker: boolean;
  readonly failure?: RunFailure;
  readonly error?: string;
  readonly commit_error?: string;
  readonly turns: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly started_at: string;
  readonly finished_at: string;
  readonly duration_ms: number;
  readonly run_directory: string;
  readonly events_path?: string;
  readonly plan_path: string;
  readonly qwenloop_config: string;
  readonly argv: readonly string[];
}

export interface RunServices {
  readonly settings: ResolvedSettings;
  readonly git: GitClientInterface;
  readonly processes: ProcessRunnerInterface;
  readonly qwenloop: QwenloopCommandInterface;
  readonly runConfig: QwenloopRunConfigInterface;
  /** The person's own qwenloop config file, when they have one. */
  readonly userConfig: () => { readonly path: string; readonly text: string } | undefined;
  readonly gate: DurabilityGateInterface;
  readonly tail: JsonlTailInterface;
  readonly lock: ModelSlotLockInterface;
  readonly clock: ClockInterface;
  readonly ids: IdSourceInterface;
  readonly naming: TaskNamingInterface;
  readonly history: RunHistoryInterface;
  /** The editor's environment, which the child's allow-list is built from. */
  readonly environ: SourceEnvironment;
}

export interface QwenloopRunInterface {
  readonly runId: string;
  readonly request: RunRequest;
  readonly status: RunStatus;
  readonly workspace: RunWorkspace | undefined;
  items(): readonly RunItem[];
  onPatch(listener: (patch: RunPatch) => void): Disposable;
  onStatus(listener: (status: RunStatus) => void): Disposable;
  /** Start and run to the end. Called once, by the queue, when the run's turn comes. */
  execute(): Promise<RunRecord>;
  /** Send a follow-up message; resolves with an error message when it could not be sent. */
  followUp(text: string): Promise<string | undefined>;
  /** Ask qwenloop to finish its turn and stop (exit 75). Before it starts, it never starts. */
  stop(): Promise<string | undefined>;
  /** End the process now (SIGTERM). Only ever at a person's request; nothing stops a run for being slow. */
  forceStop(): void;
  readonly result: Promise<RunRecord>;
}

export interface RunHistoryEntry {
  readonly record: RunRecord;
  readonly applied?: string;
  readonly discarded?: string;
}

export interface RunHistoryInterface {
  finished(record: RunRecord): void;
  applied(runId: string, detail: string): void;
  discarded(runId: string): void;
  /** Every recorded run, newest first, with what happened to it since. */
  list(): readonly RunHistoryEntry[];
}
