// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The headless CLI's words: its arguments, and how a run and a batch are shown and exit. */
import type { RunItem, RunPatch } from './run-events-interface';
import type { RunOutcome, RunRecord } from './run-interface';
import type { BatchSummary } from './batch-interface';

export interface ParsedArguments {
  readonly command: string;
  readonly positionals: readonly string[];
  readonly options: Readonly<Record<string, string | true>>;
}

export interface ArgumentParserInterface {
  /** `argv` without node and the script. Flags take a value unless declared as switches. */
  parse(argv: readonly string[]): ParsedArguments;
}

export interface PresenterInterface {
  /** One line (or streamed text) for a patch, as a terminal shows it. */
  patch(patch: RunPatch, items: readonly RunItem[]): string;
  record(record: RunRecord): string;
  batch(summary: BatchSummary): string;
  exitCode(outcome: RunOutcome): number;
  batchExitCode(summary: BatchSummary): number;
}
