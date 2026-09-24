<!-- split of #344: child 2 of 2; audit: issue-audit/updates/344.md -->
## Title
feat(gh): flatten asks the forge adapter for unresolved review threads

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the default forge, with GitHub and GitLab declared-only; `[platform] kind` defaults to `forgejo` (`vibey_gh/config.py:288`), and every forge call goes through `ForgeAdapterInterface` (`doctrines.md:168-176`). Before a flatten orphans review comments, `Flattener._review_threads` (`vibey_gh/flatten.py:609-752`) walks the branch's unresolved review threads through raw `gh`: `github_state.repository()` on the first page (`flatten.py:659`) and `github_state.gh_json("api", "graphql", "--raw-field", "query=<_THREADS_QUERY>", "--raw-field", "owner=<o>", "--raw-field", "name=<n>", "--raw-field", "branch=<b>"[, "--raw-field", "after=<cursor>"])` per page (`flatten.py:656-684`, query and page size at `flatten.py:131,152-169`). It ignores `[platform]`, so on the sovereign default it asks GitHub about a Forgejo repository. `split-336-4-review-threads` added `review_thread_page(head_ref, cursor)`, which answers the same GraphQL envelope on every forge, so the walk after the call (`flatten.py:685-752`) stays exactly as it is. Its tests (`test/test_flatten.py`, 1994 lines) substitute the forge by patching `github_state.gh_json` (`test/test_flatten.py:181`), which 9.b (`doctrines.md:349`: "Substitution happens at the declared seam, never by patching an import") forbids; this lane gives `Flattener` and `cli._flatten` declared seams instead.

This is child lane 2 of 2 of #344 (part 6 of the forge-adapter wave). Every path below is relative to `src/vibey_tools/gh/` (package `vibey_gh`) unless it starts with `src/`.

## Required behaviour
1. `Flattener` (`vibey_gh/flatten.py:257`) gains, directly after its class docstring:
   ```python
   def __init__(self, forge: ForgeAdapterInterface | None = None) -> None:
       # The declared seam for the review-thread check (9.b): `None` resolves the forge that
       # `[platform]` declares, from the configuration each plan is given.
       self._forge = forge
   ```
   The four test subclasses inherit it; `FlattenerInterface` (`vibey_gh/interfaces/flatten_interface.py`) is not changed.
2. `_review_threads` (`flatten.py:609-752`) stops being a `@staticmethod` and becomes `def _review_threads(self, cfg: GhConfig, branch: str) -> tuple[int | None, tuple[ReviewThread, ...], str]:`. Its one caller (`flatten.py:288`) becomes `number, threads, problem = self._review_threads(cfg, branch)`.
3. The walk's start (`flatten.py:651-684`, from `owner = name = cursor = siblings = ""` through the `except` block's `return`) is replaced by exactly:
   ```python
   forge = ForgeSelector().resolve(self._forge, cfg)
   name, problem = forge.repository_name()
   if problem:
       return None, (), problem
   forge = forge.for_repository(name)
   cursor = siblings = ""
   number: int | None = None
   threads: tuple[ReviewThread, ...] = ()
   seen = 0
   for page in range(_THREAD_PAGES):
       # An empty cursor asks for the first page: `$after` is nullable, and a null cursor is
       # how GraphQL spells "from the beginning", so the adapter sends `after` only for a
       # cursor the previous page named.
       payload, problem = forge.review_thread_page(branch, cursor)
       if problem:
           return number, threads, problem
   ```
   (indented to sit inside the method and the `for` loop as the old lines did). Everything after it — the `errors` check, `data.repository.pullRequests`, the empty-pulls and `page` branches, siblings, `pageInfo`, the cursor checks, `_THREAD_PAGES` and every early return, and the final `unread` sentence (`flatten.py:685-752`) — is unchanged.
