// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Loops, engines, efforts and the ladder, as `vibey loops --json` states them, and the
 * choice of engine and model for a run.
 *
 * The two layers are vibey's own (canon 8.b, 8.c). The outer layer is the loop: the
 * person's `sovereignloop` by default, and `paidloop` only once they have declared it, and
 * a sovereign run never escalates to paid by itself. The inner layer picks within the loop:
 * an engine chosen by name, or, on auto, the enabled engines whose projection achieves the
 * effort. For a local loop that means a smooth weighted round robin by `base_weight` that
 * prefers a model Ollama already holds resident. For the paid loop it means Claude through
 * claudeloop, the declared paid default, and its other adapters only when that engine is
 * not available (8.b "Paid defaults"). Auto effort starts at the task's base and climbs
 * `build_attempts` one rung per failed attempt, as `effort_for_attempt` does, and a rise
 * in effort rotates away from the previous engine. Declared by
 * `interfaces/catalogue-interface.ts`.
 */
import type {
  Catalogue,
  CatalogueEngine,
  CatalogueLoop,
  CatalogueParserInterface,
  Effort,
  EffortChoice,
  EngineEffort,
  Ladder,
  LoopName,
  LoopSelectorInterface,
  Selection,
  SelectionRequest,
} from './interfaces/catalogue-interface';
import { LocalRunners } from './local-runner';
import { ModelName } from './ollama';

export class CatalogueError extends Error {
  constructor(where: string, detail: string) {
    super(`vibey loops --json: ${where}: ${detail}`);
    this.name = 'CatalogueError';
  }
}

export class SelectionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SelectionError';
  }
}

export class Efforts {
  static readonly ALL: readonly Effort[] = ['TRIVIAL', 'LOW', 'STANDARD', 'HIGH', 'MAX'];

  static is(value: unknown): value is Effort {
    return typeof value === 'string' && (Efforts.ALL as readonly string[]).includes(value);
  }

  static rank(effort: Effort): number {
    return Efforts.ALL.indexOf(effort);
  }

  static max(left: Effort, right: Effort): Effort {
    return Efforts.rank(left) >= Efforts.rank(right) ? left : right;
  }
}

/** Reads the JSON strictly: a field of the wrong shape names itself rather than going quiet. */
class Shape {
  static record(value: unknown, where: string): Record<string, unknown> {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) {
      throw new CatalogueError(where, 'is not an object');
    }
    return value as Record<string, unknown>;
  }

  static list(value: unknown, where: string): unknown[] {
    if (!Array.isArray(value)) {
      throw new CatalogueError(where, 'is not a list');
    }
    return value;
  }

  static string(value: unknown, where: string): string {
    if (typeof value !== 'string') {
      throw new CatalogueError(where, 'is not a string');
    }
    return value;
  }

  static optionalString(value: unknown, where: string): string | null {
    return value === null || value === undefined ? null : Shape.string(value, where);
  }

  static boolean(value: unknown, where: string): boolean {
    if (typeof value !== 'boolean') {
      throw new CatalogueError(where, 'is not true or false');
    }
    return value;
  }

  static optionalBoolean(value: unknown, where: string): boolean | null {
    return value === null || value === undefined ? null : Shape.boolean(value, where);
  }

  static number(value: unknown, where: string): number {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new CatalogueError(where, 'is not a number');
    }
    return value;
  }

  static strings(value: unknown, where: string): string[] {
    return Shape.list(value, where).map((item, index) => Shape.string(item, `${where}[${index}]`));
  }

  static optionalStrings(value: unknown, where: string): string[] | null {
    return value === null || value === undefined ? null : Shape.strings(value, where);
  }

  static effort(value: unknown, where: string): Effort {
    if (!Efforts.is(value)) {
      throw new CatalogueError(where, `is not one of ${Efforts.ALL.join(', ')}`);
    }
    return value;
  }
}

