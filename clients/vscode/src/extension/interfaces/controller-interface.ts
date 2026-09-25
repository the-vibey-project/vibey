// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The extension's state for one window: the core, the tasks it started, and the next task's extras. */
import type * as vscode from 'vscode';
import type { CapabilityMenu } from '@vibey/core';
import type { Attachment, RunRecord, TaskRunInterface } from '@vibey/core';
import type { Lane } from '@vibey/core';
import type { RunItem } from '@vibey/core';

/** What the next task takes with it besides its words. */
export interface NextTask {
  attachments: Attachment[];
  /** vibey-skills plugins whose context packet the next task gets. */
  plugins: string[];
}

export interface VibeyControllerInterface {
  /** Tasks this window started, by run id, newest last. */
  readonly runs: ReadonlyMap<string, TaskRunInterface>;
  readonly next: NextTask;
  readonly output: vscode.OutputChannel;
  /** Fires whenever a view should show something new. */
  readonly onDidChange: vscode.Event<void>;
  changed(): void;
  /** The paired hub's address, when vibey is reached through one (ADR-0068). */
  readonly hubUrl: string | undefined;
  /** Keep a checked key in secret storage and switch to the hub. */
  pairHub(url: string, key: string): Promise<void>;
  /** Forget the hub's key and go back to the local command line. */
  unpairHub(): Promise<void>;
  /** The repository folder a new task works in, or undefined when no folder is open. */
  folder(): string | undefined;
  /** Which extra menus the engine the next task would run on earns (images only where the model sees). */
  menu(): Promise<CapabilityMenu>;
  /** Follow a run started elsewhere (a batch), as if this window had asked for it. */
  track(run: TaskRunInterface): void;
  /** Start a task on the model: it waits its turn, then runs on a copy. */
  ask(task: string): Promise<TaskRunInterface | undefined>;
  /** Finished tasks, newest first, with what was done with each since. */
  finished(): readonly { readonly record: RunRecord; readonly applied?: string; readonly discarded?: string }[];
  /** Every lane on this computer, read again now. */
  lanes(): Promise<readonly Lane[]>;
  /** A lane's items so far. */
  laneItems(eventsPath: string): Promise<readonly RunItem[]>;
}
