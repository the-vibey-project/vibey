<!-- split of #335: child 2 of 3; audit: issue-audit/updates/335.md -->

## Title
feat(gh)!: the forge adapter readies, closes, comments on and updates change requests, and names a fork's clone URL

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`)
and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`). PR
automation, the merge train and reconcile still act on pull requests with raw `gh`:
`vibey_gh/pr_automation.py:513-517` (`pr ready`), `vibey_gh/pr_automation.py:753-755` and
`vibey_gh/reconcile.py:355-360` (`pr close`), `vibey_gh/merge_train.py:113-121`,
`vibey_gh/pr_automation.py:740-752` and `vibey_gh/reconcile.py:349-354, 365-386` (`pr comment`),
`vibey_gh/reconcile.py:238-260` (the update-branch endpoint), and the fork mirror hard-codes
`https://github.com/` (`vibey_gh/pr_automation.py:688`). The existing `create_comment` cannot
stand in and has no caller: on GitHub it posts `issue comment` through `survey`, which demands
JSON, so it reports failure after succeeding (`vibey_gh/forge_github.py:223-229`); on Forgejo and
GitLab it posts the raw text instead of `{"body": …}` and falls back to a wrong route
(`vibey_gh/forge_forgejo.py:189-200`, `vibey_gh/forge_gitlab.py:200-212`). vibey-gh ADR 0001
(`docs/adr/0001-forge-neutral-nouns.md:57-63`): verbs answer `(value, problem)` and arrive with
their first caller, so `create_comment` is replaced by `comment_on_change_request` (the `!`).
Forgejo's work-in-progress prefixes are an instance setting, so they are a declared adapter field
rather than a hard-coded pattern (sub-doctrine 12.c).

## Required behaviour
Every path in this spec is relative to `src/vibey_tools/gh/` (package `vibey_gh`). Every verb
returns `tuple[bool, str]` unless stated otherwise, answers `(False, problem)` on any transport or
client problem, and never raises. Forgejo is the default adapter (8.b): implement and test it
first. `{R}` = `self._repository()` (Forgejo), `{P}` = `self._project()` (GitLab).

1. **Two small private helpers** (they keep each verb one or two lines):
   - `GitHubForge._acted(self, args: list[str], label: str) -> tuple[bool, str]`:
     ```python
         def _acted(self, args: list[str], label: str) -> tuple[bool, str]:
             run, problem = self._run(args)
             if run is None:
                 return False, problem
             if run.returncode == 0:
                 return True, ""
             return False, self._failed(run, label)
     ```
   - `ForgejoForge._sent` and `GitLabForge._sent(self, path: str, method: str, payload: dict[str, Any] | None) -> tuple[bool, str]`:
     ```python
         def _sent(
             self, path: str, method: str, payload: dict[str, Any] | None
         ) -> tuple[bool, str]:
             body = "" if payload is None else json.dumps(payload)
             _, problem = self.transport.survey([path, method, body], cwd=self.root)
             return (False, problem) if problem else (True, "")
     ```
   Before adding either, `grep -n "def _acted\|def _sent" vibey_gh/forge_*.py`; if an earlier lane
   already added one with exactly this behaviour, reuse it.
