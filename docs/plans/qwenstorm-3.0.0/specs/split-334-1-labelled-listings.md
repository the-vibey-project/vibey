<!-- split of #334: child 1 of 3; audit: issue-audit/updates/334.md -->

## Title
feat(gh): the forge adapter lists open change requests by base, head pair and label

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`,
`src/vibey_tools/gh/vibey_gh/config.py:288`), and every forge call must go through
`ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Three modules list open pull requests
through raw `gh`, each with its own argv: `vibey_gh/merge_train.py:319-330`
(`pr list --base <integration> --state open --json number --jq sort_by(.number)`),
`vibey_gh/promote.py:85-99` (`pr list --base <release> --head <integration> --state open --json
number --jq '.[0].number // ""'`) and `vibey_gh/pr_automation.py:584-595`
(`pr list --repo R --state open --label <exhausted> --json number`). vibey-gh ADR 0001
(`docs/adr/0001-forge-neutral-nouns.md:57-63`) has a verb arrive with its first caller and answer
`(value, problem)`. This lane adds the three number-returning listings on all three adapters so
parts 1, 2 and 4 of the wave can move off `gh`.

## Required behaviour
Every path in this spec is relative to `src/vibey_tools/gh/` (package `vibey_gh`).

1. `vibey_gh/interfaces/forge_adapter_interface.py` declares, in a new block headed
   `    # --- Change-request listings ---` placed directly above the line `    # --- Mutations ---`,
   exactly these three methods, each with the one-line docstring shown and a `...` body:
   ```python
       # --- Change-request listings ---

       def open_change_request_numbers(self, *, base: str) -> tuple[tuple[int, ...], str]:
           """The numbers of the open change requests into `base`, ascending, and a problem."""
           ...

       def open_change_request_between(self, *, base: str, head: str) -> tuple[int | None, str]:
           """The open change request from `head` into `base`, not from a fork, and a problem."""
           ...

       def labelled_open_change_request_numbers(
           self, *, label: str
       ) -> tuple[tuple[int, ...], str]:
           """The numbers of the open change requests that carry `label`, and a problem."""
           ...
   ```
2. `ForgejoForge` (`vibey_gh/forge_forgejo.py`, Forgejo is the default adapter: implement and test
   it first). `{R}` is `self._repository()` (= `quote(self.repository, safe="/")`). All three
   verbs read one paged walk: `pulls, problem = self._pages(f"repos/{self._repository()}/pulls?state=open")`.
   A `problem` answers the empty value plus that problem. A pull only counts when its
   `"number"` is an `int`; read nested objects with `(pull.get("base") or {})` and
   `(pull.get("head") or {})` so a missing object never raises.
   - `open_change_request_numbers(base=B)`: pulls whose `base.ref == B`, answered as
     `tuple(sorted(numbers))`, problem `""`.
   - `open_change_request_between(base=B, head=H)`: pulls with `base.ref == B`, `head.ref == H` and
     `head.repo_id == base.repo_id` (the same repository, so a fork's branch of the same name is
     excluded). Answer `(min(numbers), "")`, or `(None, "")` when none match.
   - `labelled_open_change_request_numbers(label=L)`: pulls whose `labels` list holds a dict
     with `name == L`, answered as `tuple(sorted(numbers))`.
   The code to append (the three verbs share one private walk):
   ```python
       def _open_pulls(self) -> tuple[list[dict[str, Any]], str]:
           pulls, problem = self._pages(f"repos/{self._repository()}/pulls?state=open")
           if problem:
               return [], problem
           return [pull for pull in pulls if isinstance(pull.get("number"), int)], ""

       def open_change_request_numbers(self, *, base: str) -> tuple[tuple[int, ...], str]:
           pulls, problem = self._open_pulls()
           if problem:
               return (), problem
           numbers = [p["number"] for p in pulls if (p.get("base") or {}).get("ref") == base]
           return tuple(sorted(numbers)), ""

       def open_change_request_between(
           self, *, base: str, head: str
       ) -> tuple[int | None, str]:
           pulls, problem = self._open_pulls()
           if problem:
               return None, problem
           numbers: list[int] = []
           for pull in pulls:
               into = pull.get("base") or {}
               source = pull.get("head") or {}
               if into.get("ref") != base or source.get("ref") != head:
                   continue
               if source.get("repo_id") == into.get("repo_id"):
                   numbers.append(pull["number"])
           return (min(numbers), "") if numbers else (None, "")

       def labelled_open_change_request_numbers(
           self, *, label: str
       ) -> tuple[tuple[int, ...], str]:
           pulls, problem = self._open_pulls()
           if problem:
               return (), problem
           numbers = [
               pull["number"]
               for pull in pulls
               if any(
                   isinstance(tag, dict) and tag.get("name") == label
                   for tag in pull.get("labels") or []
               )
           ]
           return tuple(sorted(numbers)), ""
   ```
