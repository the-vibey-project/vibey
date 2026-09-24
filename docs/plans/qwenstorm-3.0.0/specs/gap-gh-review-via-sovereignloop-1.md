## Title
feat(gh): a review transport that submits the question to sovereignloop through `vibey loop ask`, bounded and labelled

## Why
Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:204`) puts every sovereign model call
on the loop's queue; 10.e (`doctrines.md:417`) says the family's own path is used "in CI, and
in operations". vibey-gh must stay dependency-free (CLAUDE.md; `dependencies = []`) and can
import neither `vibey` nor `aio-pika`, so it cannot talk to the broker itself. It can run the
family's command line, which ships in the same `vibey` distribution (ADR-0037).

This lane adds that second transport behind `ReviewTransportInterface` (lane
`gap-gh-review-transport`). It defines the process contract vibey-gh relies on: a command
(`vibey loop ask`, the `vibey loop` group of lane `loops-submit-cli`) that takes the three
prompt parts as files, submits one pinned, schema-constrained run to sovereignloop, waits, and
prints the answer with the seat that produced it. The vibey side of that command is owed by
the A4 service-mode composition lane (see the report for this lane set); vibey-gh's side is
exact now and is tested against a scripted runner. Nothing selects this transport until lane
`gap-gh-review-via-sovereignloop-2`.

## Required behaviour
1. New `src/vibey_tools/gh/vibey_gh/loop_review_transport.py` (provenance line 1, copied
   from `vibey_gh/local_review.py:1`) holds:
   - `DEFAULT_LOOP_COMMAND: tuple[str, ...] = ("vibey", "loop", "ask")`, the declared default
     (12.c; lane `-2` makes it a key).
   - `class SubprocessLoopAskRunner` with
     `run(self, argv: Sequence[str], *, timeout: int) -> subprocess.CompletedProcess[str]`:
     `subprocess.run(list(argv), capture_output=True, text=True, timeout=timeout, check=False)  # nosec B603 - argv is a list, never a shell string`.
     `subprocess.TimeoutExpired` is re-raised as
     `TimeoutError(f"{argv[0]} did not answer within {timeout}s")`, because `review()` and
     `triage()` catch `TimeoutError` (`local_review.py:205`, `:346`) and not
     `TimeoutExpired`. Its docstring carries 10.e's written reason for not reusing
     `fakes-tenant-gh-3`'s `CommandRunner`: a review must be bounded end to end by
     `timeout_seconds`, and that runner runs fit's and tidy's commands without a deadline.
   - `class LoopReviewTransport` implementing `ReviewTransportInterface`:
     - `ROUTE = "sovereignloop"`; `route` property returns it.
     - `__init__(self, *, command: Sequence[str] = DEFAULT_LOOP_COMMAND, runner: LoopAskRunnerInterface | None = None, grace_seconds: int = 60) -> None`
       (`None` means `SubprocessLoopAskRunner()`); an empty `command` raises
       `ValueError("the loop command must name a program")`.
     - `ask(self, *, system, user, schema, model, num_ctx, timeout) -> ReviewAnswer`:
       inside `tempfile.TemporaryDirectory(prefix="vibey-gh-ask-")` write `system.txt`,
       `user.txt` (UTF-8) and `schema.json` (`json.dumps(schema)`), then run
       `[*command, "--model", model, "--system-file", <system.txt>, "--user-file", <user.txt>, "--schema-file", <schema.json>, "--num-ctx", str(num_ctx), "--timeout", str(timeout)]`
       with `timeout=timeout + grace_seconds` (the child bounds its own wait by `--timeout`;
       the grace lets it report instead of being killed).
     - A non-zero exit raises `OSError(f"{command[0]} loop ask exited {rc}: {stderr.strip()[:500]}")`.
     - Otherwise stdout is one JSON object with exactly the keys `answer`, `loop_id`,
       `engine_id`, `seat`, `model`, `run_id` (the fields of vibey's `RoutedChatAnswer`, lane
       `gap-design-via-sovereignloop-1`, with `value` named `answer`). A missing key raises
       `KeyError`; an `answer` that is not a JSON object raises
       `TypeError(f"expected a JSON object, got {type(answer).__name__}")`.
     - It returns `ReviewAnswer(answer, "sovereignloop", f"sovereignloop seat {seat} ({model}), run {run_id}")`.
