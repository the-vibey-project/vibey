# Forge adapter: every vibey-gh command goes through `[platform]`

Thirteen issue specs in one file, in the order they must land. Source checkout: vibey
`develop` at `d47c196d`. Every path below is relative to `src/vibey_tools/gh/` (the vibey-gh
tenant, package `vibey_gh`) unless it starts with `src/` or `.github/`.

**Operator decision being implemented:** every vibey-gh command reaches the forge only
through `ForgeAdapterInterface`, so the sovereign default `[platform] kind = "forgejo"`
(`vibey_gh/config.py:288`, ADR 0002) is honoured everywhere, and `github` / `gitlab` keep
working when declared. Today only the clean-repo survey does (`vibey_gh/tidy.py:128-151`).

## Order, ownership, dependencies

Wave 1 is **sequential**: every Wave-1 part edits the same protocol and the same three
adapter classes, so each one starts from `develop` after the previous one has merged.
Wave 2 starts after 0g has merged; its six parts run **in parallel** and no two of them edit
the same file (source or test). No Wave-2 part edits `vibey_gh/cli.py`, `test/conftest.py`,
`vibey_gh/forge*.py`, `vibey_gh/*transport*.py` or anything under `vibey_gh/interfaces/`.

| Part | Title | Edits (and only these) | Needs merged first |
|---|---|---|---|
| 0a | Foundation + `repository_name`, `delete_branch` | `vibey_gh/forge.py`, `forge_github.py`, `forge_forgejo.py`, `forge_gitlab.py`, `forgejo_transport.py`, `gitlab_transport.py`, `forge_selector.py`, `interfaces/forge_adapter_interface.py`, `interfaces/forge_selector_interface.py`, `interfaces/class_contracts.py`; tests `test/forge_doubles.py` (new), `test/test_forge_foundation.py` (new), `test/test_forge_adapters.py`, `test/test_platform.py` | — |
| 0b | Change-request reads | the four adapter/protocol files, `forge.py`, new `forge_forgejo_facts.py`, `forge_gitlab_facts.py` + their interfaces; tests `test/test_forge_change_request_reads.py` (new), `test/test_forge_adapters.py` | 0a |
| 0c | Change-request listings + waiting for checks | adapter/protocol files, `forge.py`, the two facts modules, `interfaces/class_contracts.py`; tests `test/test_forge_change_request_lists.py` (new) | 0b |
| 0d | Change-request writes | adapter/protocol files; tests `test/test_forge_change_request_writes.py` (new), `test/test_forge_adapters.py` | 0c |
| 0e | Issues, comments, review threads | adapter/protocol files, `forge.py`, the two facts modules; tests `test/test_forge_conversation_verbs.py` (new) | 0d |
| 0f | Secrets, tags, releases | adapter/protocol files; tests `test/test_forge_releases.py` (new), `test/test_forge_adapters.py` | 0e |
| 0g | Branch rules | adapter/protocol files, new `forge_forgejo_rules.py` + interface; tests `test/test_forge_branch_rules.py` (new) | 0f |
| 1 | merge train | `vibey_gh/merge_train.py`; tests `test/test_gh.py`, `test/test_gh_internals.py`, `test/test_protected_paths.py`, `test/test_merge_train_forge.py` (new) | 0g |
| 2 | promotion | `vibey_gh/promote.py`; tests `test/test_promote.py` | 0g |
| 3 | reconcile + GitHub-release publication | `vibey_gh/reconcile.py`, `vibey_gh/github_release.py`; tests `test/test_reconcile.py`, `test/test_github_release.py` | 0g |
| 4 | PR automation + state comment + install notices | `vibey_gh/pr_automation.py`, `vibey_gh/github_state.py`, `vibey_gh/install.py`; tests `test/test_pr_automation.py`, `test/test_gh_transport.py` | 0g |
| 5 | issue automation + conversation | `vibey_gh/issue_automation.py`, `vibey_gh/conversation.py`; tests `test/test_issue_automation.py`, `test/test_conversation.py`, `test/test_gh_cli.py` (two tests only) | 0g |
| 6 | rulesets + flatten | `vibey_gh/rulesets.py`, `vibey_gh/flatten.py`; tests `test/test_rulesets.py`, `test/test_flatten.py` | 0g |

The operator's suggested four-way Wave-2 split was adjusted after checking which files each
part edits: `install.installation_notices` is tested in `test/test_pr_automation.py:162-187`
(so install moves in with PR automation), `pr_automation.upsert_state` writes through
`github_state.upsert_comment` (so github_state moves in with PR automation), and promotion
alone is 10 call sites, which is a lane on its own.

---

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
appending to the end of the file: write the four-space-indented block with `write_file` to
an absolute path under `/private/tmp/claude-501/storm/qwenstorm-3.0.0/scratch/`, append it
with one `cat ... >> vibey_gh/forge_github.py` command, remove it, then run black once.
Never a heredoc: the lane's shell runs one self-contained command per call.
Read only the slices you need (`sed -n '120,200p' file`). Do not rewrite a whole module.

---

## Call-site inventory (Part 0's source of truth)

71 rows: 63 forge calls plus 8 private runners/aliases, in the 11 modules named by the
operator. `R` = `github_state.repository()` (or `_gh_json("repo","view",…)`) resolved first.
"Verb" names the adapter operation (catalogue below); "bound" means the Wave-2 site binds
(C6.2).

