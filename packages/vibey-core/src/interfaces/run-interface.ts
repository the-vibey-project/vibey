// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** One task, run by a loop engine, from request to recorded result. */
import type { BudgetBreach, BudgetGuardInterface, SpendLedgerInterface } from './budgets-interface';
import type { Catalogue, Effort, EffortSetting, LoopName, LoopSelectorInterface } from './catalogue-interface';
import type { EngineCommandInterface } from './engine-command-interface';
import type { SourceEnvironment } from './environment-interface';
import type { ChangedFile, GitClientInterface } from './git-interface';
import type { JsonlTailInterface } from './jsonl-interface';
import type { ModelSlotLockInterface } from './model-lock-interface';
import type { ProcessRunnerInterface } from './process-runner-interface';
import type { LocalRunnersInterface, RunnerIdentity } from './local-runner-interface';
import type { QwenloopRunConfigInterface } from './qwenloop-interface';
import type { RunFailure, RunItem, RunPatch } from './run-events-interface';
import type { CatalogueEngine } from './catalogue-interface';
import type { ResolvedSettings } from './settings-interface';
import type { DurabilityGateInterface } from './storage-interface';
import type { ClockInterface, Disposable, IdSourceInterface, TaskNamingInterface } from './support-interface';

/** Something given to a task besides its words: a file, pasted text, or an image. */
export interface Attachment {
  readonly kind: 'file' | 'text' | 'image';
  /** A file's or image's path; for pasted text, a label. */
  readonly name: string;
  /** Pasted text itself; for a file or image, undefined (the file is copied in). */
  readonly text?: string;
}

export interface RunRequest {
  /** The plan the engine is given (attachments and context are added to it). */
  readonly task: string;
  readonly title: string;
  /** A directory inside the git repository the task works on. */
  readonly directory: string;
  readonly inPlace: boolean;
  /** The branch or commit the task's copy starts from; empty means HEAD. */
  readonly baseRef: string;
  /** A base already resolved (a batch resolves it once); wins over `baseRef`. */
  readonly baseSha?: string;
  readonly loop: LoopName;
  readonly effort: EffortSetting;
  /** Where auto effort starts. */
  readonly baseEffort: Effort;
  /** `auto`, an engine id, or `engine/model`. */
  readonly engine: string;
  readonly contextWindow: number;
  /** The task's own turn limit, which wins over the effort's and the setting's. */
  readonly maxTurns?: number;
  /** What the task may change, as repository-relative globs; its commit holds nothing else. */
  readonly paths?: readonly string[];
  /** What the finished work is committed as, on the task's own branch. */
  readonly commitMessage: string;
  /** What the branch and worktree are named after: the title, or a task file's stem. */
  readonly slugSource: string;
  readonly origin: 'ask' | 'batch';
  /** The task file a batch run came from. */
  readonly source?: string;
  readonly attachments?: readonly Attachment[];
  /** A vibey-skills context packet (markdown), added to the plan. */
  readonly contextPacket?: { readonly markdown: string; readonly plugins: readonly string[]; readonly manifest?: string };
}

