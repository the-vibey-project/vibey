import { test } from "node:test";
import assert from "node:assert/strict";
import { parseCsv } from "../src/csv.ts";

test("plain rows", () => {
  assert.deepEqual(parseCsv("a,b\n1,2\n"), [["a", "b"], ["1", "2"]]);
});

test("quoted field with a comma and a doubled quote", () => {
  assert.deepEqual(parseCsv('"x,y","say ""hi"""'), [["x,y", 'say "hi"']]);
});

test("custom delimiter", () => {
  assert.deepEqual(parseCsv("a;b\n", ";"), [["a", "b"]]);
});

test("empty text has no rows", () => {
  assert.deepEqual(parseCsv(""), []);
});
