// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import type { RawSettings } from '../../src/core/interfaces/settings-interface';
import { Defaults, ExecutableLocator, SettingsResolver } from '../../src/core/settings';
import { LinuxStorage, MacStorage } from '../../src/core/storage';
import { scratch } from './helpers';

const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'package.json'), 'utf8')) as {
  contributes: { configuration: { properties: Record<string, { default: unknown; minimum?: number }> } };
};
const keyOf = (field: string): string => (field === 'environmentAllow' ? 'vibey.environment.allow' : `vibey.${field}`);

describe('Defaults', () => {
  it('declares every setting package.json declares, with the same default (12.c: no value hidden in code)', () => {
    const properties = manifest.contributes.configuration.properties;
    expect(Object.keys(properties).sort()).toEqual(Object.keys(Defaults.SETTINGS).map(keyOf).sort());
    for (const [field, value] of Object.entries(Defaults.SETTINGS)) {
      expect(properties[keyOf(field)]?.default, field).toEqual(value);
    }
  });

  it('holds every declared minimum', () => {
    const properties = manifest.contributes.configuration.properties;
    for (const [field, minimum] of Object.entries(Defaults.MINIMUMS)) {
      expect(properties[keyOf(field)]?.minimum, field).toBe(minimum);
    }
  });
});

describe('SettingsResolver', () => {
  const home = '/home/me';

  it('resolves the defaults on macOS', () => {
    const resolved = new SettingsResolver({ HOME: home }, new MacStorage()).resolve({});
    expect(resolved.ollama.root).toBe('http://127.0.0.1:11434');
    expect(resolved.ollamaSource).toBe('the default');
    expect(resolved.model).toBe('gpt-oss:20b');
    expect(resolved.modelSource).toBe('the default');
    expect(resolved.stormHome).toEqual({ path: '/home/me/git/vibey-storm', source: 'the macos default' });
    expect(resolved.stateDir).toBe('/home/me/git/vibey-storm/.vibey-vscode');
    expect(resolved.modelLockPath).toBe('/home/me/git/vibey-storm/.ollama-lock');
    expect(resolved.maxTurns).toBeUndefined();
    expect(resolved.loop).toBe('sovereignloop');
    expect(resolved.effort).toBe('auto');
    expect(resolved.baseEffort).toBe('LOW');
    expect(resolved.engine).toBe('auto');
    expect(resolved.maxConcurrentRuns).toBe(1);
    expect(resolved.refreshMs).toBe(30_000);
    expect(resolved.pollMs).toBe(500);
    expect(resolved.stuckHintMs).toBe(300_000);
    expect(resolved.forceStopAfterMs).toBe(120_000);
    expect(resolved.lanesRecentMs).toBe(3_600_000);
    expect(resolved.skillsBudget).toBe(6000);
    expect(resolved.budgetPerTurn).toEqual({ input: 20000, output: 2000 });
    expect(resolved.environmentAllow).toEqual([]);
  });

  it('takes the family variables when a setting is empty, and a setting over them', () => {
    const environ = { HOME: home, VIBEY_OLLAMA_URL: 'http://box:11434/v1', VIBEY_OLLAMA_MODEL: 'qwen3:14b', VIBEY_STORM_HOME: '/data/storm' };
    const resolver = new SettingsResolver(environ, new LinuxStorage());
    const fromEnvironment = resolver.resolve({ ollamaUrl: '  ', model: '' });
    expect(fromEnvironment.ollama.root).toBe('http://box:11434');
    expect(fromEnvironment.ollamaSource).toBe('VIBEY_OLLAMA_URL');
    expect(fromEnvironment.model).toBe('qwen3:14b');
    expect(fromEnvironment.stormHome.source).toBe('VIBEY_STORM_HOME');
    const fromSettings = resolver.resolve({ ollamaUrl: 'http://other:1', model: ' gpt-oss:120b ', stormHome: '/mine' });
    expect(fromSettings.ollamaSource).toBe('the vibey.ollamaUrl setting');
    expect(fromSettings.model).toBe('gpt-oss:120b');
    expect(fromSettings.modelSource).toBe('the vibey.model setting');
    expect(fromSettings.stormHome.path).toBe('/mine');
  });

  it('reads loops, efforts and engines generously, and falls back on nonsense', () => {
    const resolver = new SettingsResolver({ HOME: home }, new MacStorage());
    expect(resolver.resolve({ loop: ' paidloop ' }).loop).toBe('paidloop');
    expect(resolver.resolve({ loop: 'cheaploop' }).loop).toBe('sovereignloop');
    expect(resolver.resolve({ effort: 'High' }).effort).toBe('HIGH');
    expect(resolver.resolve({ effort: 'AUTO' }).effort).toBe('auto');
    expect(resolver.resolve({ effort: 'lots' }).effort).toBe('auto');
    expect(resolver.resolve({ baseEffort: 'auto' }).baseEffort).toBe('LOW');
    expect(resolver.resolve({ baseEffort: 'standard' }).baseEffort).toBe('STANDARD');
    expect(resolver.resolve({ baseEffort: 'nope' }).baseEffort).toBe('LOW');
    expect(resolver.resolve({ engine: '  ' }).engine).toBe('auto');
    expect(resolver.resolve({ engine: 'qwenloop/gpt-oss:20b' }).engine).toBe('qwenloop/gpt-oss:20b');
  });

  it('raises numbers to their minimum, rounds them down, and reads nonsense as the default', () => {
    const resolved = new SettingsResolver({ HOME: home }, new MacStorage()).resolve({
      maxTurns: 25.9,
      stuckHintMinutes: 1,
      pollMilliseconds: Number.NaN,
      contextWindow: 'lots' as unknown as number,
      skillsBudget: 99_999,
      environmentAllow: [' GITHUB_TOKEN ', ' '],
      modelLockPath: 'relative/lock',
    });
    expect(resolved.maxTurns).toBe(25);
    expect(resolved.stuckHintMs).toBe(300_000);
    expect(resolved.pollMs).toBe(500);
    expect(resolved.contextWindow).toBe(32768);
    expect(resolved.skillsBudget).toBe(32_000);
    expect(resolved.environmentAllow).toEqual(['GITHUB_TOKEN']);
    expect(path.isAbsolute(resolved.modelLockPath)).toBe(true);
  });

  it('refuses an Ollama address that is not http or https', () => {
    expect(() => new SettingsResolver({ HOME: home }, new MacStorage()).resolve({ ollamaUrl: 'ftp://x' } as Partial<RawSettings>)).toThrow(
      'is not an http:// or https:// address',
    );
  });
});

