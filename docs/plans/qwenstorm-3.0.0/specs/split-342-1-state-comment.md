<!-- split of #342: child 1 of 4; audit: issue-audit/updates/342.md -->

## Title
feat(gh): the durable state comment reaches the forge only through the adapter

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the
default forge, with GitHub and GitLab declared-only, and `[platform] kind` defaults to `forgejo`
(`vibey_gh/config.py:288`). The durable automation-state comment that PR automation, issue
automation and conversations share is written by `github_state.upsert_comment`
(`vibey_gh/github_state.py:79-134`), which resolves the repository with
`github_state.repository()` (70-75) and runs `gh pr|issue comment`, `gh api
repos/<R>/issues/comments/<id> --method PATCH` or a GraphQL mutation through the module's
`GhTransport`, so it ignores `[platform]`. It is the one write the other automation modules
share (`pr_automation.py:553-563`, `issue_automation.py:360-370`, `conversation.py:403-410`), so
it moves first, on its own; when a paid forge is declared, 8.b has it relay through the
sovereign host rather than replace it (`doctrines.md:179-184`), and that relay belongs behind
`ForgeAdapterInterface`.

## Required behaviour
Every path is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`).

1. `github_state.upsert_comment` gains a keyword-only last parameter and writes through the
   adapter:
   ```python
   # Module-level: part of the facade described above `gh_json`.
   def upsert_comment(
       number: int,
       body: str,
       comments: Sequence[dict[str, Any]],
       pattern: re.Pattern[str],
       *,
       subject: str = "pr",
       error: str = "could not persist automation state",
       forge: ForgeAdapterInterface | None = None,
   ) -> None:
       """Create the state comment, or edit the existing one in place."""
       forge = ForgeSelector().resolve(forge)
       name, problem = forge.repository_name()
       if problem:
           raise RuntimeError(problem)
       bound = forge.for_repository(name)
       existing: dict[str, Any] | None = None
       for comment in reversed(comments):
           if pattern.search(str(comment.get("body", ""))):
               existing = comment
               break
       if existing is not None:
           ok, problem = bound.update_comment(existing, body)
       elif subject == "pr":
           ok, problem = bound.comment_on_change_request(number, body)
       else:
           ok, problem = bound.comment_on_issue(number, body)
       if not ok:
           raise RuntimeError(f"{error}: {problem}")
   ```
   - The existing-comment search (`github_state.py:90-94`) is unchanged.
   - On GitHub a binding problem is today's text, `"gh repo view --json nameWithOwner:
     <stderr>"`.
   - `raise RuntimeError(f"{error}: {problem}")` reproduces both of today's texts,
     `"<error>: <stderr>"` and `"<error>: comment has no ID"` (the adapter's `update_comment`
     answers `(False, "comment has no ID")` for a comment with neither `databaseId` nor `id`).
2. `gh_json`, `repository`, `_transport`, `marker_pattern`, `parse_payload` and `render_body`
   are unchanged: `gh_json` and `repository` remain the GitHub CLI facade for the GitHub-only
   commands (`forge-snapshot` and `forecast`, `cli.py:598` and `cli.py:835`) and for modules not
   yet migrated. The module docstring changes in two places only:
   - line 2 becomes `"""Durable automation state carried in exactly one forge comment.`;
   - its last paragraph (lines 14-16) becomes:
     ```
     The state comment is written through the forge adapter (`ForgeAdapterInterface`), so it
     lands on whichever forge `[platform]` names. `gh_json` and `repository` remain the GitHub
     CLI facade, kept for the commands that are still GitHub-only (`forge-snapshot`,
     `forecast`) and for the modules that have not yet moved onto the adapter.
     ```
3. Imports in `github_state.py` (27-28) become, in this order:
   ```python
   from vibey_gh.forge_selector import ForgeSelector
   from vibey_gh.gh_transport import GhTransport
   from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
   from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
   ```
