The repository in the current directory compares dotted version numbers (src/version.ts) and picks the
newest one (src/latest.ts). One test fails: "1.10.0 is newer than 1.9.0" in tests/version.test.ts. Run it
with `node --test tests/version.test.ts`.

Symptom: compareVersions("1.10.0", "1.9.0") says the older release is newer, so latest() picks the wrong
version once any number reaches two digits.

The rule the code is meant to follow: a version is dot-separated whole numbers. They are compared left to
right as numbers, not as text. compareVersions returns a negative number, 0 or a positive number. A missing
trailing part counts as 0, so "1.2" and "1.2.0" are equal. latest() returns the newest version in the list,
or undefined for an empty list, and sortVersions() returns a new array from oldest to newest without
changing its argument.

Find the root cause in src/version.ts and fix it there. Do not edit anything under tests/. The code must
also pass `npx tsc -p .`. Run the test file, then finish.
