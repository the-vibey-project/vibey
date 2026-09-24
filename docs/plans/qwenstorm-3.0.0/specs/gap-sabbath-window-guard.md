## Title
feat(gh): the merge train and promotion stand down for the Sabbath (8.i)

## Why
Sub-doctrine **8.i, the Sabbath** was ratified into the canon on 2026-09-22 (`origin/develop`
commit `2838c62d`, PR #398; `src/vibey_tools/gh/docs/doctrines.md:335-352`): "from sundown
Friday to sundown Saturday, nothing in this family writes, merges, tests, or ships code — no
exceptions, ever … the merge train does not run, `promote-to-main` does not fire, a scheduled
workflow that would land inside the window is held rather than silently skipped … Every job
already on a queue waits exactly where 8.c and 8.e put it … (10.f: paused, not failed, not
silently dropped)".

Nothing in `vibey_gh` reads the day of the week. `grep -rniE "weekday|sabbath|isoweekday"
src/vibey_tools/gh/vibey_gh/` finds nothing, and the two entry points the doctrine names by
hand are unguarded:

- `vibey_gh/cli.py:222-310`, `_merge_train(args)`, opens with `cfg = load_config()` and goes
  straight to `merge_train.open_pull_requests(cfg, …)`. It then labels
  (`merge_train.hold_for_review`, cli.py:270), comments, pushes a local merge-forward
  (`reconcile.merge_forward`, cli.py:257), and merges (`merge_train.merge`, cli.py:290 →
  `merge_train.py:356-388`, which runs `gh pr merge` and falls back to `--admin`). Every one
  of those is a write, at any hour of any day.
- `vibey_gh/cli.py:441-453`, `_promote(args)`, calls `promote.promote(load_config(), …)`
  (`promote.py:145-251`), which commits a version bump, **pushes it to the integration
  branch** (`promote.py:203`), and opens or refreshes the promotion pull request.

The workflows that drive them run on clocks and events that fall inside the window with no
guard at all: `templates/workflows/merge-train.yml:8-23` triggers on every completed PR-review
run plus `cron: "17 7 * * 1"`, and `templates/workflows/promote-to-main.yml:20-31` follows the
merge train's success plus `cron: "17 8 * * 1"`. A pull request whose review gate goes green at
02:00 on a Saturday is merged, promoted and published — which 8.i now forbids without
exception.

This lane closes that gap at the one place both workflows actually enter the code: the
`vibey-gh` command line. It makes the window a declared, configurable fact
(sub-doctrine 12.c), not a constant, and it makes a held run say so where a person looks, so
the run is *paused*, not *silently skipped* (10.f).

## Required behaviour
Every path is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`)
except `.vibey-gh.toml`, which is the **repository root's** file.

1. **A declared window, never a computed one.** Real sundown is astronomical: it moves about
   four hours across a year, and knowing it needs either a network call or an ephemeris
   dependency. `vibey-gh` declares `dependencies = []` on purpose
   (`src/vibey_tools/gh/pyproject.toml:27-30`: "This is release tooling… each dependency it
   grows is a dependency all of them grow"), and 8.i has no "look it up" clause. So the window
   is **declared** in `.vibey-gh.toml`, in wall-clock time in a named IANA zone, and it is
   deliberately **wider** than any true sundown at that latitude: `opens` at or before the
   earliest sunset of the year, `closes` at or after the latest. A declared window may only
   ever err **toward rest** — erring the other way would let a merge land inside the real
   window, which 8.i forbids.
2. **New `[sabbath]` table**, loaded into `GhConfig.sabbath` as a frozen `SabbathConfig`:
   - `enabled: bool = True`
   - `timezone: str = "America/New_York"` — the operator's zone; every commit on this
     repository is stamped in it (`2838c62d` is `2026-09-22 17:12:16 -0400`, EDT).
   - `opens: str = "16:00"` — before the earliest sunset in that zone (about 16:28, early
     December).
   - `closes: str = "21:00"` — after the latest sunset in that zone (about 20:31, late June).
3. `SabbathConfig.__post_init__` rejects a bad declaration **at load**, naming the key:
   - a `timezone` this machine's time-zone database cannot resolve;
   - an `opens` or `closes` that is not a 24-hour `HH:MM` wall clock.
   There is no "assume it is not the Sabbath" fallback: 8.i has no exception, so an
   unanswerable window is an error, not a pass.
4. **New `SabbathWindow` class** (`vibey_gh/sabbath.py`) with an interface beside it
   (`vibey_gh/interfaces/sabbath_window_interface.py`, ADR-0016). Its one verb:
   `hold(at: datetime | None = None) -> Hold | None`.
   - `None` means "proceed": outside the window, or `enabled` is false.
   - A `Hold` means "stand down", and carries `opened` and `resumes` as timezone-aware
     `datetime`s in the declared zone.
   - `at` defaults to the injected clock (`datetime.now(UTC)`), so a test names the moment
     instead of waiting for one — the same seam `forge_snapshot.py:520` already uses.
   - `at` may be in any zone; it is converted to the declared zone before judging.
   - The window is anchored on Friday (`datetime.weekday() == 4`): it opens at `opens` on the
     most recent Friday and closes at `closes` on the Saturday after it. Daylight saving is
     handled by `zoneinfo`, not by arithmetic.
5. **`vibey-gh merge-train` is held.** `cli._merge_train` consults the window as the very
   first thing after `load_config()` — before anything is listed, judged, labelled, commented
   on, restacked or merged. Guarding `merge_train.merge()` alone would be wrong: the train
   writes to a contributor's branch (`reconcile.merge_forward`) and to a pull request
   (`hold_for_review`) long before it merges anything.
6. **`vibey-gh promote` is held.** `cli._promote` consults the window before calling
   `promote.promote(...)` — before the version bump, its push, and the promotion pull request.
7. **Held, not skipped.** A run that exits 0 having done nothing in silence *is* a silent
   skip. A held run must therefore, in both commands:
   - print exactly one line to stdout: `vibey-gh: ` + `Hold.report()`, which names the
     sub-doctrine, the moment the window opened, and the moment it resumes;
   - append `Hold.summary()` — markdown naming the window, the resume moment, and the words
     "paused, not failed" — through the existing `cli._write_summary(args, text)`
     (`cli.py:408-418`), which writes to `--summary` or `$GITHUB_STEP_SUMMARY`. Both
     subparsers already declare `--summary` (`cli.py:1303-1307`, `cli.py:1420-1422`), so the
     held state lands on the GitHub Actions run summary page with **no workflow change at
     all**;
   - return **0**. 10.f: paused is not failed. A non-zero exit under the workflows'
     `set -euo pipefail` would paint the run red and make a rested week look like a broken
     one.
8. **Resumed, not lost.** The lane adds no new trigger, on purpose. `merge-train.yml` already
   re-attempts held work on the next completed PR-review run *and* on `cron: "17 7 * * 1"`
   (template lines 8-12); `promote-to-main.yml` follows the merge train's success and has
   `cron: "17 8 * * 1"` (lines 20-24); both have `workflow_dispatch`. Nothing is dropped —
   the work waits on the pull request where it already sits and the next trigger after the
   window takes it. A dedicated post-window resume cron would be a *hard-coded* cadence in a
   rendered template, which sub-doctrine 12.c forbids; making it a declared key needs a new
   `__VIBEY_GH_…__` placeholder and an installer re-render, and that is a **separate lane**
   (see "Out of scope").
9. Nothing else changes behaviour. Outside the window, and with `enabled = false`, every
   existing code path runs exactly as it does today.

## Where to change
### Create `vibey_gh/interfaces/sabbath_window_interface.py`
Copy the shape and the provenance header from
`vibey_gh/interfaces/protected_paths_interface.py:1-11`. Interfaces declare, never consume, so
this file must **not** import `vibey_gh.sabbath`; the value protocol is declared here too, the
way `vibey_gh/interfaces/class_contracts.py:57-78` declares `ChangeRequestInterface` for
`vibey_gh.forge.ChangeRequest`.

```python
class HoldInterface(Protocol):
    """A writer standing down for the Sabbath, and the moment it resumes."""

    @property
    def opened(self) -> datetime: ...

    @property
    def resumes(self) -> datetime: ...

    def report(self) -> str:
        """One line for the log: what is held, under which rule, and until when."""
        ...

    def summary(self) -> str:
        """The same fact as markdown for a job summary, so a held run is visible where a
        person looks rather than being an empty green box."""
        ...


class SabbathWindowInterface(Protocol):
    """Decides whether sub-doctrine 8.i is holding a given moment."""

    def hold(self, at: datetime | None = None) -> HoldInterface | None:
        """The hold in force at `at` -- the clock when omitted -- or `None` when the caller
        may proceed. Never raises: `None` is the only permission to write."""
        ...
```

### Create `vibey_gh/sabbath.py`
Provenance header copied from a neighbour (`vibey_gh/protected_paths.py:1`). A module
docstring explaining the declared window (behaviour 1). Then:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial

from vibey_gh.config import SabbathConfig

__all__ = ["Hold", "SabbathWindow"]

# Friday is 4 in `datetime.weekday()`. The window opens on it and closes the next day.
_FRIDAY = 4


@dataclass(frozen=True)
class Hold:
    """Implements `HoldInterface`. A value, like `merge_train.Verdict`
    (merge_train.py:46) and `promote.Promotion` (promote.py:56)."""

    opened: datetime
    resumes: datetime

    def report(self) -> str:
        return (
            "held for the Sabbath (sub-doctrine 8.i): the window opened "
            f"{self.opened.isoformat()} and closes {self.resumes.isoformat()}; "
            "nothing merges or ships until then"
        )

    def summary(self) -> str:
        return (
            "## Held for the Sabbath\n\n"
            "Sub-doctrine 8.i: nothing writes, merges, tests or ships from sundown Friday"
            " to sundown Saturday.\n\n"
            f"- Window opened: `{self.opened.isoformat()}`\n"
            f"- Resumes: `{self.resumes.isoformat()}`\n"
            "- Nothing was merged, shipped, labelled or commented on. This run is paused,"
            " not failed (10.f); the next trigger after the window takes the work where"
            " it stands.\n"
        )


class SabbathWindow:
    """Implements `SabbathWindowInterface`."""

    def __init__(
        self, config: SabbathConfig, *, clock: Callable[[], datetime] | None = None
    ) -> None:
        self._config = config
        # The injected-clock seam `forge_snapshot.py:520` already uses, so a test names the
        # moment rather than waiting for one.
        self._clock = clock if clock is not None else partial(datetime.now, UTC)

    def hold(self, at: datetime | None = None) -> Hold | None:
        if not self._config.enabled:
            return None
        zone = self._config.zone()
        local = (at if at is not None else self._clock()).astimezone(zone)
        friday = local.date() - timedelta(days=(local.weekday() - _FRIDAY) % 7)
        opened = datetime.combine(friday, self._config.opens_at(), tzinfo=zone)
        resumes = datetime.combine(
            friday + timedelta(days=1), self._config.closes_at(), tzinfo=zone
        )
        if opened <= local < resumes:
            return Hold(opened=opened, resumes=resumes)
        return None
```

Why that arithmetic is right, and worth a comment at the `friday` line: `(weekday() - 4) % 7`
is 0 on Friday, 1 on Saturday, and 3..6 Monday through Thursday, so the anchor is always the
Friday of the window that could still be open. On a Friday morning `local < opened`; from
Sunday to Thursday `local >= resumes`; only Friday evening and Saturday fall between.

### Edit `vibey_gh/config.py`
- Module imports (`config.py:42-51`). Add, in isort order, `import re` is already there; add
  `from datetime import time` and `from zoneinfo import ZoneInfo, ZoneInfoNotFoundError`.
  **Do not** add a bare `import datetime` or `from datetime import datetime`: `config.py:428`
  has a function-local `import datetime` and a module-level name of the same spelling reads as
  a bug even though Python allows it.
- A module-level helper beside `_finite_forecast_number` (`config.py:56-63`), which is the
  precedent for "validate a TOML value and name the key in the message":
  ```python
  _WALL_CLOCK_RE = re.compile(r"(?P<hour>[01]\d|2[0-3]):(?P<minute>[0-5]\d)")


  # Module-level (ADR-0016): a validator for one scalar, used by the dataclass below and by
  # nothing else; it has no state and no second implementation to substitute.
  def _wall_clock(name: str, value: str) -> time:
      """A 24-hour wall-clock time written `HH:MM`."""
      match = _WALL_CLOCK_RE.fullmatch(str(value))
      if match is None:
          raise ValueError(f"{name} must be a 24-hour wall clock time written HH:MM: {value!r}")
      return time(int(match["hour"]), int(match["minute"]))
  ```
  `str(value)` rather than an `isinstance` guard, so a TOML `opens = 1600` is refused by the
  same one branch.
- A new frozen dataclass, placed immediately after `GithubReleaseConfig`
  (`config.py:824-846`), whose shape it copies:
  ```python
  @dataclass(frozen=True)
  class SabbathConfig:
      """`[sabbath]`: the window sub-doctrine 8.i holds open, declared rather than computed.

      8.i is sundown Friday to sundown Saturday. Sundown is astronomical -- it moves about
      four hours across a year -- and knowing it exactly needs a network call or an
      ephemeris library, neither of which this package will take (`dependencies = []`,
      pyproject.toml:27-30). So the window is DECLARED, in wall-clock time in a named IANA
      zone, and it is deliberately WIDER than any true sundown there: `opens` is at or
      before the earliest sunset of the year in that zone and `closes` at or after the
      latest, so the real twenty-four hours always sit inside it. A declared window may
      only ever err toward rest; erring the other way would let a merge land inside the
      real window, which 8.i forbids without exception.

      Keys rather than constants (sub-doctrine 12.c): an adopting repository is somewhere
      else on the planet, and this package may not decide a latitude for it. `enabled`
      defaults to TRUE because 8.i binds everything that carries this canon; a repository
      that does not carry it has to say so, in writing, in its own file.
      """

      enabled: bool = True
      timezone: str = "America/New_York"
      opens: str = "16:00"
      closes: str = "21:00"

      def __post_init__(self) -> None:
          self.zone()
          self.opens_at()
          self.closes_at()

      def zone(self) -> ZoneInfo:
          """The declared zone. A machine whose time-zone database cannot answer when the
          window opens gets an error: 8.i has no 'assume it is not the Sabbath' branch."""
          try:
              return ZoneInfo(self.timezone)
          except (ValueError, ZoneInfoNotFoundError) as exc:
              raise ValueError(
                  "sabbath.timezone must be an IANA zone name this machine's time-zone "
                  f"database carries: {self.timezone!r}"
              ) from exc

      def opens_at(self) -> time:
          return _wall_clock("sabbath.opens", self.opens)

      def closes_at(self) -> time:
          return _wall_clock("sabbath.closes", self.closes)
  ```
  `zone()`, `opens_at()` and `closes_at()` are methods rather than properties so that
  `__post_init__` can call them as plain statements and reject a bad declaration at load.
- `GhConfig`: add `sabbath: SabbathConfig = SabbathConfig()` directly after
  `estimate: EstimateConfig = EstimateConfig()` (`config.py:1511`).
- `load_config`: add `rest = data.get("sabbath", {})` to the section reads
  (`config.py:1713-1730`, beside `release = data.get("github_release", {})` at 1726), and add
  to the `return GhConfig(...)` call (`config.py:1763-1958`), immediately after the
  `github_release=GithubReleaseConfig(...)` block (`config.py:1856-1861`):
  ```python
  sabbath=SabbathConfig(
      enabled=rest.get("enabled", True),
      timezone=rest.get("timezone", SabbathConfig.timezone),
      opens=rest.get("opens", SabbathConfig.opens),
      closes=rest.get("closes", SabbathConfig.closes),
  ),
  ```

### Edit `vibey_gh/cli.py`
- Imports: add `from vibey_gh.sabbath import SabbathWindow` after
  `from vibey_gh.review_composition import PAID_HALVES, REVIEW_COMPOSER` (`cli.py:35`);
  `review_composition` sorts before `sabbath`.
- `_merge_train` (`cli.py:222-224`). Between `cfg = load_config()` and `prs = (`:
  ```python
      held = SabbathWindow(cfg.sabbath).hold()
      if held is not None:
          # 8.i: the merge train does not run in the window. Held HERE, before anything is
          # listed, judged, labelled, commented on, restacked or merged -- guarding the
          # merge alone would still let the train push to a contributor's branch. Exit 0
          # and say so where a person looks: paused, not failed (10.f), and the work is
          # re-attempted by the workflow_run trigger and the weekly cron that already exist.
          print(f"vibey-gh: {held.report()}")
          _write_summary(args, held.summary())
          return 0
  ```
- `_promote` (`cli.py:441-445`). The body becomes:
  ```python
  def _promote(args) -> int:
      cfg = load_config()
      held = SabbathWindow(cfg.sabbath).hold()
      if held is not None:
          # 8.i: `promote-to-main` does not fire in the window. Held before the version
          # bump, its push to the integration branch, and the promotion pull request --
          # each of them a write.
          print(f"vibey-gh: {held.report()}")
          _write_summary(args, held.summary())
          return 0
      try:
          result = promote.promote(cfg, dry_run=args.dry_run, method=args.method, wait=args.wait)
      except RuntimeError as exc:
  ```
  `load_config()` moves out of the `promote.promote(...)` argument list; it is still passed
  positionally, so `test/test_gh_cli.py:553`'s `lambda cfg, **kw: result` is unaffected.

### Edit the repository-root `.vibey-gh.toml`
Append a new table at the end of the file (a pure addition; do not reorder anything):

```toml

[sabbath]
# Sub-doctrine 8.i: from sundown Friday to sundown Saturday nothing in this family writes,
# merges, tests or ships. DECLARED, not computed -- real sundown needs a network call or an
# ephemeris dependency, and vibey-gh has `dependencies = []` on purpose. The window is
# therefore deliberately WIDER than any true sundown in this zone: 16:00 is before the
# earliest sunset of the year here (about 16:28, early December) and 21:00 after the latest
# (about 20:31, late June), so the real twenty-four hours always sit inside it. A declared
# window may only ever err toward rest.
enabled = true
timezone = "America/New_York"
opens = "16:00"
closes = "21:00"
```

`enabled = true` is written out rather than left to the default: this repository carries the
canon, and 8.i binds what carries it, so its own file says so.

### No new template, no new workflow
`.github/workflows/` and `vibey_gh/templates/workflows/` are **not touched**. A rendered
workflow edited by hand is reverted by the installer and flagged by the `tools-lint` drift
check, and the held state reaches the run summary page through `$GITHUB_STEP_SUMMARY` without
any YAML change at all (`cli._write_summary`, `cli.py:408-418`).

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && grep -c "class SabbathWindow" vibey_gh/sabbath.py` prints 1,
      and `vibey_gh/interfaces/sabbath_window_interface.py` exists.
- [ ] `grep -n "vibey_gh.sabbath" vibey_gh/interfaces/sabbath_window_interface.py` prints
      nothing: an interface declares, it never consumes its implementation (ADR-0016).
- [ ] `grep -c "SabbathWindow(cfg.sabbath).hold()" vibey_gh/cli.py` prints 2 — one in
      `_merge_train`, one in `_promote`.
- [ ] In `vibey_gh/cli.py`, the `held` check in `_merge_train` appears **before** the first
      `merge_train.open_pull_requests` call, and the one in `_promote` **before** the first
      `promote.promote` call.
- [ ] `grep -c "^\[sabbath\]" .vibey-gh.toml` (repository root) prints 1.
- [ ] `git diff --name-only` lists exactly: `.vibey-gh.toml`,
      `src/vibey_tools/gh/vibey_gh/cli.py`, `src/vibey_tools/gh/vibey_gh/config.py`,
      `src/vibey_tools/gh/vibey_gh/sabbath.py`,
      `src/vibey_tools/gh/vibey_gh/interfaces/sabbath_window_interface.py`,
      `src/vibey_tools/gh/test/test_sabbath.py`, `src/vibey_tools/gh/test/test_gh_cli.py`.
      Nothing under `.github/`, nothing under `docs/`, nothing under `templates/`.
- [ ] `git diff --stat` shows `test/test_gh_cli.py` only GAINING lines.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes at 100% line and branch coverage
      of `vibey_gh` (`pyproject.toml:64-71`).
- [ ] black, isort, mypy, `ruff check` and `ruff format --check` are all clean (the check
      block below).

## Tests to write first (TDD)
### New file `test/test_sabbath.py`
Provenance header copied from `test/test_promote.py:1`. Imports:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from vibey_gh.config import SabbathConfig, load_config
from vibey_gh.sabbath import Hold, SabbathWindow

ZONE = ZoneInfo("America/New_York")


def moment(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=ZONE)
```

Tests (every moment below is a real date in that zone; 2026-09-25 is a Friday and
2026-09-26 the Saturday after it):

- `test_the_window_holds_friday_evening_through_saturday_night` — `SabbathWindow(SabbathConfig())`
  returns a `Hold` at Friday 16:00 (the instant it opens), Friday 23:59, Saturday 03:00 (the
  2 a.m. merge the doctrine names), and Saturday 20:59. Each `Hold.opened` is Friday 16:00 in
  the declared zone and each `Hold.resumes` is Saturday 21:00.
- `test_nothing_is_held_outside_the_window` — `hold()` is `None` at Friday 15:59, Saturday
  21:00 exactly (the window is half-open: `closes` is when work resumes), Sunday 10:00,
  Monday 09:00, Wednesday 02:00 and the following Thursday 23:59.
- `test_a_moment_in_another_zone_is_judged_in_the_declared_one` — the same Saturday 03:00
  expressed as `datetime(2026, 9, 26, 7, 0, tzinfo=UTC)` yields a `Hold`, and
  `datetime(2026, 9, 27, 4, 0, tzinfo=UTC)` (Sunday 00:00 in the declared zone, after the
  window closed) yields `None`. Asserts the conversion, not the caller's zone.
- `test_the_window_moves_with_daylight_saving` — Saturday 2026-01-10 at 20:30 (EST) is held
  and 21:30 is not; Saturday 2026-07-11 at 20:30 (EDT) is held and 21:30 is not. Assert each
  `Hold.resumes.utcoffset()` differs between the two dates, so the window is wall-clock in the
  zone rather than a fixed UTC offset.
- `test_the_clock_is_used_when_no_moment_is_given` — `SabbathWindow(SabbathConfig(),
  clock=lambda: moment(2026, 9, 26, 3))` returns a `Hold` from a bare `hold()`, and
  `clock=lambda: moment(2026, 9, 28, 9)` returns `None`.
- `test_a_repository_that_does_not_carry_the_canon_can_switch_it_off` —
  `SabbathWindow(SabbathConfig(enabled=False)).hold(moment(2026, 9, 26, 3))` is `None`.
- `test_the_declared_window_is_wider_than_any_real_sundown_here` — the defaults are
  `enabled is True`, `timezone == "America/New_York"`, `opens == "16:00"`,
  `closes == "21:00"`; and `SabbathConfig().opens_at() < time(16, 28)` and
  `SabbathConfig().closes_at() > time(20, 31)` — the earliest and latest sunsets of the year
  in that zone, so the real window is always strictly inside the declared one.
- `test_this_repository_declares_the_window_rather_than_inheriting_it` — call
  `load_config()` against this repository's own root (`Path(__file__).resolve().parents[4]`,
  i.e. the monorepo root that owns `.vibey-gh.toml`) and assert `cfg.sabbath.enabled is True`
  and `cfg.sabbath.timezone == "America/New_York"`. Skip with `pytest.skip` if that root has
  no `.vibey-gh.toml`, so the tenant's own sdist still passes standalone.
