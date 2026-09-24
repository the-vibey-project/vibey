// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * One line per model. At most `limit` runs use a model at once (`vibey.maxConcurrentRuns`,
 * default 1: the measured ideal for gpt-oss:20b on a 24 GB Mac, #1114, sub-doctrine 8.c);
 * the rest wait in the order they were asked for. Across processes the model slot lock
 * holds the same line. Declared by `interfaces/run-queue-interface.ts`.
 */
import type { QueueSnapshot, RunQueueInterface } from './interfaces/run-queue-interface';
import type { TaskRunInterface } from './interfaces/run-interface';
import type { Disposable } from './interfaces/support-interface';
import { Emitter } from './support';

interface Lane {
  readonly running: Set<TaskRunInterface>;
  readonly waiting: TaskRunInterface[];
}

export class RunQueue implements RunQueueInterface {
  private readonly lanes = new Map<string, Lane>();
  private readonly changes = new Emitter<void>();
  private held = false;

  constructor(private readonly limit: number) {}

  enqueue(model: string, run: TaskRunInterface): void {
    const lane = this.lane(model);
    lane.waiting.push(run);
    this.fill(model, lane);
    this.changes.fire();
  }

  pause(): void {
    this.held = true;
    this.changes.fire();
  }

  resume(): void {
    this.held = false;
    for (const [model, lane] of this.lanes) {
      this.fill(model, lane);
    }
    this.changes.fire();
  }

  bump(run: TaskRunInterface): boolean {
    for (const lane of this.lanes.values()) {
      const index = lane.waiting.indexOf(run);
      if (index >= 0) {
        lane.waiting.splice(index, 1);
        lane.waiting.unshift(run);
        this.resume();
        return true;
      }
    }
    return false;
  }

  async stopAll(): Promise<readonly string[]> {
    this.pause();
    const errors: string[] = [];
    for (const run of this.snapshot().running) {
      const error = await run.stop();
      if (error !== undefined) {
        errors.push(`${run.request.title}: ${error}`);
      }
    }
    return errors;
  }

  cancel(run: TaskRunInterface): boolean {
    for (const lane of this.lanes.values()) {
      const index = lane.waiting.indexOf(run);
      if (index >= 0) {
        lane.waiting.splice(index, 1);
        void run.stop();
        void run.execute();
        this.changes.fire();
        return true;
      }
    }
    return false;
  }

  snapshot(): QueueSnapshot {
    const running: TaskRunInterface[] = [];
    const queued: TaskRunInterface[] = [];
    for (const lane of this.lanes.values()) {
      running.push(...lane.running);
      queued.push(...lane.waiting);
    }
    return { running, queued, paused: this.held };
  }

  onChange(listener: () => void): Disposable {
    return this.changes.on(listener);
  }

  private lane(model: string): Lane {
    let lane = this.lanes.get(model);
    if (lane === undefined) {
      lane = { running: new Set(), waiting: [] };
      this.lanes.set(model, lane);
    }
    return lane;
  }

  /** Start waiting runs while the line is not held and a slot is free. */
  private fill(model: string, lane: Lane): void {
    while (!this.held && lane.running.size < this.limit && lane.waiting.length > 0) {
      this.start(model, lane, lane.waiting.shift() as TaskRunInterface);
    }
  }

  private start(model: string, lane: Lane, run: TaskRunInterface): void {
    lane.running.add(run);
    const done = (): void => {
      lane.running.delete(run);
      this.fill(model, lane);
      this.changes.fire();
    };
    // execute() records every failure as a result and never rejects; the line moves on
    // either way, so a broken promise could never leave the model's slot taken.
    void run.execute().then(done, done);
  }
}
