<!-- split of #333: child 3 of 3; audit: issue-audit/updates/333.md -->

## Title
feat(gh): the forge adapter reads a change request's text, comment bodies and changed paths

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge
(`src/vibey_tools/gh/docs/doctrines.md:138`), and every forge call must go through
`ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Three more reads are still raw `gh`:

- promotion reads a pull request's title and body with `gh pr view N --json title,body`
  (`vibey_gh/promote.py:317-329`), reporting a failure through `_detail`
  (`vibey_gh/promote.py:391-396`);
- the merge train reads the bodies of a pull request's comments to find its own notice,
  `gh pr view N --json comments -q .comments[].body` (`vibey_gh/merge_train.py:110`), and
  searches stdout and stderr together (`merge_train.py:76-81`);
- the protected-paths guard needs every changed path,
  `gh api --paginate repos/{owner}/{repo}/pulls/N/files?per_page=100` parsed by
  `ProtectedPathsGuard().parse_listing` (`vibey_gh/merge_train.py:257-287`,
  `vibey_gh/protected_paths.py:52-76`).

This lane adds the three verbs, with the GitHub argv byte for byte as today, so the later lanes
that move promotion and the merge train onto the adapter change nothing a github-declared
repository sees.

## Required behaviour
1. `vibey_gh/interfaces/forge_adapter_interface.py` declares, directly after
   `change_request_with_thread` (under `# --- Change-request reads ---`):
   ```python
       def change_request_text(self, number: int) -> tuple[tuple[str, str] | None, str]:
           """A change request's `(title, body)`, and a problem."""
           ...

       def change_request_comment_bodies(self, number: int) -> tuple[tuple[str, ...], str]:
           """The bodies of a change request's comments, and a problem."""
           ...

       def changed_paths(self, number: int) -> tuple[tuple[tuple[str, ...], int] | None, str]:
           """Every path a change request touches, renames' old paths included, and how many
           files the forge listed; and a problem."""
           ...
   ```
   All three adapters implement all three.
2. **Forgejo** (`vibey_gh/forge_forgejo.py`). Implement and test it first (8.b). Append at the
   end of the class, reusing `_object` and `_pages` from the earlier lanes:
   ```python
       def change_request_text(self, number: int) -> tuple[tuple[str, str] | None, str]:
           pull, problem = self._object(f"repos/{self._repository()}/pulls/{number}")
           if pull is None:
               return None, problem
           return (str(pull.get("title") or ""), str(pull.get("body") or "")), ""

       def change_request_comment_bodies(self, number: int) -> tuple[tuple[str, ...], str]:
           # ONE request, never _pages: Forgejo's issues/{index}/comments takes no page or limit
           # and answers every comment at once. `_comments` is split-332-2's helper.
           comments, problem = self._comments(number)
           if problem:
               return (), problem
           return tuple(str(comment.get("body") or "") for comment in comments), ""

       def changed_paths(self, number: int) -> tuple[tuple[tuple[str, ...], int] | None, str]:
           files, problem = self._pages(f"repos/{self._repository()}/pulls/{number}/files")
           if problem:
               return None, problem
           paths: list[str] = []
           for entry in files:
               name = entry.get("filename")
               if not isinstance(name, str) or not name:
                   return None, "Forgejo listed a changed file without a filename"
               paths.append(name)
               previous = entry.get("previous_filename")
               if isinstance(previous, str) and previous:
                   paths.append(previous)
           return (tuple(paths), len(files)), ""
   ```
   A changed file without a filename is a problem, not a silent gap: the protected-paths guard
   must never judge a listing it could not read (the GitHub parser refuses the same case,
   `protected_paths.py:68-70`).
