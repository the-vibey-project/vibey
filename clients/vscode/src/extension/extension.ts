// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The extension's entry points. VS Code calls `activate` and `deactivate` by name, which is
 * why they are module functions: everything they do is a class's (the controller, the command
 * actions, the views, the chat participant).
 */
import * as vscode from 'vscode';
import { CommandTable } from '@vibey/core';
import { CommandActions } from './actions';
import { VibeyChat } from './chat';
import { VibeyController } from './controller';
import { EditorSettings } from './editor-settings';
import type { TreeElement } from './interfaces/trees-interface';
import { BudgetsSource, GatesSource, LanesSource, ModelSource, ProjectsSource, TasksSource, TreeItems, VibeyTree } from './trees';

let active: VibeyController | undefined;

export function activate(context: vscode.ExtensionContext): { readonly commands: readonly string[] } {
  const controller = new VibeyController(context, new EditorSettings());
  active = controller;
  const actions = new CommandActions(controller, context.extensionUri);
  const notify = (text: string): void => void vscode.window.showInformationMessage(text);
  for (const spec of CommandTable.ALL) {
    context.subscriptions.push(
      vscode.commands.registerCommand(spec.id, (element?: unknown) =>
        actions.run(spec.id, { ...(isTreeElement(element) ? { element } : {}), say: notify }),
      ),
    );
  }

  const items = new TreeItems(controller);
  const trees: [string, VibeyTree][] = [
    ['vibey.model', new VibeyTree(new ModelSource(controller), items)],
    ['vibey.runs', new VibeyTree(new TasksSource(controller), items)],
    ['vibey.lanes', new VibeyTree(new LanesSource(controller), items)],
    ['vibey.projects', new VibeyTree(new ProjectsSource(controller), items)],
    ['vibey.gates', new VibeyTree(new GatesSource(controller), items)],
    ['vibey.budgets', new VibeyTree(new BudgetsSource(controller), items)],
  ];
  for (const [id, tree] of trees) {
    context.subscriptions.push(vscode.window.createTreeView(id, { treeDataProvider: tree, showCollapseAll: false }));
  }

  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  status.command = 'vibey.showMenu';
  const label = (): void => {
    const running = [...controller.runs.values()].filter((run) => run.status !== 'finished' && run.status !== 'queued').length;
    const waiting = [...controller.runs.values()].filter((run) => run.status === 'queued').length;
    status.text = `$(sparkle) vibey${running > 0 ? ` · ${running} running` : ''}${waiting > 0 ? ` · ${waiting} waiting` : ''}`;
    status.tooltip = 'Vibey: every command';
  };
  label();
  status.show();
  context.subscriptions.push(
    status,
    controller.onDidChange(() => {
      label();
      for (const [, tree] of trees) {
        tree.refresh();
      }
    }),
  );

  const chat = new VibeyChat(controller, actions, context.extensionUri).register();
  if (chat !== undefined) {
    context.subscriptions.push(chat);
  }
  // What the smoke test checks: every command of the table is registered here.
  return { commands: actions.ids };
}

/** Ask every task this window started to wind down: the model finishes its turn, then it ends. */
export async function deactivate(): Promise<void> {
  const controller = active;
  active = undefined;
  if (controller === undefined) {
    return;
  }
  await Promise.all([...controller.runs.values()].filter((run) => run.status !== 'finished').map((run) => run.stop()));
}

/** A view item, as a menu command receives it; anything else (a URI, nothing) is not one. */
function isTreeElement(value: unknown): value is TreeElement {
  return typeof value === 'object' && value !== null && typeof (value as { kind?: unknown }).kind === 'string';
}
