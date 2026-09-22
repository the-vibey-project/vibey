## Title
feat(gh): the forge adapter reads and writes issues, comments and review threads

## Why
Issue automation, conversation, the shared state comment and flatten read issues and
threads and write comments through `gh` (IA1, IA4, CV1-CV2, CV4, GS3-GS5, FL1-FL2). The
state-comment edit needs GitHub's REST/GraphQL split (`github_state.py:99-132`) inside the
GitHub adapter, and flatten's unresolved-thread walk (`flatten.py:609-742`) needs a page
verb every forge can answer. ADR 0001; sub-doctrine 8.b.

## Required behaviour
1. `forge.py`: `ISSUE_FACT_KEYS`, `SUBJECT_FACT_KEYS`, `REVIEW_COMMENT_KEYS` (C5), in `__all__`.
2. **V26 `issue_facts(number)`** — GitHub `_read(self._scoped(["issue", "view",
   str(number)], ["--json", ISSUE_FACT_FIELDS]))`, `ISSUE_FACT_FIELDS =
   "number,title,body,state,author,labels,comments,createdAt,url"`
   (`issue_automation.py:275`); non-dict → problem. Forgejo GET `repos/{R}/issues/{n}` +
   `_pages(…/issues/{n}/comments)` → `ForgejoFacts().issue(raw, comments)` (state OPEN/CLOSED,
   `author.login`, labels, comments, `createdAt=created_at`, `url=html_url`, plus
   `"pull_request"` only when `raw["pull_request"]` is not `None`). GitLab GET
   `projects/{P}/issues/{n}` + notes → `GitLabFacts().issue(...)`.
3. **V27 `subject_facts(number)`** — GitHub `_read(self._scoped(["issue", "view",
   str(number)], ["--json", "number,title,body,state,author,labels,comments,url"]))`
   (`conversation.py:384`), then add `isPullRequest`: the path of `url` split on `/`, second
   to last segment `== "pull"` (the rule at `conversation.py:163-174`). Forgejo: V26's reads →
   `ForgejoFacts().subject(...)` with `isPullRequest = raw.get("pull_request") is not None`.
   GitLab → `NotSupported(GITLAB, "subject_facts", "GitLab numbers issues and merge
   requests separately, so a bare number names no single thread")`.
4. **V28 `open_issues(*, limit)`** — GitHub `_read(self._scoped(["issue", "list"],
   ["--state", "open", "--limit", str(limit), "--json", ISSUE_FACT_FIELDS]))`; `None` →
   `((), "")`. Forgejo `_pages(f"repos/{R}/issues?state=open&type=issues", most=limit)` and
   the comments of each → `issue()`. GitLab `_pages(f"projects/{P}/issues?state=opened",
   most=limit)` and notes of each.
5. **V29 `comment_on_issue(number, body)`** — GitHub `self._scoped(["issue", "comment",
   str(number)], ["--body", body])`, fail → `_failed(run, "gh issue comment")`. Forgejo POST
   `repos/{R}/issues/{n}/comments`; GitLab POST `projects/{P}/issues/{n}/notes`.
