// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { LaneEngine } from '../../src/core/interfaces/lanes-interface';
import type { RunRecord, RunRequest, RunStatus, TaskRunInterface } from '../../src/core/interfaces/run-interface';
import type { Disposable } from '../../src/core/interfaces/support-interface';
import { JsonlTail } from '../../src/core/jsonl';
import { LaneTracker } from '../../src/core/lanes';
import { RunQueue } from '../../src/core/run-queue';
import { scratch, settle } from './helpers';

const ENGINES: readonly LaneEngine[] = [
  { engineId: 'qwenloop', stateDir: '.qwenloop', envelope: 'type' },
  { engineId: 'claudeloop', stateDir: '.claudeloop', envelope: 'event_type+payload' },
];

/** Write a lane's events, dated `at` (epoch ms), the way a loop leaves them. */
function lane(cwd: string, stateDir: string, id: string, events: readonly unknown[], at: number, snapshot?: string): string {
  const directory = path.join(cwd, stateDir, 'runs', id);
  fs.mkdirSync(directory, { recursive: true });
  const file = path.join(directory, 'events.jsonl');
  fs.writeFileSync(file, events.map((event) => `${JSON.stringify(event)}\n`).join(''));
  if (snapshot !== undefined) {
    fs.mkdirSync(path.join(directory, 'snapshots'));
    fs.writeFileSync(path.join(directory, 'snapshots', 'latest.json'), snapshot);
  }
  fs.utimesSync(file, at / 1000, at / 1000);
  return file;
}

