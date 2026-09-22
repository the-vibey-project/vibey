## Title
refactor(gh): the interaction rules every emitting surface shares move behind `InteractionPolicy`, and conversation delegates to it unchanged

## Why
Issue #85 (rewrite: `issue-audit/updates/85.md`, Scope 1 and "Proposed child issues" 1): the
operator's one design principle for every emitting surface is "**Interactive, never
broadcast-only** … rate limits, identity labelling, and per-repo opt-in". Today those rules exist
on exactly one surface, as private helpers of `src/vibey_tools/gh/vibey_gh/conversation.py`:

- the loop guard (self-exclusion) `_is_own_comment` (`conversation.py:219-226`);
- trust `_trusted` (`:229-234`: `trusted_authors` plus the owner, normalised by
  `config.normalise_actor`, `config.py:1961-1970`);
- the stranger opt-in `if not trusted and not policy.respond_to_untrusted` (`:279-280`);
- the per-thread budget `if state.interactions >= policy.max_interactions` (`:281-286`);
- text-is-data: every contributor string is bounded by `issue_automation.sanitize`
  (`issue_automation.py:107-116`) before it reaches a summary (`request_of`, `:111-120`).

Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`) says a capability the family has is
reused, never re-implemented; 9.b (`doctrines.md:349`) says it lives in a class with an interface.
Matrix replies (#85), Moltbook (#139), OpenClaw (#297) and `@vibey` on forges (#145) will all need
these rules. vibey-gh is dependency-free (`src/vibey_tools/gh/pyproject.toml:30`), so the
conductor may import it later (CLAUDE.md, the `domain/` import rule). This lane only extracts:
behaviour is byte-for-byte unchanged.

## Required behaviour
1. New `src/vibey_tools/gh/vibey_gh/interaction_policy.py`, class
   `InteractionPolicy(InteractionPolicyInterface)`:
   - `__init__(self, *, ignore_actors: tuple[str, ...], trusted_actors: tuple[str, ...], respond_to_untrusted: bool, max_interactions: int) -> None`.
     Stores the normalised sets (`normalise_actor`) once.
   - `@classmethod from_config(cls, cfg: GhConfig) -> InteractionPolicy`: `ignore_actors=cfg.conversation.ignore_actors`,
     `trusted_actors=cfg.trusted_authors + ((cfg.owner,) if cfg.owner else ())`,
     `respond_to_untrusted=cfg.conversation.respond_to_untrusted`,
     `max_interactions=cfg.conversation.max_interactions`.
   - `is_own(self, author: str) -> bool` — exactly `_is_own_comment`'s rule.
   - `is_trusted(self, author: str) -> bool` — exactly `_trusted`'s rule (an empty login is
     never trusted).
   - `may_respond(self, author: str) -> bool` — `self.is_trusted(author) or self._respond_to_untrusted`.
   - `within_budget(self, interactions: int) -> bool` — `interactions < self._max_interactions`.
   - `as_data(self, text: str, *, limit: int = 300) -> str` — `issue_automation.sanitize(text, limit=limit)`
     (text is data: bounded, flattened, control characters removed).
   - Class docstring: the four rules and why (copy the reasoning from `conversation.py:1-24`).
2. New `src/vibey_tools/gh/vibey_gh/interfaces/interaction_policy_interface.py`:
   `InteractionPolicyInterface`, a `runtime_checkable` Protocol declaring the five methods above
   with docstrings (no `from_config`, which is construction). It imports nothing from
   `vibey_gh` outside `interfaces/`.
3. `conversation.py`:
   - `evaluate(comment, subject, cfg, *, stored=None, policy: InteractionPolicyInterface | None = None)`;
     `rules = policy or InteractionPolicy.from_config(cfg)`.
   - Replace `_is_own_comment(author, cfg)` with `rules.is_own(author)`, `_trusted(author, cfg)`
     with `rules.is_trusted(author)`, the stranger check with `if not rules.may_respond(author):`
     and the budget check with `if not rules.within_budget(state.interactions):`. Every reason
     string and the order of checks stay exactly as they are (the loop guard first).
   - `request_of` uses `rules`-free `sanitize` as today (it is also called from outside
     `evaluate`); do not change it in this lane.
   - Delete `_is_own_comment` and `_trusted` from `conversation.py` (no test references them:
     `grep -n "cv._trusted\|_is_own_comment" test/` finds nothing).
4. Nothing else changes: `issue_automation._trusted` and `pr_automation._trusted` keep their
   own rules (they judge issue/PR authors with different inputs); unifying them is not this lane.

## Where to change
- New: `vibey_gh/interaction_policy.py`, `vibey_gh/interfaces/interaction_policy_interface.py`
  (provenance header copied from `vibey_gh/interfaces/text_file_reader_interface.py:1`).
- Edit: `vibey_gh/conversation.py` (`evaluate`, delete the two helpers). Use `edit_file`.
- New test file `src/vibey_tools/gh/test/test_interaction_policy.py`. Do not edit
  `test/test_conversation.py`: every existing test there must pass unchanged — that is the proof
  of "byte-for-byte".

## Acceptance criteria
- [ ] `test/test_conversation.py` and `test/test_gh_cli.py` pass unmodified.
- [ ] `InteractionPolicy.from_config(cfg)` answers the same as the deleted helpers for the loop-guard
      logins of `test_conversation.py:61-70` (`vibey[bot]`, `vibey`, `github-actions[bot]`,
      `claude[bot]`, `app/claude`).
- [ ] `evaluate` accepts an injected `InteractionPolicyInterface` double and uses it (a double
      whose `is_own` is always True makes every comment SKIP with the loop-guard reason).
- [ ] `grep -n "_is_own_comment\|def _trusted" vibey_gh/conversation.py` finds nothing.
- [ ] vibey-gh's suite passes with its 100% branch floor; black, isort, mypy, ruff clean.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_interaction_policy.py`:
- `test_the_automation_never_counts_as_a_stranger_or_a_peer` — `is_own` is True for each
  ignore-actor spelling (`vibey[bot]`, `app/vibey`, `vibey`) and False for `owner`.