export class CatalogueParser implements CatalogueParserInterface {
  parse(value: unknown): Catalogue {
    const root = Shape.record(value, 'the answer');
    const loops = Shape.list(root.loops, 'loops').map((loop, index) => this.loop(loop, `loops[${index}]`));
    const defaultLoop = Shape.string(root.default_loop, 'default_loop');
    if (!loops.some((loop) => loop.loop === defaultLoop)) {
      throw new CatalogueError('default_loop', `names ${defaultLoop}, which is not among the loops`);
    }
    return {
      efforts: Shape.list(root.efforts, 'efforts').map((effort, index) => Shape.effort(effort, `efforts[${index}]`)),
      default_loop: defaultLoop as LoopName,
      paid_default_engine: Shape.string(root.paid_default_engine ?? root.paid_default, 'paid_default_engine'),
      ladder: this.ladder(root.ladder),
      loops,
      source: 'vibey',
    };
  }

  private ladder(value: unknown): Ladder {
    const ladder = Shape.record(value, 'ladder');
    const base = Shape.record(ladder.phase_base, 'ladder.phase_base');
    return {
      phase_base: Object.fromEntries(
        Object.entries(base).map(([phase, effort]) => [phase, Shape.effort(effort, `ladder.phase_base.${phase}`)]),
      ),
      build_attempts: Shape.list(ladder.build_attempts, 'ladder.build_attempts').map((effort, index) =>
        Shape.effort(effort, `ladder.build_attempts[${index}]`),
      ),
      exhausted_after: Shape.number(ladder.exhausted_after, 'ladder.exhausted_after'),
      rotates_when_effort_rises: Shape.boolean(ladder.rotates_when_effort_rises, 'ladder.rotates_when_effort_rises'),
    };
  }

  private loop(value: unknown, where: string): CatalogueLoop {
    const loop = Shape.record(value, where);
    const name = Shape.string(loop.loop, `${where}.loop`);
    if (name !== 'sovereignloop' && name !== 'paidloop') {
      throw new CatalogueError(`${where}.loop`, `is ${name}; the family has exactly two loops, sovereignloop and paidloop (8.c)`);
    }
    const tier = Shape.string(loop.tier, `${where}.tier`);
    if (tier !== 'local' && tier !== 'paid') {
      throw new CatalogueError(`${where}.tier`, 'is neither local nor paid');
    }
    const byEffort = Shape.record(loop.by_effort, `${where}.by_effort`);
    return {
      loop: name,
      tier,
      default: Shape.boolean(loop.default, `${where}.default`),
      declared_only: Shape.boolean(loop.declared_only, `${where}.declared_only`),
      engines: Shape.list(loop.engines, `${where}.engines`).map((engine, index) =>
        this.engine(engine, `${where}.engines[${index}]`),
      ),
      by_effort: Object.fromEntries(
        Object.entries(byEffort).map(([effort, choices]) => [
          Shape.effort(effort, `${where}.by_effort`),
          Shape.list(choices, `${where}.by_effort.${effort}`).map((choice, index) =>
            this.choice(choice, `${where}.by_effort.${effort}[${index}]`),
          ),
        ]),
      ),
    };
  }

  private choice(value: unknown, where: string): EffortChoice {
    const choice = Shape.record(value, where);
    return {
      engine_id: Shape.string(choice.engine_id, `${where}.engine_id`),
      model: Shape.optionalString(choice.model, `${where}.model`),
      achieved: Shape.effort(choice.achieved, `${where}.achieved`),
    };
  }

