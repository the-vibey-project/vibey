// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * One task, from request to recorded result.
 *
 * 1. Isolation. By default the task gets a git worktree of its own under the durable storm
 *    home, on a branch `vibey/<slug>-<id>`, so no engine edits the person's checkout.
 *    `vibey.runInPlace` runs in the open folder instead, with a warning.
 * 2. Choice. The loop, effort and engine come from `vibey loops --json` through the
 *    `LoopSelector` (sovereign by default; paid only once declared). On auto effort a failed
 *    attempt runs again in the same worktree at the ladder's next rung.
 * 3. An allow-listed environment for every engine: the basics, and the names its own
 *    descriptor declares; never `VIBEY_*`, `PG*`, or anything shaped like a database address.
 * 4. The slot: one run at a time per local machine, and per paid engine (8.c).
 * 5. Its events.jsonl, read by byte offset as it grows, in whichever envelope it is written.
 * 6. Its end: completed work is committed on the task's branch with the repository's own
 *    hooks (a refusal is recorded, never bypassed), and the outcome says which of completed,
 *    completed with no change, commit refused, failed, stopped or error it was.
 *
 * Nothing here stops a run for being slow: a local turn can take minutes, so a long silence
 * produces a hint. A graceful Stop asks the engine to end at a turn boundary; Force stop is a
 * separate act, open only once a graceful stop has had its fair time, and it is journaled.
 *
 * The engines this knows by name are the family's local runner under each name it ships as
 * (ADR-0061: gptossloop, the default, and qwenloop), and only for the binding the family
 * documents (docs/guides/local-models-ollama.md), each in its own settings' prefix:
 * `<PREFIX>_BASE_URL` names the Ollama endpoint, `<PREFIX>_MODEL` the model (only when one
 * is named, or the runner takes vibey.model: qwenloop's own config chooses its model),
 * `<PREFIX>_CONFIG` carries the run's context window over the person's own config for that
 * runner, and its per-turn desktop notification follows the setting. The names come from
 * `LocalRunners`, never from here. Declared by `interfaces/run-interface.ts`.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { SelectionError } from './catalogue';
import { ChildEnvironment, EnvironmentAllowList } from './environment';
import type { BudgetBreach } from './interfaces/budgets-interface';
import type { EventEnvelope, Selection } from './interfaces/catalogue-interface';
import type { EngineCommandInterface } from './interfaces/engine-command-interface';
import type { ChangedFile } from './interfaces/git-interface';
import type { RunnerIdentity } from './interfaces/local-runner-interface';
import type { ChildHandle, ProcessExit } from './interfaces/process-runner-interface';
import type { Invocation } from './interfaces/qwenloop-interface';
import type { RunItem, RunPatch } from './interfaces/run-events-interface';
import type {
  AttemptRecord,
  RunHistoryEntry,
  RunHistoryInterface,
  RunOutcome,
  RunRecord,
  RunRequest,
  RunServices,
  RunStatus,
  RunWorkspace,
  TaskRunInterface,
} from './interfaces/run-interface';
import type { Disposable } from './interfaces/support-interface';
import { JsonlJournal } from './jsonl';
import { RunTranscript } from './run-events';
import { Emitter } from './support';

/** Where attached files are copied, inside the task's worktree; never committed. */
export const ATTACHMENTS_DIRECTORY = '.vibey-attachments';

interface Attempting {
  readonly number: number;
  readonly runId: string;
  readonly selection: Selection;
  readonly command: EngineCommandInterface;
  readonly environment: Record<string, string>;
  readonly eventsPath: string;
  readonly argv: readonly string[];
}

export class TaskRun implements TaskRunInterface {
  /** The last characters of an engine's stderr kept, for the error a failed start reports. */
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
  private attempting: Attempting | undefined;
  private readonly attempts: AttemptRecord[] = [];
  private started = false;
  private forcedAt: string | undefined;
  private stopAt: number | undefined;
  private offset = 0;
  private lastActivity = 0;
  private hinted = false;
  private stderrTail = '';
  /** Resolves `result`; assigned in the constructor, by the promise's executor. */
  private settle!: (record: RunRecord) => void;
  private readonly runDirectory: string;
  private readonly startedAt: Date;
  private readonly startedMono: number;
  private planPath = '';
  private configPath: string | undefined;
  private placed: { kind: string; name: string; placed_at?: string }[] = [];
  private headSha: string | undefined;
  private diffStat = '';
  private changed: readonly ChangedFile[] = [];
  private uncommitted: readonly string[] = [];
  private commitError: string | undefined;
  private outOfScope: readonly string[] = [];
  private breach: BudgetBreach | undefined;
  private projection: RunRecord['projection'];
  private spent = { turns: 0, input: 0, output: 0, dollars: 0, at: 0 };

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

  get current(): TaskRunInterface['current'] {
    const attempt = this.attempting;
    return attempt === undefined
      ? undefined
      : { engine: attempt.selection.engine.engine_id, model: attempt.selection.model, effort: attempt.selection.effort };
  }

  get stopRequestedAt(): number | undefined {
    return this.stopAt;
  }

  get takesFollowUps(): boolean {
    return this.attempting !== undefined && this.attempting.selection.engine.controls.prompt !== null;
  }

  get budgetBreach(): BudgetBreach | undefined {
    return this.breach;
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
    const attempt = this.attempting;
    if (this.state !== 'running' || attempt === undefined || this.space === undefined) {
      return 'This task is not running, so there is nothing to send a follow-up to.';
    }
    const invocation = attempt.command.prompt(attempt.runId, message, this.space.cwd);
    if (invocation === undefined) {
      return `${attempt.selection.engine.engine_id} does not take follow-ups while it runs.`;
    }
    const error = await this.control(invocation, attempt.environment);
    if (error !== undefined) {
      return `The follow-up could not be sent: ${error}`;
    }
    this.say('info', 'Follow-up sent. The model reads it at the start of its next turn.');
    return undefined;
  }

  async stop(): Promise<string | undefined> {
    if (this.state === 'finishing' || this.state === 'finished') {
      return 'This task has already finished.';
    }
    this.stopAt ??= this.services.clock.monotonic();
    const attempt = this.attempting;
    if (this.child === undefined || attempt === undefined || this.space === undefined) {
      this.abort.abort();
      return undefined;
    }
    this.move('stopping');
    const invocation = attempt.command.stop(attempt.runId, this.space.cwd);
    if (invocation === undefined) {
      return `${attempt.selection.engine.engine_id} has no stop command, so it cannot be asked to wind down. Force stop opens once a stop has waited its fair time.`;
    }
    const error = await this.control(invocation, attempt.environment);
    if (error !== undefined) {
      return `The stop could not be sent: ${error}`;
    }
    this.say(
      'info',
      'Stopping. The model finishes the turn it is on, then the task ends; a slow turn can take a few minutes.',
    );
    return undefined;
  }

  forceStop(fairMs: number): string | undefined {
    if (this.child === undefined) {
      this.stopAt ??= this.services.clock.monotonic();
      this.abort.abort();
      return undefined;
    }
    if (this.stopAt === undefined) {
      return 'Press Stop first. A run is always asked to end gracefully before it can be forced.';
    }
    const waited = this.services.clock.monotonic() - this.stopAt;
    if (waited < fairMs) {
      return `Stop was asked ${Math.round(waited / 1000)} s ago. Force stop opens after ${Math.round(fairMs / 1000)} s, so the model can finish its turn.`;
    }
    this.forcedAt = this.services.clock.now().toISOString();
    this.services.history.forceStopped(this.runId, Math.round(waited));
    this.say('warn', `Force stop: the process was ended ${Math.round(waited / 1000)} s after the graceful stop was asked.`);
    this.child.kill('SIGTERM');
    return undefined;
  }

  /** The whole task; the flag says whether its directory passed the durability gate. */
  private async run(): Promise<[RunRecord, boolean]> {
    if (this.abort.signal.aborted) {
      return [this.record('wound-down', 'Stopped before it started.'), false];
    }
    this.move('preparing');
    try {
      this.services.gate.enforce({ 'run records': this.runDirectory });
    } catch (error) {
      return [this.record('error', (error as Error).message), false];
    }
    try {
      if (this.services.catalogue.notice !== undefined) {
        this.say('warn', this.services.catalogue.notice);
      }
      this.space = await this.prepare();
      this.writePlan(this.space);
      let previous: string | undefined;
      for (let number = 1; ; number += 1) {
        const outcome = await this.attempt(number, this.space, previous);
        if (outcome === undefined) {
          return [this.record('wound-down', 'Stopped before it started.'), true];
        }
        const [attempted, error] = outcome;
        // A lane a budget wound down ends as budget-exhausted; one that finished its work anyway keeps its result.
        const result: RunOutcome = this.breach !== undefined && (attempted === 'wound-down' || attempted === 'failed') ? 'budget-exhausted' : attempted;
        const again =
          result === 'failed' &&
          this.request.effort === 'auto' &&
          this.stopAt === undefined &&
          number < this.services.catalogue.ladder.exhausted_after;
        if (!again) {
          return [await this.finish(result, this.space, error), true];
        }
        previous = this.attempting?.selection.engine.engine_id;
        this.say('info', `Attempt ${number} did not finish. Auto effort tries again at the ladder's next rung, in the same copy.`);
      }
    } catch (error) {
      const stopped = this.stopAt !== undefined && this.child === undefined;
      return [this.record(stopped ? 'wound-down' : 'error', (error as Error).message), true];
    }
  }

  /** One engine run; undefined when stopped before its process started. */
  private async attempt(
    number: number,
    space: RunWorkspace,
    previous: string | undefined,
  ): Promise<[RunOutcome, string | undefined] | undefined> {
    const { settings, selector } = this.services;
    const resident = this.request.loop === 'sovereignloop' ? await this.services.resident() : [];
    const selection = selector.select({
      loop: this.request.loop,
      effort: this.request.effort,
      engine: this.request.engine,
      baseEffort: this.request.baseEffort,
      attempt: number,
      ...(previous === undefined ? {} : { previousEngine: previous }),
      resident,
      paidDeclared: this.services.paidDeclared(),
      ...(this.request.maxTurns === undefined ? {} : { taskMaxTurns: this.request.maxTurns }),
      ...(settings.maxTurns === undefined ? {} : { settingMaxTurns: settings.maxTurns }),
    });
    this.say('info', `Attempt ${number}: ${selection.reason}.`);
    const refused = this.checkBudget(selection);
    if (refused !== undefined) {
      this.breach = refused;
      return [
        'budget-exhausted',
        number === 1
          ? `Not started: ${refused.message} Edit the budget to allow it.`
          : `Auto effort stops climbing: ${refused.message}`,
      ];
    }
    const command = this.services.command(selection.engine);
    if (typeof command === 'string') {
      throw new SelectionError(command);
    }
    const runId = number === 1 ? this.runId : this.services.ids.uuid();
    const runner = this.services.runners.identify(selection.engine.engine_id);
    const effortArgv = [...selection.argv];
    if (runner !== undefined) {
      effortArgv.push(settings.desktopNotifications ? '--desktop-notifications' : '--no-desktop-notifications');
    }
    const invocation = command.run({ plan: this.planPath, runId, cwd: space.cwd, effortArgv });
    const eventsPath = command.eventsPath(space.cwd, runId);
    const environment = this.environmentFor(selection, runner);
    this.attempting = {
      number,
      runId,
      selection,
      command,
      environment,
      eventsPath,
      argv: [invocation.command, ...invocation.args],
    };
    this.offset = 0;
    this.transcript.beginAttempt();
    this.spent.at = this.services.clock.monotonic();
    this.move('waiting');
    let waited = false;
    const slot = await this.services.lockFor(selection.engine, selection.tier).acquire(
      `${this.request.title} (task ${this.runId})`,
      (holder) => {
        if (!waited) {
          waited = true;
          this.say(
            'info',
            holder === undefined
              ? `Waiting for the ${selection.tier === 'local' ? 'local model' : selection.engine.engine_id} slot: another run is using it.`
              : `Waiting: ${holder.purpose} (process ${holder.pid}) is using the ${selection.tier === 'local' ? 'local model' : selection.engine.engine_id} slot.`,
          );
        }
      },
      settings.pollMs,
      this.abort.signal,
    );
    let exit: ProcessExit;
    try {
      if (this.abort.signal.aborted) {
        return undefined;
      }
      exit = await this.watch(invocation, space.cwd, environment, eventsPath, selection.engine.events.envelope);
    } finally {
      slot.dispose();
    }
    const [outcome, error] = this.classify(exit, selection);
    this.attempts.push({
      attempt: number,
      run_id: runId,
      loop: selection.loop,
      tier: selection.tier,
      engine: selection.engine.engine_id,
      model: selection.model,
      effort: selection.effort,
      effort_source: selection.effortSource,
      ...(selection.maxTurns === undefined ? {} : { max_turns: selection.maxTurns }),
      max_turns_source: selection.maxTurnsSource,
      reason: selection.reason,
      outcome,
      exit_code: exit.code,
      signal: exit.signal,
      argv: [invocation.command, ...invocation.args],
      events_path: eventsPath,
      turns: this.transcript.attemptTurns,
    });
    return [outcome, error];
  }

  private async prepare(): Promise<RunWorkspace> {
    const { git, naming, settings, gate } = this.services;
    const repository = await git.toplevel(this.request.directory);
    if (this.request.inPlace) {
      const baseSha = await git.resolveCommit(repository, 'HEAD');
      const branch = await git.currentBranch(repository);
      this.say(
        'warn',
        'Running in place: the engine edits your open folder directly, on your current branch. This run has no Apply or Discard; review and undo it with git.',
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

  /** The plan, with what the person attached and any context packet, in the run's directory. */
  private writePlan(space: RunWorkspace): void {
    fs.mkdirSync(this.runDirectory, { recursive: true });
    const parts = [this.request.task.trimEnd()];
    const attachments = this.request.attachments ?? [];
    const files = attachments.filter((attachment) => attachment.kind !== 'text');
    if (files.length > 0) {
      const into = path.join(space.cwd, ATTACHMENTS_DIRECTORY);
      fs.mkdirSync(into, { recursive: true });
      const lines = ['', '## Files the person attached', ''];
      for (const attachment of files) {
        const target = path.join(into, path.basename(attachment.name));
        fs.copyFileSync(attachment.name, target);
        const relative = path.relative(space.cwd, target);
        this.placed.push({ kind: attachment.kind, name: attachment.name, placed_at: relative });
        lines.push(`- ${relative} (a copy of ${attachment.name}; it is not part of the change)`);
      }
      parts.push(lines.join('\n'));
    }
    for (const attachment of attachments.filter((item) => item.kind === 'text')) {
      this.placed.push({ kind: 'text', name: attachment.name });
      parts.push(['', `## Pasted by the person: ${attachment.name}`, '', attachment.text ?? ''].join('\n'));
    }
    const packet = this.request.contextPacket;
    if (packet !== undefined) {
      parts.push(['', `## Context from vibey-skills (${packet.plugins.join(', ') || 'ranked'})`, '', packet.markdown.trimEnd()].join('\n'));
    }
    this.planPath = this.path('plan.md');
    fs.writeFileSync(this.planPath, `${parts.join('\n')}\n`);
  }

  /**
   * The engine's allow-listed environment: the basics, the vibey.environment.allow setting,
   * and the names its descriptor declares. A local runner also gets the family's local
   * binding, in its own settings' prefix.
   */
  private environmentFor(selection: Selection, runner: RunnerIdentity | undefined): Record<string, string> {
    const { settings } = this.services;
    const engine = selection.engine;
    const allow = EnvironmentAllowList.MODEL_BASICS.extended(
      [...settings.environmentAllow, ...engine.env.auth, ...engine.env.passthrough],
      `the ${engine.engine_id} environment`,
    );
    const overlay: Record<string, string> = {};
    if (selection.tier === 'local') {
      overlay.OLLAMA_HOST = settings.ollama.root;
    }
    if (runner !== undefined) {
      const { runners } = this.services;
      this.configPath = this.path(`${runner.name}.toml`);
      const user = this.services.userConfig(runner);
      fs.writeFileSync(this.configPath, this.services.runConfig.compose(user?.text, { contextWindow: this.request.contextWindow }));
      overlay[runners.variable(runner, 'BASE_URL')] = settings.ollama.v1;
      overlay[runners.variable(runner, 'CONFIG')] = this.configPath;
      // vibey.model is gptossloop's model; a runner with no default of its own (qwenloop)
      // gets a model only when one is named, else its own config chooses (ADR-0061).
      const model = selection.model ?? (runner.defaultModel === null ? undefined : settings.model);
      if (model !== undefined) {
        overlay[runners.variable(runner, 'MODEL')] = model;
      }
      this.say(
        'info',
        `${runner.name} plans for a ${this.request.contextWindow.toLocaleString('en-US')}-token window on ${model ?? 'the model its own config chooses'}` +
          (user === undefined ? '.' : `, over your own config at ${user.path}.`),
      );
    }
    return new ChildEnvironment(allow, overlay).build(this.services.environ);
  }

  private watch(
    invocation: Invocation,
    cwd: string,
    environment: Record<string, string>,
    eventsPath: string,
    envelope: EventEnvelope,
  ): Promise<ProcessExit> {
    const { clock, settings, processes } = this.services;
    const child = processes.spawn(invocation.command, invocation.args, { cwd, env: environment });
    this.child = child;
    // A stop asked before this point aborted the run, so it never reaches a process.
    this.move('running');
    child.onStderr((text) => {
      this.stderrTail = `${this.stderrTail}${text}`.slice(-TaskRun.STDERR_TAIL);
    });
    this.lastActivity = clock.monotonic();
    this.hinted = false;
    const timer = clock.every(settings.pollMs, () => this.poll(eventsPath, envelope));
    return child.exited.then((exit) => {
      timer.dispose();
      this.poll(eventsPath, envelope);
      this.child = undefined;
      return exit;
    });
  }

  private poll(eventsPath: string, envelope: EventEnvelope): void {
    const { clock, settings, tail } = this.services;
    const chunk = tail.read(eventsPath, this.offset);
    if (chunk.restarted) {
      this.say('warn', 'The event log was replaced, so it is being read again from the start.');
    }
    if (chunk.nextOffset !== this.offset) {
      this.lastActivity = clock.monotonic();
      this.hinted = false;
    }
    this.offset = chunk.nextOffset;
    for (const event of chunk.records) {
      for (const patch of this.transcript.accept(event, envelope)) {
        this.patches.fire(patch);
      }
    }
    if (chunk.malformed > 0) {
      this.say('warn', `${chunk.malformed} line(s) of the event log were not JSON and were skipped.`);
    }
    this.recordSpend();
    const quiet = clock.monotonic() - this.lastActivity;
    if (!this.hinted && (this.state === 'running' || this.state === 'stopping') && quiet >= settings.stuckHintMs) {
      this.hinted = true;
      this.say(
        'info',
        `Quiet for ${Math.round(quiet / 60_000)} minutes. That can be normal: gpt-oss:20b on a 24 GB Mac writes about 26 tokens a second and may reason for 1,500 to 5,000 tokens before one tool call, so a turn can take a few minutes. Nothing has been stopped.`,
      );
    }
  }

  /** Project the attempt's cost and ask every matching budget; the first it would pass. */
  private checkBudget(selection: Selection): BudgetBreach | undefined {
    const engine = selection.engine;
    const measured = this.services.spend.perTurn(engine.engine_id);
    const perTurn = measured ?? this.services.settings.budgetPerTurn;
    const turns = selection.maxTurns;
    const dollars =
      turns === undefined ? undefined : (turns * (perTurn.input * engine.cost_per_mtok_in + perTurn.output * engine.cost_per_mtok_out)) / 1_000_000;
    this.projection = {
      ...(turns === undefined ? {} : { turns }),
      ...(dollars === undefined ? {} : { dollars: Math.round(dollars * 10_000) / 10_000 }),
      per_turn: measured === undefined ? 'declared (vibey.budgetInputTokensPerTurn, vibey.budgetOutputTokensPerTurn)' : `measured on this machine for ${engine.engine_id}`,
    };
    return this.services.budgets.wouldExceed({
      loop: selection.loop,
      engineId: engine.engine_id,
      runId: this.runId,
      projected: { ...(turns === undefined ? {} : { turns }), ...(dollars === undefined ? {} : { dollars }) },
    });
  }

  /**
   * Append what the lane spent since the last entry (at a turn boundary), then ask the
   * budgets. A budget used up winds the lane down gracefully; nothing is killed.
   */
  private recordSpend(): void {
    const attempt = this.attempting as Attempting;
    const turns = this.transcript.turns - this.spent.turns;
    if (turns <= 0) {
      return;
    }
    const engine = attempt.selection.engine;
    const input = this.transcript.inputTokens - this.spent.input;
    const output = this.transcript.outputTokens - this.spent.output;
    const reported = this.transcript.reportedDollars - this.spent.dollars;
    const now = this.services.clock.monotonic();
    this.services.spend.record({
      run_id: this.runId,
      at: this.services.clock.now().toISOString(),
      loop: attempt.selection.loop,
      engine_id: engine.engine_id,
      turns,
      input_tokens: input,
      output_tokens: output,
      dollars: reported > 0 ? reported : (input * engine.cost_per_mtok_in + output * engine.cost_per_mtok_out) / 1_000_000,
      minutes: (now - this.spent.at) / 60_000,
    });
    this.spent = { turns: this.transcript.turns, input: this.transcript.inputTokens, output: this.transcript.outputTokens, dollars: this.transcript.reportedDollars, at: now };
    if (this.breach === undefined && this.state === 'running') {
      const used = this.services.budgets.exhausted({ loop: attempt.selection.loop, engineId: engine.engine_id, runId: this.runId });
      if (used !== undefined) {
        this.breach = used;
        this.say('warn', `${used.message} The lane winds down at the end of this turn; Grant more to raise the budget.`);
        void this.stop();
      }
    }
  }

  private classify(exit: ProcessExit, selection: Selection): [RunOutcome, string | undefined] {
    if (exit.error !== undefined) {
      return ['error', `${selection.engine.engine_id} could not be started: ${exit.error}`];
    }
    if (this.forcedAt !== undefined || exit.code === this.services.runners.protocol.exitWoundDown) {
      return ['wound-down', undefined];
    }
    if (exit.code === 0) {
      return [this.transcript.failure === undefined ? 'completed' : 'failed', undefined];
    }
    if (this.stopAt !== undefined) {
      return ['wound-down', undefined];
    }
    if (this.transcript.failure !== undefined || this.transcript.attemptTurns > 0) {
      return ['failed', undefined];
    }
    const said = this.stderrTail.trim();
    return [
      'error',
      said || `${selection.engine.engine_id} ended with ${exit.code === null ? `signal ${exit.signal}` : `exit code ${exit.code}`} before its first turn`,
    ];
  }

  private async finish(outcome: RunOutcome, space: RunWorkspace, error: string | undefined): Promise<RunRecord> {
    this.move('finishing');
    const { git, catalogue } = this.services;
    const exclude = [...new Set([...catalogue.loops.flatMap((loop) => loop.engines.map((engine) => engine.state_dir)), ATTACHMENTS_DIRECTORY])];
    let final = outcome;
    if (final === 'completed' && space.mode === 'worktree') {
      const commit = await git.commitAll(space.cwd, this.request.commitMessage, exclude, this.request.paths);
      this.outOfScope = commit.outOfScope ?? [];
      if (commit.error !== undefined) {
        final = 'completed-commit-refused';
        this.commitError = commit.error;
      } else if (this.outOfScope.length > 0) {
        final = 'completed-out-of-scope';
        this.say('warn', `Left uncommitted, outside this task's paths: ${this.outOfScope.join(', ')}. Review them in its copy.`);
      }
    }
    this.headSha = await git.head(space.cwd);
    this.uncommitted = await git.uncommitted(space.cwd, exclude);
    this.changed = await git.changedFiles(space.repository, space.baseSha, this.headSha);
    this.diffStat = await git.diffStat(space.repository, space.baseSha, this.headSha);
    if (final === 'completed' && this.changed.length === 0 && this.uncommitted.length === 0) {
      final = 'completed-no-change';
    }
    return this.record(final, error);
  }

  private record(outcome: RunOutcome, error?: string): RunRecord {
    const { settings, clock, catalogue } = this.services;
    const verdict = this.transcript.verdict();
    const space = this.space;
    const last = this.attempts[this.attempts.length - 1];
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
      exit_code: last?.exit_code ?? null,
      signal: last?.signal ?? null,
      loop: this.request.loop,
      ...(last === undefined ? {} : { engine: last.engine, effort: last.effort }),
      model: last?.model ?? (this.request.loop === 'sovereignloop' ? settings.model : null),
      catalogue: catalogue.source,
      context_window: this.request.contextWindow,
      ...(last?.max_turns === undefined ? {} : { max_turns: last.max_turns }),
      ...(last === undefined ? {} : { max_turns_source: last.max_turns_source }),
      attempts: this.attempts,
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
      ...(this.headSha === undefined ? {} : { head_sha: this.headSha }),
      diff_stat: this.diffStat,
      changed_files: this.changed,
      uncommitted: this.uncommitted,
      attachments: this.placed,
      ...(this.request.contextPacket === undefined ? {} : { context_plugins: this.request.contextPacket.plugins }),
      ...(verdict.text === undefined ? {} : { verdict: verdict.text }),
      marker: verdict.marker,
      ...(failure === undefined ? {} : { failure }),
      ...(error === undefined ? {} : { error }),
      ...(this.commitError === undefined ? {} : { commit_error: this.commitError }),
      ...(this.request.paths === undefined ? {} : { paths: this.request.paths }),
      ...(this.outOfScope.length === 0 ? {} : { out_of_scope: this.outOfScope }),
      ...(this.breach === undefined
        ? {}
        : { budget: { id: this.breach.budget.id, cap: this.breach.cap, limit: this.breach.limit, spent: this.breach.spent, message: this.breach.message } }),
      ...(this.projection === undefined ? {} : { projection: this.projection }),
      ...(this.forcedAt === undefined ? {} : { force_stopped_at: this.forcedAt }),
      turns: this.transcript.turns,
      input_tokens: this.transcript.inputTokens,
      output_tokens: this.transcript.outputTokens,
      started_at: this.startedAt.toISOString(),
      finished_at: clock.now().toISOString(),
      duration_ms: Math.round(clock.monotonic() - this.startedMono),
      run_directory: this.runDirectory,
      ...(last === undefined ? {} : { events_path: last.events_path }),
      plan_path: this.path('plan.md'),
      ...(this.configPath === undefined ? {} : { engine_config: this.configPath }),
      argv: last?.argv ?? [],
    };
  }

  /** Run an engine control command; the error message when it failed. */
  private async control(invocation: Invocation, environment: Record<string, string>): Promise<string | undefined> {
    const result = await this.services.processes.run(invocation.command, invocation.args, {
      env: environment,
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

  forceStopped(runId: string, afterMs: number): void {
    this.journal.append({ type: 'run.force-stopped', run_id: runId, after_ms: afterMs, at: this.now().toISOString() });
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
