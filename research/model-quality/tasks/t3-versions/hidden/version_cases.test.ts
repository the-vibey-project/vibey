import assert from "node:assert/strict";
import { test } from "node:test";
import { compareVersions } from "../src/version.ts";
import { latest, sortVersions } from "../src/latest.ts";

test("two-digit minor beats one-digit minor", () => {
  assert.ok(compareVersions("1.10.0", "1.9.9") > 0);
  assert.ok(compareVersions("1.9.9", "1.10.0") < 0);
});

test("two-digit major beats one-digit major", () => {
  assert.ok(compareVersions("10.0.0", "9.99.99") > 0);
  assert.ok(compareVersions("2.0", "10.0") < 0);
});

test("two-digit patch", () => {
  assert.ok(compareVersions("1.0.100", "1.0.20") > 0);
});

test("missing trailing parts count as zero", () => {
  assert.equal(compareVersions("1.2", "1.2.0"), 0);
  assert.equal(compareVersions("1.2.0.0", "1.2"), 0);
  assert.ok(compareVersions("1.2", "1.2.1") < 0);
  assert.ok(compareVersions("1.2.1", "1.2") > 0);
});

test("equal versions", () => {
  assert.equal(compareVersions("3.4.5", "3.4.5"), 0);
});

test("simple ordering still works", () => {
  assert.ok(compareVersions("1.2.3", "1.2.4") < 0);
  assert.ok(compareVersions("2.0.0", "1.99.99") > 0);
});

test("latest picks the numerically newest", () => {
  assert.equal(latest(["1.9.0", "1.10.0", "1.2.0"]), "1.10.0");
  assert.equal(latest(["9.0", "10.0", "8.5"]), "10.0");
});

test("latest of an empty list is undefined", () => {
  assert.equal(latest([]), undefined);
});

test("sortVersions orders oldest to newest", () => {
  assert.deepEqual(sortVersions(["1.10.0", "1.2.0", "1.9.1", "1.9.0"]), [
    "1.2.0",
    "1.9.0",
    "1.9.1",
    "1.10.0",
  ]);
});

test("sortVersions does not change its argument", () => {
  const input = ["2.0.0", "1.0.0"];
  sortVersions(input);
  assert.deepEqual(input, ["2.0.0", "1.0.0"]);
});
