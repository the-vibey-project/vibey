<!-- split of #336: child 3 of 4; audit: issue-audit/updates/336.md -->
## Title
feat(gh): the forge adapter reads one review comment

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`, `vibey_gh/config.py:288`), and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`). When a mention names a comment ID the thread does not hold, conversation looks it up as a pull-request review comment through raw `gh`: `gh api repos/R/pulls/comments/ID` (`vibey_gh/conversation.py:202-217`), then refuses a comment from another pull request by checking the last path segment of `pull_request_url` (`conversation.py:213-215`), and renders `path`, `line` or `original_line`, and `diff_hunk` (`conversation.py:343-357`). This lane adds the verb and the neutral mapping those lines read, so part 5 (#343) can move conversation off `gh`. vibey-gh ADR 0001: a verb arrives with its first caller and answers `(value, problem)`.

This is child lane 3 of 4 of part 0e of the forge-adapter wave. Every path below is relative to `src/vibey_tools/gh/` (package `vibey_gh`) unless it starts with `src/`.

## Required behaviour
1. `vibey_gh/forge.py` gains, after `ISSUE_FACT_KEYS`/`SUBJECT_FACT_KEYS`, and in `__all__` directly after `"ProtectedRef"` (ASCII order, before `"SUBJECT_FACT_KEYS"`):
   ```python
   REVIEW_COMMENT_KEYS = (
       "id",
       "body",
       "user",
       "path",
       "line",
       "original_line",
       "diff_hunk",
       "pull_request_url",
   )
   ```
   Values: `id` as the forge gives it (an int on all three); `body`, `path`, `diff_hunk`, `pull_request_url` str (`""` when absent); `user` is `{"login": str}`; `line` and `original_line` are ints or `None`. The last path segment of `pull_request_url` is the change-request number, which the caller checks (`conversation.py:213-215`).
2. `ForgejoFacts` gains `review_comment(self, raw: dict[str, Any]) -> dict[str, Any]` answering exactly the `REVIEW_COMMENT_KEYS` keys: `id=raw.get("id")`, `body=str(raw.get("body") or "")`, `user={"login": str(user.get("login") or user.get("username") or "")}` with `user = raw.get("user") or {}`, `path=str(raw.get("path") or "")`, `line=raw.get("position")`, `original_line=raw.get("original_position")`, `diff_hunk=str(raw.get("diff_hunk") or "")`, `pull_request_url=str(raw.get("pull_request_url") or "")` (Forgejo's `PullReviewComment` carries every one of these fields).
3. `GitLabFacts` gains `review_comment(self, note: dict[str, Any], pull_request_url: str) -> dict[str, Any]` answering exactly the `REVIEW_COMMENT_KEYS` keys: `id=note.get("id")`, `body=str(note.get("body") or "")`, `user={"login": str(author.get("username") or "")}` with `author = note.get("author") or {}`, `path=str(position.get("new_path") or "")`, `line=position.get("new_line")`, `original_line=position.get("old_line")` with `position = note.get("position") or {}`, `diff_hunk=""` (a GitLab note carries no hunk), and `pull_request_url` as given.
4. `ForgejoFactsInterface` and `GitLabFactsInterface` (`vibey_gh/interfaces/forge_forgejo_facts_interface.py`, `vibey_gh/interfaces/forge_gitlab_facts_interface.py`) declare `review_comment` with the signatures above and one-line docstrings.
5. `vibey_gh/interfaces/forge_adapter_interface.py` gains, at the end of the `# --- Issues ---` block, `review_comment(self, number: int, comment_id: str) -> tuple[dict[str, Any] | None, str]` — "One review comment on a change request, keyed by `REVIEW_COMMENT_KEYS`, and a problem." All three adapters implement it:
   - Forgejo: a new private helper `_review_comments(self, number: int) -> tuple[list[dict[str, Any]], str]` answers every review comment on pull `number`: `reviews, problem = self._pages(f"repos/{R}/pulls/{number}/reviews")` (a problem → `([], problem)`); then for each review, in order, **one** GET `path = f"repos/{R}/pulls/{number}/reviews/{review.get('id')}/comments"` through `self.transport.survey([path], cwd=self.root)` (a problem → `([], problem)`; a non-list → `([], f"Forgejo answered {path} with something other than a list")`), collecting the dict items. The review-comments endpoint takes no `page`/`limit` (see Conventions), so it is not walked with `_pages`. `review_comment` then: `comments, problem = self._review_comments(number)`; a problem → `(None, problem)`; the first comment with `str(c.get("id")) == comment_id` → `(ForgejoFacts().review_comment(c), "")`; none → `(None, f"review comment {comment_id} is not on #{number}")`.
   - GitLab: `path = f"projects/{P}/merge_requests/{number}/notes/{comment_id}"`; one GET; a problem → `(None, problem)`; a non-dict → `(None, f"GitLab answered {path} with something other than an object")`; else `(GitLabFacts().review_comment(note, f"https://{self.host}/{self.repository}/-/merge_requests/{number}"), "")`.
   - GitHub: `name, problem = self.repository_name()`; a problem → `(None, problem)`; `value, problem = self._read(["api", f"repos/{name}/pulls/comments/{comment_id}"])` (no `--repo`: an API path names the repository); a problem → `(None, problem)`; a non-dict → ``(None, "`gh api` returned a review comment that is not an object")``; else `(value, "")`. `number` is unused on GitHub because the endpoint is repository-wide and the caller checks `pull_request_url`.
6. No verb raises. No consumer changes (`conversation.py` moves in part 5, #343).

## Where to change
Nine source files, because one verb is declared on the protocol, translated by both facts classes (each with its interface) and implemented on three adapters, and the keys live in `forge.py`. Each edit is small; add, never rewrite.
- `vibey_gh/forge.py`: `REVIEW_COMMENT_KEYS` and `__all__`.
- `vibey_gh/forge_forgejo_facts.py`, `vibey_gh/interfaces/forge_forgejo_facts_interface.py`: `review_comment`.
- `vibey_gh/forge_gitlab_facts.py`, `vibey_gh/interfaces/forge_gitlab_facts_interface.py`: `review_comment`.
- `vibey_gh/interfaces/forge_adapter_interface.py`: the declaration.
- `vibey_gh/forge_forgejo.py` (`review_comment` and `_review_comments`), `vibey_gh/forge_gitlab.py`, `vibey_gh/forge_github.py`: append to the end of each file (each adapter class is its module's last statement) with `python3 -c` opening the file in append mode, four-space indented, then run `python -m black --line-length 100 <file>` once. Read only the slices you need; never rewrite a whole module with `write_file`.
- Test: `test/test_forge_review_comment.py` (new), starting with the provenance header line copied from `vibey_gh/forge.py:1`.

## Acceptance criteria
- [ ] `test_review_comment_mappings_have_exactly_the_schema`: `set(ForgejoFacts().review_comment(raw)) == set(REVIEW_COMMENT_KEYS)` and the same for `GitLabFacts().review_comment(note, url)`.
- [ ] `test_github_review_comment_reads_the_repository_wide_endpoint` pins `["api", "repos/o/r/pulls/comments/31"]` and `cwd == str(tmp_path.resolve())`.
- [ ] `test_forgejo_review_comment_walks_the_pull_requests_reviews` covers found and not found, with the exact not-found text.
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`; black, isort, mypy, `ruff check` and `ruff format --check` are clean.
- [ ] `git diff --stat` lists only the nine source files and the new test file.

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` a module or class attribute, never `mock.patch`, `MagicMock` or `AsyncMock`; `monkeypatch.setenv`/`delenv` are fine.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real `gh` executable put first on `PATH`; `fake_gh.script({" ".join(argv): {"out": "...", "err": "...", "code": 0}})`; `fake_gh.invocations()` returns `[{"argv": [...], "cwd": "...", "stdin": None}]`; an unscripted argv exits 3 with `no scripted answer`. Pin `monkeypatch.setenv("GH_REPO", "o/r")` in every test whose argv contains `repos/{R}` and the adapter is unbound. A missing client is `transport=GhTransport(executable="gh-not-installed")`.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py` (`from forge_doubles import RoutedTransport`), built as `RoutedTransport({route: (value, problem), ...})`, where a route is the API path for a GET and `"<path> <METHOD>"` otherwise; a routed answer is returned every time it is asked for, nothing is consumed: keys `"<path>"` for a GET, `.calls` records every `args` tuple, an unrouted request answers `([], "no route for <key>")`. Forgejo `_pages` appends `?page=N&limit=50` and stops only at an **empty** page, so route `repos/o/r/pulls/7/reviews?page=1&limit=50` and `repos/o/r/pulls/7/reviews?page=2&limit=50` (the second `([], "")`).

`test/test_forge_review_comment.py`:
- `test_review_comment_mappings_have_exactly_the_schema`: the Forgejo mapping of a raw comment `{"id": 31, "body": "b", "user": {"login": "alice"}, "path": "a.py", "position": 3, "original_position": 2, "diff_hunk": "@@ -1 +1 @@", "pull_request_url": "https://forgejo.example/o/r/pulls/7", "resolver": None}` equals `{"id": 31, "body": "b", "user": {"login": "alice"}, "path": "a.py", "line": 3, "original_line": 2, "diff_hunk": "@@ -1 +1 @@", "pull_request_url": "https://forgejo.example/o/r/pulls/7"}`; a GitLab note with `position` `{"new_path": "a.py", "new_line": 4, "old_line": 3}` and one without `position` (path `""`, lines `None`); both key sets equal `set(REVIEW_COMMENT_KEYS)`.
- `test_forgejo_review_comment_walks_the_pull_requests_reviews`: reviews `[{"id": 1}, {"id": 2}]`; `repos/o/r/pulls/7/reviews/1/comments` answers `[{"id": 30, "body": "a", "user": {"login": "bob"}, "path": "b.py", "position": 1, "original_position": 1, "diff_hunk": "", "pull_request_url": "https://forgejo.example/o/r/pulls/7"}]`, `repos/o/r/pulls/7/reviews/2/comments` answers the comment 31 above. `review_comment(7, "31")` answers the mapping and `""`; `review_comment(7, "99")` answers `(None, "review comment 99 is not on #7")`.
- `test_gitlab_review_comment_reads_the_note`: `GitLabForge(root=tmp_path, repository="o/r", transport=routes, host="gitlab.example")`; route `projects/o%2Fr/merge_requests/7/notes/31`; the answer's `pull_request_url == "https://gitlab.example/o/r/-/merge_requests/7"`; a list answer gives `(None, "GitLab answered projects/o%2Fr/merge_requests/7/notes/31 with something other than an object")`.
- `test_github_review_comment_reads_the_repository_wide_endpoint`: unbound with `GH_REPO=o/r` runs `["api", "repos/o/r/pulls/comments/31"]`; bound `repository="x/y"` runs `["api", "repos/x/y/pulls/comments/31"]`; an object answer is returned as is; `[]` → ``(None, "`gh api` returned a review comment that is not an object")``; rc 1 with stderr `"HTTP 404: Not Found\n"` → `(None, "gh api repos/o/r/pulls/comments/31: HTTP 404: Not Found")` (the transport's text, passed through by `_read`).
- `test_every_review_comment_read_passes_a_problem_through`: parametrised over the three forges: Forgejo with an empty `RoutedTransport` (value `None`, problem starts with `"no route for "`), Forgejo whose reviews answer `[{"id": 1}]` and whose `repos/o/r/pulls/7/reviews/1/comments` route answers `([], "Forgejo API error 500: boom")` → `(None, "Forgejo API error 500: boom")`, Forgejo whose same route answers `({}, "")` → `(None, "Forgejo answered repos/o/r/pulls/7/reviews/1/comments with something other than a list")`, GitLab with an empty `RoutedTransport` → `(None, "no route for projects/o%2Fr/merge_requests/7/notes/31")`, and GitHub bound with the missing client → ``(None, "the GitHub CLI (`gh-not-installed`) is not installed")``.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_review_comment.py test/test_forge_facts.py test/test_forge_issue_reads.py
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
- Issue reads and comment writes (children 1 and 2, merged); review threads (child 4, which reuses `ForgejoForge._review_comments`).
- `conversation.py` and its tests: part 5 of the wave.
- `test/conftest.py`, `test/forge_doubles.py`, and this repository's `.vibey-gh.toml` (never write or change its `[platform]` declaration).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when the forge answered; otherwise `value` is the empty value for its type (`None` here) and `problem` is one sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable output. Forgejo is the default adapter (8.b): implement and test it first.

**C2 — GitHub.** `{R}` in a GitHub API path is the name `self.repository_name()` answers: the bound name, else a non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner`; its problem is returned at once. An `api` call carries no `--repo`. Every call runs with `cwd=self.root`.

**Helpers already on the branch (from the lanes this one depends on):**
- `GitHubForge._read(args, *, stdin=None) -> tuple[Any, str]`: decoded JSON and `""`, or `None` and a problem (a missing client → ``the GitHub CLI (`<executable>`) is not installed``; a non-zero exit → the transport's `"gh <args>: <stderr>"`).
- `ForgejoForge._pages(path, *, most: int | None = None) -> tuple[list[dict[str, Any]], str]`: walks `?page=N&limit=50` until an empty page, `([], problem)` when a page cannot be read.
- `ForgejoForge._repository()` (`quote(self.repository, safe="/")`), `GitLabForge._project()` (`quote(self.repository, safe="")`); `GitLabForge.host` (default `"gitlab.com"`) and `self.repository` unquoted build the web URL. A GET is `self.transport.survey([path], cwd=self.root)`.
- `ForgejoFacts` / `GitLabFacts` are pure classes that subclass their `@runtime_checkable` Protocol interfaces; a method added to a class must be declared on its interface in the same change or mypy refuses to instantiate the class.

**Why the review-comments read is one GET, not `_pages`.** Forgejo's `GET /repos/{owner}/{repo}/pulls/{index}/reviews/{id}/comments` declares no `page`/`limit` (Forgejo API 16.0.0-dev swagger at codeberg.org) and returns every comment of the review at once. `_pages` stops only at an empty page, so it would re-read the same comments until its 100-page cap and report a problem. `pulls/{index}/reviews` is paginated and is walked with `_pages`.

**C7 — tests.** 100% line and branch coverage of all of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`); focused runs need `--no-cov`; the whole suite runs before committing. No test leaves the machine. Never touch `test/conftest.py`.

**C8 — the formatter trap.** Both `black --line-length 100` + `isort` (profile black, `combine_as_imports`) and the root `ruff format` check the tenant, and they disagree on some wraps. Keep lines at or under 100 columns (95 with nested calls); bind a long expected value to a local before the `assert`; no implicit string concatenation that would fit on one line; multi-line calls take one argument per line with a trailing comma; no backslash continuations. If the formatters fight, restructure the line. `from forge_doubles import RoutedTransport` sits in the third-party block after `import pytest`.

**Depends on:** split-336-2-comment-writes
- split-336-2-comment-writes: the adapter and protocol files as it leaves them (this lane appends after its methods). Through it and `split-336-1-issue-reads`: `ISSUE_FACT_KEYS`/`SUBJECT_FACT_KEYS` in `forge.py`, the `# --- Issues ---` block, and every wave-1 helper (`_read`, `_pages`, `repository_name`, `host`, `RoutedTransport`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
