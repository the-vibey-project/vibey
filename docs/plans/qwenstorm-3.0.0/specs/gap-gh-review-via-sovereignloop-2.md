## Title
feat(gh)!: the sovereign review and triage go through sovereignloop when a broker is configured, and a direct Ollama call says so on the verdict

## Why
Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:204`): vibey's workers, storms and
command line put work on the loop's queue, and nothing spawns a loop directly. Lanes
`gap-gh-review-transport` and `gap-gh-review-via-sovereignloop-1` gave `local_review` two
transports behind one interface; `review()` and `triage()` still always build the direct one
(`src/vibey_tools/gh/vibey_gh/local_review.py:204`, `:345`).

This lane chooses. When a broker is configured -- `VIBEY_BUS_AMQP_URL`, the setting lane
`rmq-r01-queue-config` declares for vibey (`[bus] amqp_url`) -- the question goes through
sovereignloop. Only when none is configured does it fall back to direct Ollama, and then the
verdict says so, because a direct call is the exception 8.c tolerates, not a silent default
(7.c, `doctrines.md:82`; 10.f, `doctrines.md:419`). The route is a declared key with an
override (12.c, `doctrines.md:455`).

## Required behaviour
1. `PrAutomationFallbackConfig` (`src/vibey_tools/gh/vibey_gh/config.py:480-535`) gains two
   fields after `heartbeat_max_age_minutes` (`:508`):
   - `route: str = "auto"`. In `__post_init__`, inside the `enabled` branch:
     `if self.route not in ("auto", "loop", "direct"): raise ValueError("pr_automation.fallback.route must be auto, loop or direct")`.
   - `loop_command: tuple[str, ...] = DEFAULT_LOOP_COMMAND` (import it from
     `vibey_gh.loop_review_transport`). In `__post_init__`: an empty tuple or a blank item
     raises `ValueError("pr_automation.fallback.loop_command must name a program")`.
   The loader (`config.py:1751-1761`) reads `route=fallback.get("route", "auto")` and
   `loop_command=tuple(fallback.get("loop_command", DEFAULT_LOOP_COMMAND))`.
2. In `local_review.py`, `BROKER_URL_ENV = "VIBEY_BUS_AMQP_URL"` and new
   `class ReviewRouteChooser`:
   - `__init__(self, *, environ: Mapping[str, str] | None = None, direct: Callable[[str], ReviewTransportInterface] | None = None, loop: Callable[[Sequence[str]], ReviewTransportInterface] | None = None) -> None`;
     `None` means `os.environ`, `lambda url: OllamaReviewTransport(url)` and
     `lambda command: LoopReviewTransport(command=command)`. If `fakes-tenant-gh-3` gave
     `review()`/`triage()` an `opener` keyword, the default `direct` factory passes it on.
   - `choose(self, *, route: str, loop_command: Sequence[str], base_url: str) -> tuple[ReviewTransportInterface, str]`
     returns the transport and its label:
     | `route` | broker env set (non-blank) | transport | label |
     |---|---|---|---|
     | `direct` | either | direct | `direct Ollama: route = direct` |
     | `loop` | either | loop | `via sovereignloop` |
     | `auto` | yes | loop | `via sovereignloop` |
     | `auto` | no | direct | `direct Ollama: no broker configured` |
3. `review(argv, *, chooser: ReviewRouteChooserInterface | None = None)` and
   `triage(argv, *, chooser=None)` (`None` means `ReviewRouteChooser()`):
   - choose with `route=defaults.route`, `loop_command=defaults.loop_command`,
     `base_url=args.base_url`;
   - ask with `LocalReviewer(transport).review(diff, model=args.model, max_chars=args.max_chars, timeout=args.timeout)`
     (triage: `.triage(text, ...)`), inside the existing `try`, whose `except` clauses do not
     change: the loop transport's failures are already `OSError`, `TimeoutError`, `KeyError`,
     `TypeError` or `json.JSONDecodeError`. A failed loop call fails the review closed; it is
     never retried against Ollama.
   - after success, print `f"route: {answer.detail}"` to stderr (the job log keeps the seat),
     and label the summary with the route inside the existing bracket:
     review: `f"[{lane} — {args.model} — {label}] {...}"`; triage:
     `f"[LOCAL FALLBACK TRIAGE — {args.model} — {label}] {...}"`. Everything else in both
     summaries, the placeholders and `needs_human = True` stay as they are.
4. `ReviewRouteChooserInterface` (`choose`) is declared in
   `vibey_gh/interfaces/local_review_interface.py` beside `LocalReviewerInterface`.
5. `test/conftest.py`'s `_ACTIONS_ENV` (`:21`) gains `"VIBEY_BUS_AMQP_URL"`, so an operator's
   own broker setting never leaks into the offline suite.

## Where to change
- `src/vibey_tools/gh/vibey_gh/config.py` (edit_file: the dataclass and the loader).
- `src/vibey_tools/gh/vibey_gh/local_review.py`, `vibey_gh/interfaces/local_review_interface.py` (edit_file).
- `src/vibey_tools/gh/test/conftest.py` (one tuple, edit_file).
- New `src/vibey_tools/gh/test/test_review_route.py`, using `ScriptedReviewTransport`
  (`test/fakes.py`) through the chooser's `direct`/`loop` factories, and
  `monkeypatch.setenv`/`delenv` for the broker variable.

## Acceptance criteria
- [ ] With no broker variable and default config, `vibey-gh local-review` posts to Ollama as
      before and its summary starts `[LOCAL FALLBACK — gpt-oss:20b — direct Ollama: no broker configured]`.
- [ ] Every existing test in `test/test_local_review.py` passes unchanged (its prefix
      assertions, `:111-112`, `:374`, `:606-609`, still hold).
- [ ] A bad `route` or an empty `loop_command` in `.vibey-gh.toml` fails config loading with the stated message.
- [ ] No managed workflow template changes; `tools-lint`'s drift check reports no drift.
- [ ] vibey-gh's suite passes at its floor; black, isort, mypy pass; the ratchet is not raised.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_review_route.py`:
- `test_auto_without_a_broker_goes_direct_and_says_so`
- `test_auto_with_a_broker_goes_through_the_loop` -- `VIBEY_BUS_AMQP_URL=amqp://h/`; the loop factory received `("vibey", "loop", "ask")`.
- `test_declared_direct_and_loop_ignore_the_environment` -- parametrized over both routes and both env states.
- `test_review_labels_the_route_on_the_verdict` -- `review(["--diff", p, "--role", "sovereign"], chooser=...)` prints a verdict whose summary starts `[SOVEREIGN LANE — gpt-oss:20b — via sovereignloop]`, and stderr holds `route: scripted`.
- `test_triage_labels_the_route_and_still_needs_a_human`
- `test_a_failed_loop_call_fails_closed_without_trying_ollama` -- the loop fake raises `OSError`; exit 1; the direct factory was never called.
- `test_config_refuses_an_unknown_route_and_an_empty_loop_command`
- `test_config_reads_route_and_loop_command_from_toml` -- a `.vibey-gh.toml` with `[pr_automation.fallback] route = "loop"` and `loop_command = ["vibey", "loop", "ask", "--loop", "sovereignloop"]`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- A `--route` command-line flag (the key and the environment carry the choice).
- The vibey side of `vibey loop ask` (owed; see the report for this lane set).
- `.github/workflows/*` and `vibey_gh/templates/`: the rendered review job passes the runner's
  environment through unchanged, so nothing is re-rendered.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(gh)!: the sovereign review and triage go through sovereignloop when a broker is configured`. Do not push.
BREAKING CHANGE note for the commit body: the local verdict's summary now names its route.

## Lane card
- **Depends on:** `gap-gh-review-via-sovereignloop-1`, `rmq-r01-queue-config` (the
  `VIBEY_BUS_AMQP_URL` setting this lane reads).
- **Standing constraints:** vibey-gh stays dependency-free; fakes are plain classes;
  substitution only at declared seams; never raise the ratchet.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
