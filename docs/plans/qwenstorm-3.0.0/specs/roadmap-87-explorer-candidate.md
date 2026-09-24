## Title
feat(explorer): a discovered `Candidate` carries its provenance, in the intake's own vocabulary

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, Scope 2 "Each candidate records its provenance:
source URL, what it asks, and what it pays (and in what asset)", "Proposed child issues" 2 "with a
`Candidate` value type and interface"). Runbook 21 (`docs/runbooks/expansion/21-vibey-explorer.md`,
"Design" 1): each source "yields candidates with a source link so provenance is never lost".
Sub-doctrine 9.b (`src/vibey_tools/gh/docs/doctrines.md:349`): a class with its interface beside it.
The intake records the same facts through `vibey new --source-url --source-kind --offer`
(`roadmap-87-intake-provenance`, `vibey.domain.intake_source.IntakeSourceKind`); the explorer cannot
import `vibey` (it has third-party dependencies, and the explorer is stdlib-only), so the explorer
declares its own tuple and a root meta test holds the two vocabularies equal — one vocabulary,
checked, not two that drift. 10.b (`doctrines.md:390-393`): an offer is text, never a payment
instruction. SD-01 §4: everything in a candidate came from outside and is data.

## Required behaviour
1. `src/vibey_tools/explorer/vibey_explorer/candidate.py`:
   - `SOURCE_KINDS: tuple[str, ...] = ("forge-issue", "help-wanted", "bounty", "proposal", "other")`.
   - `@dataclass(frozen=True, slots=True) class Candidate`: `source_url: str`, `source_kind: str`,
     `title: str`, `asks: str`, `offer: str = ""`, `repository: str = ""`,
     `found_at: datetime | None = None`.
     `__post_init__` raises `ValueError` with these exact messages:
     - `source_url` not `http(s)://…` or containing whitespace → `f"candidate source_url must be an http(s) URL: {source_url!r}"`;
       longer than 2048 → `"candidate source_url is longer than 2048 characters"`;
     - `source_kind not in SOURCE_KINDS` → `f"candidate source_kind must be one of {', '.join(SOURCE_KINDS)}: {source_kind!r}"`;
     - `title` empty after strip → `"candidate title is empty"`; `len(title) > 300` → `"candidate title is longer than 300 characters"`;
     - `len(asks) > 2000` → `"candidate asks is longer than 2000 characters"`;
     - `len(offer) > 500` → `"candidate offer is longer than 500 characters"` (the intake's bound);
     - a `repository` that is non-empty and not `owner/name`-shaped (no leading/trailing `/`, no
       empty segment, no whitespace) → `f"candidate repository must be a forge namespace such as 'owner/name': {repository!r}"`;
     - a naive `found_at` → `"candidate found_at must be timezone-aware"`.
   - `def intake_arguments(self) -> tuple[str, ...]`: `("--source-url", source_url, "--source-kind", source_kind)`
     plus `("--offer", offer)` when `offer` is non-empty — exactly the flags `vibey new` accepts.
   - Module docstring: provenance is never lost (runbook 21); every field is outside text and data
     (SD-01 §4); an offer is recorded verbatim, never parsed as a payment (10.b).
   - Conformance line: `_CONFORMS: CandidateInterface = Candidate("https://example.org/", "other", "t", "a")`.
2. `src/vibey_tools/explorer/vibey_explorer/interfaces/__init__.py` (empty but for the provenance
   header and a one-line docstring) and `interfaces/candidate_interface.py`: `CandidateInterface`,
   a `runtime_checkable` Protocol declaring the seven attributes (read-only) and `intake_arguments()`.
   It imports only the standard library.
3. Root meta test `tests/meta/test_explorer_speaks_the_intake_vocabulary.py`:
   `test_explorer_source_kinds_equal_the_intake_kinds` — `tuple(k.value for k in IntakeSourceKind) == vibey_explorer.candidate.SOURCE_KINDS`
   (order included), with a docstring naming both lanes.

## Where to change
- New: `vibey_explorer/candidate.py`, `vibey_explorer/interfaces/__init__.py`,
  `vibey_explorer/interfaces/candidate_interface.py` (provenance header from
  `vibey_explorer/__init__.py:1`).
- New tests: `src/vibey_tools/explorer/test/test_candidate.py`;
  `tests/meta/test_explorer_speaks_the_intake_vocabulary.py`.

## Acceptance criteria
- [ ] A valid candidate round-trips its fields; `intake_arguments()` omits `--offer` when empty.
- [ ] Every invalid field raises its exact message (one parametrized case each).
- [ ] The explorer suite passes at 100% branch; its mypy is clean; the stdlib-only test of `-p1` passes.
- [ ] The root meta test passes.

## Tests to write first (TDD)
`src/vibey_tools/explorer/test/test_candidate.py`:
- `test_a_candidate_keeps_its_provenance`
- `test_intake_arguments_are_the_flags_vibey_new_accepts` (with and without an offer)
- `test_an_unusable_candidate_is_refused` — parametrized over the nine messages of Required behaviour 1
- `test_the_candidate_satisfies_its_interface`
`tests/meta/test_explorer_speaks_the_intake_vocabulary.py`:
- `test_explorer_source_kinds_equal_the_intake_kinds`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/explorer && python -m pytest -q && python -m mypy
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta/test_explorer_speaks_the_intake_vocabulary.py

## Out of scope
- Discovery sources (blocked on #87 open question 2), classification FOSS/paid (blocked on #87
  open question 1), scoring (`roadmap-87-scoring-skiplist`), fetching (`roadmap-87-polite-fetcher`).
- Docs, CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
