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
      gates: [{ id: 'g1', kind: 'question', projectName: 'p1', prompt: 'Who is it for?\nA second line.', options: [] }],
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
      {
        id: 'gate-g2',
        kind: 'gate',
        title: 'Greeter needs you',
        body: 'Which database?',
        route: '/gates',
        gateId: 'g2',
        gateKind: 'question',
        actions: [{ id: 'defaults', title: 'Accept the suggested answers' }],
      },
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
    expect(done).toEqual([{ id: 'finished-p1', kind: 'finished', title: 'Greeter is done', body: 'Open krypton to see what it built.', route: '/', actions: [] }]);
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

  describe('answer buttons', () => {
    it('offers the design interview its one button, and a verdict or choice its options', () => {
      expect(planner.actionsFor('question', [])).toEqual([{ id: 'defaults', title: 'Accept the suggested answers' }]);
      expect(planner.actionsFor('approval', ['accept', 'reject'])).toEqual([
        { id: 'accept', title: 'accept' },
        { id: 'reject', title: 'reject' },
      ]);
      expect(planner.actionsFor('choice', ['a', 'b', 'c']).map((a) => a.id)).toEqual(['a', 'b', 'c']);
    });

    it('offers none for a gate that spends, however many options it has', () => {
      expect(planner.actionsFor('budget_exhausted', ['25'])).toEqual([]);
      for (const kind of ['deploy_interview', 'deploy_failure_triage', 'deploy_acceptance', 'deploy_demo_review', 'deploy_anything']) {
        expect(planner.actionsFor(kind, ['yes', 'no'])).toEqual([]);
      }
    });

    it('offers none for a gate only the host answers, or one with no options or too many', () => {
      expect(planner.actionsFor('grant_attempts', ['3'])).toEqual([]);
      expect(planner.actionsFor('approval', [])).toEqual([]);
      expect(planner.actionsFor('choice', ['a', 'b', 'c', 'd'])).toEqual([]);
    });

    it('puts the buttons on the notification it plans, and none on a spending one', () => {
      const planned = planner.plan(look([]), look([gate('g1', { kind: 'approval', options: ['accept'] }), gate('g2', { kind: 'budget_exhausted', options: ['25'] })]), on);
      expect(planned.map((n) => [n.gateId, n.gateKind, n.actions.map((a) => a.id)])).toEqual([
        ['g1', 'approval', ['accept']],
        ['g2', 'budget_exhausted', []],
      ]);
    });

    it('names a set of buttons, the same for the same set', () => {
      const one = planner.actionsFor('approval', ['accept', 'reject']);
      expect(planner.categoryFor(one)).toBe('krypton-gate:accept|reject');
      expect(planner.categoryFor(planner.actionsFor('approval', ['accept', 'reject']))).toBe(planner.categoryFor(one));
      expect(planner.categoryFor(planner.actionsFor('approval', ['accept']))).not.toBe(planner.categoryFor(one));
    });

    it('turns a button into the answer the Gates screen would send', () => {
      expect(planner.answerFor('approval', ['accept', 'reject'], 'reject')).toEqual({ mode: 'verdict', value: 'reject' });
      expect(planner.answerFor('choice', ['a', 'b'], 'b')).toEqual({ mode: 'choice', value: 'b' });
      expect(planner.answerFor('question', [], 'defaults')).toEqual({ mode: 'defaults' });
    });

    it('turns nothing into an answer for a gate that spends, a button the gate lacks, or a host gate', () => {
      expect(planner.answerFor('budget_exhausted', ['25'], '25')).toBeUndefined();
      expect(planner.answerFor('deploy_acceptance', ['accept'], 'accept')).toBeUndefined();
      expect(planner.answerFor('approval', ['accept'], 'delete-everything')).toBeUndefined();
      expect(planner.answerFor('question', [], 'accept')).toBeUndefined();
      expect(planner.answerFor('grant_attempts', ['3'], '3')).toBeUndefined();
    });
  });
});
