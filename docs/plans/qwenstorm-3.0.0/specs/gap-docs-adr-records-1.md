## Title
docs(adr): decision records for 7.c (the thorough ledger) and 8.g (always measured)

## Why
Sub-doctrine 12.b and ADR-0020: "an ADR records the decision; the canon records the law. Both
get written." Two ratified sub-doctrines have no decision record: no file under
`docs/architecture/decisions/` cites 7.c or 8.g (`issue-audit/gaps.md` M8, lines 684-692).
- 7.c, the thorough ledger: `src/vibey_tools/gh/docs/doctrines.md:82-91`.
- 8.g, always measured: `doctrines.md:316-324`.
Their mechanism now exists in lanes: the redactor records each redaction
(`gap-ledger-redaction-recorded`), and measurements have a port and sinks (`gap-measure-port`,
`gap-measure-ledger-sink`). The records say what was decided and why, and name those lanes; they
claim nothing about their state beyond the tree (10.f).

## Required behaviour
1. Find the numbers: `ls docs/architecture/decisions | tail -1` prints the last record; its
   first four digits are `L` (after `gap-docs-adr-land`, `0049`). The 7.c record is
   `NA = L+1` and the 8.g record `NB = L+2`, zero-padded to four digits (`0050`, `0051`).
2. Create `docs/architecture/decisions/<NA>-the-thorough-ledger.md` with this shape, writing
   the prose from the facts given (plain words; every section present; about 60-90 lines):
   - Line 1: `# <NA> — The thorough ledger: record all that can be recorded, redact what must be, and record the redaction`
   - Line 3: `**Status:** accepted — sub-doctrine 7.c, which it argues, is ratified · **Date:** <today, from date +%F> · **Cites:** sub-doctrines 7.c, 8.g, 10.f · **Related:** ADR-0003, ADR-0033, ADR-0040, ADR-0044 · **Evidence:** the tree at the commit this record lands on`
   - `**Owes:**` paragraph: the conduct rule is 7.c; this record is its mechanism (ADR-0020).
   - `## Context`: 7.c's text in one quoted sentence ("secrets, credentials and people's
     private details are redacted where they would appear, and the redaction is itself
     recorded — never a silent omission"); the ledger is append-only by the `RULE`s in
     `migrations/0002_event.sql` (ADR-0003); event kinds are `EventKind` in
     `src/vibey/domain/ledger.py`; one redactor, `redact_payload` in
     `src/vibey/infrastructure/ledger/redact.py`, runs on every ledger write, every log line
     (`src/vibey/infrastructure/logging.py`) and the public export.
   - `## Decision`, five numbered points:
     1. The ledger holds every job, run, turn, tool call, decision, capacity signal, cost,
        measurement (8.g) and outcome, with its time, its actor and its evidence, written by
        the component that did it as it happens, never reconstructed after.
     2. A happening with no event kind is a gap, tracked like a defect (10.f), never waived
        as a saving. The lanes that closed the gaps found in 2026-09 are named:
        `gap-ledger-job-events-*`, `gap-ledger-selection-events-*`,
        `gap-ledger-provider-turns-*` and `gap-measure-ledger-sink`.
     3. Redaction: secrets, credentials and people's private details (emails, phone numbers,
        street addresses: `gap-ledger-redact-pii-*`) are replaced by `[REDACTED]` where they
        would appear, and each redaction is recorded in the payload's `_redactions` field
        with its path and class, never its value (`gap-ledger-redaction-recorded`).
     4. Append-only: completeness grows by new events; a correction is a new event that
        supersedes the old one.
     5. Publication is a separate policy: the public export withholds kinds that are not on
        its allowlist and counts what it withheld (`docs/guides/ledger-publication.md`).
        Whether `_redactions` is published is an open operator ruling; this record does not
        decide it.
   - `## Consequences`: the ledger grows with every component (partitioning, migration
     `0013_ledger_partitioning.sql`, and the search indexes of `0012_event_search_indexes.sql`
     carry it); every new component adds its kinds; readers stay forward-compatible
     (`src/vibey/domain/stored_value.py`).
   - `## Alternatives rejected`: log files as the record (not append-only, not shared, not
     queryable); sampling or aggregating events to save space (7.c: what is not held is a gap,
     not a saving); dropping a sensitive field without a trace (7.c: never a silent omission).
