// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * One task, from request to recorded result.
 *
 * 1. Isolation. By default the task gets a git worktree of its own under the durable storm
 *    home, on a branch `vibey/<slug>-<id>`, so the model never edits the person's checkout.
 *    `vibey.runInPlace` runs in the open folder instead, with a warning.
 * 2. Its own qwenloop config (QWENLOOP_CONFIG): the run's context window and turn limit,
 *    over the person's own qwenloop config, in the run's durable directory.
 * 3. An allow-listed environment: no `VIBEY_*`, no `PG*`, nothing shaped like a credential.
 * 4. The model slot: one run at a time on this computer (8.c).
 * 5. Its events.jsonl, read by byte offset as it grows.
 * 6. Its end: completed work is committed on the task's branch with the repository's own
 *    hooks (a refusal is recorded, never bypassed), and the outcome says which of
 *    completed, completed with no change, commit refused, failed, stopped or error it was.
 *
 * Nothing here stops a run for being slow: a local turn can take two minutes, so a long
 * silence produces a hint, and only a person's Stop or Force stop ends a run. Declared by
 * `interfaces/run-interface.ts`.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { ChildEnvironment, EnvironmentAllowList } from './environment';
import type { ChangedFile } from './interfaces/git-interface';
import type { ChildHandle, ProcessExit } from './interfaces/process-runner-interface';
import type { Invocation } from './interfaces/qwenloop-interface';
import type { RunItem, RunPatch } from './interfaces/run-events-interface';
import type {
  QwenloopRunInterface,
  RunHistoryEntry,
  RunHistoryInterface,
  RunOutcome,
  RunRecord,
  RunRequest,
  RunServices,
  RunStatus,
  RunWorkspace,
} from './interfaces/run-interface';
import type { Disposable } from './interfaces/support-interface';
import { JsonlJournal } from './jsonl';
import { QwenloopCommand } from './qwenloop';
import { RunTranscript } from './run-events';
import { Emitter } from './support';

/** What a run knows about itself so far; `record()` turns it into the journal line. */
interface RunFacts {
  argv: readonly string[];
  eventsPath?: string;
  exit?: ProcessExit;
  headSha?: string;
  diffStat: string;
  changed: readonly ChangedFile[];
  uncommitted: readonly string[];
  commitError?: string;
  error?: string;
}

export class QwenloopRun implements QwenloopRunInterface {
  /** The last characters of qwenloop's stderr kept, for the error a failed start reports. */
  static readonly STDERR_TAIL = 4000;

  readonly runId: string;
  readonly result: Promise<RunRecord>;

  private state: RunStatus = 'queued';
  private space: RunWorkspace | undefined;
  private readonly transcript = new RunTranscript();
  private readonly patches = new Emitter<RunPatch>();
  private readonly statuses = new Emitter<RunStatus>();
  private readonly abort = new AbortController();
  private child: ChildHandle | undefined;
  private environment: Record<string, string> = {};
  private started = false;
  private forced = false;
  private stopRequested = false;
  private offset = 0;
  private lastActivity = 0;
  private hinted = false;
  private stderrTail = '';
  private settle: (record: RunRecord) => void = () => undefined;
  private readonly runDirectory: string;
  private readonly startedAt: Date;
  private readonly startedMono: number;
  private readonly facts: RunFacts = { argv: [], diffStat: '', changed: [], uncommitted: [] };

  constructor(
    readonly request: RunRequest,
    private readonly services: RunServices,
  ) {
    this.runId = services.ids.uuid();
    this.runDirectory = path.join(services.settings.stateDir, 'runs', this.runId);
    this.startedAt = services.clock.now();
    this.startedMono = services.clock.monotonic();
    this.result = new Promise((resolve) => {
      this.settle = resolve;
    });
  }

  get status(): RunStatus {
    return this.state;
  }

  get workspace(): RunWorkspace | undefined {
    return this.space;
  }

  items(): readonly RunItem[] {
    return this.transcript.items();
  }

  onPatch(listener: (patch: RunPatch) => void): Disposable {
    return this.patches.on(listener);
  }

  onStatus(listener: (status: RunStatus) => void): Disposable {
    return this.statuses.on(listener);
  }

  async execute(): Promise<RunRecord> {
    if (this.started) {
      return this.result;
    }
    this.started = true;
    const [record, durable] = await this.run();
    if (durable) {
      try {
        fs.mkdirSync(this.runDirectory, { recursive: true });
        fs.writeFileSync(this.path('result.json'), `${JSON.stringify(record, null, 2)}\n`);
        this.services.history.finished(record);
      } catch (error) {
        this.say('error', `The result could not be recorded: ${(error as Error).message}`);
      }
    }
    this.move('finished');
    this.settle(record);
    return record;
  }

