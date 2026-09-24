## Title
test(gh): a seeded property test proves, on every adapted forge, that a verdict for one head never stands for another

## Why
Issue #138 (rewrite: `issue-audit/updates/138.md`, Scope 3: "Exact-head semantics survive
translation on every adapter. A verdict binds to a SHA, never to a change request's moving head.
There is one property test per adapter"; "Proposed child issues" 4). The Constitution's exact-head
review (Article V.1) is the promise; sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`,
`:168-177`) says every forge speaks the one protocol, so the promise must hold on GitHub, GitLab
and the default Forgejo alike.

Where the binding happens (verified in the integration clone):
- `vibey_gh/forge.py:69-76`: `ChangeRequest.head_sha` "is part of its identity … A verdict binds
  to the commit it".
- `vibey_gh/pr_automation.py:312-331` `evaluate(pr, cfg, *, expected_sha, stored)`: a head that
  is not `expected_sha` returns `blocked` with the reason
  `f"stale event for {expected_sha}; current head is {head}"` (`:330-331`).
- `pr_automation.py:295-310` `lineage_for(stored, head)`: a stored state for another head
  starts a new lineage.
- `pr_automation.py:439-442`: `if state.review_sha != head: return result("review", "current head requires automated review")`
  — a review recorded for an older head never stands in for the current one.
After the forge wave, the `pr` mapping `evaluate` reads comes from the adapter verb
`change_request_facts(number)` (spec `forge-0b`, C5 `ChangeRequestFacts` in
`specs/forge-adapter.md`), one per forge. Nothing today proves those three rules hold for the
values each adapter produces. This lane adds that proof; it changes no production code.

## Required behaviour
One new test module, `src/vibey_tools/gh/test/test_exact_head_property.py`, parametrized over
the three adapted kinds `("github", "gitlab", "forgejo")`:

1. **The forge double.** For each kind, a helper `forge_at(kind, head: str, *, draft=False)`
   returns an adapter whose `change_request_facts(7)` answers a C5 mapping for pull request 7
   with `headRefOid == head`, author `owner`, `state` OPEN, `mergeable` MERGEABLE, base
   `develop`, not draft, `reviewDecision` `""`, and one completed successful check named
   `"CI"` on that head:
   - GitHub: `GitHubForge(root=tmp_path, transport=<double>).for_repository("o/r")`, where the
     double copies `ScriptedTransport` from `test/test_forge_adapters.py:24-36` but answers
     every `survey` with `(facts_for(head), "")`; `facts_for` builds the dict with the C5 keys
     (`forge.CHANGE_REQUEST_FACT_KEYS`, added by `forge-0b`) and a `statusCheckRollup` of
     `[{"name": "CI", "status": "COMPLETED", "conclusion": "SUCCESS", "startedAt": "2026-09-22T00:00:00Z", "completedAt": "2026-09-22T00:01:00Z", "detailsUrl": ""}]`.
   - Forgejo and GitLab: `RoutedTransport` from `test/forge_doubles.py` (added by `forge-0a`),
     routed exactly as `forge-0b`'s V5 reads them (the pull/merge-request object carrying the
     head, one `CI` status `success` for that sha, and an empty reviews/approvals list), with
     `ForgejoForge(root=tmp_path, transport=…)` / `GitLabForge(root=tmp_path, transport=…)`.
     Copy the route keys from `forge-0b`'s own Forgejo/GitLab V5 tests; do not invent paths.
2. **The heads.** `heads(seed) -> list[str]`: `rng = random.Random(seed)`; a length
   `rng.randint(2, 6)` list of distinct 40-character lowercase hex strings
   (`f"{rng.getrandbits(160):040x}"`, redrawn on a repeat). Seeds are `range(25)`. No
   hypothesis: vibey-gh's dev extra has none (`pyproject.toml:33-37`) and it stays stdlib-only.
3. **`test_a_stale_expected_head_is_always_refused`** (kind × seed): for each position `i`,
   with the forge at `heads[i]` and `facts, problem = forge.change_request_facts(7)`
   (`problem == ""`), every earlier head `e` in `heads[:i]` gives
   `evaluate(facts, cfg, expected_sha=e).state == "blocked"` and
   `.reason == f"stale event for {e}; current head is {heads[i]}"`.
4. **`test_a_review_of_an_older_head_never_makes_the_current_one_ready`** (kind × seed): for
   each `i ≥ 1`, with `stored = AutomationState(lineage_sha=heads[i-1], current_sha=heads[i-1], review_sha=heads[i-1], review_passed=True)`,
   `evaluate(facts_at(heads[i]), cfg, expected_sha=heads[i], stored=stored).state == "review"`
   (never `"ready"`), and the same call with a stored review of `heads[i]` itself is `"ready"`
   (so the property is never vacuous).
5. **`test_the_lineage_restarts_on_every_head_move`** (kind × seed): for consecutive heads,
   `lineage_for(state_for(prev), cur)` has `lineage_sha == current_sha == cur`,
   `review_sha is None` and `attempts == 0`, and keeps `history`.
6. `cfg = GhConfig(root=tmp_path, owner="owner", pr_automation=PrAutomationConfig(scan_workflows=("CI",)))`
   (verify the `PrAutomationConfig` field name at `config.py`; `OWN_CHECKS`/`ignored_checks`
   must not swallow `"CI"`).
7. The module docstring states the property in one sentence and names the three code points
   above. Module-level test functions are fine (pytest collects functions).

## Where to change
- New `src/vibey_tools/gh/test/test_exact_head_property.py` only (provenance header copied from
  `test/test_forge_adapters.py:1`). No production file changes. If a property fails, do not
  "fix" production code in this lane: mark nothing xfail, stop, and report the failing kind,
  seed and heads.

## Acceptance criteria
- [ ] 3 kinds × 25 seeds for each of the three tests, all passing, in under 30 seconds.
- [ ] Every test proves non-vacuity (test 4's `"ready"` leg runs for every kind).
- [ ] No network, no `gh` binary, no `mock.patch`, no `monkeypatch.setattr` (doubles are
      injected through the adapters' `transport=` seam).
- [ ] vibey-gh's whole suite passes with its 100% branch floor (a tests-only lane cannot lower it).

## Tests to write first (TDD)
The three tests above are the deliverable:
`test_a_stale_expected_head_is_always_refused`,
`test_a_review_of_an_older_head_never_makes_the_current_one_ready`,
`test_the_lineage_restarts_on_every_head_move`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_exact_head_property.py
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Any production change (the adapters, `pr_automation`, `merge_train`).
- The merge train's gate read (`merge_train.py:290-309`), which `forge-1` moves onto the adapter;
  its pagination defect is gaps.md §L5.
- A Bitbucket adapter (#298, blocked). Docs, CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
