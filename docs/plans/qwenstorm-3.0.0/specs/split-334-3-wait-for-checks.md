<!-- split of #334: child 3 of 3; audit: issue-audit/updates/334.md -->

## Title
feat(gh): the forge adapter waits for a change request's checks

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`)
and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`).
Promotion blocks on the promotion pull request's checks with raw `gh`
(`vibey_gh/promote.py:130-133`: `gh pr checks N --watch --interval 30`), which has no Forgejo or
GitLab counterpart, so those adapters must poll. Sub-doctrine 9.b (`docs/doctrines.md:349`)
requires substitution at a declared seam, so the wait between polls is an injected `sleep`
field and the tests take no wall time. vibey-gh ADR 0001 (`docs/adr/0001-forge-neutral-nouns.md:57-63`):
the verb answers `(value, problem)` and arrives with its first caller (part 2, promotion).

## Required behaviour
Every path in this spec is relative to `src/vibey_tools/gh/` (package `vibey_gh`).

1. `vibey_gh/interfaces/forge_adapter_interface.py` declares, in a new block headed
   `    # --- Change-request checks ---` placed directly above the line `    # --- Mutations ---`
   (so after the `# --- Change-request listings ---` block):
   ```python
       # --- Change-request checks ---

       def wait_for_checks(
           self, number: int, *, interval_seconds: int, timeout_seconds: int
       ) -> tuple[bool, str]:
           """Wait until a change request's checks settle; True when they all passed."""
           ...
   ```
2. `ForgejoForge` and `GitLabForge` each gain, as their **last** dataclass field (after
   `host: str = …`, added by split-332-2):
   ```python
       sleep: Callable[[float], None] = field(default=time.sleep, repr=False, compare=False)
   ```
   with `import time` and `from collections.abc import Callable` added to the module imports.
   Because of `compare=False`, `ForgejoForge(root=r, transport=t, sleep=f) ==
   ForgejoForge(root=r, transport=t)` (so `test/test_platform.py:192-198` keeps passing
   unmodified), and `repr(...)` does not mention `sleep`.
3. Polling rules shared by Forgejo and GitLab:
   - `interval_seconds < 1` → `(False, f"checks cannot be polled every {interval_seconds} seconds")`
     without any request (this keeps `timeout_seconds // interval_seconds` from raising).
   - Otherwise poll `rounds = max(1, timeout_seconds // interval_seconds)` times, calling
     `self.sleep(interval_seconds)` before every round except the first (never after the last).
   - Every round re-reads the change request, because its head can move while it is watched.
   - A transport problem in any round → `(False, problem)` at once.
   - When every round ended undecided →
     `(False, f"checks did not settle within {timeout_seconds} seconds")`.
4. `ForgejoForge.wait_for_checks` (default adapter, implement and test it first):
   ```python
       def wait_for_checks(
           self, number: int, *, interval_seconds: int, timeout_seconds: int
       ) -> tuple[bool, str]:
           if interval_seconds < 1:
               return False, f"checks cannot be polled every {interval_seconds} seconds"
           rounds = max(1, timeout_seconds // interval_seconds)
           for round_number in range(rounds):
               if round_number:
                   self.sleep(interval_seconds)
               pull, problem = self.transport.survey(
                   [f"repos/{self._repository()}/pulls/{number}"], cwd=self.root
               )
               if problem:
                   return False, problem
               head = pull.get("head") if isinstance(pull, dict) else None
               sha = head.get("sha") if isinstance(head, dict) else None
               if not isinstance(sha, str) or not sha:
                   return False, f"Forgejo did not answer the head of pull request {number}"
               status, problem = self.transport.survey(
                   [f"repos/{self._repository()}/commits/{sha}/status"], cwd=self.root
               )
               if problem:
                   return False, problem
               combined: dict[str, Any] = status if isinstance(status, dict) else {}
               state = combined.get("state")
               if state == "success":
                   return True, ""
               if state in {"failure", "error"}:
                   return False, f"checks on {sha[:12]} ended {state}"
               if combined.get("total_count") == 0:
                   return False, "no checks are reported on the change request's head"
           return False, f"checks did not settle within {timeout_seconds} seconds"
   ```
   Any other state (`pending`, `warning`, missing) waits for the next round.
