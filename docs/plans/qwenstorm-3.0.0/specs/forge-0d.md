## Title
feat(gh): the forge adapter writes to change requests — create, edit, merge, ready, close, comment, label

## Why
Every write the merge train, promotion, reconcile and PR automation make is a raw `gh`
command (inventory MT3-MT7, MT15-16, PR3, PR5-6, PR8-9, PA3, PA6-12, RC1, RC3-5). The
adapter's existing mutation verbs cannot stand in: `create_comment`,
`update_change_request`, `merge_change_request` and `create_release` send their commands
through `survey`, which demands JSON, but `gh pr comment/edit/merge` print a URL or nothing,
so each reports failure after succeeding (`forge_github.py:223-264`); Forgejo/GitLab
`create_comment` post the raw text instead of `{"body": …}` (`forge_forgejo.py:191-196`,
`forge_gitlab.py:202-209`); Forgejo merge sends no `Do` (`forge_forgejo.py:222-224`); GitLab
merge uses POST where the API takes PUT (`forge_gitlab.py:235-237`). None of them has a
caller, so they are reshaped to the shapes their first callers need (ADR 0001). The
mirror-fork fetch hard-codes `https://github.com/` (`pr_automation.py:688`).

## Required behaviour
GitHub verbs use `_run` and report failure with the texts given, so every caller's message
stays byte-identical. `label` below is `"gh <sub> <sub>"`.
1. **V2 `fork_clone_url(owner, name)`** — empty owner or name → `("", "the change request
   names no fork repository")`. GitHub `f"https://github.com/{owner}/{name}.git"` (today's
   literal, even on GitHub Enterprise); Forgejo/GitLab `f"https://{self.host}/{owner}/{name}.git"`.
2. **V16 `create_change_request(*, base, head, title, body)`** — GitHub
   `self._scoped(["pr", "create"], ["--base", base, "--head", head, "--title", title,
   "--body", body])`; rc ≠ 0 → `(None, _failed(run, "gh pr create"))`; digits of the last
   `/` segment of stripped stdout → `(int, "")`, none → `(None, "`gh pr create` printed no
   pull request number")`. Forgejo POST `repos/{R}/pulls` `{"base", "head", "title",
   "body"}` → `number`. GitLab POST `projects/{P}/merge_requests` `{"source_branch": head,
   "target_branch": base, "title", "description": body}` → `iid`.
3. **V17 `update_change_request(number, *, title, body)`** (replaces the old signature) —
   GitHub, byte-identical to `promote.py:331-352, 391-396`: `_run(self._scoped(["pr", "edit",
   str(number)], ["--title", title, "--body", body]))`; ok → `(True, "")`; else
   `detail = " ".join((stderr or stdout or "").split())[:300] or f"gh pr edit exited {rc}"`;
   when `_PROJECTS_CLASSIC` (moved here from `promote.py:50-53`, regex
   `r"projects \(classic\)|projectcards"`, `re.IGNORECASE`) does not match → `(False,
   detail)`; when it does, `_run(["api", f"repos/{{owner}}/{{repo}}/pulls/{number}",
   "--method", "PATCH", "-f", f"title={title}", "-f", f"body={body}"])`; ok → `(True, "")`,
   else `(False, f"{detail}; the REST fallback failed too — {detail2}")` with `detail2`
   built the same way with `"gh api"`. Forgejo PATCH `repos/{R}/pulls/{n}` `{"title",
   "body"}`; GitLab PUT `projects/{P}/merge_requests/{n}` `{"title", "description"}`.
4. **V18 `merge_change_request(number, *, method, commit_body=None, bypass_rules=False)`**
   (replaces the old signature) — GitHub `self._scoped(["pr", "merge", str(number)],
   [f"--{method}"])` + (`["--body", commit_body]` when not `None`) + (`["--admin"]` when
   `bypass_rules`); fail → `(False, _failed(run, "gh pr merge", with_stdout=True))`.
   Forgejo POST `repos/{R}/pulls/{n}/merge` `{"Do": method, "force_merge": bypass_rules}`
   plus `"MergeMessageField": commit_body` when given; `method` outside
   `squash|rebase|merge` → problem. GitLab: `method == "rebase"` →
   `NotSupported(GITLAB, "merge_change_request(method='rebase')", "GitLab sets the merge
   method per project, not per merge")`; `bypass_rules` → `NotSupported(GITLAB,
   "merge_change_request(bypass_rules=True)", "GitLab has no per-merge override of approval
   rules")`; else PUT `projects/{P}/merge_requests/{n}/merge` `{"squash": method ==
   "squash"}` plus `squash_commit_message` (squash) or `merge_commit_message` (merge) =
   `commit_body` when given.
5. **V19 `mark_ready(number)`** — GitHub `self._scoped(["pr", "ready", str(number)], [])`,
   fail → `_failed(run, "gh pr ready")`. Forgejo: GET the pull; strip
   `r"^\s*(?:WIP:|\[WIP\])\s*"` (case-insensitive) from the title; unchanged and not `draft`
   → `(True, "")`; else PATCH `repos/{R}/pulls/{n}` `{"title": stripped}`. GitLab: same with
   `r"^\s*(?:Draft:|\[Draft\]|\(Draft\))\s*"` and PUT on the merge request.