- `test_a_zone_this_machine_cannot_resolve_is_refused_at_load` — `SabbathConfig(timezone="")`
  and `SabbathConfig(timezone="Nowhere/Nowhere")` each raise `ValueError` matching
  `"sabbath.timezone"`. (`""` raises `ValueError` from `zoneinfo`; `"Nowhere/Nowhere"` raises
  `ZoneInfoNotFoundError`, which subclasses `KeyError` — both are caught and re-raised as one
  message naming the key.)
- `test_a_time_that_is_not_hh_mm_is_refused_at_load` — `SabbathConfig(opens="25:00")`,
  `SabbathConfig(opens="4pm")`, `SabbathConfig(closes="21:60")` and `SabbathConfig(opens="")`
  each raise `ValueError` matching `"HH:MM"`, and the message names `sabbath.opens` or
  `sabbath.closes` respectively.
- `test_a_held_run_says_which_rule_holds_it_and_until_when` — for
  `held = SabbathWindow(SabbathConfig()).hold(moment(2026, 9, 26, 3))`:
  `"8.i" in held.report()`, `held.opened.isoformat() in held.report()`,
  `held.resumes.isoformat() in held.report()`.
- `test_a_held_run_reads_as_paused_rather_than_failed` — `summary = held.summary()`;
  `summary.startswith("## Held for the Sabbath")`, `"paused, not failed" in summary`,
  `held.resumes.isoformat() in summary`, and `summary.endswith("\n")`.
