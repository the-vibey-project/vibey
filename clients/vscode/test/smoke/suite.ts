// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Runs inside VS Code's extension host (run.ts starts it): the extension activates, registers
// every command of its one command table, contributes its views, and the commands that need
// no answer from a person run without throwing, whether or not Ollama and vibey are here.
import * as assert from 'node:assert';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { CommandTable } from '@vibey/core';

interface Manifest {
  publisher: string;
  name: string;
  displayName: string;
  contributes: {
    views: { vibey: Array<{ id: string }> };
    walkthroughs: Array<{ id: string; steps: Array<{ media: { markdown: string } }> }>;
  };
}

/** What the extension's `activate` returns: the ids of the commands it handles. */
interface ExtensionApi {
  commands: Iterable<string>;
}

async function check(name: string, body: () => unknown): Promise<void> {
  try {
    await body();
    console.log(`  ok   ${name}`);
  } catch (error) {
    console.log(`  FAIL ${name}`);
    throw error;
  }
}

export async function run(): Promise<void> {
  // First act: tell run.ts the suite started, so a failure from here on is never retried.
  const marker = process.env['VIBEY_SMOKE_STARTED'];
  if (marker) fs.writeFileSync(marker, '');
  const root = path.resolve(__dirname, '..', '..');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8')) as Manifest;
  const table = CommandTable.ALL.map((spec) => spec.id);
  const extension = vscode.extensions.getExtension<ExtensionApi>(`${manifest.publisher}.${manifest.name}`);

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

  await check('it is krypton, with a first-run walkthrough whose every page is there', async () => {
    assert.strictEqual(manifest.displayName, 'krypton');
    const tour = manifest.contributes.walkthroughs[0];
    assert.ok(tour, 'the manifest declares a walkthrough');
    assert.strictEqual(tour.id, 'krypton.firstRun');
    for (const step of tour.steps) {
      assert.ok(fs.existsSync(path.join(root, step.media.markdown)), `${step.media.markdown} is missing`);
    }
    await vscode.commands.executeCommand('workbench.action.openWalkthrough', `${manifest.publisher}.${manifest.name}#krypton.firstRun`, false);
  });

  for (const id of ['vibey.refresh', 'vibey.showLoops', 'vibey.doctor', 'vibey.showLanes', 'vibey.showProjects', 'vibey.showGates', 'vibey.showBudgets', 'vibey.endNoCap', 'vibey.disconnectHub']) {
    await check(`${id} runs`, () => vscode.commands.executeCommand(id));
  }
}
