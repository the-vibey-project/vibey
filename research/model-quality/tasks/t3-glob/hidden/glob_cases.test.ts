import assert from "node:assert/strict";
import { test } from "node:test";
import { filterNames } from "../src/filter.ts";
import { matches } from "../src/glob.ts";

test("trailing text after the match is rejected", () => {
  assert.equal(matches("*.ts", "main.tsx"), false);
  assert.equal(matches("*.ts", "main.ts.bak"), false);
});

test("leading text before the match is rejected", () => {
  assert.equal(matches("readme", "my-readme"), false);
  assert.equal(matches("readme", "readme"), true);
});

test("a literal pattern needs an exact name", () => {
  assert.equal(matches("a.txt", "a.txt.old"), false);
  assert.equal(matches("a.txt", "xa.txt"), false);
});

test("question mark is exactly one character", () => {
  assert.equal(matches("a?c", "abc"), true);
  assert.equal(matches("a?c", "xabcx"), false);
  assert.equal(matches("a?c", "ac"), false);
  assert.equal(matches("a?c", "abbc"), false);
});

test("star in the middle", () => {
  assert.equal(matches("a*c", "abc"), true);
  assert.equal(matches("a*c", "ac"), true);
  assert.equal(matches("a*c", "abcd"), false);
});

test("a lone star matches anything", () => {
  assert.equal(matches("*", ""), true);
  assert.equal(matches("*", "whatever.txt"), true);
});

test("a dot is a literal dot", () => {
  assert.equal(matches("a.b", "a.b"), true);
  assert.equal(matches("a.b", "axb"), false);
});

test("other regular expression characters are literal", () => {
  assert.equal(matches("a+b", "a+b"), true);
  assert.equal(matches("a+b", "aab"), false);
  assert.equal(matches("(x)", "(x)"), true);
});

test("filterNames keeps order and drops partial matches", () => {
  assert.deepEqual(filterNames("*.ts", ["z.ts", "a.tsx", "b.ts", "c.d.ts"]), ["z.ts", "b.ts", "c.d.ts"]);
  assert.deepEqual(filterNames("v?.md", ["v1.md", "v10.md", "xv1.md"]), ["v1.md"]);
});

test("filterNames of nothing is nothing", () => {
  assert.deepEqual(filterNames("*", []), []);
});
