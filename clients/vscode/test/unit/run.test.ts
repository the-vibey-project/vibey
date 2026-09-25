// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * One task from request to record, with every service scripted: git, the engine process, the
 * model slot, budgets and the clock. The engine is a fake child that writes events where the
 * real engine would, so the run reads them by byte offset exactly as it does in the editor.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { CatalogueParser } from '@vibey/core';
import { EngineCommand } from '../../src/core/engine-command';
import type { BudgetBreach, BudgetGuardInterface, SpendEntry, SpendLedgerInterface, SpendTotals } from '@vibey/core';
import type { CatalogueEngine, Effort, LoopSelectorInterface, Selection, SelectionRequest } from '@vibey/core';
import type { ChangedFile, CommitOutcome, GitClientInterface, MergeOutcome } from '@vibey/core';
import type { LockAttempt, LockOwner, ModelSlotLockInterface } from '@vibey/core';
import type { RunItem, RunPatch } from '@vibey/core';
import type { RunHistoryEntry, RunHistoryInterface, RunRecord, RunRequest, RunServices, RunStatus } from '@vibey/core';
import type { ResolvedSettings } from '@vibey/core';
import type { DurabilityGateInterface, VolatileHit } from '@vibey/core';
import type { Disposable } from '@vibey/core';
import { JsonlJournal, JsonlTail } from '../../src/core/jsonl';
import { LocalRunners } from '@vibey/core';
import { QwenloopCommand, QwenloopRunConfig } from '../../src/core/qwenloop';
import { ATTACHMENTS_DIRECTORY, RunHistory, TaskRun } from '../../src/core/run';
import { SettingsResolver } from '../../src/core/settings';
import { MacStorage } from '../../src/core/storage';
import { TaskNaming } from '../../src/core/support';
import { type FakeChildControl, FakeClock, FakeProcessRunner, SequentialIds, fixture, scratch, settle } from './helpers';

const CATALOGUE = new CatalogueParser().parse(JSON.parse(fixture('vibey-loops.json')));
const ENGINES = CATALOGUE.loops.flatMap((loop) => loop.engines);
const STATE_DIRS = [...new Set(ENGINES.map((engine) => engine.state_dir))];
const BASE = 'b'.repeat(40);
const HEAD = 'c'.repeat(40);
const DECLARED = 'declared (vibey.budgetInputTokensPerTurn, vibey.budgetOutputTokensPerTurn)';

/** What the editor's environment holds: basics, a DSN, libpq's password, keys, a smuggled address. */
const ENVIRON = {
  PATH: '/usr/bin:/bin',
  HOME: '/Users/me',
  LANG: 'en_US.UTF-8',
  VIBEY_PG_URL: 'postgresql://vibey:secret@localhost/vibey',
  PGPASSWORD: 'secret',
  DATABASE_URL: 'postgres://x',
  GPTOSSLOOP_DEBUG: '1',
  GPTOSSLOOP_SNEAKY: 'postgres://u:p@db/x',
  QWENLOOP_DEBUG: '2',
  QWENLOOP_SNEAKY: 'postgres://u:p@db/y',
  ANTHROPIC_API_KEY: 'sk-ant-test',
  AWS_SECRET_ACCESS_KEY: 'not for a model',
};

/** gptossloop finishing its task in one turn, with its verdict and marker. */
const DONE = [
  { type: 'turn.completed', turn: 1, input_tokens: 1200, output_tokens: 300 },
  { type: 'text_delta', text: `Done.\n\`\`\`qwenloop-verdict\nAdded the line.\n\`\`\`\n${QwenloopCommand.DONE_MARKER}\n` },
  { type: 'completed', turn: 1 },
];

function engineOf(id: string): CatalogueEngine {
  return ENGINES.find((engine) => engine.engine_id === id) as CatalogueEngine;
}

function selection(engineId: string, overrides: Partial<Selection> = {}): Selection {
  const engine = engineOf(engineId);
  const tier = CATALOGUE.loops.find((loop) => loop.engines.includes(engine))?.tier ?? 'local';
  // Both names of the local runner project a turn limit for their effort.
  const runner = engineId === 'gptossloop' || engineId === 'qwenloop';
  return {
    loop: tier === 'local' ? 'sovereignloop' : 'paidloop',
    tier,
    effort: 'LOW',
    effortSource: 'chosen',
    engine,
    model: engine.default_model,
    argv: runner ? ['--max-turns', '16'] : [],
    ...(runner ? { maxTurns: 16 } : {}),
    maxTurnsSource: runner ? 'effort' : 'none',
    reason: `${engineId} for this test`,
    ...overrides,
  };
}

/** Where an engine child writes its events: its working directory, state directory and run id. */
function eventsOf(child: FakeChildControl): string {
  const runId = child.args[child.args.indexOf('--run-id') + 1] as string;
  const engine = ENGINES.find((each) => `/bin/${each.binary}` === child.command) as CatalogueEngine;
  return path.join(child.options.cwd as string, engine.state_dir, 'runs', runId, 'events.jsonl');
}

function write(child: FakeChildControl, ...events: unknown[]): void {
  const file = eventsOf(child);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, events.map((event) => `${JSON.stringify(event)}\n`).join(''));
}

class ScriptedSelector implements LoopSelectorInterface {
  readonly requests: SelectionRequest[] = [];

  constructor(private readonly answer: (request: SelectionRequest) => Selection) {}

  select(request: SelectionRequest): Selection {
    this.requests.push(request);
    return this.answer(request);
  }

  effortForAttempt(base: Effort): Effort {
    return base;
  }
}

class FakeGit implements GitClientInterface {
  readonly calls: unknown[][] = [];
  commitOutcome: CommitOutcome = { committed: true };
  changed: readonly ChangedFile[] = [{ status: 'M', path: 'README.md' }];
  dirty: readonly string[] = [];
  branch: string | undefined = 'main';

  constructor(readonly repository: string) {}

  named(name: string): unknown[][] {
    return this.calls.filter(([called]) => called === name);
  }

  async version(): Promise<string> {
    return 'git version 2.47.0';
  }

  async toplevel(directory: string): Promise<string> {
    this.calls.push(['toplevel', directory]);
    return this.repository;
  }

  async resolveCommit(repository: string, ref: string): Promise<string> {
    this.calls.push(['resolveCommit', repository, ref]);
    return BASE;
  }

  async head(directory: string): Promise<string> {
    this.calls.push(['head', directory]);
    return HEAD;
  }

  async uncommitted(directory: string, exclude?: readonly string[]): Promise<readonly string[]> {
    this.calls.push(['uncommitted', directory, exclude]);
    return this.dirty;
  }

  async currentBranch(repository: string): Promise<string | undefined> {
    this.calls.push(['currentBranch', repository]);
    return this.branch;
  }

