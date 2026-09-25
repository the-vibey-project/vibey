#!/usr/bin/env node
// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * `vibey-vscode`: the extension's core without the editor, so the same task, batch, lanes and
 * budgets run from a terminal with the same behaviour and the same journals. Everything it
 * does lives in src/core; this file only reads arguments, prints, and exits.
 */
import * as os from 'node:os';
import * as path from 'node:path';
import { ArgumentParser, Presenter, UsageError } from '@vibey/core';
import { Doctor } from '@vibey/core';
import { JsonlJournal } from './core/jsonl';
import type { BudgetScope } from '@vibey/core';
import type { RawSettings } from '@vibey/core';
import type { TaskRunInterface } from '@vibey/core';
import { CoreServices } from './core/services';

const USAGE = `vibey-vscode: run tasks on a local model through vibey's loops, from a terminal.

  vibey-vscode ask "<task>" [options]      run one task on a copy of the repository
  vibey-vscode batch <folder> [options]    run every .md task in the folder, in name order;
                                           run it again to resume
  vibey-vscode status [--journal FILE]     the model, and a batch's progress
  vibey-vscode lanes [--json]              every lane on this computer, now
  vibey-vscode doctor                      check every piece, with paths and versions
  vibey-vscode budget list|add|edit|remove this machine's budgets
  vibey-vscode declare-paid --daily-dollars N | --monthly-dollars N | --no-cap --confirm-no-cap

Options:
  --repo DIR            a directory in the git repository (default: here)
  --base REF            what each task's branch starts from (default: HEAD)
  --in-place            edit the repository itself instead of a copy (no Apply/Discard)
  --loop sovereign|paid --effort auto|TRIVIAL|LOW|STANDARD|HIGH|MAX
  --engine auto|ENGINE|ENGINE/MODEL        --base-effort LEVEL
  --max-turns N  --context-window N  --model NAME  --ollama-url URL
  --storm-home DIR  --gptossloop PATH  --qwenloop PATH  --vibey PATH  --git PATH
  --journal FILE        the batch journal (default: under the storm home)
  --commit-type TYPE    Conventional Commits type for a task with no title (default: chore)
  --json                machine-readable output`;

const SWITCHES = new Set(['in-place', 'json', 'no-cap', 'confirm-no-cap', 'quiet']);

class HeadlessCli {
  private readonly presenter = new Presenter();
  private readonly running = new Set<TaskRunInterface>();
  private signals = 0;

  async main(argv: readonly string[]): Promise<number> {
    const args = new ArgumentParser(SWITCHES).parse(argv);
    const option = (name: string): string | undefined => {
      const value = args.options[name];
      return typeof value === 'string' ? value : undefined;
    };
    if (args.command === 'help') {
      process.stdout.write(`${USAGE}\n`);
      return 0;
    }
    if (args.command === 'version') {
      process.stdout.write(`${HeadlessCli.version()}\n`);
      return 0;
    }
    const raw: Partial<RawSettings> = {
      ...HeadlessCli.set('stormHome', option('storm-home')),
      ...HeadlessCli.set('gptossloopPath', option('gptossloop')),
      ...HeadlessCli.set('qwenloopPath', option('qwenloop')),
      ...HeadlessCli.set('cliPath', option('vibey')),
      ...HeadlessCli.set('gitPath', option('git')),
      ...HeadlessCli.set('model', option('model')),
      ...HeadlessCli.set('ollamaUrl', option('ollama-url')),
      ...HeadlessCli.set('baseRef', option('base')),
      ...HeadlessCli.set('effort', option('effort')),
      ...HeadlessCli.set('baseEffort', option('base-effort')),
      ...HeadlessCli.set('engine', option('engine')),
      ...(option('loop') === undefined ? {} : { loop: option('loop') === 'paid' ? 'paidloop' : option('loop') === 'sovereign' ? 'sovereignloop' : (option('loop') as string) }),
      ...(option('max-turns') === undefined ? {} : { maxTurns: HeadlessCli.number('max-turns', option('max-turns') as string) }),
      ...(option('context-window') === undefined ? {} : { contextWindow: HeadlessCli.number('context-window', option('context-window') as string) }),
      ...(args.options['in-place'] === true ? { runInPlace: true } : {}),
    };
    const services = new CoreServices({
      raw,
      environ: process.env,
      platform: process.platform,
      actor: `${os.userInfo().username} (vibey-vscode)`,
      workspaceRoots: () => [path.resolve(option('repo') ?? '.')],
    });
    const json = args.options.json === true;
    const repository = path.resolve(option('repo') ?? '.');
    this.trapSignals(services);
    switch (args.command) {
      case 'ask':
        return this.ask(services, args.positionals.join(' '), repository, json);
      case 'batch':
        return this.batch(services, args.positionals[0], repository, option('journal'), option('commit-type') ?? 'chore', json);
      case 'status':
        return this.status(services, option('journal'), json);
      case 'lanes':
        return this.lanes(services, json);
      case 'doctor': {
        const checks = await services.doctor().run();
        process.stdout.write(json ? `${JSON.stringify(checks, null, 2)}\n` : `${Doctor.render(checks)}\n`);
        return Doctor.failed(checks) ? 1 : 0;
      }
      case 'budget':
        return this.budget(services, args.positionals, args.options, json);
      case 'declare-paid':
        return this.declarePaid(services, args.options);
      default:
        throw new UsageError(`unknown command ${args.command}; try vibey-vscode help`);
    }
  }

