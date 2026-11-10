Create src/semver.ts exporting a function compareVersions(a: string, b: string): -1 | 0 | 1 that
compares two semantic version strings. It returns -1 if a is lower than b, 1 if a is higher, 0 if equal.

A version is MAJOR.MINOR.PATCH (three non-negative integers without leading zeros, except 0 itself),
optionally followed by "-" and a dot-separated prerelease, optionally followed by "+" and build metadata.
Examples: "1.2.3", "1.0.0-alpha.1", "2.0.0+build.5".
- Compare MAJOR, then MINOR, then PATCH, numerically ("1.10.0" is higher than "1.9.0").
- A version with a prerelease is lower than the same MAJOR.MINOR.PATCH without one:
  "1.0.0-rc.1" is lower than "1.0.0".
- Two prereleases are compared identifier by identifier (split on "."). Identifiers made only of
  digits compare numerically; other identifiers compare as plain strings (ASCII order); a numeric
  identifier is always lower than a non-numeric one; if all shared identifiers are equal, the
  prerelease with fewer identifiers is lower. So "1.0.0-alpha" < "1.0.0-alpha.1" < "1.0.0-alpha.beta"
  < "1.0.0-beta" < "1.0.0-beta.2" < "1.0.0-beta.11" < "1.0.0-rc.1".
- Build metadata is ignored: "1.0.0+a" and "1.0.0+b" are equal.
- If either string is not a valid version (for example "1.2", "01.2.3", "1.2.3-", "v1.2.3", ""), throw
  an Error.
Do not import any modules. Use only erasable TypeScript (no enums, namespaces or parameter properties).
