// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The environment a model-driven process receives is built from an allow-list, never copied.
 *
 * qwenloop runs shell commands a model chose, so whatever reaches it reaches the model. The
 * editor's environment can hold vibey's queue and ledger DSN (`VIBEY_PG_URL`), libpq's
 * variables and other credentials, and none of them may cross (vibey PR #1093, SECURITY.md).
 * The rule is the one `vibey.infrastructure.process.child_environment` enforces for engine
 * sessions: `MODEL_SESSION_FORBIDDEN` forbids every name starting `VIBEY_` or `PG`, and every
 * name containing `DSN`, `DATABASE_URL`, `PASSWORD` or `PASSWD`, whoever declares it. Nothing
 * can widen past it: not the `vibey.environment.allow` setting and not the extension's own
 * overlay. Declared by `interfaces/environment-interface.ts`.
 */
import type {
  ChildEnvironmentInterface,
  EnvironmentAllowListInterface,
  ForbiddenEnvironmentInterface,
  SourceEnvironment,
} from './interfaces/environment-interface';

const NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
/** A value that is a PostgreSQL address, whatever variable carries it. */
const DATABASE_ADDRESS = /^\s*postgres(?:ql)?:\/\//i;
const PREFIX_BODY = /^[A-Za-z0-9_]*$/;

export class ForbiddenEnvironment implements ForbiddenEnvironmentInterface {
  /** vibey's `MODEL_SESSION_FORBIDDEN`. */
  static readonly MODEL_SESSION = new ForbiddenEnvironment(
    ['VIBEY_', 'PG'],
    ['DSN', 'DATABASE_URL', 'PASSWORD', 'PASSWD'],
  );

  /** Git plumbing a hook may have exported: a git child would act on the wrong repository. */
  static readonly GIT_PLUMBING = new ForbiddenEnvironment(['GIT_'], []);

  constructor(
    private readonly prefixes: readonly string[],
    private readonly markers: readonly string[],
  ) {}

  forbids(name: string): boolean {
    return (
      this.prefixes.some((prefix) => name.startsWith(prefix)) ||
      this.markers.some((marker) => name.includes(marker))
    );
  }

  forbidsPrefix(prefix: string): boolean {
    return (
      this.prefixes.some((forbidden) => prefix.startsWith(forbidden) || forbidden.startsWith(prefix)) ||
      this.markers.some((marker) => prefix.includes(marker))
    );
  }
}

export class EnvironmentAllowList implements EnvironmentAllowListInterface {
  /**
   * What every qwenloop run receives: the basics a process needs to run and to find its
   * config, and nothing that names a server, a database or a credential.
   */
  static readonly MODEL_BASICS = new EnvironmentAllowList(
    ['PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR', 'TERM', 'LANG', 'LANGUAGE', 'TZ'],
    ['LC_'],
    ForbiddenEnvironment.MODEL_SESSION,
    'the qwenloop environment',
  );

  private readonly names: ReadonlySet<string>;

  constructor(
    names: readonly string[],
    private readonly prefixes: readonly string[],
    readonly forbidden: ForbiddenEnvironmentInterface,
    where: string,
  ) {
    for (const name of names) {
      if (!NAME.test(name)) {
        throw new Error(`${where}: ${JSON.stringify(name)} is not an environment variable name`);
      }
      if (forbidden.forbids(name)) {
        throw new Error(`${where}: ${name} can never be passed to a model-driven process`);
      }
    }
    for (const prefix of prefixes) {
      if (!PREFIX_BODY.test(prefix) || prefix === '') {
        throw new Error(`${where}: ${JSON.stringify(`${prefix}*`)} is not an environment variable prefix`);
      }
      if (forbidden.forbidsPrefix(prefix)) {
        throw new Error(`${where}: ${prefix}* can never be passed to a model-driven process`);
      }
    }
    this.names = new Set(names);
  }

  admits(name: string): boolean {
    if (this.forbidden.forbids(name)) {
      return false;
    }
    return this.names.has(name) || this.prefixes.some((prefix) => name.startsWith(prefix));
  }

  extended(entries: readonly string[], where: string): EnvironmentAllowList {
    const names = [...this.names];
    const prefixes = [...this.prefixes];
    for (const entry of entries) {
      const trimmed = entry.trim();
      if (trimmed.endsWith('*')) {
        prefixes.push(trimmed.slice(0, -1));
      } else {
        names.push(trimmed);
      }
    }
    return new EnvironmentAllowList(names, prefixes, this.forbidden, where);
  }
}

export class ChildEnvironment implements ChildEnvironmentInterface {
  private readonly overlay: Readonly<Record<string, string>>;

  constructor(
    private readonly allow: EnvironmentAllowListInterface,
    overlay: Readonly<Record<string, string>> = {},
  ) {
    for (const [name, value] of Object.entries(overlay)) {
      if (allow.forbidden.forbids(name)) {
        throw new Error(`${name} can never be passed to a model-driven process`);
      }
      if (DATABASE_ADDRESS.test(value)) {
        throw new Error(`${name} holds a database address, which is never passed to a model-driven process`);
      }
    }
    this.overlay = { ...overlay };
  }

  build(source: SourceEnvironment): Record<string, string> {
    const built: Record<string, string> = {};
    for (const [name, value] of Object.entries(source)) {
      // A database address never crosses, whatever name a passthrough glob admits it under.
      if (value !== undefined && this.allow.admits(name) && !DATABASE_ADDRESS.test(value)) {
        built[name] = value;
      }
    }
    return { ...built, ...this.overlay };
  }
}

/** The editor's environment minus a forbidden set: for programs no model drives (git, vibey). */
export class FilteredEnvironment implements ChildEnvironmentInterface {
  constructor(private readonly forbidden: ForbiddenEnvironmentInterface) {}

  build(source: SourceEnvironment): Record<string, string> {
    const built: Record<string, string> = {};
    for (const [name, value] of Object.entries(source)) {
      if (value !== undefined && !this.forbidden.forbids(name)) {
        built[name] = value;
      }
    }
    return built;
  }
}
