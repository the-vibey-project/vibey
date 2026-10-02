* **gh:** `vibey-gh advisory-check` replaces `npm audit --audit-level=high` in CI. Every npm
  advisory at high or worse still fails, except one declared in
  `.github/advisory-exceptions.toml`. A declared exception is a reviewed decision that the
  vulnerable code is not reached, and it expires within 30 days (`[advisories]`). Every run
  prints the exceptions it honours. An exception fails the check once it has expired, matches
  nothing, or a patched release replaces it. The file is a protected path. The first exception
  is GHSA-86w9-cpqp-85rv: node-forge <= 1.4.0, with no patched release. It is reached only
  through Expo's developer CLI and is in neither the web nor the Android bundle. It expires on
  2026-10-31.
