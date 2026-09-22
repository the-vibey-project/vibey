## Title
feat(gh): the forge adapter reads a change request's facts, text, comments, files and checks

## Why
The merge train and PR automation decide on a change request's full state
(`merge_train.py:250`, `pr_automation.py:472-484`), promotion reads its words
(`promote.py:317-329`), the train checks an exact head's gates (`merge_train.py:304-313`) and
the protected-paths guard needs every changed path (`merge_train.py:269-287`). All are `gh`
today. The existing `get_check_results` returns bare dicts, ignores whether a check finished
(`forge_github.py:210-219`), and its GitLab route is wrong (`forge_gitlab.py:185`: the API is
`projects/:id/repository/commits/:sha/statuses`). ADR 0001; sub-doctrine 8.b.

## Required behaviour
1. `forge.py`: `CHANGE_REQUEST_FACT_KEYS` and `THREADED_CHANGE_REQUEST_FACT_KEYS` (tuples of
   the C5 keys), in `__all__`.
2. **V5 `change_request_facts`** — GitHub: `_read(self._scoped(["pr", "view", str(number)],
   ["--json", CHANGE_REQUEST_FACT_FIELDS]))`, where `CHANGE_REQUEST_FACT_FIELDS` is the
   string at `merge_train.py:237-246` verbatim (comments too): `"number,title,state,isDraft,
   mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,author,labels,headRefOid,
   headRefName,baseRefName,isCrossRepository,body,changedFiles"` (no spaces). A non-dict
   answer (including `null`) → `(None, "`gh pr view` returned JSON that is not an object")`.
   Forgejo: GET `repos/{R}/pulls/{n}`, then `_pages(f"repos/{R}/commits/{sha}/statuses")`,
   then `_pages(f"repos/{R}/pulls/{n}/reviews")` → `ForgejoFacts().change_request(pull,
   statuses, reviews)`. GitLab: GET `projects/{P}/merge_requests/{n}`, `_pages(f"projects/{P}
   /repository/commits/{sha}/statuses")`, GET `projects/{P}/merge_requests/{n}/approvals` →
   `GitLabFacts().change_request(mr, statuses, approvals)`. Any problem → `(None, problem)`.
3. **V6 `change_request_with_thread`** — GitHub: as V5 with `THREADED_CHANGE_REQUEST_FIELDS`
   = `pr_automation.py:480-482` verbatim: `"number,title,state,isDraft,mergeable,
   mergeStateStatus,reviewDecision,statusCheckRollup,author,labels,comments,headRefOid,
   headRefName,headRepository,headRepositoryOwner,isCrossRepository,baseRefName,body"`.
   Forgejo: V5's reads plus `_pages(f"repos/{R}/issues/{n}/comments")` →
   `ForgejoFacts().threaded(...)`. GitLab: V5's reads plus
   `_pages(f"projects/{P}/merge_requests/{n}/notes?sort=asc")` (system notes dropped) and,
   only when `source_project_id != target_project_id`, GET `projects/{source_project_id}`
   for the head repository → `GitLabFacts().threaded(...)`.
4. **V7 `change_request_text`** — GitHub, byte-identical to `promote.py:317-329, 391-396`:
   `_run(self._scoped(["pr", "view", str(number)], ["--json", "title,body"]))`; rc ≠ 0 →
   `(None, " ".join((run.stderr or run.stdout or "").split())[:300] or f"gh pr view exited
   {rc}")`; stdout not JSON or not a dict → `(None, f"gh pr view {number} did not return a
   title and body")`; else `((str(title or ""), str(body or "")), "")`. Forgejo: GET
   `repos/{R}/pulls/{n}` → `(title, body)`. GitLab: GET `projects/{P}/merge_requests/{n}` →
   `(title, description)`.
5. **V8 `change_request_comment_bodies`** — GitHub: `_run(self._scoped(["pr", "view",
   str(number)], ["--json", "comments", "-q", ".comments[].body"]))`; rc 0 →
   `(((run.stdout or "") + (run.stderr or ""),), "")` (the text `merge_train._gh` returned);
   else `((), _failed(run, "gh pr view"))`. Forgejo: bodies of
   `_pages(f"repos/{R}/issues/{n}/comments")`. GitLab: bodies of non-system notes.
