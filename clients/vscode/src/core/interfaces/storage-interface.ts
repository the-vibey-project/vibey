// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Where work is kept, and the gate that refuses places the operating system empties. */

export type Environ = Readonly<Record<string, string | undefined>>;

export interface PlatformStorageInterface {
  readonly name: string;
  /** Where storm work lives when nothing declares otherwise. */
  defaultHome(environ: Environ): string;
  /** Locations this OS empties, each with when and why. */
  fixedVolatile(): ReadonlyArray<readonly [string, string]>;
  /** Environment variables that name this session's own temporary directories. */
  sessionVolatile(): ReadonlyArray<readonly [string, string]>;
  /** Where qwenloop looks for its config file when QWENLOOP_CONFIG is unset. */
  qwenloopConfigPath(environ: Environ): string;
}

export interface VolatileLocationsInterface {
  roots(): ReadonlyArray<readonly [string, string]>;
  /** The volatile location `path` resolves under, and why; undefined when it is durable. */
  containing(path: string): readonly [string, string] | undefined;
}

export interface ResolvedHome {
  readonly path: string;
  /** What declared it: the setting, VIBEY_STORM_HOME, or the platform default. */
  readonly source: string;
}

export interface StormHomeInterface {
  resolve(): ResolvedHome;
}

export interface VolatileHit {
  readonly name: string;
  readonly path: string;
  readonly resolved: string;
  readonly location: string;
  readonly why: string;
}

export interface DurabilityGateInterface {
  inspect(named: Readonly<Record<string, string>>): readonly VolatileHit[];
  /** Returns when every named path is durable; otherwise throws `VolatileStorageError`. */
  enforce(named: Readonly<Record<string, string>>): void;
}
