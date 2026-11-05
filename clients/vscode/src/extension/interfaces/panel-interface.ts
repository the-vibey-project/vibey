// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The krypton chat and task panel: a conversation and transcript as it happens, open gates, a box to type in, and its buttons. */
import type { RunItem, RunPatch } from '@vibey/core';
import type { RunStatus } from '@vibey/core';

/** An open gate shown inline in the chat panel so the operator can answer in one click. */
export interface PanelGate {
  readonly gateId: string;
  readonly kind: string;
  readonly prompt: string;
  readonly projectName: string;
  /** True when answering this gate requires the `spend` scope (`budget_exhausted`). */
  readonly isSpend: boolean;
  readonly choices: readonly { readonly label: string; readonly command: string }[];
}

/** What the page sends: a line typed, a button pressed, an image pasted, or a UI action. */
export type PanelRequest =
  | { readonly type: 'ready' }
  | { readonly type: 'send'; readonly text: string }
  | { readonly type: 'button'; readonly command: string }
  | { readonly type: 'pasteImage'; readonly dataUrl: string }
  | { readonly type: 'action'; readonly action: string; readonly payload?: unknown };

/** How the page looks: the resolved theme, whose surfaces it sits on, and the two states it must never hide. */
export interface PanelLook {
  readonly theme: 'light' | 'dark';
  /** `editor`: the editor's own surfaces (System mode); `krypton`: krypton's palette (Light or Dark). */
  readonly surface: 'editor' | 'krypton';
  /** ULTRA effort is chosen: shown with its own colour and motion (ADR-0063). */
  readonly ultra: boolean;
  /** paidloop stands declared with no cap: the UNLIMITED SPEND banner shows (ADR-0063). */
  readonly unlimited: boolean;
}

/** What the page is sent. Every string in it is shown as text, never as markup. */
export type PanelUpdate =
  | ({ readonly type: 'look' } & PanelLook)
  | {
      readonly type: 'init';
      readonly title: string;
      readonly mode: 'task' | 'lane';
      readonly items: readonly RunItem[];
      readonly gates?: readonly PanelGate[];
      readonly status: RunStatus | 'idle' | 'lane';
      readonly slash: readonly { readonly name: string; readonly usage: string; readonly description: string }[];
      readonly canPasteImage: boolean;
      readonly forceAfterMs?: number;
      readonly finishedActions: boolean;
      readonly takesFollowUps: boolean;
      readonly model?: { readonly name: string; readonly effort: string; readonly ultracode: boolean; readonly models?: readonly string[] };
      readonly agentMode?: string;
      readonly sessionDuration?: string;
      readonly subagentsCount?: number;
      readonly browserConnected?: boolean;
    }
  | { readonly type: 'gates'; readonly gates: readonly PanelGate[] }
  | { readonly type: 'patch'; readonly patch: RunPatch }
  | { readonly type: 'items'; readonly items: readonly RunItem[] }
  | {
      readonly type: 'status';
      readonly status: RunStatus | 'idle' | 'lane';
      readonly forceAfterMs?: number;
      readonly finishedActions: boolean;
      /** Whether the engine running now acts on a follow-up; the box is closed while it runs otherwise. */
      readonly takesFollowUps: boolean;
      readonly model?: { readonly name: string; readonly effort: string; readonly ultracode: boolean };
      readonly agentMode?: string;
      readonly sessionDuration?: string;
      readonly subagentsCount?: number;
      readonly browserConnected?: boolean;
    }
  | { readonly type: 'config'; readonly model?: { readonly name: string; readonly effort: string; readonly ultracode: boolean; readonly models?: readonly string[] }; readonly agentMode?: string; readonly browserConnected?: boolean }
  | { readonly type: 'note'; readonly level: 'info' | 'warn' | 'error'; readonly text: string };

export interface TaskPanelInterface {
  /** Show this task in the panel, from its first item. */
  show(runId: string): void;
  /** Open the chat workspace even when no task is running yet, loading any waiting gates. */
  openChat(): void;
  /** A line from the extension, in the panel's stream. */
  note(level: 'info' | 'warn' | 'error', text: string): void;
  reveal(): void;
  dispose(): void;
}

export interface PanelHtmlInterface {
  /** The page, with a content security policy that runs only this nonce's script. */
  page(title: string, script: string, style: string, nonce: string, cspSource: string, tokens?: string, look?: PanelLook): string;
  nonce(): string;
}
