import assert from "node:assert/strict";
import { test } from "node:test";
import { compareVersions } from "../src/version.ts";
import { latest } from "../src/latest.ts";

test("plain ordering", () => {
  assert.ok(compareVersions("1.2.3", "1.2.4") < 0);
  assert.equal(compareVersions("2.0.0", "2.0.0"), 0);
});

test("1.10.0 is newer than 1.9.0", () => {
  assert.ok(compareVersions("1.10.0", "1.9.0") > 0);
  assert.equal(latest(["1.9.0", "1.10.0", "1.2.0"]), "1.10.0");
});