describe('ExecutableLocator', () => {
  it('finds a program on PATH, skipping empty entries and non-executables', () => {
    const directory = scratch();
    const program = path.join(directory, 'qwenloop');
    fs.writeFileSync(program, '#!/bin/sh\n');
    fs.chmodSync(program, 0o755);
    fs.writeFileSync(path.join(directory, 'plain'), 'not executable');
    const locator = new ExecutableLocator({ PATH: `:/nowhere${path.delimiter}${directory}` });
    expect(locator.locate('qwenloop', '')).toEqual({ path: program, source: 'PATH' });
    expect(locator.locate('plain', '')).toEqual({ source: 'PATH', error: 'plain was not found on PATH' });
    expect(locator.locate('x', 'qwenloop')).toEqual({ path: program, source: 'the setting, found on PATH' });
    expect(locator.locate('x', program)).toEqual({ path: program, source: 'the setting' });
    expect(locator.locate('x', path.join(directory, 'plain'))).toEqual({
      source: 'the setting',
      error: `${path.join(directory, 'plain')} is not an executable file`,
    });
    expect(new ExecutableLocator({}).locate('git', '')).toEqual({ source: 'PATH', error: 'git was not found on PATH' });
    expect(ExecutableLocator.executableFile(directory)).toBe(false);
  });
});