3. **GitLab** (`vibey_gh/forge_gitlab.py`). Append at the end of the class:
   ```python
       def change_request_text(self, number: int) -> tuple[tuple[str, str] | None, str]:
           path = f"projects/{self._project()}/merge_requests/{number}"
           mr, problem = self._object(path)
           if mr is None:
               return None, problem
           return (str(mr.get("title") or ""), str(mr.get("description") or "")), ""

       def change_request_comment_bodies(self, number: int) -> tuple[tuple[str, ...], str]:
           notes_path = f"projects/{self._project()}/merge_requests/{number}/notes?sort=asc"
           notes, problem = self._pages(notes_path)
           if problem:
               return (), problem
           bodies = tuple(
               str(note.get("body") or "") for note in notes if note.get("system") is not True
           )
           return bodies, ""

       def changed_paths(self, number: int) -> tuple[tuple[tuple[str, ...], int] | None, str]:
           diffs_path = f"projects/{self._project()}/merge_requests/{number}/diffs"
           diffs, problem = self._pages(diffs_path)
           if problem:
               return None, problem
           paths: list[str] = []
           for entry in diffs:
               new_path = entry.get("new_path")
               if not isinstance(new_path, str) or not new_path:
                   return None, "GitLab listed a changed file without a path"
               paths.append(new_path)
               old_path = entry.get("old_path")
               renamed = bool(entry.get("renamed_file"))
               if renamed and isinstance(old_path, str) and old_path and old_path != new_path:
                   paths.append(old_path)
           return (tuple(paths), len(diffs)), ""
   ```
   System notes (`"system": true`) are dropped from the comment bodies.
4. **GitHub** (`vibey_gh/forge_github.py`). Add `import json` to the imports and
   `from vibey_gh.protected_paths import ProtectedPathsGuard` to the first-party imports. Append
   at the end of the class:
   ```python
       def change_request_text(self, number: int) -> tuple[tuple[str, str] | None, str]:
           args = self._scoped(["pr", "view", str(number)], ["--json", "title,body"])
           run, problem = self._run(args)
           if run is None:
               return None, problem
           if run.returncode:
               detail = " ".join((run.stderr or run.stdout or "").split())[:300]
               return None, detail or f"gh pr view exited {run.returncode}"
           try:
               data = json.loads(run.stdout or "null")
           except json.JSONDecodeError:
               data = None
           if not isinstance(data, dict):
               return None, f"gh pr view {number} did not return a title and body"
           return (str(data.get("title") or ""), str(data.get("body") or "")), ""

       def change_request_comment_bodies(self, number: int) -> tuple[tuple[str, ...], str]:
           args = self._scoped(
               ["pr", "view", str(number)],
               ["--json", "comments", "-q", ".comments[].body"],
           )
           run, problem = self._run(args)
           if run is None:
               return (), problem
           if run.returncode:
               return (), self._failed(run, "gh pr view")
           return ((run.stdout or "") + (run.stderr or ""),), ""

       def changed_paths(self, number: int) -> tuple[tuple[tuple[str, ...], int] | None, str]:
           listing = f"repos/{{owner}}/{{repo}}/pulls/{number}/files?per_page=100"
           run, problem = self._run(["api", "--paginate", listing])
           if run is None:
               return None, problem
           if run.returncode:
               return None, self._failed(run, "gh api")
           try:
               paths, listed = ProtectedPathsGuard().parse_listing(run.stdout or "")
           except (TypeError, ValueError) as error:
               unreadable = "`gh api` returned a file listing that could not be read"
               return None, f"{unreadable}: {error}"
           return (paths, listed), ""
   ```
   - `change_request_text` is byte-identical to `promote.py:317-329` with `_detail`
     (`promote.py:391-396`): the argv is `pr view N [--repo R] --json title,body`; a non-zero
     exit answers the first 300 characters of stderr (else stdout) with whitespace collapsed, or
     `gh pr view exited <rc>` when both are empty; output that is not JSON, or JSON that is not an
     object (`null` included), answers `gh pr view <n> did not return a title and body`.
   - `change_request_comment_bodies` answers stdout and stderr together, verbatim, as one string
     (what `merge_train._gh` returns, `merge_train.py:76-81`); a non-zero exit answers
     `_failed(run, "gh pr view")` (stderr, else ``"`gh pr view` exited <rc>"``).
   - `changed_paths` runs `gh api --paginate repos/{owner}/{repo}/pulls/N/files?per_page=100`
     with the literal braces (gh's own placeholders) and **no** `--repo` scope, even when bound,
     exactly as `merge_train.py:269-279`. `parse_listing` returns every `filename`, plus each
     `previous_filename`, and the number of files listed; it raises `TypeError` for a file with no
     filename and `json.JSONDecodeError` (a `ValueError`) for text that is not JSON.
5. No consumer changes (`promote.py`, `merge_train.py` stay as they are).

## Where to change
Every path in this spec is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package
`vibey_gh`) unless it starts with `src/` or `.github/`; the check block starts with
`cd src/vibey_tools/gh`. The adapter modules were edited by every earlier forge lane, so find each
anchor by the method name given here and read the file's tail before appending. Call-site anchors
in other modules are those of the storm integration branch at `4317cff6`.

