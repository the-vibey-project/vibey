import type { Clock } from "./clock.ts";
import type { KeyValueStore } from "./store.ts";

export class TtlStore implements KeyValueStore {
  private inner: KeyValueStore;
  private clock: Clock;
  private defaultTtlMs: number | undefined;
  private expiry = new Map<string, number>();

  constructor(inner: KeyValueStore, clock: Clock, defaultTtlMs?: number) {
    this.inner = inner;
    this.clock = clock;
    this.defaultTtlMs = defaultTtlMs;
  }

  private isExpired(key: string): boolean {
    const at = this.expiry.get(key);
    return at !== undefined && this.clock.now() >= at;
  }

  private drop(key: string): void {
    this.expiry.delete(key);
    this.inner.delete(key);
  }

  get(key: string): string | undefined {
    if (this.isExpired(key)) {
      this.drop(key);
      return undefined;
    }
    return this.inner.get(key);
  }

  set(key: string, value: string, ttlMs?: number): void {
    const lifetime = ttlMs ?? this.defaultTtlMs;
    if (lifetime !== undefined && !(lifetime > 0)) {
      throw new RangeError("ttl must be positive");
    }
    this.inner.set(key, value);
    if (lifetime === undefined || lifetime === Infinity) {
      this.expiry.delete(key);
    } else {
      this.expiry.set(key, this.clock.now() + lifetime);
    }
  }

  delete(key: string): boolean {
    if (this.isExpired(key)) {
      this.drop(key);
      return false;
    }
    this.expiry.delete(key);
    return this.inner.delete(key);
  }

  keys(): string[] {
    const live: string[] = [];
    for (const key of this.inner.keys()) {
      if (this.isExpired(key)) {
        this.drop(key);
      } else {
        live.push(key);
      }
    }
    return live;
  }

  sweep(): number {
    let removed = 0;
    for (const key of this.inner.keys()) {
      if (this.isExpired(key)) {
        this.drop(key);
        removed += 1;
      }
    }
    return removed;
  }
}
