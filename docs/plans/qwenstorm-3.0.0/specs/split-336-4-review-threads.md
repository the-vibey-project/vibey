<!-- split of #336: child 4 of 4; audit: issue-audit/updates/336.md -->
## Title
feat(gh): the forge adapter pages a branch's review threads

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`, `vibey_gh/config.py:288`), and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Before a flatten orphans review comments, `Flattener._review_threads` (`vibey_gh/flatten.py:609-752`) asks GitHub's GraphQL API for the unresolved threads on the branch's open pull request through raw `gh`: it resolves the repository with `github_state.repository()` on the first page (`flatten.py:659`), sends `gh api graphql --raw-field query=<_THREADS_QUERY> --raw-field owner= --raw-field name= --raw-field branch= [--raw-field after=]` (`flatten.py:657-671`, query at `flatten.py:131,152-169`), and walks the answer's envelope (`flatten.py:691-736`). This lane adds the page verb every forge can answer in that same envelope, so part 6 (`split-344-2-flatten`) can move flatten off `gh` without touching its walk. vibey-gh ADR 0001: a verb arrives with its first caller and answers `(value, problem)`.

This is child lane 4 of 4 of part 0e of the forge-adapter wave. Every path below is relative to `src/vibey_tools/gh/` (package `vibey_gh`) unless it starts with `src/`.

## Required behaviour
1. `vibey_gh/interfaces/forge_adapter_interface.py` gains, at the end of the `# --- Issues ---` block, `review_thread_page(self, head_ref: str, cursor: str) -> tuple[dict[str, Any], str]` — "One page of the review threads on the open change requests whose head is `head_ref`, as the GitHub GraphQL envelope, and a problem." The answer is the envelope flatten walks:
   ```
   {"data": {"repository": {"pullRequests": {"nodes": [
       {"number": int,
        "reviewThreads": {"pageInfo": {"hasNextPage": bool, "endCursor": str | None},
                          "nodes": [{"isResolved": bool,
                                     "comments": {"nodes": [{"path", "line", "originalLine",
                                                             "body", "author": {"login"}}]}}]}}]}}},
    "errors"?: [...]}
   ```
   On a problem the value is `{}`. `cursor` is `""` for the first page.
