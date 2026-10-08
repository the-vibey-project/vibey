// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Writes the command table into package.json, so the manifest a user installs and the table
// the extension registers from cannot disagree. Compiled by `tsc -p tsconfig.tools.json`
// (TypeScript is the only authored form, sub-doctrine 9.f) and run by `npm run compile`.
import * as fs from 'node:fs';
import * as path from 'node:path';
import { CommandTable, SlashCommands } from '@vibey/core';

interface Manifest {
  contributes: {
    commands: unknown;
    chatParticipants: Array<{ commands: unknown }>;
  };
}

const file = path.join(__dirname, '..', 'package.json');
const manifest = JSON.parse(fs.readFileSync(file, 'utf8')) as Manifest;
manifest.contributes.commands = CommandTable.ALL.map((spec) => ({
  command: spec.id,
  title: spec.title,
  category: 'krypton',
  icon: `$(${spec.icon})`,
}));
const participant = manifest.contributes.chatParticipants[0];
if (participant === undefined) {
  throw new Error('package.json declares no chat participant to give the slash commands to');
}
participant.commands = new SlashCommands().firstWords().map((word) => {
  const spec = CommandTable.ALL.find((candidate) => candidate.slash !== undefined && candidate.slash.split(' ')[0] === word);
  if (spec === undefined) {
    throw new Error(`the slash word "${word}" has no command in the table`);
  }
  return { name: word, description: spec.description };
});
const text = `${JSON.stringify(manifest, null, 2)}\n`;
if (fs.readFileSync(file, 'utf8') !== text) {
  fs.writeFileSync(file, text);
  process.stdout.write('package.json: commands updated from the command table\n');
}
