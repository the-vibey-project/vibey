<!-- split of #334: child 2 of 3; audit: issue-audit/updates/334.md -->

## Title
feat(gh): the forge adapter lists open change-request branches and whether each comes from a fork

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`)
and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`).
Reconcile lists the open pull requests' branches with raw `gh`
(`vibey_gh/reconcile.py:263-288`, argv at `:264-275`:
`pr list --repo R --state open --limit 100 --json number,headRefName,isCrossRepository`) and
needs to know whether each one comes from a fork (`:279`), but the neutral record
`ChangeRequest` (`vibey_gh/forge.py:65-80`) has no field that says so. vibey-gh ADR 0001
(`docs/adr/0001-forge-neutral-nouns.md:57-63`) adds a field with the first verb that reads it
from a real forge, and a verb with its first caller; this lane adds both so part 3 (reconcile)
can move off `gh`.

## Required behaviour
Every path in this spec is relative to `src/vibey_tools/gh/` (package `vibey_gh`).

1. `ChangeRequest` (`vibey_gh/forge.py:65-80`) gains `cross_repository: bool = False` as its
   **last** field, directly after `state: str = ""` (line 80). Every existing construction keeps
   working unchanged.
2. `ChangeRequestInterface` (`vibey_gh/interfaces/class_contracts.py:59-80`) gains, after its
   `state` property (lines 79-80):
   ```python

       @property
       def cross_repository(self) -> bool: ...
   ```
3. `ForgejoFacts` (`vibey_gh/forge_forgejo_facts.py`, added by split-333-1) gains
   `branch_request(self, raw: dict[str, Any]) -> ChangeRequest`, a pure method over one Forgejo
   pull object:
   ```python
       def branch_request(self, raw: dict[str, Any]) -> ChangeRequest:
           head = raw.get("head") or {}
           base = raw.get("base") or {}
           head_repo = head.get("repo_id")
           base_repo = base.get("repo_id")
           cross = isinstance(head_repo, int) and isinstance(base_repo, int) and head_repo != base_repo
           return ChangeRequest(
               number=int(raw["number"]),
               head_ref=str(head.get("ref") or ""),
               head_sha=str(head.get("sha") or ""),
               base_ref=str(base.get("ref") or ""),
               title=str(raw.get("title") or ""),
               body=str(raw.get("body") or ""),
               state="OPEN",
               cross_repository=cross,
           )
   ```
   The cross-repository rule is the same one `ForgejoFacts.change_request` uses for
   `isCrossRepository` (repo ids differ when both are ints, else `False`).
4. `GitLabFacts` (`vibey_gh/forge_gitlab_facts.py`, added by split-333-1) gains
   `branch_request(self, raw: dict[str, Any]) -> ChangeRequest` over one GitLab merge request:
   ```python
       def branch_request(self, raw: dict[str, Any]) -> ChangeRequest:
           return ChangeRequest(
               number=int(raw["iid"]),
               head_ref=str(raw.get("source_branch") or ""),
               head_sha=str(raw.get("sha") or ""),
               base_ref=str(raw.get("target_branch") or ""),
               title=str(raw.get("title") or ""),
               body=str(raw.get("description") or ""),
               state="OPEN",
               cross_repository=bool(raw.get("source_project_id") != raw.get("target_project_id")),
           )
   ```
5. Their interfaces declare it (ADR-0016): `ForgejoFactsInterface`
   (`vibey_gh/interfaces/forge_forgejo_facts_interface.py`) and `GitLabFactsInterface`
   (`vibey_gh/interfaces/forge_gitlab_facts_interface.py`) each gain
   ```python
       def branch_request(self, raw: dict[str, Any]) -> ChangeRequest:
           """One open change request's number, branches, head commit, text and fork flag."""
           ...
   ```
   Both interface modules import only the standard library and `vibey_gh.forge`; add
   `ChangeRequest` to their existing `from vibey_gh.forge import …` line (and `Any` from
   `typing` if it is not imported yet). Add `ChangeRequest` to the facts modules' own
   `from vibey_gh.forge import …` line the same way.
