## Title
feat(gh)!: `@vibey` is the default mention, and `@vibey-gh` stays an accepted alias with a deprecation notice

## Why
Issue #145 (rewrite: `issue-audit/updates/145.md`, "Proposed child issues" 1) records the
operator's ask of 2026-09-15: "fixing the at vibey-gh command to use at vibey instead". The
rename has not happened:

- `src/vibey_tools/gh/vibey_gh/config.py:756` `trigger: str = "@vibey-gh"` and `:1809`
  `trigger=talking.get("trigger", "@vibey-gh")`.
- `src/vibey_tools/gh/.vibey-gh.toml:65-67` sets `[conversation] trigger = "@vibey-gh"`
  explicitly, and its rendered workflow `src/vibey_tools/gh/.github/workflows/conversation.yml:45`
  filters on `contains(github.event.comment.body, '@vibey-gh')`.

`mentions()` (`vibey_gh/conversation.py:98-108`) matches on a word boundary
(`(?<![\w-])…(?![\w-])`), so a trigger of `@vibey` does **not** match `@vibey-gh`. Changing the
default alone would silently stop answering everyone who still writes `@vibey-gh`. So the old
spelling stays an accepted alias for one release, and a mention through it carries a notice.
Machine speech stays labelled and comment text stays data (Constitution III.4, SD-01 §4);
the loop guard is untouched. 12.c: the aliases are declared configuration.

## Required behaviour
1. `ConversationConfig` (`config.py:745-775`):
   - `trigger: str = "@vibey"`.
   - New field, directly after `trigger`: `aliases: tuple[str, ...] = ("@vibey-gh",)`.
   - `__post_init__` adds, after the existing trigger check:
     - `_unique_nonempty("conversation.aliases", self.aliases)` (an empty tuple is allowed);
     - any alias containing whitespace raises
       `ValueError("conversation.aliases entries must contain no whitespace")`;
     - an alias equal to `trigger` raises
       `ValueError("conversation.aliases must not repeat conversation.trigger")`.
   - New property `triggers(self) -> tuple[str, ...]` returning `(self.trigger, *self.aliases)`.
2. The loader (`config.py:1807-1815`): `trigger=talking.get("trigger", "@vibey")` and
   `aliases=tuple(talking.get("aliases", ConversationConfig().aliases))`.
3. `conversation.py`:
   - `mentions(body: str, trigger: str | tuple[str, ...]) -> bool`: a `str` is treated as a
     one-element tuple; returns True when **any** non-empty trigger matches on the existing
     word boundary. `mentions(x, "")` and `mentions(x, ())` stay False.
   - `request_of(body: str, trigger: str | tuple[str, ...]) -> str`: the text after the
     **earliest** match among the triggers, bounded exactly as today (`sanitize(..., limit=300)`).
   - New module constant `DEPRECATED_MENTION = "{alias} is deprecated and will stop working in a
     future release; mention {trigger} instead"` (a format string).
   - `Evaluation` gains `notice: str = ""` as its **last** field (so every existing keyword
     construction is unchanged).
   - `evaluate(...)`:
     - the mention check becomes `mentions(body, policy.triggers)`; its skip reason stays
       `f"the comment does not mention {policy.trigger}"`;
     - `request_of(body, policy.triggers)` feeds `request=`;
     - when the comment mentions no entry of `(policy.trigger,)` but does mention an alias, the
       returned `Evaluation` (ANSWER, ACT or BLOCKED) has
       `notice=DEPRECATED_MENTION.format(alias=<first matching alias>, trigger=policy.trigger)`.
       SKIP results never carry a notice.
   - The loop guard stays the first check, and `_is_own_comment` is unchanged.
   - Update the `mentions` docstring's example to `@vibey` / `@vibey-bot`.
4. `src/vibey_tools/gh/.vibey-gh.toml:67`: `trigger = "@vibey"`, and add
   `aliases = ["@vibey-gh"]` on the next line.
5. The workflow's cheap pre-filter. The template line is
   `vibey_gh/templates/workflows/conversation.yml:45`
   `contains(github.event.comment.body, '__VIBEY_GH_CONVERSATION_TRIGGER__'))`, rendered by
   `install.py:287` `wanted = wanted.replace("__VIBEY_GH_CONVERSATION_TRIGGER__", talk.trigger)`.
   `contains` is a substring test, so `@vibey` already admits `@vibey-gh`, and `evaluate`
   then applies the word boundary. Keep that output byte-for-byte whenever every alias
   contains the trigger. Only when some alias does not
   (`any(talk.trigger not in alias for alias in talk.aliases)`), render the placeholder's
   whole `contains(...)` expression as an `||` of one term per trigger:
   - change the template line to `__VIBEY_GH_CONVERSATION_MENTION_FILTER__)` (keeping the
     closing parenthesis that ends the `(github.event_name == … ||` group), and
   - in `install.py`, replace `:287` with a render of that placeholder:
     `contains(github.event.comment.body, '<trigger>')` for the default case, or
     `" || ".join(f"contains(github.event.comment.body, '{t}')" for t in talk.triggers)`
     otherwise.
   Every existing rendered output stays byte-identical (the default case renders the same text).
6. The tenant's rendered copy `src/vibey_tools/gh/.github/workflows/conversation.yml:45`: edit
   `'@vibey-gh'` to `'@vibey'` by hand (one line), then prove no drift with the tenant check of
   *Checks*. If that check reports any other drift, stop and report it; do not re-render the set.