3. `GitLabForge` (`vibey_gh/forge_gitlab.py`). `{P}` is `self._project()` (=
   `quote(self.repository, safe="")`); every query value is quoted with `quote(value, safe="")`
   (`quote` is already imported there). A merge request only counts when its `"iid"` is an `int`.
   - `open_change_request_numbers(base=B)`:
     `self._pages(f"projects/{P}/merge_requests?state=opened&target_branch={quote(B, safe='')}")`,
     answer the sorted `iid`s.
   - `open_change_request_between(base=B, head=H)`:
     `self._pages(f"projects/{P}/merge_requests?state=opened&target_branch={quote(B, safe='')}&source_branch={quote(H, safe='')}")`,
     keep the rows with `source_project_id == target_project_id`, answer `(min(iids), "")` or
     `(None, "")`.
   - `labelled_open_change_request_numbers(label=L)`:
     `self._pages(f"projects/{P}/merge_requests?state=opened&labels={quote(L, safe='')}")`,
     answer the sorted `iid`s.
   - A `_pages` problem answers the empty value plus that problem.
   The code to append:
   ```python
       def open_change_request_numbers(self, *, base: str) -> tuple[tuple[int, ...], str]:
           target = quote(base, safe="")
           path = f"projects/{self._project()}/merge_requests?state=opened&target_branch={target}"
           rows, problem = self._pages(path)
           if problem:
               return (), problem
           return tuple(sorted(row["iid"] for row in rows if isinstance(row.get("iid"), int))), ""

       def open_change_request_between(
           self, *, base: str, head: str
       ) -> tuple[int | None, str]:
           target, source = quote(base, safe=""), quote(head, safe="")
           query = f"state=opened&target_branch={target}&source_branch={source}"
           rows, problem = self._pages(f"projects/{self._project()}/merge_requests?{query}")
           if problem:
               return None, problem
           iids = [
               row["iid"]
               for row in rows
               if isinstance(row.get("iid"), int)
               and row.get("source_project_id") == row.get("target_project_id")
           ]
           return (min(iids), "") if iids else (None, "")

       def labelled_open_change_request_numbers(
           self, *, label: str
       ) -> tuple[tuple[int, ...], str]:
           wanted = quote(label, safe="")
           path = f"projects/{self._project()}/merge_requests?state=opened&labels={wanted}"
           rows, problem = self._pages(path)
           if problem:
               return (), problem
           return tuple(sorted(row["iid"] for row in rows if isinstance(row.get("iid"), int))), ""
   ```