6. `vibey_gh/interfaces/forge_adapter_interface.py` declares, at the end of the
   `    # --- Change-request listings ---` block (after
   `labelled_open_change_request_numbers`, added by split-334-1):
   ```python
       def open_change_request_branches(
           self, *, limit: int
       ) -> tuple[tuple[ChangeRequest, ...], str]:
           """Up to `limit` open change requests, each with its head branch and fork flag."""
           ...
   ```
7. `ForgejoForge` (default adapter, implement and test first):
   ```python
       def open_change_request_branches(
           self, *, limit: int
       ) -> tuple[tuple[ChangeRequest, ...], str]:
           path = f"repos/{self._repository()}/pulls?state=open"
           pulls, problem = self._pages(path, most=limit)
           if problem:
               return (), problem
           facts = ForgejoFacts()
           requests = tuple(
               facts.branch_request(pull)
               for pull in pulls
               if isinstance(pull.get("number"), int)
           )
           return requests, ""
   ```
8. `GitLabForge`: the same over `f"projects/{self._project()}/merge_requests?state=opened"` with
   `most=limit`, `GitLabFacts().branch_request(row)`, keeping only rows whose `"iid"` is an int.
9. `GitHubForge`, byte-for-byte `reconcile.py:264-275`'s argv once bound:
   ```python
       def open_change_request_branches(
           self, *, limit: int
       ) -> tuple[tuple[ChangeRequest, ...], str]:
           value, problem = self._read(
               self._scoped(
                   ["pr", "list"],
                   [
                       "--state",
                       "open",
                       "--limit",
                       str(limit),
                       "--json",
                       "number,headRefName,isCrossRepository",
                   ],
               )
           )
           if problem:
               return (), problem
           if value is None:
               return (), ""
           if not isinstance(value, list):
               return (), "`gh pr list` returned JSON that is not a list"
           requests = tuple(
               ChangeRequest(
                   number=item["number"],
                   head_ref=str(item.get("headRefName") or ""),
                   head_sha="",
                   base_ref="",
                   cross_repository=bool(item.get("isCrossRepository")),
               )
               for item in value
               if isinstance(item, dict) and isinstance(item.get("number"), int)
           )
           return requests, ""
   ```
10. No verb raises. No consumer changes: `reconcile.py` moves in part 3.

## Where to change
This lane spans eleven files because one verb is declared on a protocol that all three adapters
subclass (mypy refuses an adapter that leaves a declared verb unimplemented), and the verb
returns a record field and two translator methods that do not exist yet. Each edit is small.
- `vibey_gh/forge.py:77-80`: add the field line after `    state: str = ""` inside
  `ChangeRequest` with one `edit_file`. `state: str = ""` and `body: str = ""` also appear in
  `ForgeIssue`, so the `old_string` is the four lines `    base_ref: str` (line 77, unique),
  `    title: str = ""`, `    body: str = ""`, `    state: str = ""`, and the `new_string` is
  those four lines plus `    cross_repository: bool = False`.
- `vibey_gh/interfaces/class_contracts.py:70-80`: the property after `ChangeRequestInterface.state`.
  `state` properties exist on other interfaces too, so the `old_string` runs from
  `    def base_ref(self) -> str: ...` (line 71, unique in the file) through the `state` property
  (line 80), and the `new_string` is that text plus the new property.
- `vibey_gh/forge_forgejo_facts.py` and `vibey_gh/forge_gitlab_facts.py`: append
  `branch_request` to the end of the class (each class is its module's last statement; check
  with `tail -n 30`), with a heredoc as described below.
- `vibey_gh/interfaces/forge_forgejo_facts_interface.py` and
  `vibey_gh/interfaces/forge_gitlab_facts_interface.py`: append the declaration to the end of the
  Protocol class (its last statement).
