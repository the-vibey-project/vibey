## Title
feat(gh): the merge train reaches the forge only through the adapter

## Why
`vibey_gh/merge_train.py` runs `gh` directly at 14 sites through two private runners
(inventory MT1-MT16), so it ignores `[platform]` and would drive GitHub on a repository
whose declared forge is the sovereign default (ADR 0002, sub-doctrine 8.b). Every verb it
needs exists after Wave 1. Deltas that apply (C3): D1, D2, D5.

## Required behaviour
1. No `gh` runner remains: delete `_gh_json` (67-73), `_gh` (76-81), and the now-unused
   `import json`, `import subprocess`, `cast`, and `_PR_FIELDS` (237-246; the field list and
   its comments now live in `forge_github.CHANGE_REQUEST_FACT_FIELDS`).
2. Signatures (all additions keyword-only and last, per C6.1; `cli.py` is not changed):
   `hold_for_review(verdict, cfg, label=NEEDS_REVIEW_LABEL, *, forge=None)`,
   `pull_request(number, cfg=None, *, forge=None)`, `_include_changed_paths(pr, forge)`,
   `_include_exact_head_gate(pr, forge=None)`,
   `open_pull_requests(cfg, number=None, *, forge=None)`,
   `delete_head_branch(pr, *, forge=None)`,
   `merge(number, method="squash", squash_body=None, *, forge=None)`.
3. Replacements (none of these bind — today's sites passed no `--repo`):
   - `hold_for_review` (84-121): `ok, _ = forge.add_label(verdict.number, label)`; if not ok:
     `forge.create_label(label, colour="D93F0B", description="Outside contribution awaiting
     the code owner", update_existing=False)` then `forge.add_label(...)` again. Then
     `bodies, problem = forge.change_request_comment_bodies(verdict.number)`; return when
     `not problem and any(_NOTIFIED_MARKER in body for body in bodies)`; else
     `forge.comment_on_change_request(verdict.number, <the same f-string>)`.
   - `pull_request` (249-254): `facts, problem = forge.change_request_facts(number)`;
     `if problem: raise RuntimeError(problem)`; then `_include_exact_head_gate(facts,
     forge)`, and `_include_changed_paths(facts, forge)` when `cfg and cfg.protected_paths`.
   - `_include_changed_paths` (257-287): `listing, problem = forge.changed_paths(
     int(pr["number"]))`; return (leaving the keys absent) when `problem or listing is None`;
     else set `CHANGED_PATHS_KEY` / `LISTED_FILES_KEY`. Keep its docstring's reasoning.
   - `_include_exact_head_gate` (290-313): same early returns; `forge =
     ForgeSelector().resolve(forge)`; `checks, problem = forge.get_check_results(sha)`;
     raise on problem; append `{"name": check.name, "status": "COMPLETED", "conclusion":
     "SUCCESS"}` for each `check.name in GATES and check.conclusion == "success"`.
   - `open_pull_requests` (316-334): `numbers, problem = forge.open_change_request_numbers(
     base=cfg.integration_branch)`; raise on problem; `pull_request(n, cfg, forge=forge)`.
   - `delete_head_branch` (348-353): `ok, _ = forge.delete_branch(str(pr["headRefName"]))`.
   - `merge` (356-388): `body = squash_body if squash_body is not None and method ==
     "squash" else None`; plain `forge.merge_change_request(number, method=method,
     commit_body=body)` → `(True, False, "")`; then with `bypass_rules=True` → `(True, True,
     "")`; else `(False, True, " ".join(problem.split())[:300])`.
4. The module-level helpers stay module-level (this module converges on classes later,
   ADR-0016; its docstrings already say so).

## Where to change
`vibey_gh/merge_train.py` only (lines above). Imports:
`from vibey_gh.forge_selector import ForgeSelector`,
`from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface`.

## Acceptance criteria
- [ ] `grep -nE '"gh"|subprocess|_gh_json|_gh\(' vibey_gh/merge_train.py` finds nothing.
- [ ] The existing `fake_gh` tests in `test/test_gh_internals.py` (318-425, 780-832), with
  `forge=GitHubForge(root=Path.cwd())` injected and nothing else about them changed except
  the field-list import, still pass — the byte-for-byte proof.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
- `test/test_merge_train_forge.py` (new, `RecordingForge`): `test_the_train_reads_facts_
  checks_and_paths_through_the_forge`, `test_a_forge_that_cannot_list_stops_the_train`
  (raises the problem), `test_merge_falls_back_to_bypassing_rules_and_reports_the_second_
  problem`, `test_hold_creates_a_missing_label_and_mentions_the_owner_once`,
  `test_a_forgejo_shaped_forge_runs_the_same_train` (facts from `ForgejoFacts`).
- `test/test_gh_internals.py`: inject `forge=GitHubForge(root=Path.cwd())` into every
  merge-train call at 318-425 and 780-832; replace `merge_train._PR_FIELDS` with
  `forge_github.CHANGE_REQUEST_FACT_FIELDS`; add `monkeypatch.delenv("GH_REPO",
  raising=False)` to the two branch-deletion tests.
- `test/test_gh.py:530-606`: the four tests monkeypatching `merge_train._gh_json` use a
  `RecordingForge` (`change_request_facts`, `get_check_results` answering `CheckResult`s,
  `open_change_request_numbers`); widen the `pull_request` lambda to `lambda number,
  cfg=None, **_:`.
- `test/test_protected_paths.py:225-295`: `_recording` becomes a `RecordingForge` answering
  `change_request_facts` and `changed_paths`; assert `("changed_paths", 7)` was (or was not)
  called; the three parametrised failure cases become `changed_paths` answering
  `(None, "<problem>")`; widen the `pull_request` lambda.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_merge_train_forge.py test/test_gh.py test/test_gh_internals.py test/test_protected_paths.py test/test_gh_cli.py
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
`cli.py`, `reconcile.py`, `pr_automation.py`, every adapter file, `test/conftest.py`,
`test/test_gh_cli.py` (its merge-train tests replace the functions by name and must pass
unmodified). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill
trees -- the docs wave owns those. Do not push, open PRs, or change git remotes. Commit
locally with a Conventional Commit message when done.

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
appending to the end of the file: write the four-space-indented methods with `write_file` to
`STORM/scratch/append.py` (a concrete path outside the
clone — `write_file` expands nothing), append them in one command
(`cat STORM/scratch/append.py >> vibey_gh/forge_github.py`),
delete the scratch file, then run black once.
Read only the slices you need (`sed -n '120,200p' file`). Do not rewrite a whole module.

---