4. Pass-through only, so the callers' own tests can inject the forge:
   - `pr_automation.upsert_state(number, state, summary, comments, *, forge=None)`
     (`pr_automation.py:553-563`) passes `forge=forge` to `github_state.upsert_comment`.
   - `issue_automation.upsert_state(number, state, summary, comments, *, forge=None)`
     (`issue_automation.py:360-370`) passes `forge=forge` to `github_state.upsert_comment`.
   - Both annotate `forge: ForgeAdapterInterface | None = None` and import
     `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface`
     (in `pr_automation.py` between `from vibey_gh.config import GhConfig, normalise_actor` and
     `from vibey_gh.issue_automation import sanitize`; in `issue_automation.py` directly after
     the `from vibey_gh.config import (...)` block).
   - Nothing else in those two modules changes. Their `record` functions still call
     `upsert_state` without `forge` (child lane `split-342-2-pr-automation` and #343 thread it).
   - `conversation.py` is not touched (#343); its `github_state.upsert_comment` call keeps
     working with no `forge`.
5. On GitHub the argv and working directory are unchanged byte for byte when the caller passes
   `GitHubForge(root=<the process's working directory>)`. With no forge injected, `resolve`
   builds the adapter for `load_config().root`, so `gh` runs there (**D1**: the directory
   `load_config()` found by walking up from the working directory; same repository for `gh`).
   **D5**: a missing `gh` now raises `RuntimeError("the GitHub CLI (`gh`) is not installed")`
   instead of letting `FileNotFoundError` escape.
6. The function stays module-level: its facade comment (`github_state.py:78`) already gives the
   reason.
7. No import cycle: `python -c "import vibey_gh.github_state, vibey_gh.pr_automation,
   vibey_gh.issue_automation, vibey_gh.forge_selector"` succeeds.

## Where to change
- `vibey_gh/github_state.py` (134 lines): docstring line 2 and lines 14-16, imports 27-28,
  `upsert_comment` 79-134 (behaviours 1-3).
- `vibey_gh/pr_automation.py` (761 lines, `edit_file` only): `upsert_state` 553-563 and one
  import line (behaviour 4).
- `vibey_gh/issue_automation.py` (421 lines, `edit_file` only): `upsert_state` 360-370 and one
  import line (behaviour 4).
- Tests: `test/test_gh_transport.py`, `test/test_pr_automation.py` (one test),
  `test/test_issue_automation.py` (one test), `test/test_github_state_forge.py` (new). Every
  existing test file here is longer than 100 lines: change them with `edit_file`, never
  `write_file`.
- Once the edits are in, format the touched files once from `src/vibey_tools/gh`:
  `python -m black --line-length 100 vibey_gh/github_state.py vibey_gh/pr_automation.py vibey_gh/issue_automation.py test/test_gh_transport.py test/test_pr_automation.py test/test_issue_automation.py test/test_github_state_forge.py` then
  `isort vibey_gh/github_state.py vibey_gh/pr_automation.py vibey_gh/issue_automation.py test/test_gh_transport.py test/test_pr_automation.py test/test_issue_automation.py test/test_github_state_forge.py`; then run the check block. If `ruff format --check` still
  disagrees on a line, restructure that line (C8); never alternate formatters.
- Three source files, because the two `upsert_state` pass-throughs are the only way the callers'
  tests reach `upsert_comment` through a declared seam instead of a patched `subprocess.run`.
  No new class, so no new interface.

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && grep -n '_transport.run' vibey_gh/github_state.py` prints
  nothing: `github_state.py`'s only `gh` argv is in `gh_json`/`repository`.
- [ ] `test/test_gh_transport.py`'s `upsert_comment` witness tests (471-531) pass with only the
  forge argument added to the "after" lambdas: byte-for-byte argv, same `cwd`.
- [ ] No test reaches `upsert_comment` without `forge=` or a patched caller; in particular
  `test_github_helpers_and_state_persistence` (`test/test_pr_automation.py:558-595`) and
  `test_state_is_persisted_against_the_issue_subject` (`test/test_issue_automation.py:290-295`),
  which today reach it with a faked `subprocess.run` and would otherwise resolve Forgejo from the
  tenant's own `.vibey-gh.toml` and open `https://forgejo.local/`.
- [ ] `grep -c 'monkeypatch.setattr' test/test_pr_automation.py` is exactly 2 lower than before
  this lane (33 at `4317cff6`), and `grep -c 'monkeypatch.setattr' test/test_issue_automation.py`
  is exactly 1 lower (7 at `4317cff6`).
- [ ] `python -m pytest -q` passes at 100% line and branch coverage of `vibey_gh`; black, isort,
  mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
Substitution happens only at declared seams (C7): `forge=`, the conftest `fake_gh` fixture,
`monkeypatch.setenv/delenv/chdir`.

**`test/test_github_state_forge.py` (new).** Line 1 is the provenance header copied
byte-for-byte from line 1 of `test/test_gh_transport.py`.
```python
"""The durable state comment reaches the forge only through the adapter."""

from __future__ import annotations

import pytest
from forge_doubles import RecordingForge

from vibey_gh import github_state

MARKER = "vibey-gh-state-forge-test"
PATTERN = github_state.marker_pattern(MARKER)
BODY = github_state.render_body(MARKER, {"n": 1}, "State", "summary")
WRITES = {"comment_on_change_request", "comment_on_issue", "update_comment"}


def test_a_new_state_comment_goes_to_the_change_request_or_the_issue():
    on_pr = RecordingForge(comment_on_change_request=(True, ""))
    github_state.upsert_comment(7, BODY, [], PATTERN, forge=on_pr)
    wanted = [("for_repository", "o/r"), ("comment_on_change_request", 7, BODY)]
    assert [call for call in on_pr.calls if call[0] != "repository_name"] == wanted

    on_issue = RecordingForge(comment_on_issue=(True, ""))
    github_state.upsert_comment(7, BODY, [], PATTERN, subject="issue", forge=on_issue)
    wanted = [("for_repository", "o/r"), ("comment_on_issue", 7, BODY)]
    assert [call for call in on_issue.calls if call[0] != "repository_name"] == wanted


def test_an_existing_state_comment_is_updated_in_place():
    stored = {"body": BODY, "databaseId": 9}
    forge = RecordingForge(update_comment=(True, ""))
    comments = [{"body": "ordinary chatter"}, stored]
    github_state.upsert_comment(7, BODY, comments, PATTERN, forge=forge)
    assert ("update_comment", stored, BODY) in forge.calls


def test_a_refused_write_raises_with_the_callers_prefix():
    forge = RecordingForge(update_comment=(False, "comment has no ID"))
    with pytest.raises(RuntimeError) as raised:
        github_state.upsert_comment(7, BODY, [{"body": BODY}], PATTERN, forge=forge)
    assert str(raised.value) == "could not persist automation state: comment has no ID"


def test_a_repository_the_forge_cannot_name_is_an_error():
    forge = RecordingForge(repository_name=("", "no repository"))
    with pytest.raises(RuntimeError, match="no repository"):
        github_state.upsert_comment(7, BODY, [], PATTERN, forge=forge)
    assert not any(call[0] in WRITES for call in forge.calls)
```
If `isort --check-only` places `from forge_doubles import RecordingForge` differently, take
isort's placement and confirm `ruff check` agrees.

**`test/test_gh_transport.py`.** Add `from vibey_gh.forge_github import GitHubForge` between
`from vibey_gh import github_state` (27) and `from vibey_gh.gh_transport import GhTransport` (28).
In the three `upsert_comment` witness tests (471-531) only the "after" side changes: bind
`forge = GitHubForge(root=workdir)` as the test's first statement and pass `forge=forge` to every
`github_state.upsert_comment(...)` "after" lambda. `Before.*`, `CREATE`, `CREATE_ON_ISSUE`,
`REST_EDIT`, `GRAPHQL_EDIT` and every expectation stay. The four "after" lambdas become:
```python
        lambda: github_state.upsert_comment(
            7, BODY, comments, PATTERN, subject=subject, forge=forge
        ),
```
```python
        lambda: github_state.upsert_comment(7, BODY, [], PATTERN, forge=forge),
```
```python
        lambda: github_state.upsert_comment(
            7, BODY, comments, PATTERN, error="could not save", forge=forge
        ),
```
```python
        lambda: github_state.upsert_comment(7, BODY, nameless, PATTERN, forge=forge),
```
(`workdir` is the fixture at `test/test_gh_transport.py:198-204`, which `chdir`s into the
directory, so `GitHubForge(root=workdir)` runs `gh` exactly where `Before` does.)

**`test/test_pr_automation.py`.** Add `from vibey_gh.forge_github import GitHubForge` between
the `from vibey_gh.config import (...)` block (13-18) and
`from vibey_gh.install import WORKFLOWS, installation_notices, render_workflow` (19). Replace
`test_github_helpers_and_state_persistence` (558-595) with this version, which stops patching
`subprocess.run` and drives the real `fake_gh` process instead (the two `pa._gh_json(...)`
assertions stay and now run through `fake_gh` too; child lane `split-342-2-pr-automation`
deletes the alias and them):
```python
def test_github_helpers_and_state_persistence(monkeypatch, tmp_path, fake_gh):
    monkeypatch.delenv("GH_REPO", raising=False)
    forge = GitHubForge(root=tmp_path)
    state = pa.AutomationState("a", "a")
    body = pa.state_body(state, "s")
    stored = pa.state_body(state, "x")
    mutation = (
        "mutation($id:ID!,$body:String!){updateIssueComment(input:{id:$id,body:$body})"
        "{issueComment{id}}}"
    )
    named = {"out": '{"nameWithOwner":"o/r"}'}
    fake_gh.script(
        {
            "repo view": named,
            "repo view --json nameWithOwner": named,
            f"pr comment 1 --repo o/r --body {body}": {},
            f"api repos/o/r/issues/comments/9 --method PATCH --field body={body}": {},
            f"api graphql --field query={mutation} --field id=IC_node --field body={body}": {},
            f"pr comment 2 --repo explicit/repository --body {body}": {},
        }
    )
    assert pa._gh_json("repo", "view") == {"nameWithOwner": "o/r"}
    pa.upsert_state(1, state, "s", [], forge=forge)
    pa.upsert_state(1, state, "s", [{"body": "hello"}], forge=forge)
    pa.upsert_state(1, state, "s", [{"body": stored, "databaseId": 9}], forge=forge)
    node = {"body": stored, "databaseId": None, "id": "IC_node"}
    pa.upsert_state(1, state, "s", [node], forge=forge)
    argvs = [call["argv"] for call in fake_gh.invocations()]
    assert any(argv[:2] == ["pr", "comment"] for argv in argvs)
    assert any("issues/comments/9" in " ".join(argv) for argv in argvs)
    assert any(argv[:2] == ["api", "graphql"] for argv in argvs)
    with pytest.raises(RuntimeError, match="comment has no ID"):
        pa.upsert_state(1, state, "s", [{"body": stored}], forge=forge)

    monkeypatch.setenv("GH_REPO", "explicit/repository")
    fake_gh.forget()
    pa.upsert_state(2, state, "s", [], forge=forge)
    (explicit,) = fake_gh.invocations()
    assert "explicit/repository" in explicit["argv"]
    assert explicit["cwd"] == str(tmp_path.resolve())

    fake_gh.script({"api x": {"err": "boom", "code": 1}})
    with pytest.raises(RuntimeError, match="gh api"):
        pa._gh_json("api", "x")
    with pytest.raises(RuntimeError, match="persist"):
        pa.upsert_state(1, state, "s", [], forge=forge)
```
(The last write fails because `pr comment 1 --repo explicit/repository --body <body>` has no
scripted answer: the fake exits 3 and the adapter answers the refusal.)

**`test/test_issue_automation.py`.** Add `from vibey_gh.forge_github import GitHubForge` between
`from vibey_gh.config import GhConfig, IssueAutomationConfig, load_config` (19) and
`from vibey_gh.install import WORKFLOWS, render_workflow` (20). Replace
`test_state_is_persisted_against_the_issue_subject` (290-295) with:
```python
def test_state_is_persisted_against_the_issue_subject(monkeypatch, tmp_path, fake_gh):
    monkeypatch.setenv("GH_REPO", "o/r")
    state = ia.IssueState(issue=55, fingerprint="abc")
    body = ia.state_body(state, "x")
    fake_gh.script({f"issue comment 55 --repo o/r --body {body}": {}})
    ia.upsert_state(55, state, "x", [], forge=GitHubForge(root=tmp_path))
    first = fake_gh.invocations()[0]
    assert first["argv"][:5] == ["issue", "comment", "55", "--repo", "o/r"]
```

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_github_state_forge.py test/test_gh_transport.py test/test_pr_automation.py test/test_issue_automation.py test/test_conversation.py test/test_gh_cli.py test/test_forge_snapshot.py
python -c "import vibey_gh.github_state, vibey_gh.pr_automation, vibey_gh.issue_automation, vibey_gh.forge_selector"
python -m pytest -q
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check src/vibey_tools/gh
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check src/vibey_tools/gh
git diff --stat
```
`python -m pytest -q` (no `--no-cov`) is the whole suite at 100% line and branch coverage of
`vibey_gh` (`pyproject.toml:64-71`). `git diff --stat` must list only the three source files and
four test files named under "Where to change". Nothing here is platform-specific: run the same
block on macOS and on Arch Linux (8.h); CI's `tools` job reruns it on Linux.

## Out of scope
- Everything else in `pr_automation.py`: child lanes `split-342-2-pr-automation` and
  `split-342-3-fork-mirror`. `install.py`: child lane `split-342-4-install-notices`.
- `issue_automation.py` beyond `upsert_state`, and `conversation.py`: #343.
- `vibey_gh/cli.py`, `vibey_gh/forge_snapshot.py`, `vibey_gh/delivery_sources.py`, every adapter
  file (`forge_*.py`, `interfaces/`), `test/forge_doubles.py`.
- `test/conftest.py`: never touched.
- This repository's root `.vibey-gh.toml`: its `[platform]` / `kind = "github"` declaration
  (lines 18-19, merged into integration as `d3b4a388`) is the operator's, written by a human
  per 8.b (`doctrines.md:179-181`); it is why the live PR and issue automation workflows keep
  writing this comment to GitHub. The lane never writes or changes it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the
  docs wave owns those. Do not push, open PRs, or change git remotes. Commit locally with a
  Conventional Commit message when done.

## Conventions this lane relies on (everything needed is here)
**C1 — the adapter contract.** Every adapter verb answers `(value, problem)`. `problem` is `""`
exactly when the forge answered; otherwise `value` is the empty value for its type (`None`,
`()`, `frozenset()`, `False`, `{}`) and `problem` is one sentence. No verb raises for a failed
call, a missing client, a non-2xx status or unreadable output
(`vibey_gh/interfaces/forge_adapter_interface.py:9-16`). A verb a forge has no equivalent for
answers `(<empty>, NotSupported(kind, verb, reason).problem)`, whose text is
`f"{kind.value} does not support {verb}: {reason}"`; the caller reports it like any other
problem (10.f).

**C5 — comments are mappings.** A comment is `{"id": str, "url": str, "body": str, "author":
{"login": str}, "createdAt": str}`; GitHub comments may also carry `databaseId`; GitLab adds
`noteable_type` and `noteable_iid`. `update_comment` takes the comment dict exactly as found in
`comments`, because each forge needs a different part of it to edit it.

**C6 — how this module calls the adapter.** Obtain with `forge = ForgeSelector().resolve(forge)`:
`resolve(forge, cfg=None)` returns the injected `forge` when it is not `None`, else
`self.select(cfg)` when `cfg` is given, else `self.select(load_config())`. Bind where today's
code called `github_state.repository()`: `name, problem = forge.repository_name()`;
`if problem: raise RuntimeError(problem)`; `bound = forge.for_repository(name)`, once per call.

**V — the adapter verbs this lane calls** (all declared on `ForgeAdapterInterface` by wave 1).
- `repository_name(self) -> tuple[str, str]`. GitHub: the bound `self.repository`, else a
  non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner` → its `nameWithOwner`; a `gh`
  failure answers `("", "gh repo view --json nameWithOwner: <stderr>")`, a missing `gh` answers
  ``("", "the GitHub CLI (`gh`) is not installed")``. Forgejo/GitLab: `(self.repository, "")`,
  or `("", "no Forgejo repository is named: set [platform] repository, or give the clone an
  origin remote")` (with `GitLab` in the GitLab text).
- `for_repository(self, repository: str) -> ForgeAdapterInterface`: the same adapter bound to
  that repository. A bound GitHub adapter inserts `--repo <name>` right after the subcommand's
  positional argument (`pr comment 7 --repo o/r --body B`).
- `comment_on_change_request(self, number: int, body: str) -> tuple[bool, str]`. GitHub:
  `pr comment <n> [--repo <R>] --body <body>`; exit 0 → `(True, "")`, else `(False, <stripped
  stderr>)`. Forgejo: POST `repos/{R}/issues/{n}/comments` `{"body"}`; GitLab: POST
  `projects/{P}/merge_requests/{n}/notes` `{"body"}`.
- `comment_on_issue(self, number: int, body: str) -> tuple[bool, str]`. GitHub:
  `issue comment <n> [--repo <R>] --body <body>`. Forgejo: POST `repos/{R}/issues/{n}/comments`;
  GitLab: POST `projects/{P}/issues/{n}/notes`.
- `update_comment(self, comment: Mapping[str, Any], body: str) -> tuple[bool, str]`. GitHub,
  `github_state.py:99-132` moved into the adapter: when `comment.get("databaseId") is not None`,
  `api repos/<R>/issues/comments/<databaseId> --method PATCH --field body=<body>`; else a falsy
  `id` → `(False, "comment has no ID")` with no call; else `api graphql --field
  query=<mutation> --field id=<id> --field body=<body>` with the mutation
  `mutation($id:ID!,$body:String!){updateIssueComment(input:{id:$id,body:$body}){issueComment{id}}}`;
  a failure → ``(False, <stripped stderr, or "`gh api` exited <code>">)``. These are exactly the
  `REST_EDIT` / `GRAPHQL_EDIT` argv of `test/test_gh_transport.py:450-467`. Forgejo: PATCH
  `repos/{R}/issues/comments/{id}`; GitLab: PUT the note on the issue or merge request its
  `noteable_type`/`noteable_iid` name.

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`).
  Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass `forge=`. Never `monkeypatch.setattr` a module or
  class attribute (`subprocess.run`, `github_state.gh_json`, a module function), never
  `mock.patch`, `MagicMock` or `AsyncMock`. `monkeypatch.setenv/delenv/chdir` are fine.
- `RecordingForge` (`test/forge_doubles.py`, import with `from forge_doubles import
  RecordingForge`; pytest puts `test/` on `sys.path`) is the in-memory fake of
  `ForgeAdapterInterface`. It is scripted per verb by keyword:
  `RecordingForge(update_comment=(True, ""), ...)`. Each scripted verb returns its value, or,
  when the value is callable, calls it with the verb's own arguments and returns what it
  returns. `repository_name()` defaults to `("o/r", "")` and can be scripted like any verb.
  `for_repository(name)` records the call and returns the same double. `.calls` lists
  `(verb, *args, *sorted(kwargs.items()))`. An unscripted verb raises `AttributeError`.
  Whether `repository_name` itself appears in `.calls` is the double's business: every
  assertion in this spec filters it out or looks for a specific entry.
- GitHub argv proofs use the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real
  `gh` executable put first on `PATH`. `fake_gh.script({...})` replaces every answer, keyed by
  the argv joined with single spaces (a multi-line `--body` is joined as it is), each answer an
  object with optional `out`, `err`, `code` (`{}` is a silent success); an unscripted argv exits
  3 with `no scripted answer` on stderr. `fake_gh.invocations()` lists `{"argv": [...], "cwd":
  <dir>, "stdin": None}` per run (use it rather than `calls()` for a multi-line `--body`), and
  `fake_gh.forget()` clears the records but keeps the answers.
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch
  `test/conftest.py`.

**C8 — the formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
and the root `ruff format`. Keep lines at or under 100 columns (95 with nested calls); bind long
comparisons to a local before asserting; no implicit string concatenation that would fit on one
line; one argument per line with a trailing comma in multi-line calls; no backslash
continuations. If the two formatters fight over a line, restructure the line; never alternate.

**Depends on:** forge-0g, split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve, split-335-1-create-edit-merge, split-335-2-ready-close-comment, split-335-3-labels, split-336-1-issue-reads, split-336-2-comment-writes, split-336-3-review-comment, split-336-4-review-threads
- forge-0g: the end of wave 1 (#338); this lane starts from a branch where every wave-1 lane has merged.
- split-332-1-transport-seams: the transports that read an empty 2xx answer (a PATCH that returns nothing is a success).
- split-332-2-adapter-paging: `test/forge_doubles.py`, which carries the doubles.
- split-332-3-repository-name: `repository_name()` and the GitHub `_scoped`/`_run` helpers that keep the argv byte-identical.
- split-332-4-selector-resolve: `ForgeSelector.resolve` and the `RecordingForge` double.
- split-335-1-create-edit-merge: nothing called here; it appends to the same adapter files, so it lands first.
- split-335-2-ready-close-comment: `comment_on_change_request(number, body)`.
- split-335-3-labels: nothing called here; it lands first for the same reason.
- split-336-1-issue-reads: nothing called here; it lands first for the same reason.
- split-336-2-comment-writes: `comment_on_issue(number, body)` and `update_comment(comment, body)` (REST, GraphQL and the `comment has no ID` refusal).
- split-336-3-review-comment: nothing called here; it lands first for the same reason.
- split-336-4-review-threads: nothing called here; it lands first for the same reason.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
