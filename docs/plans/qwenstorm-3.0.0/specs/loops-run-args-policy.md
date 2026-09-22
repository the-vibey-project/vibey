## Title
feat(domain): the run-args policy that decides whether a RunRequest is safe to execute

ADR-0046 lane L04c (slug `loops-run-args-policy`).

## Why
- **The law.** *Security impact* (`specs/ADR-two-loops.md:386-392`): "A loop runs only the
  binaries of **its own** adapters. `args[0]` is validated as before. `cwd` must lie under
  `[loop_services] root`." §3's idempotency table (`:190`) reserves "an unsafe request" as one of
  the seat host's own rejections, and §10 (`:304`) places the seat host's rule f ("reject an
  unsafe request") in the seat host, which needs a pure check to run it against. The design
  sheet's decision D14 splits this check out of `domain/run_protocol.py` into its own sibling
  module, `domain/run_args_policy.py`, exactly as it splits the codec into `run_codec.py` (lane
  `loops-run-codec`): a `RunRequest`'s wire shape (what fields exist) is one concern; whether a
  *particular* `RunRequest* is safe to run on *this* loop (what `cwd` and `run_dir` it names) is
  another, and the second one needs the loop's own configured `root`, which the message itself
  must never carry (`RunRequest` has no `root` field, `run_protocol.py`).
- **The gap, at integration `d3b4a388`.** No such policy exists. The superseded R25
  (`specs/rmq-r25-loop-service-adapter.md` behaviour 3, carried into ADR-0046 by
  `issue-audit/updates/372.md`) is about the *caller's* `EngineQueueSaturated`, not the seat
  host's own safety check; this lane is upstream of the seat host (lane `loops-seat-host-core`),
  which calls `LocalRunExecutor.reason_to_reject(request)` (lane `loops-local-run-executor`) --
  that executor is where this policy is actually consulted, on the loop's own `root` and
  `state_dir` (`[loop_services]`, lane `loops-config-loop-services`).
- **9.b** (`doctrines.md:349`): the class gets an interface beside it.

## Required behaviour
1. **`src/vibey/domain/run_args_policy.py`** (new). Module docstring cites ADR-0046's *Security
   impact* section and says the policy is pure: `root` and every path come from the caller, never
   from a clock or the filesystem (whether a path *exists* is the executor's concern, lane
   `loops-local-run-executor`; this module only judges the request's *shape*).
2. **Constants** (`Final`, exact text):
   ```python
   REASON_CWD_NOT_ABSOLUTE = "cwd must be an absolute path"
   REASON_CWD_OUTSIDE_ROOT = "cwd {cwd} is outside the loop root {root}"
   REASON_RUN_DIR_ESCAPES_CWD = "run_dir must not contain '..' or start with '/'"
   REASON_EMPTY_ARGS = "args must not be empty"
   REASON_EMPTY_ARG = "args[{index}] must not be an empty string"
   ```
   (`REASON_CWD_OUTSIDE_ROOT` and `REASON_EMPTY_ARG` are format strings; the policy fills them in.)
3. **`class RunArgsPolicy`** (no state):
   ```python
   class RunArgsPolicy:
       """Whether a RunRequest is safe to run (ADR-0046 *Security impact*): `args[0]` is
       validated by the caller that resolves it to a binary (the executor, never here), but
       every request must still name an absolute `cwd` inside the loop's own root, a `run_dir`
       that cannot leave `cwd`, and at least one non-empty argument."""

       def reason_to_reject(self, request: RunRequest, *, root: str) -> str | None:
           if not request.cwd.startswith("/"):
               return REASON_CWD_NOT_ABSOLUTE
           if not self._within(request.cwd, root):
               return REASON_CWD_OUTSIDE_ROOT.format(cwd=request.cwd, root=root)
           if request.run_dir is not None and not self._safe_relative(request.run_dir):
               return REASON_RUN_DIR_ESCAPES_CWD
           if not request.args:
               return REASON_EMPTY_ARGS
           for index, arg in enumerate(request.args):
               if arg == "":
                   return REASON_EMPTY_ARG.format(index=index)
           return None

       @staticmethod
       def _within(cwd: str, root: str) -> bool:
           if root == "/":
               return True
           normalized_root = root.rstrip("/")
           return cwd == normalized_root or cwd.startswith(normalized_root + "/")

       @staticmethod
       def _safe_relative(run_dir: str) -> bool:
           if run_dir.startswith("/"):
               return False
           parts = run_dir.split("/")
           return ".." not in parts and "" not in parts
   ```
   - `root == "/"` (the `[loop_services] root` default) admits every absolute `cwd`: a bare
     install with no configured root restricts nothing beyond "absolute".
   - `_within` is a path-segment check, not a string prefix: `/work2` is not within `/work`.
   - `_safe_relative` refuses an empty segment (`a//b`, a trailing or leading `/` once split) and
     any `..` segment, so `run_dir` can never be joined onto `cwd` to leave it.
   - The checks run in this order because it is the cheapest-first order the seat host wants to
     report: an absolute-path mistake is worth surfacing before a root mismatch, which is worth
     surfacing before the more expensive question of whether the arguments are sane.
4. **`src/vibey/domain/interfaces/run_args_policy_interface.py`** (new): one `@runtime_checkable`
   Protocol, `RunArgsPolicyInterface`, with `reason_to_reject(self, request: RunRequest, *, root:
   str) -> str | None`. It starts with `from __future__ import annotations` and imports
   `RunRequest` only under `if TYPE_CHECKING:`, following
   `src/vibey/domain/interfaces/ledger_query_interface.py:1-21`.
5. **Shared instance:** `RUN_ARGS_POLICY: Final[RunArgsPolicyInterface] = RunArgsPolicy()`, with a
   docstring: "Stateless, so one instance serves. Annotated with the interface so `mypy --strict`
   checks the class against its seam." (the `LEDGER_RECORDS` pattern,
   `src/vibey/domain/ledger_record.py:157-159`).
