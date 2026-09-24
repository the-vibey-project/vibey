## Title
feat(domain): the evidence-bounded status vocabulary — a claim names its object, source, scope and cutoff

## Why
10.f (`src/vibey_tools/gh/docs/doctrines.md:419` at integration HEAD `4317cff6`): "every claim
about implementation, completion, failure, research or live operation is tied to observable …
evidence whose scope and cutoff are stated … When evidence is missing, stale, contradictory or
outside the stated scope, the state is unknown or blocked". ADR-0040
(`docs/architecture/decisions/0040-evidence-bounded-status.md:23-48`) fixes the vocabulary:
- `unknown`: evidence is absent, stale or contradictory;
- `active`: work has not reached a terminal event;
- `blocked`: a concrete condition prevents the next safe step;
- `failed`: a terminal event records unsuccessful work;
- `verified`: the stated checks passed for the stated revision;
- `published`: the stated remote head and pull request are evidenced.

A claim names "the object being claimed", "the evidence source" and "the scope and observation
cutoff". "When sources disagree, the narrowest supported status wins." No such vocabulary exists
in the domain, and `vibey status`, `watch` and the TUI print state with no source or cutoff (gap
N6, `issue-audit/gaps.md:749-755`). This lane adds the pure vocabulary. `gap-status-evidence-dashboard`
and `gap-status-cli-evidence` put it on the surfaces.

## Required behaviour
1. New pure module `src/vibey/domain/status_claim.py` (provenance header on line 1; imports only
   `collections.abc`, `dataclasses`, `datetime` (types only, never `now()`), `enum`, `typing`,
   `vibey.domain.job`, `vibey.domain.phase`):
   - `class EvidenceStatus(StrEnum)`: `UNKNOWN = "unknown"`, `ACTIVE = "active"`,
     `BLOCKED = "blocked"`, `FAILED = "failed"`, `VERIFIED = "verified"`, `PUBLISHED = "published"`.
   - `class EvidenceSource(StrEnum)`:
     - ADR-0040's four sources: `TRACKED_CODE = "tracked-code"`, `TEST_RESULT = "test-result"`,
       `REMOTE_RESPONSE = "remote-response"`, `EVENT_STREAM = "event-stream"`;
     - `STORE_SNAPSHOT = "store-snapshot"`: vibey's own state rows (project, job, engine health)
       read at the cutoff. Its docstring says those rows are neither tracked code nor an event
       stream.
   - `@dataclass(frozen=True, slots=True) class StatusClaim` with fields, in this order:
     `subject: str` (the object claimed), `status: EvidenceStatus`, `source: EvidenceSource`,
     `locator: str` (where in that source), `scope: str`, `cutoff: datetime`, `detail: str = ""`.
     - `__post_init__` raises `ValueError(f"{name} must not be empty")` for a blank `subject`,
       `locator` or `scope` (`not value.strip()`).
     - It raises `ValueError("cutoff must be timezone-aware")` when `cutoff.utcoffset() is None`.
     - `render(self) -> str` returns exactly
       `f"{subject}: {status.value}{d} — scope: {scope}; source: {source.value} ({locator}); cutoff: {cutoff.isoformat()}"`,
       where `d = f" ({detail})" if detail else ""`.
     - `to_payload(self) -> dict[str, str]` returns the keys `subject`, `status`, `detail`,
       `source`, `locator`, `scope` and `cutoff` (`isoformat()`), with enum values as strings.
   - `class StatusPolicy` (stateless), with:
     - `for_job_state(self, state: StoredJobState) -> EvidenceStatus | None`:
       - `READY` and `LEASED` give `ACTIVE`;
       - `AWAITING_HUMAN` and `AWAITING_CAPACITY` give `BLOCKED`;
       - `FAILED` gives `FAILED`;
       - `SUCCEEDED` and `CANCELLED` give `None`: terminal outcomes the vocabulary does not
         name, shown under their own name;
       - an `UnrecognizedJobState` gives `UNKNOWN`.
     - `for_project(self, phase: StoredPhase, queue_depth: Mapping[StoredJobState, int]) -> tuple[EvidenceStatus, str]`.
       The rules apply in this order, and each returns (status, detail):
       1. `phase` is not a `Phase` member: `(UNKNOWN, f"phase {phase.value} is not one this vibey knows")`.
       2. `phase is Phase.ABANDONED`: `(FAILED, "phase abandoned")`.
       3. `phase is Phase.DONE`: `(UNKNOWN, "phase done is a marker; this surface reads no verification evidence")`.
          A marker is not delivery (10.f).
       4. Let `n` be the sum of positive counts whose state maps to `UNKNOWN`. When `n > 0`:
          `(UNKNOWN, f"{n} job(s) in a state this vibey does not know")`.
       5. `ready + leased > 0`: `(ACTIVE, f"ready {ready}, leased {leased}")`.
       6. `awaiting_human + awaiting_capacity > 0`:
          `(BLOCKED, f"awaiting_human {h}, awaiting_capacity {c}")`.
       7. Otherwise: `(UNKNOWN, f"no job is ready, leased or parked in phase {phase.value}")`.
     - `narrowest(self, statuses: Sequence[EvidenceStatus]) -> EvidenceStatus` (ADR-0040's
       disagreement rule):
       - empty gives `UNKNOWN`;
       - all equal gives that status;
       - all in `(ACTIVE, VERIFIED, PUBLISHED)` gives the earliest of them in that order;
       - anything else gives `UNKNOWN`, because the sources contradict each other.
     - `as_of(self, claim: StatusClaim, now: datetime, max_age: timedelta) -> StatusClaim`:
       - a naive `now` raises `ValueError("now must be timezone-aware")`;
       - `max_age < timedelta(0)` raises `ValueError("max_age must not be negative")`;
       - when `now - claim.cutoff > max_age`, it returns
         `dataclasses.replace(claim, status=EvidenceStatus.UNKNOWN, detail=f"stale: observed {now - claim.cutoff} before {now.isoformat()}")`;
       - otherwise it returns `claim` unchanged.
   - `STATUS_POLICY: Final[StatusPolicyInterface] = StatusPolicy()`, and `__all__` with every public name.
