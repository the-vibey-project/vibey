<!-- split of #336: child 2 of 4; audit: issue-audit/updates/336.md -->
## Title
feat(gh): the forge adapter comments on an issue and edits a comment

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`, `vibey_gh/config.py:288`), and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Three places still write comments with raw `gh`: the shared state comment creates one with `[subject, "comment", N, "--repo", R, "--body", B]` (`vibey_gh/github_state.py:95-98`) and edits one through REST when it carries a `databaseId` (`github_state.py:99-110`) or through a GraphQL `updateIssueComment` mutation when it carries only a node ID (`github_state.py:111-132`, mutation text at `:117-120`); conversation answers with `gh issue comment N --repo R --body B` in `cfg.root` (`vibey_gh/conversation.py:414-431`). The REST/GraphQL split must live inside the GitHub adapter so a Forgejo or GitLab repository gets its own edit route. vibey-gh ADR 0001: a verb arrives with its first caller (parts 4 and 5 of the wave) and answers `(value, problem)`.

This is child lane 2 of 4 of part 0e of the forge-adapter wave. Every path below is relative to `src/vibey_tools/gh/` (package `vibey_gh`) unless it starts with `src/`.

## Required behaviour
1. `vibey_gh/interfaces/forge_adapter_interface.py` gains, at the end of the `# --- Issues ---` block that `split-336-1-issue-reads` added, two declarations with one-line docstrings, and adds `from collections.abc import Mapping` to its imports:
   - `comment_on_issue(self, number: int, body: str) -> tuple[bool, str]` — "Add a comment to an issue, and a problem."
   - `update_comment(self, comment: Mapping[str, Any], body: str) -> tuple[bool, str]` — "Replace the body of a comment this adapter read, and a problem."
2. `comment_on_issue`, on each adapter:
   - Forgejo: `_, problem = self.transport.survey([f"repos/{R}/issues/{number}/comments", "POST", json.dumps({"body": body})], cwd=self.root)`; a problem → `(False, problem)`; else `(True, "")`.
   - GitLab: the same with the path `f"projects/{P}/issues/{number}/notes"`.
   - GitHub: `run, problem = self._run(self._scoped(["issue", "comment", str(number)], ["--body", body]))`. `run is None` → `(False, problem)`; `run.returncode == 0` → `(True, "")`; else `(False, self._failed(run, "gh issue comment"))`. Bound, this is `issue comment 7 --repo o/r --body B`, byte for byte the argv of `github_state.py:97` (with `subject="issue"`) and `conversation.py:417-426`.
3. `update_comment`, on each adapter. `comment` is a mapping as the adapter's own reads return it.
   - Forgejo: `comment_id = str(comment.get("id") or "")`; unless `comment_id.isdigit()` → `(False, "comment has no ID")` with no request. Else `survey([f"repos/{R}/issues/comments/{comment_id}", "PATCH", json.dumps({"body": body})], cwd=self.root)`; a problem → `(False, problem)`; else `(True, "")`.
   - GitLab: `note_id = str(comment.get("id") or "")`, `kind = str(comment.get("noteable_type") or "")`, `iid = str(comment.get("noteable_iid") or "")`; if any of the three is empty → `(False, "comment has no ID")` with no request. The collection is `"merge_requests"` when `kind == "MergeRequest"`, else `"issues"`; then `survey([f"projects/{P}/{collection}/{iid}/notes/{note_id}", "PUT", json.dumps({"body": body})], cwd=self.root)`; a problem → `(False, problem)`; else `(True, "")`.
   - GitHub (`github_state.py:99-132` moved in):
     - when `comment.get("databaseId") is not None`: `name, problem = self.repository_name()`; a problem → `(False, problem)`; `args = ["api", f"repos/{name}/issues/comments/{comment['databaseId']}", "--method", "PATCH", "--field", f"body={body}"]`;
     - else `node = comment.get("id")`; a falsy `node` → `(False, "comment has no ID")` with no `gh` call; else `args = ["api", "graphql", "--field", f"query={UPDATE_COMMENT_MUTATION}", "--field", f"id={node}", "--field", f"body={body}"]`;
     - `run, problem = self._run(args)`; `run is None` → `(False, problem)`; `run.returncode == 0` → `(True, "")`; else ``(False, (run.stderr or "").strip() or f"`gh api` exited {run.returncode}")``.
   - `UPDATE_COMMENT_MUTATION` is a new module constant near the top of `forge_github.py`, the text of `github_state.py:117-120` verbatim, written exactly as:
     ```python
     UPDATE_COMMENT_MUTATION = (
         "mutation($id:ID!,$body:String!){updateIssueComment(input:{id:$id,body:$body})"
         "{issueComment{id}}}"
     )
     ```
     (joined it is 96 characters, so it cannot be one literal on one line; both formatters keep this two-literal form).