5. `GitLabForge.wait_for_checks`:
   ```python
       def wait_for_checks(
           self, number: int, *, interval_seconds: int, timeout_seconds: int
       ) -> tuple[bool, str]:
           if interval_seconds < 1:
               return False, f"checks cannot be polled every {interval_seconds} seconds"
           rounds = max(1, timeout_seconds // interval_seconds)
           for round_number in range(rounds):
               if round_number:
                   self.sleep(interval_seconds)
               request, problem = self.transport.survey(
                   [f"projects/{self._project()}/merge_requests/{number}"], cwd=self.root
               )
               if problem:
                   return False, problem
               pipeline = request.get("head_pipeline") if isinstance(request, dict) else None
               if not isinstance(pipeline, dict):
                   return False, "no pipeline ran on the merge request's head"
               status = pipeline.get("status")
               if status == "success":
                   return True, ""
               if status in {"failed", "canceled", "skipped"}:
                   return False, f"the head pipeline ended {status}"
           return False, f"checks did not settle within {timeout_seconds} seconds"
   ```
   Any other status (`created`, `pending`, `running`, …) waits for the next round.
6. `GitHubForge.wait_for_checks`, today's `promote.py:130-133` argv. `timeout_seconds` is not
   passed, because `gh pr checks` has no timeout flag and none is set today; say so in a comment.
   GitHub does not apply the interval refusal in 3: `gh` does its own watching.
   ```python
       def wait_for_checks(
           self, number: int, *, interval_seconds: int, timeout_seconds: int
       ) -> tuple[bool, str]:
           # `gh pr checks --watch` has no timeout flag, and promotion never set one.
           run, problem = self._run(
               self._scoped(
                   ["pr", "checks", str(number)],
                   ["--watch", "--interval", str(interval_seconds)],
               )
           )
           if run is None:
               return False, problem
           if run.returncode == 0:
               return True, ""
           return False, self._failed(run, "gh pr checks", with_stdout=True)
   ```
7. No verb raises. No consumer changes: `promote.py` moves in part 2.

## Where to change
The verb is declared on the protocol all three adapters subclass, so all three implement it in
this lane (mypy refuses an adapter that leaves a declared verb unimplemented).
- `vibey_gh/interfaces/forge_adapter_interface.py`: behaviour 1, one `edit_file` whose
  `old_string` is `    # --- Mutations ---` (find it with `grep -n`) and whose `new_string` is the
  new block, a blank line and that line.
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`: the `sleep` field with one `edit_file`
  anchored on the unique `host` field line (`    host: str = "forgejo.local"` /
  `    host: str = "gitlab.com"`; confirm with `grep -n "host: str" <file>`), the two imports, and
  the method appended to the end of the file.
- `vibey_gh/forge_github.py`: the method appended to the end of the file.
- Appending: each adapter class is its module's last statement, so append with `edit_file` (the lane's `shell` tool takes an argv list, so a shell heredoc cannot run): `old_string` is the file's last three lines copied exactly from `read_file`, and `new_string` is those same lines followed by the new code; (four-space indentation, eight inside a method, starting with one
  blank line) appends into the class. Then run
  `python -m black --line-length 100 vibey_gh/forge_forgejo.py vibey_gh/forge_gitlab.py vibey_gh/forge_github.py vibey_gh/interfaces/forge_adapter_interface.py test/test_forge_wait_for_checks.py`
  and `isort` on the same files once. Read only slices (`sed -n 'a,bp'`, `tail -n 60`); never
  rewrite a module; never `write_file` an existing file.
- `test/test_forge_wait_for_checks.py` (new), starting with the provenance header line copied
  from line 1 of `vibey_gh/forge.py` and a one-line docstring.

## Acceptance criteria
- [ ] `python -m pytest -q --no-cov test/test_forge_wait_for_checks.py test/test_platform.py test/test_forge_adapters.py` passes.
- [ ] `test_github_waits_with_pr_checks_watch` pins `pr checks 5 --watch --interval 30` unbound and
      `pr checks 5 --repo o/r --watch --interval 30` bound, each with `cwd == str(tmp_path.resolve())`.
- [ ] `test_forgejo_and_gitlab_compare_equal_whatever_they_sleep_with` passes.
- [ ] Every polling test injects `sleep=calls.append` and asserts the recorded sleeps; the file
      runs in well under a second (`python -m pytest -q --no-cov --durations=3 test/test_forge_wait_for_checks.py`
      shows no test at or above 1 s).
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`.
- [ ] black, isort, mypy, `ruff check` and `ruff format --check` are clean (block below).
- [ ] `git diff --stat` lists only the five files named under "Where to change".

## Tests to write first (TDD)
Substitute only at declared seams: the `sleep` field, the transport, and the conftest `fake_gh`.
Never `monkeypatch.setattr` an import or a module/class attribute (in particular never patch
`time.sleep`), never `mock.patch`, `MagicMock` or `AsyncMock`.

