# Release process

> **Superseded — this describes a process that no longer runs.** This package was
> released from its own repository, under its own name on PyPI. Since vibey ADR-0021
> the source lives in the vibey monorepo, and since vibey ADR-0037 it is not published
> separately at all: the whole tree ships as the single `vibey-engine` package, released
> by the monorepo's own `release.yml`. The workflows named below are inert here. This
> page is kept because it records a real past process and why each gate existed — for
> the live one, read the monorepo's `CONTRIBUTING.md` and its `vibey-releasing` skill.

Nobody cuts releases here — the automation does. Versions are **derived from
what actually changed** by [vibey-gh](https://pypi.org/project/vibey-engine/) and
published to PyPI via
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC — no
long-lived token stored anywhere).

1. Feature PRs squash-merge into `develop`; every push to `develop` publishes
   a `.devN` build to TestPyPI.
2. `promote-to-main.yml` compares `develop` and `main` by content, opens the
   promotion PR when they differ, applies the derived version bump, waits for
   checks, and rebase-merges. That push publishes to PyPI (TestPyPI first,
   then a verify step, then PyPI).
3. After each publish, `develop` is fast-forwarded onto `main` automatically —
   never back-merge by hand.

`vibey-gh version --since origin/main --explain` shows the derivation. There
is no release-please, no standing release PR, and no manual tag in the normal
flow; a `v*` tag only attaches artifacts to a GitHub Release.
