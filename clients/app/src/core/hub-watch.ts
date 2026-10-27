// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Asks `GET /health/live` while the app is in front: every 30 seconds while the hub answers,
 * and after 2, 4, 8 ... 60 seconds while it does not. It stops when told (the app went to the
 * background), so it never drains a battery. Declared by `interfaces/hub-watch-interface.ts`.
 */
import { HubStatus } from './hub-status';
import type { HubWatchState } from './interfaces/hub-status-interface';
import type { HubWatchInterface, HubWatchTimers } from './interfaces/hub-watch-interface';

const REAL_TIMERS: HubWatchTimers = {
  setTimer: (run, ms) => setTimeout(run, ms),
  clearTimer: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
  now: () => Date.now(),
};

export class HubWatch implements HubWatchInterface {
  private current: HubWatchState = { reachable: null, since: null, failures: 0 };
  private readonly listeners = new Set<(state: HubWatchState) => void>();
  private timer: unknown = undefined;
  /** Bumped by every start and stop, so an answer to an old question is recognised and dropped. */
  private generation = 0;
  private running = false;

  constructor(
    private readonly probe: () => Promise<boolean>,
    private readonly timers: HubWatchTimers = REAL_TIMERS,
    private readonly status: HubStatus = new HubStatus(),
  ) {}

  start(): void {
    if (this.running) return;
    this.running = true;
    this.generation += 1;
    void this.ask(this.generation);
  }

  stop(): void {
    this.running = false;
    this.generation += 1;
    if (this.timer !== undefined) this.timers.clearTimer(this.timer);
    this.timer = undefined;
  }

  state(): HubWatchState {
    return this.current;
  }

  subscribe(listener: (state: HubWatchState) => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private async ask(generation: number): Promise<void> {
    let answered: boolean;
    try {
      answered = await this.probe();
    } catch {
      answered = false;
    }
    if (generation !== this.generation) return;
    const changed = this.current.reachable !== answered;
    this.current = {
      reachable: answered,
      since: changed ? this.timers.now() : this.current.since,
      failures: answered ? 0 : this.current.failures + 1,
    };
    // A state is announced when it changes or when a failure count moves, so a screen can say
    // "still down" and a recovery is heard once.
    for (const listener of this.listeners) listener(this.current);
    const wait = answered ? HubStatus.STEADY_MS : this.status.backoffMs(this.current.failures);
    this.timer = this.timers.setTimer(() => void this.ask(generation), wait);
  }
}
