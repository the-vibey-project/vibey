// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { HubStatus } from '../../src/core/hub-status';
import { HubWatch } from '../../src/core/hub-watch';
import type { HubWatchTimers } from '../../src/core/interfaces/hub-watch-interface';

const status = new HubStatus();

describe('HubStatus', () => {
  it('says the hub is not running, what to run on that computer, and what the phone does', () => {
    const view = status.unreachable('http://studio.local:8765');
    expect(view.headline).toBe('The hub on your computer is not running');
    expect(view.body).toContain('http://studio.local:8765');
    expect(view.command).toBe('vibey hub start');
    expect(view.copyLabel).toBe('Copy the command');
    expect(view.notes.join(' ')).toMatch(/never stops the hub/);
    expect(view.notes.join(' ')).toMatch(/asks again by itself/);
  });

  it('reads reachability as one line', () => {
    const address = 'http://hub:8765';
    expect(status.line({ reachable: null, since: null, failures: 0 }, address, 0)).toEqual({ label: 'Checking', role: 'info', detail: address });
    expect(status.line({ reachable: true, since: null, failures: 0 }, address, 0)).toEqual({ label: 'Reachable', role: 'success', detail: address });
    const now = 10 * 86_400_000;
    const down = (ago: number) => status.line({ reachable: false, since: now - ago, failures: 3 }, address, now);
    expect(down(0)).toEqual({ label: 'Not reachable', role: 'danger', detail: `${address} · since just now` });
    expect(down(59_000).detail).toMatch(/just now/);
    expect(down(4 * 60_000).detail).toBe(`${address} · since 4 min ago`);
    expect(down(3 * 3_600_000).detail).toBe(`${address} · since 3 h ago`);
    expect(down(86_400_000).detail).toBe(`${address} · since 1 day ago`);
    expect(down(3 * 86_400_000).detail).toBe(`${address} · since 3 days ago`);
    // A clock that went backwards is not a negative age.
    expect(status.line({ reachable: true, since: now + 5000, failures: 0 }, address, now).detail).toMatch(/just now/);
  });

  it('backs off 2, 4, 8 ... and never past a minute', () => {
    const waits = [0, 1, 2, 3, 4, 5, 6, 40].map((failures) => status.backoffMs(failures));
    expect(waits).toEqual([2000, 2000, 4000, 8000, 16000, 32000, 60000, 60000]);
  });
});

class FakeTimers implements HubWatchTimers {
  clock = 1_000;
  pending: { id: number; run: () => void; ms: number }[] = [];
  cleared: unknown[] = [];
  private next = 1;
  setTimer(run: () => void, ms: number): unknown {
    const id = this.next++;
    this.pending.push({ id, run, ms });
    return id;
  }
  clearTimer(handle: unknown): void {
    this.cleared.push(handle);
    this.pending = this.pending.filter((timer) => timer.id !== handle);
  }
  now(): number {
    return this.clock;
  }
  /** Runs the one timer that is waiting, as if its time had come. */
  fire(): number {
    const timer = this.pending.shift() as { run: () => void; ms: number };
    timer.run();
    return timer.ms;
  }
}

const settle = () => new Promise<void>((resolve) => setImmediate(resolve));

describe('HubWatch', () => {
  it('asks at once, backs off while the hub is down, and says so when it comes back', async () => {
    const timers = new FakeTimers();
    const answers = [false, false, false, true];
    const probe = jest.fn(async () => answers.shift() as boolean);
    const watch = new HubWatch(probe, timers);
    const heard: (boolean | null)[] = [];
    watch.subscribe((state) => heard.push(state.reachable));
    expect(watch.state()).toEqual({ reachable: null, since: null, failures: 0 });

    watch.start();
    watch.start(); // a second start asks nothing more
    await settle();
    expect(probe).toHaveBeenCalledTimes(1);
    expect(watch.state()).toEqual({ reachable: false, since: 1_000, failures: 1 });
    expect(timers.pending[0]?.ms).toBe(2000);

    timers.clock = 5_000;
    expect(timers.fire()).toBe(2000);
    await settle();
    // Still down: the failure count grows, "since" does not move.
    expect(watch.state()).toEqual({ reachable: false, since: 1_000, failures: 2 });
    expect(timers.pending[0]?.ms).toBe(4000);

    timers.fire();
    await settle();
    expect(timers.pending[0]?.ms).toBe(8000);

    timers.clock = 9_000;
    timers.fire();
    await settle();
    expect(watch.state()).toEqual({ reachable: true, since: 9_000, failures: 0 });
    expect(timers.pending[0]?.ms).toBe(HubStatus.STEADY_MS);
    expect(heard).toEqual([false, false, false, true]);
  });

  it('treats a probe that throws as no answer, and stops listening when told', async () => {
    const timers = new FakeTimers();
    const watch = new HubWatch(async () => {
      throw new Error('offline');
    }, timers);
    const heard = jest.fn();
    const off = watch.subscribe(heard);
    watch.start();
    await settle();
    expect(watch.state().reachable).toBe(false);
    expect(heard).toHaveBeenCalledTimes(1);
    off();
    timers.fire();
    await settle();
    expect(heard).toHaveBeenCalledTimes(1);
  });

  it('stops asking in the background, drops a late answer, and starts again in front', async () => {
    const timers = new FakeTimers();
    let release: (answer: boolean) => void = () => undefined;
    const probe = jest
      .fn<Promise<boolean>, []>()
      .mockImplementationOnce(() => new Promise<boolean>((resolve) => (release = resolve)))
      .mockResolvedValue(true);
    const watch = new HubWatch(probe, timers);
    watch.stop(); // stopping what never started is harmless
    watch.start();
    watch.stop();
    release(false); // the answer to a question asked before the app went away
    await settle();
    expect(watch.state().reachable).toBeNull();
    expect(timers.pending).toHaveLength(0);

    watch.start();
    await settle();
    expect(watch.state().reachable).toBe(true);
    expect(timers.pending).toHaveLength(1);
    watch.stop();
    expect(timers.pending).toHaveLength(0);
    expect(timers.cleared).toHaveLength(1);
  });

  it('uses the real clock and timers when none are given', async () => {
    jest.useFakeTimers();
    try {
      const watch = new HubWatch(async () => true);
      watch.start();
      await jest.advanceTimersByTimeAsync(0);
      expect(watch.state().reachable).toBe(true);
      expect(watch.state().since).not.toBeNull();
      watch.stop();
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('a phone does not start or stop a hub (#1186)', () => {
  function sources(directory: string): string[] {
    return readdirSync(directory).flatMap((name) => {
      const path = join(directory, name);
      return statSync(path).isDirectory() ? sources(path) : /\.(ts|tsx)$/.test(name) ? [path] : [];
    });
  }

  it('names no route, method or request that does', () => {
    const root = join(__dirname, '..', '..');
    const files = [...sources(join(root, 'src')), ...sources(join(root, 'app'))];
    expect(files.length).toBeGreaterThan(20);
    for (const file of files) {
      const text = readFileSync(file, 'utf8');
      // The only mention of the command is the sentence that tells a person to run it elsewhere.
      expect(text).not.toMatch(/\/api\/v1\/hub\b/);
      expect(text).not.toMatch(/\b(startHub|stopHub|hubStart|hubStop|restartHub)\b/);
      expect(text).not.toMatch(/\bvibey hub stop\b/);
      if (!file.endsWith('hub-status.ts')) expect(text).not.toMatch(/vibey hub start/);
    }
  });
});
