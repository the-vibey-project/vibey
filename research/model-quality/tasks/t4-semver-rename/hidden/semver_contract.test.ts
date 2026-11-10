import { test } from "node:test";
import assert from "node:assert/strict";
import { bump, bumpVersion, cmp, compareVersions, formatVersion, parseVersion } from "../src/semver.ts";

test("parseVersion splits a version into numbers and prerelease identifiers", () => {
  assert.deepEqual(parseVersion("1.2.3"), { major: 1, minor: 2, patch: 3, prerelease: [] });
  assert.deepEqual(parseVersion("v10.0.7"), { major: 10, minor: 0, patch: 7, prerelease: [] });
  assert.deepEqual(parseVersion("1.2.3-rc.1"), { major: 1, minor: 2, patch: 3, prerelease: ["rc", "1"] });
  assert.deepEqual(parseVersion("v0.0.1-alpha.beta.7+build.5"), {
    major: 0,
    minor: 0,
    patch: 1,
    prerelease: ["alpha", "beta", "7"],
  });
  assert.deepEqual(parseVersion("2.0.0+meta"), { major: 2, minor: 0, patch: 0, prerelease: [] });
});

test("parseVersion returns a fresh object each time", () => {
  const a = parseVersion("1.2.3-rc.1");
  a.prerelease.push("x");
  a.major = 9;
  assert.deepEqual(parseVersion("1.2.3-rc.1"), { major: 1, minor: 2, patch: 3, prerelease: ["rc", "1"] });
});

for (const bad of ["1.2", "1.2.3.4", "x", "", "1.2.3-", "V1.2.3", " 1.2.3", "1.2.3 ", "1.2.x"]) {
  test(`parseVersion rejects ${JSON.stringify(bad)}`, () => {
    assert.throws(() => parseVersion(bad), (err: Error) => err.message === "invalid version: " + bad);
  });
}

test("formatVersion drops the v prefix and build metadata and joins the prerelease", () => {
  assert.equal(formatVersion({ major: 1, minor: 2, patch: 3, prerelease: [] }), "1.2.3");
  assert.equal(formatVersion({ major: 0, minor: 10, patch: 0, prerelease: ["rc", "1"] }), "0.10.0-rc.1");
  assert.equal(formatVersion(parseVersion("v4.5.6-beta+x")), "4.5.6-beta");
});

const ORDER: [string, string][] = [
  ["1.2.3", "1.10.0"],
  ["1.9.9", "2.0.0"],
  ["9.0.0", "10.0.0"],
  ["0.0.9", "0.0.10"],
  ["1.0.0-alpha", "1.0.0-alpha.1"],
  ["1.0.0-alpha.1", "1.0.0-alpha.beta"],
  ["1.0.0-alpha.beta", "1.0.0-beta"],
  ["1.0.0-beta.2", "1.0.0-beta.11"],
  ["1.0.0-rc.1", "1.0.0"],
  ["1.0.0-1", "1.0.0-a"],
  ["1.0.0-B", "1.0.0-a"],
  ["1.0.0-9", "1.0.0-10"],
];

test("compareVersions orders versions, and swapping the arguments flips the sign", () => {
  for (const [lower, higher] of ORDER) {
    assert.equal(compareVersions(lower, higher), -1, `${lower} < ${higher}`);
    assert.equal(compareVersions(higher, lower), 1, `${higher} > ${lower}`);
  }
});

test("compareVersions treats equal versions, the v prefix and build metadata as equal", () => {
  assert.equal(compareVersions("1.2.3", "1.2.3"), 0);
  assert.equal(compareVersions("1.0.0", "v1.0.0"), 0);
  assert.equal(compareVersions("1.0.0+a", "1.0.0+b"), 0);
  assert.equal(compareVersions("1.2.3-rc.1", "v1.2.3-rc.1+z"), 0);
});

test("compareVersions validates the first argument before the second", () => {
  assert.throws(() => compareVersions("1.2", "1.2.3"), /^Error: invalid version: 1\.2$/);
  assert.throws(() => compareVersions("1.2.3", "x"), /^Error: invalid version: x$/);
  assert.throws(() => compareVersions("a", "b"), /^Error: invalid version: a$/);
});

const BUMPS: [string, string, string][] = [
  ["1.2.3", "major", "2.0.0"],
  ["v1.2.3-rc.1", "major", "2.0.0"],
  ["1.2.3", "minor", "1.3.0"],
  ["1.2.3-rc.2", "minor", "1.3.0"],
  ["1.2.3", "patch", "1.2.4"],
  ["0.0.9", "patch", "0.0.10"],
  ["1.2.3-rc.1+b5", "patch", "1.2.3"],
  ["v1.2.3+meta", "patch", "1.2.4"],
  ["1.2.3", "prerelease", "1.2.4-rc.0"],
  ["1.2.3-rc.9", "prerelease", "1.2.3-rc.10"],
  ["1.2.3-beta", "prerelease", "1.2.3-beta.0"],
  ["1.2.3-1", "prerelease", "1.2.3-2"],
  ["1.2.3-alpha.beta.7", "prerelease", "1.2.3-alpha.beta.8"],
];

test("bumpVersion", () => {
  for (const [from, kind, to] of BUMPS) {
    assert.equal(bumpVersion(from, kind), to, `${from} ${kind}`);
  }
});

test("bumpVersion rejects unknown kinds and bad versions, parsing the version first", () => {
  assert.throws(() => bumpVersion("1.2.3", "huge"), /^Error: unknown bump kind: huge$/);
  assert.throws(() => bumpVersion("1.2.3", "Major"), /^Error: unknown bump kind: Major$/);
  assert.throws(() => bumpVersion("bad", "nonsense"), /^Error: invalid version: bad$/);
  assert.throws(() => bumpVersion("1.2.3.4", "patch"), /^Error: invalid version: 1\.2\.3\.4$/);
});

test("the old names cmp and bump keep working with identical results", () => {
  for (const [lower, higher] of ORDER) {
    assert.equal(cmp(lower, higher), -1);
    assert.equal(cmp(higher, lower), 1);
  }
  assert.equal(cmp("1.0.0", "v1.0.0"), 0);
  for (const [from, kind, to] of BUMPS) {
    assert.equal(bump(from, kind), to);
  }
  assert.throws(() => cmp("1.2", "1.2.3"), /invalid version: 1\.2/);
  assert.throws(() => bump("1.2.3", "huge"), /unknown bump kind: huge/);
});

test("bumping twice walks through prerelease numbers and then releases", () => {
  let v = "1.0.0";
  v = bumpVersion(v, "prerelease");
  assert.equal(v, "1.0.1-rc.0");
  v = bumpVersion(v, "prerelease");
  assert.equal(v, "1.0.1-rc.1");
  v = bumpVersion(v, "patch");
  assert.equal(v, "1.0.1");
});