4. Delete `_THREADS_PER_PAGE = 100` (`flatten.py:131`) and `_THREADS_QUERY` with the comment block above it (`flatten.py:133-169`); the adapter now owns them as `forge_github.REVIEW_THREADS_PER_PAGE` / `REVIEW_THREADS_QUERY`. Keep `_THREAD_PAGES = 20` (`flatten.py:132`) and rewrite its comment (`flatten.py:127-130`) to say it is how many pages of review threads are read before the walk itself is reported as incomplete, keeping the reason a cap beats `while True`.
5. Rewrite the docstring paragraph at `flatten.py:645-649` to say: the forge is asked through the forge adapter (`ForgeAdapterInterface.review_thread_page`), which is how every other forge call in this package is made; the repository is named ONCE, before the first page, by the adapter's `repository_name` (on GitHub, `GH_REPO`, else `gh`'s own answer for the working directory, so a flatten run from inside the worktree being rewritten asks about that worktree's repository), and every page is asked of the adapter bound to it; a repository the forge cannot name is reported as the problem, like any other unanswered question.
6. Imports: `from vibey_gh import fingerprints, github_state, reconcile` becomes `from vibey_gh import fingerprints, reconcile`; add `from vibey_gh.forge_selector import ForgeSelector` and `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface` (isort places them). `Any` and `subprocess` stay (other code uses them).
7. `cli._flatten` (`vibey_gh/cli.py:421-438`) gains the declared seam `flattener: FlattenerInterface | None = None` as its second parameter (the pattern `_install(args, resolver: FallbackPinResolverInterface | None = None)` already uses at `cli.py:164`) and calls `(flattener or flatten.Flattener()).flatten(...)` with the same arguments as today. Add `from vibey_gh.interfaces.flatten_interface import FlattenerInterface` beside the other interface imports (`cli.py:35-36`). Nothing else in `cli.py` changes; `main` still calls `_flatten(args)`.
8. Deliberate differences on GitHub (C3), and nothing else may differ: **D1** `gh` runs in `cfg.root` instead of the process's working directory (the same repository); a failing `gh api graphql` now reads ``"`gh api graphql` failed: <last stderr line>"`` (the transport's text) instead of ``"`gh api graphql` failed: gh api graphql --raw-field query=<the query> <the other fields>: <stderr>"`` (the whole argv); unparseable output reads ``"`gh api graphql` returned output that is not JSON"``; a repository `gh` cannot name reads the adapter's `repository_name` problem instead of ``"`gh api graphql` failed: <the lookup's error>"``. Every `plan.threads_problem` text the tests assert is unchanged.

## Where to change
Three files, because the flatten walk moves onto the adapter (`flatten.py`), the command must be able to hand a flattener in without patching (`cli.py`), and the tests stop patching (`test_flatten.py`).
- `vibey_gh/flatten.py` (1372 lines): `edit_file` with `old_string`s copied from `read_file` output, or checked `python3 -c` replacements; never `write_file`.
- `vibey_gh/cli.py`: `_flatten` and one import (`edit_file` only).
- `test/test_flatten.py` (1994 lines): the edits below, by `edit_file` or checked replacement; new tests are appended.

Make the `flatten.py` and `cli.py` changes first (Required behaviour 1-7). Then the test edits, in this order:
1. **One checked scripted replacement** turns every construction `Flattener()` (95: 91 `flatten.Flattener()` plus `WrongTreeFlattener()`, `RacingFlattener()`, `BogusTreeFlattener()`, `LeaselessFlattener()`, the subclasses at `test/test_flatten.py:1828-1886`) into `Flattener(_current_forge())`:
   `["python3", "-c", "from pathlib import Path\np = Path('test/test_flatten.py')\ns = p.read_text()\nold = 'Flattener()'\nnew = 'Flattener(_current_forge())'\nassert s.count(old) == 95, s.count(old)\np.write_text(s.replace(old, new))"]`
   Run it once, before any other edit to this file.
