// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Ollama: where it listens, what it serves, what it has loaded, and how to fetch a model. */

export interface OllamaEndpointInterface {
  /** The root form, no `/v1`: `http://127.0.0.1:11434`. What `VIBEY_OLLAMA_URL` holds. */
  readonly root: string;
  /** The OpenAI-compatible base URL qwenloop attaches to: `<root>/v1`. */
  readonly v1: string;
  url(path: string): string;
}

export interface LoadedModel {
  readonly name: string;
  /** The window the server loaded the model with, when this Ollama reports it. */
  readonly contextLength?: number;
}

export type ContextCheck = 'ok' | 'too-small' | 'unknown';

export interface OllamaStatus {
  readonly root: string;
  readonly reachable: boolean;
  readonly version?: string;
  /** Why the server did not answer. */
  readonly error?: string;
  readonly model: string;
  /** Undefined when the server did not answer, so nothing is known either way. */
  readonly modelPresent?: boolean;
  readonly modelSource?: string;
  readonly loaded?: LoadedModel;
  readonly contextWindow: number;
  readonly contextCheck: ContextCheck;
}

export interface OllamaProbeInterface {
  /** GET /api/version, as qwenloop's own probe asks it. */
  version(): Promise<{ readonly version?: string; readonly error?: string }>;
  /** Every model name the server offers: /v1/models, else /api/tags. */
  models(): Promise<{ readonly names: readonly string[]; readonly source: string }>;
  /** GET /api/ps: the models in memory now. */
  loaded(): Promise<readonly LoadedModel[]>;
  status(model: string, contextWindow: number): Promise<OllamaStatus>;
}

export type Platform = 'darwin' | 'linux' | 'other';

export interface OllamaAdviceInterface {
  /** One short line for a tree item or a status bar. */
  summary(status: OllamaStatus): string;
  /** What to do next, in words a beginner can follow; empty when nothing is needed. */
  advice(status: OllamaStatus, platform: Platform): readonly string[];
}

export interface PullUpdate {
  readonly status: string;
  /** Whole percent over every layer whose size is known, when any is. */
  readonly percent?: number;
  readonly completedBytes: number;
  readonly totalBytes: number;
  readonly done: boolean;
  readonly error?: string;
}

export interface PullProgressInterface {
  accept(line: string): PullUpdate;
}

export interface PullOutcome {
  readonly ok: boolean;
  readonly error?: string;
  /** The terminal command that does the same thing, shown when the pull fails. */
  readonly fallbackCommand: string;
}

export interface ModelPullerInterface {
  pull(model: string, onUpdate: (update: PullUpdate) => void, signal?: AbortSignal): Promise<PullOutcome>;
}

export interface OllamaStartFacts {
  readonly platform: Platform;
  readonly appPath: string;
  readonly appExists: boolean;
  /** `ollama` on PATH (or declared), when there is one. */
  readonly ollamaPath?: string;
  /** Linux: whether a systemd unit named `ollama` is installed. */
  readonly systemdUnit: boolean;
}

export type OllamaStartPlan =
  | { readonly kind: 'already-running'; readonly explanation: string }
  | {
      readonly kind: 'launch';
      readonly command: string;
      readonly args: readonly string[];
      readonly explanation: string;
    }
  | { readonly kind: 'terminal'; readonly commandLine: string; readonly explanation: string }
  | { readonly kind: 'impossible'; readonly explanation: string };

export interface OllamaStartPlannerInterface {
  plan(facts: OllamaStartFacts, reachable: boolean): OllamaStartPlan;
}

export interface OllamaStartFactsReaderInterface {
  read(appPath: string, ollamaPath: string | undefined): Promise<OllamaStartFacts>;
}
