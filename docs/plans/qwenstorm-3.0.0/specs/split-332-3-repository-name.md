<!-- split of #332: child 3 of 4; audit: issue-audit/updates/332.md -->

## Title
feat(gh): the forge adapter names its repository and deletes a branch

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge
(`src/vibey_tools/gh/docs/doctrines.md:138`), and every forge call must go through the one
vibey-owned protocol, `ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Two things every
later lane needs are missing from that protocol:

- **The repository's name.** The merge train and reconcile look it up before deleting a merged
  branch (`vibey_gh/merge_train.py:350-352`, `vibey_gh/reconcile.py:397`), and
  `github_state.repository()` answers it as `$GH_REPO`, else `gh repo view --json nameWithOwner`
  (`vibey_gh/github_state.py:70-75`). The GitHub adapter's own `_repository()` just returns
  `self.repository` (`vibey_gh/forge_github.py:298-299`), so an unbound adapter builds
  `repos//…` paths in `list_artifacts` (`:57-64`), `get_reviews` (`:179`), `get_check_results`
  (`:201`), `set_protected_ref` (`:269`) and `get_protected_refs` (`:278`).
- **Deleting a branch** (`merge_train.py:352`, `reconcile.py:397`).

The GitHub adapter must run the same `gh` argv as today, byte for byte, so a github-declared
repository sees no change. That needs three helpers every later GitHub verb uses: the `--repo`
scope rule, a JSON reader and a process runner that turn every failure into a problem (vibey-gh
ADR 0001: verbs answer `(value, problem)` and never raise).

## Required behaviour
1. `GitHubForge` (`vibey_gh/forge_github.py:37-299`) gains these helpers. Add `import os`,
   `import subprocess` and `from collections.abc import Sequence` to the module's imports.
   ```python
       def _scoped(self, head: list[str], tail: list[str]) -> list[str]:
           """`head`, then `--repo <name>` only when this adapter is bound, then `tail`."""
           return head + (["--repo", self.repository] if self.repository else []) + tail

       def _read(self, args: Sequence[str], *, stdin: str | None = None) -> tuple[Any, str]:
           """The JSON `gh` printed, and a problem. Never raises (vibey-gh ADR 0001)."""
           try:
               return self.transport.json(args, cwd=self.root, stdin=stdin), ""
           except FileNotFoundError:
               return None, self._not_installed()
           except RuntimeError as error:
               return None, str(error)
           except ValueError:
               label = " ".join((self.transport.executable, *args[:2]))
               return None, f"`{label}` returned output that is not JSON"

       def _run(
           self, args: Sequence[str], *, stdin: str | None = None
       ) -> tuple[subprocess.CompletedProcess[str] | None, str]:
           """The finished `gh` process, whatever it exited with, and a problem."""
           try:
               return self.transport.run(args, cwd=self.root, stdin=stdin), ""
           except FileNotFoundError:
               return None, self._not_installed()

       def _not_installed(self) -> str:
           return f"the GitHub CLI (`{self.transport.executable}`) is not installed"

       @staticmethod
       def _failed(
           run: subprocess.CompletedProcess[str], label: str, *, with_stdout: bool = False
       ) -> str:
           """What a failed `gh` said, or which command exited with what."""
           detail = (run.stderr or (run.stdout if with_stdout else "") or "").strip()
           return detail or f"`{label}` exited {run.returncode}"
   ```
   `self.transport.json` raises `RuntimeError(f"gh {' '.join(args)}: {stderr}")` on a non-zero
   exit, lets a `json.JSONDecodeError` (a `ValueError`) through for output that is not JSON, and
   `FileNotFoundError` when the executable is missing (`vibey_gh/gh_transport.py:67-77`).
   `_read` passes the `RuntimeError` text through unchanged: it is exactly what
   `merge_train._gh_json` and `github_state.gh_json` raise today.
