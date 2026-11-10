import { test } from "node:test";
import assert from "node:assert/strict";
import { formatBytes } from "../src/bytes.ts";

test("small values are plain bytes", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(1), "1 B");
  assert.equal(formatBytes(1023), "1023 B");
});

test("exact powers", () => {
  assert.equal(formatBytes(1024), "1 KiB");
  assert.equal(formatBytes(1048576), "1 MiB");
  assert.equal(formatBytes(1024 ** 3), "1 GiB");
  assert.equal(formatBytes(1024 ** 4), "1 TiB");
});

test("one decimal place", () => {
  assert.equal(formatBytes(1536), "1.5 KiB");
  assert.equal(formatBytes(1500), "1.5 KiB");
  assert.equal(formatBytes(2048 + 300), "2.3 KiB");
  assert.equal(formatBytes(5 * 1024 * 1024 + 512 * 1024), "5.5 MiB");
});

test("trailing .0 is dropped", () => {
  assert.equal(formatBytes(1030), "1 KiB");
  assert.equal(formatBytes(3 * 1024), "3 KiB");
});

test("rounding carries into the next unit", () => {
  assert.equal(formatBytes(1048575), "1 MiB");
  assert.equal(formatBytes(1024 ** 3 - 1), "1 GiB");
  assert.equal(formatBytes(1048064), "1023.5 KiB");
});

test("TiB is the largest unit", () => {
  assert.equal(formatBytes(1024 ** 5), "1024 TiB");
  assert.equal(formatBytes(3 * 1024 ** 4), "3 TiB");
});

test("invalid input throws RangeError", () => {
  for (const bad of [-1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, -1024]) {
    assert.throws(() => formatBytes(bad), RangeError, String(bad));
  }
});
