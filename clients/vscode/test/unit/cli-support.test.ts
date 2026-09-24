// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { ArgumentParser, Presenter, UsageError } from '../../src/core/cli-support';
import type { BatchSummary } from '../../src/core/interfaces/batch-interface';
import type { RunItem } from '../../src/core/interfaces/run-events-interface';
import type { RunRecord } from '../../src/core/interfaces/run-interface';
import { VolatileStorageError } from '../../src/core/storage';

describe('ArgumentParser', () => {
  const parser = new ArgumentParser(new Set(['json', 'in-place']));

  it('reads a command, positionals, valued flags and switches', () => {
    expect(parser.parse(['batch', 'docs/tasks', '--base', 'origin/develop', '--journal=j.jsonl', '--json'])).toEqual({
      command: 'batch',
      positionals: ['docs/tasks'],
      options: { base: 'origin/develop', journal: 'j.jsonl', json: true },
    });
  });

  it('reads everything after -- as positionals', () => {
    expect(parser.parse(['ask', '--', '--not-a-flag', 'x']).positionals).toEqual(['--not-a-flag', 'x']);
  });

  it('asks for help with no command, and knows --version', () => {
    expect(parser.parse([]).command).toBe('help');
    expect(parser.parse(['--help']).command).toBe('help');
    expect(parser.parse(['--version']).command).toBe('version');
  });

  it('refuses a switch with a value and a flag without one', () => {
    expect(() => parser.parse(['ask', '--json=yes'])).toThrow('--json takes no value');
    expect(() => parser.parse(['ask', '--base'])).toThrow(UsageError);
  });
});

const record = (overrides: Partial<RunRecord> = {}): RunRecord => ({
  run_id: 'r1',
  title: 'Add a line',
  origin: 'ask',
  outcome: 'completed',
  exit_code: 0,
  signal: null,
  loop: 'sovereignloop',
  model: 'gpt-oss:20b',
  catalogue: 'vibey',
  context_window: 32768,
  attempts: [],
  diff_stat: '',
  changed_files: [],
  uncommitted: [],
  attachments: [],
  marker: true,
  turns: 3,
  input_tokens: 1234,
  output_tokens: 56,
  started_at: 'a',
  finished_at: 'b',
  duration_ms: 12345,
  run_directory: '/home/runs/r1',
  plan_path: '/home/runs/r1/plan.md',
  argv: [],
  ...overrides,
});

describe('Presenter', () => {
  const presenter = new Presenter();
  const items: RunItem[] = [
    { id: 1, kind: 'assistant', text: 'thinking' },
    { id: 2, kind: 'tool-call', name: 'read_file', detail: 'path=a' },
    { id: 3, kind: 'tool-call', name: 'shell', detail: '' },
    { id: 4, kind: 'tool-result', name: 'shell', ok: false, detail: 'exit 1' },
    { id: 5, kind: 'turn', turn: 1, detail: 'Turn 1 done' },
    { id: 6, kind: 'follow-up', text: 'shorter' },
    { id: 7, kind: 'notice', level: 'warn', text: 'careful' },
    { id: 8, kind: 'tool-result', name: 'read_file', ok: true, detail: 'read 3 lines' },
  ];

  it('prints each kind of item, starting a line after streamed text', () => {
    const lines = items.map((item) => presenter.patch({ op: 'add', item }, items));
    expect(lines).toEqual([
      'thinking',
      '\n[tool] read_file path=a\n',
      '[tool] shell\n',
      '[error] exit 1\n',
      '[turn] Turn 1 done\n',
      '[you] shorter\n',
      '[warn] careful\n',
      '[ok] read 3 lines\n',
    ]);
    expect(presenter.patch({ op: 'append', id: 1, text: ' more' }, items)).toBe(' more');
  });

  it('prints a record with only what it has', () => {
    const plain = presenter.record(record());
    expect(plain).toContain('outcome: completed');
    expect(plain).toContain('engine: none on gpt-oss:20b (sovereignloop)');
    expect(plain).not.toContain('branch:');
    const full = presenter.record(
      record({
        engine: 'qwenloop',
        effort: 'LOW',
        model: null,
        branch: 'vibey/x-1',
        base_sha: 'a'.repeat(40),
        cwd: '/home/w',
        diff_stat: ' README.md | 1 +',
        uncommitted: ['notes.md'],
        verdict: 'complete: yes',
        failure: { reason: 'turn_limit', explanation: 'used all turns' },
        budget: { id: 'b', cap: 'dollars', limit: 1, spent: 1, message: 'budget used up' },
        commit_error: 'hook said no',
        error: 'boom',
      }),
    );
    expect(full).toContain('engine: qwenloop on its own model (sovereignloop, effort LOW)');
    expect(full).toContain(`branch: vibey/x-1 (${'a'.repeat(12)}..?)`);
    expect(full).toContain('worktree: /home/w');
    expect(full).toContain('   README.md | 1 +');
    expect(full).toContain('not committed: notes.md');
    expect(full).toContain('  complete: yes');
    for (const text of ['failure: used all turns', 'budget: budget used up', 'commit refused: hook said no', 'error: boom']) {
      expect(full).toContain(text);
    }
  });

  const summary = (overrides: Partial<BatchSummary> = {}): BatchSummary => ({
    journal: '/j.jsonl',
    batchId: 'b1',
    baseSha: 'c'.repeat(40),
    total: 3,
    skipped: 1,
    ran: 2,
    outcomes: { completed: 1, failed: 1 },
    remaining: 0,
    ...overrides,
  });

  it('prints a batch summary and its exit code', () => {
    expect(presenter.batch(summary())).toContain('(1 completed, 1 failed)');
    expect(presenter.batch(summary())).toContain('done.');
    expect(presenter.batch(summary({ outcomes: {}, halted: 'the run was stopped', remaining: 2 }))).toContain('halted: the run was stopped');
    expect(presenter.batchExitCode(summary())).toBe(0);
    expect(presenter.batchExitCode(summary({ halted: 'the run was stopped' }))).toBe(75);
    expect(presenter.batchExitCode(summary({ halted: 'a budget is used up: x' }))).toBe(3);
    expect(presenter.batchExitCode(summary({ halted: 'an infrastructure error' }))).toBe(1);
  });

  it('maps every outcome to an exit code', () => {
    expect(
      (['completed', 'completed-no-change', 'completed-commit-refused', 'failed', 'wound-down', 'budget-exhausted', 'error'] as const).map((outcome) =>
        presenter.exitCode(outcome),
      ),
    ).toEqual([0, 0, 4, 1, 75, 3, 1]);
  });

  it('gives a volatile path, a usage error and anything else their exit codes', () => {
    expect(Presenter.errorCode(new VolatileStorageError([]))).toBe(78);
    expect(Presenter.errorCode(new UsageError('x'))).toBe(2);
    expect(Presenter.errorCode(new Error('x'))).toBe(1);
  });
});