  private engine(value: unknown, where: string): CatalogueEngine {
    const engine = Shape.record(value, where);
    const capabilities = Shape.record(engine.capabilities, `${where}.capabilities`);
    const controls = Shape.record(engine.controls, `${where}.controls`);
    const events = Shape.record(engine.events, `${where}.events`);
    const env = Shape.record(engine.env, `${where}.env`);
    const envelope = Shape.string(events.envelope, `${where}.events.envelope`);
    if (envelope !== 'type' && envelope !== 'event_type+payload' && envelope !== 'event_type') {
      throw new CatalogueError(`${where}.events.envelope`, 'is none of "type", "event_type+payload" and "event_type"');
    }
    const efforts = Shape.list(engine.efforts, `${where}.efforts`).map((effort, index) =>
      this.effortEntry(effort, `${where}.efforts[${index}]`),
    );
    const evidence = capabilities.evidence === undefined ? {} : Shape.record(capabilities.evidence, `${where}.capabilities.evidence`);
    return {
      engine_id: Shape.string(engine.engine_id, `${where}.engine_id`),
      binary: Shape.string(engine.binary, `${where}.binary`),
      state_dir: Shape.string(engine.state_dir, `${where}.state_dir`),
      enabled: Shape.boolean(engine.enabled, `${where}.enabled`),
      // A producer from before the canon's repeals says nothing: nothing it lists is repealed.
      repealed: Shape.optionalBoolean(engine.repealed, `${where}.repealed`) ?? false,
      switch: Shape.optionalString(engine.switch, `${where}.switch`),
      // A producer from before ADR-0064 says nothing: then no engine was on by default.
      on_by_default: Shape.optionalBoolean(engine.on_by_default, `${where}.on_by_default`) ?? false,
      cost_per_mtok_in: Shape.number(engine.cost_per_mtok_in, `${where}.cost_per_mtok_in`),
      cost_per_mtok_out: Shape.number(engine.cost_per_mtok_out, `${where}.cost_per_mtok_out`),
      default_model: Shape.optionalString(engine.default_model, `${where}.default_model`),
      efforts,
      capabilities: {
        images: Shape.optionalBoolean(capabilities.images, `${where}.capabilities.images`),
        files: Shape.optionalBoolean(capabilities.files, `${where}.capabilities.files`),
        paste_text: Shape.optionalBoolean(capabilities.paste_text, `${where}.capabilities.paste_text`),
        paste_images: Shape.optionalBoolean(capabilities.paste_images, `${where}.capabilities.paste_images`),
        plugins: Shape.optionalString(capabilities.plugins, `${where}.capabilities.plugins`),
        mcp: Shape.optionalBoolean(capabilities.mcp, `${where}.capabilities.mcp`),
        evidence: Object.fromEntries(
          Object.entries(evidence).map(([key, text]) => [key, Shape.string(text, `${where}.capabilities.evidence.${key}`)]),
        ),
      },
      done_marker: Shape.optionalString(engine.done_marker, `${where}.done_marker`),
      plan_flag: Shape.optionalString(engine.plan_flag, `${where}.plan_flag`),
      supports_cwd_flag: Shape.boolean(engine.supports_cwd_flag, `${where}.supports_cwd_flag`),
      base_weight: Shape.number(engine.base_weight, `${where}.base_weight`),
      run: Shape.strings(engine.run, `${where}.run`),
      controls: {
        stop: Shape.optionalStrings(controls.stop, `${where}.controls.stop`),
        wind_down: Shape.optionalStrings(controls.wind_down, `${where}.controls.wind_down`),
        prompt: Shape.optionalStrings(controls.prompt, `${where}.controls.prompt`),
      },
      events: { path: Shape.string(events.path, `${where}.events.path`), envelope },
      env: {
        auth: Shape.strings(env.auth, `${where}.env.auth`),
        passthrough: Shape.strings(env.passthrough, `${where}.env.passthrough`),
      },
      ...CatalogueParser.notes(engine.notes, `${where}.notes`),
      ...(efforts.some((entry) => entry.argv.includes(DegradedCatalogue.TURNS_FLAG))
        ? { turns_flag: DegradedCatalogue.TURNS_FLAG }
        : {}),
    };
  }