| ID | file:line | today's `gh` argv (abridged) | returns / used as | verb | part |
|---|---|---|---|---|---|
| MT1 | merge_train.py:67-73 | `_gh_json` runner, process cwd, raises `RuntimeError("gh …: stderr")` | — | deleted | 1 |
| MT2 | merge_train.py:76-81 | `_gh` runner, returns `(rc==0, stdout+stderr)` | — | deleted | 1 |
| MT3 | merge_train.py:93 | `pr edit N --add-label L` | ok | `add_label` | 1 |
| MT4 | merge_train.py:96-104 | `label create L --color D93F0B --description "Outside contribution awaiting the code owner"` | ignored | `create_label(update_existing=False)` | 1 |
| MT5 | merge_train.py:105 | `pr edit N --add-label L` (retry) | ignored | `add_label` | 1 |
| MT6 | merge_train.py:110 | `pr view N --json comments -q .comments[].body` | text, marker search | `change_request_comment_bodies` | 1 |
| MT7 | merge_train.py:113-121 | `pr comment N --body B` | ignored | `comment_on_change_request` (unbound) | 1 |
| MT8 | merge_train.py:250 | `pr view N --json <_PR_FIELDS>` | dict for `judge` | `change_request_facts` | 1 |
| MT9 | merge_train.py:269-279 | `api --paginate repos/{owner}/{repo}/pulls/N/files?per_page=100` | raw pages → `parse_listing` | `changed_paths` | 1 |
| MT10 | merge_train.py:304 | `repo view --json nameWithOwner` | R | inside `get_check_results` | 1 |
| MT11 | merge_train.py:305 | `api repos/R/commits/SHA/check-runs` | `check_runs` | `get_check_results` | 1 |
| MT12 | merge_train.py:319-330 | `pr list --base INT --state open --json number --jq sort_by(.number)` | numbers | `open_change_request_numbers` | 1 |
| MT13 | merge_train.py:350 | `repo view --json nameWithOwner` | R | inside `delete_branch` | 1 |
| MT14 | merge_train.py:352 | `api repos/R/git/refs/heads/H --method DELETE` | ok | `delete_branch` | 1 |
| MT15 | merge_train.py:378-383 | `pr merge N --M [--body B]` | merged | `merge_change_request` | 1 |
| MT16 | merge_train.py:384-388 | `pr merge N --M [--body B] --admin` | merged, error text | `merge_change_request(bypass_rules=True)` | 1 |
| PR1 | promote.py:78-80 | `_gh(cfg, …)` runner, cwd root, `(rc==0, stdout.strip())` | — | deleted | 2 |
| PR2 | promote.py:85-99 | `pr list --base REL --head INT --state open --json number --jq '.[0].number // ""'` | int or None | `open_change_request_between` | 2 |
| PR3 | promote.py:111-127 | `pr create --base REL --head INT --title T --body B` | URL → number | `create_change_request` | 2 |
| PR4 | promote.py:132 | `pr checks N --watch --interval 30` | ok | `wait_for_checks` | 2 |
| PR5 | promote.py:139-140 | `pr merge N --M` | ok | `merge_change_request` | 2 |
| PR6 | promote.py:142 | `pr merge N --M --admin` | ok | `merge_change_request(bypass_rules=True)` | 2 |
| PR7 | promote.py:317-329 | `pr view N --json title,body` | (title, body) | `change_request_text` | 2 |
| PR8 | promote.py:331-337 | `pr edit N --title T --body B` | raise on failure | `update_change_request` | 2 |
| PR9 | promote.py:341-352 | `api repos/{owner}/{repo}/pulls/N --method PATCH -f title=T -f body=B` | Projects-classic fallback | inside `update_change_request` | 2 |
| PR10 | promote.py:386-389 | `PromotionPullRequest._gh` runner | — | deleted | 2 |
| PA1 | pr_automation.py:469 | `_gh_json = github_state.gh_json` alias | — | deleted | 4 |
| PA2 | pr_automation.py:472-484 | `pr view N --json <18 fields incl. comments, headRepository…>` | dict for `evaluate` | `change_request_with_thread` | 4 |
| PA3 | pr_automation.py:513-517 | `pr ready N` | raise on failure | `mark_ready` | 4 |
| PA4 | pr_automation.py:553-563 | `github_state.upsert_comment(subject="pr")` | state comment | via Part 4's `upsert_comment` | 4 |
| PA5 | pr_automation.py:582-596 | `pr list --repo R --state open --label EXHAUSTED --json number` | numbers | `labelled_open_change_request_numbers` (bound) | 4 |
| PA6 | pr_automation.py:634-646 | `pr edit N --repo R --remove-label EXHAUSTED` | ignored | `remove_label` (bound) | 4 |
| PA7 | pr_automation.py:651-672 | `label create NAME --color C --description D --force` ×4 | ignored | `create_label(update_existing=True)` | 4 |
| PA8 | pr_automation.py:687-693 | `git fetch https://github.com/{owner}/{repo}.git SHA` (hard-coded host) | fork head | `fork_clone_url` | 4 |
| PA9 | pr_automation.py:712-733 | `pr create --base B --head BR --title T --body B` (cwd root) | URL → number | `create_change_request` | 4 |
| PA10 | pr_automation.py:734-738 | `pr edit REPL --add-label EXTERNAL` (cwd root) | ignored | `add_label` | 4 |
| PA11 | pr_automation.py:740-751 | `pr comment N --body B` (cwd root) | ignored | `comment_on_change_request` (unbound) | 4 |
| PA12 | pr_automation.py:753-755 | `pr close N` (cwd root) | ignored | `close_change_request` (unbound) | 4 |
| RC1 | reconcile.py:237-261 | `api repos/R/pulls/N/update-branch --method PUT` | (ok, detail) | `update_change_request_branch` (bound) | 3 |
| RC2 | reconcile.py:264-287 | `pr list --repo R --state open --limit 100 --json number,headRefName,isCrossRepository` | rows | `open_change_request_branches` (bound) | 3 |
| RC3 | reconcile.py:345-354 | `pr comment N --repo R --body B` | ignored | `comment_on_change_request` (bound) | 3 |
| RC4 | reconcile.py:355-360 | `pr close N --repo R` | ignored | `close_change_request` (bound) | 3 |
| RC5 | reconcile.py:363-386 | `pr comment N --repo R --body B` (notify) | ignored | `comment_on_change_request` (bound) | 3 |
| RC6 | reconcile.py:389-404 | `api repos/R/git/refs/heads/B --method DELETE` | ok | `delete_branch` (bound) | 3 |
| GS1 | github_state.py:37-38 | `gh_json(*args)` facade | — | kept, GitHub-only | 4 |
| GS2 | github_state.py:70-75 | `repository()`: `$GH_REPO` or `repo view --json nameWithOwner` | name | kept, GitHub-only; neutral code uses `repository_name` | 4 |
| GS3 | github_state.py:95-98 | `{pr\|issue} comment N --repo R --body B` | raise on failure | `comment_on_change_request` / `comment_on_issue` (bound) | 4 |
| GS4 | github_state.py:99-110 | `api repos/R/issues/comments/ID --method PATCH --field body=B` | raise | `update_comment` (bound) | 4 |
| GS5 | github_state.py:111-132 | `api graphql --field query=<updateIssueComment> --field id=NODE --field body=B` | raise | `update_comment` | 4 |
| GR1 | github_release.py:22-23 | `_run` runner, cwd None | — | deleted | 3 |
| GR2 | github_release.py:26-30 | `repo view --json nameWithOwner` | R | `repository_name` | 3 |
| GR3 | github_release.py:46-53 | `api repos/R/git/ref/tags/TAG` | `object.sha` | `tag_target` (bound) | 3 |
| GR4 | github_release.py:55-68 | `api repos/R/git/refs --method POST --field ref=refs/tags/TAG --field sha=SHA` | raise | `create_tag` (bound) | 3 |
| GR5 | github_release.py:70-72 | `release view TAG --repo R` | exists? | `release_by_tag` (bound) | 3 |
| GR6 | github_release.py:73-92 | `release create TAG --repo R --target SHA --title TAG [--generate-notes]` | raise | `create_release` (bound) | 3 |
| IA1 | issue_automation.py:265-277 | `issue view N --repo R --json number,title,body,state,author,labels,comments,createdAt,url` | dict | `issue_facts` (bound) | 5 |
| IA2 | issue_automation.py:360-370 | `github_state.upsert_comment(subject="issue")` | state comment | unchanged call; resolves its own forge after Part 4 | 5 |
| IA3 | issue_automation.py:383-398 | `label create NAME --color C --description D --force` | ignored | `create_label(update_existing=True)` | 5 |
| IA4 | issue_automation.py:402-420 | `issue list --repo R --state open --limit N --json <IA1's 9 fields>` | list | `open_issues` (bound) | 5 |
| CV1 | conversation.py:202-217 | `api repos/R/pulls/comments/ID` | review comment | `review_comment` (bound) | 5 |
| CV2 | conversation.py:369-387 | `issue view N --repo R --json number,title,body,state,author,labels,comments,url` | subject | `subject_facts` (bound) | 5 |
| CV3 | conversation.py:399-411 | `github_state.upsert_comment(subject="issue")` | state comment | unchanged call | 5 |
| CV4 | conversation.py:414-431 | `issue comment N --repo R --body B` (cwd root) | ok | `comment_on_issue` (bound) | 5 |
| RS1 | rulesets.py:179-196 | `_api` runner: `gh api ARGS [--input -]`, JSON on stdin, raises `RuntimeError("gh api ARGS: stderr")` | — | deleted | 6 |
| RS2 | rulesets.py:204-205 | `api repos/R/rulesets` | listing | inside `branch_rules` (bound) | 6 |
| RS3 | rulesets.py:206-208 | `api repos/R/rulesets/ID` | document | `branch_rules` | 6 |
| RS4 | rulesets.py:212-213 | `api repos/R/rulesets --method POST --input -` | raise | `create_branch_rules` (bound) | 6 |
| RS5 | rulesets.py:216-224 | `api repos/R/rulesets/ID --method PUT --input -` | raise | `update_branch_rules` (bound) | 6 |
| IN1 | install.py:465-485 | `secret list --json name` | names; `FileNotFoundError` → notice | `secret_names` | 4 |
| FL1 | flatten.py:659 | `github_state.repository()` on the first page | owner/name | `repository_name` + `for_repository` | 6 |
| FL2 | flatten.py:655-676 | `api graphql --raw-field query=<_THREADS_QUERY> --raw-field owner= --raw-field name= --raw-field branch= [--raw-field after=]`, paged | GraphQL pages | `review_thread_page` | 6 |