- `vibey_gh/interfaces/forge_adapter_interface.py`: the declaration in behaviour 6, with one
  `edit_file` anchored on the `labelled_open_change_request_numbers` declaration and its `...`
  body.
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, `vibey_gh/forge_github.py`: append the
  verb to the end of each file. `forge_forgejo.py` already imports `ForgejoFacts` and
  `forge_gitlab.py` already imports `GitLabFacts` (split-333-2 added them for
  `change_request_facts`); check with `grep -n "Facts" vibey_gh/forge_forgejo.py
  vibey_gh/forge_gitlab.py` and add `from vibey_gh.forge_forgejo_facts import ForgejoFacts` /
  `from vibey_gh.forge_gitlab_facts import GitLabFacts` only if missing. `ChangeRequest` is
  already imported by all three adapters.
- Appending: each class is its module's last statement, so append with `edit_file` (the lane's `shell` tool takes an argv list, so a shell heredoc cannot run): `old_string` is the file's last three lines copied exactly from `read_file`, and `new_string` is those same lines followed by the new code; with four-space indentation (eight inside a method), starting with
  one blank line, appends into the class. Then run
  `python -m black --line-length 100 vibey_gh/forge.py vibey_gh/interfaces/class_contracts.py vibey_gh/forge_forgejo_facts.py vibey_gh/forge_gitlab_facts.py vibey_gh/interfaces/forge_forgejo_facts_interface.py vibey_gh/interfaces/forge_gitlab_facts_interface.py vibey_gh/interfaces/forge_adapter_interface.py vibey_gh/forge_forgejo.py vibey_gh/forge_gitlab.py vibey_gh/forge_github.py test/test_forge_change_request_branches.py`
  once, and `isort` on the same files. Read only the slices you need (`sed -n 'a,bp' file`,
  `tail -n 60 file`); never rewrite a whole module and never use `write_file` on an existing file.
- `test/test_forge_change_request_branches.py` (new): the tests below, starting with the
  provenance header line copied from line 1 of `vibey_gh/forge.py` and a one-line docstring.

## Acceptance criteria
- [ ] `python -m pytest -q --no-cov test/test_forge_change_request_branches.py test/test_forge_facts.py test/test_platform.py test/test_forge_adapters.py` passes.
- [ ] `test_github_branches_listing_is_reconciles_argv_when_bound` pins
      `pr list --repo o/r --state open --limit 100 --json number,headRefName,isCrossRepository`
      and the unbound argv, each with `cwd == str(tmp_path.resolve())`.
- [ ] `test_a_change_request_knows_whether_it_comes_from_a_fork` passes.
- [ ] `test_forgejo_branches_are_one_paged_walk_of_open_pulls` and
      `test_gitlab_branches_are_one_paged_walk_of_open_merge_requests` assert the exact first route.
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`.
- [ ] black, isort, mypy, `ruff check` and `ruff format --check` are clean (block below).
- [ ] `git diff --stat` lists only the eleven files named under "Where to change".

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` an import or a module/class
attribute, never `mock.patch`, `MagicMock` or `AsyncMock`.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`), a real `gh` put first on
  `PATH`. `fake_gh.script({"<argv joined by single spaces>": {"out": ..., "err": ..., "code":
  ...}})` replaces every answer; unscripted argv exits 3. `fake_gh.invocations()` lists
  `{"argv": [...], "cwd": ..., "stdin": None}` per call; `fake_gh.forget()` clears the records.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py`
  (`from forge_doubles import RoutedTransport`). It answers a GET keyed by `"<path>"`, the same
  answer every time, records every `args` tuple in `.calls`, and answers an unrouted key with
  `([], "no route for <key>")`. Read `sed -n '1,80p' test/forge_doubles.py` first and build it the
  way its constructor takes the route table (a dict of key → `(value, problem)`, written below as
  `RoutedTransport(routes)`). Forgejo pages end `page=N&limit=50` and stop at an empty page, so
  route page 2 to `([], "")`; GitLab pages end `page=N&per_page=100`.

