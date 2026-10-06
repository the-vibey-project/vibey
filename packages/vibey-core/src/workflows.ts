// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * A vibey command line for the repository's GitHub-hosted runners (ADR-0085), the same however
 * it travels: typed by a person, checked once, sent as `vibey --workflows …` or to a hub's
 * `POST /api/v1/workflows/runs`, and what came back read into one result. The exit codes are
 * `vibey -w`'s own (src/vibey/cli/workflows.py): the remote command's once it ran, else 2 for a
 * refused command line, 1 for a run that handed back no report, 124 for a wait that ran out.
 * Declared by `interfaces/workflows-interface.ts`.
 */
import { SlashArguments } from './commands';
import type { CompletedProcess } from './interfaces/process-runner-interface';
import type {
  TimerInterface,
  WorkflowsCommandLineInterface,
  WorkflowsRunResult,
  WorkflowsUpdate,
} from './interfaces/workflows-interface';

export class WorkflowsCommandLine implements WorkflowsCommandLineInterface {
  /** vibey's global option that sends the command line to the workflows; `-w` is its short form. */
  static readonly FLAG = '--workflows';
  static readonly SHORT_FLAG = '-w';
  /** How often `vibey -w` looks at the run, and so how often a hub is asked (`VIBEY_WORKFLOWS_POLL_SECONDS`). */
  static readonly POLL_MS = 10_000;
  /** How long `vibey -w` waits for the run's report (`VIBEY_WORKFLOWS_TIMEOUT_SECONDS`). */
  static readonly TIMEOUT_MS = 60 * 60_000;
  /** What the command line itself gets past that wait, so `vibey -w` says it timed out before it is stopped. */
  static readonly GRACE_MS = 60_000;
  /** The most words the hub takes in one command line (docs/reference/hub-api.json, `WorkflowRunBody`). */
  static readonly MAX_WORDS = 200;
  /** The exit code for a wait that ran out, as `timeout(1)` and `vibey -w` use it. */
  static readonly TIMED_OUT = 124;
  /** The line `vibey -w` writes to stderr once GitHub shows the run. */
  static readonly RAN_ON = /^vibey -w: ran on GitHub: (\S+)[ \t]*(?:\r?\n|$)/m;

  constructor(private readonly words = new SlashArguments()) {}

  parse(text: string): readonly string[] | string {
    const argv = [...this.words.words(text)];
    if (argv[0] === 'vibey') {
      argv.shift();
    }
    if (WorkflowsCommandLine.isFlag(argv[0])) {
      argv.shift();
    }
    return this.check(argv) ?? argv;
  }

  check(argv: readonly string[]): string | undefined {
    if (argv.length === 0) {
      return 'Say which vibey command to run on GitHub, like: status --json';
    }
    if (argv.length > WorkflowsCommandLine.MAX_WORDS) {
      return `A command line for the workflows takes at most ${WorkflowsCommandLine.MAX_WORDS} words; this one has ${argv.length}.`;
    }
    if (argv[0] === 'vibey') {
      return 'Leave out "vibey": give the command line that follows it, like: status --json';
    }
    if (WorkflowsCommandLine.isFlag(argv[0])) {
      return `Leave out ${argv[0]}: every command sent this way runs on the workflows.`;
    }
    return undefined;
  }

  /** A run's link, kept only when it is `https:`; anything else reads as no link. A client may
   *  hand it to the system's URL handler, where another scheme must never arrive. */
  static httpsUrl(url: string): string {
    return /^https:\/\/[^\s]+$/i.test(url) ? url : '';
  }

  fromProcess(completed: Pick<CompletedProcess, 'code' | 'stdout' | 'stderr'>): WorkflowsRunResult {
    const found = WorkflowsCommandLine.RAN_ON.exec(completed.stderr);
    return {
      exitCode: completed.code ?? 1,
      stdout: completed.stdout,
      stderr: found === null ? completed.stderr : completed.stderr.replace(found[0], ''),
      url: WorkflowsCommandLine.httpsUrl(found?.[1] ?? ''),
    };
  }

