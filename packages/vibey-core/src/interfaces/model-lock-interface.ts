// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** One run at a time on the model, across every process on this computer. */
import type { AbortSignalLike } from './platform-interface';
import type { Disposable } from './support-interface';

export interface LockOwner {
  readonly pid: number;
  readonly host: string;
  /** When this computer last started, in epoch milliseconds: a PID means nothing across boots. */
  readonly bootAt: number;
  readonly startedAt: string;
  readonly purpose: string;
}

export type LockAttempt =
  | { readonly acquired: true }
  | { readonly acquired: false; readonly holder?: LockOwner };

export interface ModelSlotLockInterface {
  tryAcquire(purpose: string): LockAttempt;
  release(): void;
  /** Wait until the lock is free and take it; `onWait` hears who holds it each time it is busy. */
  acquire(
    purpose: string,
    onWait: (holder: LockOwner | undefined) => void,
    pollMs: number,
    signal?: AbortSignalLike,
  ): Promise<Disposable>;
}

export interface HostFacts {
  readonly pid: number;
  readonly host: string;
  bootAt(): number;
  /** Whether a process with this PID exists on this host. */
  alive(pid: number): boolean;
}
