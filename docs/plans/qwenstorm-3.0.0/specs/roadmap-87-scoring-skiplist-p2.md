## Title
feat(explorer): the skip registry — a project that declines machine contributions is skipped once and recorded forever

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, Scope 4 "with the skip list for projects that
decline machine contributions", Acceptance "A project whose CONTRIBUTING declines machine
contributions is skipped and recorded (test)"). Runbook 21
(`docs/runbooks/expansion/21-vibey-explorer.md`, "2. An unsolicited PR spends someone else's time"):
"A project that declines machine-generated contributions is skipped, and that skip is recorded so it
is never re-evaluated by accident"; Verification: it "is skipped before any build spend, and lands
in the skip registry". Constitution III.4 (machine speech is labelled) and SD-01 §1 (public channels
only) make respecting a project's stated policy non-negotiable. Reading a CONTRIBUTING file into a
verdict is natural-language judgement and is **not** this lane: here the verdict is an input, and
the registry is the durable, append-only memory the runbook requires.

## Required behaviour
In `src/vibey_tools/explorer/vibey_explorer/skip_registry.py`, contracts in
`vibey_explorer/interfaces/skip_registry_interface.py` (stdlib only):
1. `class PolicyVerdict(StrEnum)`: `DECLINES = "declines-machine-contributions"`,
   `ALLOWS = "allows"`, `UNKNOWN = "unknown"`.
2. `@dataclass(frozen=True, slots=True) class SkipRecord`: `repository: str`, `reason: str`,
   `recorded_at: datetime` (aware), `source_url: str`.
3. `class InMemorySkipStore` and `class JsonlSkipStore(path: Path)`, both implementing
   `SkipStoreInterface`: `append(record: SkipRecord) -> None` and `get(repository: str) -> SkipRecord | None`.
   The JSONL store appends one `json.dumps(..., sort_keys=True)` line per record (never rewrites
   the file; `recorded_at` as ISO-8601), creates the parent directory, and reads the file back on
   `get` (first record for a repository wins). A malformed line raises
   `ValueError(f"skip registry line {n} is not a skip record")`.
4. `class SkipRegistry`: `__init__(self, store: SkipStoreInterface, *, clock: Callable[[], datetime])`.
   - `apply(self, candidate: Candidate, verdict: PolicyVerdict) -> bool` — True when the candidate
     may proceed. An already-skipped `candidate.repository` → False without appending again (never
     re-evaluated). `DECLINES` → append
     `SkipRecord(candidate.repository, "the project's contribution policy declines machine-authored contributions", clock(), candidate.source_url)`
     and return False. `ALLOWS` and `UNKNOWN` → True (an unknown policy is not a refusal; the
     disclosure rules still apply downstream). A candidate with an empty `repository` →
     `ValueError("a skip needs the candidate's repository")` only when a skip would be recorded.
   - `is_skipped(self, repository: str) -> bool`.

## Where to change
- New: `vibey_explorer/skip_registry.py`, `vibey_explorer/interfaces/skip_registry_interface.py`.
- New test file `src/vibey_tools/explorer/test/test_skip_registry.py`.

## Acceptance criteria
- [ ] A `DECLINES` verdict records exactly one skip and excludes the candidate; a second candidate
      from the same repository with an `ALLOWS` verdict is still excluded and nothing new is appended.
- [ ] The JSONL file only grows; its lines are sorted-key JSON; a fresh `JsonlSkipStore` on the
      same path sees earlier skips.
- [ ] 100% branch coverage; mypy clean; stdlib only.

## Tests to write first (TDD)
`src/vibey_tools/explorer/test/test_skip_registry.py`:
- `test_a_declining_project_is_skipped_and_recorded`
- `test_a_recorded_skip_is_never_re_evaluated`
- `test_allowed_and_unknown_policies_proceed`
- `test_the_jsonl_store_only_appends_and_survives_a_restart` (`tmp_path`)
- `test_a_malformed_registry_line_is_named`
- `test_a_skip_needs_a_repository`
- `test_the_stores_and_registry_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/explorer && python -m pytest -q && python -m mypy
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Reading CONTRIBUTING/AI-policy text into a verdict (a later lane; natural-language judgement runs
  on sovereignloop's queue under 8.c). Rate caps and staleness (#87 open question 3). Docs,
  CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
