// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The six views in the Vibey activity bar, and what their items stand for. */
import type * as vscode from 'vscode';
import type { Budget } from '@vibey/core';
import type { Lane } from '@vibey/core';
import type { RunRecord } from '@vibey/core';
import type { VibeyBudget, VibeyGate, VibeyProject } from '@vibey/core';

/** One item in a view. Commands run from an item's menu receive it as their argument. */
export type TreeElement =
  | {
      readonly kind: 'info';
      readonly label: string;
      readonly description?: string;
      readonly tooltip?: string;
      readonly icon?: string;
      readonly command?: vscode.Command;
      readonly children?: readonly TreeElement[];
    }
  | { readonly kind: 'run'; readonly runId: string }
  | { readonly kind: 'record'; readonly record: RunRecord; readonly applied?: string; readonly discarded?: string }
  | { readonly kind: 'lane'; readonly lane: Lane }
  | { readonly kind: 'project'; readonly project: VibeyProject }
  | { readonly kind: 'gate'; readonly gate: VibeyGate }
  | { readonly kind: 'lane-budget'; readonly budget: Budget; readonly exhausted: boolean; readonly spent: string }
  | { readonly kind: 'project-budget'; readonly budget: VibeyBudget };

/** Where a view's items come from. */
export interface TreeSourceInterface {
  roots(): Promise<readonly TreeElement[]>;
}

export interface VibeyTreeInterface extends vscode.TreeDataProvider<TreeElement> {
  refresh(): void;
}

/** How an item looks: its label, icon, description and menu. */
export interface TreeItemsInterface {
  item(element: TreeElement): vscode.TreeItem;
}
