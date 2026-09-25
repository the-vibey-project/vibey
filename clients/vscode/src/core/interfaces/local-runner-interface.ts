// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The family's local runner (src/vibey_runners/qwen) under each name it ships as: who each
 * engine is, and the protocol they share (ADR-0060).
 */
import type { RawSettings } from './settings-interface';

/** The runner's own settings, each read as `<prefix>_<name>`. */
export type RunnerVariable = 'BASE_URL' | 'MODEL' | 'API_KEY' | 'CONFIG';

/** The `vibey.*` settings that name a runner's program. */
export type RunnerPathSetting = keyof Pick<RawSettings, 'gptossloopPath' | 'qwenloopPath'>;

/** One engine the runner package ships: `RunnerIdentity` in the runner's domain/config.py. */
export interface RunnerIdentity {
  /** The engine id vibey lists it under, which is also its program's name. */
  readonly name: string;
  /** The prefix of the settings it reads, without the underscore: `GPTOSSLOOP`, `QWENLOOP`. */
  readonly envPrefix: string;
  /**
   * The model the extension hands it when nothing names one: `vibey.model`, whose default is
   * this one. `null`: its own config chooses, and it is handed a model only when a person or
   * vibey names one (vibey never hands qwenloop this era's default).
   */
  readonly defaultModel: string | null;
  /** Whether vibey switches it on unless its switch says otherwise. */
  readonly onByDefault: boolean;
  /** The setting that names its program; empty means the first one on PATH. */
  readonly pathSetting: RunnerPathSetting;
}

/** What every engine of the runner shares, whatever it is called. */
export interface RunnerProtocolInterface {
  /** Where a run keeps its records, in the directory it runs in: never the work. */
  readonly stateDir: string;
  /** The line a run prints when it finished the task. */
  readonly doneMarker: string;
  /** The info string of the fenced block that carries a run's verdict. */
  readonly verdictFence: string;
  /** The exit code of a run that stopped at a turn boundary because it was asked to. */
  readonly exitWoundDown: number;
}

export interface LocalRunnersInterface {
  /** The engine the extension runs when nothing chooses another: gptossloop. */
  readonly default: RunnerIdentity;
  readonly all: readonly RunnerIdentity[];
  readonly protocol: RunnerProtocolInterface;
  /** The runner behind an engine id; undefined for an engine that is not this runner. */
  identify(engineId: string): RunnerIdentity | undefined;
  /** The name of one of a runner's own settings: `GPTOSSLOOP_BASE_URL`, `QWENLOOP_CONFIG`. */
  variable(runner: RunnerIdentity, name: RunnerVariable): string;
  /** The pattern that passes every one of a runner's settings through: `GPTOSSLOOP_*`. */
  passthrough(runner: RunnerIdentity): string;
}
