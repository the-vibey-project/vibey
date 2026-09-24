// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** qwenloop as the extension drives it: its command lines and its per-run config file. */

export interface Invocation {
  readonly command: string;
  readonly args: readonly string[];
}

export interface QwenloopRunArguments {
  readonly planPath: string;
  readonly runId: string;
  readonly cwd: string;
  /** The OpenAI-compatible base URL, `/v1` included. */
  readonly baseUrl: string;
  readonly model: string;
  readonly effort: string;
  readonly desktopNotifications: boolean;
}

export interface QwenloopCommandInterface {
  run(options: QwenloopRunArguments): Invocation;
  /** `qwenloop prompt`: a follow-up message for a run that is still going. */
  prompt(runId: string, text: string, cwd: string): Invocation;
  /** `qwenloop stop`: finish the current turn, then end the run (exit 75). */
  stop(runId: string, cwd: string): Invocation;
  version(): Invocation;
}

export interface RunConfigValues {
  readonly contextWindow: number;
  /** Omitted: the user's own `max_turns`, else qwenloop's 40. */
  readonly maxTurns?: number;
}

export interface QwenloopRunConfigInterface {
  /**
   * The TOML a run is given through QWENLOOP_CONFIG: the user's own config file with the
   * run's `context_window` and `max_turns` in place of any the file sets.
   */
  compose(userConfig: string | undefined, values: RunConfigValues): string;
}
