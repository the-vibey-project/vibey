// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { HubError } from '../../src/core/hub-client';
import type { WorkflowRun } from '../../src/core/interfaces/hub-client-interface';
import { WorkflowRuns } from '../../src/core/workflow-runs';

const run = (fields: Partial<WorkflowRun>): WorkflowRun => ({
  request_id: 'r1',
  state: 'queued',
  url: '',
  exit_code: null,
  stdout: '',
  stderr: '',
  detail: '',
  ...fields,
});

/** A hub whose run moves through `states`, one per read, with a clock that sleeping advances. */
function scripted(states: readonly (WorkflowRun | Error)[]) {
  let clock = 0;
  const slept: number[] = [];
  const reads: string[] = [];
  const started: (readonly string[])[] = [];
  const queue = [...states];
  const client = {
    startWorkflowRun: async (argv: readonly string[]) => {
      started.push(argv);
      return run({});
    },
    workflowRun: async (requestId: string) => {
      reads.push(requestId);
      const next = queue.shift() ?? run({ state: 'running' });
      if (next instanceof Error) throw next;
      return next;
    },
  };
  const runs = new WorkflowRuns({
    now: () => clock,
    sleep: async (ms) => {
      slept.push(ms);
      clock += ms;
    },
  });
  return { client, runs, slept, reads, started };
}

describe('WorkflowRuns.split', () => {
  const runs = new WorkflowRuns();

  it('splits on white space and keeps a double-quoted phrase as one word', () => {
    expect(runs.split('  status   --json ')).toEqual({ ok: true, argv: ['status', '--json'] });
    expect(runs.split('new "a greeter app"\t--yes')).toEqual({ ok: true, argv: ['new', 'a greeter app', '--yes'] });
    expect(runs.split('note --title="two words" ""')).toEqual({ ok: true, argv: ['note', '--title=two words', ''] });
  });

  it('drops a leading vibey and -w, as a shell line would carry them', () => {
    expect(runs.split('vibey -w status')).toEqual({ ok: true, argv: ['status'] });
    expect(runs.split('vibey --workflows doctor --json')).toEqual({ ok: true, argv: ['doctor', '--json'] });
    expect(runs.split('-w gates')).toEqual({ ok: true, argv: ['gates'] });
    expect(runs.split('vibey status')).toEqual({ ok: true, argv: ['status'] });
  });

  it('refuses an unclosed quote, an empty line and an over-long one', () => {
    expect(runs.split('new "half')).toEqual({ ok: false, reason: 'A double quote is not closed.' });
    expect(runs.split('   ')).toMatchObject({ ok: false, reason: expect.stringMatching(/status --json/) });
    expect(runs.split('vibey -w')).toMatchObject({ ok: false });
    expect(runs.split(Array.from({ length: 201 }, () => 'x').join(' '))).toMatchObject({ ok: false, reason: expect.stringMatching(/200 words/) });
    expect(runs.split(Array.from({ length: 200 }, () => 'x').join(' '))).toMatchObject({ ok: true });
  });
});

describe('WorkflowRuns.follow', () => {
  it('reads every 10 seconds until the run is done, reporting each state', async () => {
    const done = run({ state: 'done', url: 'https://github.com/o/r/actions/runs/1', exit_code: 0, stdout: 'ok' });
    const { client, runs, slept, reads, started } = scripted([run({ state: 'running' }), done]);
    const seen: string[] = [];
    const outcome = await runs.follow(client, ['status', '--json'], { onUpdate: (next) => seen.push(next.state) });
    expect(outcome).toEqual({ kind: 'finished', run: done });
    expect(started).toEqual([['status', '--json']]);
    expect(reads).toEqual(['r1', 'r1']);
    expect(slept).toEqual([10_000, 10_000]);
    expect(seen).toEqual(['queued', 'running', 'done']);
  });

  it('finishes on a failed run, and needs no hooks', async () => {
    const failed = run({ state: 'failed', detail: 'the workflow is not on the default branch' });
    const { client, runs } = scripted([failed]);
    await expect(runs.follow(client, ['status'])).resolves.toEqual({ kind: 'finished', run: failed });
  });

  it('gives up after 60 minutes and says where the run carries on', async () => {
    const { client, runs, slept } = scripted(Array.from({ length: 400 }, () => run({ state: 'running', url: 'https://github.com/o/r/actions/runs/2' })));
    const outcome = await runs.follow(client, ['status']);
    expect(outcome).toMatchObject({
      kind: 'still-running',
      message: 'Still running at https://github.com/o/r/actions/runs/2. Stopped waiting after 60 min; the run carries on.',
    });
    expect(slept).toHaveLength(360);
  });

  it('names the request when GitHub has not shown the run yet', async () => {
    let clock = 0;
    const runs = new WorkflowRuns({ now: () => clock, sleep: async (ms) => void (clock += ms), everyMs: 1000, giveUpMs: 2000 });
    const client = { startWorkflowRun: async () => run({}), workflowRun: async () => run({}) };
    await expect(runs.follow(client, ['status'])).resolves.toMatchObject({
      kind: 'still-running',
      message: 'Still running on GitHub (request r1). Stopped waiting after 0 min; the run carries on.',
    });
  });

  it('stops reading once nobody watches', async () => {
    const { client, runs, reads } = scripted([]);
    const outcome = await runs.follow(client, ['status'], { cancelled: () => true });
    expect(outcome).toMatchObject({ kind: 'still-running', message: expect.stringMatching(/Stopped watching; the run carries on\.$/) });
    expect(reads).toEqual([]);
  });

  it('passes an HTTP refusal on, from the start or from a read', async () => {
    const refused = new HubError('forbidden', 'no scope', 403);
    const { client, runs } = scripted([refused]);
    await expect(runs.follow(client, ['status'])).rejects.toBe(refused);
    const off = new HubError('unavailable', 'not enabled', 503);
    const start = { startWorkflowRun: async () => Promise.reject(off), workflowRun: async () => run({}) };
    await expect(runs.follow(start, ['status'])).rejects.toBe(off);
  });

  it('waits on real timers by default', async () => {
    jest.useFakeTimers();
    try {
      const states = [run({ state: 'done', exit_code: 0 })];
      const client = { startWorkflowRun: async () => run({}), workflowRun: async () => states[0] as WorkflowRun };
      const pending = new WorkflowRuns().follow(client, ['status']);
      await jest.advanceTimersByTimeAsync(WorkflowRuns.EVERY_MS);
      await expect(pending).resolves.toMatchObject({ kind: 'finished' });
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('WorkflowRuns.present', () => {
  const runs = new WorkflowRuns();

  it('shows each state with its status role', () => {
    expect(runs.present(run({ state: 'queued' }))).toEqual({ label: 'Queued', role: 'neutral', finished: false });
    expect(runs.present(run({ state: 'running' }))).toEqual({ label: 'Running', role: 'info', finished: false });
    expect(runs.present(run({ state: 'failed' }))).toEqual({ label: 'Failed', role: 'danger', finished: true });
    expect(runs.present(run({ state: 'done', exit_code: 0 }))).toEqual({ label: 'Done · exit 0', role: 'success', finished: true });
    expect(runs.present(run({ state: 'done', exit_code: 2 }))).toEqual({ label: 'Done · exit 2', role: 'danger', finished: true });
    expect(runs.present(run({ state: 'done' }))).toEqual({ label: 'Done', role: 'success', finished: true });
  });
});