6. **V9 `changed_paths`** — GitHub: `_run(["api", "--paginate",
   f"repos/{{owner}}/{{repo}}/pulls/{number}/files?per_page=100"])` (literal braces, no
   scope); rc ≠ 0 → `(None, _failed(run, "gh api"))`; parse with
   `ProtectedPathsGuard().parse_listing(run.stdout)` (import from
   `vibey_gh.protected_paths`); `TypeError`/`ValueError` → `(None, f"`gh api` returned a
   file listing that could not be read: {error}")`; else `((paths, listed), "")`. Forgejo:
   `_pages(f"repos/{R}/pulls/{n}/files")` → each `filename`, plus `previous_filename` when a
   non-empty str; `listed = len(entries)`. GitLab: `_pages(f"projects/{P}/merge_requests/{n}
   /diffs")` → `new_path`, plus `old_path` when `renamed_file` and it differs.
7. **V10 `get_check_results`** (reshaped) → `tuple[CheckResult, ...]`. GitHub: argv
   unchanged (`api repos/{R}/commits/{sha}/check-runs`, via `_read`); keep the two existing
   shape problems; `CheckResult(name=str(r.get("name") or ""), head_sha=sha,
   conclusion=str(r.get("conclusion") or "") if r.get("status") == "completed" else "")`.
   Forgejo: `_pages(f"repos/{R}/commits/{sha}/statuses")` →
   `ForgejoFacts().check_result(status, sha)`. GitLab: the corrected route above →
   `GitLabFacts().check_result(status, sha)`.
8. New `vibey_gh/forge_forgejo_facts.py`, class `ForgejoFacts` (pure: no I/O), interface
   `vibey_gh/interfaces/forge_forgejo_facts_interface.py`:
   - `state(raw)`: `"MERGED"` if `raw.get("merged")`, `"OPEN"` if `raw["state"] == "open"`,
     else `"CLOSED"`.
   - `draft(pull)`: `pull["draft"]` when it is a bool, else the title starts (after
     whitespace, case-insensitive) with `WIP:` or `[WIP]`.
   - `check_name(context)`: strips one trailing ` (<event>)` matching `r" \([a-z_]+\)$"`
     (Forgejo Actions appends the event, e.g. `PR evaluate / gate (pull_request)`).
   - `rollup_entry(status)`: `name=check_name(context)`, `status="IN_PROGRESS"` if
     `state == "pending"` else `"COMPLETED"`, `conclusion` from
     `{"success": "SUCCESS", "failure": "FAILURE", "error": "FAILURE", "warning": "NEUTRAL"}`
     (else `None`), `startedAt=created_at`, `completedAt=updated_at`, `detailsUrl=target_url`.
   - `check_result(status, sha)`: `CheckResult(check_name(context), sha,
     {"success": "success", "failure": "failure", "error": "failure", "warning":
     "neutral"}.get(state, ""))`.
   - `review_decision(reviews)`: latest non-dismissed review per `user.login` in list order;
     any latest `REQUEST_CHANGES` → `"CHANGES_REQUESTED"`, else any `APPROVED` →
     `"APPROVED"`, else `""`.
   - `comment(raw)`: `{"id": str(id), "url": html_url, "body", "author": {"login": user.login
     or user.username}, "createdAt": created_at}`.
   - `change_request(pull, statuses, reviews)`: every C5 key; `mergeable` from
     `pull["mergeable"]` (True → `"MERGEABLE"`, False → `"CONFLICTING"`, missing →
     `"UNKNOWN"`); `mergeStateStatus="UNKNOWN"`; `isCrossRepository` = head and base
     `repo_id` differ; `changedFiles` only when `pull["changed_files"]` is an int.
   - `threaded(pull, statuses, reviews, comments)`: the threaded key set;
     `headRepository={"name": head.repo.name}`, `headRepositoryOwner={"login":
     head.repo.owner.login}` (empty strings when absent).
9. New `vibey_gh/forge_gitlab_facts.py`, class `GitLabFacts` + interface, same method names:
   state `opened`→`OPEN`, `merged`→`MERGED`, else `CLOSED`; draft = `draft` or
   `work_in_progress`; `mergeable` = `"CONFLICTING"` if `has_conflicts` else `"MERGEABLE"`;
   `mergeStateStatus="BEHIND"` when `detailed_merge_status == "need_rebase"` else
   `"UNKNOWN"`; `reviewDecision="APPROVED"` if `approvals["approved"]` else `""`; rollup from
   GitLab statuses (`success`→SUCCESS, `failed`→FAILURE, `canceled`→CANCELLED,
   `skipped`→SKIPPED, other → IN_PROGRESS/None; `startedAt=started_at or created_at`,
   `completedAt=finished_at`); `author.login = author.username`; `labels` are strings on
   GitLab → `{"name": s}`; `headRefOid=sha`; `isCrossRepository` = project ids differ;
   `changedFiles=int(changes_count)` only when it is a digit string; notes →
   `comment()` with `noteable_type`, `noteable_iid`; head repository from the fetched source
   project (`path`, `namespace.full_path`).