- `test_trust_is_the_named_authors_plus_the_owner` — owner and `trusted[bot]`/`app/trusted`
  are trusted; `stranger` and `""` are not; with no owner and no authors nobody is.
- `test_strangers_get_a_response_only_when_opted_in` — `may_respond("stranger")` False by
  default, True with `respond_to_untrusted=True`; a trusted author is always True.
- `test_the_budget_is_strict` — `max_interactions=2`: `within_budget(1)` True, `within_budget(2)` False.
- `test_text_is_bounded_and_flattened_data` — `as_data("a\nb\x00c")` is `"a b c"`;
  `len(as_data("x" * 900)) <= 300`.
- `test_from_config_reads_the_conversation_table` — a `GhConfig(root=tmp_path, owner="o", trusted_authors=("t",), conversation=ConversationConfig(max_interactions=3, respond_to_untrusted=True))`
  produces a policy with those answers.
- `test_evaluate_uses_the_injected_policy` — a small class implementing
  `InteractionPolicyInterface` whose `is_own` returns True: `cv.evaluate(comment, subject, cfg, policy=double).reason == "the automation does not answer its own comments"`.
- `test_the_policy_satisfies_its_interface` — `isinstance(InteractionPolicy.from_config(cfg), InteractionPolicyInterface)`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_interaction_policy.py test/test_conversation.py test/test_gh_cli.py
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Any new surface using the policy (Matrix replies are blocked on #85 open question 3; Moltbook
  on #139's questions). The `@vibey` rename (`roadmap-145-vibey-mention`, which lands first).
- `issue_automation` / `pr_automation` trust rules; `context()`'s briefing text.
- Docs, CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
