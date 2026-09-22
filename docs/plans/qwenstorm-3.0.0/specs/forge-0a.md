## Title
feat(gh): forge-adapter foundation — scope rule, paged reads, NotSupported, repository_name and delete_branch

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md`) makes the sovereign forge the
default, and vibey-gh ADR 0002 set `[platform] kind = "forgejo"` (`vibey_gh/config.py:288`),
but only the clean-repo survey reaches the forge through the adapter
(`vibey_gh/tidy.py:128-151`); 63 other forge calls shell out to `gh` (inventory above).
Before any module can move, the adapter needs the GitHub `--repo` rule (C2), a way to say
NotSupported (C1), paged Forgejo/GitLab reads (C4), and fixes to verbs the sovereign default
already runs: `ForgejoForge.open_change_request_heads` reads `head.branch`
(`forge_forgejo.py:72`) but Forgejo's field is `head.ref`, so the survey never excludes an
open pull request's head; `releases` never marks a draft (`forge_forgejo.py:85`);
`get_change_request`/`get_issue` read the global `id` instead of the per-repository `number`
(`forge_forgejo.py:102,124`); `get_issue_thread` falls back to a non-existent
`pulls/{n}/comments` route (`forge_forgejo.py:136-139`); and `ForgejoTransport.survey`
treats an empty 2xx body as a failure (`forgejo_transport.py:67-72`), so every DELETE would
read as refused. None of the Forgejo/GitLab listings page (Forgejo returns at most 50 per
page). ADR 0001: verbs answer `(value, problem)`; ADR-0016: every class has an interface.

## Required behaviour
1. `vibey_gh/forge.py` gains `NotSupported` (frozen dataclass: `kind: ForgeKind`, `verb: str`,
   `reason: str`; property `problem -> str` = `f"{self.kind.value} does not support
   {self.verb}: {self.reason}"`), added to `__all__`.
2. `GitHubForge` gains:
   - `_scoped(self, head: list[str], tail: list[str]) -> list[str]` = `head + (["--repo",
     self.repository] if self.repository else []) + tail`;
   - `_read(self, args: Sequence[str], *, stdin: str | None = None) -> tuple[Any, str]`:
     `self.transport.json(args, cwd=self.root, stdin=stdin)`; `FileNotFoundError` →
     `(None, f"the GitHub CLI (`{exe}`) is not installed")`; `RuntimeError` →
     `(None, str(error))` (this is `"gh <args>: <stderr>"`, the exact text
     `merge_train._gh_json`, `github_state.gh_json` and `rulesets._api` raise today);
     `ValueError` (JSON) → `(None, f"`{exe} {args[0]} {args[1]}` returned output that is not
     JSON")`;
   - `_run(self, args, *, stdin=None) -> tuple[subprocess.CompletedProcess[str] | None, str]`:
     `self.transport.run(args, cwd=self.root, stdin=stdin)`, or `(None, <not installed>)`;
   - `_failed(run, label: str, *, with_stdout: bool = False) -> str` (static):
     `(run.stderr or (run.stdout if with_stdout else "") or "").strip()` or
     `f"`{label}` exited {run.returncode}"`.
   - `repository_name()` (V1) and `delete_branch()` (V3), below.
   - The existing verbs that build `repos/{R}/…` (`list_artifacts`, `get_reviews`,
     `get_check_results`, `set_protected_ref`, `get_protected_refs`) take `R` from
     `repository_name()` and return their empty value plus its problem when it fails. The
     old `_repository()` helper is removed.
3. **V1 `repository_name(self) -> tuple[str, str]`**
   - GitHub: `self.repository` if bound; else `os.environ["GH_REPO"]` if set and non-empty;
     else `_read(["repo", "view", "--json", "nameWithOwner"])` → `nameWithOwner` (a
     non-empty str) or `("", "`gh repo view` did not name the repository")`; `_read`'s
     problem passes through unchanged.
   - Forgejo: `(self.repository, "")`, or `("", "no Forgejo repository is named: set
     [platform] repository, or give the clone an origin remote")` when empty.
   - GitLab: the same with "GitLab".