export interface RunWorkspace {
  readonly mode: 'worktree' | 'in-place';
  /** The top of the person's repository. */
  readonly repository: string;
  /** Where the engine runs: the worktree, or the repository itself when in place. */
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
  /** Completed, with changes outside the task's `paths` left uncommitted for a person to review. */
  | 'completed-out-of-scope'
  | 'failed'
  | 'wound-down'
  | 'budget-exhausted'
  | 'error';

/** One engine run inside a task: auto effort may take several, climbing the ladder. */
export interface AttemptRecord {
  readonly attempt: number;
  readonly run_id: string;
  readonly loop: LoopName;
  readonly tier: 'local' | 'paid';
  readonly engine: string;
  readonly model: string | null;
  readonly effort: Effort;
  readonly effort_source: 'chosen' | 'auto' | 'model';
  readonly max_turns?: number;
  readonly max_turns_source: string;
  /** Why this engine and model, in words. */
  readonly reason: string;
  readonly outcome: RunOutcome;
  readonly exit_code: number | null;
  readonly signal: string | null;
  readonly argv: readonly string[];
  readonly events_path: string;
  readonly turns: number;
}

/** A finished task as the journals keep it: snake_case, JSON-safe, one line. */
export interface RunRecord {
  readonly run_id: string;
  readonly title: string;
  readonly origin: 'ask' | 'batch';
  readonly source?: string;
  readonly outcome: RunOutcome;
  readonly exit_code: number | null;
  readonly signal: string | null;
  readonly loop: LoopName;
  readonly engine?: string;
  readonly model: string | null;
  readonly effort?: Effort;
  readonly catalogue: 'vibey' | 'degraded';
  readonly context_window: number;
  readonly max_turns?: number;
  readonly max_turns_source?: string;
  readonly attempts: readonly AttemptRecord[];
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
  readonly attachments: readonly { readonly kind: string; readonly name: string; readonly placed_at?: string }[];
  readonly context_plugins?: readonly string[];
  readonly verdict?: string;
  readonly marker: boolean;
  readonly failure?: RunFailure;
  readonly error?: string;
  readonly commit_error?: string;
  /** The task's scope, when its task file named one. */
  readonly paths?: readonly string[];
  /** Changed paths outside that scope, left in the task's copy and not committed. */
  readonly out_of_scope?: readonly string[];
  /** The budget that refused this run, or wound it down when it was used up. */
  readonly budget?: { readonly id: string; readonly cap: string; readonly limit: number; readonly spent: number; readonly message: string };
  /** What the run was projected to cost before it started, and where the per-turn figures came from. */
  readonly projection?: { readonly turns?: number; readonly dollars?: number; readonly per_turn: string };
  /** When a person ended the process by force, after a graceful stop had its fair time. */
  readonly force_stopped_at?: string;
  readonly turns: number;
  readonly input_tokens: number;
  readonly output_tokens: number;
  readonly started_at: string;
  readonly finished_at: string;
  readonly duration_ms: number;
  readonly run_directory: string;
  readonly events_path?: string;
  readonly plan_path: string;
  readonly engine_config?: string;
  readonly argv: readonly string[];
}

export interface RunServices {
  readonly settings: ResolvedSettings;
  readonly catalogue: Catalogue;
  readonly selector: LoopSelectorInterface;
  /** The engine's command lines, with its binary found on PATH; an error message otherwise. */
  readonly command: (engine: CatalogueEngine) => EngineCommandInterface | string;
  readonly git: GitClientInterface;
  readonly processes: ProcessRunnerInterface;
  readonly runConfig: QwenloopRunConfigInterface;
  /** The family's local runner under each name: which engines get its settings bound. */
  readonly runners: LocalRunnersInterface;
  /** The person's own config file for a local runner (its `<PREFIX>_CONFIG`, else its platform default), when they have one. */
  readonly userConfig: (runner: RunnerIdentity) => { readonly path: string; readonly text: string } | undefined;
  readonly gate: DurabilityGateInterface;
  readonly tail: JsonlTailInterface;
  /** The cross-process slot for an engine: all local models share one; each paid engine has its own. */
  readonly lockFor: (engine: CatalogueEngine, tier: 'local' | 'paid') => ModelSlotLockInterface;
  readonly clock: ClockInterface;
  readonly ids: IdSourceInterface;
  readonly naming: TaskNamingInterface;
  readonly history: RunHistoryInterface;
  /** Whether the person has declared the paid loop. */
  readonly paidDeclared: () => boolean;
  /** Models Ollama holds in memory now. */
  readonly resident: () => Promise<readonly string[]>;
  readonly budgets: BudgetGuardInterface;
  readonly spend: SpendLedgerInterface;
  /** The editor's environment, which the child's allow-list is built from. */
  readonly environ: SourceEnvironment;
}

export interface TaskRunInterface {
  readonly runId: string;
  readonly request: RunRequest;
  readonly status: RunStatus;
  readonly workspace: RunWorkspace | undefined;
  /** The engine and model of the attempt running now, once chosen. */
  readonly current: { readonly engine: string; readonly model: string | null; readonly effort: Effort } | undefined;
  readonly stopRequestedAt: number | undefined;
  /** Whether the engine running now acts on a follow-up: no prompt box otherwise. */
  readonly takesFollowUps: boolean;
  /** Set when a budget wound this run down or refused it. */
  readonly budgetBreach: BudgetBreach | undefined;
  items(): readonly RunItem[];
  onPatch(listener: (patch: RunPatch) => void): Disposable;
  onStatus(listener: (status: RunStatus) => void): Disposable;
  /** Start and run to the end. Called once, by the queue, when the run's turn comes. */
  execute(): Promise<RunRecord>;
  /** Send a follow-up message; resolves with an error message when it could not be sent. */
  followUp(text: string): Promise<string | undefined>;
  /** Ask the engine to finish its turn and stop. Before it starts, it never starts. */
  stop(): Promise<string | undefined>;
  /**
   * End the process now (SIGTERM): only after a graceful stop has had `fairMs`, and only at a
   * person's request. Nothing stops a run for being slow. The error message when refused.
   */
  forceStop(fairMs: number): string | undefined;
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
  /** A person's force stop, recorded when it happens as well as in the run's result. */
  forceStopped(runId: string, afterMs: number): void;
  /** Every recorded run, newest first, with what happened to it since. */
  list(): readonly RunHistoryEntry[];
}
