// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** How the extension runs other programs: to completion, or as a child it watches. */

export type Environment = Readonly<Record<string, string>>;

export interface RunOptions {
  readonly cwd?: string;
  readonly env?: Environment;
  /** Kill the program with SIGTERM once this many milliseconds pass. */
  readonly timeoutMs?: number;
}

export interface CompletedProcess {
  /** The exit code, or null when the program never started or was killed by a signal. */
  readonly code: number | null;
  readonly signal: string | null;
  readonly stdout: string;
  readonly stderr: string;
  /** Why the program never started (ENOENT, EACCES), or that it timed out. */
  readonly error?: string;
  readonly timedOut: boolean;
}

export interface ProcessExit {
  readonly code: number | null;
  readonly signal: string | null;
  /** Set when the program could not be started at all. */
  readonly error?: string;
}

export interface ChildHandle {
  readonly pid: number | undefined;
  onStdout(listener: (text: string) => void): void;
  onStderr(listener: (text: string) => void): void;
  /** Resolves once, when the child exits or fails to start. */
  readonly exited: Promise<ProcessExit>;
  kill(signal?: NodeJS.Signals): boolean;
}

export interface ProcessRunnerInterface {
  run(command: string, args: readonly string[], options?: RunOptions): Promise<CompletedProcess>;
  spawn(command: string, args: readonly string[], options?: RunOptions): ChildHandle;
  /** Start a program that outlives this one (a server), or say why it could not start. */
  launchDetached(
    command: string,
    args: readonly string[],
    options?: RunOptions,
  ): Promise<{ readonly pid?: number; readonly error?: string }>;
}
