# ADR-0036: the merge queue is declared, not clicked

- **Status:** Accepted
- **Date:** 2026-09-15
- **Refines:** ADR-0018 (everything-as-code, and never less generic) and
  ADR-0028 (vibey-gh owns provenance and release). Supersedes nothing.

## Context

`vibey-gh` already reconciles branch protection from configuration.
`rulesets.py` declares `deletion`, `non_fast_forward`, `required_linear_history`,
`pull_request` and `required_status_checks`, builds them from a `RulesetConfig`
in `.vibey-gh.toml`, and carries forward any rule type it does not declare
rather than deleting someone else's work.

A merge queue was never modelled. Measured on this repository on 2026-09-15:
`grep -rn "merge_queue\|merge-queue\|merge_group"` over `vibey_gh/`,
`.github/` and `.vibey-gh.toml` returns nothing, while the live `develop`
ruleset carries a `code_coverage` rule that `desired_rules()` never emits --
settings-page state with no history, no review and no way to restore it. That
is exactly the condition ADR-0018 exists to end, and it had already recurred.

The gap matters beyond tidiness. `strict_required_status_checks_policy` is
`true` for both permanent branches, so every pull request must be up to date
with its base before it can merge. With a queue, that is the queue's job. With
no queue it is a human's, serially, and the cost is visible: on 2026-09-15
twelve pull requests were open against `develop` and ten could not merge.

And a green branch is not a green merge. A pull request whose checks passed
against an older base proves only that *that* combination was green. Nothing
between `develop`'s tip and the branch's base is tested by that run. Requiring
each branch to be rebuilt by hand is a way of paying for that proof one PR at
a time, with the base moving underneath.

## Decision

**The merge queue is declared in `.vibey-gh.toml` and reconciled from it, like
every other rule on a permanent branch. It is never configured in a settings
page.**

1. **One more declared rule type.** `MERGE_QUEUE = "merge_queue"` joins the
   types `rulesets.py` owns, and `desired_rules()` emits it from policy. It is
   not a special case: an unknown rule found on an existing ruleset is still
   carried forward and reported, because a silent deletion of someone else's
   rule is still indistinguishable from data loss.

2. **Every knob is configuration, none is a constant.** GitHub requires all
   seven `merge_queue` parameters, so `MergeQueueConfig` carries all seven --
   `check_response_timeout_minutes`, `grouping_strategy`,
   `max_entries_to_build`, `max_entries_to_merge`, `merge_method`,
   `min_entries_to_merge`, `min_entries_to_merge_wait_minutes`. A hard-coded
   value here would be a decision taken away from the next adopter, silently
   (ADR-0018). The defaults are conservative, not absent.

3. **Off by default, per branch.** `enabled` defaults to `false`. A merge queue
   changes when and how a merge happens for everyone who uses the repository;
   turning that on by upgrading a tool would be a behaviour change nobody
   asked for. Each permanent branch configures its own queue, because the two
   branches do not merge the same way.

4. **`merge_method` follows the declared branch flow, it does not contradict
   it.** Feature pull requests squash into `develop`; `develop` is promoted to
   `main` as a rebase, to keep history linear. So the integration queue
   defaults to `SQUASH` and the release queue to `REBASE`, matching
   `[branches]` and the `allow_*_merge` flags already in
   `repository_profile`. `MergeQueueConfig` refuses `MERGE` outright when
   linear history is required, because a rule set that demands linear history
   and a queue that creates merge commits is a configuration that cannot
   succeed -- and failing at load is cheaper than failing at merge.

5. **The queue does not replace the gate, it feeds it.** A queue is only as
   good as the checks it waits for, so `required_checks` remains the source of
   truth for what must pass; `grouping_strategy` decides whether the whole
   group must be green (`ALLGREEN`) or only its head (`HEADGREEN`), and
   defaults to `ALLGREEN`.

## Consequences

- Branch protection and the merge queue are restored from one file. A
  repository that loses both can reconcile them back; today it could restore
  only half.
- The `code_coverage` drift on `develop` becomes visible as drift rather than
  passing unnoticed, because reconciliation now reports every rule it did not
  declare.
- Adopters get a queue they can shape. A project that wants `HEADGREEN`, a
  longer check timeout, or larger groups says so in one line rather than
  editing vibey-gh.
- Enabling a queue changes merge timing: a pull request that would have merged
  immediately now waits for its group. That is the trade being bought --
  proof that the merged result is green, rather than proof that the branch was.
- This is mechanism, not conduct, so it files as an ADR and not as a
  sub-doctrine. The conduct rule it rests on -- that the declared state is the
  state (sub-doctrine 12.c) -- already exists and is what this ADR applies.
