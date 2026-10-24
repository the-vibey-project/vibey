// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import type { FollowEnd, ProjectEvent, ProjectReaderInterface, ProjectSnapshot } from '../../src/interfaces/project-follower-interface';
import type { VibeyGate } from '../../src/interfaces/vibey-cli-interface';
import { ProjectFollower } from '../../src/project-follower';

const gate = (id: string, over: Partial<VibeyGate> = {}): VibeyGate => ({
  gate_id: id,
  project_id: 'p1',
  project_name: 'greeter',
  job_id: null,
  kind: 'design_interview',
  prompt: 'q?',
  options: [],
  default_answer: null,
  timeout_at: null,
  ...over,
});
const snap = (over: Partial<ProjectSnapshot> = {}): ProjectSnapshot => ({ name: 'greeter', phase: 'design', queue: {}, gates: [], ...over });

/** A project that moves through scripted looks, on a clock that only advances when slept on. */
class Script implements ProjectReaderInterface {
  looks = 0;
  now = 0;
  constructor(private readonly steps: readonly ProjectSnapshot[]) {}

  async status(): Promise<{ name: string; phase: string; cycle?: number; max_cycles?: number; queue_depth: Record<string, number> }> {
    const step = this.steps[Math.min(this.looks, this.steps.length - 1)] as ProjectSnapshot;
    return { name: step.name, phase: step.phase.toUpperCase(), ...(step.cycle === undefined ? {} : { cycle: step.cycle }), ...(step.maxCycles === undefined ? {} : { max_cycles: step.maxCycles }), queue_depth: Object.fromEntries(Object.entries(step.queue).map(([k, v]) => [k.toUpperCase(), v])) };
  }

  async gates(): Promise<readonly VibeyGate[]> {
    const step = this.steps[Math.min(this.looks, this.steps.length - 1)] as ProjectSnapshot;
    this.looks += 1;
    return step.gates;
  }

  timer = {
    monotonic: (): number => this.now,
    sleep: async (ms: number): Promise<void> => {
      this.now += ms;
    },
  };
}

const run = async (steps: readonly ProjectSnapshot[], over: Partial<{ maxMs: number; heartbeatMs: number; stallMs: number }> = {}, cancelAfter = Infinity): Promise<{ end: FollowEnd; events: ProjectEvent[]; script: Script }> => {
  const script = new Script(steps);
  const events: ProjectEvent[] = [];
  const end = await new ProjectFollower(script, script.timer).follow(
    'p1',
    { pollMs: 1000, maxMs: 60_000, heartbeatMs: 10_000, stallMs: 5_000, ...over, onEvent: (event) => events.push(event) },
    () => script.looks >= cancelAfter,
  );
  return { end, events, script };
};

describe('ProjectFollower.snapshot', () => {
  it("reads the project's status and its own gates, lower-casing vibey's words", async () => {
    const script = new Script([snap({ phase: 'build', cycle: 2, maxCycles: 10, queue: { ready: 3, leased: 1 }, gates: [gate('g1')] })]);
    const taken = await new ProjectFollower(script, script.timer).snapshot('p1');
    expect(taken).toMatchObject({ name: 'greeter', phase: 'build', cycle: 2, maxCycles: 10, queue: { ready: 3, leased: 1 } });
    expect(taken.gates.map((g) => g.gate_id)).toEqual(['g1']);
  });

  it('leaves out a cycle the status does not give', async () => {
    const script = new Script([snap()]);
    const taken = await new ProjectFollower(script, script.timer).snapshot('p1');
    expect('cycle' in taken || 'maxCycles' in taken).toBe(false);
  });
});

