// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import type { VibeyGate } from '../../src/core/interfaces/vibey-cli-interface';
import { GateAnswerPlanner, VibeyCli, VibeyCliError } from '../../src/core/vibey-cli';
import { FakeProcessRunner, fixture } from './helpers';

const cli = (runner: FakeProcessRunner): VibeyCli => new VibeyCli(runner, '/bin/vibey', { PATH: '/usr/bin' });
const noSuch = { code: 2, stderr: "Usage: vibey [OPTIONS] COMMAND\nError: No such command 'projects'." };

describe('VibeyCli', () => {
  it('reads projects, gates and status from the recorded JSON', async () => {
    const runner = new FakeProcessRunner()
      .on(['projects', '--json'], { stdout: fixture('vibey-projects.json') })
      .on(['gates', '--json'], { stdout: fixture('vibey-gates.json') })
      .on(['status', '--json'], { stdout: fixture('vibey-status.json') });
    const vibey = cli(runner);
    const projects = await vibey.projects();
    expect(projects.map((project) => [project.name, project.phase, project.open_gates])).toEqual([
      ['greeter', 'BUILD', 2],
      ['old-app', 'DONE', 0],
    ]);
    const gates = await vibey.gates();
    expect(gates[0]?.answer_with).toBe('vibey answer 3f2a9c1e-0b7d-4c55-9a51-2b1f0e8d7c6a --verdict accept');
    expect(gates[1]?.kind).toBe('budget_exhausted');
    await vibey.gates('7d1c');
    expect(runner.calls.at(-1)?.args).toEqual(['gates', '7d1c', '--json']);
    const status = await vibey.status();
    expect(status.queue_depth).toEqual({ ready: 2, leased: 1, succeeded: 7 });
    expect(status.circuits[0]?.engine_id).toBe('qwenloop');
    await vibey.status('7d1c');
    expect(runner.calls.at(-1)?.args).toEqual(['status', '--json', '7d1c']);
    expect(runner.calls[0]?.options.env).toEqual({ PATH: '/usr/bin' });
  });

  it('keeps only well-formed entries and fills what is missing', async () => {
    const runner = new FakeProcessRunner()
      .on(['projects'], { stdout: JSON.stringify([{ project_id: 'p', name: 'n', phase: 'BUILD' }, { name: 'no id' }, 3]) })
      .on(['gates'], { stdout: JSON.stringify({ gates: [{ gate_id: 'g', project_id: 'p', kind: 'k', prompt: 'q', options: ['a', 2], default_answer: null, timeout_at: null, job_id: null }, { gate_id: 'h', project_id: 'p', kind: 'k', prompt: 'q', options: 'x' }, {}] }) })
      .on(['status'], { stdout: JSON.stringify({ project_id: 'p', phase: 'build', queue_depth: { ready: 'two', leased: 1 }, circuits: [{ engine_id: 'x' }, { nope: 1 }], active_worktrees: ['a', 3] }) });
    const vibey = cli(runner);
    expect(await vibey.projects()).toHaveLength(1);
    const gates = await vibey.gates();
    expect(gates.map((gate) => gate.options)).toEqual([['a'], []]);
    const status = await vibey.status();
    expect(status).toMatchObject({ name: 'p', queue_depth: { leased: 1 }, circuits: [{ engine_id: 'x' }], active_worktrees: ['a'] });
    const sparse = cli(new FakeProcessRunner().on(['status'], { stdout: JSON.stringify({ project_id: 'p', phase: 'x', name: 'n', cycle: 1, max_cycles: 2, repo_path: '/r' }) }));
    expect(await sparse.status()).toEqual({ project_id: 'p', name: 'n', phase: 'x', cycle: 1, max_cycles: 2, repo_path: '/r', queue_depth: {}, circuits: [], active_worktrees: [] });
  });

  it('refuses output that is not the shape it should be', async () => {
    await expect(cli(new FakeProcessRunner().on(['projects'], { stdout: '{}' })).projects()).rejects.toThrow('did not print a list');
    await expect(cli(new FakeProcessRunner().on(['gates'], { stdout: '[]' })).gates()).rejects.toThrow('did not print {"gates": [...]}');
    await expect(cli(new FakeProcessRunner().on(['status'], { stdout: '[]' })).status()).rejects.toThrow('did not print a project');
    await expect(cli(new FakeProcessRunner().on(['status'], { stdout: 'Project: x' })).status()).rejects.toThrow('not JSON: Project: x');
    await expect(cli(new FakeProcessRunner().on(['budget'], { stdout: '{}' })).budgets()).rejects.toThrow('did not print a list');
  });

  it('says plainly which vibey lacks a command, and which release adds it; it never reads the database', async () => {
    const runner = new FakeProcessRunner().on(['projects'], noSuch).on(['--version'], { stdout: 'vibey 2.0.0\n' });
    const error = (await cli(runner)
      .projects()
      .catch((failure: unknown) => failure)) as VibeyCliError;
    expect(error).toBeInstanceOf(VibeyCliError);
    expect(error.kind).toBe('missing-command');
    expect(error.message).toBe(
      'vibey 2.0.0 (/bin/vibey) has no "vibey projects" command. It was added after vibey 2.1.0 and ships in vibey 3.0.0; point the vibey.cliPath setting at a newer vibey.',
    );
    const silent = new FakeProcessRunner().on(['loops'], noSuch).on(['--version'], { code: 1 });
    await expect(cli(silent).loops()).rejects.toThrow('this vibey (/bin/vibey) has no "vibey loops" command');
  });

  it('reports any other failure with what vibey said', async () => {
    await expect(cli(new FakeProcessRunner().on(['status'], { code: 3, stderr: 'VIBEY_PG_URL is not set.' })).status()).rejects.toThrow(
      'vibey status --json failed: VIBEY_PG_URL is not set.',
    );
    await expect(cli(new FakeProcessRunner().on(['status'], { code: null, error: 'vibey: ENOENT' })).status()).rejects.toThrow('vibey: ENOENT');
    await expect(cli(new FakeProcessRunner().on(['status'], { code: 5 })).status()).rejects.toThrow('exit 5');
    await expect(cli(new FakeProcessRunner().on(['answer'], { code: 2, stderr: 'No such command' })).answer('g', { mode: 'defaults' })).rejects.toThrow(
      'failed',
    );
  });

  it('answers, bumps, and reads the version', async () => {
    const runner = new FakeProcessRunner().on(['answer'], { stdout: 'answered g\n' }).on(['bump'], { stdout: '{"moved": []}' }).on(['--version'], { stdout: 'vibey 3.0.0\n' });
    const vibey = cli(runner);
    expect(await vibey.answer('g', { mode: 'verdict', value: 'accept' })).toBe('answered g');
    expect(await vibey.bump('j')).toBe('{"moved": []}');
    expect(runner.calls.at(-1)?.args).toEqual(['queue', 'bump', 'j', '--source', 'vscode']);
    await vibey.bump('j', 'p');
    expect(runner.calls.at(-1)?.args).toEqual(['queue', 'bump', 'j', '--source', 'vscode', '--project', 'p']);
    expect(await vibey.version()).toBe('vibey 3.0.0');
  });

  it('reads loops and budgets, and sets and clears a budget as vibey-vscode', async () => {
    const runner = new FakeProcessRunner()
      .on(['loops', '--json'], { stdout: fixture('vibey-loops.json') })
      .on(['budget', '--all', '--json'], { stdout: fixture('vibey-budget.json') })
      .on(['budget', 'set'], { stdout: 'max_cycle_dollars: 15.0 -> 20.0\n' })
      .on(['budget', 'clear'], { stdout: 'cleared\n' })
      .on(['cost'], { stdout: 'claudeloop  $1.50\n' });
    const vibey = cli(runner);
    expect((await vibey.loops()) as { default_loop: string }).toMatchObject({ default_loop: 'sovereignloop' });
    const budgets = await vibey.budgets();
    expect(budgets[0]).toMatchObject({ name: 'greeter', caps: { max_cycle_dollars: 15, max_cycle_turns: null }, spend: { dollars: 3.21, turns: 41 }, exhausted: false });
    expect(budgets[0]?.history).toHaveLength(1);
    expect(await vibey.setBudget('p', { dollars: 20, turns: 60 })).toBe('max_cycle_dollars: 15.0 -> 20.0');
    expect(runner.calls.at(-1)?.args).toEqual(['budget', 'set', 'p', '--max-cycle-dollars', '20', '--max-cycle-turns', '60', '--by', 'vibey-vscode']);
    await vibey.setBudget(undefined, {});
    expect(runner.calls.at(-1)?.args).toEqual(['budget', 'set', '--by', 'vibey-vscode']);
    expect(await vibey.clearBudget(undefined, 'dollars')).toBe('cleared');
    expect(runner.calls.at(-1)?.args).toEqual(['budget', 'clear', '--dollars', '--by', 'vibey-vscode']);
    await vibey.clearBudget('p', 'all');
    expect(runner.calls.at(-1)?.args).toEqual(['budget', 'clear', 'p', '--all', '--by', 'vibey-vscode']);
    expect(await vibey.cost()).toBe('claudeloop  $1.50');
    await vibey.cost('p');
    expect(runner.calls.at(-1)?.args).toEqual(['cost', 'p']);
  });

  it('reads a turn cap as a number, and a dollar cap that is not set as null', async () => {
    const runner = new FakeProcessRunner().on(['budget'], {
      stdout: JSON.stringify([{ project_id: 'p', name: 'n', caps: { max_cycle_dollars: null, max_cycle_turns: 60 }, spend: { dollars: 0, turns: 12 } }]),
    });
    expect((await cli(runner).budgets())[0]).toMatchObject({ caps: { max_cycle_dollars: null, max_cycle_turns: 60 }, spend: { turns: 12 } });
  });

  it('fills a budget entry that is missing parts', async () => {
    const runner = new FakeProcessRunner().on(['budget'], { stdout: JSON.stringify([{ project_id: 'p', caps: 'none', history: 'none' }, { name: 'no id' }]) });
    expect(await cli(runner).budgets()).toEqual([
      { project_id: 'p', name: 'p', caps: { max_cycle_dollars: null, max_cycle_turns: null }, spend: { dollars: 0, turns: 0 }, exhausted: false, history: [] },
    ]);
  });

  it('builds every form of vibey answer', () => {
    expect(VibeyCli.answerArgs('g', { mode: 'verdict', value: 'accept' })).toEqual(['answer', 'g', '--verdict', 'accept']);
    expect(VibeyCli.answerArgs('g', { mode: 'choice', value: 'deploy' })).toEqual(['answer', 'g', '--choice', 'deploy']);
    expect(VibeyCli.answerArgs('g', { mode: 'defaults' })).toEqual(['answer', 'g', '--defaults']);
    expect(VibeyCli.answerArgs('g', { mode: 'pairs', pairs: { q1: 'yes', q2: 'no' }, defaults: true })).toEqual(['answer', 'g', 'q1=yes', 'q2=no', '--defaults']);
    expect(VibeyCli.answerArgs('g', { mode: 'pairs', pairs: { q1: 'yes' }, defaults: false })).toEqual(['answer', 'g', 'q1=yes']);
    expect(VibeyCli.answerArgs('g', { mode: 'raw', json: '{"max_dollars": 25}' })).toEqual(['answer', 'g', '--raw', '{"max_dollars": 25}']);
  });
});