10. Old existing-verb tests for `get_check_results` in `test/test_forge_adapters.py` are
    updated to `CheckResult`.

## Where to change
- `vibey_gh/forge.py`, `vibey_gh/interfaces/forge_adapter_interface.py` (declare V5-V9, change
  V10's return type; `from vibey_gh.forge import CheckResult`).
- `vibey_gh/forge_github.py` (constants at module top, beside `GH_DEFAULT_HOST`; verbs appended per C9).
- `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py` (verbs appended).
- New: `vibey_gh/forge_forgejo_facts.py`, `vibey_gh/forge_gitlab_facts.py`,
  `vibey_gh/interfaces/forge_forgejo_facts_interface.py`,
  `vibey_gh/interfaces/forge_gitlab_facts_interface.py` (interfaces import only stdlib,
  `vibey_gh.forge` and other interfaces — precedent `forge_adapter_interface.py:27-33`).

## Acceptance criteria
- [ ] For each of V5-V10, a `fake_gh` test pins the exact GitHub argv and cwd.
- [ ] `set(ForgejoFacts().change_request(PULL, STATUSES, REVIEWS)) ==
  set(CHANGE_REQUEST_FACT_KEYS)` for a fixture with `changed_files`, and minus
  `"changedFiles"` without; the same for GitLab and for the threaded keys.
- [ ] `merge_train.judge(ForgejoFacts().change_request(...), cfg)` on a green, mergeable,
  approved fixture is ready (proves the schema feeds the unchanged judge).
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
`test/test_forge_change_request_reads.py`:
- `test_github_facts_ask_the_merge_trains_fields` (argv `pr view 7 --json <fields>`; bound
  adds `--repo o/r` after `7`; non-object → problem).
- `test_github_thread_asks_pr_automations_fields`.
- `test_github_text_reproduces_promotions_messages` (rc 1 with `stderr="x  y\n"` → `"x y"`;
  empty streams → `"gh pr view exited 1"`; `"null"` → "did not return a title and body").
- `test_github_comment_bodies_return_stdout_and_stderr_together`.
- `test_github_changed_paths_page_with_gh_placeholders` (argv
  `["api","--paginate","repos/{owner}/{repo}/pulls/7/files?per_page=100"]`, concatenated
  pages, rename adds the old path, unreadable listing → problem).
- `test_github_check_results_count_only_finished_checks`.
- `test_forgejo_facts_translate_a_pull_request` (states, draft by flag and by `WIP:`,
  conflicting, cross-repository, `changed_files` present/absent, rollup mapping incl.
  `(pull_request)` suffix stripped, review decision incl. dismissed review).
- `test_forgejo_reads_route_to_pulls_statuses_reviews_and_comments` (RoutedTransport keys).
- `test_gitlab_facts_translate_a_merge_request` and
  `test_gitlab_reads_use_the_repository_commits_statuses_route`.
- `test_every_read_passes_a_problem_through_with_nothing_read` (parametrised over forge × verb).
- `test_the_facts_feed_the_unchanged_merge_judge`.

## Checks the lane must run (all must pass)
Same block as Part 0a, with the focused run
`python -m pytest -q --no-cov test/test_forge_change_request_reads.py test/test_forge_adapters.py`.

## Out of scope
Listings, writes, issues (later Wave-1 parts); every consuming module (Wave 2). Do not edit
CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees -- the docs wave
owns those. Do not push, open PRs, or change git remotes. Commit locally with a
Conventional Commit message when done.

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
appending to the end of the file: `write_file` the new methods (four-space indented) to
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/scratch/append.py`, then in one command run
`cat /private/tmp/claude-501/storm/qwenstorm-3.0.0/scratch/append.py >> vibey_gh/forge_github.py && rm /private/tmp/claude-501/storm/qwenstorm-3.0.0/scratch/append.py`,
then run black once.
Read only the slices you need (`sed -n '120,200p' file`). Do not rewrite a whole module.

---