6. **V30 `update_comment(comment, body)`** — GitHub: `comment.get("databaseId") is not None`
   → `R` from V1, `_run(["api", f"repos/{R}/issues/comments/{databaseId}", "--method",
   "PATCH", "--field", f"body={body}"])`; else `node = comment.get("id")`, falsy →
   `(False, "comment has no ID")`, else `_run(["api", "graphql", "--field",
   f"query={UPDATE_COMMENT_MUTATION}", "--field", f"id={node}", "--field", f"body={body}"])`
   with the mutation text of `github_state.py:117-120` verbatim; failure →
   `(False, (run.stderr or "").strip() or f"`gh api` exited {rc}")` (github_state then raises
   `f"{error}: {problem}"`, today's text). Forgejo: numeric `id` or `(False, "comment has no
   ID")`; PATCH `repos/{R}/issues/comments/{id}` `{"body"}`. GitLab: `id`, `noteable_type`,
   `noteable_iid` from the mapping (else the same problem); PUT
   `projects/{P}/issues/{iid}/notes/{id}` or `…/merge_requests/{iid}/notes/{id}`.
7. **V31 `review_comment(number, comment_id)`** — GitHub `R` from V1, `_read(["api",
   f"repos/{R}/pulls/comments/{comment_id}"])` (number unused; the caller checks
   `pull_request_url`); non-dict → problem. Forgejo: `_pages(f"repos/{R}/pulls/{n}/reviews")`,
   then `repos/{R}/pulls/{n}/reviews/{review_id}/comments` for each until `str(id) ==
   comment_id` → `ForgejoFacts().review_comment(c)` (`line=position`,
   `original_line=original_position`, `user.login`, `diff_hunk`, `pull_request_url`); not
   found → `(None, f"review comment {comment_id} is not on #{number}")`. GitLab GET
   `projects/{P}/merge_requests/{n}/notes/{comment_id}` → `GitLabFacts().review_comment(note,
   f"https://{host}/{repository}/-/merge_requests/{n}")` (`path=position.new_path`,
   `line=position.new_line`, `original_line=position.old_line`, `diff_hunk=""`).
8. **V32 `review_thread_page(head_ref, cursor)`** — GitHub: `name, problem =
   self.repository_name()`; `owner, _, repo = name.partition("/")`; args `["api", "graphql",
   "--raw-field", f"query={REVIEW_THREADS_QUERY}", "--raw-field", f"owner={owner}",
   "--raw-field", f"name={repo}", "--raw-field", f"branch={head_ref}"]` + `["--raw-field",
   f"after={cursor}"]` when `cursor`; answered through **`self.transport.survey(args,
   cwd=self.root)`** so its problems are exactly the texts flatten reports today (`the GitHub
   CLI (`gh`) is not installed`, "`gh api graphql` failed: <last stderr line>"); list →
   `({}, "`gh api graphql` returned a JSON list where an object was expected")`.
   `REVIEW_THREADS_QUERY` and `REVIEW_THREADS_PER_PAGE = 100` are copied verbatim from
   `flatten.py:131,152-169` (Part 6 deletes flatten's copy). Forgejo: open pulls whose
   `head.ref == head_ref`, lowest two numbers; none → the empty envelope
   `{"data": {"repository": {"pullRequests": {"nodes": []}}}}`; else the first pull's
   reviews' comments → `ForgejoFacts().thread_page(numbers, comments)`: group comments by
   `(path, position or original_position)`; a group is resolved when any comment has a
   non-null `resolver`; its node is the earliest comment; `pageInfo = {"hasNextPage": False,
   "endCursor": None}`; a second pull becomes a sibling node with empty threads. GitLab:
   `merge_requests?state=opened&source_branch=…` (lowest two) and
   `_pages(f"projects/{P}/merge_requests/{iid}/discussions")`; a resolvable discussion is a
   thread, resolved when all its resolvable notes are `resolved`. `cursor` is ignored on
   both (one page).

## Where to change
`vibey_gh/forge.py`, `vibey_gh/interfaces/forge_adapter_interface.py` (V26-V32;
`from collections.abc import Mapping`), `vibey_gh/forge_github.py` (constants at the top),
`vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, `vibey_gh/forge_forgejo_facts.py`,
`vibey_gh/forge_gitlab_facts.py` and their interfaces (`issue`, `subject`,
`review_comment`, `thread_page`).

## Acceptance criteria
- [ ] `fake_gh` tests pin V26-V32's GitHub argv; V30's two branches reproduce
  `test/test_gh_transport.py:448-470`'s `REST_EDIT` / `GRAPHQL_EDIT` argv exactly.
- [ ] Forgejo/GitLab mappings contain every key of their schema.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
`test/test_forge_conversation_verbs.py`:
- `test_github_issue_and_subject_reads_are_todays_argv_when_bound` (subject gains
  `isPullRequest` from `/pull/7` and `/issues/7`).
- `test_github_open_issues_listing`.
- `test_github_comment_on_issue`.
- `test_github_update_comment_chooses_rest_graphql_or_refuses_without_an_id`.
- `test_github_review_comment_reads_the_repository_wide_endpoint`.
- `test_github_thread_page_is_flattens_query_and_reports_like_flatten` (first page has no
  `after=`; second has `after=c1`; missing client and rc 1 texts; list answer → problem).
- `test_forgejo_issue_subject_and_open_issues` (PR-shaped issue carries `pull_request`).
- `test_forgejo_review_comment_walks_the_pull_requests_reviews` (found, not found).
- `test_forgejo_thread_page_groups_comments_and_marks_resolution` (none, one, two pulls).
- `test_gitlab_conversation_verbs_route_and_refuse_subject_facts`.

## Checks the lane must run (all must pass)
Same block as Part 0a, focused on `test/test_forge_conversation_verbs.py`.

## Out of scope
The consuming modules (Parts 4, 5, 6). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md,
AGENTS.md, GEMINI.md or skill trees -- the docs wave owns those. Do not push, open PRs, or
change git remotes. Commit locally with a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

## Shared conventions for every forge part
## Shared conventions (binding on every part; read before your own part)

### C1 — The adapter contract

- Every verb answers `(value, problem)`. `problem` is `""` exactly when the forge answered;
  otherwise `value` is the empty value for its type (`None`, `()`, `frozenset()`, `False`,
  `{}`) and `problem` is one sentence. **No verb raises** for a failed call, a missing
  client, a non-2xx status or unreadable output (vibey-gh ADR 0001, "Every adapter verb
  answers `(value, problem)`"; `interfaces/forge_adapter_interface.py:9-16`).
- A verb a forge has no equivalent for answers
  `(<empty>, NotSupported(kind, verb, reason).problem)` — the record added in 0a. Its text is
  `f"{kind.value} does not support {verb}: {reason}"`. Never silently approximate a verb
  that is listed as NotSupported below.
- A verb arrives with its first caller (ADR 0001). Every verb in this file has a named
  caller in the call-site inventory.

### C2 — GitHub: argv fidelity, `[scope]`, `{R}`

The operator requires the GitHub adapter to run **the same `gh` argv as today, byte for
byte**, so a github-declared repository sees no change. Rules the GitHub adapter follows:

1. Each GitHub verb's argv is copied verbatim from its reference call site(s) in the
   inventory. Do not reorder flags, rename flags (`--title` is not `-t`), or add fields.
2. `[scope]` in an argv below means `["--repo", self.repository]` when the adapter is
   **bound** (`self.repository` non-empty) and nothing when it is not. It goes immediately
   after the subcommand's positional argument, or after the two-word subcommand when there
   is none: `pr view 7 [scope] --json …`, `pr list [scope] --base …`. Implemented once, in
   0a, as `GitHubForge._scoped(head, tail)`.
3. `{R}` in an API path is `name` from `self.repository_name()`: the bound name, else
   `$GH_REPO`, else `gh repo view --json nameWithOwner` — exactly what
   `github_state.repository()` does today (`github_state.py:70-75`). Literal
   `repos/{owner}/{repo}/…` (with braces) is gh's own placeholder and stays literal where a
   call site used it (MT9, PR9).
4. Every call runs with `cwd=self.root`.
5. `ForgeSelector._github` binds only an explicit `[platform] repository` (0a). So a bare
   GitHub selection is unbound, and a Wave-2 call site produces `--repo R` exactly when it
   binds (C6), which is exactly where today's code passed `--repo`.

### C3 — The only deliberate differences on GitHub

Nothing else may differ. Each Wave-2 part lists which of these apply to it.

- **D1 cwd.** Sites that ran `gh` in the process's working directory (merge train, github
  state, release publication, issue automation, conversation reads, rulesets, install,
  flatten, parts of PR automation) now run it in `cfg.root` — the directory `load_config()`
  found by walking up from that working directory (`config.py:1630-1650`). Same repository
  for `gh`.
- **D2 `$GH_REPO` first.** `merge_train.py:304,350` and `github_release.py:27` ran
  `gh repo view` unconditionally; the adapter consults `$GH_REPO` first, as
  `github_state.repository()` always has. Same name; one fewer `gh` call when it is set.
- **D3 neutral wording.** Messages that named GitHub and now run on any forge are
  neutralised: reconcile's update-branch success detail, release publication's two failure
  messages, install's secret-listing notice (listed in Parts 3 and 4).
- **D4 explicit repository.** An adopter who sets `[platform] repository` with
  `kind = "github"` gets a bound adapter, so every `pr`/`issue`/`label`/`release`/`secret`
  command carries `--repo <that name>`. With the key unset (this repository, and the
  default) nothing changes.
- **D5 exception type.** Where a site let a `FileNotFoundError` (no `gh`) or a
  `json.JSONDecodeError` escape, it now raises `RuntimeError(problem)` (or returns its
  failure value), because the adapter answers instead of raising.

### C4 — Forgejo and GitLab plumbing (built in 0a, used by every later Wave-1 part)

- Transports: `survey([path])` is a GET; `survey([path, "POST"|"PATCH"|"PUT"|"DELETE",
  body])` sends `body` (always `json.dumps(payload)`, or `""` for no body). Forgejo base URL
  `https://{host}/api/v1/`, header `Authorization: token …`; GitLab base
  `https://{host}/api/v4/`, header `PRIVATE-TOKEN`.
- `{R}` for Forgejo is `quote(self.repository, safe="/")`; `{P}` for GitLab is
  `quote(self.repository, safe="")` (existing `_repository()` / `_project()` helpers).
- `self._pages(path, *, most=None)` walks a paged listing: Forgejo `page=N&limit=50`,
  GitLab `page=N&per_page=100`, appended with `?` or `&`; stops at a short page, or once
  `most` items are held, and reports `"… listed more than 100 pages of {path}; the listing
  is incomplete"` as a problem if it never ends. Non-list page → problem.
- `self._absent(problem) -> bool`: true when the problem is the transport's 404 sentence
  (`"Forgejo API error 404"` / `"GitLab API error 404"` prefix). Use it where a verb must
  tell "the forge said it does not exist" (value `None`, problem `""`) from "could not ask".
- A 2xx answer with an empty body is `({}, "")` (fixed in 0a; today it is a failure).

### C5 — Neutral mapping schemas

The decision functions that consume change requests and issues (`merge_train.judge`,
`pr_automation.evaluate`, `ProtectedPathsGuard.refusal`, `issue_automation.evaluate`,
`conversation.evaluate/context`, `Flattener._review_threads`) read dicts, and their tests
(thousands of lines) build those dicts. To keep them untouched in this wave, the verbs that
feed them return **mappings whose keys are the ones those functions already read**. The key
spellings are therefore the historical ones; the adapters are what make the values
forge-neutral. This is a deliberate, transitional deviation from ADR 0001's "frozen
records" and is listed in the appendix for the operator.

`ChangeRequestFacts` — `forge.CHANGE_REQUEST_FACT_KEYS` (0b), returned by
`change_request_facts`:

| key | type / values |
|---|---|
| `number` | int |
| `title`, `body` | str |
| `state` | `"OPEN"` \| `"CLOSED"` \| `"MERGED"` |
| `isDraft` | bool |
| `mergeable` | `"MERGEABLE"` \| `"CONFLICTING"` \| `"UNKNOWN"` |
| `mergeStateStatus` | `"BEHIND"` or anything else (`"UNKNOWN"` when the forge cannot say) |
| `reviewDecision` | `"APPROVED"` \| `"CHANGES_REQUESTED"` \| `"REVIEW_REQUIRED"` \| `""` |
| `statusCheckRollup` | list of `{"name", "status": "COMPLETED"\|"IN_PROGRESS", "conclusion": "SUCCESS"\|"FAILURE"\|"NEUTRAL"\|"SKIPPED"\|"CANCELLED"\|None, "startedAt", "completedAt", "detailsUrl"}` |
| `author` | `{"login": str}` |
| `labels` | list of `{"name": str}` |
| `headRefOid`, `headRefName`, `baseRefName` | str |
| `isCrossRepository` | bool |
| `changedFiles` | int; **omit** when the forge does not count (the protected-paths guard then refuses rather than guesses) |

`THREADED_CHANGE_REQUEST_FACT_KEYS` (0b), returned by `change_request_with_thread`: the
table above without `changedFiles`, plus `comments` (list of `Comment`),
`headRepository: {"name": str}`, `headRepositoryOwner: {"login": str}`.

`Comment`: `{"id": str, "url": str, "body": str, "author": {"login": str}, "createdAt": str}`;
GitLab adds `"noteable_type"` and `"noteable_iid"` (needed to edit it).

`IssueFacts` — `forge.ISSUE_FACT_KEYS` (0e): `number, title, body, state ("OPEN"|"CLOSED"),
author, labels, comments, createdAt, url`; Forgejo adds `"pull_request"` (the raw object)
only when the number is a pull request, which `issue_automation.evaluate` already skips.

`SubjectFacts` — `forge.SUBJECT_FACT_KEYS` (0e): `number, title, body, state, author, labels,
comments, url, isPullRequest (bool)`.

`ReviewComment` — `forge.REVIEW_COMMENT_KEYS` (0e): `id, body, user ({"login"}), path, line,
original_line, diff_hunk, pull_request_url` (the last path segment of `pull_request_url` is
the change-request number — `conversation.py:213-215` checks it).

`ReviewThreadPage` (0e): `{"data": {"repository": {"pullRequests": {"nodes": [{"number",
"reviewThreads": {"pageInfo": {"hasNextPage", "endCursor"}, "nodes": [{"isResolved",
"comments": {"nodes": [{"path", "line", "originalLine", "body", "author": {"login"}}]}}]}}]}}},
"errors"?: [...]}` — the shape `flatten.py:691-736` walks. Forgejo and GitLab always answer
one page (`hasNextPage: false`, `endCursor: null`).

`BranchRules` (0g): the ruleset document `rulesets.build_ruleset` builds
(`rulesets.py:121-130`) plus `"id"`.

### C6 — How Wave-2 code calls the adapter

1. **Obtain.** Every public function that reaches the forge gains a keyword-only last
   parameter `forge: ForgeAdapterInterface | None = None` and starts with
   `forge = ForgeSelector().resolve(forge, cfg)` (or `ForgeSelector().resolve(forge)` when
   it has no `cfg`). `resolve` (0a) returns the injected forge, else `select(cfg)`, else
   `current()` = `select(load_config())`. Pass `forge=forge` down to every helper it calls.
   Imports: `from vibey_gh.forge_selector import ForgeSelector` and
   `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface`.
2. **Bind** exactly where the code you replace called `github_state.repository()` (or ran
   `gh repo view`) and passed `--repo`/`repos/<name>` — each Wave-2 part says which sites:
   ```python
   name, problem = forge.repository_name()
   if problem:
       raise RuntimeError(problem)
   bound = forge.for_repository(name)
   ```
   (For a site that today *returns* a failure value instead of raising, return it.) Bind
   once per public function call, as today's code resolved once per call.
3. **Failures keep their old shape.** A site that raised keeps raising, with the old prefix:
   `if problem: raise RuntimeError(problem)` (or `RuntimeError(f"<old prefix>: {problem}")`).
   A site that returned a bool keeps returning `ok`. A site that ignored the result keeps
   ignoring it. A site that returned a problem string passes `problem` through.
4. **No platform names.** After your part, `grep -n '"gh"' vibey_gh/<your files>` and
   `grep -n "subprocess" …` show no `gh` invocation, and `github_state.gh_json` /
   `github_state.repository` are not called from your files (Part 4's `github_state.py`
   keeps both as the GitHub-only facade for `forge-snapshot` / `forecast`, `cli.py:598,835`).
5. Delete runners and imports that become unused (`json`, `subprocess`, `cast`, `github_state`).
6. Tests that replace one of your functions with a positional-only lambda (for example
   `lambda n: …`) now receive `forge=` from your code: widen them to `lambda n, **_: …`.

### C7 — Tests

- The tenant's floor is **100% line and branch coverage of all of `vibey_gh`**
  (`pyproject.toml:64-71`, `--cov-fail-under=100 --cov-branch`). Every part runs the whole
  suite before committing. Focused runs need `--no-cov`.
- **GitHub argv proofs** use the conftest `fake_gh` fixture (`test/conftest.py:86-161`: a
  real `gh` on PATH; `script({...})`, `calls()`, `invocations()` with argv, cwd, stdin).
  Construct `GitHubForge(root=tmp_path)` and assert
  `fake_gh.invocations() == [{"argv": [...], "cwd": str(tmp_path.resolve()), "stdin": None}]`.
  Use `monkeypatch.setenv("GH_REPO", "o/r")` or `monkeypatch.delenv("GH_REPO", raising=False)`
  explicitly in every test whose argv contains `{R}`.
- **Forgejo/GitLab verb tests** use `RoutedTransport` from `test/forge_doubles.py` (0a):
  answers keyed by `"<path>"` for a GET or `"<path> <METHOD>"` otherwise; records every
  `args` tuple in `.calls`; an unrouted request answers `([], "no route for <key>")`.
- **Wave-2 module tests** use `RecordingForge` from `test/forge_doubles.py` (0a):
  `RecordingForge(change_request_facts=(facts, ""), …)`; every scripted verb returns its
  scripted value (or calls it, if callable), `repository_name()` defaults to `("o/r", "")`,
  `for_repository(name)` records and returns itself, and `.calls` lists
  `(verb, *args, *sorted(kwargs.items()))`. An unscripted verb raises `AttributeError`, so a
  test cannot pass by calling something it never named. Import with
  `from forge_doubles import RecordingForge` (pytest puts `test/` on `sys.path`).
- Tests import only the double they need; never touch `test/conftest.py`.

### C8 — The formatter trap

The tenant is checked by **both** `black --line-length 100` + `isort` (profile black,
`combine_as_imports`) in the `tools-lint` job (`.github/workflows/ci.yml:699-705`) **and**
the root `ruff format --check .` (ruff 0.16.3, line length 100). They disagree on some
wraps — a long `assert x == y, message` is the known ping-pong. Write lines neither wants
to rewrap:

- keep every line ≤ 100 columns and prefer ≤ 95 for anything with nested calls;
- bind a long comparison or message to a local first (`expected = …` then `assert got == expected`);
- no implicit string concatenation that would fit on one line (ruff joins it, black does
  not); use one literal, or an f-string built from locals;
- multi-line calls: one argument per line with a trailing comma (both keep it exploded);
- no backslash continuations.

Run both before committing (commands in each part). If they fight, restructure the line —
never alternate between them.

### C9 — Working in the big files

`forge_github.py`, `forge_forgejo.py` and `forge_gitlab.py` grow with every Wave-1 part.
Each adapter class is the **last statement** of its module, so add new methods by
appending to the end of the file with a shell heredoc
(`cat >> vibey_gh/forge_github.py <<'PY' … PY`, four-space indented), then run black once.
Read only the slices you need (`sed -n '120,200p' file`). Do not rewrite a whole module.

---
