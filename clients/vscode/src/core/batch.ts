// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * A folder of task files, run one at a time through the same run machinery the editor uses,
 * each task on its own worktree and branch, all from one base commit.
 *
 * The journal is the batch's memory, and it is append-only JSON lines, each fsynced before
 * the next step (the StepJournal idea of sub-doctrine 10.h):
 *
 *   batch.opened     once: the folder, the repository, the base ref and the SHA it resolved to
 *   batch.resumed    every later start
 *   task.started     a task's run has its worktree and is about to use the model
 *   task.finished    its outcome, branch, base and head SHAs, diff and verdict
 *   task.interrupted a start found a task started and never finished (the process died)
 *   batch.halted     the batch stopped early, and why
 *
 * Running the same command again resumes. A task is identified by its file name and the
 * sha256 of its content, so an edited file is a new task. Finished tasks whose outcome is
 * completed (with or without a change, or with its commit refused) or failed are skipped;
 * a task that was stopped, interrupted or hit an infrastructure error runs again, on a new
 * branch, with the earlier worktree left for a person to look at. The base is the one the
 * journal recorded, never resolved again, so every task of one batch starts from the same
 * commit. An infrastructure error (qwenloop missing, Ollama down) or a person's stop halts
 * the batch rather than failing every remaining task the same way. Declared by
 * `interfaces/batch-interface.ts`.
 */
import * as fs from 'node:fs';
import type {
  BatchListener,
  BatchOptions,
  BatchRunnerInterface,
  BatchSummary,
  RunStarter,
} from './interfaces/batch-interface';
import type { GitClientInterface } from './interfaces/git-interface';
import type { JsonlJournalInterface } from './interfaces/jsonl-interface';
import type { RunOutcome, RunRecord } from './interfaces/run-interface';
import type { DurabilityGateInterface } from './interfaces/storage-interface';
import type { ClockInterface, IdSourceInterface } from './interfaces/support-interface';
import type { TaskFile, TaskFolderInterface } from './interfaces/task-file-interface';

export interface BatchDependencies {
  readonly folder: TaskFolderInterface;
  readonly git: GitClientInterface;
  readonly gate: DurabilityGateInterface;
  readonly journal: (file: string) => JsonlJournalInterface;
  readonly start: RunStarter;
  readonly clock: ClockInterface;
  readonly ids: IdSourceInterface;
  /** Checked before the first task: an error message when the model cannot run at all. */
  readonly preflight: () => Promise<string | undefined>;
}

export class BatchRunner implements BatchRunnerInterface {
  /** Outcomes that finish a task for good: a resumed batch skips them. */
  static readonly FINAL: ReadonlySet<RunOutcome> = new Set<RunOutcome>([
    'completed',
    'completed-no-change',
    'completed-commit-refused',
    'failed',
  ]);
  static readonly JOURNAL_VERSION = 1;

  constructor(private readonly deps: BatchDependencies) {}

