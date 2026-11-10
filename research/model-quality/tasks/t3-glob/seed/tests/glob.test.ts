import assert from "node:assert/strict";
import { test } from "node:test";
import { filterNames } from "../src/filter.ts";
import { matches } from "../src/glob.ts";

test("a star matches a run of characters", () => {
  assert.equal(matches("*.ts", "main.ts"), true);
  assert.equal(matches("*.ts", "readme.md"), false);
});

test("a pattern must match the whole name", () => {
  assert.equal(matches("*.ts", "main.tsx"), false);
  assert.deepEqual(filterNames("*.ts", ["a.ts", "b.tsx"]), ["a.ts"]);
});
