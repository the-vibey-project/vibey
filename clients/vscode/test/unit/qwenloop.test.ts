// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { DegradedCatalogue, CatalogueParser } from '../../src/core/catalogue';
import { EngineCommand } from '../../src/core/engine-command';
import type { CatalogueEngine } from '../../src/core/interfaces/catalogue-interface';
import { QwenloopCommand, QwenloopRunConfig } from '../../src/core/qwenloop';
import { fixture } from './helpers';

const engines = new CatalogueParser().parse(JSON.parse(fixture('vibey-loops.json'))).loops.flatMap((loop) => loop.engines);
const engine = (id: string): CatalogueEngine => engines.find((candidate) => candidate.engine_id === id) as CatalogueEngine;

describe('QwenloopCommand', () => {
  const command = new QwenloopCommand('/bin/qwenloop');

  it("builds qwenloop's own command lines", () => {
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
  it('expands the run template exactly as argv.py builds it', () => {
    const qwenloop = new EngineCommand(engine('qwenloop'), '/bin/qwenloop');
    expect(qwenloop.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: ['--max-turns', '16'] })).toEqual({
      command: '/bin/qwenloop',
      args: ['run', '/p.md', '--run-id', 'r1', '--max-turns', '16', '--cwd', '/w'],
    });
    const cursor = new EngineCommand(engine('cursorloop'), '/bin/cursorloop');
    expect(cursor.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '--plan', '/p.md', '--run-id', 'r1', '--cwd', '/w']);
  });

  it('drops the --cwd pair where the engine takes none, even if a template carries it', () => {
    const codex = new EngineCommand({ ...engine('codexloop'), run: engine('qwenloop').run }, '/bin/codexloop');
    expect(codex.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '/p.md', '--run-id', 'r1']);
    const plain = new EngineCommand(engine('codexloop'), '/bin/codexloop');
    expect(plain.run({ plan: '/p.md', runId: 'r1', cwd: '/w', effortArgv: [] }).args).toEqual(['run', '/p.md', '--run-id', 'r1']);
  });

  it('builds stop and prompt from their templates, and says when an engine has none', () => {
    const qwenloop = new EngineCommand(engine('qwenloop'), '/bin/qwenloop');
    expect(qwenloop.stop('r1', '/w')?.args).toEqual(['stop', 'r1', '--cwd', '/w']);
    // vibey declares no prompt for a runner that ignores one: no follow-up is ever sent to it.
    expect(qwenloop.prompt('r1', 'x', '/w')).toBeUndefined();
    const prompted = new EngineCommand(
      { ...engine('qwenloop'), controls: { ...engine('qwenloop').controls, prompt: ['prompt', '{run_id}', '{text}', '--cwd', '{cwd}'] } },
      '/bin/qwenloop',
    );
    expect(prompted.prompt('r1', '-a dash', '/w')?.args).toEqual(['prompt', '--cwd', '/w', '--', 'r1', '-a dash']);
    const codex = new EngineCommand(engine('codexloop'), '/bin/codexloop');
    expect(codex.stop('r1', '/w')).toBeUndefined();
    expect(codex.prompt('r1', 'x', '/w')).toBeUndefined();
    const claude = new EngineCommand(engine('claudeloop'), '/bin/claudeloop');
    expect(claude.stop('r1', '/w')?.args).toEqual(['stop', '--run-id', 'r1', '--cwd', '/w']);
    const trailing = new EngineCommand({ ...engine('qwenloop'), controls: { stop: null, wind_down: null, prompt: ['prompt', '{text}', '--last'] } }, '/q');
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
    const headless = new EngineCommand({ ...engine('qwenloop'), run: ['run', '{plan}'] }, '/q');
    expect(() => headless.run({ plan: 'p', runId: 'r', cwd: 'w', effortArgv: [] })).toThrow('must start with {binary}');
  });
});