4. **V3 `delete_branch(self, branch: str) -> tuple[bool, str]`**
   - GitHub: `R` from V1; `_run(["api", f"repos/{R}/git/refs/heads/{branch}", "--method",
     "DELETE"])`; rc 0 → `(True, "")`; else `(False, _failed(run, "gh api", with_stdout=True))`.
   - Forgejo: `DELETE repos/{R}/branches/{quote(branch, safe="/")}`.
   - GitLab: `DELETE projects/{P}/repository/branches/{quote(branch, safe="")}`.
5. `vibey_gh/forge_selector.py`:
   - `_github` binds `repository=cfg.platform.repository` (no origin read): `gh` resolves the
     repository itself from `$GH_REPO` and the clone (honouring `gh repo set-default`, which
     an origin-URL parse ignores), and every call site relied on that. `_forgejo`/`_gitlab`
     keep reading origin and additionally pass `host=host`.
   - New `current(self) -> ForgeAdapterInterface` = `self.select(load_config())`.
   - New `resolve(self, forge: ForgeAdapterInterface | None, cfg: GhConfig | None = None) ->
     ForgeAdapterInterface`: `forge` if not `None`, else `self.select(cfg)` if `cfg` is not
     `None`, else `self.current()`.
   - `interfaces/forge_selector_interface.py` declares both with docstrings.
6. `ForgejoForge` / `GitLabForge` gain `host: str = "forgejo.local"` / `"gitlab.com"` as the
   **last** dataclass field, `_pages(path, *, most=None)` and `_absent(problem)` (C4).
   Mutation bodies are always `json.dumps(payload)`.
7. Both transports: a 2xx response whose body is empty or whitespace answers `({}, "")`;
   new field `timeout: float = 30.0` passed as `urllib.request.urlopen(req,
   timeout=self.timeout)`.
8. Fix the verbs the sovereign default runs today:
   - Forgejo `open_change_request_heads`: `_pages(f"repos/{R}/pulls?state=open",
     most=limit)`, head = `pull["head"]["ref"]`.
   - Forgejo `releases`: `_pages(f"repos/{R}/releases", most=limit)`,
     `draft=bool(row.get("draft"))`.
   - Forgejo `get_change_request`: `number=int(val["number"])`, `head_ref=head["ref"]`;
     `get_issue`: `number=int(val["number"])`.
   - Forgejo `get_issue_thread`: only `repos/{R}/issues/{n}/comments` (paged); author =
     `user.login`, falling back to `user.username`.
   - GitLab `open_change_request_heads` / `releases`: page through `_pages(…, most=limit)`
     (GitLab caps `per_page` at 100; tidy asks for 200 heads).
9. GitHub behaviour of the clean-repo survey is unchanged: `test/test_forge_github.py`
   passes untouched.

## Where to change
- `vibey_gh/forge.py` (after `ProtectedRef`, line 164): `NotSupported`.
- `vibey_gh/interfaces/class_contracts.py`: `NotSupportedInterface(Protocol)` with
  `kind`, `verb`, `reason`, `problem` properties, beside `ProtectedRefInterface`
  (class_contracts.py:~169); export it from `vibey_gh/interfaces/__init__.py` the way
  `ChangeRequestInterface` is exported.
- `vibey_gh/interfaces/forge_adapter_interface.py:36-123`: declare V1 and V3 under
  `# --- Repository ---`, with one-line docstrings in the existing style.
- `vibey_gh/forge_github.py:37-299`: helpers and verbs above; `import os`,
  `import subprocess`, `from collections.abc import Sequence`.
- `vibey_gh/forge_forgejo.py:26-270`, `vibey_gh/forge_gitlab.py:26-285`: `host`, `_pages`,
  `_absent`, V1, V3, fixes in 8.
- `vibey_gh/forgejo_transport.py:45-76`, `vibey_gh/gitlab_transport.py:48-81`: empty body,
  `timeout`.
- `vibey_gh/forge_selector.py:67-89`: `_github`, `_forgejo`, `_gitlab`, `current`, `resolve`
  (`from vibey_gh.config import load_config`).