## Where to change
- `src/vibey_tools/gh/vibey_gh/config.py` (`ConversationConfig`, the loader at `:1807-1815`).
- `src/vibey_tools/gh/vibey_gh/conversation.py` (`mentions`, `request_of`, `Evaluation`,
  `evaluate`, the constant).
- `src/vibey_tools/gh/vibey_gh/install.py` (`:287`, Required behaviour 5) and
  `src/vibey_tools/gh/vibey_gh/templates/workflows/conversation.yml:45`.
- `src/vibey_tools/gh/.vibey-gh.toml:67` and the tenant's rendered
  `src/vibey_tools/gh/.github/workflows/conversation.yml:45` (one line each).
- `src/vibey_tools/gh/test/test_conversation.py`: append tests. Existing tests stay unchanged:
  their bodies say `@vibey-gh`, which now matches through the default alias, so
  `evaluate` still answers them (they gain only a `notice`, which none of them asserts on).
- Use `edit_file`; every one of these files is long.

## Acceptance criteria
- [ ] `ConversationConfig().trigger == "@vibey"` and `ConversationConfig().aliases == ("@vibey-gh",)`.
- [ ] `mentions("hey @vibey look", ("@vibey", "@vibey-gh"))` and
      `mentions("hey @vibey-gh look", ("@vibey", "@vibey-gh"))` are True;
      `mentions("@vibey-gh-bot please", ("@vibey", "@vibey-gh"))` and
      `mentions("@vibey-bot please", ("@vibey", "@vibey-gh"))` are False.
- [ ] A trusted `@vibey-gh` mention evaluates to ANSWER with the deprecation `notice`; a
      trusted `@vibey` mention evaluates to ANSWER with `notice == ""`.
- [ ] The loop guard still wins: a `vibey[bot]` comment saying `@vibey` is SKIP.
- [ ] Invalid aliases (empty, whitespace, duplicate, equal to the trigger) raise the named errors.
- [ ] The tenant's `.vibey-gh.toml` loads with `trigger == "@vibey"`, and the tenant's managed
      workflow set has no drift.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% branch floor
      (`pyproject.toml:67-70`).

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_conversation.py`:
- `test_the_default_mention_is_vibey_with_the_old_name_as_an_alias` — the two defaults above.
- `test_a_mention_of_either_trigger_matches_on_a_word_boundary` — the four `mentions` cases
  above, plus `mentions("(@vibey)", ("@vibey",))` True and `mentions("a@vibeyx.com", ("@vibey",))` False.
- `test_the_request_follows_the_earliest_trigger` —
  `request_of("@vibey-gh fix it", ("@vibey", "@vibey-gh")) == "fix it"` and
  `request_of("see @vibey do x", ("@vibey", "@vibey-gh")) == "do x"`.
- `test_an_alias_mention_is_answered_with_a_deprecation_notice` — `evaluate(comment(body="@vibey-gh explain"), subject(), cfg(tmp_path))`
  gives `state == cv.ANSWER` and `"@vibey-gh is deprecated" in decision.notice`.
- `test_a_vibey_mention_carries_no_notice` — `body="@vibey explain"` gives ANSWER and `notice == ""`.
- `test_the_loop_guard_runs_before_the_new_trigger` — author `vibey[bot]`, body `@vibey again` → SKIP.
- `test_invalid_aliases_are_rejected` — parametrized over `{"aliases": ("",)}`,
  `{"aliases": ("@a b",)}`, `{"aliases": ("@x", "@x")}`, `{"trigger": "@x", "aliases": ("@x",)}`
  with the three messages of Required behaviour 1.
- `test_the_loader_reads_trigger_and_aliases` — write a `.vibey-gh.toml` under `tmp_path` with
  `[conversation]\ntrigger = "@bot"\naliases = ["@old-bot"]\n`, load it through the same loader
  `test_platform.py:39` uses (`load_config` on a temporary root; copy that helper), and assert
  both values.
- `test_the_workflow_filter_names_every_trigger_when_an_alias_is_not_a_superstring` — with
  `from vibey_gh.install import WORKFLOWS, render_workflow` (as `test/test_templates.py:33-43`
  imports them), render `WORKFLOWS / "conversation.yml"` for
  `GhConfig(root=tmp_path, conversation=ConversationConfig(trigger="@bot", aliases=("@helper",)))`
  and assert both `contains(github.event.comment.body, '@bot')` and
  `contains(github.event.comment.body, '@helper')` are present; render for
  `GhConfig(root=tmp_path)` and assert `contains(github.event.comment.body, '@vibey')` appears
  exactly once and `'@vibey-gh'` does not appear in that line.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_conversation.py test/test_templates.py test/test_gh_cli.py
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -c "from vibey_gh.config import load_config; from vibey_gh.install import installed; ok, problems = installed(load_config(), local=False); raise SystemExit('managed automation drift: ' + '; '.join(problems) if not ok else 0)"
    python -c "from vibey_gh.config import load_config; from vibey_gh.install import installed; ok, problems = installed(load_config(), local=False); raise SystemExit('root automation drift: ' + '; '.join(problems) if not ok else 0)"
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- `docs/configuration.md:199` and every other doc (docs wave), CHANGELOG.
- The root `.vibey-gh.toml` (it sets no trigger; the default applies) and installing
  `conversation.yml` in this repository (#145 child 3, blocked on the `vibey` identity).
- Removing the alias (a later release). Registering a GitHub App or Forgejo user (operator action).
- The interaction-policy extraction (`roadmap-85-interaction-policy`, which follows this lane).
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
