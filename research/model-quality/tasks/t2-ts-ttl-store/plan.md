`src/store.ts` defines the `KeyValueStore` interface and a `MemoryStore`; `src/clock.ts` defines
`Clock` (`now(): number`, milliseconds) and `systemClock`; `src/index.ts` has `createStore()`.
Add a store whose entries expire.

1. Create `src/ttl-store.ts` exporting class `TtlStore implements KeyValueStore`, with
   constructor `new TtlStore(inner: KeyValueStore, clock: Clock, defaultTtlMs?: number)`. It
   keeps the values in `inner` and keeps its own record of when each key expires.
2. `set(key, value, ttlMs?)` takes an optional third argument. The lifetime is `ttlMs`, or
   `defaultTtlMs` when `ttlMs` is omitted. With neither, the entry never expires. A lifetime that
   is zero, negative or `NaN` throws a `RangeError` (and stores nothing). `Infinity` means no
   expiry. The entry expires at `clock.now() + lifetime`; it is expired once `clock.now()` is
   greater than or equal to that time. Setting a key again replaces its lifetime completely (so
   a plain `set` on a key that had one makes it permanent when there is no default).
3. An expired entry is invisible: `get` returns `undefined`, `keys()` leaves it out (the rest
   keep the order the inner store gives), and `delete` returns `false` for it. Expired entries
   should also be removed from `inner` when they are found.
4. `sweep(): number` removes every expired entry from the store and returns how many it removed.
5. In `src/index.ts` change `createStore` to `createStore(options?: { ttlMs?: number; clock?:
   Clock })`. When `options.ttlMs` is given, return a `TtlStore` around a new `MemoryStore`,
   with `options.clock ?? systemClock` and `options.ttlMs` as the default lifetime. Otherwise
   return a plain `MemoryStore` as before.