- `test_the_config_loads_a_declared_window` — write a `.vibey-gh.toml` in `tmp_path`
  containing `[sabbath]` with `enabled = false`, `timezone = "UTC"`, `opens = "18:30"`,
  `closes = "19:45"`, then `load_config(tmp_path)` and assert all four values round-trip.

### Appended to `test/test_gh_cli.py` (append only; never rewrite this file)
1. Add `cli as cli_mod,` as the first entry of the existing `from vibey_gh import (...)` block
   (`test_gh_cli.py:17-25`) — the block already carries `realign as realign_mod`, and the
   tenant sets `combine_as_imports` in both isort and ruff (`pyproject.toml:100-118`).
2. Add `from vibey_gh.sabbath import Hold` after
   `from vibey_gh.merge_train import Verdict` (`test_gh_cli.py:29`).
3. Insert, immediately after the `repo` fixture (`test_gh_cli.py:32-55`):
   ```python
   class _NeverHeld:
       """The window, open. Without it every merge-train and promote test in this file
       would behave differently on a Friday evening, because `_merge_train` and `_promote`
       now read a real clock. The window's own arithmetic is proved against named moments
       in test_sabbath.py; here it is pinned."""

       def __init__(self, config) -> None:
           self.config = config

       def hold(self, at=None):
           return None


   class _AlwaysHeld(_NeverHeld):
       """The window, shut."""

       def hold(self, at=None):
           opened = datetime(2026, 9, 25, 16, 0, tzinfo=ZoneInfo("America/New_York"))
           return Hold(opened=opened, resumes=opened + timedelta(days=1, hours=5))


   @pytest.fixture(autouse=True)
   def _outside_the_sabbath(monkeypatch):
       monkeypatch.setattr(cli_mod, "SabbathWindow", _NeverHeld)
   ```
   `cli_mod.SabbathWindow` is the seam this file already substitutes things at — it does the
   same for `merge_train.open_pull_requests` (line 213) and `promote_mod.promote` (line 553).
   The lane does not change this file's established style. Add
   `from datetime import datetime, timedelta` and `from zoneinfo import ZoneInfo` to its
   stdlib import block.