`RoutedTransport` answers a key the same way every time, and polling needs a key that answers
differently on each call, so this test file defines its own in-memory double (a test double
needs no interface):
```python
class SequenceTransport:
    """Answers each route with its scripted answers in order, repeating the last one."""

    executable = "sequence"

    def __init__(self, routes: dict[str, list[tuple[Any, str]]]) -> None:
        self.routes = {key: list(answers) for key, answers in routes.items()}
        self.calls: list[tuple[str, ...]] = []

    def survey(self, args, *, cwd=None, stdin=None):
        del cwd, stdin
        self.calls.append(tuple(args))
        key = args[0] if len(args) == 1 else f"{args[0]} {args[1]}"
        answers = self.routes.get(key)
        if not answers:
            return [], f"no route for {key}"
        return answers.pop(0) if len(answers) > 1 else answers[0]
```
Build `ForgejoForge(root=tmp_path, repository="o/r", transport=transport, sleep=sleeps.append)`
and `GitLabForge(root=tmp_path, repository="o/r", transport=transport, sleep=sleeps.append)` with
`sleeps: list[float] = []`. Use `PULL = "repos/o/r/pulls/5"`, `SHA = "abcdef0123456789"`,
`STATUS = f"repos/o/r/commits/{SHA}/status"`, `MR = "projects/o%2Fr/merge_requests/5"`.

For GitHub use the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real `gh` put first
on `PATH`; `fake_gh.script({"<argv joined by single spaces>": {"out": ..., "err": ..., "code":
...}})` replaces every answer; `fake_gh.invocations()` lists `{"argv": [...], "cwd": ..., "stdin":
None}` per call; `fake_gh.forget()` clears the records.

`test/test_forge_wait_for_checks.py`:
- `test_forgejo_wait_polls_the_combined_status_until_it_settles(tmp_path)`:
  - routes `{PULL: [({"head": {"sha": SHA}}, "")], STATUS: [({"state": "pending", "total_count":
    2}, ""), ({"state": "success", "total_count": 2}, "")]}`,
    `wait_for_checks(5, interval_seconds=30, timeout_seconds=90)` → `(True, "")`, `sleeps == [30]`,
    `transport.calls == [(PULL,), (STATUS,), (PULL,), (STATUS,)]`.
  - status `{"state": "failure", "total_count": 1}` → `(False, "checks on abcdef012345 ended
    failure")`, `sleeps == []`; `"error"` → `"checks on abcdef012345 ended error"`.
  - status `{"state": "", "total_count": 0}` →
    `(False, "no checks are reported on the change request's head")`.
- `test_forgejo_wait_times_out_without_sleeping_after_the_last_round(tmp_path)`: status always
  `{"state": "pending", "total_count": 1}`; `interval_seconds=10, timeout_seconds=30` →
  `(False, "checks did not settle within 30 seconds")`, `sleeps == [10, 10]`, six calls.
  `interval_seconds=30, timeout_seconds=10` → one round, `sleeps == []`,
  `"checks did not settle within 10 seconds"`. A status answered as a list (`([], "")`) with
  `interval_seconds=10, timeout_seconds=10` also ends with the timeout sentence.
- `test_forgejo_wait_reports_what_it_could_not_read(tmp_path)`: no routes →
  `(False, "no route for repos/o/r/pulls/5")`; only the pull routed →
  `(False, f"no route for {STATUS}")`; the pull answered `({}, "")` →
  `(False, "Forgejo did not answer the head of pull request 5")`;
  `interval_seconds=0` → `(False, "checks cannot be polled every 0 seconds")` with
  `transport.calls == []`.
- `test_gitlab_wait_reads_the_head_pipeline(tmp_path)`:
  - `{MR: [({"head_pipeline": {"status": "running"}}, ""), ({"head_pipeline": {"status":
    "success"}}, "")]}`, interval 30, timeout 60 → `(True, "")`, `sleeps == [30]`.
  - parametrise or loop over `"failed"`, `"canceled"`, `"skipped"` →
    `(False, f"the head pipeline ended {status}")`.
  - `{"head_pipeline": None}` and an answer `([], "")` each →
    `(False, "no pipeline ran on the merge request's head")`.
  - always `"pending"`, interval 10, timeout 20 → `(False, "checks did not settle within 20
    seconds")`, `sleeps == [10]`.
  - no routes → `(False, "no route for projects/o%2Fr/merge_requests/5")`;
    `interval_seconds=-5` → `(False, "checks cannot be polled every -5 seconds")`, no call.
