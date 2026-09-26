// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Every command of the one command table, implemented once: palette, menu, panel and @krypton. */
import type { TaskPanelInterface } from './panel-interface';
import type { TreeElement } from './trees-interface';

/** Where a command came from, and where its words go. */
export interface Invocation {
  /** The item a view's menu ran it on. */
  readonly element?: TreeElement;
  /** What followed a slash command, typed in the panel or after @krypton. */
  readonly args?: string;
  /** Where replies go: a notification, the panel, or the chat. */
  readonly say: (text: string) => void;
  /** The run id of the panel it was typed in, when it was. */
  readonly runId?: string;
  /** The panel it was typed in: a task asked there is shown there. */
  readonly panel?: TaskPanelInterface;
}

export interface CommandActionsInterface {
  /** Run the command with this id; every id in the command table has one. */
  run(id: string, invocation: Invocation): Promise<void>;
  /** The ids this implements: exactly the command table's. */
  readonly ids: readonly string[];
}
