// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Work the extension keeps lives on durable storage, and nothing here puts it anywhere else.
 *
 * A port of `docs/plans/qwenstorm-3.0.0/tools/storm_durability.py` (sub-doctrine 10.h,
 * ADR-0057), so a task copy made from the editor and a lane made by the storm answer the
 * same questions the same way. On 2026-09-24 a reboot emptied the macOS temporary
 * directory in the middle of a storm and took every uncommitted lane with it; the gate
 * refuses, before anything is written, any path that resolves under a location the
 * operating system empties.
 *
 * One difference, on purpose: the extension's own `vibey.stormHome` setting (or the
 * headless CLI's `--storm-home`) is an explicit choice made in the tool itself, so it wins
 * over VIBEY_STORM_HOME, which wins over the platform default. The storm tools have no
 * such setting; their order is VIBEY_STORM_HOME, then storm.toml, then the default.
 * Declared by `interfaces/storage-interface.ts`.
 */
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type {
  DurabilityGateInterface,
  Environ,
  PlatformStorageInterface,
  ResolvedHome,
  StormHomeInterface,
  VolatileHit,
  VolatileLocationsInterface,
} from './interfaces/storage-interface';

/** Raised by the gate. `exitCode` is EX_CONFIG from sysexits.h, as the storm tools use. */
export class VolatileStorageError extends Error {
  static readonly EXIT_CODE = 78;

  constructor(readonly hits: readonly VolatileHit[]) {
    super(VolatileStorageError.describe(hits));
    this.name = 'VolatileStorageError';
  }

  private static describe(hits: readonly VolatileHit[]): string {
    const lines = ['refused: this work would be kept on storage the operating system empties.'];
    for (const hit of hits) {
      const shown = hit.resolved === hit.path ? hit.path : `${hit.path} -> ${hit.resolved}`;
      lines.push(`  ${hit.name}: ${shown}`);
      lines.push(`    under ${hit.location}: ${hit.why}`);
    }
    lines.push(
      'Choose a folder a restart keeps with the vibey.stormHome setting (or --storm-home, or VIBEY_STORM_HOME). ' +
        'Anything not committed there is lost at the next restart. Sub-doctrine 10.h; ADR-0057.',
    );
    return lines.join('\n');
  }
}

export abstract class PlatformStorage implements PlatformStorageInterface {
  abstract readonly name: string;
  protected abstract readonly fixed: ReadonlyArray<readonly [string, string]>;

  /** The same two session variables storm_durability.py reads. */
  private static readonly SESSION: ReadonlyArray<readonly [string, string]> = [
    ['TMPDIR', "this session's temporary directory ($TMPDIR)"],
    ['XDG_RUNTIME_DIR', "this session's runtime directory ($XDG_RUNTIME_DIR), gone at logout"],
  ];

  abstract defaultHome(environ: Environ): string;
  abstract runnerConfigPath(runner: string, environ: Environ): string;

  fixedVolatile(): ReadonlyArray<readonly [string, string]> {
    return this.fixed;
  }

  sessionVolatile(): ReadonlyArray<readonly [string, string]> {
    return PlatformStorage.SESSION;
  }

  /** The storage rules of `platform`; Windows is refused rather than guessed (#1097). */
  static detect(platform: string): PlatformStorage {
    if (platform === 'darwin') {
      return new MacStorage();
    }
    if (platform === 'win32') {
      throw new Error(
        'Windows is not supported yet (#1097). Its storage rules: %LOCALAPPDATA%\\vibey\\storm is durable; %TEMP% and %TMP% are volatile.',
      );
    }
    return new LinuxStorage();
  }

  protected static userHome(environ: Environ): string {
    return environ.HOME || os.homedir();
  }
}

/** macOS: work beside the main clone, and a temporary directory emptied at every boot. */
export class MacStorage extends PlatformStorage {
  readonly name = 'macos';
  protected readonly fixed: ReadonlyArray<readonly [string, string]> = [
    ['/tmp', 'emptied at boot on macOS'],
    ['/private/tmp', 'emptied at boot on macOS'],
    ['/var/tmp', "aged out by macOS's periodic clean-up"],
    ['/private/var/tmp', "aged out by macOS's periodic clean-up"],
    ['/var/folders', 'macOS per-user temporary storage, emptied at boot and by age'],
    ['/private/var/folders', 'macOS per-user temporary storage, emptied at boot and by age'],
  ];

  defaultHome(environ: Environ): string {
    return path.join(PlatformStorage.userHome(environ), 'git', 'vibey-storm');
  }

  /** platformdirs' user_config_path(runner) on macOS, and the file in it. */
  runnerConfigPath(runner: string, environ: Environ): string {
    return path.join(
      PlatformStorage.userHome(environ),
      'Library',
      'Application Support',
      runner,
      'config.toml',
    );
  }
}

/** Linux (Ubuntu LTS, Arch): the XDG data directory, and a tmpfs or cleaned temporary directory. */
export class LinuxStorage extends PlatformStorage {
  readonly name = 'linux';
  protected readonly fixed: ReadonlyArray<readonly [string, string]> = [
    ['/tmp', 'tmpfs, or emptied at boot by systemd-tmpfiles, on most Linux'],
    ['/var/tmp', 'aged out by systemd-tmpfiles (30 days by default)'],
    ['/dev/shm', 'memory-backed: gone at power-off'],
    ['/run/user', 'the per-user runtime directory: memory-backed, gone at logout'],
  ];