- `test_github_waits_with_pr_checks_watch(fake_gh, tmp_path)`: unbound argv
  `["pr", "checks", "5", "--watch", "--interval", "30"]` code 0 → `(True, "")`, one invocation
  with that argv and `cwd == str(tmp_path.resolve())`; bound
  `GitHubForge(root=tmp_path, repository="o/r")` runs
  `["pr", "checks", "5", "--repo", "o/r", "--watch", "--interval", "30"]`; code 1 with out
  `"1 failing check"` and no err → `(False, "1 failing check")`; code 8 with no output →
  ``(False, "`gh pr checks` exited 8")``;
  `GitHubForge(root=tmp_path, transport=GhTransport(executable="gh-not-installed"))` →
  ``(False, "the GitHub CLI (`gh-not-installed`) is not installed")``. Always pass
  `timeout_seconds=600`; it never appears in the argv.
- `test_forgejo_and_gitlab_compare_equal_whatever_they_sleep_with(tmp_path)`:
  `ForgejoForge(root=tmp_path, sleep=[].append) == ForgejoForge(root=tmp_path)`, the same for
  `GitLabForge`, `"sleep" not in repr(ForgejoForge(root=tmp_path))` and not in the GitLab repr,
  and `ForgejoForge(root=tmp_path).sleep is time.sleep`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_wait_for_checks.py test/test_platform.py test/test_forge_adapters.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --check --line-length 100 vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the five files named under "Where to change"
```

## Out of scope
- The listings (split-334-1, split-334-2, already merged) and the change-request writes
  (split-335-*).
- `promote.py` and every other consumer module (parts 1-6 of the wave). Wiring a configured
  timeout for promotion belongs to part 2.
- `vibey_gh/forge_selector.py`: the selector keeps building adapters with the default `sleep`.
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_platform.py`, `test/test_forge_github.py`
  (never edit them).
- `.vibey-gh.toml` and its `[platform] kind = "github"` declaration: never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  (this spec's title) when done.

## Conventions this lane relies on (everything needed is here)
**C1, the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when
the forge answered; otherwise `value` is `False` here and `problem` is one sentence. No verb
raises for a failed call, a missing client, a non-2xx status or unreadable output (vibey-gh ADR
0001). Forgejo is the default adapter (8.b): implement and test it first.

**C2, GitHub argv fidelity.** The GitHub argv is today's call site's, byte for byte. `[scope]` is
`["--repo", self.repository]` when bound and nothing otherwise; it goes right after the
subcommand's positional argument (`pr checks 5 [scope] --watch …`). Every call runs with
`cwd=self.root`.

**Helpers already on the branch (do not re-add them):**
- `GitHubForge._scoped(self, head: list[str], tail: list[str]) -> list[str]` =
  `head + (["--repo", self.repository] if self.repository else []) + tail`.
- `GitHubForge._run(self, args: Sequence[str], *, stdin: str | None = None) ->
  tuple[subprocess.CompletedProcess[str] | None, str]`: the finished process and `""`, or `None`
  and ``"the GitHub CLI (`<executable>`) is not installed"``.
- `GitHubForge._failed(run, label: str, *, with_stdout: bool = False) -> str` (static):
  `(run.stderr or (run.stdout if with_stdout else "") or "").strip()`, or
  ``f"`{label}` exited {run.returncode}"`` when that is empty.
- `ForgejoForge._repository()` = `quote(self.repository, safe="/")`;
  `GitLabForge._project()` = `quote(self.repository, safe="")`.
- `ForgejoForge` / `GitLabForge` are frozen dataclasses whose fields are `root`, `repository`,
  `transport` and, last, `host` (split-332-2); `for_repository` uses `dataclasses.replace`, so it
  keeps `sleep`. `field` is already imported from `dataclasses` in both modules.
- Transports answer `survey([path])` as a GET: `(dict_or_list, "")`, or `([], problem)`.

**C7, tests.** 100% line and branch coverage of all of `vibey_gh`; focused runs need `--no-cov`.

**C8, the formatter trap.** black + isort and root `ruff format` must both be clean: lines at or
under 100 columns (95 for nested calls); bind long expected values to a local before the
`assert`; no implicit string concatenation; multi-line calls one argument per line with a
trailing comma; no backslash continuations. If they fight, restructure the line.

**C9, the big files.** Append with a heredoc, run black once, read only slices, never rewrite a
module.

**Depends on:** split-334-2-open-branches
- split-334-2-open-branches: the adapter and protocol files at their post-listing state (the new block goes after its `# --- Change-request listings ---` block). #335's lanes depend on this lane.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