Against the operator's rough counts: merge_train 16 (the 17 counted a runner's two
`subprocess.run` lines separately), promote 10, pr_automation 12 (adds the two
`github_state` calls and the hard-coded `github.com` fetch URL), reconcile 6,
github_state 5, github_release 6 (adds the runner), issue_automation 4 and conversation 4
(each adds its `upsert_comment`), rulesets 5 (one runner, four routes), install 1,
flatten 2 (adds the repository lookup).

## Verb catalogue (39 verbs: 35 new, 4 reshaped, 1 removed)

| V | verb (all on `ForgeAdapterInterface`) | part | sites |
|---|---|---|---|
| V1 | `repository_name(self) -> tuple[str, str]` | 0a | MT10, MT13, GR2, GS2-users, FL1 |
| V3 | `delete_branch(self, branch: str) -> tuple[bool, str]` | 0a | MT14, RC6 |
| V5 | `change_request_facts(self, number: int) -> tuple[dict[str, Any] \| None, str]` | 0b | MT8 |
| V6 | `change_request_with_thread(self, number: int) -> tuple[dict[str, Any] \| None, str]` | 0b | PA2 |
| V7 | `change_request_text(self, number: int) -> tuple[tuple[str, str] \| None, str]` | 0b | PR7 |
| V8 | `change_request_comment_bodies(self, number: int) -> tuple[tuple[str, ...], str]` | 0b | MT6 |
| V9 | `changed_paths(self, number: int) -> tuple[tuple[tuple[str, ...], int] \| None, str]` | 0b | MT9 |
| V10 | `get_check_results(self, head_sha: str) -> tuple[tuple[CheckResult, ...], str]` (reshaped) | 0b | MT11 |
| V11 | `open_change_request_numbers(self, *, base: str) -> tuple[tuple[int, ...], str]` | 0c | MT12 |
| V12 | `open_change_request_between(self, *, base: str, head: str) -> tuple[int \| None, str]` | 0c | PR2 |
| V13 | `open_change_request_branches(self, *, limit: int) -> tuple[tuple[ChangeRequest, ...], str]` | 0c | RC2 |
| V14 | `labelled_open_change_request_numbers(self, *, label: str) -> tuple[tuple[int, ...], str]` | 0c | PA5 |
| V15 | `wait_for_checks(self, number: int, *, interval_seconds: int, timeout_seconds: int) -> tuple[bool, str]` | 0c | PR4 |
| V2 | `fork_clone_url(self, owner: str, name: str) -> tuple[str, str]` | 0d | PA8 |
| V16 | `create_change_request(self, *, base: str, head: str, title: str, body: str) -> tuple[int \| None, str]` | 0d | PR3, PA9 |
| V17 | `update_change_request(self, number: int, *, title: str, body: str) -> tuple[bool, str]` (reshaped) | 0d | PR8, PR9 |
| V18 | `merge_change_request(self, number: int, *, method: str, commit_body: str \| None = None, bypass_rules: bool = False) -> tuple[bool, str]` (reshaped) | 0d | MT15, MT16, PR5, PR6 |
| V19 | `mark_ready(self, number: int) -> tuple[bool, str]` | 0d | PA3 |
| V20 | `close_change_request(self, number: int) -> tuple[bool, str]` | 0d | RC4, PA12 |
| V21 | `comment_on_change_request(self, number: int, body: str) -> tuple[bool, str]` (replaces `create_comment`) | 0d | MT7, PA11, RC3, RC5, GS3 |
| V22 | `add_label(self, number: int, label: str) -> tuple[bool, str]` | 0d | MT3, MT5, PA10 |
| V23 | `remove_label(self, number: int, label: str) -> tuple[bool, str]` | 0d | PA6 |
| V24 | `create_label(self, name: str, *, colour: str, description: str, update_existing: bool) -> tuple[bool, str]` | 0d | MT4, PA7, IA3 |
| V25 | `update_change_request_branch(self, number: int) -> tuple[bool, str]` | 0d | RC1 |
| V26 | `issue_facts(self, number: int) -> tuple[dict[str, Any] \| None, str]` | 0e | IA1 |
| V27 | `subject_facts(self, number: int) -> tuple[dict[str, Any] \| None, str]` | 0e | CV2 |
| V28 | `open_issues(self, *, limit: int) -> tuple[tuple[dict[str, Any], ...], str]` | 0e | IA4 |
| V29 | `comment_on_issue(self, number: int, body: str) -> tuple[bool, str]` | 0e | CV4, GS3 |
| V30 | `update_comment(self, comment: Mapping[str, Any], body: str) -> tuple[bool, str]` | 0e | GS4, GS5 |
| V31 | `review_comment(self, number: int, comment_id: str) -> tuple[dict[str, Any] \| None, str]` | 0e | CV1 |
| V32 | `review_thread_page(self, head_ref: str, cursor: str) -> tuple[dict[str, Any], str]` | 0e | FL2 |
| V4 | `secret_names(self) -> tuple[frozenset[str], str]` | 0f | IN1 |
| V33 | `tag_target(self, tag: str) -> tuple[str \| None, str]` | 0f | GR3 |
| V34 | `create_tag(self, tag: str, sha: str) -> tuple[bool, str]` | 0f | GR4 |
| V35 | `release_by_tag(self, tag: str) -> tuple[ForgeRelease \| None, str]` | 0f | GR5 |
| V36 | `create_release(self, tag: str, *, target: str, title: str, generate_notes: bool) -> tuple[ForgeRelease \| None, str]` (reshaped) | 0f | GR6 |
| V37 | `branch_rules(self, name: str, branch: str) -> tuple[dict[str, Any] \| None, str]` | 0g | RS2, RS3 |
| V38 | `create_branch_rules(self, document: dict[str, Any]) -> tuple[bool, str]` | 0g | RS4 |
| V39 | `update_branch_rules(self, rules_id: str, document: dict[str, Any]) -> tuple[bool, str]` | 0g | RS5 |

**GitLab answers NotSupported for:** `merge_change_request(method="rebase")`,
`merge_change_request(bypass_rules=True)`, `update_change_request_branch`, `subject_facts`,
`branch_rules`, `create_branch_rules`, `update_branch_rules`. Everything else has a GitLab
REST route, given in its part.

---

# Part 0a — Foundation

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

# Part 0b — Change-request reads

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

# Part 0c — Change-request listings and waiting for checks

## Title
feat(gh): the forge adapter lists open change requests and waits for their checks

## Why
Four modules list open pull requests, each asking a different question with a different
`gh pr list` argv (`merge_train.py:319-330`, `promote.py:85-99`, `reconcile.py:264-275`,
`pr_automation.py:584-595`), and promotion blocks on `gh pr checks --watch`
(`promote.py:130-133`), which has no Forgejo or GitLab counterpart and must be polled there.
ADR 0001 (a verb per question, with its first caller); sub-doctrine 8.b.

## Required behaviour
1. `ChangeRequest` (`forge.py:65-80`) gains `cross_repository: bool = False` as its last
   field; `ChangeRequestInterface` (`interfaces/class_contracts.py`) gains the property.
2. **V11 `open_change_request_numbers(*, base)`** — GitHub: `_read(self._scoped(["pr",
   "list"], ["--base", base, "--state", "open", "--json", "number", "--jq",
   "sort_by(.number)"]))`; `None` → `((), "")`; list → the int `number`s in order; other →
   `((), "`gh pr list` returned JSON that is not a list")`. Forgejo:
   `_pages(f"repos/{R}/pulls?state=open")`, keep `base.ref == base`, sorted numbers. GitLab:
   `_pages(f"projects/{P}/merge_requests?state=opened&target_branch={quote(base, safe='')}")`,
   sorted `iid`s.
