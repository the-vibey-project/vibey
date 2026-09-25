# 0072 — The Sabbath, kept where the machine stands

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** sub-doctrines 8.i, 8.a, 8.j, 10.f, 12.c, 12.e · **Related:** ADR-0016, ADR-0017, ADR-0060 · **Evidence:** `develop` at `0823cdfd`, read 2026-09-25

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`, all done in the change that
carries it.

**Numbering:** the lane brief asked for 0072, because #1156 and another lane hold 0070 and
0071 in open pull requests. `tests/meta/test_adr_counts.py` requires a contiguous range on
the branch, so this record takes the next free number on `develop`, 0070. Whichever of the
three merges second renumbers, as the lane rules say.

## Context

Sub-doctrine 8.i (ratified 2026-09-22) says that from sundown Friday to sundown Saturday
nothing in this family writes, merges, tests or ships code; that the merge train does not
run and `promote-to-main` does not fire; that held work is paused, not failed and not
silently dropped (10.f). Nothing in `src/` read the day of the week: `grep -rniE
"weekday|sabbath|isoweekday" src/vibey src/vibey_tools/gh/vibey_gh` found only the canon
text. The spec `docs/plans/qwenstorm-3.0.0/specs/gap-sabbath-window-guard.md` proposed a
declared, wide wall-clock window for vibey-gh alone.

The operator ruled on 2026-09-25 that the window must follow the machine it runs on, not
one person's home, and that the heartbeat must keep going through the rest so that the
system picks itself up at Saturday sundown.

## Decision

1. **Sundown is computed, not declared.** `vibey_gh.sabbath` implements the NOAA
   solar-position algorithm (the GML solar calculator, after Meeus) with the official
   zenith of 90.833°. It is pure: no clock, no file, no network, no zone database. The
   caller passes the instant and a `tzinfo`. The formula is written out in the module. A
   golden table checks it against published NOAA sunsets to within ±2 minutes.
2. **One implementation.** `vibey-gh` declares no dependencies, so `vibey.domain.sabbath`
   re-exports it (ADR-0017) and the domain stays pure.
3. **Where the host stands, per host, in order** (`vibey_gh.sabbath_location`):
   1. an explicit override: `[sabbath] latitude/longitude` in a LOCAL `vibey.toml`,
      `~/.config/vibey/sabbath.toml`, or `VIBEY_SABBATH_LATITUDE/LONGITUDE`;
   2. the operating system's location service, where installed and permitted:
      `CoreLocationCLI` on macOS, GeoClue's `where-am-i` on Linux;
   3. the reference city of the host's IANA zone, from the system's `zone1970.tab` or
      `zone.tab`, with no network. This is *coarse*, so the window widens toward rest by
      `coarse_margin_minutes` (default 90).

   There is no IP geolocation (8.a). A resolution is cached for a week and dropped at
   once when the zone changes (8.j). Every window names its location source and accuracy
   in its `basis` (10.f). A host that no source can place uses the declared fallback times
   (Friday 14:00 → Saturday 23:00 local, configurable: wider than any mid-latitude sundown, so it errs toward rest; the brief asked 18:00 → 19:00, which the review found closes before summer sundown and opens after winter sundown), widened, and says so. It is never
   silently off.
4. **Held, visibly.** `vibey-gh merge-train` and `vibey-gh promote` consult the window
   before they touch anything. A held run prints one line, writes a job-summary section
   ("paused, not failed") and exits 0.
5. **The heartbeat keeps beating.** During the window `vibey-gh sovereign --beat`
   publishes nothing. It records `resting_until` in its beat record and exits 0, and
   `heartbeat status` reads a resting beat as healthy, never dead. The probe offers no
   sovereign lane while resting.
6. **It picks itself back up.** The first beat after the window writes `SabbathEnded` and
   re-fires the merge train and the promotion (`gh workflow run`, `[sabbath]
   resume_dispatch`). Every beat outside the window also runs the resume command of each
   lane registered with `vibey-gh sabbath register-lane`. A lane's registration is removed
   only after its command succeeds, so a replay re-runs it rather than losing it.
7. **The engine.** `WorkerLoop` claims no lease while the window holds. It logs
   `sabbath.resting` once and `sabbath.ended` once, and claims again on the first poll
   after. `vibey new` and `vibey work` decline with the reason and the resume time, and
   exit 75 (EX_TEMPFAIL). `vibey sabbath` prints the window, and `vibey doctor` reports
   the location source and FAILs for a host that no source placed.
8. **Configurable, on by default** (12.c). `[sabbath]` in `.vibey-gh.toml` and in a local
   `vibey.toml` has these keys: `enabled`, `timezone`, `latitude`, `longitude`,
   `local_config`, `offset_minutes`, `coarse_margin_minutes`, `fallback_opens`,
   `fallback_closes`, `location_service`, `resume_dispatch` and `lanes_dir`. This
   repository's committed file names only the zone (`America/New_York`) and a 90-minute
   coarse margin, because a hosted runner's clock is UTC and it has no location service.

## Consequences

- A test's outcome must not depend on the weekday. Both suites give every test a guard
  that never holds, and tests of the Sabbath itself opt in with `@pytest.mark.sabbath`
  and name their own instant.
- **Pending, not done here:**
  - Ledger events. `EventKind` is enforced by a database CHECK, so `SabbathBegan` and
    `SabbathEnded` rows need a migration. They are recorded in the heartbeat's beat record
    and the worker log instead.
  - Scheduled workflows other than the merge train and the promotion are not yet guarded.
  - A resume cron in the rendered templates would need a new placeholder (spec, "Out of
    scope").
  - The CoreLocation helper is not bundled; it is used only when installed.
