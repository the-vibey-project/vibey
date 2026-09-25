// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The small shared pieces every client leans on: the runner family, JSON-lines parsing, the
// volatile-storage refusal, the slash commands' first words, the design tokens, and the barrel.
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import * as core from '../../src';
import { SlashCommands } from '../../src/commands';
import { JsonlParse } from '../../src/jsonl-parse';
import { LocalRunners } from '../../src/local-runner';
import { DEFAULT_THEME_MODE, THEME_MODES, coloursFor, motionFor, resolveTheme, themes, tokens } from '../../src/tokens';
import { VolatileStorageError } from '../../src/volatile-storage-error';

describe('LocalRunners', () => {
  it('knows its runners by engine id, and names their variables by prefix', () => {
    expect(LocalRunners.FAMILY.identify('qwenloop')).toBe(LocalRunners.QWENLOOP);
    expect(LocalRunners.FAMILY.identify('claudeloop')).toBeUndefined();
    expect(LocalRunners.FAMILY.variable(LocalRunners.GPTOSSLOOP, 'CONFIG')).toBe('GPTOSSLOOP_CONFIG');
  });
});

describe('JsonlParse', () => {
  it('keeps the JSON lines, skips blank ones, and counts the rest as malformed', () => {
    expect(JsonlParse.lines('{"a":1}\n\n  \nnot json\n[2]\n')).toEqual({ records: [{ a: 1 }, [2]], malformed: 1 });
  });
});

describe('VolatileStorageError', () => {
  it('names each path, where it really lives, and how to choose a durable home', () => {
    const error = new VolatileStorageError([
      { name: 'storm home', path: '/tmp/storm', resolved: '/private/tmp/storm', location: '/private/tmp', why: 'emptied at restart' },
      { name: 'worktree', path: '/private/tmp/w', resolved: '/private/tmp/w', location: '/private/tmp', why: 'emptied at restart' },
    ]);
    expect(error.name).toBe('VolatileStorageError');
    expect(VolatileStorageError.EXIT_CODE).toBe(78);
    expect(error.message.split('\n').slice(0, 5)).toEqual([
      'refused: this work would be kept on storage the operating system empties.',
      '  storm home: /tmp/storm -> /private/tmp/storm',
      '    under /private/tmp: emptied at restart',
      '  worktree: /private/tmp/w',
      '    under /private/tmp: emptied at restart',
    ]);
    expect(error.message).toContain('Sub-doctrine 10.h; ADR-0057.');
  });
});

describe('SlashCommands', () => {
  it('gives the first word of every slash command once, the way a chat participant declares them', () => {
    const words = new SlashCommands().firstWords();
    expect(new Set(words).size).toBe(words.length);
    expect(words).toContain('budget');
  });
});

describe('the design tokens', () => {
  it('are the generated module itself, re-exported and never copied', () => {
    const source = fs.readFileSync(path.join(__dirname, '..', '..', 'src', 'tokens.ts'), 'utf8');
    expect(source).toContain("export * from '../../../design/dist/ts/tokens';");
    expect(fs.readdirSync(path.join(__dirname, '..', '..', 'src')).filter((name) => name.includes('token'))).toEqual(['tokens.ts']);
  });

  it('resolve a theme mode against the system, System being the default', () => {
    expect(THEME_MODES).toEqual(['light', 'dark', 'system']);
    expect(DEFAULT_THEME_MODE).toBe('system');
    expect(resolveTheme('system', true)).toBe('dark');
    expect(resolveTheme('system', false)).toBe('light');
    expect(resolveTheme('light', true)).toBe('light');
    expect(coloursFor('dark', false)).toBe(themes.dark);
    expect(motionFor(true)).toBe(tokens.motion.reduced);
    expect(motionFor(false)).toBe(tokens.motion);
  });
});

describe('@vibey/core', () => {
  it('exports the shared classes and the transports from one entry point', () => {
    for (const name of ['CatalogueParser', 'CommandTable', 'Doctor', 'GateAnswerPlanner', 'BudgetGuard', 'LocalProcessTransport', 'HubTransport', 'resolveTheme']) {
      expect(core, name).toHaveProperty(name);
    }
  });

  it('reaches no platform: nothing in src imports node:, vscode or a DOM global', () => {
    const directory = path.join(__dirname, '..', '..', 'src');
    const files = fs.readdirSync(directory, { recursive: true, encoding: 'utf8' }).filter((name) => name.endsWith('.ts'));
    for (const file of files) {
      const text = fs.readFileSync(path.join(directory, file), 'utf8');
      expect(text, file).not.toMatch(/from '(node:[a-z_]+|vscode|fs|path|os|child_process|http|https|crypto)'/);
      expect(text, file).not.toMatch(/\b(window|document)\.[a-zA-Z]|\brequire\(/);
    }
  });
});
