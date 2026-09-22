## Title
feat(gh): a declared Forgejo ruleset profile says, per rule Forgejo cannot express, whether to map it or waive it with a reason

## Why
8.b makes Forgejo the default forge. forge-0g's `ForgejoBranchRules.protection(document)` (new
file `vibey_gh/forge_forgejo_rules.py`, see `specs/forge-0g.md:32-50`) refuses six ruleset rules
that Forgejo's branch protection cannot express:
- `required_linear_history`;
- `merge_queue`;
- `required_review_thread_resolution`;
- `require_code_owner_review`;
- `require_last_push_approval`;
- non-empty `bypass_actors`.

So the **default** `[rulesets]` policy makes `vibey-gh rulesets` fail on the default forge
(`specs/forge-adapter.md:1866-1872`, `issue-audit/gaps.md` L7). The refusal is honest (10.f).
But 12.c (`doctrines.md:455`) needs the adopter's choice to be declared: map each rule to the
nearest Forgejo setting, or waive it loudly with a written reason.

This lane adds the declaration. `-2` applies it. **The values for this repository follow the
operator's ruling (`gap-ops-canon-rulings` item 7). The proposal below is only a proposal.**

## Required behaviour
1. `vibey_gh/config.py`: the rulesets configuration dataclass (find it:
   `grep -n "class Rulesets" src/vibey_tools/gh/vibey_gh/config.py`) gains
   `forgejo: ForgejoRulesProfile = ForgejoRulesProfile()`, a new frozen dataclass:
   - `map: tuple[str, ...] = ()`: rules to translate. Only `require_last_push_approval` and
     `require_code_owner_review` may be mapped; any other name raises
     `ValueError("rulesets.forgejo.map: <name> has no Forgejo equivalent; waive it with a reason or leave it refused")`.
   - `waive: Mapping[str, str] = {}`: rule name to reason. The reason must be a non-empty
     string of at least 10 characters (`ValueError` naming `rulesets.forgejo.waive.<name>`).
     The names must be among the six refused rules.
   - A name in both `map` and `waive` raises `ValueError`.
   - Every rule not named stays **refused**, which is today's behaviour, so the default
     changes nothing.
2. `load_config` parses `[rulesets.forgejo]`, with `map = [...]` and a `waive` sub-table,
   following the pattern of the other nested tables in the file.
3. The root `.vibey-gh.toml` gains a `[rulesets.forgejo]` table with the **ruled** values.
   Read them from STORM-CONTEXT.md's "Operator rulings" (recorded by `gap-ops-canon-rulings`).
   If no ruling is recorded, stop and report BLOCKED. The proposal the operator rules on:
   - map `require_last_push_approval` to Forgejo's `dismiss_stale_approvals = true`;
   - map `require_code_owner_review` to `block_on_official_review_requests = true`
     (approximate; to be verified on the target Forgejo version);
   - waive `required_linear_history`: "the merge train squashes and promotion rebases (ADR-0028); history stays linear by construction";
   - waive `merge_queue`: "vibey-gh merge-train is this repository's merge queue";
   - waive `required_review_thread_resolution`: "the merge train re-reads review state before merging";
   - waive `bypass_actors`: "Forgejo push/merge whitelists are managed as a follow-up".

## Where to change
- `src/vibey_tools/gh/vibey_gh/config.py` (edit_file only).
- `.vibey-gh.toml` (root).
- Tests: append to `src/vibey_tools/gh/test/test_config.py`.

## Acceptance criteria
- [ ] With no table, `ForgejoRulesProfile()` has empty `map` and `waive`, so every rule is refused as today.
- [ ] An unmappable name in `map`, a short reason, an unknown rule, or a rule in both raises the exact `ValueError`.
- [ ] The root config loads, with the ruled values.
- [ ] vibey-gh's gates pass.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_config.py`:
- `test_forgejo_profile_defaults_refuse_everything`
- `test_forgejo_profile_validation` (parametrized)
- `test_repository_declares_its_forgejo_profile`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Applying the profile (`gap-gh-forgejo-ruleset-profile-2`), and docs.

Commit as `feat(gh): declare a Forgejo ruleset profile`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
