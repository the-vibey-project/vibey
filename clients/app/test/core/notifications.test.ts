// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import type { VibeyGate, VibeyProject } from '@vibey/core';
import { NotificationPlanner } from '../../src/core/notifications';
import { SettingsModel } from '../../src/core/settings';

const planner = new NotificationPlanner();
const on = new SettingsModel().defaults.notifications;
const gate = (id: string, over: Partial<VibeyGate> = {}): VibeyGate => ({
  gate_id: id,
  project_id: 'p1',
  project_name: 'Greeter',
  job_id: null,
  kind: 'question',
  prompt: 'Who is it for?\nA second line.',
  options: [],
  default_answer: null,
  timeout_at: null,
  ...over,
});
const project = (phase: string, id = 'p1'): VibeyProject => ({ project_id: id, name: 'Greeter', phase });
const look = (gates: VibeyGate[], projects: VibeyProject[] = [project('BUILD')]) => planner.snapshot(projects, gates);

describe('NotificationPlanner', () => {
  it('reads a look at the hub, lower-casing phases and naming a project by id when it has no name', () => {
    expect(look([gate('g1', { project_name: undefined })])).toEqual({
      gates: [{ id: 'g1', kind: 'question', projectName: 'p1', prompt: 'Who is it for?\nA second line.' }],
      phases: { p1: { name: 'Greeter', phase: 'build' } },
    });
  });

  it('says nothing about what was already there when the app opened', () => {
    expect(planner.plan(undefined, look([gate('g1')]), on)).toEqual([]);
  });

  it('notifies a new question once, with its first line and where to answer it', () => {
    const before = look([gate('g1')]);
    const after = look([gate('g1'), gate('g2', { prompt: 'Which database?' })]);
    expect(planner.plan(before, after, on)).toEqual([
      { id: 'gate-g2', kind: 'gate', title: 'Greeter needs you', body: 'Which database?', route: '/gates' },
    ]);
    expect(planner.plan(after, after, on)).toEqual([]);
  });

  it('keeps a spending question in its own class, so it can be silenced apart', () => {
    const planned = planner.plan(look([]), look([gate('g1', { kind: 'budget_exhausted' })]), on);
    expect(planned.map((n) => n.kind)).toEqual(['budget']);
    expect(planner.plan(look([]), look([gate('g1', { kind: 'budget_exhausted' })]), { ...on, budget: false })).toEqual([]);
  });

  it('cuts a long first line, and has something to say when the prompt is empty', () => {
    const long = planner.plan(look([]), look([gate('g1', { prompt: 'x'.repeat(300) })]), on)[0];
    expect(long?.body).toHaveLength(NotificationPlanner.BODY_CHARS);
    expect(long?.body.endsWith('…')).toBe(true);
    expect(planner.plan(look([]), look([gate('g1', { prompt: '  \n ' })]), on)[0]?.body).toBe('Open krypton to answer.');
    expect(planner.plan(look([]), look([gate('g1', { prompt: 'short' })]), on)[0]?.body).toBe('short');
  });

  it('notifies when a project finishes or is unwound, but not for a project it has only just seen', () => {
    const done = planner.plan(look([], [project('BUILD')]), look([], [project('DONE')]), on);
    expect(done).toEqual([{ id: 'finished-p1', kind: 'finished', title: 'Greeter is done', body: 'Open krypton to see what it built.', route: '/' }]);
    const unwound = planner.plan(look([], [project('BUILD')]), look([], [project('ABANDONED')]), on);
    expect(unwound[0]).toMatchObject({ title: 'Greeter was unwound', route: '/' });
    expect(planner.plan(look([], []), look([], [project('DONE')]), on)).toEqual([]);
    expect(planner.plan(look([], [project('DONE')]), look([], [project('DONE')]), on)).toEqual([]);
    expect(planner.plan(look([], [project('DESIGN')]), look([], [project('BUILD')]), on)).toEqual([]);
  });

  it('leaves out every class the person switched off', () => {
    const before = look([], [project('BUILD')]);
    const after = look([gate('g1')], [project('DONE')]);
    expect(planner.plan(before, after, on).map((n) => n.kind)).toEqual(['gate', 'finished']);
    expect(planner.plan(before, after, { ...on, gate: false }).map((n) => n.kind)).toEqual(['finished']);
    expect(planner.plan(before, after, { ...on, finished: false }).map((n) => n.kind)).toEqual(['gate']);
  });
});