4. `test_the_merge_train_is_held_for_the_sabbath(repo, capsys, monkeypatch, tmp_path)`:
   `monkeypatch.setattr(cli_mod, "SabbathWindow", _AlwaysHeld)`; then
   `monkeypatch.setattr(merge_train, "open_pull_requests", lambda *a, **k: pytest.fail("8.i: the train must not even list pull requests"))`;
   `out = tmp_path / "held.md"`; assert `main(["merge-train", "--summary", str(out)]) == 0`;
   assert `"held for the Sabbath"` and `"8.i"` are in the captured stdout; assert the written
   file contains `"## Held for the Sabbath"` and `"paused, not failed"`.
5. `test_promotion_is_held_for_the_sabbath(repo, capsys, monkeypatch, tmp_path)`: the same
   shape, with `monkeypatch.setattr(promote_mod, "promote", lambda *a, **k: pytest.fail("8.i: promotion must not push a version bump"))`
   and `main(["promote", "--summary", str(out)]) == 0`. `promote_mod` is **not** a
   module-level import in this file: `test_gh_cli.py:546` does
   `from vibey_gh import promote as promote_mod` inside the test function. Copy that — a
   function-local import, not a new top-level one.
6. `test_outside_the_window_the_train_runs_as_it_always_did(repo, capsys, monkeypatch)`: with
   the autouse `_NeverHeld` in force, `monkeypatch.setattr(merge_train, "open_pull_requests",
   lambda cfg: [])` and assert `main(["merge-train"]) == 0` and `"no open pull requests"` in
   stdout — the `held is None` arc of the new branch, proved rather than assumed.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_sabbath.py
