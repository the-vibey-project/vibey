// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Writes package.json's `contributes.commands` and the @vibey chat participant's commands from the
// one command table (@vibey/core's commands.ts, built to its dist/). `npm run compile` runs it; the unit
// suite fails if package.json and the table ever disagree.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { CommandTable, SlashCommands } = require('@vibey/core');

const file = path.join(__dirname, '..', 'package.json');
const manifest = JSON.parse(fs.readFileSync(file, 'utf8'));
manifest.contributes.commands = CommandTable.ALL.map((spec) => ({
  command: spec.id,
  title: spec.title,
  category: 'krypton',
  icon: `$(${spec.icon})`,
}));
manifest.contributes.chatParticipants[0].commands = new SlashCommands().firstWords().map((word) => ({
  name: word,
  description: CommandTable.ALL.find((spec) => spec.slash !== undefined && spec.slash.split(' ')[0] === word).description,
}));
const text = `${JSON.stringify(manifest, null, 2)}\n`;
if (fs.readFileSync(file, 'utf8') !== text) {
  fs.writeFileSync(file, text);
  process.stdout.write('package.json: commands updated from the command table\n');
}