describe('LaneTracker', () => {
  const T = Date.parse('2026-09-24T12:00:00.000Z');

  it('finds every lane under the roots, whoever started it, and folds each into what a person reads', () => {
    const home = scratch();
    const worktree = path.join(home, 'vscode-vibey-docs-0123abcd');
    const running = lane(
      worktree,
      '.qwenloop',
      'r-running',
      [
        { type: 'text_delta', text: 'Reading ' },
        { type: 'text_delta', text: 'the README.' },
        { type: 'turn.completed', turn: 1, input_tokens: 1200, output_tokens: 300 },
        { type: 'tool.call', turn: 2, name: 'write_file', arguments: { path: 'README.md' } },
      ],
      T,
    );
    lane(worktree, '.qwenloop', 'r-answered', [{ type: 'tool.call', name: 'read_file' }, { type: 'tool_result', name: 'read_file', result: { content: 'a' } }], T - 1000);
    lane(home, '.claudeloop', 'c-done', [{ event_type: 'turn.completed', payload: { turn: 1, input_tokens: 5, output_tokens: 6 } }, { event_type: 'finished', payload: { success: true } }], T);
    lane(worktree, '.qwenloop', 'r-failed', [{ type: 'failed', reason: 'turn_limit', max_turns: 16 }], T);
    lane(worktree, '.qwenloop', 'r-completed-mid-call', [{ type: 'tool.call', name: 'run_tests' }, { type: 'completed', turn: 3 }], T);
    lane(worktree, '.qwenloop', 'r-stopped', [], T, '{"status": "winding_down"}');
    lane(worktree, '.qwenloop', 'r-snapshot-failed', [], T, '{"status": "failed"}');
    lane(worktree, '.qwenloop', 'r-snapshot-running', [], T, '{"status": "running"}');
    lane(worktree, '.qwenloop', 'r-snapshot-broken', [], T, '{broken');
    lane(worktree, '.qwenloop', 'r-quiet', [{ type: 'turn.completed', turn: 1 }], T - 10 * 60_000);
    lane(worktree, '.qwenloop', 'r-old', [{ type: 'turn.completed', turn: 1 }], T - 48 * 3_600_000);
    fs.mkdirSync(path.join(worktree, '.qwenloop', 'runs', 'r-no-events'));
    lane(path.join(home, '.hidden'), '.qwenloop', 'r-hidden', [], T);
    fs.writeFileSync(path.join(home, 'not-a-directory'), '');

    const tracker = new LaneTracker(ENGINES, () => [home, home], new JsonlTail(), () => T + 1000, 5 * 60_000, 24 * 3_600_000);
    expect(tracker.lanes()).toEqual([]);
    const lanes = tracker.refresh();
    expect(tracker.lanes()).toBe(lanes);
    const byId = new Map(lanes.map((each) => [each.id, each]));
    expect([...byId.keys()].sort()).toEqual([
      'c-done',
      'r-answered',
      'r-completed-mid-call',
      'r-failed',
      'r-quiet',
      'r-running',
      'r-snapshot-broken',
      'r-snapshot-failed',
      'r-snapshot-running',
      'r-stopped',
    ]);
    expect(byId.get('r-running')).toEqual({
      id: 'r-running',
      engine: 'qwenloop',
      cwd: worktree,
      eventsPath: running,
      label: 'vscode-vibey-docs-0123abcd · qwenloop',
      state: 'running',
      turn: 1,
      tool: 'write_file',
      startedAt: expect.any(Number) as unknown as number,
      lastEventAt: T,
      inputTokens: 1200,
      outputTokens: 300,
    });
    expect(byId.get('r-answered')).not.toHaveProperty('tool');
    expect(byId.get('c-done')).toMatchObject({ engine: 'claudeloop', cwd: home, state: 'finished', outcome: 'completed', turn: 1, inputTokens: 5 });
    expect(byId.get('r-failed')).toMatchObject({ state: 'finished', outcome: 'failed' });
    expect(byId.get('r-completed-mid-call')).toMatchObject({ state: 'finished', outcome: 'completed' });
    expect(byId.get('r-completed-mid-call')).not.toHaveProperty('tool');
    expect(byId.get('r-stopped')).toMatchObject({ state: 'finished', outcome: 'stopped' });
    expect(byId.get('r-snapshot-failed')).toMatchObject({ outcome: 'failed' });
    expect(byId.get('r-snapshot-running')).toMatchObject({ state: 'running' });
    expect(byId.get('r-snapshot-running')).not.toHaveProperty('outcome');
    expect(byId.get('r-snapshot-broken')).not.toHaveProperty('outcome');
    expect(byId.get('r-quiet')).toMatchObject({ state: 'quiet' });
    const started = lanes.map((each) => each.startedAt);
    expect(started).toEqual([...started].sort((left, right) => right - left));
    expect(tracker.items(running).map((item) => item.kind)).toEqual(['assistant', 'turn', 'tool-call']);
    expect(tracker.items('/nowhere/events.jsonl')).toEqual([]);
  });

  it('reads only what was added since the last look, and forgets a lane whose record is gone', () => {
    const home = scratch();
    const file = lane(home, '.qwenloop', 'r1', [{ type: 'tool.call', name: 'read_file' }], T);
    const gone = lane(home, '.qwenloop', 'r2', [], T);
    const tracker = new LaneTracker(ENGINES, () => [home], new JsonlTail(), () => T, 60_000, 3_600_000);
    expect(tracker.refresh().find((each) => each.id === 'r1')).toMatchObject({ tool: 'read_file', turn: 0 });
    fs.appendFileSync(file, `${JSON.stringify({ type: 'tool_result', name: 'read_file', result: { content: '' } })}\n${JSON.stringify({ type: 'turn.completed', turn: 1 })}\n`);
    fs.utimesSync(file, T / 1000, T / 1000);
    fs.rmSync(path.dirname(gone), { recursive: true });
    const lanes = tracker.refresh();
    expect(lanes.map((each) => each.id)).toEqual(['r1']);
    expect(lanes[0]).toMatchObject({ turn: 1 });
    expect(lanes[0]).not.toHaveProperty('tool');
    expect(tracker.items(file).map((item) => item.kind)).toEqual(['tool-call', 'tool-result', 'turn']);
  });

  it("dates a lane from its record's birth, or from its change time where the filesystem keeps no birth", () => {
    expect(LaneTracker.born({ birthtimeMs: 3, ctimeMs: 5 })).toBe(3);
    expect(LaneTracker.born({ birthtimeMs: 0, ctimeMs: 5 })).toBe(5);
  });
});

/** A run the queue can start and the test can finish. */
class FakeRun implements TaskRunInterface {
  readonly runId: string;
  readonly request: RunRequest;
  readonly status: RunStatus = 'queued';
  readonly workspace = undefined;
  readonly current = undefined;
  readonly stopRequestedAt = undefined;
  readonly takesFollowUps = false;
  readonly budgetBreach = undefined;
  readonly result: Promise<RunRecord>;
  executed = 0;
  stopped = 0;
  stopAnswer: string | undefined;
  private finish: (record: RunRecord) => void = () => undefined;
  private crashWith: (error: Error) => void = () => undefined;

  constructor(title: string) {
    this.runId = `run-${title}`;
    this.request = { title } as RunRequest;
    this.result = new Promise<RunRecord>((resolve, reject) => {
      this.finish = resolve;
      this.crashWith = reject;
    });
    // A crash is the queue's to handle; the test's own promise must not count as unhandled.
    this.result.catch(() => undefined);
  }

  items(): readonly [] {
    return [];
  }

  onPatch(): Disposable {
    return { dispose: () => undefined };
  }

