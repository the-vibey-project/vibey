// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import type { VibeyAbandonReport, VibeyGate } from '../../src/interfaces/vibey-cli-interface';
import { ProjectDriver } from '../../src/project-driver';
import { GateAnswerPlanner } from '../../src/vibey-cli';

const driver = new ProjectDriver(new GateAnswerPlanner());
const gate = (over: Partial<VibeyGate>): VibeyGate => ({
  gate_id: 'g1',
  project_id: 'p1',
  project_name: 'greeter',
  job_id: null,
  kind: 'review',
  prompt: 'Is the page right?',
  options: ['accept', 'changes'],
  default_answer: null,
  timeout_at: null,
  answer_with: 'vibey answer g1 --verdict accept',
  ...over,
});
const interview = gate({ kind: 'design_interview', prompt: 'Who is it for?', options: [], answer_with: 'vibey answer g1 --defaults' });
const spending = gate({ kind: 'budget_exhausted', prompt: 'Out of budget.', options: [], answer_with: 'vibey answer g1 --raw {}' });
const report = (over: Partial<VibeyAbandonReport> = {}): VibeyAbandonReport => ({
  project_id: 'p1',
  name: 'greeter',
  from: 'BUILD',
  to: 'ABANDONED',
  dry_run: true,
  already_abandoned: false,
  written: false,
  cancelled_jobs: 2,
  withdrawn_gates: 1,
  ...over,
});

describe('ProjectDriver.parseNew', () => {
  it('takes the first word as the name and the rest as what to build', () => {
    expect(driver.parseNew('greeter a page that greets people', 'folder')).toEqual({ name: 'greeter', intake: 'a page that greets people' });
    expect(driver.parseNew('  greeter  ', 'folder')).toEqual({ name: 'greeter', intake: '' });
  });

  it('falls back to the folder name when nothing is said, and refuses a name the shell would take for a flag', () => {
    expect(driver.parseNew('', 'my-app')).toEqual({ name: 'my-app', intake: '' });
    expect(driver.parseNew('   ', 'my app (v2)')).toEqual({ name: 'my-app-v2', intake: '' });
    expect(driver.parseNew('', '---')).toBeUndefined();
    expect(driver.parseNew('--help do it', 'folder')).toBeUndefined();
  });
});

describe('ProjectDriver.newProjectRefusal', () => {
  it('explains that a folder holds one live project and what to do about it', () => {
    const said = driver.newProjectRefusal('Error: checkout /w is held by live project p1 (phase BUILD); two live projects never share a checkout');
    expect(said).toContain('already has a live project');
    expect(said).toMatch(/\/resume.*\/unwind/);
  });

  it('says nothing about any other error', () => {
    expect(driver.newProjectRefusal('Error: the database is not reachable')).toBeUndefined();
  });
});

describe('ProjectDriver.describeStarted', () => {
  it("tells a person what started, what happens next, and how to pause or end it", () => {
    const lines = driver.describeStarted({ project_id: 'p1', name: 'greeter', outcome: 'design job j1' }, 'started worker');
    expect(lines[0]).toBe('Started "greeter" (p1). design job j1');
    expect(lines[1]).toBe('started worker');
    expect(lines.join(' ')).toMatch(/\/next.*\/reply.*\/pause.*\/resume.*\/unwind/);
    expect(driver.describeStarted({ project_id: 'p1', name: 'greeter', outcome: '' }, '')[1]).toBe('Its worker is running.');
  });
});

describe('ProjectDriver.abandonConfirmation', () => {
  it('says exactly what would be cancelled and that it cannot be undone', () => {
    const confirmation = driver.abandonConfirmation(report());
    expect(confirmation).toMatchObject({ title: 'Unwind "greeter"?', nothingToDo: false });
    expect(confirmation.detail).toContain('2 queued or running jobs');
    expect(confirmation.detail).toContain('1 waiting question');
    expect(confirmation.detail).toContain('cannot be undone');
    expect(confirmation.detail).toContain('BUILD');
  });

  it('copes with no phase, and with a project that is already abandoned', () => {
    expect(driver.abandonConfirmation(report({ from: '', cancelled_jobs: 1, withdrawn_gates: 0 })).detail).toContain('its current phase');
    expect(driver.abandonConfirmation(report({ already_abandoned: true }))).toEqual({
      title: '"greeter" is already abandoned.',
      detail: 'Nothing was changed.',
      nothingToDo: true,
    });
  });
});

