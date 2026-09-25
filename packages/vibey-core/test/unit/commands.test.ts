// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { CommandTable, SlashArguments, SlashCommands } from '../../src/commands';
import type { CommandSpec } from '../../src/interfaces/commands-interface';

describe('the one command table', () => {
  it('has unique ids and unique slash names', () => {
    const ids = CommandTable.ALL.map((spec) => spec.id);
    const slashes = CommandTable.ALL.map((spec) => spec.slash).filter((slash) => slash !== undefined);
    expect(new Set(ids).size).toBe(ids.length);
    expect(new Set(slashes).size).toBe(slashes.length);
  });

  it('groups every command, and finds one by id', () => {
    const grouped = CommandTable.grouped();
    expect(grouped.map(([group]) => group)).toEqual(CommandTable.GROUPS);
    expect(grouped.flatMap(([, specs]) => specs)).toHaveLength(CommandTable.ALL.length);
    expect(CommandTable.byId('vibey.ask')?.slash).toBe('ask');
    expect(CommandTable.byId('vibey.nothing')).toBeUndefined();
  });
});

describe('SlashCommands', () => {
  const slash = new SlashCommands();

  it('reads text that is not a command as text', () => {
    expect(slash.parse('  hello there ')).toEqual({ kind: 'text', text: 'hello there' });
  });

  it('reads a command and its arguments', () => {
    const parsed = slash.parse('/ASK add a line to README.md ');
    expect(parsed.kind).toBe('command');
    expect(parsed.kind === 'command' && parsed.spec.id).toBe('vibey.ask');
    expect(parsed.kind === 'command' && parsed.args).toBe('add a line to README.md');
    const bare = slash.parse('/stop');
    expect(bare.kind === 'command' && bare.args).toBe('');
  });

  it('reads the longest command a message names: /budget add before /budget', () => {
    const add = slash.parse('/Budget   ADD day paidloop dollars=5');
    expect(add.kind === 'command' && add.spec.slash).toBe('budget add');
    expect(add.kind === 'command' && add.args).toBe('day paidloop dollars=5');
    const bare = slash.parse('/budget');
    expect(bare.kind === 'command' && bare.spec.slash).toBe('budget');
    expect(bare.kind === 'command' && bare.args).toBe('');
    const list = slash.parse('/budget everything');
    expect(list.kind === 'command' && list.spec.slash).toBe('budget');
    expect(list.kind === 'command' && list.args).toBe('everything');
  });

  it('answers an unknown command plainly', () => {
    expect(slash.parse('/frobnicate now')).toEqual({ kind: 'unknown', name: 'frobnicate', reply: 'Unknown command /frobnicate. Try /help.' });
    expect(slash.parse('/')).toEqual({ kind: 'unknown', name: '', reply: 'Unknown command /. Try /help.' });
  });

  it('completes what has been typed after the slash', () => {
    expect(slash.complete('/st').map((spec) => spec.slash)).toEqual(['stop', 'start', 'stop-all', 'status', 'start-ollama']);
    expect(slash.complete('')).toHaveLength(CommandTable.ALL.length);
    expect(slash.complete('/zzz')).toEqual([]);
  });

  it('lists every slash command by group for /help, skipping groups with none', () => {
    const help = slash.help();
    expect(help).toContain('Run:');
    expect(help).toContain('/ask <task>');
    expect(help).toContain('/lanes  Every lane running');
    const lone: CommandSpec[] = [
      { id: 'a', title: 'A', group: 'Run', icon: 'x', slash: 'a', description: 'the a', example: '/a' },
      { id: 'b', title: 'B', group: 'Ollama', icon: 'x', description: 'no slash', example: 'b' },
    ];
    const partial = new SlashCommands(lone);
    expect(partial.help()).toBe('Run:\n  /a  the a');
    expect(partial.complete('')).toHaveLength(1);
  });
});

describe('SlashArguments', () => {
  const read = new SlashArguments();

  it('reads a loop by its everyday names', () => {
    for (const word of ['sovereign', 'SovereignLoop', 'free', 'local']) {
      expect(read.loop(word)).toBe('sovereignloop');
    }
    expect(read.loop(' paid ')).toBe('paidloop');
    expect(read.loop('paidloop')).toBe('paidloop');
    expect(read.loop('cheap')).toBe('Say /loop sovereign or /loop paid, not "cheap".');
  });

  it('reads an effort in any case, or auto', () => {
    expect(read.effort('AUTO')).toBe('auto');
    expect(read.effort('high')).toBe('HIGH');
    expect(read.effort('extreme')).toContain('not "extreme"');
  });

  it('splits words the way a shell does', () => {
    expect(read.words(`3f2a --raw '{"max_dollars": 25}' "two words" es\\ caped`)).toEqual([
      '3f2a',
      '--raw',
      '{"max_dollars": 25}',
      'two words',
      'es caped',
    ]);
    expect(read.words('  ')).toEqual([]);
    expect(read.words('""')).toEqual(['']);
    expect(read.words('trailing\\')).toEqual(['trailing\\']);
  });
});
