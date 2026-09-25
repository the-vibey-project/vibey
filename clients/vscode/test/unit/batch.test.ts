// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** A folder of task files, run one at a time and resumed from its journal. */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { BatchRunner } from '../../src/core/batch';
import type { BatchOptions } from '@vibey/core';
import type { ChangedFile, CommitOutcome, GitClientInterface, MergeOutcome } from '@vibey/core';
import type { RunRecord, RunRequest, RunStatus, RunWorkspace, TaskRunInterface } from '@vibey/core';
import type { VolatileHit } from '@vibey/core';
import type { Disposable } from '@vibey/core';
import type { TaskFile } from '@vibey/core';
import { JsonlJournal } from '../../src/core/jsonl';
import { TaskFolder } from '../../src/core/task-file';
import { FakeClock, SequentialIds, scratch } from './helpers';

const BASE = 'b'.repeat(40);

class RepositoryGit implements GitClientInterface {
  readonly resolved: string[] = [];

  constructor(private readonly repository: string) {}

  async version(): Promise<string> {
    return 'git version 2.47.0';
  }

  async toplevel(): Promise<string> {
    return this.repository;
  }

  async resolveCommit(_repository: string, ref: string): Promise<string> {
    this.resolved.push(ref);
    return BASE;
  }

  async head(): Promise<string> {
    return BASE;
  }

  async uncommitted(): Promise<readonly string[]> {
    return [];
  }

  async currentBranch(): Promise<string | undefined> {
    return 'main';
  }

  async addWorktree(): Promise<void> {}

  async removeWorktree(): Promise<void> {}

  async deleteBranch(): Promise<void> {}

  async branchExists(): Promise<boolean> {
    return false;
  }

  async commitAll(): Promise<CommitOutcome> {
    return { committed: true };
  }

  async diffStat(): Promise<string> {
    return '';
  }

  async changedFiles(): Promise<readonly ChangedFile[]> {
    return [];
  }

  async diff(): Promise<string> {
    return '';
  }

  async merge(): Promise<MergeOutcome> {
    return { ok: true, output: '' };
  }
}

/** A run the batch starts; the test says when it waits for the model and how it ends. */
class ScriptedRun implements TaskRunInterface {
  readonly status: RunStatus = 'queued';
  workspace: RunWorkspace | undefined;
  readonly current = undefined;
  readonly stopRequestedAt = undefined;
  readonly takesFollowUps = false;
  readonly budgetBreach = undefined;
  readonly result: Promise<RunRecord>;
  private readonly listeners = new Set<(status: RunStatus) => void>();
  private finish: (record: RunRecord) => void = () => undefined;

  constructor(
    readonly request: RunRequest,
    readonly runId: string,
  ) {
    this.result = new Promise((resolve) => {
      this.finish = resolve;
    });
  }

  items(): readonly [] {
    return [];
  }

  onPatch(): Disposable {
    return { dispose: () => undefined };
  }

  onStatus(listener: (status: RunStatus) => void): Disposable {
    this.listeners.add(listener);
    return { dispose: () => this.listeners.delete(listener) };
  }

  emit(status: RunStatus): void {
    for (const listener of [...this.listeners]) {
      listener(status);
    }
  }

  get listening(): number {
    return this.listeners.size;
  }

  execute(): Promise<RunRecord> {
    return this.result;
  }

  async followUp(): Promise<string | undefined> {
    return undefined;
  }

  async stop(): Promise<string | undefined> {
    return undefined;
  }

  forceStop(): string | undefined {
    return undefined;
  }

  end(record: Partial<RunRecord>): void {
    this.finish({ run_id: this.runId, outcome: 'completed', ...record } as RunRecord);
  }
}

type Behaviour = (run: ScriptedRun) => void;

/** Waits for the model on a worktree of its own, then ends with `record`. */
function ends(record: Partial<RunRecord>, workspace: Partial<RunWorkspace> = {}): Behaviour {
  return (run) => {
    run.emit('preparing');
    run.emit('waiting');
    run.workspace = {
      mode: 'worktree',
      repository: '/repo',
      cwd: `/storm/${run.runId}`,
      branch: `vibey/${run.request.slugSource}-${run.runId}`,
      baseRef: run.request.baseRef,
      baseSha: run.request.baseSha as string,
      ...workspace,
    };
    run.emit('waiting');
    run.emit('waiting');
    run.emit('running');
    run.end(record);
  };
}