  async addWorktree(repository: string, worktree: string, branch: string, base: string): Promise<void> {
    this.calls.push(['addWorktree', repository, worktree, branch, base]);
  }

  async removeWorktree(): Promise<void> {}

  async deleteBranch(): Promise<void> {}

  async branchExists(): Promise<boolean> {
    return false;
  }

  async commitAll(worktree: string, message: string, exclude?: readonly string[], paths?: readonly string[]): Promise<CommitOutcome> {
    this.calls.push(paths === undefined ? ['commitAll', worktree, message, exclude] : ['commitAll', worktree, message, exclude, paths]);
    return this.commitOutcome;
  }

  async diffStat(repository: string, from: string, to: string): Promise<string> {
    this.calls.push(['diffStat', repository, from, to]);
    return ' README.md | 1 +';
  }

  async changedFiles(repository: string, from: string, to: string): Promise<readonly ChangedFile[]> {
    this.calls.push(['changedFiles', repository, from, to]);
    return this.changed;
  }

  async diff(): Promise<string> {
    return '';
  }

  async merge(): Promise<MergeOutcome> {
    return { ok: true, output: '' };
  }
}

/** The model slot: free at once, or busy a few times first, and a place to act while waiting. */
class FakeLock implements ModelSlotLockInterface {
  readonly purposes: string[] = [];
  released = 0;
  busy = 0;
  holder: LockOwner | undefined;
  whileWaiting: (() => Promise<unknown>) | undefined;
  failWith: Error | undefined;

  tryAcquire(): LockAttempt {
    return { acquired: true };
  }

  release(): void {
    this.released += 1;
  }

  async acquire(purpose: string, onWait: (holder: LockOwner | undefined) => void): Promise<Disposable> {
    this.purposes.push(purpose);
    for (let time = 0; time < this.busy; time += 1) {
      onWait(this.holder);
    }
    await this.whileWaiting?.();
    if (this.failWith !== undefined) {
      throw this.failWith;
    }
    return { dispose: () => this.release() };
  }
}

class RecordingHistory implements RunHistoryInterface {
  readonly records: RunRecord[] = [];
  readonly forced: [string, number][] = [];
  failing = false;

  finished(record: RunRecord): void {
    if (this.failing) {
      throw new Error('disk full');
    }
    this.records.push(record);
  }

  applied(): void {}

  discarded(): void {}

  forceStopped(runId: string, afterMs: number): void {
    this.forced.push([runId, afterMs]);
  }

  list(): readonly RunHistoryEntry[] {
    return [];
  }
}

class ScriptedBudgets implements BudgetGuardInterface {
  readonly asked: unknown[] = [];
  refusals: (BudgetBreach | undefined)[] = [];
  used: BudgetBreach | undefined;

  wouldExceed(context: Parameters<BudgetGuardInterface['wouldExceed']>[0]): BudgetBreach | undefined {
    this.asked.push(context);
    return this.refusals.shift();
  }

  exhausted(): BudgetBreach | undefined {
    return this.used;
  }

  usage(): undefined {
    return undefined;
  }
}

class RecordingSpend implements SpendLedgerInterface {
  readonly entries: SpendEntry[] = [];
  measured: { readonly input: number; readonly output: number } | undefined;

  record(entry: SpendEntry): void {
    this.entries.push(entry);
  }

  totals(): SpendTotals {
    return { dollars: 0, turns: 0, minutes: 0, input_tokens: 0, output_tokens: 0, runs: 0 };
  }

  perTurn(): { readonly input: number; readonly output: number } | undefined {
    return this.measured;
  }

  perHour(): number | null {
    return null;
  }
}

class Gate implements DurabilityGateInterface {
  readonly asked: Record<string, string>[] = [];
  refuse: string | undefined;

  inspect(): readonly VolatileHit[] {
    return [];
  }

  enforce(named: Readonly<Record<string, string>>): void {
    this.asked.push({ ...named });
    for (const name of Object.keys(named)) {
      if (name === this.refuse) {
        throw new Error(`${name} would be on storage a restart empties`);
      }
    }
  }
}

const BREACH: BudgetBreach = {
  budget: { id: 'b1', scope: 'day', loop: 'any', caps: { turns: 1 } },
  cap: 'turns',
  limit: 1,
  spent: 1,
  message: 'The daily budget b1 is used up: 1 turns of 1 turns.',
};

interface HarnessOptions {
  readonly request?: Partial<RunRequest>;
  readonly select?: (request: SelectionRequest) => Selection;
  readonly settings?: Partial<ResolvedSettings>;
  readonly services?: Partial<RunServices>;
}

function harness(options: HarnessOptions = {}) {
  const home = scratch('vibey-run-');
  const repository = path.join(home, 'project');
  const resolved = new SettingsResolver({ HOME: home }, new MacStorage()).resolve({ stormHome: home, pollMilliseconds: 100 });
  const settings: ResolvedSettings = { ...resolved, ...options.settings };
  const processes = new FakeProcessRunner();
  const git = new FakeGit(repository);
  const clock = new FakeClock();
  const lock = new FakeLock();
  const locks: [string, string][] = [];
  const history = new RecordingHistory();
  const budgets = new ScriptedBudgets();
  const spend = new RecordingSpend();
  const gate = new Gate();
  const selector = new ScriptedSelector(options.select ?? (() => selection('gptossloop')));
  const services: RunServices = {
    settings,
    catalogue: CATALOGUE,
    selector,
    command: (engine) => new EngineCommand(engine, `/bin/${engine.binary}`),
    git,
    processes,
    runConfig: new QwenloopRunConfig(),
    runners: LocalRunners.FAMILY,
    userConfig: () => undefined,
    gate,
    tail: new JsonlTail(),
    lockFor: (engine, tier) => {
      locks.push([engine.engine_id, tier]);
      return lock;
    },
    clock,
    ids: new SequentialIds(),
    naming: new TaskNaming(),
    history,
    paidDeclared: () => false,
    resident: async () => ['gpt-oss:20b'],
    budgets,
    spend,
    environ: ENVIRON,
    ...options.services,
  };
  const request: RunRequest = {
    task: '# Add a line to README.md\n\nSay hello to new readers.\n',
    title: 'Add a line to README.md',
    directory: path.join(repository, 'docs'),
    inPlace: false,
    baseRef: '',
    loop: 'sovereignloop',
    effort: 'LOW',
    baseEffort: 'LOW',
    engine: 'auto',
    contextWindow: 32768,
    commitMessage: 'docs: add a line to the README',
    slugSource: 'Add a line to README.md',
    origin: 'ask',
    ...options.request,
  };
  const run = new TaskRun(request, services);
  const patches: RunPatch[] = [];
  const statuses: RunStatus[] = [];
  run.onPatch((patch) => patches.push(patch));
  run.onStatus((status) => statuses.push(status));
  const naming = new TaskNaming();
  const short = naming.shortId(run.runId);
  const runDirectory = path.join(settings.stateDir, 'runs', run.runId);
  return {
    run,
    home,
    repository,
    settings,
    processes,
    git,
    clock,
    lock,
    locks,
    history,
    budgets,
    spend,
    gate,
    selector,
    patches,
    statuses,
    runDirectory,
    worktree: path.join(home, naming.worktreeName(repository, naming.slug(request.slugSource), short)),
    branch: naming.branch(naming.slug(request.slugSource), short),
    notices: (): string[] =>
      run
        .items()
        .filter((item): item is Extract<RunItem, { kind: 'notice' }> => item.kind === 'notice')
        .map((item) => item.text),
  };
}

