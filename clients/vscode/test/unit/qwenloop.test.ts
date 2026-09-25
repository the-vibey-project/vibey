// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { DegradedCatalogue, CatalogueParser } from '../../src/core/catalogue';
import { EngineCommand } from '../../src/core/engine-command';
import type { CatalogueEngine } from '../../src/core/interfaces/catalogue-interface';
import { LocalRunners } from '../../src/core/local-runner';
import { QwenloopCommand, QwenloopRunConfig } from '../../src/core/qwenloop';
import { fixture } from './helpers';

const engines = new CatalogueParser().parse(JSON.parse(fixture('vibey-loops.json'))).loops.flatMap((loop) => loop.engines);
const engine = (id: string): CatalogueEngine => engines.find((candidate) => candidate.engine_id === id) as CatalogueEngine;

describe('LocalRunners', () => {
  it('knows the runner under both names it ships as, each with its own settings (ADR-0062)', () => {
    const runners = LocalRunners.FAMILY;
    expect(runners.default).toBe(LocalRunners.GPTOSSLOOP);
    expect(runners.all.map((runner) => runner.name)).toEqual(['gptossloop', 'qwenloop']);
    expect(runners.identify('gptossloop')).toBe(LocalRunners.GPTOSSLOOP);
    expect(runners.identify('qwenloop')).toBe(LocalRunners.QWENLOOP);
    expect(runners.identify('claudeloop-local')).toBeUndefined();
    expect(runners.variable(LocalRunners.GPTOSSLOOP, 'BASE_URL')).toBe('GPTOSSLOOP_BASE_URL');
    expect(runners.variable(LocalRunners.GPTOSSLOOP, 'MODEL')).toBe('GPTOSSLOOP_MODEL');
    expect(runners.variable(LocalRunners.GPTOSSLOOP, 'API_KEY')).toBe('GPTOSSLOOP_API_KEY');
    expect(runners.variable(LocalRunners.QWENLOOP, 'CONFIG')).toBe('QWENLOOP_CONFIG');
    expect(runners.passthrough(LocalRunners.GPTOSSLOOP)).toBe('GPTOSSLOOP_*');
    expect(runners.passthrough(LocalRunners.QWENLOOP)).toBe('QWENLOOP_*');
    expect(LocalRunners.GPTOSSLOOP).toMatchObject({ defaultModel: 'gpt-oss:20b', onByDefault: true, pathSetting: 'gptossloopPath' });
    expect(LocalRunners.QWENLOOP).toMatchObject({ defaultModel: null, onByDefault: false, pathSetting: 'qwenloopPath' });
    // One protocol, whichever name runs.
    expect(runners.protocol).toEqual({ stateDir: '.qwenloop', doneMarker: 'QWENLOOP_TASK_FULLY_COMPLETE', verdictFence: 'qwenloop-verdict', exitWoundDown: 75 });
    expect(QwenloopCommand.DONE_MARKER).toBe(runners.protocol.doneMarker);
    expect(QwenloopCommand.EXIT_WOUND_DOWN).toBe(runners.protocol.exitWoundDown);
  });

  it('is configurable: another table, another default, another protocol', () => {
    const protocol = { stateDir: '.elsewhere', doneMarker: 'DONE', verdictFence: 'v', exitWoundDown: 3 };
    const qwenFirst = new LocalRunners([LocalRunners.QWENLOOP, LocalRunners.GPTOSSLOOP], protocol);
    expect(qwenFirst.default).toBe(LocalRunners.QWENLOOP);
    expect(qwenFirst.protocol).toBe(protocol);
    expect(new LocalRunners([LocalRunners.GPTOSSLOOP]).protocol).toBe(LocalRunners.PROTOCOL);
  });
});

describe('QwenloopCommand', () => {
  const command = new QwenloopCommand('/bin/qwenloop');

  it("builds the runner's own command lines", () => {
    expect(
      command.run({
        planPath: '/p.md',
        runId: 'r',
        cwd: '/w',
        baseUrl: 'http://h/v1',
        model: 'gpt-oss:20b',
        effort: 'standard',
        desktopNotifications: false,
      }).args,
    ).toEqual(['run', '/p.md', '--run-id', 'r', '--cwd', '/w', '--backend', 'openai-compat', '--base-url', 'http://h/v1', '--model', 'gpt-oss:20b', '--no-desktop-notifications', '--effort', 'standard']);
    expect(
      command.run({ planPath: '/p.md', runId: 'r', cwd: '/w', baseUrl: 'u', model: 'm', effort: '', desktopNotifications: true }).args,
    ).toContain('--desktop-notifications');
    expect(command.prompt('r', '-dash first', '/w').args).toEqual(['prompt', '--cwd', '/w', '--', 'r', '-dash first']);
    expect(command.stop('r', '/w').args).toEqual(['stop', '--cwd', '/w', '--', 'r']);
    expect(command.version()).toEqual({ command: '/bin/qwenloop', args: ['--version'] });
  });
});

