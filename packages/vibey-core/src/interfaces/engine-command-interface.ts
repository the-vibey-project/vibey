// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** A loop engine's command lines and event file, from the templates `vibey loops --json` gives. */
import type { Invocation } from './qwenloop-interface';

export interface RunArguments {
  readonly plan: string;
  readonly runId: string;
  readonly cwd: string;
  /** The chosen effort's argv, turn budget already applied. */
  readonly effortArgv: readonly string[];
}

export interface EngineCommandInterface {
  run(args: RunArguments): Invocation;
  /** A control command, or undefined when this engine has none of that kind. */
  stop(runId: string, cwd: string): Invocation | undefined;
  prompt(runId: string, text: string, cwd: string): Invocation | undefined;
  eventsPath(cwd: string, runId: string): string;
  version(): Invocation;
}