  /** An engine's notes: a list of lines (a single string from an older producer is one line). */
  private static notes(value: unknown, where: string): { notes?: readonly string[] } {
    if (value === undefined || value === null) {
      return {};
    }
    const lines = (typeof value === 'string' ? [value] : Shape.strings(value, where)).filter((line) => line.trim() !== '');
    return lines.length === 0 ? {} : { notes: lines };
  }

  private effortEntry(value: unknown, where: string): EngineEffort {
    const entry = Shape.record(value, where);
    return {
      effort: Shape.effort(entry.effort, `${where}.effort`),
      argv: Shape.strings(entry.argv, `${where}.argv`),
      achieved: Shape.effort(entry.achieved, `${where}.achieved`),
      model: Shape.optionalString(entry.model, `${where}.model`),
      notes: Shape.optionalString(entry.notes, `${where}.notes`) ?? '',
    };
  }
}

/**
 * What the extension runs when vibey cannot say: an older vibey without `vibey loops`, or
 * none at all. sovereignloop with the family's default local runner, gptossloop (ADR-0064),
 * on the configured model, effort auto with no ladder, and only the capabilities the
 * runner's own CLI shows. The run and control shapes are the runner's own
 * (`qwenloop/cli/app.py`), the only engine it knows without vibey.
 *
 * qwenloop is deliberately not listed. It is the same runner on a Qwen model, and it runs
 * only once vibey switches it on (VIBEY_FEATURE_QWENLOOP=1); with no vibey to read that
 * switch, listing it would offer an engine nothing here can say is on, or one a switch the
 * person sets would never turn on. Naming it (`vibey.engine`) says it is not an engine here.
 *
 * gptossloop ships in the same vibey release as `vibey loops`, so behind a vibey too old
 * for `vibey loops` there is no gptossloop either: the run then says gptossloop cannot be
 * found and that it ships with vibey, which is the whole fix. The older `qwenloop` that
 * ran gpt-oss there is not offered in its place: it reads QWENLOOP_*, and since ADR-0064 a
 * program by that name means the Qwen engine.
 */
export class DegradedCatalogue {
  static readonly TURNS_FLAG = '--max-turns';

  static sovereign(model: string, notice: string): Catalogue {
    const runners = LocalRunners.FAMILY;
    const runner = runners.default;
    const note = `vibey loops is not available: the turn limit is the task's max_turns or vibey.maxTurns when set, else ${runner.name}'s own`;
    const local: CatalogueEngine = {
      engine_id: runner.name,
      binary: runner.name,
      state_dir: runners.protocol.stateDir,
      enabled: true,
      repealed: false,
      switch: null,
      on_by_default: runner.onByDefault,
      cost_per_mtok_in: 0,
      cost_per_mtok_out: 0,
      default_model: model,
      efforts: Efforts.ALL.map((effort) => ({ effort, argv: [], achieved: 'STANDARD' as Effort, model, notes: note })),
      capabilities: { images: null, files: true, paste_text: true, paste_images: null, plugins: null, mcp: null, evidence: {} },
      done_marker: runners.protocol.doneMarker,
      plan_flag: null,
      supports_cwd_flag: true,
      base_weight: 1,
      run: ['{binary}', 'run', '{plan_flag?}', '{plan}', '--run-id', '{run_id}', '{effort_argv...}', '--cwd', '{cwd}'],
      controls: {
        stop: ['stop', '{run_id}', '--cwd', '{cwd}'],
        wind_down: ['wind-down', '{run_id}', '--cwd', '{cwd}'],
        // A runner released before vibey 3.0.0 reads no follow-up, and gptossloop is the
        // runner's name only since ADR-0064, so every gptossloop does: it gets a prompt box.
        prompt: ['prompt', '{run_id}', '{text}', '--cwd', '{cwd}'],
      },
      events: { path: '{cwd}/{state_dir}/runs/{run_id}/events.jsonl', envelope: 'type' },
      env: { auth: [], passthrough: [runners.passthrough(runner)] },
      notes: [note],
      turns_flag: DegradedCatalogue.TURNS_FLAG,
    };
    return {
      efforts: Efforts.ALL,
      default_loop: 'sovereignloop',
      paid_default_engine: 'claudeloop',
      ladder: { phase_base: {}, build_attempts: [], exhausted_after: 1, rotates_when_effort_rises: false },
      loops: [
        {
          loop: 'sovereignloop',
          tier: 'local',
          default: true,
          declared_only: false,
          engines: [local],
          by_effort: Object.fromEntries(
            Efforts.ALL.map((effort) => [effort, [{ engine_id: runner.name, model, achieved: 'STANDARD' as Effort }]]),
          ),
        },
      ],
      source: 'degraded',
      notice,
    };
  }
}