2. `mark_ready(self, number: int) -> tuple[bool, str]`:
   - Forgejo: `ForgejoForge` gains a last dataclass field
     `wip_prefixes: tuple[str, ...] = ("WIP:", "[WIP]")` (Forgejo's default
     `[repository.pull-request] WORK_IN_PROGRESS_PREFIXES`; an adopter's instance may differ).
     ```python
         def mark_ready(self, number: int) -> tuple[bool, str]:
             path = f"repos/{self._repository()}/pulls/{number}"
             pull, problem = self.transport.survey([path], cwd=self.root)
             if problem:
                 return False, problem
             if not isinstance(pull, dict):
                 return False, f"Forgejo did not answer pull request {number} as an object"
             title = str(pull.get("title") or "")
             prefixes = "|".join(re.escape(prefix) for prefix in self.wip_prefixes)
             stripped = re.sub(rf"^\s*(?:{prefixes})\s*", "", title, count=1, flags=re.IGNORECASE)
             if stripped == title and not pull.get("draft"):
                 return True, ""
             return self._sent(path, "PATCH", {"title": stripped})
     ```
     (`import re` is added to `forge_forgejo.py`.)
   - GitLab: a module constant after the imports of `forge_gitlab.py` (GitLab fixes these three
     prefixes itself; they are not an instance setting), plus `import re`:
     ```python
     # GitLab marks a merge request as a draft by exactly these title prefixes.
     _DRAFT_PREFIX = re.compile(r"^\s*(?:Draft:|\[Draft\]|\(Draft\))\s*", re.IGNORECASE)
     ```
     and
     ```python
         def mark_ready(self, number: int) -> tuple[bool, str]:
             path = f"projects/{self._project()}/merge_requests/{number}"
             request, problem = self.transport.survey([path], cwd=self.root)
             if problem:
                 return False, problem
             if not isinstance(request, dict):
                 return False, f"GitLab did not answer merge request {number} as an object"
             title = str(request.get("title") or "")
             stripped = _DRAFT_PREFIX.sub("", title, count=1)
             if stripped == title and not request.get("draft"):
                 return True, ""
             return self._sent(path, "PUT", {"title": stripped})
     ```
   - GitHub: `return self._acted(self._scoped(["pr", "ready", str(number)], []), "gh pr ready")`.
3. `close_change_request(self, number: int) -> tuple[bool, str]`:
   - Forgejo: `self._sent(f"repos/{R}/pulls/{number}", "PATCH", {"state": "closed"})`.
   - GitLab: `self._sent(f"projects/{P}/merge_requests/{number}", "PUT", {"state_event": "close"})`.
   - GitHub: `self._acted(self._scoped(["pr", "close", str(number)], []), "gh pr close")`.
4. `comment_on_change_request(self, number: int, body: str) -> tuple[bool, str]`:
   - Forgejo: `self._sent(f"repos/{R}/issues/{number}/comments", "POST", {"body": body})` (a pull
     request's conversation lives on its issue).
   - GitLab: `self._sent(f"projects/{P}/merge_requests/{number}/notes", "POST", {"body": body})`.
   - GitHub:
     `self._acted(self._scoped(["pr", "comment", str(number)], ["--body", body]), "gh pr comment")`.
   - **Remove `create_comment`** from the protocol and all three adapters. It has no caller
     outside the adapters. Delete its assertions in `test/test_forge_adapters.py`, so that
     `grep -rn create_comment vibey_gh test` finds nothing.
5. `update_change_request_branch(self, number: int) -> tuple[bool, str]`:
   - Forgejo: `self._sent(f"repos/{R}/pulls/{number}/update?style=merge", "POST", None)` (empty
     body).
   - GitLab: no request; answer
     `(False, NotSupported(ForgeKind.GITLAB, "update_change_request_branch", "GitLab can only rebase a merge request's source branch server-side, which rewrites it").problem)`,
     that is `"gitlab does not support update_change_request_branch: GitLab can only rebase a merge request's source branch server-side, which rewrites it"`.
   - GitHub (`{R}` from `repository_name()`, no `--repo`, as `reconcile.py:245-257` today):
     ```python
         def update_change_request_branch(self, number: int) -> tuple[bool, str]:
             name, problem = self.repository_name()
             if problem:
                 return False, problem
             run, problem = self._run(
                 ["api", f"repos/{name}/pulls/{number}/update-branch", "--method", "PUT"]
             )
             if run is None:
                 return False, problem
             if run.returncode == 0:
                 return True, ""
             lines = (run.stderr or "").strip().splitlines()
             return False, lines[-1] if lines else "refused"
     ```
     This is `reconcile.py:258-260`'s text without its `IndexError` on whitespace-only stderr.
6. `fork_clone_url(self, owner: str, name: str) -> tuple[str, str]`:
   - An empty `owner` or `name` → `("", "the change request names no fork repository")`.
   - Forgejo/GitLab: `(f"https://{self.host}/{owner}/{name}.git", "")` (`host` is the dataclass
     field split-332-2 added: `"forgejo.local"` / `"gitlab.com"` by default, the configured
     `[platform] host` when the selector builds the adapter).
   - GitHub: `(f"https://{GH_DEFAULT_HOST}/{owner}/{name}.git", "")`, which is today's literal
     `https://github.com/{owner}/{repo}.git` at `pr_automation.py:688` spelled with the module's
     existing `GH_DEFAULT_HOST = "github.com"` constant.
7. No consumer changes: `merge_train.py`, `pr_automation.py`, `reconcile.py` move in parts 1, 3
   and 4.

## Where to change
The protocol change forces all three adapters to change in the same lane (they subclass it).
- `vibey_gh/interfaces/forge_adapter_interface.py`:
  - replace the `create_comment` declaration (lines 92-94 at integration HEAD `4317cff6`; find it
    with `grep -n "def create_comment"`), whose exact text is
    ```python
        def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
            """A new comment on an issue or change request, and a problem."""
            ...
    ```
    with
    ```python
        def comment_on_change_request(self, number: int, body: str) -> tuple[bool, str]:
            """Post a comment on a change request's conversation, and a problem."""
            ...

        def mark_ready(self, number: int) -> tuple[bool, str]:
            """Take a change request out of draft, and a problem."""
            ...

        def close_change_request(self, number: int) -> tuple[bool, str]:
            """Close a change request without merging it, and a problem."""
            ...

        def update_change_request_branch(self, number: int) -> tuple[bool, str]:
            """Merge the base forward into a change request's head branch, and a problem."""
            ...
    ```
  - add directly after the `delete_branch` declaration (split-332-3; `grep -n "def delete_branch"`):
    ```python
        def fork_clone_url(self, owner: str, name: str) -> tuple[str, str]:
            """The HTTPS clone URL of the repository `owner/name` on this forge, and a problem."""
            ...
    ```
  `ForgeComment` stays imported (`get_issue_thread` still uses it).
- `vibey_gh/forge_github.py`: delete this exact block (lines 223-229 at `4317cff6`) and the blank
  line after it:
  ```python
      def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
          _, problem = self.transport.survey(
              ["issue", "comment", str(number), "--body", body], cwd=self.root
          )
          if problem:
              return None, problem
          return ForgeComment(id="unknown", author="system", body=body), ""
  ```
  then append `_acted` and the five verbs to the end of the file.
- `vibey_gh/forge_forgejo.py`: delete this exact block (lines 189-200 at `4317cff6`) and the blank
  line after it:
  ```python
      def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
          # Try issues then PRs
          _, problem = self.transport.survey(
              [f"repos/{self._repository()}/issues/{number}/comments", "POST", body], cwd=self.root
          )
          if problem:
              _, problem = self.transport.survey(
                  [f"repos/{self._repository()}/pulls/{number}/comments", "POST", body], cwd=self.root
              )
          if problem:
              return None, problem
          return ForgeComment(id="unknown", author="system", body=body), ""
  ```
  add `import re`, add the `wip_prefixes` field after the current last field (`sleep`, from
  split-334-3; anchor the `edit_file` on its unique line
  `    sleep: Callable[[float], None] = field(default=time.sleep, repr=False, compare=False)`),
  then append `_sent` and the five verbs.
- `vibey_gh/forge_gitlab.py`: delete this exact block (lines 200-212 at `4317cff6`) and the blank
  line after it:
  ```python
      def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
          # We'll try creating on issue, then MR
          _, problem = self.transport.survey(
              [f"projects/{self._project()}/issues/{number}/notes", "POST", body], cwd=self.root
          )
          if problem:
              _, problem = self.transport.survey(
                  [f"projects/{self._project()}/merge_requests/{number}/notes", "POST", body],
                  cwd=self.root,
              )
          if problem:
              return None, problem
          return ForgeComment(id="unknown", author="system", body=body), ""
  ```
  add `import re` and `_DRAFT_PREFIX` after the imports, then append `_sent` and the five verbs.
  `ForgeKind` and `NotSupported` are already imported (split-335-1); confirm with `grep -n`.
- `ForgeComment` stays imported in all three adapters (`get_issue_thread` uses it); ruff reports
  any import that does become unused as F401, and then delete it.
- Appending: each adapter class is its module's last statement, so append with `edit_file` (the lane's `shell` tool takes an argv list, so a shell heredoc cannot run): `old_string` is the file's last three lines copied exactly from `read_file`, and `new_string` is those same lines followed by the new code;
  (four-space indentation, eight inside a method, starting with one blank line) appends into the
  class. Then run
  `python -m black --line-length 100 vibey_gh/forge_github.py vibey_gh/forge_forgejo.py vibey_gh/forge_gitlab.py vibey_gh/interfaces/forge_adapter_interface.py test/test_forge_change_request_actions.py test/test_forge_adapters.py`
  and `isort` on the same files once. Read only slices; never rewrite a module; if an
  `old_string` does not match, read the current text with `sed -n` and copy it exactly.
- `test/test_forge_change_request_actions.py` (new), starting with the provenance header line
  copied from line 1 of `vibey_gh/forge.py` and a one-line docstring.
- `test/test_forge_adapters.py`: delete exactly these assertions (at `4317cff6` lines 127-128,
  239-247 and 346-354), each with one `edit_file`, plus one of the blank lines left around the
  GitHub pair; touch nothing else:
  ```python
      assert _github(ScriptedTransport(({}, ""))).create_comment(7, "body")[0].body == "body"
      assert _github(ScriptedTransport(([], "down"))).create_comment(7, "body") == (None, "down")
  ```
  ```python
      assert _gitlab(ScriptedTransport(({}, ""))).create_comment(7, "body")[0].body == "body"
      assert (
          _gitlab(ScriptedTransport(([], "first"), ({}, ""))).create_comment(7, "body")[0].body
          == "body"
      )
      assert _gitlab(ScriptedTransport(([], "first"), ([], "second"))).create_comment(7, "body") == (
          None,
          "second",
      )
  ```
  ```python
      assert _forgejo(ScriptedTransport(({}, ""))).create_comment(7, "body")[0].body == "body"
      assert (
          _forgejo(ScriptedTransport(([], "first"), ({}, ""))).create_comment(7, "body")[0].body
          == "body"
      )
      assert _forgejo(ScriptedTransport(([], "first"), ([], "second"))).create_comment(7, "body") == (
          None,
          "second",
      )
  ```

## Acceptance criteria
- [ ] `python -m pytest -q --no-cov test/test_forge_change_request_actions.py test/test_forge_adapters.py` passes.
- [ ] `grep -rn create_comment vibey_gh test` prints nothing.
- [ ] `test_github_ready_close_comment_argvs` pins every GitHub `pr` argv unbound and bound, with
      `cwd == str(tmp_path.resolve())`.
- [ ] GitLab's NotSupported answer for `update_change_request_branch` is asserted verbatim.
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`.
- [ ] black, isort, mypy, `ruff check` and `ruff format --check` are clean (block below).
- [ ] `git diff --stat` lists only the six files named under "Where to change".

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` an import or a module/class
attribute, never `mock.patch`, `MagicMock` or `AsyncMock`. `monkeypatch.setenv` /
`monkeypatch.delenv` of `GH_REPO` is the declared environment seam.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`), a real `gh` put first on
  `PATH`. `fake_gh.script({"<argv joined by single spaces>": {"out": ..., "err": ..., "code":
  ...}})` replaces every answer; unscripted argv exits 3. `fake_gh.invocations()` lists
  `{"argv": [...], "cwd": ..., "stdin": None}` per call; `fake_gh.forget()` clears the records.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py`
  (`from forge_doubles import RoutedTransport`); keys `"<path>"` for a GET and
  `"<path> <METHOD>"` otherwise; every `args` tuple is recorded in `.calls`; an unrouted key
  answers `([], "no route for <key>")`. Read `sed -n '1,80p' test/forge_doubles.py` first and
  build it the way its constructor takes the route table (a dict of key → `(value, problem)`,
  written below as `RoutedTransport(routes)`). Assert JSON bodies with `json.loads(call[2])`.
  Adapters: `ForgejoForge(root=tmp_path, repository="o/r", transport=t)`,
  `GitLabForge(root=tmp_path, repository="o/r", transport=t)`.

`test/test_forge_change_request_actions.py`:
- `test_forgejo_actions_route_and_send_json(tmp_path)`: routes
  `"repos/o/r/issues/5/comments POST"` → `({"id": 1}, "")`, `"repos/o/r/pulls/5 PATCH"` →
  `({}, "")`, `"repos/o/r/pulls/5/update?style=merge POST"` → `({}, "")`.
  `comment_on_change_request(5, "hi") == (True, "")` with body `{"body": "hi"}`;
  `close_change_request(5) == (True, "")` with body `{"state": "closed"}`;
  `update_change_request_branch(5) == (True, "")` recorded as
  `("repos/o/r/pulls/5/update?style=merge", "POST", "")`.
- `test_forgejo_mark_ready_strips_wip_and_skips_a_ready_pull(tmp_path)`, GET route
  `"repos/o/r/pulls/5"` and PATCH route `"repos/o/r/pulls/5 PATCH"` → `({}, "")`:
  - `{"title": "WIP: Add x", "draft": True}` → `(True, "")`, PATCH body `{"title": "Add x"}`;
  - `{"title": "  [wip]  Add x", "draft": False}` → PATCH body `{"title": "Add x"}`;
  - `{"title": "Add x", "draft": False}` → `(True, "")` with only the GET recorded;
  - `{"title": "Add x", "draft": True}` → PATCH body `{"title": "Add x"}`;
  - `ForgejoForge(root=tmp_path, repository="o/r", transport=t, wip_prefixes=("Draft:",))` with
    `{"title": "Draft: Add x"}` → PATCH body `{"title": "Add x"}`;
  - GET answering `([], "")` → `(False, "Forgejo did not answer pull request 5 as an object")`
    and no PATCH.
- `test_gitlab_actions_route_and_refuse_update_branch(tmp_path)`: routes
  `"projects/o%2Fr/merge_requests/5/notes POST"` → `({"id": 1}, "")` and
  `"projects/o%2Fr/merge_requests/5 PUT"` → `({}, "")`. Comment body `{"body": "hi"}`; close body
  `{"state_event": "close"}`; on a fresh transport `update_change_request_branch(5)` answers the
  NotSupported sentence in behaviour 5 (bind it to a local first) and `transport.calls == []`.
- `test_gitlab_mark_ready_strips_draft(tmp_path)`: GET `"projects/o%2Fr/merge_requests/5"`, PUT
  route → `({}, "")`. Titles `"Draft: Add x"`, `"[Draft] Add x"` and `"(draft) Add x"` each PUT
  `{"title": "Add x"}`; `{"title": "Add x", "draft": False}` → `(True, "")` with only the GET;
  `{"title": "Add x", "draft": True}` → PUT `{"title": "Add x"}`; a GET answering `([], "")` →
  `(False, "GitLab did not answer merge request 5 as an object")`.
- `test_github_ready_close_comment_argvs(fake_gh, tmp_path, bound)`, parametrised
  `bound in (False, True)`; the adapter is `GitHubForge(root=tmp_path, repository="o/r" if bound
  else "")` and `scope = ["--repo", "o/r"] if bound else []`:
  - `mark_ready(5)` runs `["pr", "ready", "5", *scope]`;
  - `close_change_request(5)` runs `["pr", "close", "5", *scope]`;
  - `comment_on_change_request(5, "hi there")` runs `["pr", "comment", "5", *scope, "--body", "hi there"]`;
  - each with code 0 answers `(True, "")`, and `fake_gh.invocations()` pins argv and cwd;
  - each with code 1 and err `denied` answers `(False, "denied")`; with code 1 and no output,
    ``"`gh pr ready` exited 1"``, ``"`gh pr close` exited 1"``, ``"`gh pr comment` exited 1"``.
- `test_github_update_branch_reports_the_last_stderr_line_or_refused(fake_gh, tmp_path, monkeypatch)`:
  with `monkeypatch.setenv("GH_REPO", "o/r")` and an unbound adapter, argv
  `["api", "repos/o/r/pulls/5/update-branch", "--method", "PUT"]`: code 0 → `(True, "")`; code 1
  err `"first\nlast line\n"` → `(False, "last line")`; code 1 err `"   \n"` → `(False, "refused")`;
  code 1 with no err → `(False, "refused")`. A bound `GitHubForge(root=tmp_path,
  repository="a/b")` runs `["api", "repos/a/b/pulls/5/update-branch", "--method", "PUT"]`. With
  `monkeypatch.delenv("GH_REPO", raising=False)`, unbound, and `repo view --json nameWithOwner`
  scripted code 1 err `boom` → `(False, "gh repo view --json nameWithOwner: boom")` and that is
  the only invocation.
- `test_fork_clone_url_per_forge(tmp_path)`: `GitHubForge(root=tmp_path).fork_clone_url("alice",
  "fork") == ("https://github.com/alice/fork.git", "")`;
  `ForgejoForge(root=tmp_path, host="forge.example")` → `"https://forge.example/alice/fork.git"`;
  `GitLabForge(root=tmp_path)` → `"https://gitlab.com/alice/fork.git"`; for each adapter,
  `fork_clone_url("", "fork")` and `fork_clone_url("alice", "")` answer
  `("", "the change request names no fork repository")`.
- `test_every_action_passes_a_problem_through(kind, verb, tmp_path, monkeypatch)`, parametrised
  over `kind` in `("forgejo", "gitlab", "github")` and `verb` in `("comment", "ready", "close",
  "update_branch")`, skipping (`pytest.skip`) only `("gitlab", "update_branch")`, whose refusal is
  tested above. Forgejo/GitLab use a `RoutedTransport` with no routes; GitHub uses
  `GitHubForge(root=tmp_path, transport=GhTransport(executable="gh-not-installed"))`
  (`from vibey_gh.gh_transport import GhTransport`) with `monkeypatch.setenv("GH_REPO", "o/r")`.
  Every answer is `False` with a problem that equals
  ``"the GitHub CLI (`gh-not-installed`) is not installed"`` (GitHub) or starts with
  `"no route for "` (Forgejo, GitLab).

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_change_request_actions.py test/test_forge_adapters.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --check --line-length 100 vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the six files named under "Where to change"
```

## Out of scope
- `create_change_request`, `update_change_request`, `merge_change_request` (split-335-1, already
  merged) and the label verbs (split-335-3-labels).
- Issue comments and comment edits (`comment_on_issue`, `update_comment`: the #336 lanes).
- `merge_train.py`, `pr_automation.py`, `reconcile.py` and every other consumer module (parts 1,
  3 and 4); wiring `wip_prefixes` to `[platform]` configuration or the selector.
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_forge_github.py` (never edit them).
- `.vibey-gh.toml` and its `[platform] kind = "github"` declaration: never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  (this spec's title) when done.

## Conventions this lane relies on (everything needed is here)
**C1, the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when
the forge answered; otherwise `value` is the empty value (`False`, or `""` for
`fork_clone_url`) and `problem` is one sentence. No verb raises. A verb a forge has no equivalent
for answers the empty value plus `NotSupported(kind, verb, reason).problem`, whose text is
`f"{kind.value} does not support {verb}: {reason}"` (`ForgeKind.GITLAB.value` is `"gitlab"`);
never silently approximate it.

**C2, GitHub argv fidelity.** The GitHub argv is today's call site's, byte for byte. `[scope]` is
`["--repo", self.repository]` when bound and nothing otherwise, right after the subcommand's
positional argument (`pr ready 5 [scope]`, `pr comment 5 [scope] --body …`). An `api` path uses
`{R}` from `repository_name()` and carries no `--repo`. Every call runs with `cwd=self.root`.

**Helpers already on the branch (do not re-add them):**
- `GitHubForge._scoped(self, head: list[str], tail: list[str]) -> list[str]` =
  `head + (["--repo", self.repository] if self.repository else []) + tail`.
- `GitHubForge._run(self, args: Sequence[str], *, stdin: str | None = None) ->
  tuple[subprocess.CompletedProcess[str] | None, str]`: the process and `""`, or `None` and
  ``"the GitHub CLI (`<executable>`) is not installed"``.
- `GitHubForge._failed(run, label: str, *, with_stdout: bool = False) -> str` (static):
  `(run.stderr or (run.stdout if with_stdout else "") or "").strip()`, or
  ``f"`{label}` exited {run.returncode}"`` when that is empty.
- `GitHubForge.repository_name(self) -> tuple[str, str]`: the bound `self.repository`, else a
  non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner` read through `_read` (a failure
  there is `"gh repo view --json nameWithOwner: <stderr>"`).
- `GH_DEFAULT_HOST = "github.com"` at the top of `forge_github.py`.
- `ForgejoForge` / `GitLabForge`: `_repository()` = `quote(self.repository, safe="/")`,
  `_project()` = `quote(self.repository, safe="")`; field `host` (defaults `"forgejo.local"` /
  `"gitlab.com"`, split-332-2) and last field `sleep` (split-334-3). `json`, `Any` and `field`
  are already imported in both modules.
- Transports: `survey([path])` is a GET; `survey([path, METHOD, body])` sends `body`; a 2xx with
  an empty body answers `({}, "")`; a failure answers `([], problem)`.

**C7, tests.** 100% line and branch coverage of all of `vibey_gh`; focused runs need `--no-cov`.

**C8, the formatter trap.** black + isort and root `ruff format` must both be clean: lines at or
under 100 columns (95 for nested calls); bind long expected values to a local before the
`assert`; no implicit string concatenation; multi-line calls one argument per line with a
trailing comma; no backslash continuations. If they fight, restructure the line.

**C9, the big files.** Append with a heredoc, delete with an exact `edit_file`, run black once,
read only slices, never rewrite a module.

**Depends on:** split-335-1-create-edit-merge
- split-335-1-create-edit-merge: the reshaped `# --- Mutations ---` block, `ForgeKind`/`NotSupported` imported in `forge_gitlab.py`, and `test/test_forge_adapters.py` already free of the old update/merge assertions.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
