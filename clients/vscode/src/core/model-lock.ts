// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * One run at a time on the model, whoever starts it: the editor, or `vibey-vscode batch` in
 * a terminal. The measured ideal on a 24 GB Mac is one concurrent run of gpt-oss:20b; at
 * two, answers drifted from what one run gives (#1114, sub-doctrine 8.c).
 *
 * The lock is a directory, because creating one is atomic on every local filesystem, with
 * an `owner.json` saying who holds it. A holder that is gone (its process ended, or the
 * computer restarted since) no longer holds it, so a crash never leaves the model locked
 * for good. It is the same `mkdir` lock the family's other tools take (vibey-gh's
 * `DirectoryLock`, storm shell tooling), which hold a bare directory for as long as they
 * run: a lock whose holder does not say who is theirs, and is never broken from here, and
 * neither is one held from another host. Declared by `interfaces/model-lock-interface.ts`.
 */
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type { ClockInterface, Disposable } from '@vibey/core';
import type {
  HostFacts,
  LockAttempt,
  LockOwner,
  ModelSlotLockInterface,
} from '@vibey/core';

export class LocalHost implements HostFacts {
  readonly pid = process.pid;
  readonly host = os.hostname();

  bootAt(): number {
    return Date.now() - os.uptime() * 1000;
  }

  alive(pid: number): boolean {
    try {
      process.kill(pid, 0);
      return true;
    } catch (error) {
      // EPERM: the process exists and belongs to someone else.
      return (error as NodeJS.ErrnoException).code === 'EPERM';
    }
  }
}

export class ModelSlotLock implements ModelSlotLockInterface {
  /** Two boot times this far apart are two different boots. */
  static readonly BOOT_TOLERANCE_MS = 120_000;
  private static readonly OWNER = 'owner.json';

  private held = false;

  constructor(
    private readonly directory: string,
    private readonly clock: ClockInterface,
    private readonly facts: HostFacts = new LocalHost(),
  ) {}

  tryAcquire(purpose: string): LockAttempt {
    fs.mkdirSync(path.dirname(this.directory), { recursive: true });
    try {
      fs.mkdirSync(this.directory);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'EEXIST') {
        throw error;
      }
      const holder = this.holder();
      if (this.stale(holder)) {
        fs.rmSync(this.directory, { recursive: true, force: true });
        return this.tryAcquire(purpose);
      }
      return holder === undefined ? { acquired: false } : { acquired: false, holder };
    }
    const owner: LockOwner = {
      pid: this.facts.pid,
      host: this.facts.host,
      bootAt: Math.round(this.facts.bootAt()),
      startedAt: this.clock.now().toISOString(),
      purpose,
    };
    fs.writeFileSync(path.join(this.directory, ModelSlotLock.OWNER), `${JSON.stringify(owner)}\n`);
    this.held = true;
    return { acquired: true };
  }

  release(): void {
    if (this.held) {
      this.held = false;
      fs.rmSync(this.directory, { recursive: true, force: true });
    }
  }

  async acquire(
    purpose: string,
    onWait: (holder: LockOwner | undefined) => void,
    pollMs: number,
    signal?: AbortSignal,
  ): Promise<Disposable> {
    for (;;) {
      if (signal?.aborted) {
        throw new Error('stopped while waiting for the model');
      }
      const attempt = this.tryAcquire(purpose);
      if (attempt.acquired) {
        return { dispose: () => this.release() };
      }
      onWait(attempt.holder);
      await this.clock.sleep(pollMs);
    }
  }

  private holder(): LockOwner | undefined {
    try {
      const parsed: unknown = JSON.parse(
        fs.readFileSync(path.join(this.directory, ModelSlotLock.OWNER), 'utf8'),
      );
      const owner = parsed as Partial<LockOwner>;
      return typeof owner.pid === 'number' && typeof owner.host === 'string' && typeof owner.bootAt === 'number'
        ? (owner as LockOwner)
        : undefined;
    } catch {
      return undefined;
    }
  }

  private stale(holder: LockOwner | undefined): boolean {
    // No owner file: another tool's bare `mkdir` lock, held for as long as it runs.
    if (holder === undefined || holder.host !== this.facts.host) {
      return false;
    }
    const otherBoot = Math.abs(holder.bootAt - this.facts.bootAt()) > ModelSlotLock.BOOT_TOLERANCE_MS;
    return otherBoot || !this.facts.alive(holder.pid);
  }
}
