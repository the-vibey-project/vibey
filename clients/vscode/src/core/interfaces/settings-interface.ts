// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Every declared setting, as the editor (or the headless CLI's flags) hands it over, and resolved. */
import type { Effort, EffortSetting, LoopName } from './catalogue-interface';
import type { OllamaEndpointInterface } from './ollama-interface';
import type { ResolvedHome } from './storage-interface';

/** One field per `vibey.*` key in package.json's `contributes.configuration`. */
export interface RawSettings {
  readonly cliPath: string;
  readonly qwenloopPath: string;
  readonly ollamaPath: string;
  readonly gitPath: string;
  readonly vibeySkillsPath: string;
  readonly ollamaUrl: string;
  readonly ollamaAppPath: string;
  readonly model: string;
  readonly loop: string;
  readonly effort: string;
  readonly baseEffort: string;
  readonly engine: string;
  readonly maxTurns: number;
  readonly contextWindow: number;
  readonly runInPlace: boolean;
  readonly baseRef: string;
  readonly stormHome: string;
  readonly modelLockPath: string;
  readonly maxConcurrentRuns: number;
  readonly refreshSeconds: number;
  readonly pollMilliseconds: number;
  readonly stuckHintMinutes: number;
  readonly forceStopAfterSeconds: number;
  readonly lanesRecentMinutes: number;
  readonly skillsBudget: number;
  readonly budgetInputTokensPerTurn: number;
  readonly budgetOutputTokensPerTurn: number;
  readonly desktopNotifications: boolean;
  readonly environmentAllow: readonly string[];
}

export interface ResolvedSettings {
  readonly raw: RawSettings;
  readonly ollama: OllamaEndpointInterface;
  /** Where the address came from: the setting, VIBEY_OLLAMA_URL, or the default. */
  readonly ollamaSource: string;
  readonly model: string;
  readonly modelSource: string;
  readonly stormHome: ResolvedHome;
  /** `<storm home>/.vibey-vscode`: run records, per-run plans and configs, batch journals. */
  readonly stateDir: string;
  readonly modelLockPath: string;
  /** The last word on a turn limit: a task's own, then the effort's, come first. */
  readonly maxTurns?: number;
  readonly contextWindow: number;
  readonly loop: LoopName;
  readonly effort: EffortSetting;
  readonly baseEffort: Effort;
  readonly engine: string;
  readonly runInPlace: boolean;
  readonly baseRef: string;
  readonly maxConcurrentRuns: number;
  readonly refreshMs: number;
  readonly pollMs: number;
  readonly stuckHintMs: number;
  readonly forceStopAfterMs: number;
  readonly lanesRecentMs: number;
  readonly skillsBudget: number;
  /** A projection's tokens per turn, until this machine has measured an engine's own. */
  readonly budgetPerTurn: { readonly input: number; readonly output: number };
  readonly desktopNotifications: boolean;
  readonly environmentAllow: readonly string[];
}

export interface SettingsResolverInterface {
  resolve(raw: Partial<RawSettings>): ResolvedSettings;
}

export interface LocatedExecutable {
  readonly path?: string;
  /** How it was found: the setting, or PATH. */
  readonly source: string;
  readonly error?: string;
}

export interface ExecutableLocatorInterface {
  locate(name: string, declared: string): LocatedExecutable;
}
