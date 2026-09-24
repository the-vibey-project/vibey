// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Small seams every part of the core shares: events, time, identifiers, safe text, names. */

export interface Disposable {
  dispose(): void;
}

export interface EmitterInterface<T> {
  on(listener: (value: T) => void): Disposable;
  fire(value: T): void;
}

export interface ClockInterface {
  now(): Date;
  /** Milliseconds from an arbitrary start that never goes backwards. */
  monotonic(): number;
  every(milliseconds: number, callback: () => void): Disposable;
  sleep(milliseconds: number): Promise<void>;
}

export interface IdSourceInterface {
  uuid(): string;
}

export interface HtmlTextInterface {
  escape(text: string): string;
}

export interface TaskNamingInterface {
  /** Lower-case ASCII words joined by `-`; `fallback` (default `task`) when nothing is left. */
  slug(text: string, fallback?: string): string;
  shortId(runId: string): string;
  branch(slug: string, shortId: string): string;
  worktreeName(repository: string, slug: string, shortId: string): string;
  title(task: string): string;
}