6. **V20 `close_change_request(number)`** — GitHub `self._scoped(["pr", "close",
   str(number)], [])`; Forgejo PATCH pull `{"state": "closed"}`; GitLab PUT
   `{"state_event": "close"}`.
7. **V21 `comment_on_change_request(number, body)`** — GitHub `self._scoped(["pr",
   "comment", str(number)], ["--body", body])`, fail → `_failed(run, "gh pr comment")`.
   Forgejo POST `repos/{R}/issues/{n}/comments` `{"body"}` (pull-request conversation lives
   on the issue). GitLab POST `projects/{P}/merge_requests/{n}/notes` `{"body"}`.
   **Remove `create_comment`** from the protocol and all three adapters.
8. **V22 `add_label(number, label)`** — GitHub `self._scoped(["pr", "edit", str(number)],
   ["--add-label", label])`; Forgejo POST `repos/{R}/issues/{n}/labels`
   `{"labels": [label]}`; GitLab PUT merge request `{"add_labels": label}`.
9. **V23 `remove_label(number, label)`** — GitHub `self._scoped(["pr", "edit",
   str(number)], ["--remove-label", label])`; Forgejo: find the id in
   `_pages(f"repos/{R}/labels")`, none → `(True, "")`, else DELETE
   `repos/{R}/issues/{n}/labels/{id}`; GitLab PUT `{"remove_labels": label}`.
10. **V24 `create_label(name, *, colour, description, update_existing)`** — GitHub
    `self._scoped(["label", "create", name], ["--color", colour, "--description",
    description])` + `["--force"]` when `update_existing`. Forgejo: look the name up in
    `_pages(f"repos/{R}/labels")`; found and `update_existing` → PATCH `repos/{R}/labels/{id}`
    `{"color": f"#{colour}", "description"}`; found otherwise → `(False, f"label {name!r}
    already exists")`; absent → POST `repos/{R}/labels` `{"name", "color": f"#{colour}",
    "description"}`. GitLab: POST `projects/{P}/labels`; a `"GitLab API error 409"` problem
    with `update_existing` → PUT `projects/{P}/labels/{quote(name, safe='')}` `{"color",
    "description"}`.
11. **V25 `update_change_request_branch(number)`** — GitHub: `R` from V1;
    `_run(["api", f"repos/{R}/pulls/{number}/update-branch", "--method", "PUT"])`; ok →
    `(True, "")`; else `lines = (run.stderr or "").strip().splitlines()`, `(False, lines[-1]
    if lines else "refused")` (today's text, `reconcile.py:258-261`, without its IndexError
    on whitespace-only stderr). Forgejo POST `repos/{R}/pulls/{n}/update?style=merge`.
    GitLab → `NotSupported(GITLAB, "update_change_request_branch", "GitLab can only rebase a
    merge request's source branch server-side, which rewrites it")`.

## Where to change
`vibey_gh/interfaces/forge_adapter_interface.py` (declare V2, V16, V19-V25; replace the
signatures of `update_change_request` and `merge_change_request`; delete `create_comment`),
`vibey_gh/forge_github.py` (`import re`; `_PROJECTS_CLASSIC` at module top),
`vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, `vibey_gh/forge.py` only if a
docstring references a removed verb.

## Acceptance criteria
- [ ] `grep -n "create_comment" vibey_gh test` finds nothing.
- [ ] A `fake_gh` test pins every GitHub argv above, unbound and (for `pr …`) bound.
- [ ] GitLab's three NotSupported answers are asserted verbatim.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
`test/test_forge_change_request_writes.py`:
- `test_github_create_reads_the_number_from_the_url` (and no URL → problem).
- `test_github_update_falls_back_to_rest_only_for_projects_classic` (three cases:
  success; plain refusal → collapsed detail; Projects-classic refusal then REST success;
  both fail → the joined message).
- `test_github_merge_argv_orders_method_body_admin` (`pr merge 5 --squash --body B --admin`).
- `test_github_ready_close_comment_label_argvs` (parametrised).
- `test_github_create_label_forces_only_when_asked`.
- `test_github_update_branch_reports_the_last_stderr_line_or_refused`.
- `test_fork_clone_url_per_forge`.
- `test_forgejo_writes_route_and_send_json` (RoutedTransport; assert the JSON bodies).
- `test_forgejo_mark_ready_strips_wip_and_skips_a_ready_pull`.
- `test_forgejo_labels_are_looked_up_by_name`.
- `test_gitlab_writes_route_and_refuse_what_gitlab_cannot_do`.
Update `test/test_forge_adapters.py` where it drives `create_comment`,
`update_change_request` or `merge_change_request` (`test_github_reads_and_writes_every_
neutral_verb`, `test_gitlab_adapter_covers_list_and_mutation_paths`,
`test_forgejo_adapter_covers_list_and_mutation_paths`).

## Checks the lane must run (all must pass)
Same block as Part 0a, focused on `test/test_forge_change_request_writes.py test/test_forge_adapters.py`.

## Out of scope
Consumers (Wave 2). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md
or skill trees -- the docs wave owns those. Do not push, open PRs, or change git remotes.
Commit locally with a Conventional Commit message when done.

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