describe('ProjectDriver.oldestGate', () => {
  it("is the first gate, or the first of one project's", () => {
    const gates = [gate({ gate_id: 'a', project_id: 'p1' }), gate({ gate_id: 'b', project_id: 'p2' })];
    expect(driver.oldestGate(gates)?.gate_id).toBe('a');
    expect(driver.oldestGate(gates, 'p2')?.gate_id).toBe('b');
    expect(driver.oldestGate(gates, 'p9')).toBeUndefined();
    expect(driver.oldestGate([])).toBeUndefined();
  });
});

describe('ProjectDriver.describeGate', () => {
  it('shows the prompt in full, then numbered answers, marking the default', () => {
    const text = driver.describeGate(gate({ default_answer: 'accept' }));
    expect(text).toContain('greeter is waiting on you (review):');
    expect(text).toContain('Is the page right?');
    expect(text).toContain('1. accept (the default)');
    expect(text).toContain('2. changes');
    expect(text).toContain('3. Answer with JSON…');
    expect(text).toContain('/reply 1 to /reply 3');
  });

  it('names the project by id when it has no name, and lists the interview answers with their descriptions', () => {
    const text = driver.describeGate({ ...interview, project_name: undefined });
    expect(text).toContain('p1 is waiting on you (design_interview):');
    expect(text).toContain('1. Accept every default — vibey answer --defaults');
    expect(text).toContain('2. Answer questions… — QUESTION_ID=ANSWER pairs');
  });
});

describe('ProjectDriver.reply', () => {
  it('asks for an answer when none is given', () => {
    expect(driver.reply(gate({}), '  ')).toMatchObject({ kind: 'invalid', message: expect.stringContaining('Say which answer') });
  });

  it('turns a number into the answer it names, or says the list it runs over', () => {
    expect(driver.reply(gate({}), '1')).toEqual({ kind: 'answer', answer: { mode: 'verdict', value: 'accept' }, summary: 'accept' });
    expect(driver.reply(gate({}), '9')).toEqual({ kind: 'invalid', message: 'There is no answer 9; the list runs from 1 to 3.' });
    expect(driver.reply(gate({}), '0')).toMatchObject({ kind: 'invalid' });
  });

  it('asks for more when the numbered answer needs more input', () => {
    expect(driver.reply(interview, '2')).toMatchObject({ kind: 'more', needs: 'pairs', message: expect.stringContaining('QUESTION_ID=ANSWER') });
    expect(driver.reply(interview, '1')).toEqual({ kind: 'answer', answer: { mode: 'defaults' }, summary: 'Accept every default' });
    expect(driver.reply(spending, '1')).toMatchObject({ kind: 'more', needs: 'raw', message: expect.stringContaining('JSON object') });
  });

  it('matches words to the verdicts and choices a question takes, whatever the case', () => {
    expect(driver.reply(gate({}), 'Changes')).toEqual({ kind: 'answer', answer: { mode: 'verdict', value: 'changes' }, summary: 'changes' });
    const pick = gate({ kind: 'triage', options: ['now', 'later'], answer_with: 'vibey answer g1 --choice now' });
    expect(driver.reply(pick, 'later')).toMatchObject({ kind: 'answer', answer: { mode: 'choice', value: 'later' } });
    expect(driver.reply(gate({}), 'maybe')).toEqual({ kind: 'invalid', message: '"maybe" is not one of the answers: accept, changes.' });
  });

  it('takes defaults, or pairs, for an interview, and says what is wrong with a malformed pair', () => {
    expect(driver.reply(interview, 'defaults')).toMatchObject({ kind: 'answer', answer: { mode: 'defaults' } });
    expect(driver.reply(interview, 'Accept all')).toMatchObject({ kind: 'answer', answer: { mode: 'defaults' } });
    expect(driver.reply(interview, 'accept')).toMatchObject({ kind: 'answer', answer: { mode: 'defaults' } });
    expect(driver.reply(interview, 'q1=yes q2=no')).toEqual({
      kind: 'answer',
      answer: { mode: 'pairs', pairs: { q1: 'yes', q2: 'no' }, defaults: true },
      summary: 'Answered q1, q2; the rest take their defaults',
    });
    expect(driver.reply(interview, 'yes please')).toEqual({ kind: 'invalid', message: '"yes" is not QUESTION_ID=ANSWER.' });
  });

  it('takes JSON for the questions that want it, and refuses words and broken JSON', () => {
    expect(driver.reply(spending, '{"max_dollars": 25}')).toEqual({ kind: 'answer', answer: { mode: 'raw', json: '{"max_dollars": 25}' }, summary: 'Answered with JSON' });
    expect(driver.reply(spending, '{nope')).toMatchObject({ kind: 'invalid', message: expect.stringContaining('not JSON') });
    expect(driver.reply(spending, 'more money')).toEqual({ kind: 'invalid', message: 'This question takes a JSON object, for example: /reply {"max_dollars": 25}.' });
  });
});