`test/test_forge_change_request_branches.py`:
- `test_a_change_request_knows_whether_it_comes_from_a_fork()`:
  `ChangeRequest(number=1, head_ref="topic", head_sha="", base_ref="").cross_repository is False`;
  one built with `cross_repository=True` answers `True`; it is an instance of
  `ChangeRequestInterface` (`from vibey_gh.interfaces.class_contracts import ChangeRequestInterface`);
  `dataclasses.fields(ChangeRequest)[-1].name == "cross_repository"`; assigning
  `record.cross_repository = False` raises `dataclasses.FrozenInstanceError`.
- `test_forgejo_facts_read_a_branch_request()`: `ForgejoFacts().branch_request(raw)` for
  `{"number": 9, "title": "T", "body": None, "head": {"ref": "topic", "sha": "abc", "repo_id": 2},
  "base": {"ref": "develop", "repo_id": 1}}` equals
  `ChangeRequest(9, "topic", "abc", "develop", "T", "", "OPEN", True)`; the same with both
  `repo_id`s `1` gives `cross_repository=False`; `{"number": 4}` (no head, no base) gives
  `ChangeRequest(4, "", "", "", "", "", "OPEN", False)`; and
  `isinstance(ForgejoFacts(), ForgejoFactsInterface)`.
- `test_gitlab_facts_read_a_branch_request()`: `GitLabFacts().branch_request(raw)` for
  `{"iid": 3, "source_branch": "topic", "sha": "abc", "target_branch": "main", "title": "T",
  "description": None, "source_project_id": 2, "target_project_id": 1}` equals
  `ChangeRequest(3, "topic", "abc", "main", "T", "", "OPEN", True)`; equal project ids give
  `False`; and `isinstance(GitLabFacts(), GitLabFactsInterface)`.
- `test_forgejo_branches_are_one_paged_walk_of_open_pulls(tmp_path)`. Routes
  `"repos/o/r/pulls?state=open&page=1&limit=50"` → `([FORK, SAME, {"number": "x"}], "")` and
  `"repos/o/r/pulls?state=open&page=2&limit=50"` → `([], "")`, where FORK is the first Forgejo raw
  object above and SAME is `{"number": 4, "head": {"ref": "fix", "sha": "def", "repo_id": 1},
  "base": {"ref": "develop", "repo_id": 1}}`. `open_change_request_branches(limit=100)` answers
  the two records (9 with `cross_repository=True`, 4 with `False`) in that order and `""`;
  `transport.calls[0] == ("repos/o/r/pulls?state=open&page=1&limit=50",)`. With `limit=1` the
  answer is only the first record.
- `test_gitlab_branches_are_one_paged_walk_of_open_merge_requests(tmp_path)`. Route
  `"projects/o%2Fr/merge_requests?state=opened&page=1&per_page=100"` → the GitLab raw object
  above, `{"iid": 1, "source_branch": "fix", "sha": "def", "target_branch": "main",
  "source_project_id": 1, "target_project_id": 1}` and `{"iid": "x"}`. The answer is the two
  records (3 cross, 1 not) and `""`; the first recorded call is that route.
- `test_github_branches_listing_is_reconciles_argv_when_bound(fake_gh, tmp_path)`. Bound
  `GitHubForge(root=tmp_path, repository="o/r")` runs
  `["pr", "list", "--repo", "o/r", "--state", "open", "--limit", "100", "--json", "number,headRefName,isCrossRepository"]`
  answering
  `[{"number": 5, "headRefName": "topic", "isCrossRepository": false}, {"number": 6, "headRefName": null, "isCrossRepository": true}, {"number": "x"}, "junk"]`
  → `(ChangeRequest(5, "topic", "", "", cross_repository=False), ChangeRequest(6, "", "", "",
  cross_repository=True))` and `""`, one invocation with that argv and
  `cwd == str(tmp_path.resolve())`. Unbound `GitHubForge(root=tmp_path)` runs the same argv
  without `--repo o/r`. `null` → `((), "")`; `{}` →
  ``((), "`gh pr list` returned JSON that is not a list")``.