3. **V12 `open_change_request_between(*, base, head)`** — GitHub: `_run(self._scoped(["pr",
   "list"], ["--base", base, "--head", head, "--state", "open", "--json", "number", "--jq",
   '.[0].number // ""']))`; rc ≠ 0 → `(None, _failed(run, "gh pr list"))`; stripped stdout
   all digits → `(int, "")`, else `(None, "")`. Forgejo: open pulls with `base.ref == base`,
   `head.ref == head` and same repository → lowest number or `None`. GitLab:
   `merge_requests?state=opened&target_branch=…&source_branch=…` → lowest `iid` or `None`.
4. **V13 `open_change_request_branches(*, limit)`** — GitHub: `_read(self._scoped(["pr",
   "list"], ["--state", "open", "--limit", str(limit), "--json",
   "number,headRefName,isCrossRepository"]))` → `ChangeRequest(number=int(item["number"]),
   head_ref=str(item.get("headRefName") or ""), head_sha="", base_ref="",
   cross_repository=bool(item.get("isCrossRepository")))` for every dict item with an int
   `number`. Forgejo: `_pages(…pulls?state=open, most=limit)` →
   `ForgejoFacts().branch_request(pull)` (new: number, head.ref, head.sha, base.ref, title,
   body, `"OPEN"`, cross). GitLab: `_pages(…merge_requests?state=opened, most=limit)` →
   `GitLabFacts().branch_request(mr)`.
5. **V14 `labelled_open_change_request_numbers(*, label)`** — GitHub: `_read(self._scoped(
   ["pr", "list"], ["--state", "open", "--label", label, "--json", "number"]))`. Forgejo:
   open pulls whose `labels[].name` contains `label`. GitLab:
   `merge_requests?state=opened&labels={quote(label, safe='')}`.
6. **V15 `wait_for_checks(number, *, interval_seconds, timeout_seconds)`** — GitHub:
   `_run(self._scoped(["pr", "checks", str(number)], ["--watch", "--interval",
   str(interval_seconds)]))` — `timeout_seconds` is not passed (gh has no timeout, and today
   none is set); rc 0 → `(True, "")`, else `(False, _failed(run, "gh pr checks",
   with_stdout=True))`. Forgejo/GitLab gain `sleep: Callable[[float], None] =
   field(default=time.sleep, repr=False, compare=False)`; poll
   `rounds = max(1, timeout_seconds // interval_seconds)` times, sleeping `interval_seconds`
   between rounds (not after the last):
   - Forgejo: GET `repos/{R}/pulls/{n}` → `head.sha`; GET `repos/{R}/commits/{sha}/status`;
     `state == "success"` → `(True, "")`; `failure`/`error` →
     `(False, f"checks on {sha[:12]} ended {state}")`; `total_count == 0` →
     `(False, "no checks are reported on the change request's head")`; else wait.
   - GitLab: GET `projects/{P}/merge_requests/{n}` → `head_pipeline.status`: `success` →
     True; `failed`/`canceled`/`skipped` → False with the status; no pipeline →
     `(False, "no pipeline ran on the merge request's head")`; else wait.
   - Exhausted → `(False, f"checks did not settle within {timeout_seconds} seconds")`.