3. Create `docs/architecture/decisions/<NB>-always-measured.md` the same way:
   - Line 1: `# <NB> — Always measured: every loop, lane, queue, surface, test run and model records its measurements, and vibey tunes itself from them`
   - Line 3: `**Status:** accepted — sub-doctrine 8.g, which it argues, is ratified · **Date:** <today> · **Cites:** sub-doctrines 8.g, 7.c, 10.f, 12.c · **Related:** ADR-0044, ADR-0045, ADR-0046, ADR-0047, ADR-<NA> · **Evidence:** the tree at the commit this record lands on`
   - `**Owes:**` paragraph: the conduct rule is 8.g; this record is its mechanism.
   - `## Context`: 8.g in one quoted sentence ("Nothing runs unmeasured; a component that
     cannot report its measurements is incomplete"); before it, `[telemetry]` built an
     in-process tracer and metrics recorder with no external exporter
     (`docs/reference/configuration.md`, section `[telemetry]`), and no port carried a
     measurement to the ledger.
   - `## Decision`, six numbered points:
     1. One port, `MeasurementPort`, fed by `MeasurementSource`s and fanning out over sinks,
        with a registered in-memory fake (`gap-measure-port`).
     2. One vocabulary: latency, throughput, queue depth and waiting time, resource use and
        outcome, recorded as the `MeasurementRecorded` ledger kind (`gap-measure-domain`).
     3. Sinks: the ledger, in the project or in the fleet ledger (`gap-measure-ledger-sink`),
        OpenTelemetry (`gap-measure-otel-sink`) and the log (`gap-measure-log-sink`). The
        `[measure]` table declares where they go and how often samplers run
        (`gap-measure-config`; 12.c).
     4. Unmeasured is incomplete: a meta-test fails when a loop, surface, sampler, sink,
        harness or delivery command reports nothing (`gap-measure-meta`).
     5. vibey tunes from evidence, within declared bands: rotation weights
        (`gap-rotation-derived-weights-*`), model residency (`gap-residency-tuning-*`) and
        lane capacity (`gap-lane-capacity-*`). A default is never replaced by an assumption.
     6. Measurements are published with the decisions they drive, naming object, source and
        cutoff (`vibey measure`, `gap-measure-cli`; 10.f).
   - `## Consequences`: every new loop, lane, queue or surface ships its measurements in the
     same change; the cost of measuring is itself measured.
   - `## Alternatives rejected`: measuring only in CI benchmarks (8.g says always, in real
     time); a third-party APM as the record (10.e: the family's ledger is the record, and OTel
     is only a sink); sampling a fraction of runs (the ledger would carry gaps, 7.c).
4. `properdocs.yml`: after the last decision-record entry, add both, in the same form:
   `- "<NA> — The thorough ledger": architecture/decisions/<NA>-the-thorough-ledger.md` and
   `- "<NB> — Always measured": architecture/decisions/<NB>-always-measured.md`.
5. The advertised count (`(N ADRs` in `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/index.md`,
   and `(N ADRs: 0001–<last>)` in `GEMINI.md`) becomes the number of files on disk.

## Where to change
- New: the two ADR files. Edit with edit_file: `properdocs.yml`, `CLAUDE.md`, `AGENTS.md`,
  `GEMINI.md`, `README.md`, `docs/index.md` (the count line only).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta/test_adr_counts.py tests/meta/test_adr_status_follows_canon.py` passes.
- [ ] `grep -l "Cites:\*\* sub-doctrines 7.c" docs/architecture/decisions/*.md` names the new 7.c record;
      `grep -l "Cites:\*\* sub-doctrines 8.g" …` names the 8.g record.
- [ ] Each new file has the headings `## Context`, `## Decision`, `## Consequences`,
      `## Alternatives rejected`, and an `**Owes:**` paragraph.
- [ ] Neither record says `_redactions` is or will be published.

## Tests to write first (TDD)
None new: `tests/meta/test_adr_counts.py` and `tests/meta/test_adr_status_follows_canon.py`
(from `gap-docs-adr-status-2`) hold the numbering, the nav, the counts and the status.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    uv run --with 'properdocs==1.6.7' --with 'properdocs-theme-mkdocs==1.6.7' properdocs build --strict --site-dir "$TMPDIR/vibey-site"
If properdocs cannot be installed (no network), say so in the verdict.

## Out of scope
- The 8.d, 8.h, 7.a and reader-rule records (`gap-docs-adr-records-2`, `-3`).
- Code, the canon, and every other docs file.

Commit as `docs(adr): decision records for 7.c (the thorough ledger) and 8.g (always measured)`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