4. `GitHubForge` (`vibey_gh/forge_github.py`). Argv is byte-for-byte today's; `self._scoped(head, tail)`
   inserts `--repo <name>` right after `pr list` only when the adapter is bound.
   - `open_change_request_numbers(base=B)`:
     `value, problem = self._read(self._scoped(["pr", "list"], ["--base", B, "--state", "open", "--json", "number", "--jq", "sort_by(.number)"]))`,
     then `return self._listed_numbers(value, problem)`.
   - `labelled_open_change_request_numbers(label=L)`:
     `value, problem = self._read(self._scoped(["pr", "list"], ["--state", "open", "--label", L, "--json", "number"]))`,
     then `return self._listed_numbers(value, problem)`.
   - New private static helper, appended with the verbs:
     ```python
         @staticmethod
         def _listed_numbers(value: Any, problem: str) -> tuple[tuple[int, ...], str]:
             if problem:
                 return (), problem
             if value is None:
                 return (), ""
             if not isinstance(value, list):
                 return (), "`gh pr list` returned JSON that is not a list"
             numbers = tuple(
                 item["number"]
                 for item in value
                 if isinstance(item, dict) and isinstance(item.get("number"), int)
             )
             return numbers, ""
     ```
     So: problem → `((), problem)`; `null` → `((), "")`; a list → the int `number` of every dict
     item, in the order given; anything else → ``((), "`gh pr list` returned JSON that is not a list")``.
   - `open_change_request_between(base=B, head=H)`:
     ```python
         run, problem = self._run(
             self._scoped(
                 ["pr", "list"],
                 [
                     "--base",
                     base,
                     "--head",
                     head,
                     "--state",
                     "open",
                     "--json",
                     "number",
                     "--jq",
                     '.[0].number // ""',
                 ],
             )
         )
         if run is None:
             return None, problem
         if run.returncode != 0:
             return None, self._failed(run, "gh pr list")
         out = (run.stdout or "").strip()
         return (int(out), "") if out.isdigit() else (None, "")
     ```
5. No verb raises: a missing `gh`, a non-zero exit, a transport problem or malformed JSON is
   always an answer.
6. No consumer changes. `merge_train.py`, `promote.py` and `pr_automation.py` move in parts 1, 2
   and 4.

## Where to change
- `vibey_gh/interfaces/forge_adapter_interface.py`: the block in behaviour 1, inserted with one
  `edit_file` whose `old_string` is the line `    # --- Mutations ---` (unique; at integration
  HEAD `4317cff6` it is line 90, earlier lanes of the wave move it, so find it with
  `grep -n "# --- Mutations ---" vibey_gh/interfaces/forge_adapter_interface.py`) and whose
  `new_string` is the new block, a blank line, then that same line.
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, `vibey_gh/forge_github.py`: append the
  methods to the end of each file. Each adapter class (`ForgejoForge`, `GitLabForge`,
  `GitHubForge`) is its module's last statement, so append into the class with `edit_file` (the lane's `shell` tool takes an argv list, so a shell heredoc cannot run): `old_string` is the file's last three lines copied exactly from `read_file`, and `new_string` is those same lines followed by the new code, every line indented four spaces (eight inside
  a method), starting with one blank line. Then run
  `python -m black --line-length 100 vibey_gh/forge_forgejo.py vibey_gh/forge_gitlab.py vibey_gh/forge_github.py vibey_gh/interfaces/forge_adapter_interface.py`
  once. Read only the slices you need (`sed -n 'a,bp' file`, `tail -n 60 file`). Never rewrite a
  whole module and never use `write_file` on these files.
- `test/test_forge_change_request_lists.py` (new): the tests below. Start it with the provenance
  header line copied from line 1 of `vibey_gh/forge.py`, then a one-line module docstring.
- Nothing else. No new class is added, so no new interface file is needed.

## Acceptance criteria
- [ ] `python -m pytest -q --no-cov test/test_forge_change_request_lists.py` passes.
- [ ] Each GitHub verb's argv and `cwd` are pinned by a `fake_gh` test, both unbound and bound
      (`--repo o/r` right after `pr list`): `test_github_numbers_listing_is_the_merge_trains_argv`,
      `test_github_between_reads_the_jq_answer`,
      `test_github_labelled_listing_is_pr_automations_argv_when_bound`.
- [ ] The Forgejo and GitLab tests assert the exact routes requested through `RoutedTransport`,
      including the page query `_pages` appends: `test_forgejo_listings_filter_one_paged_walk`,
      `test_gitlab_listings_use_query_filters`.