describe('ProjectFollower.diff', () => {
  const follower = new ProjectFollower(new Script([snap()]), { monotonic: () => 0, sleep: async () => undefined });

  it('says where a project is the first time, and when its phase changes', () => {
    expect(follower.diff(undefined, snap({ cycle: 1, maxCycles: 10 }))).toEqual([{ kind: 'phase', name: 'greeter', from: undefined, to: 'design', cycle: 1, maxCycles: 10 }]);
    expect(follower.diff(snap(), snap({ phase: 'build' }))).toEqual([{ kind: 'phase', name: 'greeter', from: 'design', to: 'build' }]);
    expect(follower.diff(snap(), snap())).toEqual([]);
  });

  it('says a project is finished, and stops there', () => {
    expect(follower.diff(snap({ phase: 'review' }), snap({ phase: 'done', gates: [gate('g')] }))).toEqual([{ kind: 'finished', name: 'greeter', phase: 'done' }]);
    expect(follower.diff(undefined, snap({ phase: 'abandoned' }))).toEqual([{ kind: 'finished', name: 'greeter', phase: 'abandoned' }]);
  });

  it('reports a gate once, when it first appears', () => {
    const open = snap({ gates: [gate('g1')] });
    expect(follower.diff(snap(), open)).toEqual([{ kind: 'gate', gate: gate('g1') }]);
    expect(follower.diff(open, open)).toEqual([]);
    expect(follower.diff(open, snap({ gates: [gate('g1'), gate('g2')] }))).toEqual([{ kind: 'gate', gate: gate('g2') }]);
  });

  it('reports jobs that failed since the last look, never on the first look', () => {
    expect(follower.diff(snap({ queue: { failed: 1 } }), snap({ queue: { failed: 3 } }))).toEqual([{ kind: 'failed', name: 'greeter', count: 2 }]);
    expect(follower.diff(snap({ queue: { failed: 3 } }), snap({ queue: { failed: 3 } }))).toEqual([]);
    expect(follower.diff(snap({ queue: { failed: 3 } }), snap({ queue: {} }))).toEqual([]);
    expect(follower.diff(undefined, snap({ queue: { failed: 2 } }))).toHaveLength(1);
    expect(follower.diff(snap(), snap({ queue: { failed: 1 } }))).toEqual([{ kind: 'failed', name: 'greeter', count: 1 }]);
  });
});

describe('ProjectFollower.describe', () => {
  const follower = new ProjectFollower(new Script([snap()]), { monotonic: () => 0, sleep: async () => undefined });

  it('says what a phase is, with its cycle when it has one', () => {
    expect(follower.describe({ kind: 'phase', name: 'g', from: undefined, to: 'design' })).toBe('"g" is designing: it interviews you and writes the design.');
    expect(follower.describe({ kind: 'phase', name: 'g', from: 'design', to: 'build', cycle: 1, maxCycles: 10 })).toContain('moved on: now building: it writes the code on its own');
    expect(follower.describe({ kind: 'phase', name: 'g', from: 'design', to: 'build', cycle: 2 })).toContain('(cycle 2)');
    expect(follower.describe({ kind: 'phase', name: 'g', from: 'design', to: 'build', cycle: 1, maxCycles: 10 })).toContain('(cycle 1 of 10)');
    expect(follower.describe({ kind: 'phase', name: 'g', from: undefined, to: 'mystery' })).toBe('"g" is mystery.');
  });

  it('names a project that needs you, by name or by id', () => {
    expect(follower.describe({ kind: 'gate', gate: gate('g1') })).toBe('"greeter" needs you (design_interview).');
    expect(follower.describe({ kind: 'gate', gate: gate('g1', { project_name: undefined }) })).toBe('"p1" needs you (design_interview).');
  });

  it('says what failed, stalled and finished, with the command that helps', () => {
    expect(follower.describe({ kind: 'failed', name: 'g', count: 1 })).toMatch(/^1 job failed in "g"\..*\/resume/);
    expect(follower.describe({ kind: 'failed', name: 'g', count: 2 })).toMatch(/^2 jobs failed/);
    expect(follower.describe({ kind: 'stalled', name: 'g', seconds: 12.4 })).toMatch(/12 seconds.*no worker.*\/resume/);
    expect(follower.describe({ kind: 'finished', name: 'g', phase: 'done' })).toBe('"g" is done.');
    expect(follower.describe({ kind: 'finished', name: 'g', phase: 'abandoned' })).toBe('"g" was unwound.');
  });

  it('says it is still working, with what is running and waiting', () => {
    expect(follower.describe({ kind: 'working', name: 'g', phase: 'build', ready: 2, running: 1 })).toBe('Still working on "g" (building; 1 running, 2 waiting).');
    expect(follower.describe({ kind: 'working', name: 'g', phase: 'build', ready: 0, running: 0 })).toBe('Still working on "g" (building).');
    expect(follower.describe({ kind: 'working', name: 'g', phase: 'odd', ready: 0, running: 2 })).toBe('Still working on "g" (odd; 2 running).');
  });
});