## Where to change
`vibey_gh/forge.py`, `vibey_gh/interfaces/class_contracts.py`,
`vibey_gh/interfaces/forge_adapter_interface.py` (V11-V15), `vibey_gh/forge_github.py`,
`vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, `vibey_gh/forge_forgejo_facts.py`,
`vibey_gh/forge_gitlab_facts.py` (+ their interfaces for `branch_request`).

## Acceptance criteria
- [ ] Each GitHub verb's argv is pinned by a `fake_gh` test, unbound and bound.
- [ ] `ForgejoForge(root=…, transport=…)` compares equal regardless of `sleep`.
- [ ] Polling tests take no wall time (inject `sleep=calls.append`).
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
`test/test_forge_change_request_lists.py`:
- `test_github_numbers_listing_is_the_merge_trains_argv` (and `null` → empty).
- `test_github_between_reads_the_jq_answer` (`"7\n"` → 7, `"\n"` → None, rc 1 → problem).
- `test_github_branches_listing_is_reconciles_argv_when_bound` (`pr list --repo o/r
  --state open --limit 100 --json number,headRefName,isCrossRepository`).
- `test_github_labelled_listing_is_pr_automations_argv_when_bound`.
- `test_github_waits_with_pr_checks_watch`.
- `test_forgejo_listings_filter_one_paged_walk` and `test_gitlab_listings_use_query_filters`.
- `test_forgejo_wait_polls_the_combined_status_until_it_settles` (pending → success; failure;
  no statuses; timeout, asserting the sleeps).
- `test_gitlab_wait_reads_the_head_pipeline`.
- `test_a_change_request_knows_whether_it_comes_from_a_fork`.

## Checks the lane must run (all must pass)
Same block as Part 0a, focused on `test/test_forge_change_request_lists.py test/test_platform.py`.

## Out of scope
Consumers (Wave 2); writes (0d). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md,
AGENTS.md, GEMINI.md or skill trees -- the docs wave owns those. Do not push, open PRs, or
change git remotes. Commit locally with a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# Part 0d — Change-request writes

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

# Part 0e — Issues, comments and review threads

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

# Part 0f — Secrets, tags and releases

## Title
feat(gh): the forge adapter lists repository secrets and cuts tags and releases

## Why
Release publication creates an immutable tag and a release through five `gh` calls
(`github_release.py:22-92`) and `install` inventories secrets with `gh secret list`
(`install.py:465-485`). The existing `create_release` (`forge_github.py:255-264`) cannot
serve: it sends through `survey` (JSON-only) and has no `--target`/`--generate-notes`.
ADR 0001; sub-doctrine 8.b.

## Required behaviour
1. **V4 `secret_names()`** — GitHub `_read(self._scoped(["secret", "list"], ["--json",
   "name"]))` → `frozenset` of the `name`s; non-list → problem. Forgejo
   `_pages(f"repos/{R}/actions/secrets")` → `name`s (a 404 on an older Forgejo comes back as
   the transport's problem; do not special-case it). GitLab `_pages(f"projects/{P}/variables")`
   → `key`s.
2. **V33 `tag_target(tag)`** — "(sha, "") exists; (None, "") the forge said it does not;
   (None, problem) could not ask." GitHub: `R` from V1, `_run(["api",
   f"repos/{R}/git/ref/tags/{tag}"])`; rc ≠ 0 → `(None, "")` when stderr contains
   `(HTTP 404)`, else `(None, _failed(run, "gh api"))`; stdout not JSON →
   `(None, "`gh api` returned a tag reference that is not JSON")`; else `object.sha`.
   Forgejo GET `repos/{R}/git/refs/tags/{tag}` (a list, or one object) → the entry whose
   `ref == f"refs/tags/{tag}"` → `object.sha`; `_absent` → `(None, "")`. GitLab GET
   `projects/{P}/repository/tags/{quote(tag, safe='')}` → `commit.id`; 404 → `(None, "")`.
3. **V34 `create_tag(tag, sha)`** — GitHub `R` from V1, `_run(["api", f"repos/{R}/git/refs",
   "--method", "POST", "--field", f"ref=refs/tags/{tag}", "--field", f"sha={sha}"])`, fail →
   `(run.stderr or "").strip()` or the exited sentence (today's message suffix,
   `github_release.py:66-67`). Forgejo POST `repos/{R}/tags` `{"tag_name": tag, "target":
   sha}`. GitLab POST `projects/{P}/repository/tags` `{"tag_name": tag, "ref": sha}`.
4. **V35 `release_by_tag(tag)`** — GitHub `_run(self._scoped(["release", "view", tag], []))`;
   rc 0 → `(ForgeRelease(tag=tag), "")`; `"release not found"` in lower-cased stderr →
   `(None, "")`; else `(None, _failed(run, "gh release view"))`. Forgejo GET
   `repos/{R}/releases/tags/{tag}` → `ForgeRelease(tag_name, name, draft)`, 404 → None.
   GitLab GET `projects/{P}/releases/{quote(tag, safe='')}`, 404 → None.
5. **V36 `create_release(tag, *, target, title, generate_notes)`** (replaces the old
   signature) — GitHub `_run(self._scoped(["release", "create", tag], ["--target", target,
   "--title", title]) + (["--generate-notes"] if generate_notes else []))`; fail →
   `(None, (run.stderr or "").strip() or …)`; ok → `ForgeRelease(tag=tag, name=title)`.
   Forgejo POST `repos/{R}/releases` `{"tag_name": tag, "target_commitish": target, "name":
   title, "body": "", "draft": False, "prerelease": False}`. GitLab POST
   `projects/{P}/releases` `{"tag_name": tag, "ref": target, "name": title}`. Neither has a
   notes generator: `generate_notes` is ignored there, and the method's docstring says so.

## Where to change
`vibey_gh/interfaces/forge_adapter_interface.py` (V4, V33-V35; V36's new signature),
`vibey_gh/forge_github.py`, `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`.

## Acceptance criteria
- [ ] `fake_gh` tests pin every GitHub argv; bound `release view v1 --repo o/r` and
  `release create v1 --repo o/r --target abc --title v1 --generate-notes`.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
`test/test_forge_releases.py`:
- `test_github_secret_names`, `test_github_tag_target_tells_absent_from_unreachable`,
  `test_github_create_tag_argv_and_failure_text`,
  `test_github_release_view_and_create_argv`.
- `test_forgejo_secret_tag_and_release_routes` (incl. a refs list with a longer tag name
  that must not match).
- `test_gitlab_secret_tag_and_release_routes`.
Update the `create_release` assertions in `test/test_forge_adapters.py`.

## Checks the lane must run (all must pass)
Same block as Part 0a, focused on `test/test_forge_releases.py test/test_forge_adapters.py`.

## Out of scope
`github_release.py`, `install.py` (Parts 3 and 4). Do not edit CHANGELOG.md, docs/, ADRs,
CLAUDE.md, AGENTS.md, GEMINI.md or skill trees -- the docs wave owns those. Do not push,
open PRs, or change git remotes. Commit locally with a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# Part 0g — Branch rules

## Title
feat(gh): the forge adapter reads and writes branch rules, refusing what a forge cannot express

## Why
`vibey-gh rulesets` reconciles GitHub rulesets through `gh api` (`rulesets.py:179-224`).
Forgejo expresses branch protection as `branch_protections`, which covers only part of a
ruleset; GitLab spreads it across protected branches and paid-tier approval/push rules.
`rulesets.reconcile_one` refuses to skip silently (`rulesets.py:227-231`), so a rule a forge
cannot express must come back as a problem, never be dropped. ADR 0001; sub-doctrine 8.b.

## Required behaviour
1. **V37 `branch_rules(name, branch)`** — GitHub: `R` from V1; `listing, problem =
   _read(["api", f"repos/{R}/rulesets"])` (`None` → `[]`); the first dict with
   `item.get("name") == name` → `_read(["api", f"repos/{R}/rulesets/{item['id']}"])` →
   `(document or None, problem)`; none → `(None, "")`. `branch` is unused on GitHub.
   Forgejo: GET `repos/{R}/branch_protections/{quote(branch, safe='')}`; `_absent` →
   `(None, "")`; else `ForgejoBranchRules().document(protection, name, branch)`.
2. **V38 `create_branch_rules(document)`** — GitHub: `_run(["api", f"repos/{R}/rulesets",
   "--method", "POST", "--input", "-"], stdin=json.dumps(document))`; fail →
   `(False, f"{exe} api repos/{R}/rulesets --method POST: {(run.stderr or '').strip()}")` —
   the exact text `rulesets._api` raises today (`rulesets.py:194-195`, which omits
   `--input -`). Forgejo: `payload, problem = ForgejoBranchRules().protection(document)`;
   problem → `(False, problem)`; POST `repos/{R}/branch_protections` with `payload |
   {"rule_name": branch}`.
3. **V39 `update_branch_rules(rules_id, document)`** — GitHub: as V38 with PUT and
   `f"repos/{R}/rulesets/{rules_id}"`. Forgejo: PATCH
   `repos/{R}/branch_protections/{quote(rules_id, safe='')}` with the payload (no
   `rule_name`).
4. GitLab: all three → `NotSupported(GITLAB, "branch rules", "GitLab expresses protection as
   protected branches plus paid-tier approval and push rules, which vibey-gh does not map
   rulesets onto")`.
5. New `vibey_gh/forge_forgejo_rules.py`, class `ForgejoBranchRules` (pure) + interface
   `vibey_gh/interfaces/forge_forgejo_rules_interface.py`:
   - `protection(document) -> tuple[dict[str, Any] | None, str]` refuses (problem =
     `NotSupported(FORGEJO, "branch rules", f"no equivalent for {', '.join(items)}").problem`)
     any of: `target != "branch"`; `enforcement != "active"`; non-empty `bypass_actors`;
     `conditions` other than exactly one `refs/heads/<branch>` include and no excludes; a
     rule type outside `deletion, non_fast_forward, required_signatures, pull_request,
     required_status_checks`; a `pull_request` parameter `require_code_owner_review`,
     `require_last_push_approval` or `required_review_thread_resolution` that is true.
     Otherwise the payload: `{"enable_push": False, "require_signed_commits": <has
     required_signatures>, "required_approvals": count, "dismiss_stale_approvals":
     dismiss_stale_reviews_on_push, "enable_status_check": bool(contexts),
     "status_check_contexts": [c["context"] …], "block_on_outdated_branch":
     strict_required_status_checks_policy}`.
   - `document(protection, name, branch) -> dict[str, Any]`: `{"id": branch, "name": name,
     "target": "branch", "enforcement": "active", "bypass_actors": [], "conditions":
     {"ref_name": {"include": [f"refs/heads/{branch}"], "exclude": []}}, "rules": [deletion,
     non_fast_forward, (required_signatures if require_signed_commits), pull_request with
     the five parameters `build_ruleset` writes (the three refused ones False),
     (required_status_checks when enable_status_check and contexts)]}`.
   - Round trip: for a document `rulesets.build_ruleset` makes from an expressible policy,
     `rulesets.diff_ruleset(doc, document(protection(doc)…)).changed` is False.

## Where to change
`vibey_gh/interfaces/forge_adapter_interface.py` (V37-V39), `vibey_gh/forge_github.py`
(`import json`), `vibey_gh/forge_forgejo.py`, `vibey_gh/forge_gitlab.py`, new
`vibey_gh/forge_forgejo_rules.py` + interface.

## Acceptance criteria
- [ ] `fake_gh` tests pin the GitHub argv and stdin (`read_stdin: true` answer) and the
  failure text `"gh api repos/o/r/rulesets --method POST: HTTP 422"`.
- [ ] The default `RulesetsConfig()` integration policy is **refused** on Forgejo, naming
  `required_linear_history`, `required_review_thread_resolution` and `bypass_actors`.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
`test/test_forge_branch_rules.py`:
- `test_github_rules_are_listed_then_fetched_by_id` (and not found → `(None, "")`).
- `test_github_rules_are_posted_and_put_as_json_on_stdin`.
- `test_forgejo_expressible_rules_round_trip_through_branch_protection`.
- `test_forgejo_refuses_every_rule_it_cannot_express` (parametrised, one per refusal).
- `test_forgejo_absent_protection_is_no_rules`.
- `test_gitlab_branch_rules_are_not_supported`.

## Checks the lane must run (all must pass)
Same block as Part 0a, focused on `test/test_forge_branch_rules.py test/test_rulesets.py`.

## Out of scope
`rulesets.py` (Part 6). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
GEMINI.md or skill trees -- the docs wave owns those. Do not push, open PRs, or change git
remotes. Commit locally with a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# Part 1 — The merge train

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

# Part 2 — Promotion

## Title
feat(gh): promotion reaches the forge only through the adapter

## Why
`vibey_gh/promote.py` opens, reads, rewrites, waits on and merges the promotion pull request
through two private `gh` runners (inventory PR1-PR10). On the sovereign default it would
still drive GitHub (ADR 0002, sub-doctrine 8.b). Deltas that apply (C3): D5 only — promotion
already ran `gh` in `cfg.root` and never passed `--repo`.

## Required behaviour
1. Delete `_gh` (78-80), `PromotionPullRequest._gh` (386-389), `PromotionPullRequest._detail`
   (391-396), `_PROJECTS_CLASSIC` (50-53, now in `forge_github`), and `import json` if unused.
   `_git` stays.
2. `open_pull_request(cfg, *, forge=None)`: `number, _ = forge.open_change_request_between(
   base=cfg.release_branch, head=cfg.integration_branch)`; return it (a failed listing reads
   as "none open", exactly as today; the create that follows reports its own failure).
3. `create_pull_request(cfg, body, *, forge=None)`: `number, _ = forge.create_change_request(
   base=cfg.release_branch, head=cfg.integration_branch, title=PromotionPullRequest(cfg,
   forge).title(versioning.read_version(cfg)), body=body)`; return it.
4. `checks_pass(cfg, number, *, forge=None)`: `ok, _ = forge.wait_for_checks(number,
   interval_seconds=30, timeout_seconds=CHECK_TIMEOUT_SECONDS)`.
5. `merge(cfg, number, method=DEFAULT_METHOD, *, forge=None)`: plain
   `merge_change_request(number, method=method)` → `(True, False)`; else with
   `bypass_rules=True` → `(ok, True)`.
6. `promote(cfg=None, *, dry_run=False, method=DEFAULT_METHOD, wait=False, forge=None)`:
   resolve the forge **after** the dry-run return (a dry run still asks the forge nothing,
   `test_identical_trees_promote_nothing`), and pass it to every helper and to
   `PromotionPullRequest(cfg, forge)`.
7. `PromotionPullRequest.__init__(self, cfg, forge=None)`; a private `_adapter()` returns
   `ForgeSelector().resolve(self._forge, self._cfg)`.
   - `read(number)`: `text, problem = self._adapter().change_request_text(number)`;
     `if problem: raise RuntimeError(problem)`; return `text`.
   - `write(number, title, body)`: `ok, problem = self._adapter().update_change_request(
     number, title=title, body=body)`; `if not ok: raise RuntimeError(problem)`.
   - `refresh` is unchanged. Update the class docstring (it names `gh`).
   The texts `read`/`write` raise are unchanged on GitHub (0b V7, 0d V17 reproduce them).

## Where to change
`vibey_gh/promote.py` only. Imports as C6.1. `PromotionPullRequestInterface`
(`interfaces/promotion_pull_request_interface.py`) is unchanged — do not edit it.

## Acceptance criteria
- [ ] `grep -nE '"gh"|_gh\(|_detail' vibey_gh/promote.py` finds nothing.
- [ ] Every existing test in `test/test_promote.py` passes with only `cfg_for`
  (test_promote.py:49-57) changed to add `platform=PlatformConfig(kind="github")` — the
  byte-for-byte proof through its own fake `gh`.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
In `test/test_promote.py`:
- `test_a_promotion_speaks_only_neutral_verbs` — `promote(cfg, wait=True,
  forge=RecordingForge(...))` on a project with a content change; assert the verb sequence
  `open_change_request_between` → `create_change_request` → `wait_for_checks(7,
  interval_seconds=30, timeout_seconds=1800)` → `merge_change_request(7, method='rebase')`.
- `test_a_dry_run_resolves_no_forge` (monkeypatch `ForgeSelector.resolve` to fail).
- `test_read_and_write_raise_the_forges_problem_verbatim` (`PromotionPullRequest(cfg,
  RecordingForge(change_request_text=(None, "boom"), update_change_request=(False,
  "nope")))`).
- `test_a_refused_merge_is_retried_bypassing_rules`.

## Checks the lane must run (all must pass)
The Part 1 block with the focused run
`python -m pytest -q --no-cov test/test_promote.py test/test_gh_cli.py test/test_gh_transport.py`.

## Out of scope
`cli.py` (its promote tests replace `promote.promote` by name), `versioning.py`, adapter
files, `interfaces/`. Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md
or skill trees -- the docs wave owns those. Do not push, open PRs, or change git remotes.
Commit locally with a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# Part 3 — Branch reconciliation and release publication

## Title
feat(gh): branch reconciliation and release publication reach the forge only through the adapter

## Why
`vibey_gh/reconcile.py` lists, comments on, closes, updates and deletes through `gh`
(inventory RC1-RC6) and `vibey_gh/github_release.py` tags and publishes through a private
runner (GR1-GR6). Both bypass `[platform]` (ADR 0002, sub-doctrine 8.b). Deltas (C3): D1
and D2 (github_release), D3, D5.

## Required behaviour
reconcile.py — every function below resolves (C6.1) and **binds** (C6.2), because each site
today calls `github_state.repository()`; a binding problem raises `RuntimeError(problem)`
except in `update_branch`, which returns `(False, problem)`:
1. `update_branch(cfg, number, *, forge=None)` (237-261): `ok, problem =
   bound.update_change_request_branch(number)` → `(True, "the forge merged the base
   forward")` (D3; was "GitHub merged …") or `(False, problem)`.
2. `open_pull_requests(cfg, *, forge=None)` (264-287): `requests, problem =
   bound.open_change_request_branches(limit=100)`; raise on problem; `BranchFacts(number=
   request.number, branch=request.head_ref, fork=request.cross_repository,
   unique_commits=0 if not fork and not _unsafe(branch) else 1)`.
3. `close_pull_request(cfg, decision, *, forge=None)` (345-360): bind once;
   `bound.comment_on_change_request(decision.number, body)` then
   `bound.close_change_request(decision.number)`, results ignored.
4. `notify(cfg, decision, *, forge=None)` (363-386): bind; comment, result ignored.
5. `delete_branch(cfg, branch, *, fork=False, forge=None)` (389-404): the `deletable` guard
   first, as today; bind; `ok, _ = bound.delete_branch(branch)`; return `ok`.
6. `reconcile(cfg, *, dry_run=False, forge=None)`: resolve once and pass `forge=forge` to
   the five functions above (not to the git-only `measure`, `rebase_branch`,
   `merge_forward`). Drop `from vibey_gh import github_state` if unused.

github_release.py:
7. Delete `_run` and `_repository` (22-30) and `import json`/`import subprocess` if unused.
8. `publish(cfg, *, target, version=None, forge=None)`: after the `enabled` check and the tag
   computation, resolve with `cfg`; `name, problem = forge.repository_name()` → on problem
   `raise RuntimeError(f"could not identify the repository: {problem}")` (D3); bind.
   - `tagged, _ = bound.tag_target(tag)` (the problem is ignored: any answer but a SHA
     leads to the create, which reports the real failure — today's behaviour);
   - `tagged is not None`: unchanged comparison / refusal / early `ReleaseResult`;
   - else `ok, problem = bound.create_tag(tag, target)`; not ok →
     `RuntimeError(f"could not create immutable tag {tag}: {problem}")`;
   - `release, _ = bound.release_by_tag(tag)`; `None` → `created, problem =
     bound.create_release(tag, target=target, title=tag,
     generate_notes=cfg.github_release.generate_notes)`; `None` →
     `RuntimeError(f"tag {tag} exists but release creation failed: {problem}")` (D3).

## Where to change
`vibey_gh/reconcile.py`, `vibey_gh/github_release.py`. Imports as C6.1.

## Acceptance criteria
- [ ] `grep -nE '"gh"|github_state' vibey_gh/reconcile.py vibey_gh/github_release.py`
  finds nothing (git's `subprocess` use in reconcile stays).
- [ ] The existing `subprocess.run`-faking tests in `test/test_reconcile.py` that exercise
  these five functions pass with `forge=GitHubForge(root=<their cfg root>)` injected and
  their argv assertions untouched.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
- `test/test_reconcile.py`: `test_reconcile_binds_once_per_call_and_speaks_neutral_verbs`
  (`RecordingForge`), `test_a_forge_that_cannot_name_the_repository_is_an_error`,
  `test_update_branch_says_the_forge_merged_it`. Widen every monkeypatched
  `open_pull_requests`/`close_pull_request`/`update_branch`/`notify`/`delete_branch` lambda
  to accept `**_`; the one test monkeypatching `rc.github_state.gh_json` uses a
  `RecordingForge` instead.
- `test/test_github_release.py`: replace the `_run` fakes with a `RecordingForge`
  (existing tag same SHA → no-op; other SHA → no-op or refusal; create tag + release with
  and without notes; each failure message, with `match="release creation failed"`); delete
  `test_run_uses_noninteractive_subprocess` (its runner is gone); add
  `test_publication_on_github_is_todays_argv` with `fake_gh`, `GH_REPO` unset, and
  `forge=GitHubForge(root=tmp_path)`: `repo view --json nameWithOwner`,
  `api repos/o/r/git/ref/tags/v1.0.0` (rc 1, `(HTTP 404)`),
  `api repos/o/r/git/refs --method POST --field ref=refs/tags/v1.0.0 --field sha=abc`,
  `release view v1.0.0 --repo o/r` (rc 1), `release create v1.0.0 --repo o/r --target abc
  --title v1.0.0 --generate-notes`.

## Checks the lane must run (all must pass)
The Part 1 block with the focused run
`python -m pytest -q --no-cov test/test_reconcile.py test/test_github_release.py test/test_flatten.py test/test_gh_cli.py`.

## Out of scope
`realign.py`, `flatten.py` (imports reconcile; Part 6), `cli.py`, adapter files. Do not
edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees -- the docs
wave owns those. Do not push, open PRs, or change git remotes. Commit locally with a
Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# Part 4 — PR automation, the state comment and install notices

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
The Part 1 block with the focused run
`python -m pytest -q --no-cov test/test_pr_automation.py test/test_gh_transport.py test/test_gh_cli.py test/test_forge_snapshot.py`.

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

# Part 5 — Issue automation and conversation

## Title
feat(gh): issue automation and conversations reach the forge only through the adapter

## Why
`vibey_gh/issue_automation.py` (IA1-IA4) and `vibey_gh/conversation.py` (CV1-CV4) read
issues and threads and write replies through `gh` / `github_state.gh_json`, ignoring
`[platform]` (ADR 0002, sub-doctrine 8.b). Deltas (C3): D1, D5.

## Required behaviour
issue_automation.py (every read binds, C6.2, raising on a binding problem):
1. `fetch_issue(number, *, forge=None)`: bind; `facts, problem = bound.issue_facts(number)`;
   raise on problem.
2. `evaluate_issue(number, cfg, *, forge=None)`: resolve with `cfg`; `fetch_issue(number,
   forge=forge)`.
3. `record(number, payload, *, forge=None)`: `fetch_issue(number, forge=forge)`; the state
   write still calls `upsert_state(...)` → `github_state.upsert_comment(...)` **without**
   `forge` (so this part does not depend on Part 4; after Part 4 it resolves its own).
4. `ensure_labels(*, forge=None)`: `create_label(..., update_existing=True)` per definition.
5. `eligible_issues(cfg, *, limit=100, forge=None)`: bind; `issues, problem =
   bound.open_issues(limit=limit)`; raise on problem; evaluate each as today.
conversation.py:
6. `ConversationThread.__init__(self, subject, forge=None)`; `is_pull_request` returns
   `self._subject["isPullRequest"]` when it is a bool, else today's URL rule (keep the
   docstring; add one sentence about the adapter's flag).
7. `_review_comment(wanted)` (202-217): `forge = ForgeSelector().resolve(self._forge)`; bind
   (raise on problem); `found, problem = bound.review_comment(self.number, wanted)`; problem
   → `RuntimeError(f"comment {wanted} is neither on #{self.number} nor a review comment on
   it: {problem}")`; then today's `pull_request_url` check, unchanged.
8. `fetch_subject(number, *, forge=None)`: bind; `bound.subject_facts(number)`; raise.
9. `record(number, payload, *, forge=None)`: `fetch_subject(number, forge=forge)`; the
   `github_state.upsert_comment(...)` call stays without `forge`.
10. `reply(number, body, cfg, *, forge=None)`: resolve with `cfg`; bind — a binding problem
    returns `False`; `ok, _ = bound.comment_on_issue(number, body)`; return `ok`.
11. Remove `subprocess` imports that become unused.

## Where to change
`vibey_gh/issue_automation.py`, `vibey_gh/conversation.py`. `ConversationThreadInterface`
(`interfaces/conversation_interface.py`) is not changed.

## Acceptance criteria
- [ ] `grep -nE '"gh"|gh_json|github_state.repository' vibey_gh/issue_automation.py
  vibey_gh/conversation.py` finds nothing.
- [ ] `test/test_gh_cli.py::test_conversation_cli_answers_the_review_comment_that_mentioned_it`
  and `…_fails_loudly_on_a_comment_it_cannot_find` (798-850) pass with their scripted `gh`
  answers untouched, after writing `[platform]\nkind = "github"\n` into the `repo`
  fixture's `.vibey-gh.toml` inside those two tests only — the end-to-end byte-for-byte proof.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
- `test/test_issue_automation.py`: `test_issue_reads_bind_and_use_neutral_verbs`,
  `test_eligible_issues_raise_when_the_forge_cannot_list`,
  `test_ensure_labels_through_the_forge` (`RecordingForge`); replace the three
  `ia.github_state.gh_json` monkeypatches and two `subprocess.run` fakes; widen
  `fetch_issue`/`upsert_state` lambdas.
- `test/test_conversation.py`: `test_a_forge_flag_decides_pull_request_before_the_url`,
  `test_review_comment_problem_is_reported_with_the_old_prefix`,
  `test_reply_is_false_when_the_repository_cannot_be_named`; replace the
  `cv.github_state.gh_json` monkeypatch and the two `subprocess.run` fakes; widen lambdas.
- `test/test_gh_cli.py`: the two edits above, nothing else.

## Checks the lane must run (all must pass)
The Part 1 block with the focused run
`python -m pytest -q --no-cov test/test_issue_automation.py test/test_conversation.py test/test_gh_cli.py`.

## Out of scope
`github_state.py` (Part 4), `cli.py`, adapter files, any other test in `test/test_gh_cli.py`.
Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees --
the docs wave owns those. Do not push, open PRs, or change git remotes. Commit locally with
a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# Part 6 — Rulesets and flatten

## Title
feat(gh): rulesets and flatten reach the forge only through the adapter

## Why
`vibey_gh/rulesets.py` reconciles rulesets through a private `gh api` runner (RS1-RS5) and
`vibey_gh/flatten.py` walks unresolved review threads through `github_state.gh_json`
GraphQL (FL1-FL2). Both ignore `[platform]` (ADR 0002, sub-doctrine 8.b). Deltas (C3): D1,
D5; flatten's repository-lookup failure text becomes the adapter's (see 8).

## Required behaviour
rulesets.py:
1. Delete `_api` (179-196) and `import json`/`import subprocess` if unused; drop
   `github_state` if unused.
2. `fetch_ruleset(name, branch, *, forge=None)`: resolve; bind (raise on problem);
   `document, problem = bound.branch_rules(name, branch)`; raise on problem; return it.
3. `create_ruleset(payload, *, forge=None)`: bind; `ok, problem =
   bound.create_branch_rules(payload)`; not ok → `RuntimeError(problem)`.
4. `update_ruleset(ruleset_id, payload, *, forge=None)`: bind;
   `bound.update_branch_rules(str(ruleset_id), payload)`; raise the same way.
5. `reconcile_one(branch, policy, *, dry_run=False, forge=None)` calls
   `fetch_ruleset(name, branch, forge=forge)` and passes `forge` to create/update;
   `reconcile(cfg, *, dry_run=False, forge=None)` resolves with `cfg` once.
6. The pure half (`desired_rules`, `build_ruleset`, `diff_ruleset`, …) is untouched.
flatten.py:
7. `Flattener.__init__(self, forge: ForgeAdapterInterface | None = None)` storing it;
   `_review_threads` becomes an instance method `_review_threads(self, cfg, branch)` and its
   one caller (`flatten.py:288`) passes `cfg`.
8. The walk: `forge = ForgeSelector().resolve(self._forge, cfg)`; before the first page
   `name, problem = forge.repository_name()`; problem → `return None, (), problem`;
   `forge = forge.for_repository(name)`; each page `payload, problem =
   forge.review_thread_page(branch, cursor)`; problem → `return number, threads, problem`
   (on GitHub the texts are today's: missing client and "`gh api graphql` failed: …").
   Everything after — `errors`, `data.repository.pullRequests`, siblings, `pageInfo`, the
   cap `_THREAD_PAGES` and every early return — is unchanged. Delete `_THREADS_QUERY` and
   `_THREADS_PER_PAGE` (now `forge_github.REVIEW_THREADS_QUERY`/`…_PER_PAGE`), the
   `try/except` around the old call, and the `github_state` import. Rewrite the docstring
   paragraph at 645-649 to say the forge adapter is asked.

## Where to change
`vibey_gh/rulesets.py`, `vibey_gh/flatten.py`. `FlattenerInterface`
(`interfaces/flatten_interface.py`) is not changed.

## Acceptance criteria
- [ ] `grep -nE '"gh"|gh_json|github_state' vibey_gh/rulesets.py vibey_gh/flatten.py`
  finds nothing.
- [ ] `test/test_rulesets.py`'s end-to-end `fetch_ruleset` test (469-483) and
  `test_a_request_body_is_actually_sent` (596-) pass with `forge=GitHubForge(root=…)`
  injected and their argv/stdin asserts untouched.
- [ ] Every assertion in `test/test_flatten.py` about `plan.threads_problem` text passes
  unchanged.
- [ ] Whole suite green at 100%; formatters/type checks clean.

## Tests to write first (TDD)
- `test/test_rulesets.py`: `test_rulesets_bind_and_use_branch_rule_verbs`,
  `test_a_forge_that_refuses_the_rules_raises_its_problem` (e.g. a Forgejo NotSupported
  sentence), `test_reconcile_one_passes_the_branch_to_the_fetch`. Replace the `_api`
  monkeypatches (441-452) with `RecordingForge`/`fake_gh`; widen the `fetch_ruleset`,
  `create_ruleset`, `update_ruleset`, `reconcile_one` lambdas (`lambda name, branch, **_:`).
- `test/test_flatten.py`: the autouse `forge` fixture (171-182) stops monkeypatching
  `github_state.gh_json`; instead it patches `flatten.ForgeSelector.resolve` to return the
  fake. The `Forge` double (84-160) gains `repository_name()` → `("the-vibey-project/vibey",
  "")`, `for_repository(name)` → itself, and `review_thread_page(head_ref, cursor)` that
  records `("review_thread_page", head_ref, *([f"after={cursor}"] if cursor else []))` and
  converts its scripted replies the way flatten used to: `FileNotFoundError` →
  `({}, "the GitHub CLI (`gh`) is not installed")`; `OSError`/`RuntimeError`/`ValueError`/
  `LookupError`/`TypeError` → `({}, f"`gh api graphql` failed: {str(exc).strip() or
  type(exc).__name__}")`; a dict → `(reply, "")`. Update the three `forge.calls` assertions
  (1011-1013) to the new tuples. Add `test_a_repository_the_forge_cannot_name_is_reported`.

## Checks the lane must run (all must pass)
The Part 1 block with the focused run
`python -m pytest -q --no-cov test/test_rulesets.py test/test_flatten.py test/test_gh_cli.py`.

## Out of scope
`reconcile.py` (Part 3; flatten only imports it), `cli.py` (its rulesets/flatten tests
replace functions by name), adapter files. Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md,
AGENTS.md, GEMINI.md or skill trees -- the docs wave owns those. Do not push, open PRs, or
change git remotes. Commit locally with a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# Appendix — known gaps, risks and follow-ups (for the operator; not lane work)

1. **Rollout break for undeclared GitHub adopters.** The first Wave-2 merge makes the
   forgejo default real for that command. Any adopter on GitHub whose `.vibey-gh.toml` has
   no `[platform] kind = "github"` (ADR 0002's migration note) will have its merge train,
   promotion, PR automation, etc. talk to `forgejo.local`. This repository already declares
   github (`b60dad4c`). Decide whether Wave 2 carries `!`/`BREAKING CHANGE` (versioning then
   derives a major bump) and whether `vibey-gh doctor` should warn when
   `GITHUB_ACTIONS=true` and the kind is forgejo — a follow-up, not in these specs.
2. **Mapping schemas keep GitHub's key spellings (C5).** A deliberate, transitional
   deviation from ADR 0001's frozen records, so `judge`/`evaluate` and their tests stay
   untouched. Follow-up: convert those decision functions to neutral records.
3. **Forgejo has no faithful equivalent for:** rulesets' `required_linear_history`,
   `merge_queue`, `required_review_thread_resolution`, `require_code_owner_review`,
   `require_last_push_approval` and `bypass_actors` (0g refuses them — so the **default**
   `[rulesets]` policy makes `vibey-gh rulesets` fail on Forgejo until the operator decides
   a mapping; note that `enable_push = false` also blocks promotion's own version-bump push
   when no bypass exists); `--generate-notes` (releases get an empty body);
   `mergeStateStatus: BEHIND` (the train restacks only on conflicts); `reviewDecision`
   (derived from latest reviews); GitHub's GraphQL `reviewThreads.isResolved` (reconstructed
   from review comments' `resolver`, grouped by path and position); `gh pr checks --watch`
   (polled); `gh pr ready` (WIP-prefix title edit); `--admin` (`force_merge`, which only
   overrides what Forgejo lets an admin override); `gh secret list`
   (`/actions/secrets`, availability to verify on the target Forgejo version); a PR's
   `changed_files` count (when absent, protected-path repositories refuse unattended merges).
4. **Gate names on Forgejo Actions** carry an event suffix (`PR evaluate / gate
   (pull_request)`); 0b strips it, but the `GATES` names and the required-check names must
   be verified against a live Forgejo runner before the train can merge anything there.
5. **GitLab NotSupported:** rebase-method merges, rule-bypassing merges, server-side
   update-branch, conversation subjects (issue and MR numbers collide), branch rules.
   Conversation automation therefore does not run on GitLab.
6. **Existing adapter defects fixed along the way:** Forgejo heads/draft/number/comment
   routes and empty-2xx handling (0a — these affect the sovereign default's `tidy` today);
   GitLab statuses route and merge verb (0b, 0d); every GitHub mutation verb that parsed a
   URL as JSON (0d, 0f). `set_protected_ref` / `get_protected_refs` are left as they are:
   unused, and GitHub's `PUT …/protection` with no body would be refused.
7. **Not covered by the 11 modules, so still GitHub-only after this wave:** `vibey-gh
   forge-snapshot` (`cli.py:598-604`, `forge_snapshot.GithubForgeReader`), `vibey-gh
   forecast` (`cli.py:835-837`, `delivery_sources.DeliverySourceReader`), and every `gh`
   invocation inside the rendered workflow templates (`vibey_gh/templates/`). "Every command
   through the adapter" needs a follow-up for these three.
8. **Latent GitHub behaviour kept byte-for-byte:** the exact-head gate read is not paginated
   (`check-runs` returns 30 per page); promotion treats "could not list" as "none open";
   release publication treats any unreadable tag or release as absent.
9. **Docs** (`docs/configuration.md` `[platform]` "only the reads that have moved onto the
   adapter use this table today", `docs/architecture.md`, ADR 0001's consequences) are
   stale once Wave 2 lands — the docs wave owns them.