2. The `Forge` double (`test/test_flatten.py:84-159`): its class docstring becomes "What the forge adapter would have answered, or how `gh` would have failed." (one line, under 100 columns); `__init__` also sets `self.naming: tuple[str, str] = ("the-vibey-project/vibey", "")` and `self.bound: list[str] = []`; `__call__` is replaced by three methods:
   ```python
   def repository_name(self) -> tuple[str, str]:
       return self.naming

   def for_repository(self, repository: str) -> Forge:
       self.bound.append(repository)
       return self

   def review_thread_page(self, head_ref: str, cursor: str) -> tuple[dict[str, Any], str]:
       """One page, converted the way flatten converted `gh`'s answer before the adapter."""
       after = [f"after={cursor}"] if cursor else []
       self.calls.append(("review_thread_page", head_ref, *after))
       reply = self.replies.pop(0) if self.replies else self.reply
       if isinstance(reply, FileNotFoundError):
           return {}, "the GitHub CLI (`gh`) is not installed"
       if isinstance(reply, (OSError, RuntimeError, ValueError, LookupError, TypeError)):
           said = str(reply).strip() or type(reply).__name__
           return {}, f"`gh api graphql` failed: {said}"
       if isinstance(reply, BaseException):
           raise reply
       return reply, ""
   ```
   `repository_name` and `for_repository` do not append to `self.calls`, so the three assertions at `test/test_flatten.py:1011-1013` (`len(forge.calls) == 2`, `"after=cursor-1" in forge.calls[1]`, no `after=` in `forge.calls[0]`) and those at `:1144` and `:1196` hold unchanged. `page`, `pull_request`, `pages` and `no_pull_request` are unchanged.
3. Directly before the autouse fixture, add (with its reason comment):
   ```python
   # Module-level (vibey ADR-0016): every `Flattener(_current_forge())` in this file reads back
   # the fake the autouse fixture below installed for the running test.
   _FORGES: list[Forge] = []


   def _current_forge() -> Forge:
       """The fake the autouse `forge` fixture installed for the running test."""
       return _FORGES[-1]
   ```