describe('ProjectFollower.follow', () => {
  it('hands back when a question appears, having said where the project is first', async () => {
    const { end, events } = await run([snap(), snap(), snap({ gates: [gate('g1')] })]);
    expect(end).toBe('needs-you');
    expect(events.map((e) => e.kind)).toEqual(['phase', 'gate']);
  });

  it('hands back at once for a question that was already waiting when the follow began', async () => {
    const { end, events, script } = await run([snap({ gates: [gate('g1')] })]);
    expect(end).toBe('needs-you');
    expect(events.map((e) => e.kind)).toEqual(['phase', 'gate']);
    expect(script.looks).toBe(1);
  });

  it('follows a project through its phases to the end', async () => {
    const { end, events } = await run([snap(), snap({ phase: 'build' }), snap({ phase: 'review' }), snap({ phase: 'done' })]);
    expect(end).toBe('finished');
    expect(events.map((e) => (e.kind === 'phase' ? e.to : e.kind))).toEqual(['design', 'build', 'review', 'finished']);
  });

  it('stops at the first look when told to, and mid-way when told to', async () => {
    expect((await run([snap()], {}, 0)).end).toBe('cancelled');
    const midway = await run([snap(), snap(), snap({ phase: 'build' })], {}, 2);
    expect(midway.end).toBe('cancelled');
  });

  it('says it is still working after a quiet while, and gives up when its time is up', async () => {
    const { end, events } = await run([snap({ phase: 'build', queue: { leased: 1 } })], { maxMs: 25_000, heartbeatMs: 10_000 });
    expect(end).toBe('timeout');
    expect(events.map((e) => e.kind)).toEqual(['phase', 'working', 'working']);
  });

  it('counts what is waiting as well as what is running when it says it is still working', async () => {
    const { events } = await run([snap({ phase: 'build', queue: { ready: 4 } })], { maxMs: 12_000, heartbeatMs: 10_000, stallMs: 1_000_000 });
    expect(events.find((e) => e.kind === 'working')).toMatchObject({ ready: 4, running: 0 });
  });

  it('says when work is queued and nothing is running it, once, and not while it runs', async () => {
    const waiting = snap({ phase: 'build', queue: { ready: 2 } });
    const stalled = await run([waiting], { maxMs: 20_000, stallMs: 5_000, heartbeatMs: 1_000_000 });
    expect(stalled.events.filter((e) => e.kind === 'stalled')).toHaveLength(1);
    const running = await run([snap({ phase: 'build', queue: { ready: 2, leased: 1 } })], { maxMs: 20_000, stallMs: 5_000, heartbeatMs: 1_000_000 });
    expect(running.events.some((e) => e.kind === 'stalled')).toBe(false);
  });

  it('forgets a stall when work starts, so a later one is said again', async () => {
    const waiting = snap({ phase: 'build', queue: { ready: 1 } });
    const running = snap({ phase: 'build', queue: { ready: 1, leased: 1 } });
    const steps = [waiting, waiting, waiting, waiting, waiting, waiting, running, waiting, waiting, waiting, waiting, waiting, waiting, waiting];
    const { events } = await run(steps, { maxMs: 14_000, stallMs: 3_000, heartbeatMs: 1_000_000 });
    expect(events.filter((e) => e.kind === 'stalled')).toHaveLength(2);
  });

  it('reports jobs that fail while it watches', async () => {
    const { events } = await run([snap({ phase: 'build' }), snap({ phase: 'build', queue: { failed: 1 } })], { maxMs: 3_000 });
    expect(events.some((e) => e.kind === 'failed')).toBe(true);
  });
});
