// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Tasks waiting their turn on a model, first in, first out. */
import type { TaskRunInterface } from './run-interface';
import type { Disposable } from './support-interface';

export interface QueueSnapshot {
  readonly running: readonly TaskRunInterface[];
  /** In the order they will start. */
  readonly queued: readonly TaskRunInterface[];
  /** Held: nothing waiting starts until the queue is started again. */
  readonly paused: boolean;
}

export interface RunQueueInterface {
  /** Start `run` now if its model has a free slot, else put it at the back of the line. */
  enqueue(model: string, run: TaskRunInterface): void;
  /** Take a waiting run out of the line; it ends as stopped without ever starting. */
  cancel(run: TaskRunInterface): boolean;
  snapshot(): QueueSnapshot;
  onChange(listener: () => void): Disposable;
  /** Hold the line: runs already going continue, nothing waiting starts. */
  pause(): void;
  /** Start the line again, filling every free slot. */
  resume(): void;
  /** Move a waiting run to the front of its line, and start the line if it was held. */
  bump(run: TaskRunInterface): boolean;
  /** Hold the line, then ask every running run to wind down, one after another. The errors. */
  stopAll(): Promise<readonly string[]>;
}
