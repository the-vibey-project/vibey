Refactor src/semver.ts: give its two public functions clearer names and pull the version parsing
out into its own function. Behaviour must not change: every call that works today must return the
same value, and every call that throws today must throw the same message.

1. Export an interface Version { major: number; minor: number; patch: number; prerelease: string[] }
   and a function parseVersion(v: string): Version. It accepts exactly the strings the code
   accepts today (an optional leading "v", build metadata after "+" is ignored) and throws
   Error("invalid version: " + v) for anything else. Each call returns a fresh object.
2. Export formatVersion(v: Version): string, which renders major.minor.patch and appends "-" plus the
   prerelease identifiers joined by "." when there are any. It never prints a "v" or build metadata.
3. Rename cmp to compareVersions and bump to bumpVersion (same parameters, same return values, same
   error messages, same order of validation). Both must be built on parseVersion and formatVersion.
4. The old names cmp and bump must remain exported from src/semver.ts and keep working exactly as
   before.
5. Use only erasable TypeScript (no enums, namespaces or parameter properties).

Keep tests/semver.test.ts passing and make sure `npx --yes --package typescript@5.9.3 tsc -p .`
reports no errors. Run the tests with `node --test tests/*.test.ts`. Then finish.
