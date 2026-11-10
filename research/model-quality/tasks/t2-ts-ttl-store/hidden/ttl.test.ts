import assert from "node:assert/strict";
import { test } from "node:test";
import type { Clock } from "../src/clock.ts";
import { createStore } from "../src/index.ts";
import { MemoryStore } from "../src/store.ts";
import { TtlStore } from "../src/ttl-store.ts";

class FakeClock implements Clock {
  t = 1000;
  now(): number {
    return this.t;
  }
}

function make(defaultTtl?: number): { store: TtlStore; clock: FakeClock; inner: MemoryStore } {
  const clock = new FakeClock();
  const inner = new MemoryStore();
  return { store: new TtlStore(inner, clock, defaultTtl), clock, inner };
}

test("values without a lifetime never expire", () => {
  const { store, clock } = make();
  store.set("a", "1");
  clock.t += 10 ** 12;
  assert.equal(store.get("a"), "1");
});

test("explicit ttl expires at exactly now + ttl", () => {
  const { store, clock } = make();
  store.set("a", "1", 100);
  clock.t = 1099;
  assert.equal(store.get("a"), "1");
  clock.t = 1100;
  assert.equal(store.get("a"), undefined);
});

test("default ttl applies and an explicit ttl overrides it", () => {
  const { store, clock } = make(50);
  store.set("a", "1");
  store.set("b", "2", 500);
  clock.t = 1060;
  assert.equal(store.get("a"), undefined);
  assert.equal(store.get("b"), "2");
});

test("overwriting resets the lifetime", () => {
  const { store, clock } = make();
  store.set("a", "1", 100);
  clock.t = 1050;
  store.set("a", "2", 100);
  clock.t = 1120;
  assert.equal(store.get("a"), "2");
  clock.t = 1150;
  assert.equal(store.get("a"), undefined);
});

test("overwriting without ttl makes the key permanent when there is no default", () => {
  const { store, clock } = make();
  store.set("a", "1", 10);
  store.set("a", "2");
  clock.t += 5000;
  assert.equal(store.get("a"), "2");
});

test("invalid lifetimes throw RangeError and store nothing", () => {
  const { store } = make();
  for (const bad of [0, -5, Number.NaN]) {
    assert.throws(() => store.set("a", "1", bad), RangeError);
  }
  assert.equal(store.get("a"), undefined);
  assert.deepEqual(store.keys(), []);
});

test("Infinity means no expiry", () => {
  const { store, clock } = make();
  store.set("a", "1", Infinity);
  clock.t += 10 ** 12;
  assert.equal(store.get("a"), "1");
});

test("keys skips expired entries and keeps order", () => {
  const { store, clock } = make();
  store.set("a", "1");
  store.set("b", "2", 10);
  store.set("c", "3");
  assert.deepEqual(store.keys(), ["a", "b", "c"]);
  clock.t += 10;
  assert.deepEqual(store.keys(), ["a", "c"]);
});

test("delete reports false for expired and missing keys", () => {
  const { store, clock } = make();
  store.set("a", "1", 10);
  store.set("b", "2");
  assert.equal(store.delete("b"), true);
  assert.equal(store.delete("b"), false);
  clock.t += 10;
  assert.equal(store.delete("a"), false);
  assert.equal(store.delete("zzz"), false);
});

test("deleted key stays gone when set again without ttl", () => {
  const { store, clock } = make();
  store.set("a", "1", 10);
  store.delete("a");
  store.set("a", "2");
  clock.t += 100;
  assert.equal(store.get("a"), "2");
});

test("sweep removes expired entries from the inner store and counts them", () => {
  const { store, clock, inner } = make();
  store.set("a", "1", 10);
  store.set("b", "2", 10);
  store.set("c", "3");
  assert.equal(store.sweep(), 0);
  clock.t += 10;
  assert.equal(store.sweep(), 2);
  assert.deepEqual(inner.keys(), ["c"]);
  assert.equal(store.sweep(), 0);
});

test("createStore with ttl returns a store whose entries expire", () => {
  const clock = new FakeClock();
  const store = createStore({ ttlMs: 100, clock });
  store.set("a", "1");
  assert.equal(store.get("a"), "1");
  clock.t += 100;
  assert.equal(store.get("a"), undefined);
});

test("createStore without options is a plain memory store", () => {
  const store = createStore();
  assert.ok(store instanceof MemoryStore);
  store.set("a", "1");
  assert.equal(store.get("a"), "1");
  assert.deepEqual(store.keys(), ["a"]);
  assert.equal(store.delete("a"), true);
});

test("memory store behaviour is unchanged", () => {
  const m = new MemoryStore();
  m.set("x", "1");
  m.set("y", "2");
  assert.deepEqual(m.keys(), ["x", "y"]);
  assert.equal(m.get("nope"), undefined);
});
