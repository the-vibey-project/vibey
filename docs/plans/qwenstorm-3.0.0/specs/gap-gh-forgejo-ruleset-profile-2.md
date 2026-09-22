## Title
feat(gh): on Forgejo, branch rules apply the declared profile, mapping what it maps and printing every waiver

## Why
`gap-gh-forgejo-ruleset-profile-1` declares, per rule Forgejo cannot express, `map` or
`waive` with a reason. forge-0g's `ForgejoBranchRules.protection(document)` still refuses all
six (`specs/forge-0g.md:32-50`). This lane makes it honour the declaration without ever
dropping a rule silently (10.f, and `rulesets.reconcile_one`'s own no-silent-skip rule,
`vibey_gh/rulesets.py:226-230`).

## Required behaviour
1. `ForgejoBranchRules` (`vibey_gh/forge_forgejo_rules.py`, from forge-0g) gains
   `__init__(self, profile: ForgejoRulesProfile = ForgejoRulesProfile()) -> None`, a
   constructor seam whose default reproduces forge-0g exactly.
2. `protection(document)`:
   - A refused rule that the profile **maps** is translated instead:
     - `require_last_push_approval` becomes `"dismiss_stale_approvals": True`;
     - `require_code_owner_review` becomes `"block_on_official_review_requests": True`.
   - A refused rule that the profile **waives** is left out of the payload.
   - Any refused rule the profile names in neither still refuses with forge-0g's exact
     `NotSupported` sentence, naming only the still-refused items.
3. New method `waivers(self, document) -> tuple[str, ...]`: one line per waived rule
   **present** in the document, in the fixed order of the six names:
   `f"WAIVED on Forgejo: {rule} — {reason}"`. It returns `()` when nothing is waived.
4. `ForgejoForge.create_branch_rules` and `update_branch_rules` (forge-0g) print each line of
   `self._rules.waivers(document)` to stderr before the request, so a waiver is visible in every
   run's log. `ForgejoForge` gets its `ForgejoBranchRules` through a new dataclass field
   `rules: ForgejoBranchRulesInterface = field(default_factory=ForgejoBranchRules)`.
   `ForgeSelector.resolve`, where it builds `ForgejoForge` from `GhConfig`, passes
   `ForgejoBranchRules(cfg.rulesets.forgejo)`.
5. `ForgejoBranchRulesInterface` (forge-0g) gains `waivers`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/forge_forgejo_rules.py` and its interface
  `vibey_gh/interfaces/forge_forgejo_rules_interface.py`.
- `vibey_gh/forge_forgejo.py` (the two write verbs and the new field).
- The Forgejo branch of `vibey_gh/forge_selector.py` (one argument).
- Tests: append to `src/vibey_tools/gh/test/test_forge_branch_rules.py` (created by forge-0g).
  Use `ForgejoForge` with a routed transport double and capture stderr with `capsys`. No patching.

## Acceptance criteria
- [ ] With the default profile, forge-0g's tests pass unchanged, including its refusal of the
      default policy naming `required_linear_history`, `required_review_thread_resolution` and `bypass_actors`.
- [ ] A profile that waives the three rules and maps the other two yields a payload with
      `dismiss_stale_approvals` and `block_on_official_review_requests` set to true and no
      refusal, and `waivers()` returns the three exact lines.
- [ ] `create_branch_rules` prints the waiver lines to stderr before the request (assert the order with the recorded transport).
- [ ] A profile that waives only `merge_queue` still refuses, naming the remaining items only.
- [ ] Round trip: for a mapped document,
      `rulesets.diff_ruleset(doc, document(protection(doc)…)).changed` behaves as forge-0g
      specifies for expressible policies, or, if a mapped field cannot round-trip, the test
      pins the known difference and the commit body says so.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
Append to `test/test_forge_branch_rules.py`:
- `test_default_profile_keeps_forge_0g_refusals`
- `test_mapped_rules_translate`
- `test_waived_rules_are_dropped_and_listed`
- `test_waivers_are_printed_before_the_write`
- `test_partially_declared_profile_still_refuses_the_rest`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Forgejo push and merge whitelists for bypass actors (a follow-up), the GitLab adapter, and docs.

Commit as `feat(gh): Forgejo branch rules apply the declared profile`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