2. New `src/vibey_tools/gh/vibey_gh/interfaces/loop_review_transport_interface.py`
   (provenance line 1) declares `LoopAskRunnerInterface` (the `run` above) and
   `LoopReviewTransportInterface(ReviewTransportInterface, Protocol)` with no new members.
3. `test/fakes.py` gains `class ScriptedLoopAskRunner` (implements `LoopAskRunnerInterface`):
   constructed with a list of `(returncode, stdout, stderr)` triples or exceptions; records
   each `(argv, timeout)` in `calls`, and copies the three files' contents into
   `seen_files` while they exist; raises `LookupError("no scripted loop answer left")` when
   empty. `test/test_port_parity.py` registers it for `LoopAskRunnerInterface` and lists
   `LoopReviewTransportInterface` in `EXEMPT` as a class contract.

## Where to change
- New `vibey_gh/loop_review_transport.py` and
  `vibey_gh/interfaces/loop_review_transport_interface.py` (under `src/vibey_tools/gh/`).
- `src/vibey_tools/gh/test/fakes.py`, `test/test_port_parity.py` (append / edit_file).
- New `src/vibey_tools/gh/test/test_loop_review_transport.py`.

## Acceptance criteria
- [ ] `grep -rnE "^\s*(import|from) vibey(\s|\.|$)|aio_pika" src/vibey_tools/gh/vibey_gh` prints nothing.
- [ ] `grep -n "shell=True" src/vibey_tools/gh/vibey_gh/loop_review_transport.py` prints nothing.
- [ ] vibey-gh's suite passes at its floor; black, isort, mypy pass; the ratchet is not raised.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_loop_review_transport.py`:
- `test_loop_transport_runs_the_declared_argv` -- the runner saw `["vibey", "loop", "ask", "--model", "gpt-oss:20b", "--system-file", ..., "--user-file", ..., "--schema-file", ..., "--num-ctx", "8192", "--timeout", "600"]` and `timeout == 660`.
- `test_the_prompt_parts_travel_as_files` -- `seen_files` holds the system text, the user text and `json.dumps(REVIEW_SCHEMA)`.
- `test_the_answer_names_the_seat` -- stdout `{"answer": {"pass": true}, "loop_id": "sovereignloop", "engine_id": "sovereignloop", "seat": "gpt-oss-20b", "model": "gpt-oss:20b", "run_id": "r1"}` gives `verdict == {"pass": True}`, `route == "sovereignloop"`, `detail == "sovereignloop seat gpt-oss-20b (gpt-oss:20b), run r1"`.
- `test_a_failed_submit_is_an_oserror_with_its_stderr` -- exit 3 with stderr `"no broker"`.
- `test_a_timeout_becomes_timeouterror` -- a `SubprocessLoopAskRunner` given `["python3", "-c", "import time; time.sleep(5)"]` with `timeout=1` raises `TimeoutError` (real subprocess; no network).
- `test_a_malformed_answer_is_refused` -- missing `seat` raises `KeyError`; `"answer": [1]` raises `TypeError`; non-JSON stdout raises `json.JSONDecodeError`.
- `test_an_empty_command_is_refused`.
- `test_transport_satisfies_its_interfaces`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Choosing this transport, the config keys and the labels (`gap-gh-review-via-sovereignloop-2`).
- The vibey command `vibey loop ask` itself (owed on the vibey side; see the report).
- The managed workflow templates: nothing rendered changes, so no drift check moves.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(gh): a review transport that submits to sovereignloop through vibey loop ask`. Do not push.

## Lane card
- **Depends on:** `gap-gh-review-transport`, `loops-submit-cli` (the `vibey loop` command group).
- **Standing constraints:** vibey-gh stays dependency-free and never imports `vibey`; fakes are
  plain classes; substitution only at declared seams; never raise the ratchet.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
