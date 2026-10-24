# 0096 — On Forgejo, branch rules are mapped where Forgejo can express them and waived loudly where it cannot

**Status:** proposed · **Date:** 2026-10-24 · **Cites:** sub-doctrines 8.b, 10.f, 12.c · **Related:** ADR-0028, vibey-gh ADR-0002 · **Ruling:** #668, item 7

## Context

Sub-doctrine 8.b makes Forgejo the default forge. The storm's forge-adapter specification
(`specs/forge-0g.md`, under `docs/plans/qwenstorm-3.0.0/`) translates a GitHub ruleset document into
Forgejo branch protection, and refuses six ruleset rules that Forgejo's branch protection cannot express:

- `required_linear_history`
- `merge_queue`
- `required_review_thread_resolution`
- `require_code_owner_review`
- `require_last_push_approval`
- a non-empty `bypass_actors`

The refusal is honest (10.f), but it means the default `[rulesets]` policy makes `vibey-gh rulesets` fail
on the default forge. Sub-doctrine 12.c asks that an adopter's answer to that be declared in the
repository, not decided at the keyboard. That translation is specified, not yet built: there is no
`forge_forgejo_rules.py` in the tree.

## Decision

**For each of the six, the repository declares either a mapping to the nearest Forgejo setting or a
waiver with a written reason. Where Forgejo can express a rule it is mapped; where it cannot it is waived,
loudly.** A rule that is named in neither stays refused, which is today's behaviour, so the default
changes nothing. The declaration is a `[rulesets.forgejo]` table: a `map` list, and a `waive` table
whose reasons are not empty. A rule in both is an error.

The storm's proposal for this repository, which the operator's ruling adopts and this record's merge
carries:

| rule | disposition |
|---|---|
| `require_last_push_approval` | **map** to Forgejo's `dismiss_stale_approvals = true` |
| `require_code_owner_review` | **map** to `block_on_official_review_requests = true` (approximate) |
| `required_linear_history` | **waive**: the merge train squashes and promotion rebases (ADR-0028), so history is linear by construction |
| `merge_queue` | **waive**: `vibey-gh merge-train` is this repository's merge queue |
| `required_review_thread_resolution` | **waive**: the merge train re-reads review state before merging |
| `bypass_actors` | **waive**: Forgejo's push and merge whitelists are a follow-up |

## Consequences

- **The two mappings are approximate.** They were chosen from the proposal and have not been checked on a
  real Forgejo. They must be verified on the target Forgejo version before anything relies on them, and a
  mapping that proves wrong becomes a waiver.
- **Every waiver is printed** each time branch rules are applied, so a rule the forge does not enforce is
  never silent.
- **Nothing is built.** The configuration table, its parsing and the rule translation are still to be
  written; the storm's `gap-gh-forgejo-ruleset-profile` specifications describe them.
- **Rule status.** A decision under 8.b and 12.c, not a new rule: it owes no sub-doctrine (ADR-0020).