export class LoopSelector implements LoopSelectorInterface {
  /** Smooth weighted round robin state, per loop and effort, as vibey's rotation keeps it. */
  private readonly current = new Map<string, number>();

  constructor(private readonly catalogue: Catalogue) {}

  effortForAttempt(base: Effort, attempt: number): Effort {
    const { ladder } = this.catalogue;
    if (!Number.isInteger(attempt) || attempt < 1) {
      throw new SelectionError('an attempt is counted from 1');
    }
    if (attempt > ladder.exhausted_after) {
      throw new SelectionError(
        `the effort ladder is exhausted after ${ladder.exhausted_after} attempt(s); vibey parks the work for a person at this point`,
      );
    }
    const rung = ladder.build_attempts[attempt - 1];
    return rung === undefined ? base : Efforts.max(base, rung);
  }

  select(request: SelectionRequest): Selection {
    const loop = this.catalogue.loops.find((candidate) => candidate.loop === request.loop);
    if (loop === undefined) {
      throw new SelectionError(
        this.catalogue.source === 'degraded'
          ? `${request.loop} is not available: ${this.catalogue.notice}`
          : `${request.loop} is not one of the loops vibey lists`,
      );
    }
    if (loop.declared_only && !request.paidDeclared) {
      throw new SelectionError(
        `${loop.loop} is declared-only: vendors bill their own accounts, so it runs only after you declare it (vibey.loop, then confirm once).`,
      );
    }
    let effort: Effort;
    let effortSource: Selection['effortSource'];
    if (request.effort === 'auto') {
      effort = this.effortForAttempt(request.baseEffort, request.attempt);
      effortSource = 'auto';
    } else {
      effort = request.effort;
      effortSource = 'chosen';
    }
    const slash = request.engine.indexOf('/');
    const engineId = slash < 0 ? request.engine : request.engine.slice(0, slash);
    const wantedModel = slash < 0 ? undefined : request.engine.slice(slash + 1);
    let engine: CatalogueEngine;
    let reason: string;
    if (engineId === 'auto' || engineId === '') {
      [engine, reason] = this.automatic(loop, effort, request);
    } else {
      engine = this.named(loop, engineId);
      reason = `${engine.engine_id} as you chose`;
    }
    let model: string | null;
    if (wantedModel === undefined || wantedModel === '') {
      model = LoopSelector.entry(engine, effort).model ?? engine.default_model;
    } else if (loop.tier === 'local') {
      model = wantedModel;
      reason += `, on ${wantedModel} as you chose`;
    } else {
      const byModel = engine.efforts.find((entry) => entry.model === wantedModel);
      if (byModel === undefined) {
        const models = [...new Set(engine.efforts.map((entry) => entry.model).filter((name): name is string => name !== null))];
        throw new SelectionError(
          models.length === 0
            ? `${engine.engine_id} does not take a model by name; its effort chooses the model`
            : `${engine.engine_id} has no model ${wantedModel}; its models are ${models.join(', ')}`,
        );
      }
      effort = byModel.effort;
      effortSource = 'model';
      model = wantedModel;
      reason += `, on ${wantedModel}, which is its ${effort} effort`;
    }
    const entry = LoopSelector.entry(engine, effort);
    const turns = LoopSelector.turns(engine, entry.argv, request);
    return {
      loop: loop.loop,
      tier: loop.tier,
      effort,
      effortSource,
      engine,
      model,
      argv: turns.argv,
      ...(turns.maxTurns === undefined ? {} : { maxTurns: turns.maxTurns }),
      maxTurnsSource: turns.source,
      reason: `${reason}; effort ${effort} (${effortSource === 'auto' ? `auto, attempt ${request.attempt}` : effortSource === 'model' ? 'set by the model' : 'as you chose'}), which it achieves as ${entry.achieved}${entry.notes ? ` (${entry.notes})` : ''}`,
    };
  }