describe('TaskRun', () => {
  it('runs a task on a worktree and branch of its own, commits it there, and records everything', async () => {
    const h = harness();
    h.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    expect(h.run.status).toBe('queued');
    expect(h.run.current).toBeUndefined();
    expect(h.run.workspace).toBeUndefined();
    expect(h.run.stopRequestedAt).toBeUndefined();
    expect(h.run.budgetBreach).toBeUndefined();
    const record = await h.run.execute();

    const plan = path.join(h.runDirectory, 'plan.md');
    const config = path.join(h.runDirectory, 'gptossloop.toml');
    const events = path.join(h.worktree, '.qwenloop', 'runs', h.run.runId, 'events.jsonl');
    expect(h.git.calls.slice(0, 3)).toEqual([
      ['toplevel', path.join(h.repository, 'docs')],
      ['resolveCommit', h.repository, 'HEAD'],
      ['addWorktree', h.repository, h.worktree, h.branch, BASE],
    ]);
    expect(h.gate.asked).toEqual([{ 'run records': h.runDirectory }, { 'task worktree': h.worktree }]);
    const child = h.processes.children[0] as FakeChildControl;
    expect(child.command).toBe('/bin/gptossloop');
    expect(child.args).toEqual(['run', plan, '--run-id', h.run.runId, '--max-turns', '16', '--no-desktop-notifications', '--cwd', h.worktree]);
    expect(child.options.cwd).toBe(h.worktree);
    // The allow-list: no DSN, no libpq password, no database address under any name, no key it was not given.
    expect(child.options.env).toEqual({
      PATH: '/usr/bin:/bin',
      HOME: '/Users/me',
      LANG: 'en_US.UTF-8',
      // gptossloop's own settings pass through; qwenloop's never reach it, and neither does
      // a database address under a runner's prefix.
      GPTOSSLOOP_DEBUG: '1',
      OLLAMA_HOST: h.settings.ollama.root,
      GPTOSSLOOP_BASE_URL: h.settings.ollama.v1,
      GPTOSSLOOP_MODEL: 'gpt-oss:20b',
      GPTOSSLOOP_CONFIG: config,
    });
    expect(fs.readFileSync(config, 'utf8')).toContain('context_window = 32768\n');
    expect(fs.readFileSync(plan, 'utf8')).toBe('# Add a line to README.md\n\nSay hello to new readers.\n');
    expect(h.git.named('commitAll')).toEqual([['commitAll', h.worktree, 'docs: add a line to the README', [...STATE_DIRS, ATTACHMENTS_DIRECTORY]]]);
    expect(record).toMatchObject({
      run_id: h.run.runId,
      title: 'Add a line to README.md',
      origin: 'ask',
      outcome: 'completed',
      exit_code: 0,
      signal: null,
      loop: 'sovereignloop',
      engine: 'gptossloop',
      effort: 'LOW',
      model: 'gpt-oss:20b',
      catalogue: 'vibey',
      context_window: 32768,
      max_turns: 16,
      max_turns_source: 'effort',
      mode: 'worktree',
      repository: h.repository,
      cwd: h.worktree,
      branch: h.branch,
      base_ref: 'HEAD',
      base_sha: BASE,
      head_sha: HEAD,
      diff_stat: ' README.md | 1 +',
      changed_files: [{ status: 'M', path: 'README.md' }],
      uncommitted: [],
      attachments: [],
      verdict: 'Added the line.',
      marker: true,
      projection: { turns: 16, dollars: 0, per_turn: DECLARED },
      turns: 1,
      input_tokens: 1200,
      output_tokens: 300,
      started_at: '2026-09-24T12:00:00.000Z',
      run_directory: h.runDirectory,
      events_path: events,
      plan_path: plan,
      engine_config: config,
      argv: ['/bin/gptossloop', ...child.args],
    });
    for (const absent of ['error', 'failure', 'commit_error', 'budget', 'force_stopped_at', 'source', 'context_plugins']) {
      expect(record).not.toHaveProperty(absent);
    }
    expect(record.attempts).toEqual([
      {
        attempt: 1,
        run_id: h.run.runId,
        loop: 'sovereignloop',
        tier: 'local',
        engine: 'gptossloop',
        model: 'gpt-oss:20b',
        effort: 'LOW',
        effort_source: 'chosen',
        max_turns: 16,
        max_turns_source: 'effort',
        reason: 'gptossloop for this test',
        outcome: 'completed',
        exit_code: 0,
        signal: null,
        argv: ['/bin/gptossloop', ...child.args],
        events_path: events,
        turns: 1,
      },
    ]);
    expect(JSON.parse(fs.readFileSync(path.join(h.runDirectory, 'result.json'), 'utf8'))).toEqual(record);
    expect(h.history.records).toEqual([record]);
    expect(h.statuses).toEqual(['preparing', 'waiting', 'running', 'finishing', 'finished']);
    expect(h.lock.purposes).toEqual([`Add a line to README.md (task ${h.run.runId})`]);
    expect(h.lock.released).toBe(1);
    expect(h.locks).toEqual([['gptossloop', 'local']]);
    expect(h.selector.requests).toEqual([
      { loop: 'sovereignloop', effort: 'LOW', engine: 'auto', baseEffort: 'LOW', attempt: 1, resident: ['gpt-oss:20b'], paidDeclared: false },
    ]);
    expect(h.budgets.asked).toEqual([{ loop: 'sovereignloop', engineId: 'gptossloop', runId: h.run.runId, projected: { turns: 16, dollars: 0 } }]);
    expect(h.spend.entries).toEqual([
      { run_id: h.run.runId, at: '2026-09-24T12:00:00.000Z', loop: 'sovereignloop', engine_id: 'gptossloop', turns: 1, input_tokens: 1200, output_tokens: 300, dollars: 0, minutes: 0 },
    ]);
    expect(h.notices()).toEqual([
      `Working on a copy: ${h.worktree}, branch ${h.branch}, from HEAD at ${BASE.slice(0, 12)}.`,
      'Attempt 1: gptossloop for this test.',
      'gptossloop plans for a 32,768-token window on gpt-oss:20b.',
      'The engine reports the task complete at turn 1.',
    ]);
    expect(h.patches.length).toBeGreaterThanOrEqual(h.run.items().length);
    expect(h.run.current).toEqual({ engine: 'gptossloop', model: 'gpt-oss:20b', effort: 'LOW' });
    expect(h.run.workspace).toMatchObject({ mode: 'worktree', branch: h.branch, baseSha: BASE });
    expect(await h.run.execute()).toBe(record);
    expect(await h.run.result).toBe(record);
    expect(h.run.status).toBe('finished');
  });

  it('calls completed work that changed nothing completed-no-change, and keeps a refused commit as such', async () => {
    const unchanged = harness();
    unchanged.git.changed = [];
    unchanged.git.commitOutcome = { committed: false };
    unchanged.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    expect((await unchanged.run.execute()).outcome).toBe('completed-no-change');

    const leftOver = harness();
    leftOver.git.changed = [];
    leftOver.git.dirty = ['notes.txt'];
    leftOver.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    expect(await leftOver.run.execute()).toMatchObject({ outcome: 'completed', uncommitted: ['notes.txt'] });

    const refused = harness();
    refused.git.commitOutcome = { committed: false, error: 'trailing-whitespace....Failed' };
    refused.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    expect(await refused.run.execute()).toMatchObject({ outcome: 'completed-commit-refused', commit_error: 'trailing-whitespace....Failed' });
  });

  it("commits only the task's paths, and calls the task completed-out-of-scope when it changed more", async () => {
    const h = harness({ request: { paths: ['docs/guides/install.md'] } });
    h.git.commitOutcome = { committed: true, outOfScope: ['pyproject.toml', 'uv.lock'] };
    h.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    const record = await h.run.execute();
    expect(h.git.named('commitAll')[0]?.[4]).toEqual(['docs/guides/install.md']);
    expect(record).toMatchObject({ outcome: 'completed-out-of-scope', paths: ['docs/guides/install.md'], out_of_scope: ['pyproject.toml', 'uv.lock'] });
    expect(h.notices()).toContain("Left uncommitted, outside this task's paths: pyproject.toml, uv.lock. Review them in its copy.");

    const refused = harness({ request: { paths: ['docs/'] } });
    refused.git.commitOutcome = { committed: false, error: 'hook said no', outOfScope: ['uv.lock'] };
    refused.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    expect(await refused.run.execute()).toMatchObject({ outcome: 'completed-commit-refused', commit_error: 'hook said no', out_of_scope: ['uv.lock'] });

    const inScope = harness({ request: { paths: ['docs/'] } });
    inScope.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    const clean = await inScope.run.execute();
    expect(clean).toMatchObject({ outcome: 'completed', paths: ['docs/'] });
    expect(clean).not.toHaveProperty('out_of_scope');
  });

  it('runs in place on the checked-out branch when asked, with a warning and no commit', async () => {
    const h = harness({ request: { inPlace: true } });
    h.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    const record = await h.run.execute();
    expect(h.git.calls.slice(0, 3)).toEqual([
      ['toplevel', path.join(h.repository, 'docs')],
      ['resolveCommit', h.repository, 'HEAD'],
      ['currentBranch', h.repository],
    ]);
    expect(h.git.named('addWorktree')).toEqual([]);
    expect(h.git.named('commitAll')).toEqual([]);
    expect(h.gate.asked).toEqual([{ 'run records': h.runDirectory }]);
    expect(record).toMatchObject({ outcome: 'completed', mode: 'in-place', cwd: h.repository, branch: 'main', base_ref: 'HEAD' });
    expect(h.notices()[0]).toContain('Running in place');

    const detached = harness({ request: { inPlace: true } });
    detached.git.branch = undefined;
    detached.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    expect(await detached.run.execute()).not.toHaveProperty('branch');
  });

  it('starts from a base a batch resolved once, and names it as the batch did', async () => {
    const h = harness({ request: { baseRef: 'origin/develop', baseSha: 'f'.repeat(40), origin: 'batch', source: '01-readme.md' } });
    h.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    const record = await h.run.execute();
    expect(h.git.named('resolveCommit')).toEqual([]);
    expect(h.git.named('addWorktree')[0]?.[4]).toBe('f'.repeat(40));
    expect(record).toMatchObject({ origin: 'batch', source: '01-readme.md', base_ref: 'origin/develop', base_sha: 'f'.repeat(40) });
  });

  it('adds attachments, pasted text and a context packet to the plan, and copies files in where they are never committed', async () => {
    const outside = scratch();
    const notes = path.join(outside, 'notes.md');
    const shot = path.join(outside, 'shot.png');
    fs.writeFileSync(notes, 'the notes');
    fs.writeFileSync(shot, 'png bytes');
    const h = harness({
      request: {
        attachments: [
          { kind: 'file', name: notes },
          { kind: 'image', name: shot },
          { kind: 'text', name: 'the error', text: 'TypeError: x is undefined' },
          { kind: 'text', name: 'nothing pasted' },
        ],
        contextPacket: { markdown: '# Context\n\nUse the house style.\n', plugins: ['frontend-design'], manifest: '/m.json' },
      },
    });
    h.processes.onSpawn = (child) => {
      write(child, ...DONE);
      child.exit({ code: 0, signal: null });
    };
    const record = await h.run.execute();
    const plan = fs.readFileSync(path.join(h.runDirectory, 'plan.md'), 'utf8');
    expect(plan).toBe(
      [
        '# Add a line to README.md\n\nSay hello to new readers.',
        '',
        '## Files the person attached',
        '',
        `- .vibey-attachments/notes.md (a copy of ${notes}; it is not part of the change)`,
        `- .vibey-attachments/shot.png (a copy of ${shot}; it is not part of the change)`,
        '',
        '## Pasted by the person: the error',
        '',
        'TypeError: x is undefined',
        '',
        '## Pasted by the person: nothing pasted',
        '',
        '',
        '',
        '## Context from vibey-skills (frontend-design)',
        '',
        '# Context\n\nUse the house style.\n',
      ].join('\n'),
    );
    expect(fs.readFileSync(path.join(h.worktree, ATTACHMENTS_DIRECTORY, 'notes.md'), 'utf8')).toBe('the notes');
    expect(record.attachments).toEqual([
      { kind: 'file', name: notes, placed_at: '.vibey-attachments/notes.md' },
      { kind: 'image', name: shot, placed_at: '.vibey-attachments/shot.png' },
      { kind: 'text', name: 'the error' },
      { kind: 'text', name: 'nothing pasted' },
    ]);
    expect(record.context_plugins).toEqual(['frontend-design']);

    const ranked = harness({ request: { contextPacket: { markdown: 'ranked context', plugins: [] } } });
    ranked.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    await ranked.run.execute();
    expect(fs.readFileSync(path.join(ranked.runDirectory, 'plan.md'), 'utf8')).toContain('## Context from vibey-skills (ranked)\n\nranked context\n');
  });

  it("writes gptossloop's window over the person's own gptossloop config, and asks for its desktop notifications when set", async () => {
    const asked: string[] = [];
    const h = harness({
      settings: { desktopNotifications: true },
      services: {
        userConfig: (runner) => {
          asked.push(runner.name);
          return { path: '/Users/me/.config/gptossloop/config.toml', text: 'context_window = 8192\nidle_timeout_seconds = 90\n' };
        },
      },
      request: { contextWindow: 65536 },
      select: () => selection('gptossloop', { model: null }),
    });
    h.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    await h.run.execute();
    expect(asked).toEqual(['gptossloop']);
    const config = fs.readFileSync(path.join(h.runDirectory, 'gptossloop.toml'), 'utf8');
    expect(config).toContain('context_window = 65536');
    expect(config).toContain('idle_timeout_seconds = 90');
    expect(config).not.toContain('8192');
    const child = h.processes.children[0] as FakeChildControl;
    expect(child.args).toContain('--desktop-notifications');
    // No model from the catalogue: gptossloop takes vibey.model, whose default is its own.
    expect(child.options.env?.GPTOSSLOOP_MODEL).toBe('gpt-oss:20b');
    expect(child.options.env).not.toHaveProperty('QWENLOOP_MODEL');
    expect(h.notices()).toContain(
      'gptossloop plans for a 65,536-token window on gpt-oss:20b, over your own config at /Users/me/.config/gptossloop/config.toml.',
    );
  });

  it('binds qwenloop through its own QWENLOOP_* settings and config, and hands it a model only when one is named (ADR-0064)', async () => {
    const asked: string[] = [];
    const run = async (model: string | null) => {
      const h = harness({
        services: {
          userConfig: (runner) => {
            asked.push(runner.name);
            return runner.name === 'qwenloop' ? { path: '/Users/me/.config/qwenloop/config.toml', text: 'model = "qwen3:14b"\n' } : undefined;
          },
        },
        select: () => selection('qwenloop', { model }),
      });
      h.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
      await h.run.execute();
      return { h, child: h.processes.children[0] as FakeChildControl };
    };
    const own = await run(null);
    const config = path.join(own.h.runDirectory, 'qwenloop.toml');
    expect(own.child.command).toBe('/bin/qwenloop');
    expect(own.child.args).toContain('--no-desktop-notifications');
    expect(own.child.options.env).toEqual({
      PATH: '/usr/bin:/bin',
      HOME: '/Users/me',
      LANG: 'en_US.UTF-8',
      QWENLOOP_DEBUG: '2',
      OLLAMA_HOST: own.h.settings.ollama.root,
      QWENLOOP_BASE_URL: own.h.settings.ollama.v1,
      QWENLOOP_CONFIG: config,
    });
    expect(fs.readFileSync(config, 'utf8')).toContain('model = "qwen3:14b"');
    expect(own.h.notices()).toContain(
      'qwenloop plans for a 32,768-token window on the model its own config chooses, over your own config at /Users/me/.config/qwenloop/config.toml.',
    );
    const named = await run('qwen3:14b');
    expect(named.child.options.env?.QWENLOOP_MODEL).toBe('qwen3:14b');
    expect(named.h.notices()).toContain(
      'qwenloop plans for a 32,768-token window on qwen3:14b, over your own config at /Users/me/.config/qwenloop/config.toml.',
    );
    expect(asked).toEqual(['qwenloop', 'qwenloop']);
  });

  it('runs a paid engine with its own keys and no local binding, and counts what it says it spent', async () => {
    const h = harness({
      request: { loop: 'paidloop', engine: 'claudeloop' },
      select: () => selection('claudeloop', { argv: ['--preset', 'low', '--effort', 'medium', '--max-turns', '10'], maxTurns: 10, maxTurnsSource: 'task' }),
      services: { paidDeclared: () => true },
    });
    h.spend.measured = { input: 1000, output: 100 };
    h.lock.busy = 2;
    h.processes.onSpawn = (child) => {
      write(child, { event_type: 'turn.completed', payload: { turn: 1, input_tokens: 1000, output_tokens: 100, cost_usd: 0.25 } });
      h.clock.tick();
      write(child, { event_type: 'turn.completed', payload: { turn: 2, input_tokens: 2000, output_tokens: 200 } }, { event_type: 'finished', payload: { success: true } });
      child.exit({ code: 0, signal: null });
    };
    const record = await h.run.execute();
    const child = h.processes.children[0] as FakeChildControl;
    expect(child.command).toBe('/bin/claudeloop');
    expect(child.args).toEqual(['run', path.join(h.runDirectory, 'plan.md'), '--run-id', h.run.runId, '--preset', 'low', '--effort', 'medium', '--max-turns', '10', '--cwd', h.worktree]);
    expect(child.options.env).toEqual({ PATH: '/usr/bin:/bin', HOME: '/Users/me', LANG: 'en_US.UTF-8', ANTHROPIC_API_KEY: 'sk-ant-test' });
    expect(h.locks).toEqual([['claudeloop', 'paid']]);
    expect(h.selector.requests[0]).toMatchObject({ loop: 'paidloop', resident: [], paidDeclared: true });
    expect(h.notices().filter((text) => text.startsWith('Waiting'))).toEqual(['Waiting for the claudeloop slot: another run is using it.']);
    expect(h.spend.entries.map((entry) => [entry.turns, entry.input_tokens, entry.output_tokens, entry.dollars])).toEqual([
      [1, 1000, 100, 0.25],
      [1, 2000, 200, 0.009],
    ]);
    expect(record).toMatchObject({ outcome: 'completed', loop: 'paidloop', engine: 'claudeloop', model: null, max_turns: 10, max_turns_source: 'task', turns: 2 });
    expect(record.projection).toEqual({ turns: 10, dollars: 0.045, per_turn: 'measured on this machine for claudeloop' });
    expect(record).not.toHaveProperty('engine_config');
  });

  it('says once who holds the model slot it waits for, whichever tier', async () => {
    const holder: LockOwner = { pid: 42, host: 'this-mac', bootAt: 0, startedAt: 'x', purpose: 'a batch task' };
    const local = harness();
    local.lock.busy = 3;
    local.lock.holder = holder;
    local.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    await local.run.execute();
    expect(local.notices().filter((text) => text.startsWith('Waiting'))).toEqual(['Waiting: a batch task (process 42) is using the local model slot.']);

    const unnamed = harness();
    unnamed.lock.busy = 1;
    unnamed.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    await unnamed.run.execute();
    expect(unnamed.notices()).toContain('Waiting for the local model slot: another run is using it.');

    const paid = harness({ request: { loop: 'paidloop' }, select: () => selection('codexloop') });
    paid.lock.busy = 1;
    paid.lock.holder = holder;
    paid.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    await paid.run.execute();
    expect(paid.notices()).toContain('Waiting: a batch task (process 42) is using the codexloop slot.');
  });

  it('climbs the effort ladder after a failed attempt on auto effort, in the same copy, rotating engines as the selector says', async () => {
    let spawned = 0;
    const h = harness({
      request: { effort: 'auto', maxTurns: 60 },
      settings: { maxTurns: 30 },
      select: (request) => selection('gptossloop', { effort: request.attempt === 1 ? 'LOW' : 'STANDARD', effortSource: 'auto' }),
    });
    h.processes.onSpawn = (child) => {
      spawned += 1;
      if (spawned === 1) {
        write(child, { type: 'turn.completed', turn: 1 }, { type: 'failed', reason: 'turn_limit', max_turns: 16 });
        child.exit({ code: 1, signal: null });
      } else {
        write(child, ...DONE);
        child.exit({ code: 0, signal: null });
      }
    };
    const record = await h.run.execute();
    expect(h.selector.requests.map((request) => [request.attempt, request.previousEngine, request.taskMaxTurns, request.settingMaxTurns])).toEqual([
      [1, undefined, 60, 30],
      [2, 'gptossloop', 60, 30],
    ]);
    expect(h.git.named('addWorktree')).toHaveLength(1);
    const [first, second] = h.processes.children as FakeChildControl[];
    expect(first?.options.cwd).toBe(second?.options.cwd);
    expect(record.attempts.map((attempt) => [attempt.attempt, attempt.outcome, attempt.effort, attempt.turns])).toEqual([
      [1, 'failed', 'LOW', 1],
      [2, 'completed', 'STANDARD', 1],
    ]);
    expect(record.attempts[1]?.run_id).not.toBe(h.run.runId);
    expect(record).toMatchObject({ outcome: 'completed', turns: 2, effort: 'STANDARD' });
    expect(record).not.toHaveProperty('failure');
    expect(h.notices()).toContain("Attempt 1 did not finish. Auto effort tries again at the ladder's next rung, in the same copy.");
    expect(h.spend.entries.map((entry) => entry.turns)).toEqual([1, 1]);
  });

  it('stops climbing where the ladder ends', async () => {
    const h = harness({ request: { effort: 'auto' }, services: { catalogue: { ...CATALOGUE, ladder: { ...CATALOGUE.ladder, exhausted_after: 1 } } } });
    h.processes.onSpawn = (child) => {
      write(child, { type: 'failed', reason: 'empty_response' });
      child.exit({ code: 0, signal: null });
    };
    const record = await h.run.execute();
    expect(record).toMatchObject({ outcome: 'failed', failure: { reason: 'empty_response' } });
    expect(record.attempts).toHaveLength(1);
    expect(h.git.named('commitAll')).toEqual([]);
  });

  it("tells an engine that never took a turn from a task that failed, in the engine's own words", async () => {
    const outcome = async (exit: { code: number | null; signal: string | null; error?: string }, stderr = '', events: unknown[] = []) => {
      const h = harness();
      h.processes.onSpawn = (child) => {
        write(child, ...events);
        child.stderr(stderr);
        child.exit(exit);
      };
      const record = await h.run.execute();
      return [record.outcome, record.error];
    };
    expect(await outcome({ code: null, signal: null, error: 'spawn /bin/gptossloop ENOENT' })).toEqual(['error', 'gptossloop could not be started: spawn /bin/gptossloop ENOENT']);
    expect(await outcome({ code: 2, signal: null }, 'Traceback...\nqwenloop: error: model not found\n')).toEqual(['error', 'Traceback...\nqwenloop: error: model not found']);
    expect(await outcome({ code: 2, signal: null })).toEqual(['error', 'gptossloop ended with exit code 2 before its first turn']);
    expect(await outcome({ code: null, signal: 'SIGKILL' })).toEqual(['error', 'gptossloop ended with signal SIGKILL before its first turn']);
    expect(await outcome({ code: 1, signal: null }, '', [{ type: 'turn.completed', turn: 1 }])).toEqual(['failed', undefined]);
    const long = await outcome({ code: 2, signal: null }, 'x'.repeat(TaskRun.STDERR_TAIL + 500));
    expect(long[1]).toHaveLength(TaskRun.STDERR_TAIL);
  });

  it('reports an engine that cannot run before anything starts, and shows a catalogue notice first', async () => {
    const h = harness({
      services: {
        command: () => 'gptossloop cannot run: not found on PATH. It ships with vibey (pip install vibey), or set vibey.gptossloopPath.',
        catalogue: { ...CATALOGUE, notice: 'vibey loops is not available, so the picker is limited.' },
      },
    });
    const record = await h.run.execute();
    expect(record).toMatchObject({ outcome: 'error', error: expect.stringContaining('gptossloop cannot run') as unknown as string, mode: 'worktree' });
    expect(h.processes.children).toEqual([]);
    expect(h.notices()[0]).toBe('vibey loops is not available, so the picker is limited.');
    expect(fs.existsSync(path.join(h.runDirectory, 'result.json'))).toBe(true);
  });

  it('asks the engine to wind down on Stop, and records the wound-down exit as such', async () => {
    const h = harness();
    h.processes.onSpawn = async (child) => {
      write(child, { type: 'turn.completed', turn: 1 });
      expect(await h.run.stop()).toBeUndefined();
      expect(h.run.status).toBe('stopping');
      expect(h.run.stopRequestedAt).toBe(0);
      child.exit({ code: QwenloopCommand.EXIT_WOUND_DOWN, signal: null });
    };
    const record = await h.run.execute();
    const child = h.processes.children[0] as FakeChildControl;
    expect(record.outcome).toBe('wound-down');
    expect(h.processes.calls).toEqual([
      { command: '/bin/gptossloop', args: ['stop', h.run.runId, '--cwd', h.worktree], options: { env: child.options.env, timeoutMs: 30_000 } },
    ]);
    expect(h.notices()).toContain('Stopping. The model finishes the turn it is on, then the task ends; a slow turn can take a few minutes.');
    expect(h.statuses).toEqual(['preparing', 'waiting', 'running', 'stopping', 'finishing', 'finished']);
    expect(h.git.named('commitAll')).toEqual([]);
    expect(await h.run.stop()).toBe('This task has already finished.');
  });

  it("says when a stop cannot be sent, and when an engine has no stop, and ends a stopped run's failure as wound down", async () => {
    const h = harness();
    h.processes.on(['stop'], { code: 1, stderr: 'no such run\n' });
    h.processes.onSpawn = async (child) => {
      expect(await h.run.stop()).toBe('The stop could not be sent: no such run');
      child.exit({ code: 1, signal: null });
    };
    expect((await h.run.execute()).outcome).toBe('wound-down');

    // An engine whose catalogue declares no controls at all.
    const bare = { ...engineOf('codexloop'), controls: { stop: null, wind_down: null, prompt: null } };
    const codex = harness({ request: { loop: 'paidloop' }, select: () => selection('codexloop', { engine: bare }) });
    codex.processes.onSpawn = async (child) => {
      expect(await codex.run.followUp('hello')).toBe('codexloop does not take follow-ups while it runs.');
      expect(await codex.run.stop()).toBe(
        'codexloop has no stop command, so it cannot be asked to wind down. Force stop opens once a stop has waited its fair time.',
      );
      // Stop was pressed: the fair time for Force stop runs from now, and follow-ups are over.
      expect(codex.run.status).toBe('stopping');
      expect(await codex.run.followUp('hello')).toBe('This task is not running, so there is nothing to send a follow-up to.');
      child.exit({ code: 0, signal: null });
    };
    expect((await codex.run.execute()).outcome).toBe('completed');
  });

  it('opens Force stop only after a graceful stop has had its fair time, and journals it', async () => {
    const h = harness();
    h.processes.onSpawn = async (child) => {
      expect(h.run.forceStop(120_000)).toBe('Press Stop first. A run is always asked to end gracefully before it can be forced.');
      await h.run.stop();
      h.clock.advance(30_000);
      expect(h.run.forceStop(120_000)).toBe('Stop was asked 30 s ago. Force stop opens after 120 s, so the model can finish its turn.');
      h.clock.advance(91_000);
      expect(h.run.forceStop(120_000)).toBeUndefined();
      expect(child.killed).toEqual(['SIGTERM']);
      child.exit({ code: null, signal: 'SIGTERM' });
    };
    const record = await h.run.execute();
    expect(record).toMatchObject({ outcome: 'wound-down', signal: 'SIGTERM', force_stopped_at: '2026-09-24T12:02:01.000Z' });
    expect(h.history.forced).toEqual([[h.run.runId, 121_000]]);
    expect(h.notices()).toContain('Force stop: the process was ended 121 s after the graceful stop was asked.');
  });

  it('never starts a run stopped before its turn came, and records nothing for it', async () => {
    const stopped = harness();
    expect(await stopped.run.stop()).toBeUndefined();
    expect(stopped.run.stopRequestedAt).toBe(0);
    const record = await stopped.run.execute();
    expect(record).toMatchObject({ outcome: 'wound-down', error: 'Stopped before it started.', model: 'gpt-oss:20b', argv: [], attempts: [] });
    expect(record).not.toHaveProperty('engine');
    expect(record).not.toHaveProperty('mode');
    expect(stopped.statuses).toEqual(['finished']);
    expect(stopped.history.records).toEqual([]);
    expect(fs.existsSync(stopped.runDirectory)).toBe(false);

    const forced = harness({ request: { loop: 'paidloop' } });
    expect(forced.run.forceStop(1)).toBeUndefined();
    expect(await forced.run.execute()).toMatchObject({ outcome: 'wound-down', model: null });
  });

  it('never starts a run stopped while it waited for the model', async () => {
    const released = harness();
    released.lock.busy = 1;
    released.lock.whileWaiting = () => released.run.stop();
    const record = await released.run.execute();
    expect(record).toMatchObject({ outcome: 'wound-down', error: 'Stopped before it started.', mode: 'worktree' });
    expect(released.processes.children).toEqual([]);
    expect(released.lock.released).toBe(1);
    expect(fs.existsSync(path.join(released.runDirectory, 'result.json'))).toBe(true);

    const refused = harness();
    refused.lock.whileWaiting = () => refused.run.stop();
    refused.lock.failWith = new Error('stopped while waiting for the model');
    expect(await refused.run.execute()).toMatchObject({ outcome: 'wound-down', error: 'stopped while waiting for the model' });

    const broken = harness();
    broken.lock.failWith = new Error('EACCES: the lock directory cannot be made');
    expect(await broken.run.execute()).toMatchObject({ outcome: 'error', error: 'EACCES: the lock directory cannot be made' });
  });

  it('sends follow-ups to a running engine that takes them, and says plainly when it cannot', async () => {
    // gptossloop takes follow-ups, as vibey's catalogue says.
    const h = harness();
    expect(h.run.takesFollowUps).toBe(false);
    expect(await h.run.followUp('hello')).toBe('This task is not running, so there is nothing to send a follow-up to.');
    let answer: { code: number | null; error?: string } = { code: 0 };
    h.processes.on(['prompt'], () => answer);
    h.processes.onSpawn = async (child) => {
      expect(h.run.takesFollowUps).toBe(true);
      expect(await h.run.followUp('   ')).toBe('There is nothing to send.');
      expect(await h.run.followUp(' make it shorter ')).toBeUndefined();
      answer = { code: 3 };
      expect(await h.run.followUp('again')).toBe('The follow-up could not be sent: exit 3');
      answer = { code: null, error: 'timed out after 30000 ms' };
      expect(await h.run.followUp('once more')).toBe('The follow-up could not be sent: timed out after 30000 ms');
      child.exit({ code: 0, signal: null });
    };
    await h.run.execute();
    expect(h.processes.calls[0]?.args).toEqual(['prompt', '--cwd', h.worktree, '--', h.run.runId, 'make it shorter']);
    expect(h.notices()).toContain('Follow-up sent. The model reads it at the start of its next turn.');
  });

  it('gives no follow-up to an engine whose catalogue declares no prompt', async () => {
    const gptossloop = engineOf('gptossloop');
    const silent = { ...gptossloop, controls: { ...gptossloop.controls, prompt: null } };
    const h = harness({ select: () => selection('gptossloop', { engine: silent }) });
    h.processes.onSpawn = async (child) => {
      expect(h.run.takesFollowUps).toBe(false);
      expect(await h.run.followUp('hello')).toBe('gptossloop does not take follow-ups while it runs.');
      child.exit({ code: 75, signal: null });
    };
    await h.run.execute();
    expect(h.processes.calls).toEqual([]);
  });

  it('refuses run records or a worktree on storage a restart empties', async () => {
    const records = harness();
    records.gate.refuse = 'run records';
    expect(await records.run.execute()).toMatchObject({ outcome: 'error', error: 'run records would be on storage a restart empties' });
    expect(records.statuses).toEqual(['preparing', 'finished']);
    expect(records.git.calls).toEqual([]);
    expect(fs.existsSync(records.runDirectory)).toBe(false);

    const worktree = harness();
    worktree.gate.refuse = 'task worktree';
    expect(await worktree.run.execute()).toMatchObject({ outcome: 'error', error: 'task worktree would be on storage a restart empties' });
    expect(worktree.git.named('addWorktree')).toEqual([]);
    expect(fs.existsSync(path.join(worktree.runDirectory, 'result.json'))).toBe(true);
  });

  it('refuses a run a budget would not allow, before it starts', async () => {
    const h = harness();
    h.budgets.refusals = [BREACH];
    const record = await h.run.execute();
    expect(record).toMatchObject({
      outcome: 'budget-exhausted',
      error: `Not started: ${BREACH.message} Edit the budget to allow it.`,
      budget: { id: 'b1', cap: 'turns', limit: 1, spent: 1, message: BREACH.message },
      projection: { turns: 16, dollars: 0, per_turn: DECLARED },
    });
    expect(h.run.budgetBreach).toBe(BREACH);
    expect(h.processes.children).toEqual([]);
  });

  it('projects no turns or dollars for an engine that takes no turn limit', async () => {
    const h = harness({ request: { loop: 'paidloop' }, select: () => selection('codexloop') });
    h.budgets.refusals = [BREACH];
    const record = await h.run.execute();
    expect(record.projection).toEqual({ per_turn: DECLARED });
    expect(h.budgets.asked).toEqual([{ loop: 'paidloop', engineId: 'codexloop', runId: h.run.runId, projected: {} }]);
  });

  it('winds a lane down when a budget is used up while it runs; nothing is killed', async () => {
    const h = harness();
    h.budgets.used = BREACH;
    h.processes.onSpawn = async (child) => {
      write(child, { type: 'turn.completed', turn: 1 });
      h.clock.tick();
      expect(h.run.status).toBe('stopping');
      await settle();
      h.clock.tick();
      child.exit({ code: QwenloopCommand.EXIT_WOUND_DOWN, signal: null });
    };
    const record = await h.run.execute();
    expect(record).toMatchObject({ outcome: 'budget-exhausted', budget: { id: 'b1' } });
    expect(h.processes.calls.map((call) => call.args[0])).toEqual(['stop']);
    expect((h.processes.children[0] as FakeChildControl).killed).toEqual([]);
    expect(h.notices()).toContain(`${BREACH.message} The lane winds down at the end of this turn; Grant more to raise the budget.`);
  });

  it('keeps the result of a lane that finished its work after its budget ran out, and calls a failure then budget-exhausted', async () => {
    const finished = harness();
    finished.budgets.used = BREACH;
    finished.processes.onSpawn = (child) => {
      write(child, DONE[0]);
      finished.clock.tick();
      write(child, DONE[1], DONE[2]);
      child.exit({ code: 0, signal: null });
    };
    expect(await finished.run.execute()).toMatchObject({ outcome: 'completed', budget: { id: 'b1' } });

    const failed = harness();
    failed.budgets.used = BREACH;
    failed.processes.onSpawn = (child) => {
      write(child, { type: 'turn.completed', turn: 1 });
      failed.clock.tick();
      write(child, { type: 'failed', reason: 'turn_limit' });
      child.exit({ code: 0, signal: null });
    };
    expect((await failed.run.execute()).outcome).toBe('budget-exhausted');
  });

  it("stops auto effort's climb at a budget", async () => {
    const h = harness({ request: { effort: 'auto' } });
    h.budgets.refusals = [undefined, BREACH];
    h.processes.onSpawn = (child) => {
      write(child, { type: 'turn.completed', turn: 1 }, { type: 'failed', reason: 'turn_limit' });
      child.exit({ code: 0, signal: null });
    };
    const record = await h.run.execute();
    expect(record).toMatchObject({ outcome: 'budget-exhausted', error: `Auto effort stops climbing: ${BREACH.message}` });
    expect(record.attempts).toHaveLength(1);
  });

  it('reads the event log as it grows: lines that are not JSON, a replaced log, and a long quiet spell', async () => {
    const h = harness({ settings: { stuckHintMs: 300_000 } });
    h.processes.onSpawn = (child) => {
      const file = eventsOf(child);
      write(child, { type: 'turn.completed', turn: 1 });
      h.clock.tick();
      fs.appendFileSync(file, 'this is not json\n');
      h.clock.tick();
      fs.writeFileSync(file, `${JSON.stringify({ type: 'turn.started' })}\n`);
      h.clock.tick();
      h.clock.advance(300_000);
      h.clock.tick();
      h.clock.tick();
      write(child, { type: 'turn.completed', turn: 2 });
      h.clock.tick();
      child.exit({ code: 75, signal: null });
    };
    await h.run.execute();
    const notices = h.notices();
    expect(notices).toContain('1 line(s) of the event log were not JSON and were skipped.');
    expect(notices).toContain('The event log was replaced, so it is being read again from the start.');
    expect(notices.filter((text) => text.startsWith('Quiet for 5 minutes.'))).toHaveLength(1);
    expect(h.clock.active).toBe(0);
  });

  it('says so when the result cannot be recorded, and still finishes', async () => {
    const h = harness();
    h.history.failing = true;
    h.processes.onSpawn = (child) => child.exit({ code: 75, signal: null });
    const record = await h.run.execute();
    expect(record.outcome).toBe('wound-down');
    expect(h.notices()).toContain('The result could not be recorded: disk full');
    expect(h.run.status).toBe('finished');
  });
});

