// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * A vibey command line sent to the repository's GitHub-hosted runners and followed to its end,
 * as `vibey -w` does on the host (ADR-0085): read every 10 seconds, for at most 60 minutes, and
 * then said plainly to be still running rather than reported as anything it is not.
 * Declared by `interfaces/workflow-runs-interface.ts`.
 */
import { HubClient } from './hub-client';
import type { HubClientInterface, WorkflowRun } from './interfaces/hub-client-interface';
import type {
  CommandLineParse,
  WorkflowFollowHooks,
  WorkflowOutcome,
  WorkflowRunView,
  WorkflowRunsInterface,
  WorkflowRunsTiming,
} from './interfaces/workflow-runs-interface';

export class WorkflowRuns implements WorkflowRunsInterface {
  static readonly EVERY_MS = 10_000;
  static readonly GIVE_UP_MS = 60 * 60_000;

  private readonly sleep: (ms: number) => Promise<void>;
  private readonly now: () => number;
  private readonly everyMs: number;
  private readonly giveUpMs: number;

  constructor(timing: WorkflowRunsTiming = {}) {
    this.sleep = timing.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    this.now = timing.now ?? Date.now;
    this.everyMs = timing.everyMs ?? WorkflowRuns.EVERY_MS;
    this.giveUpMs = timing.giveUpMs ?? WorkflowRuns.GIVE_UP_MS;
  }

  split(line: string): CommandLineParse {
    const words: string[] = [];
    let word = '';
    let started = false;
    let quoted = false;
    for (const char of line) {
      if (char === '"') {
        quoted = !quoted;
        started = true;
      } else if (!quoted && /\s/.test(char)) {
        if (started) words.push(word);
        word = '';
        started = false;
      } else {
        word += char;
        started = true;
      }
    }
    if (quoted) return { ok: false, reason: 'A double quote is not closed.' };
    if (started) words.push(word);
    let argv = words;
    if (argv[0] === 'vibey') argv = argv.slice(1);
    if (argv[0] === '-w' || argv[0] === '--workflows') argv = argv.slice(1);
    if (argv.length === 0) return { ok: false, reason: 'Type a vibey command, for example: status --json' };
    if (argv.length > HubClient.MAX_ARGV) {
      return { ok: false, reason: `A command line is at most ${HubClient.MAX_ARGV} words.` };
    }
    return { ok: true, argv };
  }

  async follow(
    client: Pick<HubClientInterface, 'startWorkflowRun' | 'workflowRun'>,
    argv: readonly string[],
    hooks: WorkflowFollowHooks = {},
  ): Promise<WorkflowOutcome> {
    const started = this.now();
    let run = await client.startWorkflowRun(argv);
    hooks.onUpdate?.(run);
    for (;;) {
      if (this.present(run).finished) return { kind: 'finished', run };
      if (this.now() - started >= this.giveUpMs) {
        return this.stillRunning(run, `Stopped waiting after ${Math.round(this.giveUpMs / 60_000)} min; the run carries on.`);
      }
      await this.sleep(this.everyMs);
      if (hooks.cancelled?.() === true) return this.stillRunning(run, 'Stopped watching; the run carries on.');
      run = await client.workflowRun(run.request_id);
      hooks.onUpdate?.(run);
    }
  }

  present(run: WorkflowRun): WorkflowRunView {
    switch (run.state) {
      case 'queued':
        return { label: 'Queued', role: 'neutral', finished: false };
      case 'running':
        return { label: 'Running', role: 'info', finished: false };
      case 'failed':
        return { label: 'Failed', role: 'danger', finished: true };
      case 'done':
        return run.exit_code === null
          ? { label: 'Done', role: 'success', finished: true }
          : { label: `Done · exit ${run.exit_code}`, role: run.exit_code === 0 ? 'success' : 'danger', finished: true };
    }
  }

  private stillRunning(run: WorkflowRun, why: string): WorkflowOutcome {
    const where = run.url === '' ? `on GitHub (request ${run.request_id})` : `at ${run.url}`;
    return { kind: 'still-running', run, message: `Still running ${where}. ${why}` };
  }
}