describe('QwenloopRunConfig', () => {
  const config = new QwenloopRunConfig();

  it("writes the run's window, and its turn limit when there is one", () => {
    expect(config.compose(undefined, { contextWindow: 65536 })).toBe(
      '# Written by the vibey VS Code extension for one run. Safe to delete.\ncontext_window = 65536\n',
    );
    expect(config.compose(undefined, { contextWindow: 32768.7, maxTurns: 60 })).toContain('context_window = 32768\nmax_turns = 60\n');
  });

  it("keeps the person's own config, replacing only the top-level keys the run sets", () => {
    const user = ['context_window = 8192', 'max_turns = 12', 'idle_timeout_seconds = 60', '', '[tools]', 'context_window = 5', 'max_turns = 5'].join('\n');
    const window = config.compose(user, { contextWindow: 65536 });
    expect(window).toContain('context_window = 65536');
    expect(window).not.toContain('context_window = 8192');
    expect(window).toContain('max_turns = 12');
    expect(window).toContain('[tools]\ncontext_window = 5\nmax_turns = 5');
    const both = config.compose(user, { contextWindow: 65536, maxTurns: 40 });
    expect(both).not.toContain('max_turns = 12');
    expect(both).toContain('max_turns = 40');
  });
});

describe('EngineCommand', () => {
  it('expands the run template exactly as argv.py builds it, for either name of the runner', () => {
    const gptossloop = new EngineCommand(engine('gptossloop'), '/bin/gptossloop');
    expect(gptossloop.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: ['--max-turns', '16'] })).toEqual({
      command: '/bin/gptossloop',
      args: ['run', '/p.md', '--run-id', 'r1', '--max-turns', '16', '--cwd', '/w'],
    });
    const qwenloop = new EngineCommand(engine('qwenloop'), '/bin/qwenloop');
    expect(qwenloop.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '/p.md', '--run-id', 'r1', '--cwd', '/w']);
    // The degraded catalogue's template carries {plan_flag?}; the runner takes no plan flag.
    const degraded = new EngineCommand(DegradedCatalogue.sovereign('gpt-oss:20b', 'n').loops[0]?.engines[0] as CatalogueEngine, '/bin/gptossloop');
    expect(degraded.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '/p.md', '--run-id', 'r1', '--cwd', '/w']);
    const cursor = new EngineCommand(engine('cursorloop'), '/bin/cursorloop');
    expect(cursor.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '--plan', '/p.md', '--run-id', 'r1', '--cwd', '/w']);
  });

  it('drops the --cwd pair where the engine takes none, even if a template carries it', () => {
    const codex = new EngineCommand({ ...engine('codexloop'), run: engine('gptossloop').run }, '/bin/codexloop');
    expect(codex.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '/p.md', '--run-id', 'r1']);
    const plain = new EngineCommand(engine('codexloop'), '/bin/codexloop');
    expect(plain.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '/p.md', '--run-id', 'r1']);
  });

  it('builds stop and prompt from their templates, and says when an engine has none', () => {
    for (const name of ['gptossloop', 'qwenloop']) {
      const runner = new EngineCommand(engine(name), `/bin/${name}`);
      expect(runner.stop('r1', '/w')?.args).toEqual(['stop', 'r1', '--cwd', '/w']);
      expect(runner.prompt('r1', '-a dash', '/w')?.args).toEqual(['prompt', '--cwd', '/w', '--', 'r1', '-a dash']);
    }
    // vibey declares no prompt for an engine that ignores one: no follow-up is ever sent to it.
    const cursor = new EngineCommand(engine('cursorloop'), '/bin/cursorloop');
    expect(cursor.prompt('r1', 'x', '/w')).toBeUndefined();
    const codex = new EngineCommand(engine('codexloop'), '/bin/codexloop');
    expect(codex.stop('r1', '/w')?.args).toEqual(['stop', '--run-id', 'r1']);
    const claude = new EngineCommand(engine('claudeloop'), '/bin/claudeloop');
    expect(claude.stop('r1', '/w')?.args).toEqual(['stop', '--run-id', 'r1', '--cwd', '/w']);
    const trailing = new EngineCommand({ ...engine('gptossloop'), controls: { stop: null, wind_down: null, prompt: ['prompt', '{text}', '--last'] } }, '/q');
    expect(trailing.prompt('r', 't', '/w')?.args).toEqual(['prompt', '--', 't', '--last']);
  });

  it('finds the events file and the version', () => {
    const claude = new EngineCommand(engine('claudeloop'), '/bin/claudeloop');
    expect(claude.eventsPath('/w', 'r1')).toBe('/w/.claudeloop/runs/r1/events.jsonl');
    expect(claude.version()).toEqual({ command: '/bin/claudeloop', args: ['--version'] });
  });

  it('refuses a template it cannot fill, rather than guess', () => {
    const odd = new EngineCommand({ ...DegradedCatalogue.sovereign('m', 'n').loops[0]?.engines[0] as CatalogueEngine, run: ['{binary}', 'run', '{profile}'] }, '/q');
    expect(() => odd.run({ plan: 'p', runId: 'r', cwd: 'w', effortArgv: [] })).toThrow('the template placeholder {profile}');
    const headless = new EngineCommand({ ...engine('gptossloop'), run: ['run', '{plan}'] }, '/q');
    expect(() => headless.run({ plan: 'p', runId: 'r', cwd: 'w', effortArgv: [] })).toThrow('must start with {binary}');
  });
});