6. The module is pure: no I/O, no clock, no `pathlib` (a real filesystem check belongs to the
   executor, not this policy — `pathlib.PurePosixPath` would also work but plain string splitting
   keeps the module free of any temptation to touch a real path). `tests/domain/test_domain_purity.py`
   walks it.

## Where to change
- New: `src/vibey/domain/run_args_policy.py`,
  `src/vibey/domain/interfaces/run_args_policy_interface.py`, `tests/domain/test_run_args_policy.py`.
- Line 1 of each new file is the provenance comment, copied byte for byte from line 1 of
  `src/vibey/domain/engine.py`.
- Imports in `run_args_policy.py`: `Final` from `typing`; `RunRequest` from
  `vibey.domain.run_protocol` (lane `loops-run-protocol-messages`);
  `RunArgsPolicyInterface` from the new interface module.
- If `src/vibey/domain/run_protocol.py` does not exist, stop and report
  `blocked: loops-run-protocol-messages has not landed`.
- No fake is registered: the policy is pure and used directly in tests.

## Acceptance criteria
- [ ] Every branch of `reason_to_reject` has its own test, below.
- [ ] `root == "/"` admits any absolute `cwd`; every other `root` refuses a `cwd` that is not it
      or a path segment beneath it.
- [ ] `run_dir` refuses an absolute path and any `..` segment; a plain relative path is accepted.
- [ ] `tests/domain/test_domain_purity.py` passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_run_args_policy.py` (pure objects only). Build a valid request with a local
factory `_request(**overrides)` returning a `RunRequest` with `run_id=UUID(int=1)`,
`loop_id=LoopId.SOVEREIGNLOOP`, `engine_id="sovereignloop"`, `route_id=None`, `model_pin=None`,
`purpose=RunPurpose.RUN`, `args=("run", "plan.md")`, `cwd="/work/repo"`, `run_dir=None`,
`supersedes=None`, `deadline_seconds=60`, `start_by=datetime(2026, 9, 22, 12, tzinfo=UTC)`,
`capture_output=False`, `requested_at=datetime(2026, 9, 22, 11, 59, tzinfo=UTC)`, `caller="test"`,
overridden with `dataclasses.replace`-style keyword overrides. Use `policy = RunArgsPolicy()`.
- `test_a_valid_request_is_accepted`: `policy.reason_to_reject(_request(), root="/work") is None`.
- `test_a_relative_cwd_is_refused`: `_request(cwd="work/repo")` →
  `"cwd must be an absolute path"`.
- `test_a_cwd_outside_the_root_is_refused`: `_request(cwd="/other/repo")`, `root="/work"` →
  `"cwd /other/repo is outside the loop root /work"`.
- `test_a_cwd_that_merely_shares_a_prefix_is_refused`: `_request(cwd="/work2/repo")`,
  `root="/work"` → refused (a string-prefix check would wrongly accept this).
- `test_the_default_root_admits_any_absolute_cwd`: `_request(cwd="/anything/at/all")`,
  `root="/"` → `None`.
- `test_a_root_with_a_trailing_slash_behaves_like_one_without`: `root="/work/"` accepts
  `cwd="/work/repo"` exactly as `root="/work"` does.
- `test_a_run_dir_that_stays_inside_cwd_is_accepted`: `_request(run_dir=".sovereignloop/runs/r1")`,
  `root="/work"` → `None`.
- `test_an_absolute_run_dir_is_refused`: `_request(run_dir="/etc/passwd")` →
  `"run_dir must not contain '..' or start with '/'"`.
- `test_a_run_dir_that_escapes_cwd_is_refused` (parametrized over `"../../etc"`, `"a/../../b"`,
  `"a//b"`): each refused with the same message.
- `test_empty_args_is_refused`: `_request(args=())` → `"args must not be empty"`.
- `test_an_empty_argument_names_its_index`: `_request(args=("run", "", "plan.md"))` →
  `"args[1] must not be an empty string"`.
- `test_checks_run_in_the_documented_order`: a request that fails both the `cwd`-absolute check
  and the empty-args check (`cwd="relative", args=()`) reports the `cwd` message, not the args one.
- `test_classes_satisfy_their_interfaces`: `isinstance(RunArgsPolicy(), RunArgsPolicyInterface)`
  and `isinstance(RUN_ARGS_POLICY, RunArgsPolicyInterface)`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/run_args_policy.py src/vibey/domain/interfaces/run_args_policy_interface.py tests/domain/test_run_args_policy.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_run_args_policy.py tests/domain/test_run_protocol.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Whether `cwd` or `run_dir` actually exist on disk, and any read of `meta.json` (lane
  `loops-local-run-executor`, and rule d of `loops-seat-host-fence`).
- Validating `args[0]` against the loop's own adapter list (the seat host already knows which
  adapters it may run; this policy only judges shape, never identity).
- The `[loop_services] root` and `state_dir` configuration itself (lane `loops-config-loop-services`).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-run-protocol-messages`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`.
- Every job is idempotent under replay; the ledger is append-only (no updates, no deletes; a correction is a new event that supersedes the prior one).
- `write_file` REPLACES the whole file. Never use it on a file that already exists unless the complete content with the change applied is written back. Every line not meant to change must still be there. For any existing file longer than 100 lines, do not use `write_file` at all.
- Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one occurrence and reports when the text is missing or not unique. Only if `edit_file` cannot express a change, use a checked replacement through the `shell` tool, and the `shell` tool takes an **argv list**, never a shell string: a shell here-document that redirects a block of text into a command never works this way and must never be written. For any one-off script, write it with `write_file` to `.qwenstorm/<name>.py`, then run it as `["python3", ".qwenstorm/<name>.py"]`. To append to an existing file, use `edit_file` with `old_string` equal to the file's exact last few lines. Copy `old_string` exactly, including indentation; if a checked assert fails, read the file again and fix the string; never fall back to rewriting the whole file.
- Add tests by appending to an existing test file (read it, append, write the whole file back with everything before the addition unchanged) or by creating a new test file. Never rewrite an existing test file's prior content.
- Every source file begins with the provenance header line `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`. Keep it on every file touched, and put it on every file created (copy it from a neighbour file in the same package, byte for byte).
- Only edit the files named under "Where to change" and the tests named under "Tests to write first". If another file seems like it must change, say so in the verdict instead of editing it.
- After each change, run the focused tests named in this spec. If a test not meant to be affected fails, undo the change with a targeted replacement and try again rather than pushing forward.
- Before the final verdict, run `git diff --stat` and confirm no file lost lines that were not meant to be removed.
- Tests substitute only at declared seams: constructor injection, keyword injection, or a named fixture. Never `monkeypatch.setattr` on an import, a module attribute or a class attribute; never `mock.patch`; never a bare `MagicMock` or `AsyncMock` standing in for a port. A fake is a plain class with real in-memory behaviour for every method it implements; no method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- Persistence goes only through the ORM seams declared in the `orm-*.md` specs in this same directory. No raw `asyncpg` SQL, no `text()`, no `exec_driver_sql()` and no SQL string literal in a loops lane.
- No failure-text string a lane writes may trail off with an ellipsis character: write every failure message out in full, to its last word.
- Do not edit `CHANGELOG.md`, anything under `docs/`, any ADR, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or a skill tree (the docs wave owns those). Do not push, open a pull request, or change a git remote. Commit locally, with the Title as the Conventional Commit subject.
- Protected tests are never edited, under any circumstance: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
