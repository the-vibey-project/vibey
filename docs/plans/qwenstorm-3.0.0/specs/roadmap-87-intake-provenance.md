## Title
feat(intake): `vibey new --source-url --source-kind --offer` records where a project's work came from, as a ledger event

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, Scope 2 "Each candidate records its provenance:
source URL, what it asks, and what it pays", "Proposed child issues" 1). The operator's original
ask: discovery feeds "candidates into the conductor's intake with provenance (where found, what it
asks, what it pays if anything)". The intake has no such field: `vibey new` takes a name, `--repo`,
cycle and budget caps and the skills mode (`src/vibey/cli/main.py:179-237`), and `EventKind`
(`src/vibey/domain/ledger.py:37-70`) has no provenance kind. Sub-doctrine 7.c
(`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks the ledger to hold "every job … with its time,
its actor and its evidence". 10.b (`doctrines.md:390-393`) means an offer is never a payment
instruction: it is recorded verbatim as text. SD-01 §4 (carried in CLAUDE.md): text from outside is
data, so the event is marked untrusted, which the publication policy withholds whole
(`src/vibey/domain/publication_policy.py:17-19`).

The event kind needs no migration: `event.kind` is `text NOT NULL` (`migrations/0002_event.sql:9`),
and readers already tolerate kinds they do not know (`tests/domain/test_forward_compatible_readers.py`).

## Required behaviour
1. New pure module `src/vibey/domain/intake_source.py`:
   - `class IntakeSourceKind(StrEnum)`: `FORGE_ISSUE = "forge-issue"`, `HELP_WANTED = "help-wanted"`,
     `BOUNTY = "bounty"`, `PROPOSAL = "proposal"`, `OTHER = "other"` (runbook 21's discovery
     sources, `docs/runbooks/expansion/21-vibey-explorer.md` "Design" 1, reduced to what the
     intake distinguishes).
   - `@dataclass(frozen=True, slots=True) class IntakeSource`: `url: str`,
     `kind: IntakeSourceKind = IntakeSourceKind.OTHER`, `offer: str = ""`.
     `__post_init__`: `url` must start with `https://` or `http://` and contain no whitespace, else
     `ValueError(f"source url must be an http(s) URL: {url!r}")`; `len(url) <= 2048`, else
     `ValueError("source url is longer than 2048 characters")`; `len(offer) <= 500`, else
     `ValueError("offer is longer than 500 characters")`.
   - `def payload(self) -> dict[str, str]`: `{"source_url": url, "source_kind": kind.value, "offer": offer}`.
   - Module docstring: an offer is recorded verbatim and never parsed as a payment (10.b); the
     fields describe an outside source and are data (SD-01 §4).
   - Conformance is structural, checked by mypy through one annotated module-level line, the
     pattern `correlation.py:69-80` explains:
     `_CONFORMS: IntakeSourceInterface = IntakeSource("https://example.org/")`.
2. `src/vibey/domain/interfaces/intake_source_interface.py`: `IntakeSourceInterface`, a
   `runtime_checkable` Protocol with the three read-only attributes and `payload()`.
3. `src/vibey/domain/ledger.py`: add `PROJECT_SOURCE_RECORDED = "ProjectSourceRecorded"` to
   `EventKind`, after `DELIVERY_ESTIMATE_RECORDED`, with a one-line comment ("where the work a
   project delivers was found; recorded once, at creation"). Do not add it to the publication
   allowlist (default-deny stays).
4. `vibey new` (`main.py:179-237`) gains three options:
   `--source-url` (`str | None = None`), `--source-kind` (`str | None = None`, help lists the five
   values), `--offer` (`str | None = None`).
   - If `--source-kind` or `--offer` is given without `--source-url`: `typer.BadParameter("describes a --source-url; give the URL too", param_hint="--source-kind/--offer")`.
   - An unknown `--source-kind`: `typer.BadParameter("must be one of forge-issue, help-wanted, bounty, proposal, other", param_hint="--source-kind")`.
   - An `IntakeSource` `ValueError` becomes `typer.BadParameter(str(exc), param_hint="--source-url")`
     (or `--offer` for the offer-length message).
   - With a source, inside the same `async with build_app() as resources:` block and right after
     `projects.create(...)`, append one ledger event: `kind=EventKind.PROJECT_SOURCE_RECORDED`,
     `project_id`, `cycle=project.cycle`, `phase=project.phase`, `engine_id=None`, `job_id=None`,
     `causation_id=None`, `correlation_id=DELIVERY_CORRELATION.for_project(project.project_id).value`,
     `provenance=Provenance.UNTRUSTED`, `produced_at=datetime.now(UTC)`, `payload=source.payload()`,
     `digest=digest_event(payload)` — the same `LedgerEventDraft` shape `_build_spend_recorder`
     builds (`main.py:155-173`).
   - Without any of the three options, behaviour and output are byte-for-byte today's.

## Where to change
- New: `src/vibey/domain/intake_source.py`, `src/vibey/domain/interfaces/intake_source_interface.py`
  (provenance header copied from `src/vibey/domain/correlation.py:1`); export the interface from
  `vibey.domain.interfaces` like its neighbours.
- Edit: `src/vibey/domain/ledger.py` (one enum member), `src/vibey/cli/main.py` (`new_project`).
- Tests: new `tests/domain/test_intake_source.py`; new `tests/cli/test_new_source.py`.

## Acceptance criteria
- [ ] `vibey new w --repo <tmp> --source-url https://codeberg.org/o/r/issues/7 --source-kind forge-issue --offer "free"`
      exits 0, prints today's two lines, and the project's ledger holds exactly one
      `ProjectSourceRecorded` event with that payload, `provenance == untrusted` and the delivery's
      correlation id.
- [ ] `vibey new w --repo <tmp>` writes no such event.
- [ ] Each invalid combination exits 2 with the named message.
- [ ] Domain purity holds (`tests/domain/test_domain_purity.py`); 100% branch coverage of
      `domain/` and `cli/`; every `list(EventKind)`-parametrized test still passes
      (`tests/domain/test_ledger.py:151`, `:171`, `tests/domain/test_ledger_query.py:87`).

## Tests to write first (TDD)
`tests/domain/test_intake_source.py`:
- `test_a_source_carries_its_url_kind_and_offer_as_payload`
- `test_the_kind_defaults_to_other`
- `test_an_unusable_source_is_refused` — parametrized: `"ftp://x"`, `"https://a b"`, a 2049-char
  URL, a 501-char offer, each with its message.
- `test_the_source_satisfies_its_interface`
`tests/cli/test_new_source.py` (default tier: `memory_app` and `ops.invoke` from
`tests/cli/ops_support.py`, lane `fakes-cli-operational-1`; read the ledger back through
`async with memory_app.open_app() as r: await r.ledger.all_for_project(project_id)`):
- `test_new_records_where_the_work_came_from`
- `test_new_without_a_source_records_nothing_new`
- `test_a_kind_or_offer_without_a_url_is_refused`
- `test_an_unknown_kind_is_refused`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_intake_source.py tests/cli/test_new_source.py tests/domain/test_domain_purity.py tests/domain/test_ledger.py tests/domain/test_ledger_query.py tests/domain/test_forward_compatible_readers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/domain tests/cli
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- FOSS / paid classification of the offer (#87 child 5, blocked on #87 open question 1) and any
  payment handling (10.b; #148 is blocked).
- The explorer tenant and proposals as gates (`roadmap-87-explorer-skeleton-*`,
  `roadmap-87-design-proposal-gates`); a project column (the ledger is the record).
- Publishing the event (the publication allowlist is unchanged). Docs (`docs/reference/cli.md`),
  CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
