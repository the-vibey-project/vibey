- **Feature:** `vibey-gh advisory-check [--workspace PATH]... [--audit-file JSON]` is
  `npm audit --audit-level=<level>` with declared, expiring exceptions (`[advisories]`:
  `audit_level`, `exceptions_file`, `max_exception_days`, `warn_days`). Each `[[exception]]`
  names one GHSA advisory, package and workspace, gives the reachability reason, `added`,
  `expires` (at most `max_exception_days` later) and `retire_when`, and may link `upstream`.
  The check prints each exception it honours, its expiry, and the packages flagged only
  because of it. It exits 1 on:
  - an unexcepted advisory;
  - an expired exception;
  - a stale exception (matches nothing at the level);
  - an exception whose package has a patched release in the GitHub advisory database;
  - an exception for a workspace with no lockfile.

  An npm error, an unreadable report, a package with no advisory behind its severity, or an
  unreadable advisory database is refused, never passed.