function setup(behaviours: Behaviour[] = [], preflight: () => Promise<string | undefined> = async () => undefined) {
  const home = scratch('vibey-batch-');
  const folder = path.join(home, 'tasks');
  fs.mkdirSync(folder);
  const repository = path.join(home, 'repo');
  const git = new RepositoryGit(repository);
  const requests: RunRequest[] = [];
  const runs: ScriptedRun[] = [];
  const gate = { refuse: false, inspect: (): readonly VolatileHit[] => [], enforce: (): void => undefined };
  const runner = new BatchRunner({
    folder: new TaskFolder(),
    git,
    gate: {
      inspect: () => gate.inspect(),
      enforce: (named) => {
        if (gate.refuse) {
          throw new Error(`${Object.keys(named)[0]} is on storage a restart empties`);
        }
      },
    },
    journal: (file) => new JsonlJournal(file),
    start: async (request) => {
      requests.push(request);
      const run = new ScriptedRun(request, `run-${runs.length + 1}`);
      runs.push(run);
      const behave = behaviours[runs.length - 1] ?? ends({ outcome: 'completed' });
      setImmediate(() => behave(run));
      return run;
    },
    clock: new FakeClock(),
    ids: new SequentialIds(),
    preflight,
  });
  const options: BatchOptions = {
    directory: folder,
    repository: path.join(repository, 'docs'),
    baseRef: '',
    journal: path.join(home, 'journal.jsonl'),
    commitType: 'docs',
    contextWindow: 32768,
    loop: 'sovereignloop',
    effort: 'auto',
    baseEffort: 'LOW',
    engine: 'auto',
  };
  const task = (name: string, text: string): TaskFile => {
    fs.writeFileSync(path.join(folder, name), text);
    return new TaskFolder().load(folder).find((each) => each.name === name) as TaskFile;
  };
  const journal = (): Record<string, unknown>[] => [...new JsonlJournal(options.journal).readAll().records];
  return { home, folder, repository, git, requests, runs, runner, options, task, journal, gate };
}