  fromHub(status: unknown): { readonly update: WorkflowsUpdate; readonly result?: WorkflowsRunResult } {
    const record = typeof status === 'object' && status !== null && !Array.isArray(status) ? (status as Record<string, unknown>) : {};
    const text = (key: string): string => (typeof record[key] === 'string' ? (record[key] as string) : '');
    const update: WorkflowsUpdate = { state: text('state') || 'unknown', url: WorkflowsCommandLine.httpsUrl(text('url')) };
    if (update.state === 'done' && typeof record.exit_code === 'number') {
      return { update, result: { exitCode: record.exit_code, stdout: text('stdout'), stderr: text('stderr'), url: update.url } };
    }
    if (update.state === 'done' || update.state === 'failed') {
      const why = text('detail') || (update.state === 'done' ? 'the run finished but handed back no exit code' : 'failed');
      return { update, result: { exitCode: 1, stdout: text('stdout'), stderr: `${text('stderr')}vibey -w: ${why}\n`, url: update.url } };
    }
    return { update };
  }

  timedOut(url: string, timeoutMs: number): WorkflowsRunResult {
    const where = url === '' ? '.' : `: ${url}`;
    return {
      exitCode: WorkflowsCommandLine.TIMED_OUT,
      stdout: '',
      stderr: `vibey -w: no report from GitHub within ${WorkflowsCommandLine.duration(timeoutMs)}; the run may still finish${where}\n`,
      url,
    };
  }

  report(argv: readonly string[], result: WorkflowsRunResult): readonly string[] {
    const lines = [
      `$ vibey -w ${WorkflowsCommandLine.shown(argv)}`,
      result.url === '' ? 'GitHub showed no run for it.' : `ran on GitHub: ${result.url}`,
      `exit code ${result.exitCode}`,
    ];
    for (const [name, text] of [['stdout', result.stdout], ['stderr', result.stderr]] as const) {
      if (text.trim() !== '') {
        lines.push(`--- ${name}`, ...text.replace(/\s+$/, '').split(/\r?\n/));
      }
    }
    return lines;
  }

  summary(argv: readonly string[], result: WorkflowsRunResult): string {
    const command = `vibey -w ${WorkflowsCommandLine.shown(argv)}`;
    const where = result.url === '' ? '' : ` (${result.url})`;
    if (result.exitCode === WorkflowsCommandLine.TIMED_OUT) {
      return `${command}: no report from GitHub in time; the run may still finish${where}.`;
    }
    const last = result.exitCode === 0 ? undefined : result.stderr.split(/\r?\n/).filter((line) => line.trim() !== '').at(-1);
    return `${command} exited ${result.exitCode}${where}${last === undefined ? '.' : `: ${last.trim()}`}`;
  }

  /** The command line as a person would type it again: a word with a space or a quote is quoted. */
  static shown(argv: readonly string[]): string {
    return argv.map((word) => (word === '' || /[\s"'\\]/.test(word) ? JSON.stringify(word) : word)).join(' ');
  }

  /** `90 seconds`, `1 minute`, `60 minutes`. */
  static duration(milliseconds: number): string {
    const [count, unit] = milliseconds % 60_000 === 0 ? [milliseconds / 60_000, 'minute'] : [Math.ceil(milliseconds / 1000), 'second'];
    return `${count} ${unit}${count === 1 ? '' : 's'}`;
  }

  private static isFlag(word: string | undefined): boolean {
    return word === WorkflowsCommandLine.FLAG || word === WorkflowsCommandLine.SHORT_FLAG;
  }
}

/**
 * The wait a poll loop needs, from what every JavaScript platform has: `setTimeout` (reached
 * through `globalThis`, because this package builds against no platform's types) and the wall
 * clock. A client with a clock of its own passes that instead.
 */
export class PortableTimer implements TimerInterface {
  sleep(milliseconds: number): Promise<void> {
    const host = globalThis as unknown as { setTimeout(callback: () => void, milliseconds: number): unknown };
    return new Promise((resolve) => {
      host.setTimeout(resolve, milliseconds);
    });
  }

  monotonic(): number {
    return Date.now();
  }
}