  private async ask(services: CoreServices, task: string, repository: string, json: boolean): Promise<number> {
    if (!task.trim()) {
      throw new UsageError('ask needs a task: vibey-vscode ask "add a line to README.md"');
    }
    const { settings } = services;
    const title = services.naming.title(task);
    const run = await services.start({
      task,
      title,
      directory: repository,
      inPlace: settings.runInPlace,
      baseRef: settings.baseRef,
      loop: settings.loop,
      effort: settings.effort,
      baseEffort: settings.baseEffort,
      engine: settings.engine,
      contextWindow: settings.contextWindow,
      commitMessage: `chore(vibey): ${title}`,
      slugSource: title,
      origin: 'ask',
    });
    const record = await this.follow(run, json);
    process.stdout.write(json ? `${JSON.stringify(record)}\n` : `\n${this.presenter.record(record)}`);
    return this.presenter.exitCode(record.outcome);
  }

  private async batch(
    services: CoreServices,
    directory: string | undefined,
    repository: string,
    journal: string | undefined,
    commitType: string,
    json: boolean,
  ): Promise<number> {
    if (directory === undefined) {
      throw new UsageError('batch needs a folder of .md task files: vibey-vscode batch docs/tasks');
    }
    const { settings } = services;
    const summary = await services.batch().run(
      {
        directory: path.resolve(directory),
        repository,
        baseRef: settings.baseRef,
        journal: journal === undefined ? services.journalFor(directory, repository) : path.resolve(journal),
        commitType,
        contextWindow: settings.contextWindow,
        loop: settings.loop,
        effort: settings.effort,
        baseEffort: settings.baseEffort,
        engine: settings.engine,
      },
      {
        onPlanned: (tasks, skipped, pending) =>
          process.stdout.write(`${tasks.length} task(s): ${skipped.length} already finished, ${pending.length} to run.\n`),
        onNote: (text) => process.stdout.write(`[note] ${text}\n`),
        onTaskStarted: (task, run, index, total) => {
          process.stdout.write(`\n=== ${index}/${total} ${task.name}: ${task.title}\n`);
          void this.follow(run, json);
        },
        onTaskFinished: (task, record) =>
          process.stdout.write(json ? `${JSON.stringify({ file: task.name, ...record })}\n` : `\n${this.presenter.record(record)}`),
      },
    );
    process.stdout.write(`\n${this.presenter.batch(summary)}\n`);
    return this.presenter.batchExitCode(summary);
  }

  private async status(services: CoreServices, journal: string | undefined, json: boolean): Promise<number> {
    const status = await services.probe.status(services.settings.model, services.settings.contextWindow);
    const lines = [services.advice.summary(status), ...services.advice.advice(status, services.platform)];
    const progress: Record<string, unknown> = {};
    if (journal !== undefined) {
      const records = new JsonlJournal(path.resolve(journal)).readAll().records;
      const finished = records.filter((line) => line.type === 'task.finished');
      progress.finished = finished.map((line) => ({ file: line.file, outcome: line.outcome, branch: line.branch, head_sha: line.head_sha }));
      lines.push(`${finished.length} task(s) finished in ${journal}:`, ...finished.map((line) => `  ${String(line.file)}: ${String(line.outcome)} ${String(line.branch ?? '')}`));
    }
    process.stdout.write(json ? `${JSON.stringify({ ollama: status, ...progress }, null, 2)}\n` : `${lines.join('\n')}\n`);
    return status.reachable && status.modelPresent === true ? 0 : 1;
  }

  private async lanes(services: CoreServices, json: boolean): Promise<number> {
    const lanes = services.lanes(await services.catalogue()).refresh();
    if (json) {
      process.stdout.write(`${JSON.stringify(lanes, null, 2)}\n`);
      return 0;
    }
    const now = Date.now();
    for (const lane of lanes) {
      process.stdout.write(
        `${lane.state.padEnd(8)} ${lane.label}  turn ${lane.turn}${lane.tool === undefined ? '' : `, running ${lane.tool}`}, ${Math.round((now - lane.startedAt) / 60_000)} min, ${lane.inputTokens + lane.outputTokens} tokens${lane.outcome === undefined ? '' : ` (${lane.outcome})`}\n`,
      );
    }
    process.stdout.write(lanes.length === 0 ? 'No lanes in the last hour.\n' : '');
    return 0;
  }

