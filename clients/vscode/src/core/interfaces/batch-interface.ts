// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** A folder of task files, run one at a time, each on its own branch, resumable from its journal. */
import type { Effort, EffortSetting, LoopName } from './catalogue-interface';
import type { RunOutcome, RunRecord, RunRequest, TaskRunInterface } from './run-interface';
import type { TaskFile } from './task-file-interface';

export interface BatchOptions {
  /** The folder of `*.md` task files. */
  readonly directory: string;
  /** A directory inside the git repository the tasks work on. */
  readonly repository: string;
  /** What every task's branch starts from; resolved once and recorded. Empty means HEAD. */
  readonly baseRef: string;
  /** The journal file; kept on durable storage. */
  readonly journal: string;
  /** The Conventional Commits type of a task with no `commit_message` or `title`. */
  readonly commitType: string;
  readonly contextWindow: number;
  readonly loop: LoopName;
  /** The effort every task runs at unless its file says otherwise; `auto` climbs the ladder. */
  readonly effort: EffortSetting;
  readonly baseEffort: Effort;
  /** `auto`, an engine id, or `engine/model`. */
  readonly engine: string;
}

export interface BatchListener {
  onPlanned?(tasks: readonly TaskFile[], skipped: readonly TaskFile[], pending: readonly TaskFile[]): void;
  onNote?(text: string): void;
  onTaskStarted?(task: TaskFile, run: TaskRunInterface, index: number, total: number): void;
  onTaskFinished?(task: TaskFile, record: RunRecord): void;
}

export interface BatchSummary {
  readonly journal: string;
  readonly batchId: string;
  readonly baseSha: string;
  readonly total: number;
  readonly skipped: number;
  readonly ran: number;
  readonly outcomes: Readonly<Partial<Record<RunOutcome, number>>>;
  /** Why the batch stopped before its last task: an error, or a person's stop. */
  readonly halted?: string;
  /** Tasks not yet finished: what the next run of the same command will do. */
  readonly remaining: number;
}

export interface BatchRunnerInterface {
  run(options: BatchOptions, listener?: BatchListener): Promise<BatchSummary>;
}

/** Starts one task as a run (through the queue) and hands it back. */
export type RunStarter = (request: RunRequest) => Promise<TaskRunInterface>;
