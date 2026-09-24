## Title
feat(gh): PR automation, the durable state comment and install notices reach the forge only through the adapter

## Why
`vibey_gh/pr_automation.py` (PA1-PA12), the shared state comment in
`vibey_gh/github_state.py` (GS3-GS5) and `install.installation_notices` (IN1) call `gh`
directly; the fork mirror even fetches from a hard-coded `https://github.com/`
(`pr_automation.py:688`). All ignore `[platform]` (ADR 0002, sub-doctrine 8.b). Deltas
(C3): D1, D3 (install notice), D5.

## Required behaviour
pr_automation.py:
1. Delete `_gh_json = github_state.gh_json` (469) and every `subprocess` `gh` call.
2. `fetch_pr(number, *, forge=None)`: `facts, problem = forge.change_request_with_thread(
   number)`; raise on problem; return `facts`.
3. `evaluate_pr(number, head_sha, cfg, *, forge=None)` and `ready_draft(number, head_sha,
   cfg, *, forge=None)`: resolve with `cfg`, pass to `fetch_pr`. `ready_draft`'s gh call →
   `ok, problem = forge.mark_ready(number)`; not ok →
   `RuntimeError(f"could not mark PR ready: {problem}")`.
4. `upsert_state(number, state, summary, comments, *, forge=None)` →
   `github_state.upsert_comment(…, forge=forge)`. `record(number, payload, kind, *,
   forge=None)` passes `forge` to `fetch_pr` and `upsert_state`.
5. `exhausted_pull_requests(cfg, *, forge=None)`: bind (C6.2);
   `bound.labelled_open_change_request_numbers(label=EXHAUSTED_LABEL)`; raise on problem;
   return `list(numbers)`.
6. `self_heal(number, cfg, *, forge=None)`: `fetch_pr`/`upsert_state` with `forge`; the
   label removal binds and calls `bound.remove_label(number, EXHAUSTED_LABEL)` (result
   ignored).
7. `ensure_labels(*, forge=None)`: for each definition `forge.create_label(name,
   colour=colour, description=description, update_existing=True)` (results ignored).
8. `mirror_fork(number, cfg, *, forge=None)`: unchanged checks; `url, problem =
   forge.fork_clone_url(owner, repo)` (raise on problem) → `git fetch --quiet <url> <head>`;
   `replacement, problem = forge.create_change_request(base=str(pr["baseRefName"]),
   head=branch, title=f"Repair #{number}: {title}", body=body)`; `None` →
   `RuntimeError(f"could not open replacement pull request: {problem}")`; then
   `forge.add_label(replacement, EXTERNAL_REPAIR_LABEL)`,
   `forge.comment_on_change_request(number, <same text>)`,
   `forge.close_change_request(number)` — **unbound**, as today.
github_state.py:
9. `upsert_comment(number, body, comments, pattern, *, subject="pr", error=…, forge=None)`:
   `forge = ForgeSelector().resolve(forge)`; `name, problem = forge.repository_name()` →
   raise `RuntimeError(problem)` (on GitHub this is today's
   `"gh repo view --json nameWithOwner: <stderr>"`); `bound = forge.for_repository(name)`;
   the existing-comment search is unchanged; none → `bound.comment_on_change_request` when
   `subject == "pr"`, else `bound.comment_on_issue`; found → `bound.update_comment(existing,
   body)`; not ok → `RuntimeError(f"{error}: {problem}")`.
10. `gh_json`, `repository`, `_transport`, `marker_pattern`, `parse_payload`, `render_body`
    are unchanged. Rewrite the module docstring's last paragraph (14-16): writes go through
    the forge adapter; `gh_json` and `repository` remain the GitHub CLI facade kept for the
    GitHub-only commands (`forge-snapshot`, `forecast`, `cli.py:598,835`).
install.py:
11. `installation_notices(*, forge=None)`: `names, problem =
    ForgeSelector().resolve(forge).secret_names()`; on problem return `(*notices,
    f"could not list repository secrets ({problem}); skipping secret/permission checks")`
    (D3: was `"gh not found; skipping …"` for a missing `gh`, and silence for any other
    failure); otherwise the two "configure repository secret" notices as today.

## Where to change
`vibey_gh/pr_automation.py`, `vibey_gh/github_state.py`, `vibey_gh/install.py` (only
`installation_notices`, 465-485). Imports as C6.1. Check for an import cycle with
`python -c "import vibey_gh.github_state, vibey_gh.pr_automation"`.

## Acceptance criteria
- [ ] `grep -nE '"gh"' vibey_gh/pr_automation.py vibey_gh/install.py` finds nothing, and
  `github_state.py`'s only `gh` argv is in `gh_json`/`repository`.
- [ ] `test/test_gh_transport.py`'s `upsert_comment` witness tests (482-531) pass with only
  `forge=GitHubForge(root=workdir)` added to the "after" lambdas — byte-for-byte, same cwd.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
- `test/test_gh_transport.py`: add `forge=GitHubForge(root=workdir)` to each
  `github_state.upsert_comment(...)` call in 482-531 (Before and every expectation stay).
- `test/test_pr_automation.py`: `test_mirror_fork_uses_the_forges_clone_url_and_verbs`,
  `test_ready_draft_raises_the_forges_problem`, `test_self_heal_binds_before_removing_the_
  label`, `test_exhausted_listing_raises_when_the_forge_cannot_list`,
  `test_ensure_labels_updates_existing_definitions` (all `RecordingForge`). Widen every
  `monkeypatch.setattr(pa, "fetch_pr", lambda n: …)` and `"upsert_state", lambda *a: …`
  (lines ~385-431 and wherever else `grep -n 'setattr(pa, "fetch_pr"\|setattr(pa,
  "upsert_state"'` finds them) to accept `**_`. The `subprocess.run`-faking tests of
  `self_heal`/`ensure_labels`/`mirror_fork`/`ready_draft`/`upsert_state` (e.g. 380-431,
  555-580) either inject `forge=GitHubForge(root=tmp_path)` (keeping their argv asserts) or
  move to `RecordingForge`; `pa._gh_json` at 568 is removed from the test.
  `test_installation_notices_report_missing_secrets` /
  `…_degrade_when_gh_is_not_installed` (162-187) inject a `RecordingForge(secret_names=…)`
  and assert the new notice text; `test_install_finishes_when_gh_is_not_on_path` writes
  `[platform]\nkind = "github"\n` into its repository's `.vibey-gh.toml` so it never
  reaches for a Forgejo host.

## Checks the lane must run (all must pass)
Part 1's block, inlined here so this issue is self-contained:
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_pr_automation.py test/test_gh_transport.py test/test_gh_cli.py test/test_forge_snapshot.py
python -m pytest -q
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check src/vibey_tools/gh
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check src/vibey_tools/gh
git diff --stat
```

## Out of scope
`issue_automation.py`, `conversation.py` (Part 5 — they keep calling `upsert_comment`
without `forge`), `cli.py`, `forge_snapshot.py`, `delivery_sources.py`, adapter files,
the rest of `install.py`. Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
GEMINI.md or skill trees -- the docs wave owns those. Do not push, open PRs, or change git
remotes. Commit locally with a Conventional Commit message when done.

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
appending to the end of the file: write the four-space-indented method bodies with
`write_file` to `STORM/scratch/forge_methods.py`, then
append them in one command
(`cat STORM/scratch/forge_methods.py >> vibey_gh/forge_github.py`),
delete the scratch file, then run black once.
Read only the slices you need (`sed -n '120,200p' file`). Do not rewrite a whole module.

---
