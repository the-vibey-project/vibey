// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Every value the extension acts on is a declared setting (sub-doctrine 12.c), resolved here
 * the same way for the editor and for the headless CLI: an explicit setting or flag wins,
 * then the family's environment variable (VIBEY_OLLAMA_URL, VIBEY_OLLAMA_MODEL,
 * VIBEY_STORM_HOME), then the default. `DEFAULT_SETTINGS` mirrors package.json's
 * `contributes.configuration`, and a unit test holds the two equal. Declared by
 * `interfaces/settings-interface.ts`.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import type {
  ExecutableLocatorInterface,
  LocatedExecutable,
  RawSettings,
  ResolvedSettings,
  SettingsResolverInterface,
} from './interfaces/settings-interface';
import type { Environ, PlatformStorageInterface } from './interfaces/storage-interface';
import { OllamaEndpoint } from './ollama';
import { StormHome } from './storage';

export class Defaults {
  /** The model qwenloop defaults to (`DEFAULT_ENDPOINT_MODEL`), and this era's default (8.d). */
  static readonly MODEL = 'gpt-oss:20b';

  static readonly SETTINGS: RawSettings = {
    cliPath: '',
    qwenloopPath: '',
    ollamaPath: '',
    gitPath: '',
    ollamaUrl: '',
    ollamaAppPath: '/Applications/Ollama.app',
    model: '',
    maxTurns: 0,
    effort: 'standard',
    contextWindow: 32768,
    runInPlace: false,
    baseRef: '',
    stormHome: '',
    modelLockPath: '',
    maxConcurrentRuns: 1,
    refreshSeconds: 30,
    pollMilliseconds: 500,
    stuckHintMinutes: 5,
    desktopNotifications: false,
    environmentAllow: [],
  };

  /** The declared minimum of each numeric setting; a smaller value is raised to it. */
  static readonly MINIMUMS: Readonly<Partial<Record<keyof RawSettings, number>>> = {
    maxTurns: 0,
    contextWindow: 1024,
    maxConcurrentRuns: 1,
    refreshSeconds: 5,
    pollMilliseconds: 100,
    stuckHintMinutes: 5,
  };
}

export class SettingsResolver implements SettingsResolverInterface {
  /** Where the extension keeps its own records, inside the storm home. */
  static readonly STATE_DIRECTORY = '.vibey-vscode';
  /** The model lock's default name inside the storm home. */
  static readonly LOCK_DIRECTORY = '.ollama-lock';

  constructor(
    private readonly environ: Environ,
    private readonly platform: PlatformStorageInterface,
  ) {}

  resolve(partial: Partial<RawSettings>): ResolvedSettings {
    const raw: RawSettings = { ...Defaults.SETTINGS, ...partial };
    const [ollamaRoot, ollamaSource] = this.layered(raw.ollamaUrl, 'VIBEY_OLLAMA_URL', OllamaEndpoint.DEFAULT_ROOT, 'vibey.ollamaUrl');
    const [model, modelSource] = this.layered(raw.model, 'VIBEY_OLLAMA_MODEL', Defaults.MODEL, 'vibey.model');
    const stormHome = new StormHome(raw.stormHome, this.environ, this.platform).resolve();
    const lock = raw.modelLockPath.trim();
    const maxTurns = SettingsResolver.atLeast(raw, 'maxTurns');
    return {
      raw,
      ollama: new OllamaEndpoint(ollamaRoot),
      ollamaSource,
      model,
      modelSource,
      stormHome,
      stateDir: path.join(stormHome.path, SettingsResolver.STATE_DIRECTORY),
      modelLockPath: lock ? path.resolve(lock) : path.join(stormHome.path, SettingsResolver.LOCK_DIRECTORY),
      ...(maxTurns > 0 ? { maxTurns } : {}),
      contextWindow: SettingsResolver.atLeast(raw, 'contextWindow'),
      effort: raw.effort.trim(),
      runInPlace: raw.runInPlace,
      baseRef: raw.baseRef.trim(),
      maxConcurrentRuns: SettingsResolver.atLeast(raw, 'maxConcurrentRuns'),
      refreshMs: SettingsResolver.atLeast(raw, 'refreshSeconds') * 1000,
      pollMs: SettingsResolver.atLeast(raw, 'pollMilliseconds'),
      stuckHintMs: SettingsResolver.atLeast(raw, 'stuckHintMinutes') * 60_000,
      desktopNotifications: raw.desktopNotifications,
      environmentAllow: raw.environmentAllow.map((entry) => entry.trim()).filter((entry) => entry !== ''),
    };
  }

  /** The setting when set, else the environment variable when set, else the default. */
  private layered(setting: string, variable: string, fallback: string, key: string): [string, string] {
    if (setting.trim()) {
      return [setting.trim(), `the ${key} setting`];
    }
    const declared = this.environ[variable]?.trim();
    if (declared) {
      return [declared, variable];
    }
    return [fallback, 'the default'];
  }

  /** A whole number no smaller than the declared minimum; not a number means the default. */
  private static atLeast(raw: RawSettings, key: keyof RawSettings): number {
    const minimum = Defaults.MINIMUMS[key] as number;
    const value = Math.floor(Number(raw[key]));
    return Math.max(minimum, Number.isFinite(value) ? value : Number(Defaults.SETTINGS[key]));
  }
}

export class ExecutableLocator implements ExecutableLocatorInterface {
  constructor(
    private readonly environ: Environ,
    private readonly isExecutable: (candidate: string) => boolean = ExecutableLocator.executableFile,
  ) {}

  locate(name: string, declared: string): LocatedExecutable {
    const wanted = declared.trim();
    if (wanted.includes('/')) {
      const absolute = path.resolve(wanted);
      return this.isExecutable(absolute)
        ? { path: absolute, source: 'the setting' }
        : { source: 'the setting', error: `${absolute} is not an executable file` };
    }
    const program = wanted || name;
    const source = wanted ? 'the setting, found on PATH' : 'PATH';
    for (const directory of (this.environ.PATH ?? '').split(path.delimiter)) {
      if (!directory) {
        continue;
      }
      const candidate = path.join(directory, program);
      if (this.isExecutable(candidate)) {
        return { path: candidate, source };
      }
    }
    return { source, error: `${program} was not found on PATH` };
  }

  /** A regular file this process may execute. */
  static executableFile(candidate: string): boolean {
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return fs.statSync(candidate).isFile();
    } catch {
      return false;
    }
  }
}