2. GitHub (`vibey_gh/forge_github.py`):
   - Two new module constants near the top, beside the other module constants, copied verbatim from `flatten.py:131` and `flatten.py:152-169` with the names changed (part 6 deletes flatten's copy):
     ```python
     REVIEW_THREADS_PER_PAGE = 100
     REVIEW_THREADS_QUERY = """
     query($owner:String!,$name:String!,$branch:String!,$after:String){
       repository(owner:$owner,name:$name){
         pullRequests(headRefName:$branch,states:OPEN,first:2){
           nodes{
             number
             reviewThreads(first:PER_PAGE,after:$after){
               pageInfo{hasNextPage endCursor}
               nodes{
                 isResolved
                 comments(first:1){nodes{path line originalLine body author{login}}}
               }
             }
           }
         }
       }
     }
     """.replace("PER_PAGE", str(REVIEW_THREADS_PER_PAGE))
     ```
     Copy the query's lines from `flatten.py:152-169` itself (read them with `sed -n '152,169p' vibey_gh/flatten.py`): in the module they start at column 0 and nest two spaces per level, and the block above is only indented because it sits in this list. Above them, a comment of your own saying that `pullRequests(first:2)` is how a second open change request on the same head is detected, and that `pageInfo` is what lets the caller walk every page.
   - `review_thread_page`: `name, problem = self.repository_name()`; a problem → `({}, problem)`. `owner, _, repo = name.partition("/")`. `args = ["api", "graphql", "--raw-field", f"query={REVIEW_THREADS_QUERY}", "--raw-field", f"owner={owner}", "--raw-field", f"name={repo}", "--raw-field", f"branch={head_ref}"]`, plus `["--raw-field", f"after={cursor}"]` only when `cursor` is non-empty. `value, problem = self.transport.survey(args, cwd=self.root)` (the transport's `survey`, **not** `_read`, so a missing client reads ``the GitHub CLI (`gh`) is not installed`` and a failed call reads ``"`gh api graphql` failed: <last stderr line>"``, the texts flatten reports today); a problem → `({}, problem)`; a list → ``({}, "`gh api graphql` returned a JSON list where an object was expected")``; a dict → `(value, "")`.
3. Forgejo (`vibey_gh/forge_forgejo.py`), `cursor` ignored (Forgejo answers every thread on one page):
   - `pulls, problem = self._pages(f"repos/{R}/pulls?state=open")`; a problem → `({}, problem)`.
   - `numbers = tuple(sorted(int(pull["number"]) for pull in pulls if (pull.get("head") or {}).get("ref") == head_ref))[:2]` (the lowest two).
   - No numbers → `(ForgejoFacts().thread_page((), []), "")`.
   - Else `comments, problem = self._review_comments(numbers[0])` (the helper `split-336-3-review-comment` added: every review comment of that pull, all reviews in order); a problem → `({}, problem)`; else `(ForgejoFacts().thread_page(numbers, comments), "")`.
4. `ForgejoFacts.thread_page(self, numbers: tuple[int, ...], comments: list[dict[str, Any]]) -> dict[str, Any]` (pure):
   - no `numbers` → `{"data": {"repository": {"pullRequests": {"nodes": []}}}}`;
   - else sort `comments` by `(str(c.get("created_at") or ""), int(c.get("id") or 0))`, then group them, in that order, by `(str(c.get("path") or ""), c.get("position") or c.get("original_position"))`;
   - each group is one thread: `isResolved` is true when any comment in the group has a non-`None` `resolver`; its single comment node is the group's earliest comment `first`: `{"path": str(first.get("path") or ""), "line": first.get("position"), "originalLine": first.get("original_position"), "body": str(first.get("body") or ""), "author": {"login": str(user.get("login") or user.get("username") or "")}}` with `user = first.get("user") or {}`;
   - the answer is `{"data": {"repository": {"pullRequests": {"nodes": nodes}}}}` where `nodes[0] = {"number": numbers[0], "reviewThreads": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": threads}}` and, when there is a second number, `nodes[1] = {"number": numbers[1], "reviewThreads": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}}` (a sibling with empty threads, which flatten reports as a partial check).
5. GitLab (`vibey_gh/forge_gitlab.py`), `cursor` ignored:
   - `requests, problem = self._pages(f"projects/{P}/merge_requests?state=opened&source_branch={quote(head_ref, safe='')}")`; a problem → `({}, problem)`.
   - `numbers = tuple(sorted(int(request["iid"]) for request in requests))[:2]`.
   - No numbers → `(GitLabFacts().thread_page((), []), "")`.
   - Else `discussions, problem = self._pages(f"projects/{P}/merge_requests/{numbers[0]}/discussions")`; a problem → `({}, problem)`; else `(GitLabFacts().thread_page(numbers, discussions), "")`.
6. `GitLabFacts.thread_page(self, numbers: tuple[int, ...], discussions: list[dict[str, Any]]) -> dict[str, Any]` (pure), with the same envelope, `pageInfo` and sibling rules as item 4:
   - a discussion is a thread when at least one of its notes has `resolvable` true; other discussions are skipped;
   - `isResolved` is true when every resolvable note has `resolved` true;
   - its comment node is built from the discussion's first note `first`, with `position = first.get("position") or {}`: `{"path": str(position.get("new_path") or position.get("old_path") or ""), "line": position.get("new_line"), "originalLine": position.get("old_line"), "body": str(first.get("body") or ""), "author": {"login": str(author.get("username") or "")}}` with `author = first.get("author") or {}`.
7. `ForgejoFactsInterface` and `GitLabFactsInterface` declare `thread_page` with the signatures above and one-line docstrings.
8. No verb raises. No consumer changes: `flatten.py` moves in `split-344-2-flatten`.

## Where to change
Eight source files: the protocol, three adapters, and both facts classes with their interfaces, because the page is declared once, answered per forge, and the Forgejo and GitLab translations are pure methods beside the earlier ones. Each edit is small; add, never rewrite.
- `vibey_gh/interfaces/forge_adapter_interface.py`: the declaration.
- `vibey_gh/forge_github.py`: the two constants near the top and `review_thread_page` appended.
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`: `review_thread_page` appended (`quote` is already imported in the GitLab module).
- `vibey_gh/forge_forgejo_facts.py`, `vibey_gh/interfaces/forge_forgejo_facts_interface.py`, `vibey_gh/forge_gitlab_facts.py`, `vibey_gh/interfaces/forge_gitlab_facts_interface.py`: `thread_page`. A private helper that builds the envelope from `(numbers, threads)` is fine inside each facts class.
- Append methods to the end of each adapter file (each adapter class is its module's last statement) with `python3 -c` opening the file in append mode, four-space indented, then run `python -m black --line-length 100 <file>` once. Read only the slices you need; never rewrite a whole module with `write_file`.
- Test: `test/test_forge_review_threads.py` (new), starting with the provenance header line copied from `vibey_gh/forge.py:1`.

## Acceptance criteria
- [ ] `test_github_thread_page_is_flattens_query_and_reports_like_flatten`: the first page's argv has no `after=`; the second (cursor `"c1"`) ends `"--raw-field", "after=c1"`; `forge_github.REVIEW_THREADS_QUERY` equals the test's own literal of the query with `first:100`.
- [ ] `test_forgejo_thread_page_groups_comments_and_marks_resolution` covers none, one and two open pulls on the head.
- [ ] `test_gitlab_thread_page_reads_resolvable_discussions` covers none, one and two merge requests.
- [ ] `python -m pytest -q` passes with 100% line and branch coverage of `vibey_gh`; black, isort, mypy, `ruff check` and `ruff format --check` are clean; `test/test_flatten.py` still passes unmodified.
- [ ] `git diff --stat` lists only the eight source files and the new test file.

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` a module or class attribute, never `mock.patch`, `MagicMock` or `AsyncMock`; `monkeypatch.setenv`/`delenv` are fine.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real `gh` executable first on `PATH`; `fake_gh.script({" ".join(argv): {"out": "...", "err": "...", "code": 0}})` keys answers by the space-joined argv (the query's newlines are part of the key, which is fine); `fake_gh.invocations()` returns `[{"argv": [...], "cwd": "...", "stdin": None}]`; `fake_gh.forget()` clears the records. A missing client is `transport=GhTransport(executable="gh-not-installed")`.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py` (`from forge_doubles import RoutedTransport`), built as `RoutedTransport({route: (value, problem), ...})`, where a route is the API path for a GET and `"<path> <METHOD>"` otherwise; a routed answer is returned every time it is asked for, nothing is consumed: keys `"<path>"` for a GET; `.calls` records every `args` tuple; an unrouted request answers `([], "no route for <key>")`. Forgejo `_pages` appends `?`/`&` then `page=N&limit=50` and stops only at an **empty** page (route each listing's page 2 as `([], "")`); GitLab `_pages` appends `page=N&per_page=100` and stops at a page shorter than 100.

`test/test_forge_review_threads.py` (write the expected query as a local triple-quoted literal with `first:100`; do not import it from `flatten`, whose copy part 6 deletes):
- `test_github_thread_page_is_flattens_query_and_reports_like_flatten`: `GitHubForge(root=tmp_path, repository="o/r")`; `review_thread_page("feat/thing", "")` runs `["api", "graphql", "--raw-field", f"query={QUERY}", "--raw-field", "owner=o", "--raw-field", "name=r", "--raw-field", "branch=feat/thing"]` in `str(tmp_path.resolve())` and answers the scripted envelope; `review_thread_page("feat/thing", "c1")` runs the same argv plus `["--raw-field", "after=c1"]`; the scripted answer `[]` → ``({}, "`gh api graphql` returned a JSON list where an object was expected")``; rc 1 with stderr `"HTTP 401\nBad credentials\n"` → ``({}, "`gh api graphql` failed: Bad credentials")``; the missing client → ``({}, "the GitHub CLI (`gh-not-installed`) is not installed")``; unbound with `monkeypatch.setenv("GH_REPO", "o/r")` runs the same argv; unbound with `GH_REPO` removed and `gh repo view` unscripted answers `{}` and a non-empty problem, and no `graphql` invocation is made.
- `test_forgejo_thread_page_groups_comments_and_marks_resolution`: open pulls `[{"number": 5, "head": {"ref": "feat/thing"}}, {"number": 3, "head": {"ref": "feat/thing"}}, {"number": 9, "head": {"ref": "other"}}]`; reviews of #3 `[{"id": 11}, {"id": 12}]`; `repos/o/r/pulls/3/reviews/11/comments` answers `[{"id": 101, "path": "a.py", "position": 3, "original_position": 3, "created_at": "2026-09-01T10:00:00Z", "resolver": None, "user": {"login": "alice"}, "body": "first"}, {"id": 102, "path": "a.py", "position": 3, "original_position": 3, "created_at": "2026-09-01T10:05:00Z", "resolver": {"login": "bob"}, "user": {"login": "bob"}, "body": "done"}]`; `repos/o/r/pulls/3/reviews/12/comments` answers `[{"id": 103, "path": "b.py", "position": None, "original_position": 7, "created_at": "2026-09-01T09:00:00Z", "resolver": None, "user": {"username": "carol"}, "body": "outdated"}]`. `review_thread_page("feat/thing", "")` answers the envelope with `nodes[0]["number"] == 3`, threads exactly `[{"isResolved": False, "comments": {"nodes": [{"path": "b.py", "line": None, "originalLine": 7, "body": "outdated", "author": {"login": "carol"}}]}}, {"isResolved": True, "comments": {"nodes": [{"path": "a.py", "line": 3, "originalLine": 3, "body": "first", "author": {"login": "alice"}}]}}]` (in that order: groups follow their earliest comment), `pageInfo == {"hasNextPage": False, "endCursor": None}`, and `nodes[1] == {"number": 5, "reviewThreads": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}}`; the same call with cursor `"c1"` answers the same. With only #3 open: one node. With no pull on the head: `{"data": {"repository": {"pullRequests": {"nodes": []}}}}` and no reviews request.
- `test_gitlab_thread_page_reads_resolvable_discussions`: merge requests `projects/o%2Fr/merge_requests?state=opened&source_branch=feat%2Fthing&page=1&per_page=100` → `[{"iid": 4}, {"iid": 2}]`; `projects/o%2Fr/merge_requests/2/discussions?page=1&per_page=100` → an individual non-resolvable note (skipped); a discussion of two resolvable notes both `resolved` (first note body `"rename this"`, author `{"username": "alice"}`, `position` `{"new_path": "a.py", "new_line": 3, "old_line": 2}`; second note body `"done"`, author `bob`); a discussion of one resolvable unresolved note (body `"and this"`, author `alice`, `position` `{"new_path": None, "old_path": "gone.py", "new_line": None, "old_line": 9}`). The answer is `nodes[0]["number"] == 2` with threads exactly `[{"isResolved": True, "comments": {"nodes": [{"path": "a.py", "line": 3, "originalLine": 2, "body": "rename this", "author": {"login": "alice"}}]}}, {"isResolved": False, "comments": {"nodes": [{"path": "gone.py", "line": None, "originalLine": 9, "body": "and this", "author": {"login": "alice"}}]}}]`, then the sibling `4` with empty threads. Also none (`[]` → the empty envelope) and one.
- `test_every_thread_page_read_passes_a_problem_through`: parametrised: Forgejo with an empty `RoutedTransport` (value `{}`, problem starts with `"no route for "`); Forgejo whose pulls listing answers and whose reviews listing does not (value `{}`, problem starts with `"no route for "`); GitLab with an empty `RoutedTransport`; GitLab whose merge requests answer and whose discussions do not.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_review_threads.py test/test_forge_review_comment.py test/test_forge_facts.py test/test_flatten.py
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
- `vibey_gh/flatten.py` and `test/test_flatten.py`: `split-344-2-flatten` moves flatten onto this verb and deletes `_THREADS_QUERY`/`_THREADS_PER_PAGE` there. Do not touch flatten here.
- Issue reads, comment writes and the review comment (children 1-3, merged); `ForgejoForge._review_comments` is reused, not changed.
- `test/conftest.py`, `test/forge_doubles.py`, and this repository's `.vibey-gh.toml` (never write or change its `[platform]` declaration).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when the forge answered; otherwise `value` is the empty value for its type (`{}` here) and `problem` is one sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable output. Forgejo is the default adapter (8.b): implement and test it first.

**C2 — GitHub.** `{R}`/the owner and name come from `self.repository_name()`: the bound name, else a non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner`; its problem is returned at once. The GraphQL call uses `--raw-field`, not `--field`, because the variables are `String`s and `--field` would coerce a numeric branch or cursor. Every call runs with `cwd=self.root`. `GhTransport.survey(args, *, cwd)` labels its problems with `" ".join((executable, *args[:2]))`, here `gh api graphql`: a missing client → ``the GitHub CLI (`gh`) is not installed``; a non-zero exit → ``"`gh api graphql` failed: <last line of stderr, else stdout, else 'no output'>"``; unparseable output → ``"`gh api graphql` returned output that is not JSON"``; a JSON list or object is answered as is.

**C5 — the envelope is flatten's schema.** Flatten's walk reads `errors`, `data.repository.pullRequests.nodes`, each node's `number` and `reviewThreads.{pageInfo, nodes}`, each thread's `isResolved` and its first comment's `path`, `line`, `originalLine`, `body` and `author.login` (every one nullable). Keeping GitHub's key spellings is the wave's deliberate, transitional schema, so the walk stays untouched. Forgejo and GitLab always answer one page (`hasNextPage: False`, `endCursor: None`).

**Helpers already on the branch (from the lanes this one depends on):** `repository_name()` on every adapter; `ForgejoForge._pages` / `GitLabForge._pages(path, *, most: int | None = None) -> tuple[list[dict[str, Any]], str]` (`([], problem)` when a page cannot be read); `ForgejoForge._review_comments(number) -> tuple[list[dict[str, Any]], str]` (every review comment on the pull, one GET per review, from `split-336-3-review-comment`); Forgejo `{R}` = `self._repository()`, GitLab `{P}` = `self._project()`; `ForgejoFacts` / `GitLabFacts` are pure classes subclassing their `@runtime_checkable` Protocol interfaces, so a new method must be declared on the interface in the same change.

**C7 — tests.** 100% line and branch coverage of all of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`); focused runs need `--no-cov`; the whole suite runs before committing. No test leaves the machine. Never touch `test/conftest.py`.

**C8 — the formatter trap.** Both `black --line-length 100` + `isort` (profile black, `combine_as_imports`) and the root `ruff format` check the tenant, and they disagree on some wraps. Keep lines at or under 100 columns (95 with nested calls); bind a long expected value (the envelopes) to a local before the `assert`; no implicit string concatenation that would fit on one line; multi-line calls take one argument per line with a trailing comma; no backslash continuations. If the formatters fight, restructure the line. `from forge_doubles import RoutedTransport` sits in the third-party block after `import pytest`.

**Depends on:** split-336-3-review-comment
- split-336-3-review-comment: `ForgejoForge._review_comments`, and the adapter, protocol and facts files as it leaves them (this lane appends after its methods). Through it and children 1-2: the `# --- Issues ---` block and every wave-1 helper (`repository_name`, `_pages`, `RoutedTransport`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
