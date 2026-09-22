<!-- split of #336: child 1 of 4; audit: issue-audit/updates/336.md -->
## Title
feat(gh): the forge adapter reads an issue, a conversation subject and the open issues

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge (`src/vibey_tools/gh/docs/doctrines.md:138`, `vibey_gh/config.py:288`), and every forge call must go through `ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Issue automation and conversation still read issues with raw `gh`: `vibey_gh/issue_automation.py:265-277` (`issue view N --repo R --json number,title,body,state,author,labels,comments,createdAt,url`), `vibey_gh/issue_automation.py:402-421` (`issue list --repo R --state open --limit N --json <the same fields>`) and `vibey_gh/conversation.py:369-386` (`issue view N --repo R --json number,title,body,state,author,labels,comments,url`). `issue_automation.evaluate` and `conversation` read these as dicts with `gh`'s key spellings, so this lane returns mappings with exactly those keys (the wave's transitional schema), plus the `isPullRequest` flag that `conversation.py:162-174` derives from the URL. vibey-gh ADR 0001: a verb arrives with its first caller and answers `(value, problem)`.

This is child lane 1 of 4 of part 0e of the forge-adapter wave (issues, comments and review threads). Every path below is relative to `src/vibey_tools/gh/` (package `vibey_gh`) unless it starts with `src/`.

## Required behaviour
1. `vibey_gh/forge.py` gains two module constants, placed after the existing `*_FACT_KEYS` constants, each added to `__all__` in ASCII order (`"ISSUE_FACT_KEYS"` directly after `"ForgeUser"`; `"SUBJECT_FACT_KEYS"` directly before `"THREADED_CHANGE_REQUEST_FACT_KEYS"`):
   ```python
   ISSUE_FACT_KEYS = (
       "number",
       "title",
       "body",
       "state",
       "author",
       "labels",
       "comments",
       "createdAt",
       "url",
   )
   SUBJECT_FACT_KEYS = (
       "number",
       "title",
       "body",
       "state",
       "author",
       "labels",
       "comments",
       "url",
       "isPullRequest",
   )
   ```
   Value schema for both: `number` int; `title`, `body`, `createdAt`, `url` str; `state` is `"OPEN"` or `"CLOSED"`; `author` is `{"login": str}`; `labels` is a list of `{"name": str}`; `comments` is a list of the comment mappings the facts classes' existing `comment()` builds (`{"id", "url", "body", "author": {"login"}, "createdAt"}`, GitLab adding `"noteable_type"` and `"noteable_iid"`); `isPullRequest` bool.
2. `ForgejoFacts` (`vibey_gh/forge_forgejo_facts.py`) gains two pure methods:
   - `issue(self, raw: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]` answers exactly the `ISSUE_FACT_KEYS` keys:
     `number=int(raw["number"])`, `title=str(raw.get("title") or "")`, `body=str(raw.get("body") or "")`, `state="OPEN"` if `raw.get("state") == "open"` else `"CLOSED"`, `author={"login": str(user.get("login") or user.get("username") or "")}` with `user = raw.get("user") or {}`, `labels=[{"name": str(label.get("name") or "")} for label in raw.get("labels") or [] if isinstance(label, dict)]`, `comments=[self.comment(item) for item in comments]`, `createdAt=str(raw.get("created_at") or "")`, `url=str(raw.get("html_url") or "")`. It adds `"pull_request": raw["pull_request"]` **only** when `raw.get("pull_request") is not None` (a Forgejo issue that is a pull request carries a non-null `pull_request` object; `issue_automation.evaluate` already skips any issue with that key, `issue_automation.py:224`).
   - `subject(self, raw: dict[str, Any], comments: list[dict[str, Any]]) -> dict[str, Any]` answers exactly the `SUBJECT_FACT_KEYS` keys: the same values as `issue()` for the eight shared keys (no `createdAt`, never `pull_request`), plus `isPullRequest = raw.get("pull_request") is not None`.
3. `GitLabFacts` (`vibey_gh/forge_gitlab_facts.py`) gains `issue(self, raw: dict[str, Any], notes: list[dict[str, Any]]) -> dict[str, Any]` answering exactly the `ISSUE_FACT_KEYS` keys: `number=int(raw["iid"])`, `title=str(raw.get("title") or "")`, `body=str(raw.get("description") or "")`, `state="OPEN"` if `raw.get("state") == "opened"` else `"CLOSED"`, `author={"login": str(author.get("username") or "")}` with `author = raw.get("author") or {}`, `labels=[{"name": str(label)} for label in raw.get("labels") or []]` (GitLab labels are strings), `comments=[self.comment(note) for note in notes if not note.get("system")]` (system notes are dropped), `createdAt=str(raw.get("created_at") or "")`, `url=str(raw.get("web_url") or "")`.
4. `vibey_gh/interfaces/forge_forgejo_facts_interface.py` (`ForgejoFactsInterface`) declares `issue` and `subject`, and `vibey_gh/interfaces/forge_gitlab_facts_interface.py` (`GitLabFactsInterface`) declares `issue`, each with the signature above, a one-line docstring and a `...` body.
5. `vibey_gh/interfaces/forge_adapter_interface.py` gains a new block, appended at the end of the `ForgeAdapterInterface` class body, headed `    # --- Issues ---`, declaring the three verbs below with one-line docstrings. All three adapters implement them.
   - `issue_facts(self, number: int) -> tuple[dict[str, Any] | None, str]` — "An issue's facts, keyed by `ISSUE_FACT_KEYS`, and a problem."
     - Forgejo: GET `repos/{R}/issues/{n}` (`self.transport.survey([path], cwd=self.root)`). A problem → `(None, problem)`; a non-dict answer → `(None, f"Forgejo answered {path} with something other than an object")`. Then GET the comments `repos/{R}/issues/{n}/comments` with **one** `survey` call (Forgejo's issue-comments endpoint takes no `page`/`limit` and returns every comment at once, so it is not walked with `_pages`; see Conventions). A problem → `(None, problem)`; a non-list answer → `(None, f"Forgejo answered {comments_path} with something other than a list")`. Answer `(ForgejoFacts().issue(raw, [c for c in listing if isinstance(c, dict)]), "")`.
     - GitLab: GET `projects/{P}/issues/{n}` (problem → `(None, problem)`; non-dict → `(None, f"GitLab answered {path} with something other than an object")`), then `self._pages(f"projects/{P}/issues/{n}/notes?sort=asc")` (problem → `(None, problem)`), then `(GitLabFacts().issue(raw, notes), "")`.
     - GitHub: `value, problem = self._read(self._scoped(["issue", "view", str(number)], ["--json", ISSUE_FACT_FIELDS]))`. A problem → `(None, problem)`; a non-dict value → ``(None, "`gh issue view` returned JSON that is not an object")``; else `(value, "")`. `ISSUE_FACT_FIELDS = "number,title,body,state,author,labels,comments,createdAt,url"` is a new module constant near the top of `forge_github.py`, beside the other `*_FIELDS` constants (the string at `issue_automation.py:275`).
   - `subject_facts(self, number: int) -> tuple[dict[str, Any] | None, str]` — "An issue or change request by its number, keyed by `SUBJECT_FACT_KEYS`, and a problem."
     - Forgejo: the same two reads as `issue_facts`, same problems, then `(ForgejoFacts().subject(raw, comments), "")`.
     - GitLab: `(None, NotSupported(ForgeKind.GITLAB, "subject_facts", "GitLab numbers issues and merge requests separately, so a bare number names no single thread").problem)`, making no request. The text is exactly `gitlab does not support subject_facts: GitLab numbers issues and merge requests separately, so a bare number names no single thread`.
     - GitHub: `value, problem = self._read(self._scoped(["issue", "view", str(number)], ["--json", "number,title,body,state,author,labels,comments,url"]))` (the field list of `conversation.py:384`). A problem → `(None, problem)`; a non-dict → ``(None, "`gh issue view` returned JSON that is not an object")``. Else answer `({**value, "isPullRequest": is_pull}, "")` where, by the rule at `conversation.py:172-174`: `segments = [part for part in urlparse(str(value.get("url") or "")).path.split("/") if part]` and `is_pull = len(segments) >= 2 and segments[-2] == "pull"`.
   - `open_issues(self, *, limit: int) -> tuple[tuple[dict[str, Any], ...], str]` — "Up to `limit` open issues, each keyed by `ISSUE_FACT_KEYS`, and a problem."
     - Forgejo: `issues, problem = self._pages(f"repos/{R}/issues?state=open&type=issues", most=limit)`; a problem → `((), problem)`. For each issue, the single comments GET above (a problem or non-list → `((), <that problem>)`). Answer the tuple of `ForgejoFacts().issue(raw, comments)` in listing order.
     - GitLab: `issues, problem = self._pages(f"projects/{P}/issues?state=opened", most=limit)`; a problem → `((), problem)`. For each issue, `self._pages(f"projects/{P}/issues/{raw['iid']}/notes?sort=asc")` (a problem → `((), problem)`). Answer the tuple of `GitLabFacts().issue(raw, notes)`.
     - GitHub: `value, problem = self._read(self._scoped(["issue", "list"], ["--state", "open", "--limit", str(limit), "--json", ISSUE_FACT_FIELDS]))`. A problem → `((), problem)`; `None` → `((), "")`; a list → `(tuple(item for item in value if isinstance(item, dict)), "")`; anything else → ``((), "`gh issue list` returned JSON that is not a list")``.
6. No verb raises. No consumer changes: `issue_automation.py` and `conversation.py` move onto these verbs in part 5 of the wave (#343).

## Where to change
This lane spans nine source files because one verb is declared on the protocol, translated by the two facts classes, and implemented on three adapters. Each edit is small; add, never rewrite.
- `vibey_gh/forge.py`: the two constants and `__all__` (the module has no class to append to; place the constants after `THREADED_CHANGE_REQUEST_FACT_KEYS`).
- `vibey_gh/forge_forgejo_facts.py` (`ForgejoFacts.issue`, `ForgejoFacts.subject`) and `vibey_gh/interfaces/forge_forgejo_facts_interface.py`. Import `SUBJECT_FACT_KEYS` from `vibey_gh.forge` if you build `subject()` from it.
- `vibey_gh/forge_gitlab_facts.py` (`GitLabFacts.issue`) and `vibey_gh/interfaces/forge_gitlab_facts_interface.py`.
- `vibey_gh/interfaces/forge_adapter_interface.py`: the `# --- Issues ---` block with three declarations (`Any` is already imported there).
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, `vibey_gh/forge_github.py`: append the three methods to the end of each file (each adapter class is its module's last statement). Append with `python3 -c` opening the file in append mode, for example `["python3", "-c", "from pathlib import Path\nwith Path('vibey_gh/forge_forgejo.py').open('a') as fh:\n    fh.write('''\n    def issue_facts(...)...\n''')"]`, four-space indented, then run `python -m black --line-length 100 <file>` once. Read only the slices you need (`sed -n 'a,bp'`); never rewrite a whole module with `write_file`.
- `vibey_gh/forge_github.py` also gains `ISSUE_FACT_FIELDS` (near the top, beside the other `*_FIELDS` constants) and `urlparse` in its existing `from urllib.parse import urlencode` line (it becomes `from urllib.parse import urlencode, urlparse`).
- `vibey_gh/forge_gitlab.py`: `NotSupported` and `ForgeKind` come from `vibey_gh.forge`; #335's lanes already import them there, and if either is missing add it to the existing `from vibey_gh.forge import (...)` block.
- Every new file starts with the provenance header line copied from `vibey_gh/forge.py:1`.
- Test: `test/test_forge_issue_reads.py` (new).

## Acceptance criteria
- [ ] `test_forgejo_issue_subject_and_open_issues`: `set(issue) == set(ISSUE_FACT_KEYS)` for a plain Forgejo issue, `set(issue) == set(ISSUE_FACT_KEYS) | {"pull_request"}` for a pull-request-shaped one, and `set(subject) == set(SUBJECT_FACT_KEYS)`.
- [ ] `test_gitlab_issue_reads_and_refuses_subject_facts`: `set(issue) == set(ISSUE_FACT_KEYS)`, system notes dropped, and the NotSupported text verbatim with no request made.
- [ ] `fake_gh` tests pin the GitHub argv and `cwd` of all three verbs, unbound (`issue view 7 --json number,title,body,state,author,labels,comments,createdAt,url`) and bound (`issue view 7 --repo o/r --json number,title,body,state,author,labels,comments,createdAt,url`, `issue list --repo o/r --state open --limit 5 --json number,title,body,state,author,labels,comments,createdAt,url`).
- [ ] `python -m pytest -q` (whole tenant suite) passes with 100% line and branch coverage of `vibey_gh`; black, isort, mypy, `ruff check` and `ruff format --check` are clean (the block below).
- [ ] `git diff --stat` lists only the files under "Where to change" and the new test file.

## Tests to write first (TDD)
Substitute only at declared seams. Never `monkeypatch.setattr` a module or class attribute, never `mock.patch`, `MagicMock` or `AsyncMock`; `monkeypatch.setenv`/`delenv` are fine.
- GitHub: the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real `gh` executable put first on `PATH`. `fake_gh.script({" ".join(argv): {"out": "...", "err": "...", "code": 0}})` scripts answers keyed by the space-joined argv; an unscripted argv exits 3 with `no scripted answer`. `fake_gh.invocations()` returns `[{"argv": [...], "cwd": "...", "stdin": None}, ...]`; `fake_gh.forget()` clears the records. Build `GitHubForge(root=tmp_path)` (unbound) or `GitHubForge(root=tmp_path, repository="o/r")` (bound) and assert `cwd == str(tmp_path.resolve())`. A missing client is `GitHubForge(root=tmp_path, repository="o/r", transport=GhTransport(executable="gh-not-installed"))`, whose problem is ``the GitHub CLI (`gh-not-installed`) is not installed``.
- Forgejo/GitLab: `RoutedTransport` from `test/forge_doubles.py` (import it with `from forge_doubles import RoutedTransport`), built as `RoutedTransport({route: (value, problem), ...})`, where a route is the API path for a GET and `"<path> <METHOD>"` otherwise; a routed answer is returned every time it is asked for, nothing is consumed. It answers keyed by `"<path>"` for a GET and `"<path> <METHOD>"` otherwise, records every `args` tuple in `.calls`, and answers an unrouted request `([], "no route for <key>")`. Build `ForgejoForge(root=tmp_path, repository="o/r", transport=routes)` and `GitLabForge(root=tmp_path, repository="o/r", transport=routes)`; Forgejo `{R}` is `o/r`, GitLab `{P}` is `o%2Fr`. `_pages` appends `?` or `&` then `page=N&limit=50` (Forgejo, which stops only at an **empty** page, so route page 2 as `([], "")`) or `page=N&per_page=100` (GitLab, which stops at a page shorter than 100).

`test/test_forge_issue_reads.py`:
- `test_forgejo_issue_subject_and_open_issues`: routes `repos/o/r/issues/7` (a plain issue: `number` 7, `state` `"open"`, `user.login` `"alice"`, one label, `pull_request` `None`), `repos/o/r/issues/7/comments` (two comments), `repos/o/r/issues/8` (a pull-request-shaped issue with `pull_request` `{"merged": False}`, `state` `"closed"`, `user` carrying only `username`), `repos/o/r/issues/8/comments` (`[]`), and the listing `repos/o/r/issues?state=open&type=issues&page=1&limit=50` (the issue 7 object) plus `repos/o/r/issues?state=open&type=issues&page=2&limit=50` (`[]`). Asserts: `issue_facts(7)` values (state `"OPEN"`, `author == {"login": "alice"}`, labels, the two comment mappings via `comment()`, `createdAt`, `url`); `issue_facts(8)` has `pull_request` and `state == "CLOSED"` and `author.login` from `username`; `subject_facts(8)["isPullRequest"] is True` and `subject_facts(7)["isPullRequest"] is False`; `open_issues(limit=5)` answers one mapping equal to `issue_facts(7)`'s; the key-set equalities of the acceptance criteria.
- `test_gitlab_issue_reads_and_refuses_subject_facts`: routes `projects/o%2Fr/issues/7` (`iid` 7, `state` `"opened"`, `description` `None`, `author.username` `"bob"`, labels `["bug"]`, `web_url`), `projects/o%2Fr/issues/7/notes?sort=asc&page=1&per_page=100` (one system note and one ordinary note), and `projects/o%2Fr/issues?state=opened&page=1&per_page=100`. Asserts `body == ""`, `labels == [{"name": "bug"}]`, `author == {"login": "bob"}`, `number == 7`, exactly one comment (the ordinary note, carrying `noteable_type`/`noteable_iid`), and that `open_issues(limit=5)` answers one mapping equal to `issue_facts(7)`'s; and, on a `GitLabForge` over a fresh `RoutedTransport()`, `subject_facts(7) == (None, expected)` with the exact NotSupported text above while that transport's `.calls` stays `[]`.
- `test_github_issue_and_subject_reads_are_todays_argv_when_bound`: unbound `issue_facts(7)` runs `["issue", "view", "7", "--json", "number,title,body,state,author,labels,comments,createdAt,url"]`; bound runs `["issue", "view", "7", "--repo", "o/r", "--json", "number,title,body,state,author,labels,comments,createdAt,url"]`; `subject_facts(7)` runs `["issue", "view", "7", "--repo", "o/r", "--json", "number,title,body,state,author,labels,comments,url"]` and answers `isPullRequest` true for `url` `https://github.com/o/r/pull/7` and false for `https://github.com/o/r/issues/7`; a JSON list answer gives ``(None, "`gh issue view` returned JSON that is not an object")``.
- `test_github_open_issues_listing`: bound `open_issues(limit=5)` runs `["issue", "list", "--repo", "o/r", "--state", "open", "--limit", "5", "--json", "number,title,body,state,author,labels,comments,createdAt,url"]`; `[{"number": 1}, "x"]` → `(({"number": 1},), "")`; `null` (out `"null"`) → `((), "")`; an object → ``((), "`gh issue list` returned JSON that is not a list")``.
- `test_every_issue_read_passes_a_problem_through`: parametrised over forge × verb (Forgejo and GitLab with an empty `RoutedTransport`: the value is the empty value and the problem starts with `"no route for "`; GitHub with the missing client: the exact not-installed sentence). GitLab `subject_facts` is excluded (it refuses without asking).

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_issue_reads.py test/test_forge_facts.py test/test_forge_adapters.py
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
- Comment writes (`comment_on_issue`, `update_comment`), the review comment and review threads: child lanes 2-4 (`split-336-2-comment-writes`, `split-336-3-review-comment`, `split-336-4-review-threads`).
- `issue_automation.py`, `conversation.py`, `github_state.py`: parts 4 and 5 of the wave.
- The existing `get_issue` / `get_issue_thread` verbs: left as they are.
- `test/conftest.py`, `test/forge_doubles.py`, and this repository's `.vibey-gh.toml` (its `[platform] kind = "github"` declaration is the operator's; never write or change it).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every verb answers `(value, problem)`. `problem` is `""` exactly when the forge answered; otherwise `value` is the empty value for its type (`None`, `()`) and `problem` is one sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable output. A verb a forge has no equivalent for answers `(<empty>, NotSupported(kind, verb, reason).problem)`; `NotSupported` is the frozen dataclass in `vibey_gh.forge` whose `problem` is `f"{kind.value} does not support {verb}: {reason}"`. Forgejo is the default adapter (8.b): implement and test it first.

**C2 — GitHub argv fidelity.** Each GitHub verb runs today's `gh` argv byte for byte. `self._scoped(head, tail)` returns `head + ["--repo", self.repository] + tail` when the adapter is bound (`self.repository` non-empty) and `head + tail` when it is not; `--repo` therefore sits right after the subcommand's positional argument (`issue view 7 --repo o/r --json <fields>`) or after the two-word subcommand (`issue list --repo o/r --state open --limit 5 --json <fields>`). Every call runs with `cwd=self.root`.

**Helpers already on the branch (from the wave-1 lanes this one depends on):**
- `GitHubForge._read(args, *, stdin=None) -> tuple[Any, str]` runs `self.transport.json(args, cwd=self.root, stdin=stdin)`: decoded JSON (`None` for empty output) and `""`, or `None` and a problem (a missing client → ``the GitHub CLI (`<executable>`) is not installed``; a non-zero exit → the transport's `"gh <args>: <stderr>"`; unparseable output → ``"`gh <a> <b>` returned output that is not JSON"``).
- `ForgejoForge._pages` / `GitLabForge._pages(path, *, most: int | None = None) -> tuple[list[dict[str, Any]], str]` walks a paged listing (query rules in the test section above), answering at most `most` dict items, `([], problem)` when a page cannot be read, `([], f"{Forge} answered {path} with something other than a list")` for a non-list page, and a problem after 100 pages.
- Forgejo `{R}` is `self._repository()` (`quote(self.repository, safe="/")`); GitLab `{P}` is `self._project()` (`quote(self.repository, safe="")`). A GET is `self.transport.survey([path], cwd=self.root)`.
- `ForgejoFacts.comment(raw)` → `{"id": str(raw["id"]), "url": html_url or "", "body": body or "", "author": {"login": user.login or user.username or ""}, "createdAt": created_at or ""}`; `GitLabFacts.comment(note)` → `{"id": str(id), "url": "", "body", "author": {"login": author.username}, "createdAt", "noteable_type", "noteable_iid"}`. Both classes are pure, hold no state, and subclass their `@runtime_checkable` Protocol interface; a method added to a class must be declared on its interface in the same change or mypy refuses to instantiate the class.

**Why Forgejo issue comments are one GET, not `_pages`.** Forgejo's `GET /repos/{owner}/{repo}/issues/{index}/comments` declares only `since` and `before` (Forgejo API 16.0.0-dev swagger at codeberg.org): it ignores `page`/`limit` and returns every comment in one answer. `ForgejoForge._pages` stops only at an empty page, so walking this endpoint would re-read the same comments until its 100-page cap and report the listing as incomplete. The paginated endpoints (`issues`, `pulls`, `pulls/{n}/reviews`) are walked with `_pages`.

**C7 — tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`, `--cov-fail-under=100 --cov-branch`); focused runs need `--no-cov`, and the whole suite runs before committing. No test leaves the machine. Never touch `test/conftest.py`.

**C8 — the formatter trap.** The tenant is checked by both `black --line-length 100` + `isort` (profile black, `combine_as_imports`) and the root `ruff format`, which disagree on some wraps. Keep every line at or under 100 columns (95 with nested calls); bind a long expected value to a local before the `assert`; no implicit string concatenation that would fit on one line; multi-line calls take one argument per line with a trailing comma; no backslash continuations. If the two formatters fight over a line, restructure the line; never alternate between them. The formatters put `from forge_doubles import RoutedTransport` in the third-party block, after `import pytest`.

**Depends on:** split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve, split-333-1-facts-translators, split-333-2-change-request-reads, split-333-3-change-request-text, split-334-1-labelled-listings, split-334-2-open-branches, split-334-3-wait-for-checks, split-335-1-create-edit-merge, split-335-2-ready-close-comment, split-335-3-labels
- split-332-1-transport-seams: `NotSupported` in `vibey_gh.forge`, and transports that read an empty 2xx answer as `({}, "")`.
- split-332-2-adapter-paging: `_pages`, the adapters' `host` field, and `RoutedTransport` in `test/forge_doubles.py`.
- split-332-3-repository-name: `GitHubForge._scoped` and `_read`, and `repository_name()`.
- split-332-4-selector-resolve: `ForgeSelector.resolve` and `RecordingForge`; this lane only needs the tree it leaves.
- split-333-1-facts-translators: `ForgejoFacts` / `GitLabFacts`, their interfaces, `comment()`, and `THREADED_CHANGE_REQUEST_FACT_KEYS` in `forge.py`.
- split-333-2-change-request-reads: the `*_FIELDS` constants at the top of `forge_github.py`.
- split-333-3-change-request-text: the adapter files as it leaves them (this lane appends after its methods).
- split-334-1-labelled-listings: the adapter files as it leaves them.
- split-334-2-open-branches: the adapter files and facts classes as it leaves them.
- split-334-3-wait-for-checks: the adapters' `sleep` field (constructors in tests use keywords, so field order does not matter).
- split-335-1-create-edit-merge: `NotSupported`/`ForgeKind` imported in `forge_gitlab.py`.
- split-335-2-ready-close-comment: the adapter files as it leaves them (`create_comment` removed).
- split-335-3-labels: the adapter files as it leaves them; the wave's first half is sequential.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