  async followUp(text: string): Promise<string | undefined> {
    const message = text.trim();
    if (!message) {
      return 'There is nothing to send.';
    }
    if (this.state !== 'running' || this.space === undefined) {
      return 'This task is not running, so there is nothing to send a follow-up to.';
    }
    const error = await this.control(this.services.qwenloop.prompt(this.runId, message, this.space.cwd));
    if (error !== undefined) {
      return `qwenloop could not take the follow-up: ${error}`;
    }
    this.say('info', 'Follow-up sent. The model reads it at the start of its next turn.');
    return undefined;
  }

  async stop(): Promise<string | undefined> {
    if (this.state === 'finishing' || this.state === 'finished') {
      return 'This task has already finished.';
    }
    this.stopRequested = true;
    if (this.child === undefined || this.space === undefined) {
      this.abort.abort();
      return undefined;
    }
    this.move('stopping');
    const error = await this.control(this.services.qwenloop.stop(this.runId, this.space.cwd));
    if (error !== undefined) {
      return `qwenloop could not be asked to stop: ${error}`;
    }
    this.say(
      'info',
      'Asked to stop. The model finishes the turn it is on, then the task ends; a slow turn can take a couple of minutes. Force stop ends it at once.',
    );
    return undefined;
  }

  forceStop(): void {
    this.stopRequested = true;
    if (this.child === undefined) {
      this.abort.abort();
      return;
    }
    this.forced = true;
    this.child.kill('SIGTERM');
  }

  /** The whole run; the flag says whether its directory passed the durability gate. */
  private async run(): Promise<[RunRecord, boolean]> {
    const { settings, gate } = this.services;
    if (this.abort.signal.aborted) {
      return [this.record('wound-down', 'Stopped before it started.'), false];
    }
    this.move('preparing');
    try {
      gate.enforce({ 'run records': this.runDirectory });
    } catch (error) {
      return [this.record('error', (error as Error).message), false];
    }
    try {
      this.space = await this.prepare();
      const invocation = this.writeInputs(this.space);
      this.move('waiting');
      let waited = false;
      const slot = await this.services.lock.acquire(
        `${this.request.title} (run ${this.runId})`,
        (holder) => {
          if (!waited) {
            waited = true;
            this.say(
              'info',
              holder === undefined
                ? `Waiting for the model: another run is using ${settings.model}.`
                : `Waiting for the model: ${holder.purpose} (process ${holder.pid}) is using ${settings.model}.`,
            );
          }
        },
        settings.pollMs,
        this.abort.signal,
      );
      try {
        if (this.abort.signal.aborted) {
          return [this.record('wound-down', 'Stopped before it started.'), true];
        }
        this.facts.exit = await this.watch(invocation, this.space.cwd);
      } finally {
        slot.dispose();
      }
      return [await this.finish(this.facts.exit, this.space), true];
    } catch (error) {
      const outcome: RunOutcome = this.stopRequested && this.child === undefined ? 'wound-down' : 'error';
      return [this.record(outcome, (error as Error).message), true];
    }
  }

  private async prepare(): Promise<RunWorkspace> {
    const { git, naming, settings, gate } = this.services;
    const repository = await git.toplevel(this.request.directory);
    if (this.request.inPlace) {
      const baseSha = await git.resolveCommit(repository, 'HEAD');
      const branch = await git.currentBranch(repository);
      this.say(
        'warn',
        'Running in place: the model edits your open folder directly, on your current branch. This run has no Apply or Discard; review and undo it with git.',
      );
      return { mode: 'in-place', repository, cwd: repository, ...(branch === undefined ? {} : { branch }), baseRef: 'HEAD', baseSha };
    }
    const baseRef = this.request.baseRef || 'HEAD';
    const baseSha = this.request.baseSha ?? (await git.resolveCommit(repository, baseRef));
    const slug = naming.slug(this.request.slugSource);
    const short = naming.shortId(this.runId);
    const branch = naming.branch(slug, short);
    const worktree = path.join(settings.stormHome.path, naming.worktreeName(repository, slug, short));
    gate.enforce({ 'task worktree': worktree });
    await git.addWorktree(repository, worktree, branch, baseSha);
    this.say('info', `Working on a copy: ${worktree}, branch ${branch}, from ${baseRef} at ${baseSha.slice(0, 12)}.`);
    return { mode: 'worktree', repository, cwd: worktree, branch, baseRef, baseSha };
  }

