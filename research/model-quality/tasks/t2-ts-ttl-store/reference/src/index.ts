import { systemClock } from "./clock.ts";
import type { Clock } from "./clock.ts";
import { MemoryStore } from "./store.ts";
import type { KeyValueStore } from "./store.ts";
import { TtlStore } from "./ttl-store.ts";

export function createStore(options?: {
  ttlMs?: number;
  clock?: Clock;
}): KeyValueStore {
  if (options?.ttlMs !== undefined) {
    return new TtlStore(new MemoryStore(), options.clock ?? systemClock, options.ttlMs);
  }
  return new MemoryStore();
}