2. New `src/vibey/domain/interfaces/status_claim_interface.py`, in the style of
   `publication_policy_interface.py:1-20`: `StatusClaimInterface` (the seven properties, `render`,
   `to_payload`) and `StatusPolicyInterface` (the four methods), both `@runtime_checkable`
   Protocols. Domain types are imported under `TYPE_CHECKING` only.
3. `src/vibey/domain/interfaces/__init__.py`: import both after the `publication_policy_interface`
   block (`:49-56`), and add `"StatusClaimInterface"` and `"StatusPolicyInterface"` to `__all__`
   between `"SovereignResearchUnavailableInterface"` and `"StoredValueParserInterface"`
   (`:136-137`). Use edit_file.
4. Nothing else changes.

## Where to change
- New: `src/vibey/domain/status_claim.py`, `src/vibey/domain/interfaces/status_claim_interface.py`,
  `tests/domain/test_status_claim.py`.
- Edit: `src/vibey/domain/interfaces/__init__.py` (two insertions).
- These are pure values and policy, so there is no fake to register (the fakes registry scans
  application ports, `specs/fakes-registry.md:93-96`).

## Acceptance criteria
- [ ] `StatusClaim(subject=" ", …)` and a naive cutoff raise `ValueError`.
- [ ] `render()` of a claim with `detail="ready 1, leased 0"` equals the exact f-string above.
- [ ] `for_project` covers rules 1–7, each pinned by a test case.
- [ ] `narrowest([VERIFIED, PUBLISHED]) is VERIFIED`, `narrowest([ACTIVE, FAILED]) is UNKNOWN`
      and `narrowest([]) is UNKNOWN`.
- [ ] `as_of` turns a claim 11 minutes old into `UNKNOWN` at `max_age=timedelta(minutes=10)`, and
      keeps a claim 9 minutes old.
- [ ] `isinstance(STATUS_POLICY, StatusPolicyInterface)` and `isinstance(<a claim>, StatusClaimInterface)`.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_status_claim.py` (provenance header):
- `test_the_vocabulary_is_adr_0040s` (the six values, in order)
- `test_a_claim_refuses_blank_fields_and_a_naive_cutoff` (parametrized)
- `test_render_names_object_status_scope_source_and_cutoff` (with and without `detail`)
- `test_to_payload_carries_every_field_as_text`
- `test_job_states_map_to_the_vocabulary` (parametrized over the seven `JobState` members and an
  `UnrecognizedJobState`)
- `test_project_status_rules` (parametrized, ids naming the rule, one case per rule 1–7, plus
  "active wins over blocked" when both counts are positive)
- `test_narrowest_supported_status_wins` (parametrized)
- `test_a_stale_claim_becomes_unknown` and `test_as_of_refuses_a_naive_now_and_a_negative_age`
- `test_the_policy_and_a_claim_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Showing claims on any surface (`gap-status-evidence-dashboard`, `gap-status-cli-evidence`).
- Claims about runs, branches and pull requests (`VERIFIED`, `PUBLISHED` producers). The
  vocabulary carries them, and their producers are follow-ups.
- Docs, CHANGELOG.md, ADRs.

Commit as `feat(domain): the evidence-bounded status vocabulary`. Do not push.

## Lane card
- **Depends on:** nothing.
- **Kind:** one pure domain module, its interface, one test file.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