python -m pytest -q --no-cov test/test_gh_cli.py
python -c 'from vibey_gh.config import SabbathConfig; c = SabbathConfig(); print(c.zone(), c.opens_at(), c.closes_at())'
python -c 'from datetime import datetime; from zoneinfo import ZoneInfo; from vibey_gh.config import SabbathConfig; from vibey_gh.sabbath import SabbathWindow; w = SabbathWindow(SabbathConfig()); z = ZoneInfo("America/New_York"); print(w.hold(datetime(2026, 9, 26, 3, tzinfo=z)), w.hold(datetime(2026, 9, 28, 9, tzinfo=z)))'
python -m pytest -q
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check src/vibey_tools/gh
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check src/vibey_tools/gh
python3 -c 'import tomllib, pathlib; data = tomllib.loads(pathlib.Path(".vibey-gh.toml").read_text(encoding="utf-8")); print(data["sabbath"])'
git status --porcelain .github/workflows
git diff --stat
```
`python -m pytest -q` (no `--no-cov`) is the whole tenant suite at 100% line and branch
coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`); focused runs need
`--no-cov`. `git status --porcelain .github/workflows` must print **nothing** — this lane
renders no workflow and edits none, so there is no installer drift to answer for.
Nothing here is platform-specific: run the same block on macOS and on Arch Linux (8.h).

