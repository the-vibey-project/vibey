// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The task panel: a task's transcript as it happens, a box to type in, and its buttons. */
import type { RunItem, RunPatch } from '../../core/interfaces/run-events-interface';
import type { RunStatus } from '../../core/interfaces/run-interface';

/** What the page sends: a line typed, a button pressed, an image pasted. */
export type PanelRequest =
  | { readonly type: 'ready' }
  | { readonly type: 'send'; readonly text: string }
  | { readonly type: 'button'; readonly command: string }
  | { readonly type: 'pasteImage'; readonly dataUrl: string };

/** What the page is sent. Every string in it is shown as text, never as markup. */
export type PanelUpdate =
  | {
      readonly type: 'init';
      readonly title: string;
      readonly mode: 'task' | 'lane';
      readonly items: readonly RunItem[];
      readonly status: RunStatus | 'idle' | 'lane';
      readonly slash: readonly { readonly name: string; readonly usage: string; readonly description: string }[];
      readonly canPasteImage: boolean;
      readonly forceAfterMs?: number;
      readonly finishedActions: boolean;
      readonly takesFollowUps: boolean;
    }
  | { readonly type: 'patch'; readonly patch: RunPatch }
  | { readonly type: 'items'; readonly items: readonly RunItem[] }
  | {
      readonly type: 'status';
      readonly status: RunStatus | 'idle' | 'lane';
      readonly forceAfterMs?: number;
      readonly finishedActions: boolean;
      /** Whether the engine running now acts on a follow-up; the box is closed while it runs otherwise. */
      readonly takesFollowUps: boolean;
    }
  | { readonly type: 'note'; readonly level: 'info' | 'warn' | 'error'; readonly text: string };

export interface TaskPanelInterface {
  /** Show this task in the panel, from its first item. */
  show(runId: string): void;
  /** A line from the extension, in the panel's stream. */
  note(level: 'info' | 'warn' | 'error', text: string): void;
  reveal(): void;
  dispose(): void;
}

export interface PanelHtmlInterface {
  /** The page, with a content security policy that runs only this nonce's script. */
  page(title: string, script: string, style: string, nonce: string, cspSource: string): string;
  nonce(): string;
}
