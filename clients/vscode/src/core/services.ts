// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The one place the core is put together, for the editor and for `vibey-vscode` alike, so the
 * two behave the same: same settings, same paths, same child environments, same journals.
 * Declared by `interfaces/services-interface.ts`.
 */
import { createHash } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { BatchRunner } from './batch';
import { BudgetGuard, BudgetStore, SpendLedger } from './budgets';
import { Capabilities, SkillsContext, SkillsMarketplace } from './capabilities';
import { CatalogueParser, CatalogueSource, LoopSelector } from './catalogue';
import { SlashArguments, SlashCommands } from './commands';
import { Doctor } from './doctor';
import { EngineCommand } from './engine-command';
import { FilteredEnvironment, ForbiddenEnvironment } from './environment';
import { GitClient } from './git';
import { NodeHttpClient } from './http-client';
import type { Catalogue, CatalogueEngine, LoopName } from './interfaces/catalogue-interface';
import type { HttpClientInterface } from './interfaces/http-client-interface';
import type { RunnerIdentity } from './interfaces/local-runner-interface';
import type { Platform } from './interfaces/ollama-interface';
import type { ProcessRunnerInterface } from './interfaces/process-runner-interface';
import type { RunRequest, RunServices } from './interfaces/run-interface';
import type { ServicesInterface, ServicesOptions } from './interfaces/services-interface';
import type { RawSettings, ResolvedSettings } from './interfaces/settings-interface';
import type { ClockInterface, IdSourceInterface } from './interfaces/support-interface';
import { JsonlJournal, JsonlTail } from './jsonl';
import { LaneTracker } from './lanes';
import { LocalRunners } from './local-runner';
import { ModelSlotLock } from './model-lock';
import { ModelPuller, OllamaStartFactsReader, OllamaStartPlanner } from './ollama-lifecycle';
import { OllamaAdvice, OllamaProbe } from './ollama';
import { NodeProcessRunner } from './process-runner';
import { QwenloopRunConfig } from './qwenloop';
import { RunHistory, TaskRun } from './run';
import { RunQueue } from './run-queue';
import { ExecutableLocator, SettingsResolver } from './settings';
import { DurabilityGate, PlatformStorage, VolatileLocations } from './storage';
import { HtmlText, RandomIds, SystemClock, TaskNaming } from './support';
import { TaskFolder } from './task-file';
import { GateAnswerPlanner, VibeyCli } from './vibey-cli';

export class CoreServices implements ServicesInterface {
  readonly settings: ResolvedSettings;
  readonly platform: Platform;
  readonly storage: PlatformStorage;
  readonly processes: ProcessRunnerInterface;
  readonly http: HttpClientInterface;
  readonly clock: ClockInterface;
  readonly ids: IdSourceInterface;
  readonly naming = new TaskNaming();
  readonly tail = new JsonlTail();
  readonly html = new HtmlText();
  readonly locator: ExecutableLocator;
  /** For programs no model drives (git, vibey, ollama): the editor's environment minus git plumbing. */
  readonly toolEnvironment: Record<string, string>;
  readonly gate: DurabilityGate;
  readonly probe: OllamaProbe;
  readonly advice = new OllamaAdvice();
  readonly puller: ModelPuller;
  readonly startPlanner = new OllamaStartPlanner();
  readonly startFacts: OllamaStartFactsReader;
  readonly git: GitClient;
  /** Undefined when no `vibey` can be found: the views say so. */
  readonly vibey: VibeyCli | undefined;
  readonly history: RunHistory;
  readonly budgets: BudgetStore;
  readonly spend: SpendLedger;
  readonly guard: BudgetGuard;
  readonly queue: RunQueue;
  readonly capabilities = new Capabilities();
  readonly marketplace = new SkillsMarketplace();
  readonly skills: SkillsContext | undefined;
  readonly answers = new GateAnswerPlanner();
  readonly slash = new SlashCommands();
  readonly slashArguments = new SlashArguments();
  /** The family's local runner under each of its names: gptossloop by default, and qwenloop (ADR-0064). */
  readonly runners = LocalRunners.FAMILY;
  private readonly catalogueSource: CatalogueSource;
  private catalogueLoad: Promise<Catalogue> | undefined;
  private selector: { catalogue: Catalogue; selector: LoopSelector } | undefined;