2. `GitHubForge.repository_name(self) -> tuple[str, str]`: the bound `self.repository`; else a
   non-empty `$GH_REPO`; else `_read(["repo", "view", "--json", "nameWithOwner"])`, whose problem
   passes through unchanged; a JSON answer without a non-empty string `nameWithOwner` answers
   ``("", "`gh repo view` did not name the repository")``:
   ```python
       def repository_name(self) -> tuple[str, str]:
           if self.repository:
               return self.repository, ""
           exported = os.environ.get("GH_REPO", "")
           if exported:
               return exported, ""
           value, problem = self._read(["repo", "view", "--json", "nameWithOwner"])
           if problem:
               return "", problem
           name = value.get("nameWithOwner") if isinstance(value, dict) else None
           if isinstance(name, str) and name:
               return name, ""
           return "", "`gh repo view` did not name the repository"
   ```
3. `GitHubForge.delete_branch(self, branch: str) -> tuple[bool, str]`: `name` from
   `repository_name()` (its problem → `(False, problem)`); then
   `_run(["api", f"repos/{name}/git/refs/heads/{branch}", "--method", "DELETE"])` (today's argv
   at `merge_train.py:352`; the branch is not quoted); `(None, problem)` → `(False, problem)`;
   exit 0 → `(True, "")`; any other exit → `(False, self._failed(run, "gh api",
   with_stdout=True))`.
4. The existing GitHub verbs that build `repos/{R}/…` take `R` from `repository_name()`, and when
   it has a problem return their empty value plus that problem, before asking anything else:
   `list_artifacts` → `([], problem)` (resolve the name first, then build the mapping with it),
   `get_reviews` → `((), problem)`, `get_check_results` → `((), problem)`, `set_protected_ref` →
   `(False, problem)`, `get_protected_refs` → `(frozenset(), problem)`. Their argv and every other
   behaviour stay as they are (they keep calling `self.transport.survey`). The old
   `_repository()` helper (`forge_github.py:298-299`) is removed.
5. `ForgejoForge` and `GitLabForge` gain:
   ```python
       def repository_name(self) -> tuple[str, str]:
           if self.repository:
               return self.repository, ""
           remedy = "set [platform] repository, or give the clone an origin remote"
           return "", f"no Forgejo repository is named: {remedy}"

       def delete_branch(self, branch: str) -> tuple[bool, str]:
           branch_path = quote(branch, safe="/")
           path = f"repos/{self._repository()}/branches/{branch_path}"
           _, problem = self.transport.survey([path, "DELETE", ""], cwd=self.root)
           if problem:
               return False, problem
           return True, ""
   ```
   GitLab says `"no GitLab repository is named: {remedy}"`, and its `delete_branch` uses
   `branch_path = quote(branch, safe="")` and
   `path = f"projects/{self._project()}/repository/branches/{branch_path}"`. A 2xx answer with an
   empty body (every DELETE) is already `({}, "")` after child lane 1.
6. `vibey_gh/interfaces/forge_adapter_interface.py` declares both verbs directly after
   `for_repository` (lines 40-42), before `# --- Generic Walk (for snapshots) ---` (line 44):
   ```python
       # --- Repository ---

       def repository_name(self) -> tuple[str, str]:
           """The `owner/name` this adapter calls, and a problem."""
           ...

       def delete_branch(self, branch: str) -> tuple[bool, str]:
           """Deletes a branch on the forge, and a problem."""
           ...
   ```
   All three adapters subclass this protocol, so each must implement both verbs (mypy treats an
   unimplemented protocol member of an explicit subclass as abstract).
7. `test/test_forge_adapters.py`'s `_github()` helper (integration lines 39-40; one line lower
   now, after child lane 1's added import) builds
   `GitHubForge(root=Path("/repo"), repository="o/r", transport=transport)`, so the
   `ScriptedTransport`-driven GitHub assertions never need to ask `gh` for the name.
8. `test/test_forge_github.py` passes unmodified.

## Where to change
Every path in this spec is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package
`vibey_gh`) unless it starts with `src/` or `.github/`; the check block starts with
`cd src/vibey_tools/gh`. Line anchors in `vibey_gh/forge_github.py` and
`vibey_gh/interfaces/forge_adapter_interface.py` are those of the storm integration branch at
`4317cff6` (no earlier lane touches them). `vibey_gh/forge_forgejo.py` and
`vibey_gh/forge_gitlab.py` were edited by child lane 2, so read their tails before appending.