- `test/forge_doubles.py` (new): `RoutedTransport` and `RecordingForge` exactly as C7
  describes, each with a class docstring.

## Acceptance criteria
- [ ] `python -m pytest -q` passes with 100% coverage.
- [ ] `test/test_forge_github.py` is unmodified and passes.
- [ ] `ForgeSelector().select(GhConfig(root=tmp))` still equals
  `ForgejoForge(root=tmp, transport=ForgejoTransport(host="forgejo.local", token=""))`
  (`test/test_platform.py:192-198` passes unmodified).
- [ ] `grep -n "_repository()" vibey_gh/forge_github.py` finds nothing.
- [ ] black, isort, mypy, ruff check and ruff format --check are clean (commands below).

## Tests to write first (TDD)
`test/test_forge_foundation.py`:
- `test_not_supported_names_the_forge_the_verb_and_the_reason` — exact `problem` text; frozen.
- `test_github_scope_is_empty_until_bound` — `_scoped(["pr","view","7"], ["--json","x"])`
  unbound vs `for_repository("o/r")`.
- `test_github_repository_name_prefers_binding_then_gh_repo_then_gh` — `fake_gh`: bound → no
  call; `GH_REPO=a/b` → no call; unset → one `repo view --json nameWithOwner` in
  `str(tmp_path.resolve())`; failure → problem `"gh repo view --json nameWithOwner: boom"`;
  `{}` → "did not name the repository"; no `gh` on PATH → "is not installed".
- `test_github_read_turns_every_failure_into_a_problem` — rc 1, non-JSON, missing client.
- `test_github_delete_branch_runs_todays_argv` — `api repos/o/r/git/refs/heads/fix/thing
  --method DELETE`; refusal → `(False, <stderr>)`.
- `test_forgejo_and_gitlab_repository_name_and_delete_branch_routes` — `RoutedTransport`:
  `repos/o/r/branches/fix/thing DELETE`, `projects/o%2Fr/repository/branches/fix%2Fthing DELETE`;
  empty repository → problem.
- `test_forgejo_pages_until_a_short_page_and_reports_an_endless_listing` and the GitLab twin.
- `test_absent_recognises_only_the_404_sentence`.
- `test_transports_read_an_empty_success_as_an_empty_object` and
  `test_transports_pass_their_timeout` (monkeypatch `urllib.request.urlopen`).
- `test_forgejo_heads_read_head_ref_and_releases_read_draft` (the tidy fixes).
- `test_selector_binds_github_only_to_an_explicit_repository`,
  `test_selector_current_loads_the_configuration`, `test_resolve_prefers_injection_then_cfg`.
Update:
- `test/test_platform.py:270-276`: the GitHub assertion becomes `== ""` for an origin-only
  clone, and add an explicit-repository case.
- `test/test_forge_adapters.py`: `_github()` builds `GitHubForge(root=…, repository="o/r",
  transport=…)`; Forgejo fixtures use `{"head": {"ref": …}}` and `"number"` (lines 287, 305-306);
  the paged Forgejo/GitLab paths now end `page=1&limit=50` / `page=1&per_page=100`; the
  `urlopen` fake at the end of the file accepts `timeout`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_foundation.py test/test_forge_adapters.py test/test_platform.py test/test_forge_github.py test/test_tidy.py
python -m pytest -q                                   # whole suite, 100% line+branch
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check src/vibey_tools/gh
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check src/vibey_tools/gh
git diff --stat   # only the files this part owns
```

## Out of scope
Every module outside the adapter layer (`merge_train`, `promote`, … — Wave 2). No new verbs
beyond V1 and V3. Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or
skill trees -- the docs wave owns those. Do not push, open PRs, or change git remotes.
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
appending to the end of the file: write the four-space-indented method bodies with
`write_file` to `/private/tmp/claude-501/storm/qwenstorm-3.0.0/scratch/forge_methods.py`, then
append them in one command
(`cat /private/tmp/claude-501/storm/qwenstorm-3.0.0/scratch/forge_methods.py >> vibey_gh/forge_github.py`),
delete the scratch file, then run black once.
Read only the slices you need (`sed -n '120,200p' file`). Do not rewrite a whole module.

---