  private named(loop: CatalogueLoop, engineId: string): CatalogueEngine {
    const engine = loop.engines.find((candidate) => candidate.engine_id === engineId);
    if (engine === undefined) {
      throw new SelectionError(
        `${engineId} is not an engine of ${loop.loop}; its engines are ${loop.engines.map((candidate) => candidate.engine_id).join(', ')}`,
      );
    }
    if (engine.repealed) {
      throw new SelectionError(`${engineId} is repealed by the canon (8.b): it is listed, but it never runs`);
    }
    if (!engine.enabled) {
      throw new SelectionError(`${engineId} is switched off${LoopSelector.switchAdvice(engine)}`);
    }
    return engine;
  }

  private automatic(loop: CatalogueLoop, effort: Effort, request: SelectionRequest): [CatalogueEngine, string] {
    const enabled = (loop.by_effort[effort] ?? [])
      .map((choice) => ({ choice, engine: loop.engines.find((candidate) => candidate.engine_id === choice.engine_id) }))
      .filter(
        (pair): pair is { choice: EffortChoice; engine: CatalogueEngine } =>
          pair.engine !== undefined && pair.engine.enabled && !pair.engine.repealed,
      );
    if (enabled.length === 0) {
      throw new SelectionError(`no engine of ${loop.loop} that is switched on can run at ${effort}`);
    }
    if (loop.tier === 'paid') {
      const preferred = enabled.find((pair) => pair.engine.engine_id === this.catalogue.paid_default_engine);
      if (preferred !== undefined) {
        return [preferred.engine, `auto: ${preferred.engine.engine_id}, the declared paid default (8.b)`];
      }
    }
    const exact = enabled.filter((pair) => pair.choice.achieved === effort);
    let group = exact.length > 0 ? exact : enabled;
    const why: string[] = [exact.length > 0 ? `achieves ${effort}` : `nothing achieves ${effort} exactly, so the nearest`];
    if (loop.tier === 'local') {
      const resident = group.filter((pair) => {
        const model = pair.choice.model ?? pair.engine.default_model;
        return model !== null && request.resident.some((name) => ModelName.same(name, model));
      });
      if (resident.length > 0) {
        group = resident;
        why.push('its model is already loaded in Ollama');
      }
    }
    if (
      this.catalogue.ladder.rotates_when_effort_rises &&
      request.previousEngine !== undefined &&
      request.effort === 'auto' &&
      request.attempt > 1 &&
      Efforts.rank(effort) > Efforts.rank(this.effortForAttempt(request.baseEffort, request.attempt - 1)) &&
      group.length > 1
    ) {
      group = group.filter((pair) => pair.engine.engine_id !== request.previousEngine);
      why.push(`the effort rose, so it rotates away from ${request.previousEngine}`);
    }
    const chosen = this.roundRobin(`${loop.loop}:${effort}`, group.map((pair) => pair.engine));
    return [chosen, `auto: ${chosen.engine_id} (${why.join('; ')}${group.length > 1 ? `; weighted round robin over ${group.length}` : ''})`];
  }