  /** The plan, the run's qwenloop config, and the child's environment. */
  private writeInputs(space: RunWorkspace): Invocation {
    const { settings } = this.services;
    const planPath = this.path('plan.md');
    const configPath = this.path('qwenloop.toml');
    fs.mkdirSync(this.runDirectory, { recursive: true });
    fs.writeFileSync(planPath, this.request.task);
    const user = this.services.userConfig();
    fs.writeFileSync(
      configPath,
      this.services.runConfig.compose(user?.text, {
        contextWindow: this.request.contextWindow,
        ...(this.request.maxTurns === undefined ? {} : { maxTurns: this.request.maxTurns }),
      }),
    );
    this.environment = new ChildEnvironment(
      EnvironmentAllowList.MODEL_BASICS.extended(settings.environmentAllow, 'the vibey.environment.allow setting'),
      { QWENLOOP_CONFIG: configPath, OLLAMA_HOST: settings.ollama.root },
    ).build(this.services.environ);
    const invocation = this.services.qwenloop.run({
      planPath,
      runId: this.runId,
      cwd: space.cwd,
      baseUrl: settings.ollama.v1,
      model: settings.model,
      effort: this.request.effort,
      desktopNotifications: settings.desktopNotifications,
    });
    this.facts.argv = [invocation.command, ...invocation.args];
    this.facts.eventsPath = path.join(space.cwd, '.qwenloop', 'runs', this.runId, 'events.jsonl');
    this.say(
      'info',
      `qwenloop plans for a ${this.request.contextWindow.toLocaleString('en-US')}-token window` +
        (this.request.maxTurns === undefined ? '' : ` and at most ${this.request.maxTurns} turns`) +
        (user === undefined ? '.' : `, over your own config at ${user.path}.`),
    );
    return invocation;
  }

  private watch(invocation: Invocation, cwd: string): Promise<ProcessExit> {
    const { clock, settings, processes } = this.services;
    const events = this.facts.eventsPath as string;
    const child = processes.spawn(invocation.command, invocation.args, { cwd, env: this.environment });
    this.child = child;
    this.move(this.stopRequested ? 'stopping' : 'running');
    child.onStderr((text) => {
      this.stderrTail = `${this.stderrTail}${text}`.slice(-QwenloopRun.STDERR_TAIL);
    });
    this.lastActivity = clock.monotonic();
    const timer = clock.every(settings.pollMs, () => this.poll(events));
    return child.exited.then((exit) => {
      timer.dispose();
      this.poll(events);
      return exit;
    });
  }

  private poll(events: string): void {
    const { clock, settings, tail } = this.services;
    const chunk = tail.read(events, this.offset);
    if (chunk.restarted) {
      this.say('warn', 'The event log was replaced, so it is being read again from the start.');
    }
    if (chunk.nextOffset !== this.offset) {
      this.lastActivity = clock.monotonic();
      this.hinted = false;
    }
    this.offset = chunk.nextOffset;
    for (const event of chunk.records) {
      for (const patch of this.transcript.accept(event)) {
        this.patches.fire(patch);
      }
    }
    if (chunk.malformed > 0) {
      this.say('warn', `${chunk.malformed} line(s) of the event log were not JSON and were skipped.`);
    }
    const quiet = clock.monotonic() - this.lastActivity;
    if (!this.hinted && (this.state === 'running' || this.state === 'stopping') && quiet >= settings.stuckHintMs) {
      this.hinted = true;
      this.say(
        'info',
        `No news from the model for ${Math.round(quiet / 60_000)} minutes. That can be normal: on a 24 GB Mac one turn of gpt-oss:20b took 16.5 s typically and nearly two minutes at the slow end. Nothing has been stopped; Stop is there if you want it.`,
      );
    }
  }

  private async finish(exit: ProcessExit, space: RunWorkspace): Promise<RunRecord> {
    this.move('finishing');
    const { git } = this.services;
    let outcome: RunOutcome;
    let error: string | undefined;
    if (exit.error !== undefined) {
      outcome = 'error';
      error = `qwenloop could not be started: ${exit.error}`;
    } else if (this.forced || exit.code === QwenloopCommand.EXIT_WOUND_DOWN) {
      outcome = 'wound-down';
    } else if (exit.code === 0) {
      outcome = 'completed';
    } else if (this.transcript.failure !== undefined) {
      outcome = 'failed';
    } else {
      outcome = 'error';
      error = this.stderrTail.trim() || `qwenloop ended with ${exit.code === null ? `signal ${exit.signal}` : `exit code ${exit.code}`}`;
    }
    if (outcome === 'completed' && space.mode === 'worktree') {
      const commit = await git.commitAll(space.cwd, this.request.commitMessage);
      if (commit.error !== undefined) {
        outcome = 'completed-commit-refused';
        this.facts.commitError = commit.error;
      }
    }
    this.facts.headSha = await git.head(space.cwd);
    this.facts.uncommitted = await git.uncommitted(space.cwd);
    this.facts.changed = await git.changedFiles(space.repository, space.baseSha, this.facts.headSha);
    this.facts.diffStat = await git.diffStat(space.repository, space.baseSha, this.facts.headSha);
    if (outcome === 'completed' && this.facts.changed.length === 0 && this.facts.uncommitted.length === 0) {
      outcome = 'completed-no-change';
    }
    return this.record(outcome, error);
  }

