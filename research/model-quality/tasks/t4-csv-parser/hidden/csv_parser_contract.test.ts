import { test } from "node:test";
import assert from "node:assert/strict";
import { CsvParser, parseCsv } from "../src/csv.ts";

const CASES: [string, string[][]][] = [
  ["a,b\n1,2\n", [["a", "b"], ["1", "2"]]],
  ["a,b\r\nc\r\n", [["a", "b"], ["c"]]],
  ["x\ry\rz", [["x"], ["y"], ["z"]]],
  ["", []],
  ["\n", [[""]]],
  ["\r", [[""]]],
  ["a\n", [["a"]]],
  ["a\n\n", [["a"], [""]]],
  ["a,b\n\nc", [["a", "b"], [""], ["c"]]],
  ["a,", [["a", ""]]],
  ["a,b,,\n,c", [["a", "b", "", ""], ["", "c"]]],
  ['""', [[""]]],
  ['""""', [['"']]],
  ['"a"""," ""b"', [['a"', ' "b']]],
  ['"l1\nl2",x', [["l1\nl2", "x"]]],
  ['"a,"\n,', [["a,"], ["", ""]]],
  ['ab"cd', [['ab"cd']]],
  ['"ab"cd', [["abcd"]]],
  [' "a"', [[' "a"']]],
  ['"unterminated', [["unterminated"]]],
  ['a,"b"\n', [["a", "b"]]],
];

for (const [input, expected] of CASES) {
  test(`CsvParser default delimiter: ${JSON.stringify(input)}`, () => {
    assert.deepEqual(new CsvParser().parse(input), expected);
    assert.deepEqual(new CsvParser({}).parse(input), expected);
  });
}

test("parseCsv still gives the same rows", () => {
  for (const [input, expected] of CASES) {
    assert.deepEqual(parseCsv(input), expected);
    assert.deepEqual(parseCsv(input, ","), expected);
  }
});

test("a delimiter option is honoured by the class and by parseCsv", () => {
  assert.deepEqual(new CsvParser({ delimiter: "\t" }).parse("a\tb,c\n1\t2"), [["a", "b,c"], ["1", "2"]]);
  assert.deepEqual(new CsvParser({ delimiter: ";" }).parse('a;b;"c;d"\n'), [["a", "b", "c;d"]]);
  assert.deepEqual(parseCsv("a|b\n", "|"), [["a", "b"]]);
  assert.deepEqual(parseCsv("a;b,c\n", ";"), [["a", "b,c"]]);
});

test("the delimiter is exposed and defaults to a comma", () => {
  assert.equal(new CsvParser().delimiter, ",");
  assert.equal(new CsvParser({ delimiter: "|" }).delimiter, "|");
  assert.equal(new CsvParser({}).delimiter, ",");
});

test("one parser can parse many texts, each result independent", () => {
  const parser = new CsvParser();
  const first = parser.parse('a,"b\nc');
  const second = parser.parse("x,y\n");
  const third = parser.parse('a,"b\nc');
  assert.deepEqual(first, [["a", "b\nc"]]);
  assert.deepEqual(second, [["x", "y"]]);
  assert.deepEqual(third, first);
  assert.notEqual(third, first);
  first[0]![0] = "changed";
  assert.deepEqual(parser.parse('a,"b\nc'), [["a", "b\nc"]]);
});

test("an unterminated quote in one call does not leak into the next", () => {
  const parser = new CsvParser();
  parser.parse('"never closed,still open');
  assert.deepEqual(parser.parse("a,b"), [["a", "b"]]);
});

test("two parsers with different delimiters do not interfere", () => {
  const semi = new CsvParser({ delimiter: ";" });
  const comma = new CsvParser();
  assert.deepEqual(semi.parse("a;b"), [["a", "b"]]);
  assert.deepEqual(comma.parse("a;b"), [["a;b"]]);
  assert.deepEqual(semi.parse("a,b"), [["a,b"]]);
});