- [ ] `test_every_listing_passes_a_problem_through` passes for all 9 forge × verb cases.
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`.
- [ ] black, isort, mypy, `ruff check` and `ruff format --check` are clean (block below).
- [ ] `git diff --stat` lists only the five files named under "Where to change".

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` an import or a module/class
attribute, never `mock.patch`, `MagicMock` or `AsyncMock`.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`), a real `gh` executable put
  first on `PATH`. `fake_gh.script({"<argv joined by single spaces>": {"out": ..., "err": ...,
  "code": ...}})` replaces every scripted answer; an unscripted argv exits 3 with
  `no scripted answer`. `fake_gh.invocations()` returns `[{"argv": [...], "cwd": ..., "stdin":
  None}, ...]` in call order; `fake_gh.forget()` clears the records but keeps the answers. Build
  `GitHubForge(root=tmp_path)` (unbound) or `GitHubForge(root=tmp_path, repository="o/r")` (bound)
  and compare `cwd` with `str(tmp_path.resolve())` (macOS `/private` symlink safe).
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py`, imported as
  `from forge_doubles import RoutedTransport` (pytest puts `test/` on `sys.path`). It answers a
  GET keyed by `"<path>"` and anything else keyed by `"<path> <METHOD>"`, gives the same answer
  every time a key is asked, records every `args` tuple in `.calls`, and answers an unrouted key
  with `([], "no route for <key>")`. Read `sed -n '1,80p' test/forge_doubles.py` first and build
  it the way its constructor takes the route table (a dict of key → `(value, problem)`, written
  below as `RoutedTransport(routes)`). Build `ForgejoForge(root=tmp_path, repository="o/r",
  transport=transport)` and `GitLabForge(root=tmp_path, repository="o/r", transport=transport)`.
- Forgejo's `_pages` appends `page=N&limit=50` and GitLab's `page=N&per_page=100` (with `?` or
  `&`). Forgejo stops at an empty page, so every Forgejo listing test also routes page 2 to
  `([], "")`; GitLab stops at a page shorter than 100 items, so one page is enough.

`test/test_forge_change_request_lists.py`:
- `test_github_numbers_listing_is_the_merge_trains_argv(fake_gh, tmp_path)`. Unbound argv
  `["pr", "list", "--base", "develop", "--state", "open", "--json", "number", "--jq", "sort_by(.number)"]`
  answering `[{"number": 5}, "junk", {"number": "6"}, {"number": 3}]` gives `((5, 3), "")` and
  exactly one invocation with that argv and `cwd == str(tmp_path.resolve())`. Answering `null`
  gives `((), "")`; answering `{}` gives
  ``((), "`gh pr list` returned JSON that is not a list")``. Bound, the argv is
  `["pr", "list", "--repo", "o/r", "--base", "develop", "--state", "open", "--json", "number", "--jq", "sort_by(.number)"]`.
- `test_github_between_reads_the_jq_answer(fake_gh, tmp_path)`. Argv
  `["pr", "list", "--base", "main", "--head", "develop", "--state", "open", "--json", "number", "--jq", '.[0].number // ""']`
  (its fake_gh key ends `--jq .[0].number // ""`). Out `"7\n"` → `(7, "")`; out `"\n"` →
  `(None, "")`; code 1 with err `boom` → `(None, "boom")`; code 1 with no output →
  ``(None, "`gh pr list` exited 1")``. Bound, `--repo o/r` follows `pr list`. Pin the argv and
  `cwd` of the first call.
