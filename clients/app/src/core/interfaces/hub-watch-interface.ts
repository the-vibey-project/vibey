// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Keeps asking the hub whether it answers, patiently, and says when that changes. */
import type { HubWatchState } from './hub-status-interface';

/** The clock and timers, injected so tests wait for nothing. */
export interface HubWatchTimers {
  setTimer(run: () => void, ms: number): unknown;
  clearTimer(handle: unknown): void;
  now(): number;
}

export interface HubWatchInterface {
  /** Asks now, then again on a schedule, until `stop`. A second `start` does nothing. */
  start(): void;
  /** Stops asking (the app went to the background); a late answer is ignored. */
  stop(): void;
  state(): HubWatchState;
  /** Called with every new state; returns the way to stop listening. */
  subscribe(listener: (state: HubWatchState) => void): () => void;
}