Four production files, because each verb is declared on the protocol and all three adapters must
implement it in the same change:
- `vibey_gh/interfaces/forge_adapter_interface.py`: the three declarations.
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`: the three methods appended.
- `vibey_gh/forge_github.py`: the two imports and the three methods appended.
- Test: `test/test_forge_change_request_text.py` (new).
- Only if `test/test_patching_ratchet.py` exists when you start (another storm lane adds the
  tenant's patching ratchet) and it fails on a test file this lane created: record that file in
  `test/patching_baseline.json` with its true counts, all zero (this lane adds no patch). Never
  raise a count. If the ratchet does not exist, skip this.

## Acceptance criteria
- [ ] `test_github_text_reproduces_promotions_messages`,
      `test_github_comment_bodies_return_stdout_and_stderr_together` and
      `test_github_changed_paths_page_with_gh_placeholders` pin the exact GitHub argv and cwd.
- [ ] `test_every_text_read_passes_a_problem_through` passes for every forge × verb.
- [ ] `python -m pytest -q` (run in `src/vibey_tools/gh`) passes with 100% line and branch
      coverage of `vibey_gh`; black, isort, mypy, ruff check and ruff format --check are clean.

## Tests to write first (TDD)
New file `test/test_forge_change_request_text.py` (provenance header first). GitHub tests use the
conftest `fake_gh` fixture; Forgejo and GitLab tests use `RoutedTransport`. Imports:
```python
from __future__ import annotations

import pytest
from forge_doubles import RoutedTransport