  defaultHome(environ: Environ): string {
    const data = LinuxStorage.xdg(environ.XDG_DATA_HOME);
    return data === undefined
      ? path.join(PlatformStorage.userHome(environ), '.local', 'share', 'vibey', 'storm')
      : path.join(data, 'vibey', 'storm');
  }

  /** platformdirs' user_config_path(runner) on Linux, and the file in it. */
  runnerConfigPath(runner: string, environ: Environ): string {
    const config = LinuxStorage.xdg(environ.XDG_CONFIG_HOME);
    return config === undefined
      ? path.join(PlatformStorage.userHome(environ), '.config', runner, 'config.toml')
      : path.join(config, runner, 'config.toml');
  }

  /** The XDG spec: a relative value is invalid and is ignored. */
  private static xdg(value: string | undefined): string | undefined {
    return value !== undefined && path.isAbsolute(value) ? value : undefined;
  }
}

/** Paths as the operating system will really store them: through every symlink that exists. */
export class ResolvedPath {
  /**
   * `raw` with `~` expanded, made absolute, and resolved through the symlinks of the part
   * that exists; the rest is kept as written, so a directory not yet made is judged by
   * where it would be made. Python's `Path.resolve(strict=False)`.
   */
  static of(raw: string, home: string = os.homedir()): string {
    const expanded = raw === '~' ? home : raw.startsWith('~/') ? path.join(home, raw.slice(2)) : raw;
    const absolute = path.resolve(expanded);
    const missing: string[] = [];
    let existing = absolute;
    while (!fs.existsSync(existing)) {
      missing.unshift(path.basename(existing));
      existing = path.dirname(existing);
    }
    return path.join(fs.realpathSync.native(existing), ...missing);
  }

  /** True when `candidate` is `root` or under it (POSIX paths; Windows is refused above). */
  static within(candidate: string, root: string): boolean {
    const relative = path.relative(root, candidate);
    return relative !== '..' && !relative.startsWith(`..${path.sep}`);
  }
}

export class VolatileLocations implements VolatileLocationsInterface {
  private readonly found: ReadonlyArray<readonly [string, string]>;

  constructor(environ: Environ, platform: PlatformStorageInterface) {
    const userHome = ResolvedPath.of(environ.HOME || os.homedir());
    const found = new Map<string, string>();
    for (const [raw, why] of platform.fixedVolatile()) {
      const where = ResolvedPath.of(raw);
      if (!found.has(where)) {
        found.set(where, why);
      }
    }
    for (const [name, why] of platform.sessionVolatile()) {
      const value = environ[name];
      if (!value) {
        continue;
      }
      const where = ResolvedPath.of(value);
      // TMPDIR=/ or TMPDIR=$HOME would make every path volatile, which says nothing about
      // any of them. Such a value is its own misconfiguration, not evidence about where
      // work is (the same rule as storm_durability.py).
      if (where === path.parse(where).root || ResolvedPath.within(userHome, where)) {
        continue;
      }
      if (!found.has(where)) {
        found.set(where, why);
      }
    }
    this.found = [...found.entries()].sort((left, right) => right[0].length - left[0].length);
  }

  roots(): ReadonlyArray<readonly [string, string]> {
    return this.found;
  }

  containing(candidate: string): readonly [string, string] | undefined {
    const where = ResolvedPath.of(candidate);
    return this.found.find(([root]) => ResolvedPath.within(where, root));
  }
}

export class StormHome implements StormHomeInterface {
  /** The environment variable the storm tools declare the home with. */
  static readonly ENV = 'VIBEY_STORM_HOME';

  constructor(
    private readonly setting: string,
    private readonly environ: Environ,
    private readonly platform: PlatformStorageInterface,
  ) {}

  resolve(): ResolvedHome {
    const setting = this.setting.trim();
    if (setting) {
      return { path: StormHome.absolute(setting, 'the vibey.stormHome setting', this.environ), source: 'the vibey.stormHome setting' };
    }
    const declared = this.environ[StormHome.ENV];
    if (declared) {
      return { path: StormHome.absolute(declared, StormHome.ENV, this.environ), source: StormHome.ENV };
    }
    return { path: this.platform.defaultHome(this.environ), source: `the ${this.platform.name} default` };
  }

  /**
   * A declared home must be absolute (or `~/...`): relative to what? The answer would change
   * with the directory a tool was started from, and two tools would disagree.
   */
  private static absolute(value: string, where: string, environ: Environ): string {
    const home = environ.HOME || os.homedir();
    const expanded = value === '~' ? home : value.startsWith('~/') ? path.join(home, value.slice(2)) : value;
    if (!path.isAbsolute(expanded)) {
      throw new Error(`${where} = ${JSON.stringify(value)} must be an absolute path (or ~/...)`);
    }
    return path.normalize(expanded);
  }
}

export class DurabilityGate implements DurabilityGateInterface {
  constructor(private readonly locations: VolatileLocationsInterface) {}

  inspect(named: Readonly<Record<string, string>>): readonly VolatileHit[] {
    const hits: VolatileHit[] = [];
    for (const [name, candidate] of Object.entries(named)) {
      const found = this.locations.containing(candidate);
      if (found !== undefined) {
        hits.push({
          name,
          path: candidate,
          resolved: ResolvedPath.of(candidate),
          location: found[0],
          why: found[1],
        });
      }
    }
    return hits;
  }

  enforce(named: Readonly<Record<string, string>>): void {
    const hits = this.inspect(named);
    if (hits.length > 0) {
      throw new VolatileStorageError(hits);
    }
  }
}
