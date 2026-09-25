// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Runs inside VS Code's extension host (run.js starts it): the extension activates, registers
// every command of its one command table, contributes its views, and the commands that need
// no answer from a person run without throwing, whether or not Ollama and vibey are here.
'use strict';
const assert = require('node:assert');
const path = require('node:path');
const vscode = require('vscode');

async function check(name, body) {
  try {
    await body();
    console.log(`  ok   ${name}`);
  } catch (error) {
    console.log(`  FAIL ${name}`);
    throw error;
  }
}

exports.run = async function run() {
  const root = path.resolve(__dirname, '..', '..');
  const manifest = require(path.join(root, 'package.json'));
  const table = require(path.join(root, 'out', 'core', 'commands.js')).CommandTable.ALL.map((spec) => spec.id);
  const extension = vscode.extensions.getExtension(`${manifest.publisher}.${manifest.name}`);

  await check('the extension is installed and activates', async () => {
    assert.ok(extension, 'the extension is present');
    const api = await extension.activate();
    assert.ok(extension.isActive, 'it is active');
    assert.deepStrictEqual([...api.commands].sort(), [...table].sort(), 'its handlers are exactly the command table');
  });

  await check('every command of the table is registered', async () => {
    const registered = new Set(await vscode.commands.getCommands(true));
    const missing = table.filter((id) => !registered.has(id));
    assert.deepStrictEqual(missing, [], `not registered: ${missing.join(', ')}`);
  });

  await check('the six views are contributed', async () => {
    const views = manifest.contributes.views.vibey.map((view) => view.id);
    assert.deepStrictEqual(views, ['vibey.model', 'vibey.runs', 'vibey.lanes', 'vibey.projects', 'vibey.gates', 'vibey.budgets']);
    for (const view of views) {
      await vscode.commands.executeCommand(`${view}.focus`);
    }
  });

  for (const id of ['vibey.refresh', 'vibey.showLoops', 'vibey.doctor', 'vibey.showLanes', 'vibey.showProjects', 'vibey.showGates', 'vibey.showBudgets']) {
    await check(`${id} runs`, () => vscode.commands.executeCommand(id));
  }
};
