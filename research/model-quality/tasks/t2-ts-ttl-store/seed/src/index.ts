import { MemoryStore } from "./store.ts";
import type { KeyValueStore } from "./store.ts";

export function createStore(): KeyValueStore {
  return new MemoryStore();
}