describe('BatchRunner', () => {
  it('runs every task in name order, each on its own branch from one base, journaling every step', async () => {
    const s = setup([ends({ outcome: 'completed', head_sha: 'c'.repeat(40) }), ends({ outcome: 'completed-no-change' }, { branch: undefined })]);
    const readme = s.task(
      '01-readme.md',
      '---\ntitle: "docs(readme): a short front page: for beginners"\ncommit_message: "docs(readme): rewrite the front page"\ncontext_window: 65536\nmax_turns: 60\neffort: high\npaths: ["README.md"]\n---\nRewrite the README.\n',
    );
    const install = s.task('02-install.md', '# Install guide\n\nWrite it.\n');
    fs.writeFileSync(path.join(s.folder, 'notes.txt'), 'not a task');
    const heard: string[] = [];
    const summary = await s.runner.run(s.options, {
      onPlanned: (tasks, skipped, pending) => heard.push(`planned ${tasks.length}/${skipped.length}/${pending.length}`),
      onTaskStarted: (task, run, index, total) => heard.push(`started ${task.name} ${run.runId} ${index}/${total}`),
      onTaskFinished: (task, record) => heard.push(`finished ${task.name} ${record.outcome}`),
    });
    expect(summary).toEqual({
      journal: s.options.journal,
      batchId: '00000001-aaaa-4bbb-8ccc-000000000001',
      baseSha: BASE,
      total: 2,
      skipped: 0,
      ran: 2,
      outcomes: { completed: 1, 'completed-no-change': 1 },
      remaining: 0,
    });
    expect(heard).toEqual([
      'planned 2/0/2',
      'started 01-readme.md run-1 1/2',
      'finished 01-readme.md completed',
      'started 02-install.md run-2 2/2',
      'finished 02-install.md completed-no-change',
    ]);
    expect(s.git.resolved).toEqual(['HEAD']);
    expect(s.requests[0]).toEqual({
      task: 'Rewrite the README.\n',
      title: 'docs(readme): a short front page: for beginners',
      directory: s.repository,
      inPlace: false,
      baseRef: 'HEAD',
      baseSha: BASE,
      contextWindow: 65536,
      maxTurns: 60,
      paths: ['README.md'],
      loop: 'sovereignloop',
      effort: 'HIGH',
      baseEffort: 'LOW',
      engine: 'auto',
      commitMessage: 'docs(readme): rewrite the front page',
      slugSource: '01-readme',
      origin: 'batch',
      source: '01-readme.md',
    });
    expect(s.requests[1]).toMatchObject({ title: 'Install guide', contextWindow: 32768, effort: 'auto', commitMessage: 'docs: 02-install' });
    expect(s.requests[1]).not.toHaveProperty('maxTurns');
    expect(s.requests[1]).not.toHaveProperty('paths');
    const lines = s.journal();
    expect(lines.map((line) => `${String(line.type)} ${String(line.file ?? '')}`.trim())).toEqual([
      'batch.opened',
      'task.started 01-readme.md',
      'task.finished 01-readme.md',
      'task.started 02-install.md',
      'task.finished 02-install.md',
    ]);
    expect(lines[0]).toEqual({
      type: 'batch.opened',
      journal_version: 1,
      batch_id: summary.batchId,
      directory: fs.realpathSync(s.folder),
      repository: s.repository,
      base_ref: 'HEAD',
      base_sha: BASE,
      tasks: [
        { file: '01-readme.md', sha256: readme.sha256 },
        { file: '02-install.md', sha256: install.sha256 },
      ],
      at: '2026-09-24T12:00:00.000Z',
    });
    expect(lines[1]).toEqual({
      type: 'task.started',
      file: '01-readme.md',
      sha256: readme.sha256,
      run_id: 'run-1',
      branch: 'vibey/01-readme-run-1',
      cwd: '/storm/run-1',
      base_sha: BASE,
      context_window: 65536,
      max_turns: 60,
      paths: ['README.md'],
      at: '2026-09-24T12:00:00.000Z',
    });
    expect(lines[2]).toMatchObject({ file: '01-readme.md', sha256: readme.sha256, run_id: 'run-1', outcome: 'completed', head_sha: 'c'.repeat(40) });
    expect(lines[3]).not.toHaveProperty('branch');
    expect(lines[3]).not.toHaveProperty('max_turns');
    expect(lines[3]).not.toHaveProperty('paths');
    expect(s.runs.map((run) => run.listening)).toEqual([0, 0]);
  });

  it('resumes: skips what finished for good, reruns what was interrupted or stopped, and keeps the recorded base', async () => {
    const s = setup();
    const done = s.task('01-done.md', 'done');
    const cut = s.task('02-cut.md', 'cut');
    const stopped = s.task('03-stopped.md', 'stopped');
    const bare = s.task('04-bare.md', 'bare');
    const edited = s.task('05-edited.md', 'edited again');
    const journal = new JsonlJournal(s.options.journal);
    journal.append({ type: 'batch.opened', batch_id: 'batch-1', base_ref: 'origin/develop', base_sha: 'd'.repeat(40) });
    journal.append({ type: 'task.finished', file: done.name, sha256: done.sha256, outcome: 'completed' });
    journal.append({ type: 'task.started', file: cut.name, sha256: cut.sha256, run_id: 'old-2', branch: 'vibey/02-cut-old', cwd: '/storm/old-2' });
    journal.append({ type: 'task.finished', file: stopped.name, sha256: stopped.sha256, outcome: 'wound-down' });
    journal.append({ type: 'task.started', file: bare.name, sha256: bare.sha256, run_id: 'old-4' });
    journal.append({ type: 'task.finished', file: edited.name, sha256: 'an-older-version', outcome: 'completed' });
    journal.append({ type: 'task.finished', file: 5, sha256: done.sha256 });
    const notes: string[] = [];
    const summary = await s.runner.run(s.options, { onNote: (note) => notes.push(note) });
    expect(summary).toMatchObject({ batchId: 'batch-1', baseSha: 'd'.repeat(40), total: 5, skipped: 1, ran: 4, remaining: 0 });
    expect(s.requests.map((request) => request.source)).toEqual(['02-cut.md', '03-stopped.md', '04-bare.md', '05-edited.md']);
    expect(s.requests.every((request) => request.baseRef === 'origin/develop' && request.baseSha === 'd'.repeat(40))).toBe(true);
    expect(s.git.resolved).toEqual([]);
    expect(notes).toEqual([
      '02-cut.md was started and never finished (run old-2); it runs again.',
      '04-bare.md was started and never finished (run old-4); it runs again.',
    ]);
    const added = s.journal().slice(7);
    expect(added[0]).toEqual({ type: 'batch.resumed', batch_id: 'batch-1', at: '2026-09-24T12:00:00.000Z' });
    expect(added[1]).toEqual({
      type: 'task.interrupted',
      file: cut.name,
      sha256: cut.sha256,
      run_id: 'old-2',
      branch: 'vibey/02-cut-old',
      cwd: '/storm/old-2',
      at: '2026-09-24T12:00:00.000Z',
    });
    expect(added[2]).toEqual({ type: 'task.interrupted', file: bare.name, sha256: bare.sha256, run_id: 'old-4', at: '2026-09-24T12:00:00.000Z' });
  });

  it('will not resume a journal from another base: one batch, one commit', async () => {
    const s = setup();
    s.task('01.md', 'one');
    new JsonlJournal(s.options.journal).append({ type: 'batch.opened', batch_id: 'b', base_ref: 'origin/develop', base_sha: 'd'.repeat(40) });
    await expect(s.runner.run({ ...s.options, baseRef: 'main' })).rejects.toThrow(
      `${s.options.journal} was opened with base origin/develop (dddddddddddd), not main. Every task of one batch starts from the same commit; give --journal a new file to start a batch from another base.`,
    );
    expect((await s.runner.run({ ...s.options, baseRef: 'origin/develop' })).ran).toBe(1);
  });

  it('halts on an infrastructure error, a stop or a spent budget, and counts the halting task as not finished', async () => {
    const halted = async (record: Partial<RunRecord>): Promise<[string | undefined, number, number]> => {
      const s = setup([ends({ outcome: 'failed' }), ends(record)]);
      s.task('01.md', 'one');
      s.task('02.md', 'two');
      s.task('03.md', 'three');
      const summary = await s.runner.run(s.options);
      const last = s.journal().at(-1);
      expect(last).toMatchObject({ type: 'batch.halted', batch_id: summary.batchId, file: '02.md', reason: summary.halted });
      return [summary.halted, summary.ran, summary.remaining];
    };
    expect(await halted({ outcome: 'error', error: 'qwenloop was not found on PATH' })).toEqual([
      'an infrastructure error, not a task failure: qwenloop was not found on PATH',
      2,
      2,
    ]);
    expect(await halted({ outcome: 'error' })).toEqual(['an infrastructure error, not a task failure: unknown', 2, 2]);
    expect(await halted({ outcome: 'wound-down' })).toEqual(['the run was stopped', 2, 2]);
    expect(
      await halted({ outcome: 'budget-exhausted', budget: { id: 'b', cap: 'dollars', limit: 5, spent: 5, message: 'The daily budget b is used up.' } }),
    ).toEqual(['a budget is used up: The daily budget b is used up.', 2, 2]);
    expect(await halted({ outcome: 'budget-exhausted' })).toEqual(['a budget is used up: see the journal', 2, 2]);
  });

  it('checks once, before the first task, that the model can run at all', async () => {
    const s = setup([], async () => 'Ollama is not answering at http://127.0.0.1:11434: connect ECONNREFUSED');
    s.task('01.md', 'one');
    s.task('02.md', 'two');
    const summary = await s.runner.run(s.options);
    expect(summary).toMatchObject({ ran: 0, remaining: 2, halted: 'Ollama is not answering at http://127.0.0.1:11434: connect ECONNREFUSED' });
    expect(s.requests).toEqual([]);
    expect(s.journal().at(-1)).toMatchObject({ type: 'batch.halted', reason: summary.halted });
  });

  it('has nothing to do when every task has finished, and does not even check the model', async () => {
    let checked = 0;
    const s = setup([], async () => {
      checked += 1;
      return undefined;
    });
    const only = s.task('01.md', 'one');
    new JsonlJournal(s.options.journal).append({ type: 'batch.opened', batch_id: 'b', base_ref: 'HEAD', base_sha: BASE });
    new JsonlJournal(s.options.journal).append({ type: 'task.finished', file: only.name, sha256: only.sha256, outcome: 'completed-out-of-scope' });
    expect(await s.runner.run(s.options)).toMatchObject({ total: 1, skipped: 1, ran: 0, remaining: 0 });
    expect(checked).toBe(0);
  });

  it('refuses an empty folder, and a journal on storage a restart empties', async () => {
    const s = setup();
    await expect(s.runner.run(s.options)).rejects.toThrow(`${s.folder} has no .md task files`);
    s.gate.refuse = true;
    await expect(s.runner.run(s.options)).rejects.toThrow('batch journal is on storage a restart empties');
  });
});
