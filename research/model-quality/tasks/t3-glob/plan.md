The repository in the current directory matches file names against simple wildcard patterns (src/glob.ts)
and filters lists of names with them (src/filter.ts). One test fails: "a pattern must match the whole name"
in tests/glob.test.ts. Run it with `node --test tests/glob.test.ts`.

Symptom: matches("*.ts", "main.tsx") is true, and filterNames("*.ts", ["a.ts", "b.tsx"]) returns both names,
although "b.tsx" is not a TypeScript file.

The rule the code is meant to follow: a pattern matches a name only when it matches the entire name, not
just a part of it. In a pattern, "*" stands for any run of characters (including none), "?" stands for
exactly one character, and every other character, including ".", stands only for itself. filterNames keeps
the matching names in their original order.

Find the root cause in src/glob.ts and fix it there. Do not edit anything under tests/. The code must also
pass `npx tsc -p .`. Run the test file, then finish.