  constructor(private readonly options: ServicesOptions) {
    const environ = options.environ;
    this.storage = PlatformStorage.detect(options.platform);
    this.platform = options.platform === 'darwin' ? 'darwin' : options.platform === 'linux' ? 'linux' : 'other';
    this.settings = new SettingsResolver(environ, this.storage).resolve(options.raw);
    this.processes = options.processes ?? new NodeProcessRunner();
    this.http = options.http ?? new NodeHttpClient();
    this.clock = options.clock ?? new SystemClock();
    this.ids = options.ids ?? new RandomIds();
    this.locator = new ExecutableLocator(environ, options.isExecutable);
    this.toolEnvironment = new FilteredEnvironment(ForbiddenEnvironment.GIT_PLUMBING).build(environ);
    this.gate = new DurabilityGate(new VolatileLocations(environ, this.storage));
    this.probe = new OllamaProbe(this.http, this.settings.ollama);
    this.puller = new ModelPuller(this.http, this.settings.ollama);
    this.startFacts = new OllamaStartFactsReader(this.platform, fs.existsSync, this.processes);
    this.git = new GitClient(this.processes, this.locator.locate('git', this.settings.raw.gitPath).path ?? 'git', this.toolEnvironment);
    const vibey = this.locator.locate('vibey', this.settings.raw.cliPath).path;
    this.vibey = vibey === undefined ? undefined : new VibeyCli(this.processes, vibey, this.toolEnvironment);
    const state = this.settings.stateDir;
    this.history = new RunHistory(new JsonlJournal(path.join(state, 'runs.jsonl')), () => this.clock.now());
    this.budgets = new BudgetStore(state, new JsonlJournal(path.join(state, 'budget-journal.jsonl')), this.clock, this.ids, options.actor);
    this.spend = new SpendLedger(new JsonlJournal(path.join(state, 'spend.jsonl')), this.tail);
    this.guard = new BudgetGuard(this.budgets, this.spend, this.clock);
    this.queue = new RunQueue(this.settings.maxConcurrentRuns);
    const skills = this.locator.locate('vibey-skills', this.settings.raw.vibeySkillsPath).path;
    this.skills =
      skills === undefined
        ? undefined
        : new SkillsContext(this.processes, skills, this.toolEnvironment, path.join(state, 'skills'), this.settings.skillsBudget, this.ids);
    const loops = this.vibey;
    this.catalogueSource = new CatalogueSource(loops === undefined ? undefined : () => loops.loops(), new CatalogueParser(), this.settings.model);
  }

  /** `vibey loops --json`, read once and kept until `reload` is asked for. */
  catalogue(reload = false): Promise<Catalogue> {
    if (reload || this.catalogueLoad === undefined) {
      this.catalogueLoad = this.catalogueSource.load();
    }
    return this.catalogueLoad;
  }

  paidDeclared(): boolean {
    return this.budgets.paid() !== undefined;
  }

  async runServices(): Promise<RunServices> {
    const catalogue = await this.catalogue();
    if (this.selector === undefined || this.selector.catalogue !== catalogue) {
      this.selector = { catalogue, selector: new LoopSelector(catalogue) };
    }
    return {
      settings: this.settings,
      catalogue,
      selector: this.selector.selector,
      command: (engine) => this.command(engine),
      git: this.git,
      processes: this.processes,
      runConfig: new QwenloopRunConfig(),
      runners: this.runners,
      userConfig: (runner) => this.userConfig(runner),
      gate: this.gate,
      tail: this.tail,
      lockFor: (engine, tier) =>
        new ModelSlotLock(
          tier === 'local' ? this.settings.modelLockPath : path.join(this.settings.stateDir, 'locks', engine.engine_id),
          this.clock,
        ),
      clock: this.clock,
      ids: this.ids,
      naming: this.naming,
      history: this.history,
      paidDeclared: () => this.paidDeclared(),
      resident: async () => {
        try {
          return (await this.probe.loaded()).map((model) => model.name);
        } catch {
          return [];
        }
      },
      budgets: this.guard,
      spend: this.spend,
      environ: this.options.environ,
    };
  }

