import { test } from "node:test";
import assert from "node:assert/strict";
import { compareVersions } from "../src/semver.ts";

test("core comparison is numeric", () => {
  assert.equal(compareVersions("1.10.0", "1.9.0"), 1);
  assert.equal(compareVersions("1.2.3", "1.2.4"), -1);
  assert.equal(compareVersions("2.0.0", "10.0.0"), -1);
  assert.equal(compareVersions("1.2.3", "1.2.3"), 0);
  assert.equal(compareVersions("0.0.0", "0.0.0"), 0);
});

test("prerelease is lower than release", () => {
  assert.equal(compareVersions("1.0.0-rc.1", "1.0.0"), -1);
  assert.equal(compareVersions("1.0.0", "1.0.0-rc.1"), 1);
});

test("prerelease ordering chain", () => {
  const chain = [
    "1.0.0-alpha",
    "1.0.0-alpha.1",
    "1.0.0-alpha.beta",
    "1.0.0-beta",
    "1.0.0-beta.2",
    "1.0.0-beta.11",
    "1.0.0-rc.1",
    "1.0.0",
  ];
  for (let i = 0; i < chain.length - 1; i++) {
    assert.equal(compareVersions(chain[i]!, chain[i + 1]!), -1, `${chain[i]} < ${chain[i + 1]}`);
    assert.equal(compareVersions(chain[i + 1]!, chain[i]!), 1);
  }
});

test("numeric identifiers compare numerically", () => {
  assert.equal(compareVersions("1.0.0-2", "1.0.0-10"), -1);
  assert.equal(compareVersions("1.0.0-alpha.9", "1.0.0-alpha.10"), -1);
});

test("numeric identifier is lower than text identifier", () => {
  assert.equal(compareVersions("1.0.0-1", "1.0.0-a"), -1);
  assert.equal(compareVersions("1.0.0-a", "1.0.0-1"), 1);
});

test("text identifiers compare in ASCII order", () => {
  assert.equal(compareVersions("1.0.0-Beta", "1.0.0-alpha"), -1);
  assert.equal(compareVersions("1.0.0-alpha", "1.0.0-beta"), -1);
});

test("build metadata is ignored", () => {
  assert.equal(compareVersions("1.0.0+a", "1.0.0+b"), 0);
  assert.equal(compareVersions("1.0.0-rc.1+x", "1.0.0-rc.1"), 0);
  assert.equal(compareVersions("1.0.1+a", "1.0.0+z"), 1);
});

test("major dominates prerelease", () => {
  assert.equal(compareVersions("2.0.0-alpha", "1.9.9"), 1);
});

test("invalid versions throw", () => {
  for (const bad of ["1.2", "01.2.3", "1.2.3-", "v1.2.3", "", "1.2.3.4", "a.b.c", "1.2.3+"]) {
    assert.throws(() => compareVersions(bad, "1.0.0"), Error, bad);
    assert.throws(() => compareVersions("1.0.0", bad), Error, bad);
  }
});