Four production files, because a verb declared on the protocol must be implemented by all three
adapters in the same change:
- `vibey_gh/forge_github.py`: imports (lines 15-19); `list_artifacts` (48-81), `get_reviews`
  (177-197), `get_check_results` (199-221), `set_protected_ref` (266-274), `get_protected_refs`
  (276-287) edited in place; `_repository` (298-299) replaced, with `edit_file`, by
  `repository_name`, `delete_branch`, `_scoped`, `_read`, `_run`, `_not_installed` and `_failed`.
- `vibey_gh/forge_forgejo.py` and `vibey_gh/forge_gitlab.py`: `repository_name` and
  `delete_branch` appended at the end of the class.
- `vibey_gh/interfaces/forge_adapter_interface.py`: the two declarations (after line 42).
- `test/test_forge_foundation.py`: new imports in the top import block, new tests appended.
- `test/test_forge_adapters.py`: the `_github()` helper (`def _github(transport: ScriptedTransport)
  -> GitHubForge:`, integration lines 39-40).
- Only if `test/test_patching_ratchet.py` exists when you start (another storm lane adds the
  tenant's patching ratchet) and it fails on a test file this lane created: record that file in
  `test/patching_baseline.json` with its true counts, all zero (this lane adds no patch). Never
  raise a count. If the ratchet does not exist, skip this.

## Acceptance criteria
- [ ] `python -m pytest -q` (run in `src/vibey_tools/gh`) passes with 100% line and branch
      coverage of `vibey_gh`.
- [ ] `grep -n "_repository()" vibey_gh/forge_github.py` finds nothing.
- [ ] `test/test_forge_github.py` passes and `git diff --stat` does not show it.
- [ ] Every test named below passes.
- [ ] black, isort, mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
GitHub argv tests use the conftest `fake_gh` fixture (described under Conventions). Forgejo and
GitLab tests use `RoutedTransport` from `test/forge_doubles.py`. To prove "gh is not installed",
build `GhTransport(executable="gh-not-installed")`. Never patch a module attribute or an import.

**`test/test_forge_foundation.py`.** Add to the top import block (keep isort order): `import
subprocess` (after `import dataclasses`), `from vibey_gh.forge_github import GitHubForge` and
`from vibey_gh.gh_transport import GhTransport` (after the `vibey_gh.forge_gitlab` and
`vibey_gh.forgejo_transport` imports respectively, as isort orders them). Then append:
```python
def test_github_scope_is_empty_until_bound(tmp_path):
    forge = GitHubForge(root=tmp_path)
    unbound = ["pr", "view", "7", "--json", "x"]
    assert forge._scoped(["pr", "view", "7"], ["--json", "x"]) == unbound
    bound = ["pr", "view", "7", "--repo", "o/r", "--json", "x"]
    assert forge.for_repository("o/r")._scoped(["pr", "view", "7"], ["--json", "x"]) == bound


def test_github_repository_name_prefers_binding_then_gh_repo_then_gh(
    fake_gh, tmp_path, monkeypatch
):
    forge = GitHubForge(root=tmp_path)
    assert forge.for_repository("o/r").repository_name() == ("o/r", "")
    monkeypatch.setenv("GH_REPO", "a/b")
    assert forge.repository_name() == ("a/b", "")
    assert fake_gh.invocations() == []
    monkeypatch.setenv("GH_REPO", "")
    key = "repo view --json nameWithOwner"
    fake_gh.script({key: {"out": '{"nameWithOwner": "c/d"}'}})
    assert forge.repository_name() == ("c/d", "")
    argv = ["repo", "view", "--json", "nameWithOwner"]
    expected = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
    assert fake_gh.invocations() == expected
    fake_gh.script({key: {"err": "boom\n", "code": 1}})
    assert forge.repository_name() == ("", "gh repo view --json nameWithOwner: boom")
    unnamed = "`gh repo view` did not name the repository"
    fake_gh.script({key: {"out": "{}"}})
    assert forge.repository_name() == ("", unnamed)
    fake_gh.script({key: {"out": "[]"}})
    assert forge.repository_name() == ("", unnamed)
    absent = GhTransport(executable="gh-not-installed")
    missing = GitHubForge(root=tmp_path, transport=absent)
    not_installed = "the GitHub CLI (`gh-not-installed`) is not installed"
    assert missing.repository_name() == ("", not_installed)


def test_github_read_and_run_turn_every_failure_into_a_problem(fake_gh, tmp_path):
    fake_gh.script(
        {
            "pr view 7": {"out": '{"a": 1}'},
            "pr view 8": {"err": "nope\n", "code": 1},
            "pr view 9": {"out": "not json"},
        }
    )
    forge = GitHubForge(root=tmp_path)
    assert forge._read(["pr", "view", "7"]) == ({"a": 1}, "")
    assert forge._read(["pr", "view", "8"]) == (None, "gh pr view 8: nope")
    not_json = "`gh pr view` returned output that is not JSON"
    assert forge._read(["pr", "view", "9"]) == (None, not_json)
    run, problem = forge._run(["pr", "view", "8"])
    assert problem == "" and run is not None and run.returncode == 1
    absent = GhTransport(executable="gh-not-installed")
    missing = GitHubForge(root=tmp_path, transport=absent)
    not_installed = "the GitHub CLI (`gh-not-installed`) is not installed"
    assert missing._read(["pr", "view", "7"]) == (None, not_installed)
    assert missing._run(["pr", "view", "7"]) == (None, not_installed)


def test_github_failed_prefers_stderr_then_stdout_then_the_exit_code():
    both = subprocess.CompletedProcess(["gh"], 1, stdout="out\n", stderr="err\n")
    only_out = subprocess.CompletedProcess(["gh"], 2, stdout="out\n", stderr="")
    silent = subprocess.CompletedProcess(["gh"], 3, stdout=None, stderr=None)
    assert GitHubForge._failed(both, "gh api") == "err"
    assert GitHubForge._failed(only_out, "gh api") == "`gh api` exited 2"
    assert GitHubForge._failed(only_out, "gh api", with_stdout=True) == "out"
    assert GitHubForge._failed(silent, "gh api", with_stdout=True) == "`gh api` exited 3"


def test_github_delete_branch_runs_todays_argv(fake_gh, tmp_path, monkeypatch):
    monkeypatch.setenv("GH_REPO", "o/r")
    key = "api repos/o/r/git/refs/heads/fix/thing --method DELETE"
    fake_gh.script({key: {"out": ""}})
    forge = GitHubForge(root=tmp_path)
    assert forge.delete_branch("fix/thing") == (True, "")
    argv = ["api", "repos/o/r/git/refs/heads/fix/thing", "--method", "DELETE"]
    expected = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
    assert fake_gh.invocations() == expected
    fake_gh.script({key: {"err": "Reference does not exist\n", "code": 1}})
    assert forge.delete_branch("fix/thing") == (False, "Reference does not exist")
    fake_gh.script({key: {"out": '{"message": "Not Found"}\n', "code": 1}})
    assert forge.delete_branch("fix/thing") == (False, '{"message": "Not Found"}')
    monkeypatch.delenv("GH_REPO")
    unnamed = "gh repo view --json nameWithOwner: no scripted answer"
    assert forge.delete_branch("fix/thing") == (False, unnamed)
    absent = GhTransport(executable="gh-not-installed")
    missing = GitHubForge(root=tmp_path, repository="o/r", transport=absent)
    not_installed = "the GitHub CLI (`gh-not-installed`) is not installed"
    assert missing.delete_branch("fix/thing") == (False, not_installed)


def test_github_verbs_take_the_repository_from_repository_name(fake_gh, tmp_path, monkeypatch):
    monkeypatch.delenv("GH_REPO", raising=False)
    forge = GitHubForge(root=tmp_path)
    problem = "gh repo view --json nameWithOwner: no scripted answer"
    assert forge.list_artifacts("issue") == ([], problem)
    assert forge.get_reviews(7) == ((), problem)
    assert forge.get_check_results("abc") == ((), problem)
    assert forge.set_protected_ref("main", True) == (False, problem)
    assert forge.get_protected_refs() == (frozenset(), problem)
    monkeypatch.setenv("GH_REPO", "o/r")
    fake_gh.forget()
    fake_gh.script({"api repos/o/r/pulls/7/reviews": {"out": "[]"}})
    assert forge.get_reviews(7) == ((), "")
    argv = ["api", "repos/o/r/pulls/7/reviews"]
    expected = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
    assert fake_gh.invocations() == expected


def test_forgejo_and_gitlab_repository_name_and_delete_branch_routes(tmp_path):
    forgejo_transport = RoutedTransport({"repos/o/r/branches/fix/thing DELETE": ({}, "")})
    forgejo = ForgejoForge(root=tmp_path, repository="o/r", transport=forgejo_transport)
    assert forgejo.repository_name() == ("o/r", "")
    assert forgejo.delete_branch("fix/thing") == (True, "")
    assert forgejo_transport.calls == [("repos/o/r/branches/fix/thing", "DELETE", "")]
    gitlab_route = "projects/o%2Fr/repository/branches/fix%2Fthing DELETE"
    gitlab_transport = RoutedTransport({gitlab_route: ({}, "")})
    gitlab = GitLabForge(root=tmp_path, repository="o/r", transport=gitlab_transport)
    assert gitlab.repository_name() == ("o/r", "")
    assert gitlab.delete_branch("fix/thing") == (True, "")
    deleted = ("projects/o%2Fr/repository/branches/fix%2Fthing", "DELETE", "")
    assert gitlab_transport.calls == [deleted]
    refused = ForgejoForge(root=tmp_path, repository="o/r", transport=RoutedTransport())
    assert refused.delete_branch("x") == (False, "no route for repos/o/r/branches/x DELETE")
    refused_gitlab = GitLabForge(root=tmp_path, repository="o/r", transport=RoutedTransport())
    gitlab_refusal = "no route for projects/o%2Fr/repository/branches/x DELETE"
    assert refused_gitlab.delete_branch("x") == (False, gitlab_refusal)
    remedy = "set [platform] repository, or give the clone an origin remote"
    forgejo_unnamed = f"no Forgejo repository is named: {remedy}"
    assert ForgejoForge(root=tmp_path).repository_name() == ("", forgejo_unnamed)
    gitlab_unnamed = f"no GitLab repository is named: {remedy}"
    assert GitLabForge(root=tmp_path).repository_name() == ("", gitlab_unnamed)
```

**`test/test_forge_adapters.py`**, the `_github()` helper: it returns
`GitHubForge(root=Path("/repo"), repository="o/r", transport=transport)`. Every other assertion
in that file stays as it is and must still pass.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_foundation.py test/test_forge_adapters.py test/test_forge_github.py test/test_platform.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the files named under "Where to change"
git status --short   # no new file
```
If black or isort reports a file you touched, run `python -m black --line-length 100 <file>` and
`isort <file>` on that file only, then run the whole block again.

## Out of scope
- `vibey_gh/forge_selector.py` (the GitHub binding, `current`, `resolve`) and `RecordingForge`:
  child lane 4 (`split-332-4-selector-resolve`).
- Every other verb and every consuming module (`merge_train.py`, `reconcile.py`, …): later forge
  lanes. Do not reshape `get_check_results`'s return value; a later lane does.
- `vibey_gh/github_state.py`: it keeps its own `repository()` for the GitHub-only callers.
- `test/conftest.py`, `test/test_forge_github.py`, `test/forge_doubles.py`.
- The repository's `[platform] kind = "github"` declaration in the root `.vibey-gh.toml`
  (lines 18-19): never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  when done.

## Conventions this lane relies on (everything needed is here)
- **The adapter contract (vibey-gh ADR 0001).** Every verb answers `(value, problem)`. `problem`
  is `""` exactly when the forge answered; otherwise `value` is the empty value for its type
  (`None`, `()`, `frozenset()`, `False`, `[]`, `{}`) and `problem` is one sentence. No verb raises
  for a failed call, a missing client, a non-2xx status or unreadable output
  (`vibey_gh/interfaces/forge_adapter_interface.py:9-16`).
- **GitHub: argv fidelity, the scope, `{R}`.**
  1. Each GitHub verb's argv is copied verbatim from the call site it replaces. Do not reorder
     flags, rename flags (`--title` is not `-t`), or add fields.
  2. The scope is `["--repo", self.repository]` when the adapter is bound (`self.repository`
     non-empty) and nothing when it is not. It goes immediately after the subcommand's positional
     argument, or after the two-word subcommand when there is none: `pr view 7 --repo o/r --json
     …`, `pr list --repo o/r --base …`. `_scoped(head, tail)` is the one place it is built.
  3. `{R}` in a `gh api` path is the name from `self.repository_name()`: the bound name, else
     `$GH_REPO`, else `gh repo view --json nameWithOwner`, exactly what
     `github_state.repository()` does today (`vibey_gh/github_state.py:70-75`). Literal
     `repos/{owner}/{repo}/…` (with braces) is gh's own placeholder and stays literal where a call
     site used it.
  4. Every call runs with `cwd=self.root`.
- **Forgejo and GitLab plumbing (after child lane 2).** `{R}` for Forgejo is
  `quote(self.repository, safe="/")` (`self._repository()`); `{P}` for GitLab is
  `quote(self.repository, safe="")` (`self._project()`). `survey([path, "DELETE", ""])` sends a
  DELETE with no body.
- **`fake_gh`** (fixture at `test/conftest.py:151-156`; class `FakeGh` at
  `test/conftest.py:87-144`) puts a real `gh` executable first on `PATH` (through
  `monkeypatch.setenv`, a declared seam). `fake_gh.script({"<argv joined by single spaces>":
  {"out": "...", "err": "...", "code": 0}})` replaces every scripted answer; an argv with no answer
  exits 3 and prints `no scripted answer` on stderr. `fake_gh.invocations()` lists
  `{"argv": [...], "cwd": "<directory gh ran in>", "stdin": None}` per call, in order (compare
  `cwd` with `str(tmp_path.resolve())`); `fake_gh.forget()` clears the records and keeps the
  answers. It does not set `GH_REPO`: every test whose argv holds a repository name sets or
  deletes `GH_REPO` itself.
- **`RoutedTransport`** (`test/forge_doubles.py`, child lane 2; import with
  `from forge_doubles import RoutedTransport`) answers keyed by `"<path>"` for a GET and
  `"<path> <METHOD>"` otherwise, records every `args` tuple in `.calls`, and answers an unrouted
  request with `([], "no route for <key>")`.
- **Tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
  (`pyproject.toml:64-71`). Focused runs need `--no-cov`; the whole-suite run must pass without
  it. Substitute only at a declared seam: no `monkeypatch.setattr` of an import or of a module or
  class attribute, no `mock.patch`, no `MagicMock`/`AsyncMock` (sub-doctrine 9.b). Never touch
  `test/conftest.py`.
- **Working in the big files.** Each adapter class is the last statement of its module, so a new
  method is added at the end of the class: use `edit_file` with the class's current last method
  (read the tail with `tail -n 40 <file>`) as `old_string`, and that same method followed by the
  new methods (indented four spaces) as `new_string`. Change an existing method with `edit_file`
  on that method alone. Read only the slices you need (`sed -n '170,230p'
  vibey_gh/forge_github.py`). Never rewrite a whole module and never use `write_file` on an
  existing file. New test code goes at the end of the test file; new imports go into the file's
  top import block.
- **The formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
  (profile black, `combine_as_imports`; CI job `tools-lint`, `.github/workflows/ci.yml:699-705`)
  and the root `ruff format --check .` (line length 100). They disagree on some wraps, so write
  lines neither wants to rewrap:
  - keep every line at or under 100 columns, and at or under 95 for anything with nested calls;
  - bind a long comparison, expected value or path to a local first;
  - never use implicit string concatenation; use one literal, or an f-string built from locals;
  - never put a string literal inside an f-string's braces; bind it to a local first;
  - write multi-line calls with one argument per line and a trailing comma;
  - never use backslash continuations.

  If the two formatters fight over a line, restructure the line. Never alternate between them.
- **Platforms (8.h).** The suite must pass on Arch Linux and macOS: no GNU-only tools in tests,
  and compare paths through `Path.resolve()`.

**Depends on:** split-332-2-adapter-paging
- split-332-2-adapter-paging: `RoutedTransport` in `test/forge_doubles.py`, the imports it added to
  `test/test_forge_foundation.py`, and the adapters' reshaped tails this lane appends to.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