from vibey_gh.forge_forgejo import ForgejoForge
from vibey_gh.forge_github import GitHubForge
from vibey_gh.forge_gitlab import GitLabForge
from vibey_gh.gh_transport import GhTransport
```
Tests:
- `test_github_text_reproduces_promotions_messages(fake_gh, tmp_path)`:
  ```python
      fake_gh.script(
          {
              "pr view 7 --json title,body": {"out": '{"title": "T", "body": "B"}'},
              "pr view 8 --json title,body": {"out": '{"title": null}'},
              "pr view 9 --json title,body": {"err": "x  y\n", "code": 1},
              "pr view 10 --json title,body": {"code": 1},
              "pr view 11 --json title,body": {"out": "null"},
              "pr view 12 --json title,body": {"out": "not json"},
              "pr view 13 --json title,body": {"err": "a " * 200, "code": 1},
              "pr view 7 --repo o/r --json title,body": {"out": '{"title": "T"}'},
          }
      )
      forge = GitHubForge(root=tmp_path)
      assert forge.change_request_text(7) == (("T", "B"), "")
      argv = ["pr", "view", "7", "--json", "title,body"]
      expected = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == expected
      assert forge.change_request_text(8) == (("", ""), "")
      assert forge.change_request_text(9) == (None, "x y")
      assert forge.change_request_text(10) == (None, "gh pr view exited 1")
      unread = "gh pr view 11 did not return a title and body"
      assert forge.change_request_text(11) == (None, unread)
      not_json = "gh pr view 12 did not return a title and body"
      assert forge.change_request_text(12) == (None, not_json)
      long_detail = " ".join(("a " * 200).split())[:300]
      assert forge.change_request_text(13) == (None, long_detail)
      assert forge.for_repository("o/r").change_request_text(7) == (("T", ""), "")
      bound = ["pr", "view", "7", "--repo", "o/r", "--json", "title,body"]
      assert fake_gh.invocations()[-1]["argv"] == bound
      absent = GhTransport(executable="gh-not-installed")
      missing = GitHubForge(root=tmp_path, transport=absent)
      not_installed = "the GitHub CLI (`gh-not-installed`) is not installed"
      assert missing.change_request_text(7) == (None, not_installed)
  ```
- `test_github_comment_bodies_return_stdout_and_stderr_together(fake_gh, tmp_path)`:
  ```python
      key = "pr view 7 --json comments -q .comments[].body"
      fake_gh.script({key: {"out": "first\nsecond\n", "err": "warn\n"}})
      forge = GitHubForge(root=tmp_path)
      assert forge.change_request_comment_bodies(7) == (("first\nsecond\nwarn\n",), "")
      argv = ["pr", "view", "7", "--json", "comments", "-q", ".comments[].body"]
      expected = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == expected
      fake_gh.script({key: {"err": "boom\n", "code": 1}})
      assert forge.change_request_comment_bodies(7) == ((), "boom")
      fake_gh.script({key: {"out": "ignored\n", "code": 1}})
      assert forge.change_request_comment_bodies(7) == ((), "`gh pr view` exited 1")
      bound_key = "pr view 7 --repo o/r --json comments -q .comments[].body"
      fake_gh.script({bound_key: {"out": ""}})
      assert forge.for_repository("o/r").change_request_comment_bodies(7) == (("",), "")
      absent = GhTransport(executable="gh-not-installed")
      missing = GitHubForge(root=tmp_path, transport=absent)
      not_installed = "the GitHub CLI (`gh-not-installed`) is not installed"
      assert missing.change_request_comment_bodies(7) == ((), not_installed)
  ```
- `test_github_changed_paths_page_with_gh_placeholders(fake_gh, tmp_path)`:
  ```python
      key = "api --paginate repos/{owner}/{repo}/pulls/7/files?per_page=100"
      pages = '[{"filename": "a.py"}][{"filename": "b.py", "previous_filename": "old.py"}]'
      fake_gh.script({key: {"out": pages}})
      forge = GitHubForge(root=tmp_path, repository="o/r")
      assert forge.changed_paths(7) == ((("a.py", "b.py", "old.py"), 2), "")
      argv = ["api", "--paginate", "repos/{owner}/{repo}/pulls/7/files?per_page=100"]
      expected = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == expected
      unreadable = "`gh api` returned a file listing that could not be read"
      fake_gh.script({key: {"out": '[{"no": 1}]'}})
      no_name = f"{unreadable}: a listed file has no filename: {{'no': 1}}"
      assert forge.changed_paths(7) == (None, no_name)
      fake_gh.script({key: {"out": "oops"}})
      value, problem = forge.changed_paths(7)
      assert value is None and problem.startswith(f"{unreadable}: ")
      fake_gh.script({key: {"err": "HTTP 404\n", "code": 1}})
      assert forge.changed_paths(7) == (None, "HTTP 404")
      fake_gh.script({key: {"code": 1}})
      assert forge.changed_paths(7) == (None, "`gh api` exited 1")
      absent = GhTransport(executable="gh-not-installed")
      missing = GitHubForge(root=tmp_path, transport=absent)
      not_installed = "the GitHub CLI (`gh-not-installed`) is not installed"
      assert missing.changed_paths(7) == (None, not_installed)
  ```
  (the adapter is bound to `o/r` and the argv still carries no `--repo`.)
- `test_forgejo_reads_text_comment_bodies_and_changed_paths(tmp_path)`: a Forgejo adapter bound to
  `"o/r"` over `RoutedTransport` with these routes:
  - `"repos/o/r/pulls/7"` → `({"title": "T", "body": None}, "")`;
    `change_request_text(7) == (("T", ""), "")`;
  - `"repos/o/r/pulls/8"` → `([], "")`; `change_request_text(8) == (None, "Forgejo answered
    repos/o/r/pulls/8 with something other than an object")` (build it from a path local);
  - `"repos/o/r/issues/7/comments"` → `([{"body": "a"}, {"body": None}], "")`
    and `"...page=2&limit=50"` → `([], "")`; `change_request_comment_bodies(7) == (("a", ""), "")`;
  - `"repos/o/r/pulls/7/files?page=1&limit=50"` → `([{"filename": "a.py"}, {"filename": "b.py",
    "previous_filename": "old.py"}, {"filename": "c.py", "previous_filename": ""}], "")` and
    `"...page=2&limit=50"` → `([], "")`; `changed_paths(7) == ((("a.py", "b.py", "old.py",
    "c.py"), 3), "")`;
  - `"repos/o/r/pulls/8/files?page=1&limit=50"` → `([{"filename": ""}], "")`;
    `changed_paths(8) == (None, "Forgejo listed a changed file without a filename")`.
  Bind each long route key and expected value to a local.
- `test_gitlab_reads_text_comment_bodies_and_changed_paths(tmp_path)`: a GitLab adapter bound to
  `"o/r"` over `RoutedTransport` with these routes:
  - `"projects/o%2Fr/merge_requests/7"` → `({"title": "T", "description": "D"}, "")`;
    `change_request_text(7) == (("T", "D"), "")`;
  - `"projects/o%2Fr/merge_requests/7/notes?sort=asc&page=1&per_page=100"` →
    `([{"body": "a", "system": False}, {"body": "merged", "system": True}], "")`;
    `change_request_comment_bodies(7) == (("a",), "")`;
  - `"projects/o%2Fr/merge_requests/7/diffs?page=1&per_page=100"` →
    `([{"new_path": "a.py", "old_path": "a.py"}, {"new_path": "b.py", "old_path": "old.py",
    "renamed_file": True}, {"new_path": "c.py", "old_path": "c.py", "renamed_file": True}], "")`;
    `changed_paths(7) == ((("a.py", "b.py", "old.py", "c.py"), 3), "")`;
  - `"projects/o%2Fr/merge_requests/8/diffs?page=1&per_page=100"` → `([{"old_path": "x"}], "")`;
    `changed_paths(8) == (None, "GitLab listed a changed file without a path")`.
  Bind each long route key and expected value to a local.
- `test_every_text_read_passes_a_problem_through`:
  ```python
  @pytest.mark.parametrize("kind", ["github", "forgejo", "gitlab"])
  @pytest.mark.parametrize(
      ("verb", "empty"),
      [
          ("change_request_text", None),
          ("change_request_comment_bodies", ()),
          ("changed_paths", None),
      ],
  )
  def test_every_text_read_passes_a_problem_through(fake_gh, tmp_path, kind, verb, empty):
      forges = {
          "github": GitHubForge(root=tmp_path, repository="o/r"),
          "forgejo": ForgejoForge(root=tmp_path, repository="o/r", transport=RoutedTransport()),
          "gitlab": GitLabForge(root=tmp_path, repository="o/r", transport=RoutedTransport()),
      }
      value, problem = getattr(forges[kind], verb)(7)
      assert value == empty
      if kind == "github":
          assert problem == "no scripted answer"
      else:
          assert problem.startswith("no route for ")
  ```
  (`fake_gh` has no answers here, so every `gh` call exits 3 and prints `no scripted answer`.)

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_change_request_text.py test/test_forge_change_request_reads.py test/test_forge_adapters.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the files named under "Where to change"
git status --short   # the one new file, test/test_forge_change_request_text.py, and nothing else new
```
If black or isort reports a file you touched, run `python -m black --line-length 100 <file>` and
`isort <file>` on that file only, then run the whole block again.

## Out of scope
- `vibey_gh/promote.py`, `vibey_gh/merge_train.py`, `vibey_gh/protected_paths.py` and every other
  consumer: later forge lanes move them onto these verbs.
- `change_request_facts`, `change_request_with_thread`, `get_check_results` (the previous lane)
  and every listing, write, issue, release and branch-rule verb (later forge lanes).
- `vibey_gh/forge.py`, the facts modules and their interfaces.
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_forge_adapters.py`.
- The repository's `[platform] kind = "github"` declaration in the root `.vibey-gh.toml`
  (lines 18-19): never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  when done.

## Conventions this lane relies on (everything needed is here)
- **Shared rules for this lane and the previous one** (from the parent's plan):
  - Every verb answers `(value, problem)`, never raises, and returns the empty value with a
    one-sentence problem when it could not ask.
  - **Forgejo is the default adapter (8.b): implement and test it first.**
  - GitHub argv is copied byte for byte from the named call site. `self._scoped(head, tail)`
    inserts `--repo <bound name>` only when the adapter is bound.
  - `{R}` in a GitHub API path is `repository_name()`'s answer. Forgejo `{R}` =
    `quote(repository, safe="/")` (`self._repository()`), GitLab `{P}` =
    `quote(repository, safe="")` (`self._project()`). Literal `repos/{owner}/{repo}/…` (with
    braces) is gh's own placeholder and stays literal where the call site used it, with no scope.
  - GitHub tests use the conftest `fake_gh` fixture. Forgejo/GitLab tests use `RoutedTransport`
    from `test/forge_doubles.py`.
  - Append new methods to the end of each adapter module (the class is the module's last
    statement). Do not rewrite whole files.
- **The adapter contract (vibey-gh ADR 0001).** `problem` is `""` exactly when the forge
  answered; otherwise `value` is the empty value for its type (`None`, `()`, `frozenset()`,
  `False`, `[]`, `{}`) and `problem` is one sentence. No verb raises for a failed call, a missing
  client, a non-2xx status or unreadable output (`interfaces/forge_adapter_interface.py:9-16`).
- **What the earlier lanes built, and this lane calls:**
  - `GitHubForge._scoped(head: list[str], tail: list[str]) -> list[str]`: `head`, then
    `["--repo", self.repository]` only when bound, then `tail`.
  - `GitHubForge._run(args, *, stdin=None) -> tuple[subprocess.CompletedProcess[str] | None,
    str]`: the finished process whatever it exited with, or `(None, "the GitHub CLI (`gh`) is not
    installed")`.
  - `GitHubForge._failed(run, label, *, with_stdout=False) -> str` (static): the stripped stderr
    (or stdout, only with `with_stdout=True`), else ``"`<label>` exited <rc>"``.
  - `ForgejoForge._object(path)` / `GitLabForge._object(path) -> tuple[dict[str, Any] | None,
    str]`: one GET that must answer a JSON object, else `(None, "<Forgejo|GitLab> answered <path>
    with something other than an object")`; a transport problem passes through.
  - `ForgejoForge._pages(path, *, most=None)` / `GitLabForge._pages(...) -> tuple[list[dict[str,
    Any]], str]`: every dict of a paged listing. Forgejo appends `?`/`&` + `page=N&limit=50` and
    stops at an empty page; GitLab appends `page=N&per_page=100` and stops at a page shorter than
    100. A transport problem passes through as `([], problem)`.
- **`fake_gh`** (fixture at `test/conftest.py:151-156`; class `FakeGh` at
  `test/conftest.py:87-144`) puts a real `gh` executable first on `PATH` (through
  `monkeypatch.setenv`, a declared seam). `fake_gh.script({"<argv joined by single spaces>":
  {"out": "...", "err": "...", "code": 0}})` replaces every scripted answer; an argv with no answer
  exits 3 and prints `no scripted answer` on stderr. `fake_gh.invocations()` lists
  `{"argv": [...], "cwd": "<directory gh ran in>", "stdin": None}` per call, in order (compare
  `cwd` with `str(tmp_path.resolve())`). To prove "gh is not installed", build
  `GhTransport(executable="gh-not-installed")`.
- **`RoutedTransport`** (`test/forge_doubles.py`; `from forge_doubles import RoutedTransport`)
  answers keyed by `"<path>"` for a GET and `"<path> <METHOD>"` otherwise, returns the same routed
  answer every time, records every `args` tuple in `.calls`, and answers an unrouted request with
  `([], "no route for <key>")`.
- **Tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
  (`pyproject.toml:64-71`). Focused runs need `--no-cov`; the whole-suite run must pass without
  it. Substitute only at a declared seam: no `monkeypatch.setattr` of an import or of a module or
  class attribute, no `mock.patch`, no `MagicMock`/`AsyncMock` (sub-doctrine 9.b). Never touch
  `test/conftest.py`.
- **Working in the big files.** Each adapter class is the last statement of its module, so a new
  method is added at the end of the class: use `edit_file` with the class's current last method
  (read the tail with `tail -n 40 <file>`) as `old_string`, and that same method followed by the
  new methods (indented four spaces) as `new_string`. Read only the slices you need. Never rewrite
  a whole module and never use `write_file` on an existing file.
- **The formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
  (profile black, `combine_as_imports`; CI job `tools-lint`, `.github/workflows/ci.yml:699-705`)
  and the root `ruff format --check .` (line length 100). They disagree on some wraps, so write
  lines neither wants to rewrap:
  - keep every line at or under 100 columns, and at or under 95 for anything with nested calls;
  - bind a long comparison, expected value or path to a local first;
  - never use implicit string concatenation; use one literal, or an f-string built from locals;
  - never put a string literal inside an f-string's braces; bind it to a local first;
  - write multi-line calls and collections with one element per line and a trailing comma;
  - never use backslash continuations.

  If the two formatters fight over a line, restructure the line. Never alternate between them.
- **Platforms (8.h).** The suite must pass on Arch Linux and macOS: no GNU-only tools in tests,
  and compare paths through `Path.resolve()`.

**Depends on:** split-333-2-change-request-reads
- split-333-2-change-request-reads: the `_object` helpers on both HTTP adapters and the
  `# --- Change-request reads ---` section of the protocol this lane extends.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