4. The autouse `forge` fixture (`test/test_flatten.py:171-182`) keeps `monkeypatch.setenv("GH_REPO", "the-vibey-project/vibey")`, **drops** `monkeypatch.setattr(github_state, "gh_json", fake)`, and sets `_FORGES[:] = [fake]` before `return fake`. Its docstring says every `Flattener` in this file is built with this fake at the constructor seam, so no test can reach a real forge.
5. Imports: `from vibey_gh import flatten, github_state` becomes `from vibey_gh import cli, flatten`; add `import argparse` to the standard-library block.
6. The flatten CLI tests (`test/test_flatten.py:1945-1991`) that reach the forge call the command through its seam: add, before them, a helper with its reason comment
   ```python
   # Module-level (vibey ADR-0016): the namespace `vibey-gh flatten` parses, so a command test
   # can hand `cli._flatten` its flattener at the declared seam.
   def flatten_args(**given: Any) -> argparse.Namespace:
       parsed: dict[str, Any] = {
           "onto": None,
           "message": None,
           "push": False,
           "dry_run": False,
           "orphan_comments": False,
       }
       return argparse.Namespace(**(parsed | given))
   ```
   (These are the defaults `main`'s `flatten` parser gives, `cli.py:1425-1464`.)
   then in `test_the_cli_dry_runs_then_rewrites` (add the `forge` parameter) replace `cli_main(["flatten", "--dry-run"])` with `cli._flatten(flatten_args(dry_run=True), flattener=flatten.Flattener(forge))` and `cli_main(["flatten"])` with `cli._flatten(flatten_args(), flattener=flatten.Flattener(forge))`; in `test_the_cli_refuses_unresolved_threads_and_orphans_them_only_when_told_to` replace `cli_main(["flatten"])` with `cli._flatten(flatten_args(), flattener=flatten.Flattener(forge))` and `cli_main(["flatten", "--orphan-comments"])` with `cli._flatten(flatten_args(orphan_comments=True), flattener=flatten.Flattener(forge))`. Every assertion, the `.vibey-gh.toml` write and `monkeypatch.chdir(work)` stay (`_flatten` still calls `load_config()`). `test_the_cli_reports_a_refusal_on_stderr_and_exits_non_zero` keeps `cli_main(["flatten"])`: it refuses before any forge call.
7. Append `test_a_repository_the_forge_cannot_name_is_reported` (see below).

## Acceptance criteria
- [ ] `grep -nE '"gh"|gh_json|github_state|_THREADS_QUERY|_THREADS_PER_PAGE' vibey_gh/flatten.py` finds nothing.
- [ ] `grep -c 'monkeypatch.setattr' test/test_flatten.py` prints `0`, and `grep -n 'ForgeSelector' test/test_flatten.py` finds nothing (no test patches the selector).
- [ ] Every existing `plan.threads_problem` assertion in `test/test_flatten.py` passes unchanged, and so do the `forge.calls` assertions at `:1011-1013`, `:1144` and `:1196`.
- [ ] `test_a_repository_the_forge_cannot_name_is_reported` passes.
- [ ] Whole suite green at 100% line and branch coverage of `vibey_gh`; black, isort, mypy, `ruff check` and `ruff format --check` clean; `git diff --stat` lists only `vibey_gh/flatten.py`, `vibey_gh/cli.py` and `test/test_flatten.py`.

## Tests to write first (TDD)
Substitute only at declared seams: `Flattener(forge)` and `cli._flatten(args, flattener=<a Flattener>)`. Never `monkeypatch.setattr` a module or class attribute (not `github_state.gh_json`, not `flatten.ForgeSelector.resolve`), never `mock.patch`, `MagicMock` or `AsyncMock`. `monkeypatch.setenv`/`chdir` are fine.

`test/test_flatten.py`:
- `test_a_repository_the_forge_cannot_name_is_reported(work, forge)`: `topic(work)`; `commit(work, "feat: work", file="x.txt")`; `problem = "no Forgejo repository is named: set [platform] repository, or give the clone an origin remote"`; `forge.naming = ("", problem)`; `plan, notes = flatten.Flattener(forge).flatten(cfg(work), dry_run=True)`; assert `plan.pull_request is None`, `plan.threads == ()`, `plan.threads_problem == problem`, `forge.calls == []` (no page was asked), `forge.bound == []`, and some note starts with `"review threads: NOT CHECKED"`.
- The converted fixture, double and CLI tests above must keep every existing test green: run `python -m pytest -q --no-cov test/test_flatten.py` once test edits 1-5 are all in place (the tests cannot pass between them), then after each later step.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_flatten.py test/test_gh_cli.py test/test_forge_review_threads.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check src/vibey_tools/gh
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check src/vibey_tools/gh
git diff --stat   # only vibey_gh/flatten.py, vibey_gh/cli.py and test/test_flatten.py
```
Nothing here is platform-specific: the same commands prove the change on macOS (the lane host) and on Linux (CI's `tools` job), per 8.h.

## Out of scope
- `rulesets.py` (`split-344-1-rulesets`), `reconcile.py` (#341; flatten only imports it), every adapter file (`vibey_gh/forge*.py`, `vibey_gh/*transport*.py`, anything under `vibey_gh/interfaces/`), `FlattenerInterface`, and every other function in `cli.py`.
- `test/conftest.py`, `test/forge_doubles.py`, `test/test_gh_cli.py`, `test/test_forge_review_threads.py`.
- This repository's `.vibey-gh.toml`: its `[platform] kind = "github"` declaration is the operator's (already on the integration branch, d3b4a388); never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every adapter verb answers `(value, problem)`. `problem` is `""` exactly when the forge answered; otherwise `value` is the empty value for its type and `problem` is one sentence. No verb raises for a failed call, a missing client, a non-2xx status or unreadable output (`vibey_gh/interfaces/forge_adapter_interface.py:9-16`). A verb a forge has no equivalent for answers `(<empty>, NotSupported(kind, verb, reason).problem)`, text `f"{kind.value} does not support {verb}: {reason}"`; the caller reports it like any other problem (10.f), never special-cases a forge, never skips silently.

**C5 — the review-thread page is flatten's envelope.** `review_thread_page(self, head_ref: str, cursor: str) -> tuple[dict[str, Any], str]` answers `{"data": {"repository": {"pullRequests": {"nodes": [{"number", "reviewThreads": {"pageInfo": {"hasNextPage", "endCursor"}, "nodes": [{"isResolved", "comments": {"nodes": [{"path", "line", "originalLine", "body", "author": {"login"}}]}}]}}]}}}, "errors"?: [...]}` (the shape `flatten.py:691-736` walks), or `({}, problem)`. An empty `cursor` asks for the first page. GitHub sends flatten's query through `gh api graphql --raw-field query=<the query> --raw-field owner=<o> --raw-field name=<n> --raw-field branch=<head_ref>` (adding `--raw-field after=<cursor>` only for a non-empty cursor) and reports ``the GitHub CLI (`gh`) is not installed``, ``"`gh api graphql` failed: <last stderr line>"``, ``"`gh api graphql` returned output that is not JSON"`` or ``"`gh api graphql` returned a JSON list where an object was expected"``. Forgejo and GitLab always answer one page (`hasNextPage: False`, `endCursor: None`) and ignore the cursor. `repository_name() -> tuple[str, str]` names the repository (when none is declared Forgejo answers `("", "no Forgejo repository is named: set [platform] repository, or give the clone an origin remote")`, and GitLab the same sentence with "GitLab") and `for_repository(name)` returns the adapter bound to it.

**C6 — how this module calls the adapter.** Resolve with `ForgeSelector().resolve(forge, cfg)`: it returns the injected forge, else `select(cfg)`, else `select(load_config())`. Bind where today's code called `github_state.repository()`: `name, problem = forge.repository_name()`, then `forge.for_repository(name)`. A site that returned a problem instead of raising returns it (here: `return None, (), problem`).

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`). Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass the forge to `Flattener(...)` and the flattener to `cli._flatten(...)`. Never `monkeypatch.setattr` a module or class attribute, never `mock.patch`, `MagicMock` or `AsyncMock`. `monkeypatch.setenv/delenv/chdir` are fine.
- `test/test_flatten.py` keeps its own `Forge` double (it is the file's recorded conversion of flatten's old `gh` failures); it does not need `RecordingForge`.
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch `test/conftest.py`.

**C8 — the formatter trap.** Checked by both `black --line-length 100` + `isort` and the root `ruff format`. Keep lines ≤ 100 columns (≤ 95 with nested calls); bind long comparisons to a local before asserting; no implicit string concatenation that would fit on one line; one argument per line with a trailing comma in multi-line calls; no backslash continuations. If the two fight, restructure the line; never alternate between them.

**Depends on:** forge-0g, split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve, split-336-1-issue-reads, split-336-2-comment-writes, split-336-3-review-comment, split-336-4-review-threads
- forge-0g: the end of wave 1; the protocol and adapters as they leave it (wave 2 starts after it).
- split-332-1-transport-seams: the transports every resolved adapter rides on.
- split-332-2-adapter-paging: `ForgejoForge`/`GitLabForge` `_pages`, which their `review_thread_page` walks.
- split-332-3-repository-name: `repository_name()` on every adapter, which the walk calls before the first page.
- split-332-4-selector-resolve: `ForgeSelector().resolve(forge, cfg)`.
- split-336-1-issue-reads: the `# --- Issues ---` protocol block the page verb sits in.
- split-336-2-comment-writes: the adapter files as it leaves them.
- split-336-3-review-comment: `ForgejoForge._review_comments`, which the Forgejo page uses.
- split-336-4-review-threads: `review_thread_page` on all three adapters and `forge_github.REVIEW_THREADS_QUERY`/`REVIEW_THREADS_PER_PAGE`, which replace flatten's constants.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