- `test_every_branch_listing_passes_a_problem_through(kind, tmp_path)`, parametrised over
  `("forgejo", "gitlab", "github")`: Forgejo/GitLab with a `RoutedTransport` that has no routes
  answer `()` and a problem starting `"no route for "`; GitHub with
  `GitHubForge(root=tmp_path, transport=GhTransport(executable="gh-not-installed"))` answers
  `()` and ``"the GitHub CLI (`gh-not-installed`) is not installed"``.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_change_request_branches.py test/test_forge_facts.py test/test_platform.py test/test_forge_adapters.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --check --line-length 100 vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the eleven files named under "Where to change"
```

## Out of scope
- The three number listings (split-334-1, already merged) and `wait_for_checks`
  (split-334-3-wait-for-checks).
- `reconcile.py` and every other consumer module (parts 1-6 of the wave).
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_forge_facts.py`,
  `test/test_forge_github.py` (never edit them).
- `.vibey-gh.toml` and its `[platform] kind = "github"` declaration: never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  (this spec's title) when done.

## Conventions this lane relies on (everything needed is here)
**C1, the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when
the forge answered; otherwise `value` is the empty value (`()` here) and `problem` is one
sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable
output (vibey-gh ADR 0001). Forgejo is the default adapter (8.b): implement and test it first.

**C2, GitHub argv fidelity.** The GitHub argv is today's call site's, byte for byte. `[scope]` is
`["--repo", self.repository]` when bound and nothing otherwise, right after `pr list`. Every call
runs with `cwd=self.root`.

**Helpers already on the branch (do not re-add them):**
- `GitHubForge._scoped(self, head: list[str], tail: list[str]) -> list[str]` =
  `head + (["--repo", self.repository] if self.repository else []) + tail`.
- `GitHubForge._read(self, args: Sequence[str], *, stdin: str | None = None) -> tuple[Any, str]`:
  `self.transport.json(args, cwd=self.root, stdin=stdin)`; `FileNotFoundError` →
  ``(None, "the GitHub CLI (`<executable>`) is not installed")``; `RuntimeError` →
  `(None, str(error))` (`"gh <argv>: <stderr>"`); `ValueError` →
  ``(None, "`gh <args[0]> <args[1]>` returned output that is not JSON")``; empty stdout is `None`.
- `ForgejoForge._pages` / `GitLabForge._pages(self, path: str, *, most: int | None = None) ->
  tuple[list[dict[str, Any]], str]`: the paged walk described above; keeps dict items only; stops
  once `most` items are held and answers the first `most`; any problem answers `([], problem)`.
- `ForgejoForge._repository()` = `quote(self.repository, safe="/")`;
  `GitLabForge._project()` = `quote(self.repository, safe="")`.
- `ForgejoFacts` / `GitLabFacts` (split-333-1): pure classes (no I/O, no state) translating
  Forgejo/GitLab REST objects, each subclassing its `@runtime_checkable` Protocol interface, which
  declares every public method with a one-line docstring.

**C7, tests.** 100% line and branch coverage of all of `vibey_gh`; focused runs need `--no-cov`.

**C8, the formatter trap.** black + isort and root `ruff format` must both be clean: lines at or
under 100 columns (95 for nested calls); bind long expected values to a local before the
`assert`; no implicit string concatenation; multi-line calls one argument per line with a
trailing comma; no backslash continuations. If they fight, restructure the line.

**C9, the big files.** Append with a heredoc, run black once, read only slices, never rewrite a
module.

**Depends on:** split-334-1-labelled-listings
- split-334-1-labelled-listings: the `# --- Change-request listings ---` block in the protocol, which this lane extends, and the same adapter files at their post-listing state.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