### C8 — the formatter trap
This tenant is checked by `black --line-length 100` + `isort` **and** by the root
`ruff format`. Keep lines at or under 100 columns (95 with nested calls); bind long
expressions to a local before asserting; no implicit string concatenation that would fit on
one line; one argument per line with a trailing comma in multi-line calls; no backslash
continuations. If the two formatters disagree about a line, **restructure that line**; never
alternate formatters. After the edits, format once from `src/vibey_tools/gh`:
`python -m black --line-length 100 vibey_gh test` then `isort vibey_gh test`, then run the
block above.

### A trap this lane must not fall into
The integration branch this lane starts from is **one commit behind** `origin/develop` and
does **not** yet contain 8.i in `src/vibey_tools/gh/docs/doctrines.md` (`edbf86f7` vs
`2838c62d`; the only difference is that docs commit). So: cite 8.i in comments and docstrings,
but **never write a test that reads `doctrines.md`** — it would pass on `develop` and fail
here. Do not edit `doctrines.md` or `corpus-index.json`; the canon lands by its own merge.

## Out of scope
- **Workflow templates and rendered workflows.** `vibey_gh/templates/workflows/*.yml` and
  `.github/workflows/*.yml` are untouched. A post-window resume cron, and the
  `__VIBEY_GH_…__` placeholder that would keep its cadence configurable under 12.c, are a
  separate lane; the existing `workflow_run` triggers and weekly crons already re-attempt
  held work (behaviour 8).