  onStatus(): Disposable {
    return { dispose: () => undefined };
  }

  execute(): Promise<RunRecord> {
    this.executed += 1;
    return this.result;
  }

  async followUp(): Promise<string | undefined> {
    return undefined;
  }

  async stop(): Promise<string | undefined> {
    this.stopped += 1;
    return this.stopAnswer;
  }

  forceStop(): string | undefined {
    return undefined;
  }

  end(): void {
    this.finish({ run_id: this.runId, outcome: 'completed' } as RunRecord);
  }

  crash(): void {
    this.crashWith(new Error('broken'));
  }
}

describe('RunQueue', () => {
  const names = (runs: readonly TaskRunInterface[]): string[] => runs.map((run) => run.request.title);

  it('runs one task at a time per model, first come first served, and the next when one ends', async () => {
    const queue = new RunQueue(1);
    let changes = 0;
    const listening = queue.onChange(() => (changes += 1));
    const [a, b, c] = [new FakeRun('a'), new FakeRun('b'), new FakeRun('c')];
    queue.enqueue('gpt-oss:20b', a);
    queue.enqueue('gpt-oss:20b', b);
    queue.enqueue('paidloop', c);
    expect(names(queue.snapshot().running)).toEqual(['a', 'c']);
    expect(names(queue.snapshot().queued)).toEqual(['b']);
    expect(b.executed).toBe(0);
    a.end();
    await settle();
    expect(names(queue.snapshot().running)).toEqual(['b', 'c']);
    expect(b.executed).toBe(1);
    expect(changes).toBe(4);
    listening.dispose();
    b.end();
    await settle();
    expect(changes).toBe(4);
    expect(names(queue.snapshot().running)).toEqual(['c']);
  });

  it('lets more run at once when the limit allows', () => {
    const queue = new RunQueue(2);
    const runs = [new FakeRun('a'), new FakeRun('b'), new FakeRun('c')];
    runs.forEach((run) => queue.enqueue('m', run));
    expect(names(queue.snapshot().running)).toEqual(['a', 'b']);
    expect(names(queue.snapshot().queued)).toEqual(['c']);
  });

  it('frees the slot even when a run fails in a way it did not record', async () => {
    const queue = new RunQueue(1);
    const [a, b] = [new FakeRun('a'), new FakeRun('b')];
    queue.enqueue('m', a);
    queue.enqueue('m', b);
    a.crash();
    await settle();
    expect(names(queue.snapshot().running)).toEqual(['b']);
  });

  it('holds the line, starts it again, and moves a waiting run to the front', () => {
    const queue = new RunQueue(1);
    queue.pause();
    const [a, b, c] = [new FakeRun('a'), new FakeRun('b'), new FakeRun('c')];
    queue.enqueue('m', a);
    queue.enqueue('m', b);
    queue.enqueue('m', c);
    expect(queue.snapshot()).toMatchObject({ running: [], paused: true });
    expect(queue.bump(c)).toBe(true);
    expect(queue.snapshot().paused).toBe(false);
    expect(names(queue.snapshot().running)).toEqual(['c']);
    expect(names(queue.snapshot().queued)).toEqual(['a', 'b']);
    expect(queue.bump(new FakeRun('stranger'))).toBe(false);
    queue.pause();
    queue.resume();
    expect(names(queue.snapshot().running)).toEqual(['c']);
  });

  it('takes a waiting run out of the line, ending it without ever starting it', () => {
    const queue = new RunQueue(1);
    const [a, b] = [new FakeRun('a'), new FakeRun('b')];
    queue.enqueue('m', a);
    queue.enqueue('m', b);
    expect(queue.cancel(b)).toBe(true);
    expect(b.stopped).toBe(1);
    expect(b.executed).toBe(1);
    expect(names(queue.snapshot().queued)).toEqual([]);
    expect(queue.cancel(a)).toBe(false);
  });

  it('stops everything: holds the line, then asks each running run to wind down, and collects what failed', async () => {
    const queue = new RunQueue(1);
    const [a, b, c] = [new FakeRun('a'), new FakeRun('b'), new FakeRun('c')];
    a.stopAnswer = 'qwenloop stop failed';
    queue.enqueue('one', a);
    queue.enqueue('two', b);
    queue.enqueue('one', c);
    expect(await queue.stopAll()).toEqual(['a: qwenloop stop failed']);
    expect([a.stopped, b.stopped, c.stopped]).toEqual([1, 1, 0]);
    expect(queue.snapshot().paused).toBe(true);
    a.end();
    await settle();
    expect(names(queue.snapshot().running)).toEqual(['b']);
    expect(c.executed).toBe(0);
  });
});
