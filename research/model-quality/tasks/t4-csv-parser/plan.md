Refactor src/csv.ts: pull the parsing out of the long parseCsv function into a class. Behaviour
must not change: parseCsv must return exactly what it returns today for every input, including
blank lines, quotes in the middle of a field, an unterminated quote and \r line endings.

1. Export a class CsvParser from src/csv.ts with the constructor
   new CsvParser(options?: CsvOptions), where CsvOptions is an exported interface
   { delimiter?: string } and the delimiter defaults to ",".
2. CsvParser has a public readonly property delimiter holding the delimiter in use, and a method
   parse(text: string): string[][] that does what parseCsv does today. Calling parse again on the
   same instance must start from a clean state and never reuse anything from an earlier call.
3. parseCsv(text: string, delimiter: string = ",") keeps its name and signature, stays exported
   from src/csv.ts, and now just delegates to CsvParser.
4. Use only erasable TypeScript (no enums, namespaces or parameter properties).

Keep tests/csv.test.ts passing and make sure `npx --yes --package typescript@5.9.3 tsc -p .`
reports no errors. Run the tests with `node --test tests/*.test.ts`. Then finish.