describe('GateAnswerPlanner', () => {
  const planner = new GateAnswerPlanner();
  const gate = (overrides: Partial<VibeyGate>): VibeyGate => ({
    gate_id: 'g',
    project_id: 'p',
    job_id: null,
    kind: 'question',
    prompt: 'q',
    options: [],
    default_answer: null,
    timeout_at: null,
    ...overrides,
  });

  it('reads the answer mode from the hint vibey gives, else from the kind', () => {
    expect(planner.mode(gate({ answer_with: 'vibey answer g --verdict accept' }))).toBe('verdict');
    expect(planner.mode(gate({ answer_with: 'vibey answer g --choice deploy' }))).toBe('choice');
    expect(planner.mode(gate({ answer_with: 'vibey answer g --defaults' }))).toBe('interview');
    expect(planner.mode(gate({ answer_with: 'vibey answer g q1=yes' }))).toBe('interview');
    expect(planner.mode(gate({ answer_with: "vibey answer g --raw '{}'" }))).toBe('raw');
    expect(planner.mode(gate({ kind: 'design.interview' }))).toBe('interview');
    expect(planner.mode(gate({ kind: 'deploy_acceptance' }))).toBe('verdict');
    expect(planner.mode(gate({ kind: 'deploy_failure_triage' }))).toBe('choice');
    expect(planner.mode(gate({ kind: 'budget_exhausted' }))).toBe('raw');
  });

  it('offers the options, marks the default, and always offers JSON', () => {
    const verdicts = planner.choices(gate({ answer_with: '--verdict x', options: ['accept', 'changes'], default_answer: 'accept' }));
    expect(verdicts.map((choice) => [choice.label, choice.description])).toEqual([
      ['accept', 'the default'],
      ['changes', undefined],
      ['Answer with JSON…', 'vibey answer --raw, for any other shape'],
    ]);
    expect(verdicts[0]?.answer).toEqual({ mode: 'verdict', value: 'accept' });
    expect(planner.choices(gate({ kind: 'review.collect' })).map((choice) => choice.label)).toEqual([...GateAnswerPlanner.VERDICTS, 'Answer with JSON…']);
    expect(planner.choices(gate({ kind: 'deploy.route' })).map((choice) => choice.label)).toEqual(['Answer with JSON…']);
    expect(planner.choices(gate({ kind: 'design.interview' })).map((choice) => choice.needs ?? choice.answer?.mode)).toEqual(['defaults', 'pairs', 'raw']);
    expect(planner.choices(gate({ kind: 'budget_exhausted' })).map((choice) => choice.needs)).toEqual(['raw']);
  });

  it('reads QUESTION_ID=ANSWER pairs and checks raw JSON', () => {
    expect(planner.parsePairs(' q1=yes  q2=a=b ')).toEqual({ q1: 'yes', q2: 'a=b' });
    expect(planner.parsePairs('  ')).toBe('Type at least one QUESTION_ID=ANSWER pair.');
    expect(planner.parsePairs('q1=yes =x')).toBe('"=x" is not QUESTION_ID=ANSWER.');
    expect(planner.parsePairs('word')).toBe('"word" is not QUESTION_ID=ANSWER.');
    expect(planner.checkRaw('{"max_dollars": 25}')).toBeUndefined();
    expect(planner.checkRaw('[1]')).toContain('takes a JSON object');
    expect(planner.checkRaw('{bad')).toContain('That is not JSON');
  });
});