4. The two GitHub branches reproduce `test/test_gh_transport.py:450-467`'s `REST_EDIT` and `GRAPHQL_EDIT` argv exactly: for a bound adapter (`repository="o/r"`) and `{"databaseId": 9}` the argv is `["api", "repos/o/r/issues/comments/9", "--method", "PATCH", "--field", "body=<B>"]`; for `{"databaseId": None, "id": "IC_node"}` it is `["api", "graphql", "--field", "query=<mutation>", "--field", "id=IC_node", "--field", "body=<B>"]`.
5. No verb raises. No consumer changes: `github_state.py` moves in part 4 (#342) and `conversation.py` in part 5 (#343).

## Where to change
Four source files: the protocol and the three adapters, because one verb is declared once and implemented per forge.
- `vibey_gh/interfaces/forge_adapter_interface.py`: `from collections.abc import Mapping` (isort puts it before `from typing import Any, Protocol, runtime_checkable`) and the two declarations.
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, `vibey_gh/forge_github.py`: append both methods to the end of each file (each adapter class is its module's last statement) with `python3 -c` opening the file in append mode, four-space indented, then run `python -m black --line-length 100 <file>` once. Add `from collections.abc import Mapping` to each of the three (`json` is already imported in the Forgejo and GitLab modules). Read only the slices you need; never rewrite a whole module with `write_file`.
- `vibey_gh/forge_github.py` also gains `UPDATE_COMMENT_MUTATION` near the top, beside the other module constants.
- Test: `test/test_forge_comment_writes.py` (new), starting with the provenance header line copied from `vibey_gh/forge.py:1`.

## Acceptance criteria
- [ ] `test_github_update_comment_is_the_state_comments_rest_or_graphql_edit` pins both argv lists above, bound, and asserts `forge_github.UPDATE_COMMENT_MUTATION` equals the test's own two-literal copy of the mutation.
- [ ] `test_github_comment_on_issue_is_todays_argv` pins `issue comment 7 --body B` unbound and `issue comment 7 --repo o/r --body B` bound, with `cwd == str(tmp_path.resolve())`.
- [ ] Forgejo and GitLab tests assert the exact `(path, METHOD, body)` tuples recorded by `RoutedTransport`, and that `(False, "comment has no ID")` makes no request.
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`; black, isort, mypy, `ruff check` and `ruff format --check` are clean.
- [ ] `git diff --stat` lists only the four source files and the new test file.

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` a module or class attribute, never `mock.patch`, `MagicMock` or `AsyncMock`; `monkeypatch.setenv`/`delenv` are fine.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real `gh` executable put first on `PATH`. `fake_gh.script({" ".join(argv): {"out": "", "err": "", "code": 0}})` keys answers by the space-joined argv (an unscripted argv exits 3 with `no scripted answer`); `fake_gh.invocations()` returns `[{"argv": [...], "cwd": "...", "stdin": None}]`; `fake_gh.forget()` clears the records. A missing client is `GhTransport(executable="gh-not-installed")` passed as `transport=`, whose problem is ``the GitHub CLI (`gh-not-installed`) is not installed``.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py` (`from forge_doubles import RoutedTransport`), built as `RoutedTransport({route: (value, problem), ...})`, where a route is the API path for a GET and `"<path> <METHOD>"` otherwise; a routed answer is returned every time it is asked for, nothing is consumed. Keys are `"<path>"` for a GET and `"<path> <METHOD>"` otherwise; `.calls` records every `args` tuple, so a write is `(path, "POST", body)` and `json.loads(call[2])` gives the payload; an unrouted request answers `([], "no route for <key>")`.

`test/test_forge_comment_writes.py` (define `BODY = "<!-- state:{\"n\":1} -->\ntwo words and \"a quote\""` and the mutation as a local two-literal constant; do not import from another test module):
- `test_forgejo_comment_writes_route_and_send_json`: `comment_on_issue(7, BODY)` records `("repos/o/r/issues/7/comments", "POST", json.dumps({"body": BODY}))` and answers `(True, "")`; `update_comment({"id": "41"}, BODY)` records `("repos/o/r/issues/comments/41", "PATCH", json.dumps({"body": BODY}))`; `update_comment({"id": "IC_x"}, BODY)` and `update_comment({}, BODY)` answer `(False, "comment has no ID")` and add no call.
- `test_gitlab_comment_writes_route_by_noteable_type`: `comment_on_issue(7, BODY)` records `("projects/o%2Fr/issues/7/notes", "POST", json.dumps({"body": BODY}))`; a note `{"id": "5", "noteable_type": "Issue", "noteable_iid": 7}` PUTs `projects/o%2Fr/issues/7/notes/5`; `{"id": "6", "noteable_type": "MergeRequest", "noteable_iid": 3}` PUTs `projects/o%2Fr/merge_requests/3/notes/6`; a note missing `noteable_iid` answers `(False, "comment has no ID")` with no call.
- `test_github_comment_on_issue_is_todays_argv`: unbound and bound argv as in the acceptance criteria; rc 1 with stderr `"boom\n"` → `(False, "boom")`; rc 1 with no output → ``(False, "`gh issue comment` exited 1")``.
- `test_github_update_comment_is_the_state_comments_rest_or_graphql_edit`: bound `GitHubForge(root=tmp_path, repository="o/r")`; `{"databaseId": 9}` runs the REST argv; `{"databaseId": None, "id": "IC_node"}` runs the GraphQL argv; unbound with `monkeypatch.setenv("GH_REPO", "o/r")` gives the same REST argv; `{"databaseId": None}` → `(False, "comment has no ID")` and `fake_gh.invocations() == []`; the REST argv scripted with `{"err": "HTTP 422\n", "code": 1}` → `(False, "HTTP 422")`; scripted with `{"code": 1}` and no output → ``(False, "`gh api` exited 1")``.
- `test_every_comment_write_passes_a_problem_through`: parametrised over forge × verb. Forgejo and GitLab over an empty `RoutedTransport()`, exactly: Forgejo `comment_on_issue(7, BODY)` → `(False, "no route for repos/o/r/issues/7/comments POST")` and `update_comment({"id": "41"}, BODY)` → `(False, "no route for repos/o/r/issues/comments/41 PATCH")`; GitLab `comment_on_issue(7, BODY)` → `(False, "no route for projects/o%2Fr/issues/7/notes POST")` and `update_comment({"id": "5", "noteable_type": "Issue", "noteable_iid": 7}, BODY)` → `(False, "no route for projects/o%2Fr/issues/7/notes/5 PUT")`. GitHub, bound, with the missing client: `(False, "the GitHub CLI (`gh-not-installed`) is not installed")` for `comment_on_issue`, for `update_comment({"databaseId": 9}, BODY)` and for `update_comment({"id": "IC_node"}, BODY)`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_comment_writes.py test/test_forge_issue_reads.py test/test_forge_adapters.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --check --line-length 100 vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the files named under "Where to change" and the new test file
```
Nothing here is platform-specific: the same commands prove the change on macOS (the lane host) and on Linux (CI's `tools` job), per 8.h.

## Out of scope
- The issue reads (child 1, merged), the review comment and review threads (children 3 and 4).
- `github_state.py`, `conversation.py`, `issue_automation.py` and their tests: parts 4 and 5 of the wave. `test/test_gh_transport.py` is read for its argv, never edited.
- `comment_on_change_request` (#335's lane): unchanged.
- `test/conftest.py`, `test/forge_doubles.py`, and this repository's `.vibey-gh.toml` (never write or change its `[platform]` declaration).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when the forge answered; otherwise `value` is the empty value for its type (`False` here) and `problem` is one sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable output. Forgejo is the default adapter (8.b): implement and test it first.

**C2 — GitHub argv fidelity.** Each GitHub verb runs today's `gh` argv byte for byte. `self._scoped(head, tail)` returns `head + ["--repo", self.repository] + tail` when the adapter is bound (`self.repository` non-empty) and `head + tail` otherwise. `{R}` in a GitHub API path is the name `self.repository_name()` answers: the bound name, else a non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner`; its problem is returned at once. Every call runs with `cwd=self.root`.

**Helpers already on the branch (from the lanes this one depends on):**
- `GitHubForge._run(args, *, stdin=None) -> tuple[subprocess.CompletedProcess[str] | None, str]`: the completed run and `""`, or `None` and ``the GitHub CLI (`<executable>`) is not installed``.
- `GitHubForge._failed(run, label, *, with_stdout=False) -> str` (static): `(run.stderr or (run.stdout if with_stdout else "") or "").strip()` or ``f"`{label}` exited {run.returncode}"``.
- `repository_name() -> tuple[str, str]` on every adapter.
- Forgejo `{R}` is `self._repository()` (`quote(self.repository, safe="/")`); GitLab `{P}` is `self._project()` (`quote(self.repository, safe="")`). A mutation is `self.transport.survey([path, METHOD, json.dumps(payload)], cwd=self.root)`; a 2xx answer with an empty body reads as `({}, "")`.
- The comment mappings the adapters read (`split-336-1-issue-reads`): Forgejo `{"id": "<digits>", "url", "body", "author", "createdAt"}`, GitLab `{"id": "<digits>", "url", "body", "author", "createdAt", "noteable_type", "noteable_iid"}`, GitHub as `gh` returns it (`databaseId` and/or node `id`).

**C7 — tests.** 100% line and branch coverage of all of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`); focused runs need `--no-cov`; the whole suite runs before committing. No test leaves the machine. Never touch `test/conftest.py`.

**C8 — the formatter trap.** Both `black --line-length 100` + `isort` (profile black, `combine_as_imports`) and the root `ruff format` check the tenant, and they disagree on some wraps. Keep lines at or under 100 columns (95 with nested calls); bind a long expected value to a local before the `assert`; no implicit string concatenation that would fit on one line (the mutation does not fit, which is why it stays two literals); multi-line calls take one argument per line with a trailing comma; no backslash continuations. If the formatters fight, restructure the line. `from forge_doubles import RoutedTransport` sits in the third-party block after `import pytest`.

**Depends on:** split-336-1-issue-reads
- split-336-1-issue-reads: the `# --- Issues ---` block in the protocol, the comment mappings its reads return, and the adapter files as it leaves them (this lane appends after its methods). Through it, every wave-1 lane before it (`_scoped`, `_run`, `_failed`, `repository_name`, `RoutedTransport`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