  /** Start a task: it waits its turn in the queue for its loop, and runs when the slot is free. */
  async start(request: RunRequest): Promise<TaskRun> {
    const run = new TaskRun(request, await this.runServices());
    this.queue.enqueue(request.loop, run);
    return run;
  }

  batch(): BatchRunner {
    return new BatchRunner({
      folder: new TaskFolder(),
      git: this.git,
      gate: this.gate,
      journal: (file) => new JsonlJournal(file),
      start: (request) => this.start(request),
      clock: this.clock,
      ids: this.ids,
      preflight: async () => {
        const status = await this.probe.status(this.settings.model, this.settings.contextWindow);
        if (this.settings.loop !== 'sovereignloop') {
          return undefined;
        }
        if (!status.reachable) {
          return `Ollama is not answering at ${status.root}: ${status.error}`;
        }
        return status.modelPresent === true ? undefined : `${this.settings.model} is not downloaded; run: ollama pull ${this.settings.model}`;
      },
    });
  }

  doctor(): Doctor {
    return new Doctor({
      settings: this.settings,
      platform: this.platform,
      gate: this.gate,
      locator: this.locator,
      processes: this.processes,
      environment: this.toolEnvironment,
      probe: this.probe,
      advice: this.advice,
      catalogue: () => this.catalogue(),
      environ: this.options.environ,
      forbidden: ForbiddenEnvironment.MODEL_SESSION,
      paidDeclared: () => this.paidDeclared(),
      runner: this.runners.default,
    });
  }

  lanes(catalogue: Catalogue): LaneTracker {
    const engines = new Map<string, CatalogueEngine>();
    for (const loop of catalogue.loops) {
      for (const engine of loop.engines) {
        engines.set(engine.state_dir, engines.get(engine.state_dir) ?? engine);
      }
    }
    return new LaneTracker(
      [...engines.values()].map((engine) => ({ engineId: engine.binary, stateDir: engine.state_dir, envelope: engine.events.envelope })),
      () => [this.settings.stormHome.path, ...this.options.workspaceRoots()],
      this.tail,
      () => this.clock.now().getTime(),
      this.settings.stuckHintMs,
      this.settings.lanesRecentMs,
    );
  }

  /** Where a batch of `directory` against `repository` keeps its journal, unless told otherwise. */
  journalFor(directory: string, repository: string): string {
    const key = createHash('sha256').update(`${path.resolve(directory)}\0${path.resolve(repository)}`).digest('hex').slice(0, 10);
    return path.join(this.settings.stateDir, 'batches', `${this.naming.slug(path.basename(path.resolve(directory)))}-${key}.jsonl`);
  }

  /** The loop a task runs in: the setting, sovereign by default. */
  loop(): LoopName {
    return this.settings.loop;
  }

  withSettings(raw: Partial<RawSettings>): CoreServices {
    return new CoreServices({ ...this.options, raw: { ...this.options.raw, ...raw } });
  }

  /** An engine's command lines; a local runner's program may be named by its own setting. */
  private command(engine: CatalogueEngine): EngineCommand | string {
    const runner = this.runners.identify(engine.engine_id);
    const declared = runner === undefined ? '' : this.settings.raw[runner.pathSetting];
    const located = this.locator.locate(engine.binary, declared);
    if (located.path !== undefined) {
      return new EngineCommand(engine, located.path);
    }
    const fix = runner === undefined
      ? 'Install it, or choose another engine.'
      : `It ships with vibey (pip install vibey-engine), or set vibey.${runner.pathSetting}.`;
    return `${engine.engine_id} cannot run: ${located.error}. ${fix}`;
  }

  /** The runner's own config file: its `<PREFIX>_CONFIG` when set, else where it looks by default. */
  private userConfig(runner: RunnerIdentity): { readonly path: string; readonly text: string } | undefined {
    const file = this.options.environ[this.runners.variable(runner, 'CONFIG')] || this.storage.runnerConfigPath(runner.name, this.options.environ);
    try {
      return { path: file, text: fs.readFileSync(file, 'utf8') };
    } catch {
      return undefined;
    }
  }
}
