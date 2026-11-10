import { test } from "node:test";
import assert from "node:assert/strict";
import { bump, cmp } from "../src/semver.ts";

test("cmp orders by number", () => {
  assert.equal(cmp("1.2.3", "1.10.0"), -1);
  assert.equal(cmp("2.0.0", "1.9.9"), 1);
  assert.equal(cmp("1.0.0", "v1.0.0"), 0);
});

test("a prerelease is lower than its release", () => {
  assert.equal(cmp("1.0.0-rc.1", "1.0.0"), -1);
});

test("bump", () => {
  assert.equal(bump("1.2.3", "minor"), "1.3.0");
  assert.equal(bump("1.2.3-rc.1", "patch"), "1.2.3");
  assert.equal(bump("1.2.3", "prerelease"), "1.2.4-rc.0");
});

test("invalid input throws", () => {
  assert.throws(() => cmp("1.2", "1.2.3"), /invalid version/);
});
