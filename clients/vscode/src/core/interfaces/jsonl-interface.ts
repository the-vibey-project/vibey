// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Append-only JSON-lines files: read from a byte position, and written one durable line at a time. */

export interface TailChunk {
  readonly records: readonly unknown[];
  /** Complete lines that were not JSON; skipped, and counted so nothing is lost silently. */
  readonly malformed: number;
  /** Where the next read starts: just past the last complete line read. */
  readonly nextOffset: number;
  /** The file does not exist yet. */
  readonly missing: boolean;
  /** The file became shorter than the offset, so it was read again from the start. */
  readonly restarted: boolean;
}

export interface JsonlTailInterface {
  read(file: string, offset: number): TailChunk;
}

export interface JournalContents {
  readonly records: readonly Record<string, unknown>[];
  readonly malformed: number;
}

export interface JsonlJournalInterface {
  readonly file: string;
  /** Write one line and fsync it before returning. */
  append(record: Readonly<Record<string, unknown>>): void;
  readAll(): JournalContents;
}