- **Every other writer.** `merge_train.merge()`, `promote.promote()`, `realign`, `reconcile`,
  `flatten`, `yank`, `github_release`, `issue_automation`, `pr_automation` and `fitloop` get
  no guard here. This lane guards the two entry points 8.i names by hand; a defence-in-depth
  lane extends the window to the rest of the library surface.
- **`vibey` itself** (`src/vibey/**`) — the six-phase queue, the `*loop` runners, and the
  storm lanes are their own lanes; this one is the vibey-gh tenant only.
- **A `vibey-gh sabbath` reporting subcommand** for other workflows to consult — a later lane.
- **A computed sundown** from a declared latitude and longitude (a stdlib-only NOAA solar
  calculation). It would narrow the window to the real one; it needs an operator decision on
  coordinates and on whether a computed boundary may ever be *narrower* than the declared one.
- **Documentation.** `src/vibey_tools/gh/docs/configuration.md` owes a `[sabbath]` row, and
  `docs/reference/configuration.md` at the repository root owes the same; the docs wave owns
  both. Do not edit `CHANGELOG.md`, `docs/`, ADRs, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or
  any skill tree.
- Do not push, open pull requests, or change git remotes. Commit locally with
  `feat(gh): hold the merge train and promotion for the Sabbath (8.i)`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

**Depends on:** none
