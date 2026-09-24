// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The headless CLI's pure parts: reading its arguments, and turning a run's patches, its
 * record and a batch's summary into terminal text and an exit code. `src/cli.ts` only wires
 * these to the process, so what a terminal sees is tested here. Declared by
 * `interfaces/cli-interface.ts`.
 */
import type { BatchSummary } from './interfaces/batch-interface';
import type { ArgumentParserInterface, ParsedArguments, PresenterInterface } from './interfaces/cli-interface';
import type { RunItem, RunPatch } from './interfaces/run-events-interface';
import type { RunOutcome, RunRecord } from './interfaces/run-interface';
import { VolatileStorageError } from './storage';

export class UsageError extends Error {
  static readonly EXIT_CODE = 2;

  constructor(message: string) {
    super(message);
    this.name = 'UsageError';
  }
}

export class ArgumentParser implements ArgumentParserInterface {
  constructor(
    /** Flags that take no value: `--json`, `--in-place`. */
    private readonly switches: ReadonlySet<string>,
  ) {}

  parse(argv: readonly string[]): ParsedArguments {
    const [command, ...rest] = argv;
    if (command === undefined || command.startsWith('-')) {
      return { command: command === '--version' ? 'version' : 'help', positionals: [], options: {} };
    }
    const positionals: string[] = [];
    const options: Record<string, string | true> = {};
    let onlyPositionals = false;
    for (let index = 0; index < rest.length; index += 1) {
      const token = rest[index] as string;
      if (onlyPositionals || !token.startsWith('--')) {
        positionals.push(token);
        continue;
      }
      if (token === '--') {
        onlyPositionals = true;
        continue;
      }
      const equals = token.indexOf('=');
      const name = token.slice(2, equals < 0 ? undefined : equals);
      if (this.switches.has(name)) {
        if (equals >= 0) {
          throw new UsageError(`--${name} takes no value`);
        }
        options[name] = true;
        continue;
      }
      if (equals >= 0) {
        options[name] = token.slice(equals + 1);
        continue;
      }
      const value = rest[index + 1];
      if (value === undefined) {
        throw new UsageError(`--${name} needs a value`);
      }
      options[name] = value;
      index += 1;
    }
    return { command, positionals, options };
  }
}

export class Presenter implements PresenterInterface {
  patch(patch: RunPatch, items: readonly RunItem[]): string {
    if (patch.op === 'append') {
      return patch.text;
    }
    const item = patch.item;
    const previous = items[items.indexOf(item) - 1];
    const lead = previous?.kind === 'assistant' ? '\n' : '';
    switch (item.kind) {
      case 'assistant':
        return item.text;
      case 'tool-call':
        return `${lead}[tool] ${item.name}${item.detail ? ` ${item.detail}` : ''}\n`;
      case 'tool-result':
        return `${lead}[${item.ok ? 'ok' : 'error'}] ${item.detail}\n`;
      case 'turn':
        return `${lead}[turn] ${item.detail}\n`;
      case 'follow-up':
        return `${lead}[you] ${item.text}\n`;
      case 'notice':
        return `${lead}[${item.level}] ${item.text}\n`;
    }
  }

  record(record: RunRecord): string {
    const lines = [
      `outcome: ${record.outcome}`,
      `title: ${record.title}`,
      `engine: ${record.engine ?? 'none'} on ${record.model ?? 'its own model'} (${record.loop}${record.effort === undefined ? '' : `, effort ${record.effort}`})`,
      `turns: ${record.turns} (${record.input_tokens.toLocaleString('en-US')} tokens in, ${record.output_tokens.toLocaleString('en-US')} out), ${(record.duration_ms / 1000).toFixed(1)} s`,
    ];
    if (record.branch !== undefined) {
      lines.push(`branch: ${record.branch} (${record.base_sha?.slice(0, 12)}..${record.head_sha?.slice(0, 12) ?? '?'})`);
    }
    if (record.cwd !== undefined) {
      lines.push(`worktree: ${record.cwd}`);
    }
    if (record.diff_stat) {
      lines.push('changes:', ...record.diff_stat.split('\n').map((line) => `  ${line}`));
    }
    if (record.uncommitted.length > 0) {
      lines.push(`not committed: ${record.uncommitted.join(', ')}`);
    }
    if (record.out_of_scope !== undefined) {
      lines.push(`out of scope (${record.paths?.join(', ') ?? ''}), left for a person to review: ${record.out_of_scope.join(', ')}`);
    }
    if (record.verdict !== undefined) {
      lines.push('verdict:', ...record.verdict.split('\n').map((line) => `  ${line}`));
    }
    for (const [label, value] of [
      ['failure', record.failure?.explanation],
      ['budget', record.budget?.message],
      ['commit refused', record.commit_error],
      ['error', record.error],
    ] as const) {
      if (value !== undefined) {
        lines.push(`${label}: ${value}`);
      }
    }
    lines.push(`journal: ${record.run_directory}`);
    return `${lines.join('\n')}\n`;
  }

  batch(summary: BatchSummary): string {
    const outcomes = Object.entries(summary.outcomes)
      .map(([outcome, count]) => `${count} ${outcome}`)
      .join(', ');
    return [
      `batch ${summary.batchId} from ${summary.baseSha.slice(0, 12)}: ${summary.total} task(s), ${summary.skipped} already finished, ${summary.ran} run now${outcomes ? ` (${outcomes})` : ''}`,
      summary.halted === undefined ? 'done.' : `halted: ${summary.halted}`,
      `${summary.remaining} task(s) remain; run the same command again to resume.`,
      `journal: ${summary.journal}`,
    ].join('\n');
  }

  exitCode(outcome: RunOutcome): number {
    const codes: Record<RunOutcome, number> = {
      completed: 0,
      'completed-no-change': 0,
      'completed-commit-refused': 4,
      'completed-out-of-scope': 4,
      failed: 1,
      'wound-down': 75,
      'budget-exhausted': 3,
      error: 1,
    };
    return codes[outcome];
  }

  /**
   * 0 only when every task this run started ended completed: a batch that ran to its end
   * with a failed task says so (1), and so does one a person must look at (4): a commit a
   * hook refused, or changes left outside a task's paths.
   */
  batchExitCode(summary: BatchSummary): number {
    if (summary.halted !== undefined) {
      if (summary.halted.startsWith('the run was stopped')) {
        return 75;
      }
      return summary.halted.startsWith('a budget') ? 3 : 1;
    }
    if ((summary.outcomes.failed ?? 0) > 0) {
      return 1;
    }
    const review = (summary.outcomes['completed-commit-refused'] ?? 0) + (summary.outcomes['completed-out-of-scope'] ?? 0);
    return review > 0 ? 4 : 0;
  }

  /** The exit code for an error that ended the command before or outside a run. */
  static errorCode(error: unknown): number {
    if (error instanceof VolatileStorageError) {
      return VolatileStorageError.EXIT_CODE;
    }
    return error instanceof UsageError ? UsageError.EXIT_CODE : 1;
  }
}