describe('RunHistory', () => {
  it('keeps every finished run and what was done with it since, newest first', () => {
    const journal = new JsonlJournal(path.join(scratch(), 'runs.jsonl'));
    const history = new RunHistory(journal, () => new Date('2026-09-24T13:00:00.000Z'));
    history.finished({ run_id: 'a', title: 'A' } as RunRecord);
    history.finished({ run_id: 'b', title: 'B' } as RunRecord);
    history.applied('a', 'merged into main');
    history.discarded('b');
    history.forceStopped('b', 121_000);
    history.applied('ghost', 'never finished here');
    fs.appendFileSync(journal.file, '{"type": "run.applied"}\n');
    expect(history.list()).toEqual([
      { record: { run_id: 'b', title: 'B' }, discarded: '2026-09-24T13:00:00.000Z' },
      { record: { run_id: 'a', title: 'A' }, applied: '2026-09-24T13:00:00.000Z' },
    ]);
    expect(journal.readAll().records.map((line) => line.type)).toEqual([
      'run.finished',
      'run.finished',
      'run.applied',
      'run.discarded',
      'run.force-stopped',
      'run.applied',
      'run.applied',
    ]);
    expect(journal.readAll().records[4]).toEqual({ type: 'run.force-stopped', run_id: 'b', after_ms: 121_000, at: '2026-09-24T13:00:00.000Z' });
  });
});
