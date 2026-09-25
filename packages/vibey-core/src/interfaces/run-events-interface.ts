// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** A run's events.jsonl, as a person reads it: text, tool calls and results, turns, and the verdict. */
import type { EventEnvelope } from './catalogue-interface';

export type NoticeLevel = 'info' | 'warn' | 'error';

export type RunItem =
  | { readonly id: number; readonly kind: 'assistant'; readonly text: string }
  | {
      readonly id: number;
      readonly kind: 'tool-call';
      readonly turn?: number;
      readonly name: string;
      readonly detail: string;
    }
  | {
      readonly id: number;
      readonly kind: 'tool-result';
      readonly name: string;
      readonly ok: boolean;
      readonly detail: string;
    }
  | { readonly id: number; readonly kind: 'turn'; readonly turn: number; readonly detail: string }
  | { readonly id: number; readonly kind: 'follow-up'; readonly text: string }
  | { readonly id: number; readonly kind: 'notice'; readonly level: NoticeLevel; readonly text: string };

/** How the view changes: a new item, or more text on the assistant item it already shows. */
export type RunPatch =
  | { readonly op: 'add'; readonly item: RunItem }
  | { readonly op: 'append'; readonly id: number; readonly text: string };

export interface RunFailure {
  readonly reason: string;
  readonly turn?: number;
  readonly explanation: string;
}

export interface Verdict {
  /** The body of the last ```qwenloop-verdict fence (the runner's, whichever name ran), when there is one. */
  readonly text?: string;
  /** Whether the completion marker was written. */
  readonly marker: boolean;
}

export interface RunTranscriptInterface {
  /** One event, in the envelope its engine writes. */
  accept(event: unknown, envelope?: EventEnvelope): readonly RunPatch[];
  /** A line from the extension itself (waiting, a hint, an error), in the same stream. */
  note(level: NoticeLevel, text: string): RunPatch;
  items(): readonly RunItem[];
  readonly turns: number;
  readonly attemptTurns: number;
  beginAttempt(): void;
  readonly completed: boolean;
  readonly failure: RunFailure | undefined;
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly reportedDollars: number;
  verdict(): Verdict;
}
