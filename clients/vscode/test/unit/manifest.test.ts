// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The extension's manifest and README against the one command table, which @vibey/core owns.
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { CommandTable, SlashCommands } from '@vibey/core';

const root = path.join(__dirname, '..', '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')) as {
  contributes: {
    commands: { command: string; title: string; category: string; icon: string }[];
    chatParticipants: { id: string; commands: { name: string; description: string }[] }[];
  };
};

describe('the one command table, as this extension contributes it', () => {
  it('is exactly the commands package.json contributes, titles and icons included', () => {
    const contributed = manifest.contributes.commands.map((command) => [command.command, command.title, command.category, command.icon]);
    const declared = CommandTable.ALL.map((spec) => [spec.id, spec.title, 'krypton', `$(${spec.icon})`]);
    expect(contributed).toEqual(declared);
  });

  it("is exactly the @krypton chat participant's commands: each slash command's first word, once", () => {
    // VS Code reads `@krypton /budget add ...` as the command `budget` and the prompt `add ...`,
    // so the participant declares first words and the panel's parser reads the rest.
    const participant = manifest.contributes.chatParticipants[0];
    expect(participant?.id).toBe('krypton.chat');
    const words = new SlashCommands().firstWords();
    const declared = words.map((word) => ({
      name: word,
      description: CommandTable.ALL.find((spec) => spec.slash?.split(' ')[0] === word)?.description,
    }));
    expect(participant?.commands).toEqual(declared);
    for (const spec of CommandTable.ALL.filter((each) => each.slash !== undefined)) {
      expect(words).toContain(spec.slash?.split(' ')[0]);
    }
  });

  it('has a worked example in the README for every command (doctrine 3)', () => {
    const readme = fs.readFileSync(path.join(root, 'README.md'), 'utf8');
    for (const spec of CommandTable.ALL) {
      expect(readme, `${spec.id} is missing from the README`).toContain(spec.id);
      expect(readme, `${spec.example} is missing from the README`).toContain(spec.example);
    }
  });
});