- `test_github_labelled_listing_is_pr_automations_argv_when_bound(fake_gh, tmp_path)`. Bound
  `GitHubForge(root=tmp_path, repository="o/r")` runs
  `["pr", "list", "--repo", "o/r", "--state", "open", "--label", "L", "--json", "number"]`;
  `[{"number": 2}]` → `((2,), "")`. Unbound runs
  `["pr", "list", "--state", "open", "--label", "L", "--json", "number"]`. Code 1 with err `boom`
  on the bound argv → `((), "gh pr list --repo o/r --state open --label L --json number: boom")`
  (the transport's own `RuntimeError` text, passed through by `_read`).
- `test_forgejo_listings_filter_one_paged_walk(tmp_path)`. Routes
  `"repos/o/r/pulls?state=open&page=1&limit=50"` → `(PULLS, "")` and
  `"repos/o/r/pulls?state=open&page=2&limit=50"` → `([], "")`, with
  ```python
  PULLS = [
      {"number": 9, "base": {"ref": "develop", "repo_id": 1},
       "head": {"ref": "topic", "repo_id": 1}, "labels": [{"name": "L"}]},
      {"number": 4, "base": {"ref": "develop", "repo_id": 1},
       "head": {"ref": "fix", "repo_id": 1}, "labels": []},
      {"number": 7, "base": {"ref": "main", "repo_id": 1},
       "head": {"ref": "develop", "repo_id": 1}, "labels": [{"name": "L"}]},
      {"number": 3, "base": {"ref": "main", "repo_id": 1},
       "head": {"ref": "develop", "repo_id": 2}, "labels": []},
      {"number": "x", "base": {"ref": "develop"}, "head": {"ref": "develop"},
       "labels": [{"name": "L"}]},
  ]
  ```
  (write it one key per line if black prefers). Assert: `open_change_request_numbers(base="develop")
  == ((4, 9), "")`; `open_change_request_between(base="main", head="develop") == (7, "")` (3 is a
  fork and is excluded); `open_change_request_between(base="main", head="nope") == (None, "")`;
  `labelled_open_change_request_numbers(label="L") == ((7, 9), "")`; and
  `transport.calls[0] == ("repos/o/r/pulls?state=open&page=1&limit=50",)`.
- `test_gitlab_listings_use_query_filters(tmp_path)`. Routes:
  - `"projects/o%2Fr/merge_requests?state=opened&target_branch=release%2F1.0&page=1&per_page=100"`
    → `([{"iid": 8}, {"iid": 2}, {"iid": "x"}], "")`; `open_change_request_numbers(base="release/1.0")
    == ((2, 8), "")`.
  - `"projects/o%2Fr/merge_requests?state=opened&target_branch=main&source_branch=develop&page=1&per_page=100"`
    → rows `{"iid": 6, "source_project_id": 1, "target_project_id": 1}`,
    `{"iid": 5, "source_project_id": 2, "target_project_id": 1}`,
    `{"iid": 9, "source_project_id": 1, "target_project_id": 1}`;
    `open_change_request_between(base="main", head="develop") == (6, "")` (5 is a fork).
  - `"projects/o%2Fr/merge_requests?state=opened&target_branch=main&source_branch=nope&page=1&per_page=100"`
    → `([], "")`; `open_change_request_between(base="main", head="nope") == (None, "")`.
  - `"projects/o%2Fr/merge_requests?state=opened&labels=needs%20review&page=1&per_page=100"`
    → `([{"iid": 4}, {"iid": 1}], "")`;
    `labelled_open_change_request_numbers(label="needs review") == ((1, 4), "")`.
  - Assert the first element of each recorded call equals the route asked for.
- `test_every_listing_passes_a_problem_through(kind, verb, tmp_path)`, parametrised over
  `kind` in `("forgejo", "gitlab", "github")` and `verb` in `("numbers", "between", "labelled")`.
  Forgejo and GitLab use `RoutedTransport` with no routes; GitHub uses
  `GitHubForge(root=tmp_path, transport=GhTransport(executable="gh-not-installed"))`
  (`from vibey_gh.gh_transport import GhTransport`). The value is `()` for numbers and labelled,
  `None` for between. The problem is exactly
  ``"the GitHub CLI (`gh-not-installed`) is not installed"`` for GitHub and starts with
  `"no route for "` for Forgejo and GitLab.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_change_request_lists.py test/test_forge_adapters.py test/test_platform.py
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
- `open_change_request_branches` and the `ChangeRequest.cross_repository` field (child lane 2,
  split-334-2-open-branches) and `wait_for_checks` (child lane 3, split-334-3-wait-for-checks).
- Every consumer module: `merge_train.py`, `promote.py`, `pr_automation.py`, `reconcile.py`
  (parts 1-6 of the wave).
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_forge_github.py` (never edit them).
- `.vibey-gh.toml` and its `[platform] kind = "github"` declaration: never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  (this spec's title) when done.

## Conventions this lane relies on (everything needed is here)
**C1, the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when
the forge answered; otherwise `value` is the empty value for its type (`()` or `None` here) and
`problem` is one sentence. No verb raises for a failed call, a missing client, a non-2xx status
or unreadable output (vibey-gh ADR 0001).

**C2, GitHub argv fidelity.** Each GitHub verb runs the same `gh` argv as today's call site, byte
for byte: do not reorder flags, rename them or add fields. `[scope]` is `["--repo",
self.repository]` when the adapter is bound (`self.repository` non-empty) and nothing otherwise;
it goes right after the two-word subcommand (`pr list [scope] --base …`). Every call runs with
`cwd=self.root`.

**Helpers already on the branch (added by the #332 and #333 lanes; do not re-add them):**
- `GitHubForge._scoped(self, head: list[str], tail: list[str]) -> list[str]` =
  `head + (["--repo", self.repository] if self.repository else []) + tail`.
- `GitHubForge._read(self, args: Sequence[str], *, stdin: str | None = None) -> tuple[Any, str]`:
  `self.transport.json(args, cwd=self.root, stdin=stdin)`. `FileNotFoundError` →
  ``(None, "the GitHub CLI (`<executable>`) is not installed")``; `RuntimeError` →
  `(None, str(error))`, which for a non-zero exit is `"gh <argv joined by spaces>: <stderr>"`;
  `ValueError` → ``(None, "`gh <args[0]> <args[1]>` returned output that is not JSON")``. Empty
  stdout reads as `null`, that is `None`.
- `GitHubForge._run(self, args: Sequence[str], *, stdin: str | None = None) ->
  tuple[subprocess.CompletedProcess[str] | None, str]`: the finished process and `""`, or `None`
  and the same not-installed sentence.
- `GitHubForge._failed(run, label: str, *, with_stdout: bool = False) -> str` (static):
  `(run.stderr or (run.stdout if with_stdout else "") or "").strip()`, or
  ``f"`{label}` exited {run.returncode}"`` when that is empty.
- `ForgejoForge._pages` / `GitLabForge._pages(self, path: str, *, most: int | None = None) ->
  tuple[list[dict[str, Any]], str]`: walks a paged listing, appending `?` or `&` then
  `page=N&limit=50` (Forgejo, stops at an empty page) or `page=N&per_page=100` (GitLab, stops at
  a page shorter than 100 items), keeps dict items only, stops once `most` items are held, and
  answers `([], problem)` on any transport problem, a non-list page or more than 100 pages.
- `ForgejoForge._repository()` = `quote(self.repository, safe="/")`;
  `GitLabForge._project()` = `quote(self.repository, safe="")`.
- Transports answer `survey([path])` as a GET and `survey([path, METHOD, body])` otherwise; a 2xx
  with an empty body is `({}, "")`.

**C7, tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
(`pyproject.toml` `--cov-fail-under=100 --cov-branch`), so every branch above needs a test.
Focused runs need `--no-cov`. Tests import only the double they need.

**C8, the formatter trap.** `black --line-length 100` + `isort` (CI tools-lint) and the root
`ruff format` must both be clean, and they disagree on some wraps. So: keep lines at or under 100
columns (95 for nested calls); bind a long expected value to a local before the `assert`; do not
use implicit string concatenation; write multi-line calls with one argument per line and a
trailing comma; do not use backslash continuations. If the two formatters fight over a line,
restructure the line; never alternate between them. Fix import order with
`isort test/test_forge_change_request_lists.py`.

**C9, the big files.** Append to the adapter modules with a heredoc, run black once, read only
slices, never rewrite a module.

**Depends on:** split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve, split-333-1-facts-translators, split-333-2-change-request-reads, split-333-3-change-request-text
- split-332-1-transport-seams: transports answer an empty 2xx as `({}, "")`.
- split-332-2-adapter-paging: `ForgejoForge._pages` / `GitLabForge._pages` and `RoutedTransport` in `test/forge_doubles.py`.
- split-332-3-repository-name: `GitHubForge._scoped`, `_read`, `_run`, `_failed`.
- split-332-4-selector-resolve: nothing directly; it must be merged so the adapter files are at their post-foundation state.
- split-333-1-facts-translators: nothing directly; merged first because the wave's first half is sequential.
- split-333-2-change-request-reads: nothing directly; its methods precede these at the end of each adapter file.
- split-333-3-change-request-text: nothing directly; the last lane before this one to append to the same adapter files.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