  private record(outcome: RunOutcome, error?: string): RunRecord {
    const { settings, clock } = this.services;
    const verdict = this.transcript.verdict();
    const space = this.space;
    const exit = this.facts.exit;
    const failure = this.transcript.failure;
    if (error !== undefined) {
      this.say(outcome === 'wound-down' ? 'info' : 'error', error);
    }
    return {
      run_id: this.runId,
      title: this.request.title,
      origin: this.request.origin,
      ...(this.request.source === undefined ? {} : { source: this.request.source }),
      outcome,
      exit_code: exit?.code ?? null,
      signal: exit?.signal ?? null,
      model: settings.model,
      context_window: this.request.contextWindow,
      ...(this.request.maxTurns === undefined ? {} : { max_turns: this.request.maxTurns }),
      ...(space === undefined
        ? {}
        : {
            mode: space.mode,
            repository: space.repository,
            cwd: space.cwd,
            ...(space.branch === undefined ? {} : { branch: space.branch }),
            base_ref: space.baseRef,
            base_sha: space.baseSha,
          }),
      ...(this.facts.headSha === undefined ? {} : { head_sha: this.facts.headSha }),
      diff_stat: this.facts.diffStat,
      changed_files: this.facts.changed,
      uncommitted: this.facts.uncommitted,
      ...(verdict.text === undefined ? {} : { verdict: verdict.text }),
      marker: verdict.marker,
      ...(failure === undefined ? {} : { failure }),
      ...(error === undefined ? {} : { error }),
      ...(this.facts.commitError === undefined ? {} : { commit_error: this.facts.commitError }),
      turns: this.transcript.turns,
      input_tokens: this.transcript.inputTokens,
      output_tokens: this.transcript.outputTokens,
      started_at: this.startedAt.toISOString(),
      finished_at: clock.now().toISOString(),
      duration_ms: Math.round(clock.monotonic() - this.startedMono),
      run_directory: this.runDirectory,
      ...(this.facts.eventsPath === undefined ? {} : { events_path: this.facts.eventsPath }),
      plan_path: this.path('plan.md'),
      qwenloop_config: this.path('qwenloop.toml'),
      argv: this.facts.argv,
    };
  }

  /** Run a qwenloop control command; the error message when it failed. */
  private async control(invocation: Invocation): Promise<string | undefined> {
    const result = await this.services.processes.run(invocation.command, invocation.args, {
      env: this.environment,
      timeoutMs: 30_000,
    });
    return result.code === 0 ? undefined : (result.stderr || result.error || `exit ${result.code}`).trim();
  }

  private say(level: 'info' | 'warn' | 'error', text: string): void {
    this.patches.fire(this.transcript.note(level, text));
  }

  private move(status: RunStatus): void {
    this.state = status;
    this.statuses.fire(status);
  }

  private path(name: string): string {
    return path.join(this.runDirectory, name);
  }
}

/** Every finished run, and what was done with it after, in one append-only journal. */
export class RunHistory implements RunHistoryInterface {
  constructor(
    private readonly journal: JsonlJournal,
    private readonly now: () => Date,
  ) {}

  finished(record: RunRecord): void {
    this.journal.append({ type: 'run.finished', ...record });
  }

  applied(runId: string, detail: string): void {
    this.journal.append({ type: 'run.applied', run_id: runId, detail, at: this.now().toISOString() });
  }

  discarded(runId: string): void {
    this.journal.append({ type: 'run.discarded', run_id: runId, at: this.now().toISOString() });
  }

  list(): readonly RunHistoryEntry[] {
    const entries = new Map<string, { record: RunRecord; applied?: string; discarded?: string }>();
    for (const line of this.journal.readAll().records) {
      const runId = line.run_id;
      if (typeof runId !== 'string') {
        continue;
      }
      if (line.type === 'run.finished') {
        const record: Record<string, unknown> = { ...line };
        delete record.type;
        entries.set(runId, { record: record as unknown as RunRecord });
        continue;
      }
      const entry = entries.get(runId);
      if (entry === undefined) {
        continue;
      }
      if (line.type === 'run.applied') {
        entry.applied = String(line.at);
      } else if (line.type === 'run.discarded') {
        entry.discarded = String(line.at);
      }
    }
    return [...entries.values()].reverse();
  }
}