  private budget(
    services: CoreServices,
    positionals: readonly string[],
    options: Readonly<Record<string, string | true>>,
    json: boolean,
  ): number {
    const [action, id] = positionals;
    const store = services.budgets;
    const caps = {
      ...(typeof options.dollars === 'string' ? { dollars: HeadlessCli.number('dollars', options.dollars, true) } : {}),
      ...(typeof options.turns === 'string' ? { turns: HeadlessCli.number('turns', options.turns) } : {}),
      ...(typeof options.minutes === 'string' ? { minutes: HeadlessCli.number('minutes', options.minutes) } : {}),
    };
    if (action === undefined || action === 'list') {
      const budgets = store.list();
      process.stdout.write(json ? `${JSON.stringify(budgets, null, 2)}\n` : `${budgets.map((budget) => `${budget.id}  ${budget.scope} ${budget.loop}${budget.engine_id === undefined ? '' : ` ${budget.engine_id}`}  ${JSON.stringify(budget.caps)}`).join('\n') || 'No budgets.'}\n`);
      return 0;
    }
    if (action === 'add') {
      const added = store.add({
        scope: (typeof options.scope === 'string' ? options.scope : 'day') as BudgetScope,
        loop: (typeof options.loop === 'string' ? options.loop : 'any') as 'any',
        ...(typeof options.engine === 'string' ? { engine_id: options.engine } : {}),
        caps,
      });
      process.stdout.write(`added ${added.id}\n`);
      return 0;
    }
    if (id === undefined) {
      throw new UsageError(`budget ${action} needs a budget id; see vibey-vscode budget list`);
    }
    if (action === 'edit') {
      store.edit(id, { caps: { ...store.list().find((budget) => budget.id === id)?.caps, ...caps } });
      process.stdout.write(`edited ${id}\n`);
      return 0;
    }
    if (action === 'remove') {
      store.remove(id);
      process.stdout.write(`removed ${id}\n`);
      return 0;
    }
    throw new UsageError(`budget takes list, add, edit or remove, not ${action}`);
  }

  private declarePaid(services: CoreServices, options: Readonly<Record<string, string | true>>): number {
    if (options['no-cap'] === true) {
      services.budgets.declarePaid({ noCap: true, confirmed: options['confirm-no-cap'] === true });
      process.stdout.write('paidloop declared with no dollar cap (recorded in the budget journal).\n');
      return 0;
    }
    const daily = options['daily-dollars'];
    const monthly = options['monthly-dollars'];
    if (typeof daily !== 'string' && typeof monthly !== 'string') {
      throw new UsageError('declare-paid needs --daily-dollars N or --monthly-dollars N (or --no-cap --confirm-no-cap)');
    }
    const scope = typeof daily === 'string' ? 'day' : 'month';
    const dollars = HeadlessCli.number('dollars', (typeof daily === 'string' ? daily : monthly) as string, true);
    services.budgets.declarePaid({ scope, dollars });
    process.stdout.write(`paidloop declared, with a ${scope === 'day' ? 'daily' : 'monthly'} cap of $${dollars.toFixed(2)}. Vendors bill their own accounts.\n`);
    return 0;
  }

  /** Stream a run's patches to the terminal, then its record. */
  private follow(run: TaskRunInterface, json: boolean): Promise<Awaited<TaskRunInterface['result']>> {
    this.running.add(run);
    const subscription = run.onPatch((patch) => {
      process.stdout.write(json ? `${JSON.stringify(patch)}\n` : this.presenter.patch(patch, run.items()));
    });
    return run.result.finally(() => {
      subscription.dispose();
      this.running.delete(run);
    });
  }

  /**
   * Ctrl-C (or SIGTERM) asks every running task to wind down gracefully and lets the journal
   * record it; a second one after the fair wait ends them by force. Nothing ends on its own.
   */
  private trapSignals(services: CoreServices): void {
    const handle = (): void => {
      this.signals += 1;
      if (this.signals === 1) {
        process.stderr.write('\nStopping: each task finishes its turn, then ends. Press Ctrl-C again to force it, once the fair wait has passed.\n');
        void services.queue.stopAll();
        return;
      }
      for (const run of this.running) {
        const refused = run.forceStop(services.settings.forceStopAfterMs);
        if (refused !== undefined) {
          process.stderr.write(`${refused}\n`);
        }
      }
    };
    process.on('SIGINT', handle);
    process.on('SIGTERM', handle);
  }

  private static set<K extends keyof RawSettings>(key: K, value: string | undefined): Partial<RawSettings> {
    return value === undefined ? {} : ({ [key]: value } as Partial<RawSettings>);
  }

  private static number(name: string, value: string, fractional = false): number {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0 || (!fractional && !Number.isInteger(parsed))) {
      throw new UsageError(`--${name} must be a positive ${fractional ? 'number' : 'whole number'}, not ${value}`);
    }
    return parsed;
  }

  private static version(): string {
    // Read at run time from the package the CLI ships in, so it can never disagree with it.
    const manifest = require(path.join(__dirname, '..', 'package.json')) as { version: string };
    return `vibey-vscode ${manifest.version}`;
  }
}

new HeadlessCli()
  .main(process.argv.slice(2))
  .then(
    (code) => {
      process.exitCode = code;
    },
    (error: unknown) => {
      process.stderr.write(`vibey-vscode: ${(error as Error).message}\n`);
      process.exitCode = Presenter.errorCode(error);
    },
  );