  async run(options: BatchOptions, listener: BatchListener = {}): Promise<BatchSummary> {
    const { deps } = this;
    deps.gate.enforce({ 'batch journal': options.journal });
    const tasks = deps.folder.load(options.directory);
    if (tasks.length === 0) {
      throw new Error(`${options.directory} has no .md task files`);
    }
    const journal = deps.journal(options.journal);
    const lines = journal.readAll().records;
    const repository = await deps.git.toplevel(options.repository);
    const opened = lines.find((line) => line.type === 'batch.opened');
    let batchId: string;
    let baseRef: string;
    let baseSha: string;
    if (opened === undefined) {
      batchId = deps.ids.uuid();
      baseRef = options.baseRef || 'HEAD';
      baseSha = await deps.git.resolveCommit(repository, baseRef);
      journal.append({
        type: 'batch.opened',
        journal_version: BatchRunner.JOURNAL_VERSION,
        batch_id: batchId,
        directory: fs.realpathSync(options.directory),
        repository,
        base_ref: baseRef,
        base_sha: baseSha,
        tasks: tasks.map((task) => ({ file: task.name, sha256: task.sha256 })),
        at: this.now(),
      });
    } else {
      batchId = String(opened.batch_id);
      baseRef = String(opened.base_ref);
      baseSha = String(opened.base_sha);
      if (options.baseRef && options.baseRef !== baseRef) {
        throw new Error(
          `${options.journal} was opened with base ${baseRef} (${baseSha.slice(0, 12)}), not ${options.baseRef}. ` +
            'Every task of one batch starts from the same commit; give --journal a new file to start a batch from another base.',
        );
      }
      journal.append({ type: 'batch.resumed', batch_id: batchId, at: this.now() });
    }

    const state = BatchRunner.state(lines);
    const skipped: TaskFile[] = [];
    const pending: TaskFile[] = [];
    for (const task of tasks) {
      const last = state.get(BatchRunner.key(task.name, task.sha256));
      if (last !== undefined && last.type === 'task.finished' && BatchRunner.FINAL.has(last.outcome as RunOutcome)) {
        skipped.push(task);
        continue;
      }
      if (last !== undefined && last.type === 'task.started') {
        journal.append({
          type: 'task.interrupted',
          file: task.name,
          sha256: task.sha256,
          run_id: last.run_id,
          ...(last.branch === undefined ? {} : { branch: last.branch }),
          ...(last.cwd === undefined ? {} : { cwd: last.cwd }),
          at: this.now(),
        });
        listener.onNote?.(`${task.name} was started and never finished (run ${String(last.run_id)}); it runs again.`);
      }
      pending.push(task);
    }
    listener.onPlanned?.(tasks, skipped, pending);

    const outcomes: Partial<Record<RunOutcome, number>> = {};
    const summary = (ran: number, remaining: number, halted?: string): BatchSummary => ({
      journal: options.journal,
      batchId,
      baseSha,
      total: tasks.length,
      skipped: skipped.length,
      ran,
      outcomes,
      ...(halted === undefined ? {} : { halted }),
      remaining,
    });
    if (pending.length === 0) {
      return summary(0, 0);
    }
    const problem = await deps.preflight();
    if (problem !== undefined) {
      journal.append({ type: 'batch.halted', batch_id: batchId, reason: problem, at: this.now() });
      return summary(0, pending.length, problem);
    }

    let ran = 0;
    for (const [index, task] of pending.entries()) {
      const run = await deps.start({
        task: task.plan,
        title: task.title,
        directory: repository,
        inPlace: false,
        baseRef,
        baseSha,
        contextWindow: task.metadata.contextWindow ?? options.contextWindow,
        ...(task.metadata.maxTurns === undefined ? {} : { maxTurns: task.metadata.maxTurns }),
        loop: options.loop,
        effort: task.metadata.effort ?? options.effort,
        baseEffort: options.baseEffort,
        engine: options.engine,
        commitMessage: task.metadata.commitMessage ?? task.metadata.title ?? `${options.commitType}: ${task.stem}`,
        slugSource: task.stem,
        origin: 'batch',
        source: task.name,
      });
      let recorded = false;
      const started = run.onStatus((status) => {
        const space = run.workspace;
        if (!recorded && status === 'waiting' && space !== undefined) {
          recorded = true;
          journal.append({
            type: 'task.started',
            file: task.name,
            sha256: task.sha256,
            run_id: run.runId,
            ...(space.branch === undefined ? {} : { branch: space.branch }),
            cwd: space.cwd,
            base_sha: space.baseSha,
            context_window: run.request.contextWindow,
            ...(run.request.maxTurns === undefined ? {} : { max_turns: run.request.maxTurns }),
            at: this.now(),
          });
        }
      });
      listener.onTaskStarted?.(task, run, index + 1, pending.length);
      const record = await run.result;
      started.dispose();
      ran += 1;
      outcomes[record.outcome] = (outcomes[record.outcome] ?? 0) + 1;
      journal.append({ type: 'task.finished', file: task.name, sha256: task.sha256, ...record });
      listener.onTaskFinished?.(task, record);
      const halt = BatchRunner.halt(record);
      if (halt !== undefined) {
        journal.append({ type: 'batch.halted', batch_id: batchId, file: task.name, reason: halt, at: this.now() });
        // The task that halted the batch is not finished either: it runs again next time.
        return summary(ran, pending.length - ran + 1, halt);
      }
    }
    return summary(ran, 0);
  }

  /** Why the batch must stop after this record, or undefined to go on. */
  private static halt(record: RunRecord): string | undefined {
    if (record.outcome === 'error') {
      return `an infrastructure error, not a task failure: ${record.error ?? 'unknown'}`;
    }
    if (record.outcome === 'wound-down') {
      return 'the run was stopped';
    }
    if (record.outcome === 'budget-exhausted') {
      return `a budget is used up: ${record.budget?.message ?? 'see the journal'}`;
    }
    return undefined;
  }

  /** The last line recorded for each task, by file name and content. */
  private static state(lines: readonly Record<string, unknown>[]): Map<string, Record<string, unknown>> {
    const state = new Map<string, Record<string, unknown>>();
    for (const line of lines) {
      if (
        (line.type === 'task.started' || line.type === 'task.finished' || line.type === 'task.interrupted') &&
        typeof line.file === 'string' &&
        typeof line.sha256 === 'string'
      ) {
        state.set(BatchRunner.key(line.file, line.sha256), line);
      }
    }
    return state;
  }

  private static key(file: string, sha256: string): string {
    return `${file}\0${sha256}`;
  }

  private now(): string {
    return this.deps.clock.now().toISOString();
  }
}
