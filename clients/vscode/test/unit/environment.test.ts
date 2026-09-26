// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import {
  ChildEnvironment,
  EnvironmentAllowList,
  FilteredEnvironment,
  ForbiddenEnvironment,
} from '../../src/core/environment';
import { fixture } from './helpers';

/** An editor environment holding everything vibey forbids a model-driven process. */
const editor = {
  PATH: '/usr/bin',
  HOME: '/home/me',
  USER: 'me',
  LANG: 'en_US.UTF-8',
  LC_ALL: 'en_US.UTF-8',
  TMPDIR: '/var/scratch',
  SHELL: '/bin/zsh',
  TERM: 'xterm',
  VIBEY_PG_URL: 'postgresql://vibey:secret@localhost/vibey',
  VIBEY_API_TOKEN: 'tok',
  PGPASSWORD: 'secret',
  PGHOST: '/run/pg',
  MY_DSN: 'x',
  APP_DATABASE_URL: 'x',
  SMTP_PASSWORD: 'x',
  GITHUB_TOKEN: 'gh',
  ANTHROPIC_API_KEY: 'sk-ant',
  QWENLOOP_API_KEY: 'k',
  GIT_DIR: '/elsewhere/.git',
  UNSET: undefined,
};

/** Whatever any allow-list says, these never reach a model-driven process. */
function assertClean(environment: Record<string, string>): void {
  for (const [name, value] of Object.entries(environment)) {
    expect(name.startsWith('VIBEY_'), name).toBe(false);
    expect(name.startsWith('PG'), name).toBe(false);
    expect(/^\s*postgres(ql)?:\/\//i.test(value), `${name} carries a database address`).toBe(false);
  }
}

describe('ForbiddenEnvironment', () => {
  it("forbids vibey's own names, libpq's, and anything shaped like a database credential", () => {
    const forbidden = ForbiddenEnvironment.MODEL_SESSION;
    for (const name of ['VIBEY_PG_URL', 'PGPASSWORD', 'MY_DSN', 'APP_DATABASE_URL', 'SMTP_PASSWORD', 'X_PASSWD']) {
      expect(forbidden.forbids(name), name).toBe(true);
    }
    expect(forbidden.forbids('PATH')).toBe(false);
    expect(forbidden.forbidsPrefix('VIB')).toBe(true);
    expect(forbidden.forbidsPrefix('VIBEY_X')).toBe(true);
    expect(forbidden.forbidsPrefix('MY_PASSWORD_')).toBe(true);
    expect(forbidden.forbidsPrefix('CLAUDELOOP_')).toBe(false);
  });
});

describe('EnvironmentAllowList', () => {
  it('admits the basics and LC_*, and nothing forbidden', () => {
    const allow = EnvironmentAllowList.MODEL_BASICS;
    expect(allow.admits('PATH')).toBe(true);
    expect(allow.admits('LC_CTYPE')).toBe(true);
    expect(allow.admits('GITHUB_TOKEN')).toBe(false);
    expect(allow.admits('VIBEY_PG_URL')).toBe(false);
  });

  it('extends with names and prefixes, and refuses any that could admit a forbidden name', () => {
    const extended = EnvironmentAllowList.MODEL_BASICS.extended([' GITHUB_TOKEN ', 'CLAUDELOOP_*'], 'test');
    expect(extended.admits('GITHUB_TOKEN')).toBe(true);
    expect(extended.admits('CLAUDELOOP_PROFILE')).toBe(true);
    expect(() => EnvironmentAllowList.MODEL_BASICS.extended(['VIBEY_PG_URL'], 'the setting')).toThrow(
      'the setting: VIBEY_PG_URL can never be passed',
    );
    expect(() => EnvironmentAllowList.MODEL_BASICS.extended(['P*'], 'the setting')).toThrow('P* can never be passed');
    expect(() => EnvironmentAllowList.MODEL_BASICS.extended(['*'], 'the setting')).toThrow('"*" is not an environment variable prefix');
    expect(() => EnvironmentAllowList.MODEL_BASICS.extended(['A-B*'], 'the setting')).toThrow('is not an environment variable prefix');
    expect(() => EnvironmentAllowList.MODEL_BASICS.extended(['9BAD'], 'the setting')).toThrow('is not an environment variable name');
  });
});

describe('ChildEnvironment', () => {
  it('builds from the allow-list and lays the overlay over it', () => {
    const built = new ChildEnvironment(EnvironmentAllowList.MODEL_BASICS, {
      QWENLOOP_CONFIG: '/home/me/run/qwenloop.toml',
      OLLAMA_HOST: 'http://127.0.0.1:11434',
    }).build(editor);
    expect(Object.keys(built).sort()).toEqual(
      ['HOME', 'LANG', 'LC_ALL', 'OLLAMA_HOST', 'PATH', 'QWENLOOP_CONFIG', 'SHELL', 'TERM', 'TMPDIR', 'USER'].sort(),
    );
    assertClean(built);
  });

  it("keeps every catalogue engine's own names while never passing a VIBEY_*, PG* or database address", () => {
    const catalogue = JSON.parse(fixture('vibey-loops.json')) as {
      loops: { engines: { engine_id: string; env: { auth: string[]; passthrough: string[] } }[] }[];
    };
    const hostile = {
      ...editor,
      ANTHROPIC_BASE_URL: 'postgres://db.internal/prod',
      CLAUDE_CONFIG_DIR: '/home/me/.claude',
      GPTOSSLOOP_API_KEY: 'g',
      GPTOSSLOOP_BASE_URL: 'postgres://db.internal/prod',
    };
    for (const engine of catalogue.loops.flatMap((loop) => loop.engines)) {
      const allow = EnvironmentAllowList.MODEL_BASICS.extended([...engine.env.auth, ...engine.env.passthrough], engine.engine_id);
      const built = new ChildEnvironment(allow).build(hostile);
      assertClean(built);
      if (engine.engine_id === 'claudeloop') {
        expect(built.ANTHROPIC_API_KEY).toBe('sk-ant');
        expect(built.CLAUDE_CONFIG_DIR).toBe('/home/me/.claude');
        expect(built.ANTHROPIC_BASE_URL).toBeUndefined();
      }
      // The two names of the local runner each get their own settings, never the other's.
      if (engine.engine_id === 'gptossloop') {
        expect(built.GPTOSSLOOP_API_KEY).toBe('g');
        expect(built.GPTOSSLOOP_BASE_URL).toBeUndefined();
        expect(built.QWENLOOP_API_KEY).toBeUndefined();
      }
      if (engine.engine_id === 'qwenloop') {
        expect(built.QWENLOOP_API_KEY).toBe('k');
        expect(built.GPTOSSLOOP_API_KEY).toBeUndefined();
      }
    }
  });

  it('refuses a forbidden overlay name, and an overlay value that is a database address', () => {
    expect(() => new ChildEnvironment(EnvironmentAllowList.MODEL_BASICS, { PGHOST: 'x' })).toThrow('PGHOST can never be passed');
    expect(() => new ChildEnvironment(EnvironmentAllowList.MODEL_BASICS, { QWENLOOP_BASE_URL: 'PostgreSQL://x' })).toThrow(
      'holds a database address',
    );
  });
});

describe('FilteredEnvironment', () => {
  it('passes everything but the forbidden names, for programs no model drives', () => {
    const built = new FilteredEnvironment(ForbiddenEnvironment.GIT_PLUMBING).build(editor);
    expect(built.GIT_DIR).toBeUndefined();
    expect(built.VIBEY_PG_URL).toBe(editor.VIBEY_PG_URL);
    expect('UNSET' in built).toBe(false);
  });
});