  /** vibey's smooth weighted round robin (ADR-0005): the heaviest current weight wins, then pays the total. */
  private roundRobin(key: string, engines: readonly CatalogueEngine[]): CatalogueEngine {
    const total = engines.reduce((sum, engine) => sum + Math.max(engine.base_weight, 0), 0);
    let best = engines[0] as CatalogueEngine;
    let bestWeight = Number.NEGATIVE_INFINITY;
    for (const engine of engines) {
      const name = `${key}:${engine.engine_id}`;
      const weight = (this.current.get(name) ?? 0) + Math.max(engine.base_weight, 0);
      this.current.set(name, weight);
      if (weight > bestWeight) {
        best = engine;
        bestWeight = weight;
      }
    }
    const name = `${key}:${best.engine_id}`;
    this.current.set(name, (this.current.get(name) as number) - total);
    return best;
  }

  /** How to switch an engine back on: an on-by-default engine is off only because its switch says so. */
  private static switchAdvice(engine: CatalogueEngine): string {
    if (engine.switch === null) {
      return '';
    }
    return engine.on_by_default
      ? `; it is on by default, so ${engine.switch} or vibey's [features] table switched it off`
      : `; switch it on with ${engine.switch}`;
  }

  private static entry(engine: CatalogueEngine, effort: Effort): EngineEffort {
    const entry = engine.efforts.find((candidate) => candidate.effort === effort);
    if (entry === undefined) {
      throw new SelectionError(`${engine.engine_id} lists no ${effort} effort`);
    }
    return entry;
  }

  /**
   * The turn budget, resolved once (contract "Turn budget precedence"): the task's own
   * `max_turns`, else the effort's projection, else the vibey.maxTurns setting. An engine
   * takes a turn limit only when its projection shows the flag; `--max-turns` is never
   * passed twice.
   */
  private static turns(
    engine: CatalogueEngine,
    argv: readonly string[],
    request: SelectionRequest,
  ): { argv: string[]; maxTurns?: number; source: Selection['maxTurnsSource'] } {
    const flag = engine.turns_flag;
    const withoutFlag: string[] = [];
    let projected: number | undefined;
    for (let index = 0; index < argv.length; index += 1) {
      if (argv[index] === flag) {
        projected = Number(argv[index + 1]);
        index += 1;
        continue;
      }
      withoutFlag.push(argv[index] as string);
    }
    const chosen: [number, Selection['maxTurnsSource']] | undefined =
      request.taskMaxTurns !== undefined
        ? [request.taskMaxTurns, 'task']
        : projected !== undefined
          ? [projected, 'effort']
          : request.settingMaxTurns !== undefined
            ? [request.settingMaxTurns, 'setting']
            : undefined;
    if (chosen === undefined) {
      return { argv: withoutFlag, source: 'none' };
    }
    if (flag === undefined) {
      return { argv: withoutFlag, source: 'not supported by this engine' };
    }
    return { argv: [...withoutFlag, flag, String(chosen[0])], maxTurns: chosen[0], source: chosen[1] };
  }
}

/** The catalogue from vibey, or the degraded sovereign default with a notice that says why. */
export class CatalogueSource {
  constructor(
    private readonly loops: (() => Promise<unknown>) | undefined,
    private readonly parser: CatalogueParserInterface,
    private readonly model: string,
  ) {}

  async load(): Promise<Catalogue> {
    const fallback = `The extension runs sovereignloop with ${LocalRunners.FAMILY.default.name} on ${this.model} and effort auto.`;
    if (this.loops === undefined) {
      return DegradedCatalogue.sovereign(this.model, `vibey was not found, so the loop and model picker is limited. ${fallback} Install vibey, or set vibey.cliPath.`);
    }
    try {
      return this.parser.parse(await this.loops());
    } catch (error) {
      return DegradedCatalogue.sovereign(this.model, `${(error as Error).message} ${fallback}`);
    }
  }
}
