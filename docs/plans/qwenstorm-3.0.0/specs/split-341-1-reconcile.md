<!-- split of #341: child 1 of 2; audit: issue-audit/updates/341.md -->

## Title
feat(gh): branch reconciliation reaches the forge only through the adapter

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the
default forge, with GitHub and GitLab declared-only, and `[platform] kind` defaults to `forgejo`
(`vibey_gh/config.py:288`). `vibey_gh/reconcile.py` still lists, comments on, closes, updates and
deletes through `gh` and `github_state`: `update_branch` (`reconcile.py:238-260`),
`open_pull_requests` (263-288), `close_pull_request` (339-360), `notify` (363-386) and
`delete_branch` (389-405) each resolve the repository with `github_state.repository()` and pass
`--repo`/`repos/<name>`, so reconciliation ignores `[platform]` and would drive GitHub on a
repository whose forge is the sovereign default. This is live branch machinery: `realign.py:62`
runs `reconcile.reconcile(cfg)` after every realign, and `vibey-gh reconcile-branches` runs it
directly (`cli.py:1146`). When a paid forge is declared, 8.b has it relay through the sovereign
host rather than replace it (`doctrines.md:179-184`); that relay belongs behind
`ForgeAdapterInterface`, so every forge call here moves onto the interface, and sub-doctrine 9.b
(`doctrines.md:349`: "Substitution happens at the declared seam, never by patching an import")
moves the tests onto the `forge=` seam.

## Required behaviour
Every path is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`).

Each of the five functions in items 1-5 **resolves** (C6.1) and **binds** (C6.2), because each
site calls `github_state.repository()` today. A binding problem raises `RuntimeError(problem)`,
except in `update_branch`, which returns `(False, problem)`.

1. `update_branch(cfg, number, *, forge=None)`:
   ```python
   forge = ForgeSelector().resolve(forge, cfg)
   name, problem = forge.repository_name()
   if problem:
       return False, problem
   bound = forge.for_repository(name)
   ok, problem = bound.update_change_request_branch(number)
   if ok:
       return True, "the forge merged the base forward"
   return False, problem
   ```
   D3: the success detail was `"GitHub merged the base forward"`. The docstring's first line
   becomes `Merge the base forward using the forge's own update-branch operation.`; the rest of
   the docstring stays.
2. `open_pull_requests(cfg, *, forge=None)`: resolve, bind (raise on a binding problem), then
   `requests, problem = bound.open_change_request_branches(limit=100)`; `if problem: raise
   RuntimeError(problem)`. For each request build exactly today's facts:
   `BranchFacts(number=request.number, branch=request.head_ref, fork=request.cross_repository,
   unique_commits=0 if not fork and not _unsafe(branch) else 1)` (with `branch` and `fork` bound
   to locals first, as the loop at 276-288 does today).
3. `close_pull_request(cfg, decision, *, forge=None)`: resolve, bind once (raise on a binding
   problem), then `bound.comment_on_change_request(decision.number, body)` with the same `body`
   text as today (`reconcile.py:341-348`), then `bound.close_change_request(decision.number)`.
   Both results are ignored, as today.
4. `notify(cfg, decision, *, forge=None)`: resolve, bind (raise on a binding problem), then
   `bound.comment_on_change_request(decision.number, text)` with the same text as today
   (`reconcile.py:375-380`, built from `cfg.integration_branch` and `cfg.release_branch`). The
   result is ignored.
5. `delete_branch(cfg, branch, *, fork=False, forge=None)`: the `deletable` guard runs first,
   exactly as today (it raises `ValueError(f"refusing to delete protected or unsafe branch
   {branch!r}")` before anything else); then resolve, bind (raise on a binding problem),
   `ok, _ = bound.delete_branch(branch)`, `return ok`.
6. `reconcile(cfg, *, dry_run=False, forge=None)`: after the `reconcile_branches` early return
   (`reconcile.py:411-412`, unchanged), resolve once with
   `forge = ForgeSelector().resolve(forge, cfg)` and pass `forge=forge` to `open_pull_requests`,
   `close_pull_request`, `delete_branch`, `update_branch` and `notify`. The git-only `measure`,
   `rebase_branch` and `merge_forward` get no `forge`. The comment at `reconcile.py:435-437`
   becomes:
   ```python
   # The forge refuses a branch it calls conflicting (or cannot update one server-side
   # at all), and decides that without this repository's merge drivers. The same merge
   # often succeeds here, so try it rather than leaving the branch stuck.
   ```
7. Delete `from vibey_gh import github_state` (`reconcile.py:36`). `import subprocess` stays: git
   still uses it. Add
   `from vibey_gh.forge_selector import ForgeSelector` and
   `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface` after
   `from vibey_gh.config import GhConfig`.
8. On GitHub the argv is unchanged byte for byte, and `gh` still runs in `cfg.root` (the adapter
   runs every command with `cwd=self.root`, and the selector builds it with `root=cfg.root`).
   The only deliberate differences: **D3** the update-branch success detail (item 1); **D5** a
   missing `gh` or unreadable output now raises `RuntimeError(problem)` (or, in `update_branch`,
   returns `(False, problem)`) instead of letting `FileNotFoundError` or a JSON error escape.
   `realign.py:64-69` already catches `RuntimeError`, so a realign still stands, and
   `cli._reconcile` (`cli.py:1143-1149`) already catches it too.
9. On Forgejo (the default) and GitLab the same code runs. GitLab has no server-side
   update-branch and answers `(False, "gitlab does not support update_change_request_branch:
   GitLab can only rebase a merge request's source branch server-side, which rewrites it")`;
   `update_branch` returns that `(False, problem)`, and `reconcile()` then falls back to
   `merge_forward` for a non-fork branch, exactly as it does for a refusal today.
10. The six functions (`update_branch`, `open_pull_requests`, `close_pull_request`, `notify`,
    `delete_branch`, `reconcile`) stay module-level, and each carries this two-line reason
    directly above its `def` (9.b, `doctrines.md:349`):
    ```python
    # Module-level (ADR-0016): realign.py and cli.py call this module's functions by name;
    # the module converges on a class in its own lane.
    ```
11. Every other comment and docstring that names GitHub (`reconcile.py:64`, `96`, `109-112`,
    `128-130`, `183-188`, `209-211`, `295-296`) stays as it is. The close and notify texts do not
    change.

## Where to change
- `vibey_gh/reconcile.py` only (445 lines: change it with `edit_file`, never `write_file`):
  - imports at 36-37 (behaviour 7);
  - `update_branch` 238-260 (behaviour 1);
  - `open_pull_requests` 263-288 (behaviour 2);
  - `close_pull_request` 339-360 (behaviour 3);
  - `notify` 363-386 (behaviour 4);
  - `delete_branch` 389-405 (behaviour 5);
  - `reconcile` 408-445 (behaviour 6).
  The new signatures, which black wraps as it likes:
  ```python
  def update_branch(cfg: GhConfig, number: int, *, forge: ForgeAdapterInterface | None = None) -> tuple[bool, str]:
  def open_pull_requests(cfg: GhConfig, *, forge: ForgeAdapterInterface | None = None) -> list[BranchFacts]:
  def close_pull_request(cfg: GhConfig, decision: Decision, *, forge: ForgeAdapterInterface | None = None) -> None:
  def notify(cfg: GhConfig, decision: Decision, *, forge: ForgeAdapterInterface | None = None) -> None:
  def delete_branch(cfg: GhConfig, branch: str, *, fork: bool = False, forge: ForgeAdapterInterface | None = None) -> bool:
  def reconcile(cfg: GhConfig, *, dry_run: bool = False, forge: ForgeAdapterInterface | None = None) -> list[dict[str, Any]]:
  ```
  The pattern to copy for obtaining a forge is `vibey_gh/tidy.py:128-129` (the clean-repo
  survey, the one module already on the adapter), with `ForgeSelector().resolve(forge, cfg)` in
  place of its `if forge is None` test.
- Tests: `test/test_reconcile.py` only (649 lines: `edit_file` per test, never `write_file`).
- Once the edits are in, format the touched files once from `src/vibey_tools/gh`:
  `python -m black --line-length 100 vibey_gh/reconcile.py test/test_reconcile.py` then
  `isort vibey_gh/reconcile.py test/test_reconcile.py`; then run the check block. If `ruff format --check` still
  disagrees on a line, restructure that line (C8); never alternate formatters.
- No new class, so no new interface.

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && grep -nE '"gh"|github_state' vibey_gh/reconcile.py` prints
  nothing (git's `subprocess` use stays).
- [ ] `grep -c 'monkeypatch.setattr' test/test_reconcile.py` prints a number no higher than 38
  (63 at `4317cff6`; this lane removes the 25 patches of `subprocess.run` for `gh`, of
  `github_state.gh_json` and of the five forge-reaching functions, and adds none).
- [ ] `grep -nE 'setattr\(rc, "(open_pull_requests|update_branch|close_pull_request|notify|delete_branch)"|github_state' test/test_reconcile.py`
  prints nothing.
- [ ] Every test that reaches one of the five functions passes `forge=` (a call without it would
  resolve Forgejo from the tenant's own `.vibey-gh.toml` and open `https://forgejo.local/`).
- [ ] `test_a_realign_stands_even_when_reconciliation_cannot_reach_github` and
  `test_realign_reconciles_the_branches_its_rewrite_stranded` (`test/test_reconcile.py:606-649`)
  and `test/test_gh_cli.py`'s `reconcile-branches` tests (851 onwards) pass unmodified.
- [ ] `python -m pytest -q` passes at 100% line and branch coverage of `vibey_gh`; black, isort,
  mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
All in `test/test_reconcile.py`. Substitution happens only at declared seams (C7): `forge=`,
the conftest `fake_gh` fixture, and `monkeypatch.setenv`. The patches of the git-only
`unique_commits`, `is_behind`, `rebase_branch` and `merge_forward` that already exist stay as
they are (they are not this lane's; a git seam is a later lane), and no new test adds a patch.

**Imports.** The block at `test/test_reconcile.py:10-18` becomes:
```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from forge_doubles import RecordingForge

from vibey_gh import reconcile as rc
from vibey_gh.config import BranchSyncConfig, GhConfig, RealignConfig
from vibey_gh.forge import ChangeRequest
from vibey_gh.forge_github import GitHubForge
```
If `isort --check-only` places `from forge_doubles import RecordingForge` differently, take
isort's placement and confirm `ruff check` agrees (both read the tenant's `combine_as_imports`
settings); the wave-1 test files that already import `forge_doubles` show the accepted order.

**New tests (append at the end of the file).**
```python
def test_reconcile_binds_once_per_call_and_speaks_neutral_verbs(tmp_path):
    config = cfg(tmp_path)
    forge = RecordingForge(
        open_change_request_branches=((ChangeRequest(1, "vibey-gh/issue/dup", "", ""),), ""),
        update_change_request_branch=(True, ""),
        comment_on_change_request=(True, ""),
        close_change_request=(True, ""),
        delete_branch=(True, ""),
    )
    closing = rc.Decision(1, "vibey-gh/issue/dup", rc.CLOSE, "why")
    telling = rc.Decision(4, "feature/x", rc.LEAVE, "why", notify=True)
    rc.open_pull_requests(config, forge=forge)
    rc.update_branch(config, 3, forge=forge)
    rc.close_pull_request(config, closing, forge=forge)
    rc.notify(config, telling, forge=forge)
    assert rc.delete_branch(config, "vibey-gh/issue/dup", forge=forge) is True
    seen = [call[:2] for call in forge.calls if call[0] != "repository_name"]
    bind = ("for_repository", "o/r")
    expected = [
        bind,
        ("open_change_request_branches", ("limit", 100)),
        bind,
        ("update_change_request_branch", 3),
        bind,
        ("comment_on_change_request", 1),
        ("close_change_request", 1),
        bind,
        ("comment_on_change_request", 4),
        bind,
        ("delete_branch", "vibey-gh/issue/dup"),
    ]
    assert seen == expected


def test_a_forge_that_cannot_name_the_repository_is_an_error(tmp_path):
    config = cfg(tmp_path)
    forge = RecordingForge(repository_name=("", "no repository"))
    assert rc.update_branch(config, 3, forge=forge) == (False, "no repository")
    closing = rc.Decision(1, "vibey-gh/a", rc.CLOSE, "why")
    telling = rc.Decision(4, "feature/x", rc.LEAVE, "why", notify=True)
    for attempt in (
        lambda: rc.open_pull_requests(config, forge=forge),
        lambda: rc.close_pull_request(config, closing, forge=forge),
        lambda: rc.notify(config, telling, forge=forge),
        lambda: rc.delete_branch(config, "vibey-gh/a", forge=forge),
    ):
        with pytest.raises(RuntimeError, match="no repository"):
            attempt()
    assert not any(call[0] == "for_repository" for call in forge.calls)

    refused = RecordingForge(open_change_request_branches=((), "the forge is down"))
    with pytest.raises(RuntimeError, match="the forge is down"):
        rc.open_pull_requests(config, forge=refused)


def test_update_branch_says_the_forge_merged_it(tmp_path):
    merged = RecordingForge(update_change_request_branch=(True, ""))
    wanted = (True, "the forge merged the base forward")
    assert rc.update_branch(cfg(tmp_path), 12, forge=merged) == wanted
    problem = (
        "gitlab does not support update_change_request_branch: GitLab can only rebase a "
        "merge request's source branch server-side, which rewrites it"
    )
    refused = RecordingForge(update_change_request_branch=(False, problem))
    assert rc.update_branch(cfg(tmp_path), 12, forge=refused) == (False, problem)
```

**GitHub argv proofs.** These stop patching `subprocess.run` and `rc.github_state.gh_json` and
drive a real `gh` process (the conftest `fake_gh`), asserting argv and working directory.
- `test_update_branch_uses_githubs_own_endpoint_and_reports_refusals` (312-326) becomes:
  ```python
  def test_update_branch_uses_githubs_own_endpoint_and_reports_refusals(
      tmp_path, monkeypatch, fake_gh
  ):
      monkeypatch.setenv("GH_REPO", "o/r")
      forge = GitHubForge(root=tmp_path)
      update = "api repos/o/r/pulls/12/update-branch --method PUT"
      fake_gh.script({update: {}})
      applied, detail = rc.update_branch(cfg(tmp_path), 12, forge=forge)
      assert applied and "merged the base forward" in detail
      expected = [{"argv": update.split(), "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == expected

      # A refusal must say why: "not applied, no detail" is how two branches sat stuck.
      fake_gh.script({update: {"err": "gh: merge conflict (HTTP 422)\n", "code": 1}})
      applied, detail = rc.update_branch(cfg(tmp_path), 12, forge=forge)
      assert not applied and "422" in detail
  ```
- The four tests of the "gh adapters" block (429-471) become:
  ```python
  def test_open_pull_requests_reads_branch_ownership(monkeypatch, tmp_path, fake_gh):
      monkeypatch.setenv("GH_REPO", "o/r")
      forge = GitHubForge(root=tmp_path)
      fields = "number,headRefName,isCrossRepository"
      listing = f"pr list --repo o/r --state open --limit 100 --json {fields}"
      rows = [
          {"number": 1, "headRefName": "vibey-gh/issue/1", "isCrossRepository": False},
          {"number": 2, "headRefName": "theirs", "isCrossRepository": True},
      ]
      fake_gh.script({listing: {"out": json.dumps(rows)}})
      listed = rc.open_pull_requests(cfg(tmp_path), forge=forge)
      assert [(f.number, f.fork) for f in listed] == [(1, False), (2, True)]
      expected = [{"argv": listing.split(), "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == expected

      fake_gh.script({listing: {"out": "null"}})
      assert rc.open_pull_requests(cfg(tmp_path), forge=forge) == []


  def test_closing_explains_itself_before_it_closes(monkeypatch, tmp_path, fake_gh):
      monkeypatch.setenv("GH_REPO", "o/r")
      # Neither call is scripted. `close_pull_request` ignores both results, as it always
      # has, so the fake's refusal changes nothing, and the fake still records each argv.
      decision = rc.Decision(3, "b", rc.CLOSE, "why")
      rc.close_pull_request(cfg(tmp_path), decision, forge=GitHubForge(root=tmp_path))
      comment, close = fake_gh.invocations()
      assert comment["argv"][:6] == ["pr", "comment", "3", "--repo", "o/r", "--body"]
      body = comment["argv"][6]
      assert "already on" in body and "nothing is lost" in body
      assert close["argv"] == ["pr", "close", "3", "--repo", "o/r"]
      assert comment["cwd"] == close["cwd"] == str(tmp_path.resolve())


  def test_a_contributor_is_told_how_to_recover_their_own_branch(monkeypatch, tmp_path, fake_gh):
      monkeypatch.setenv("GH_REPO", "o/r")
      decision = rc.Decision(4, "feature/x", rc.LEAVE, "why", notify=True)
      rc.notify(cfg(tmp_path), decision, forge=GitHubForge(root=tmp_path))
      (comment,) = fake_gh.invocations()
      assert comment["argv"][:6] == ["pr", "comment", "4", "--repo", "o/r", "--body"]
      body = comment["argv"][6]
      assert "git rebase origin/develop" in body
      assert "left the branch untouched" in body


  def test_delete_branch_reports_whether_github_accepted_it(monkeypatch, tmp_path, fake_gh):
      monkeypatch.setenv("GH_REPO", "o/r")
      forge = GitHubForge(root=tmp_path)
      delete = "api repos/o/r/git/refs/heads/vibey-gh/issue/1 --method DELETE"
      fake_gh.script({delete: {}})
      assert rc.delete_branch(cfg(tmp_path), "vibey-gh/issue/1", forge=forge) is True
      assert fake_gh.calls() == [delete]
      fake_gh.script({})
      assert rc.delete_branch(cfg(tmp_path), "vibey-gh/issue/1", forge=forge) is False
  ```

**Orchestration tests** (477-603) pass `forge=RecordingForge(...)` to `rc.reconcile(...)`
instead of patching `open_pull_requests`, `update_branch`, `close_pull_request`, `notify` and
`delete_branch`. Their assertions on actions and outcomes stay. A verb a test expects never to
be reached is left unscripted: reaching it raises `AttributeError`.
- `test_reconcile_applies_one_action_per_pull_request` (477-532): delete the
  `open_pull_requests` patch (479-489), the `update_branch` patch (499-501) and the
  `close_pull_request`/`delete_branch`/`notify` patches (506-508); keep `counts`, the
  `unique_commits`/`is_behind` patches, `done: list[str] = []` (502) and the `rebase_branch`
  patch (503-505); then, after the `rebase_branch` patch, add
  ```python
  requests = (
      ChangeRequest(1, "vibey-gh/issue/dup", "", ""),
      ChangeRequest(2, "vibey-gh/issue/work", "", ""),
      ChangeRequest(3, "feature/theirs", "", ""),
      ChangeRequest(4, "theirs", "", "", cross_repository=True),
      ChangeRequest(5, "vibey-gh/issue/current", "", ""),
  )
  forge = RecordingForge(
      open_change_request_branches=(requests, ""),
      update_change_request_branch=lambda n: (done.append(f"update #{n}") or True, ""),
      comment_on_change_request=(True, ""),
      close_change_request=lambda n: (done.append(f"close #{n}") or True, ""),
      delete_branch=lambda b: (done.append(f"delete {b}") or True, ""),
  )
  ```
  call `rc.reconcile(config, forge=forge)`, and expect
  `done == ["close #1", "delete vibey-gh/issue/dup", "rebase vibey-gh/issue/work",
  "update #3", "update #4"]` (the old `"close vibey-gh/issue/dup"` entry is now `"close #1"`,
  because the forge closes by number). Every other assertion stays, including
  `outcomes[1]["detail"] == "ok"` (it comes from the patched `rebase_branch`).
- `test_a_closed_duplicate_keeps_its_branch_when_deletion_is_disabled` (535-544): keep the
  `unique_commits` patch; replace the other three patches with
  `forge = RecordingForge(open_change_request_branches=((ChangeRequest(1, "vibey-gh/a", "", ""),), ""), comment_on_change_request=(True, ""), close_change_request=(True, ""))`
  (one keyword per line), `delete_branch` left unscripted; call
  `rc.reconcile(cfg(tmp_path, delete_duplicate_branches=False), forge=forge)[0]`.
- `test_a_contributor_is_notified_when_updating_their_branch_is_disabled` (547-558): keep the
  `unique_commits`/`is_behind` patches; replace the `open_pull_requests` and `notify` patches
  with `open_change_request_branches=((ChangeRequest(3, "feature/theirs", "", ""),), "")` and
  `comment_on_change_request=lambda n, body: (told.append(n) or True, "")`; the last assertion
  becomes `assert told == [3]` (the forge comments on the number).
- `test_a_branch_github_refuses_falls_back_to_a_local_merge` (561-576): keep the
  `unique_commits`/`is_behind`/`merge_forward` patches; replace the `open_pull_requests` and
  `update_branch` patches with `open_change_request_branches=((ChangeRequest(3,
  "feature/theirs", "", ""),), "")` and
  `update_change_request_branch=(False, "merge conflict (HTTP 422)")`.
- `test_a_fork_github_refuses_is_never_merged_locally` (579-589): keep the `merge_forward`
  patch; bind `fork = ChangeRequest(4, "theirs", "", "", cross_repository=True)` and use
  `open_change_request_branches=((fork,), "")`, `update_change_request_branch=(False,
  "refused")`; the outcome still has `applied is False` and `detail == "refused"`.
- `test_a_dry_run_decides_without_touching_anything` (592-603): keep the `unique_commits` and
  `rebase_branch` patches, delete the `close_pull_request` and `delete_branch` patches, and
  script only `open_change_request_branches=((ChangeRequest(1, "vibey-gh/a", "", ""),), "")`;
  call `rc.reconcile(cfg(tmp_path), dry_run=True, forge=forge)`.
- `test_a_realign_stands_even_when_reconciliation_cannot_reach_github` and
  `test_realign_reconciles_the_branches_its_rewrite_stranded` (606-649) are not edited.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_reconcile.py test/test_flatten.py test/test_gh_cli.py
python -c "import vibey_gh.reconcile, vibey_gh.realign, vibey_gh.flatten, vibey_gh.forge_selector"
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
`vibey_gh` (`pyproject.toml:64-71`). `git diff --stat` must list only
`src/vibey_tools/gh/vibey_gh/reconcile.py` and `src/vibey_tools/gh/test/test_reconcile.py`.
Nothing here is platform-specific: run the same block on macOS and on Arch Linux (8.h); CI's
`tools` job reruns it on Linux.

## Out of scope
- `vibey_gh/github_release.py`: child lane `split-341-2-release-publication`.
- `vibey_gh/realign.py`, `vibey_gh/flatten.py` (imports `reconcile`; #344), `vibey_gh/cli.py`,
  `vibey_gh/github_state.py`, every adapter file (`forge_*.py`, `interfaces/`), and
  `test/forge_doubles.py`.
- A git seam for `unique_commits`, `is_behind`, `rebase_branch`, `merge_forward`: the existing
  patches of those stay until a later lane gives git a declared seam.
- `test/conftest.py`: never touched.
- This repository's root `.vibey-gh.toml`: its `[platform]` / `kind = "github"` declaration
  (lines 18-19, merged into integration as `d3b4a388`) is the operator's, written by a human
  per 8.b (`doctrines.md:179-181`). The lane never writes or changes it.
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
problem (10.f), never special-cases a forge, and never skips silently.

**C6 — how this module calls the adapter.**
1. Obtain: each public function gains a keyword-only last parameter
   `forge: ForgeAdapterInterface | None = None` and starts with
   `forge = ForgeSelector().resolve(forge, cfg)`. `resolve(forge, cfg=None)` returns the
   injected `forge` when it is not `None`, else `self.select(cfg)` when `cfg` is given, else
   `self.select(load_config())`.
2. Bind where today's code called `github_state.repository()`, once per public call:
   ```python
   name, problem = forge.repository_name()
   if problem:
       raise RuntimeError(problem)
   bound = forge.for_repository(name)
   ```
   On GitHub, `repository_name()` is `$GH_REPO`, else `gh repo view --json nameWithOwner`,
   exactly `github_state.repository()` (`github_state.py:70-75`).
3. A site that raised keeps raising; a site that returned a value keeps returning it; a site
   that ignored a result keeps ignoring it.

**V — the adapter verbs this lane calls** (all declared on `ForgeAdapterInterface` by wave 1).
- `repository_name(self) -> tuple[str, str]`. GitHub: the bound `self.repository`, else a
  non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner` → its `nameWithOwner`; a `gh`
  failure answers `("", "gh repo view --json nameWithOwner: <stderr>")`, a missing `gh` answers
  ``("", "the GitHub CLI (`gh`) is not installed")``. Forgejo/GitLab: `(self.repository, "")`,
  or `("", "no Forgejo repository is named: set [platform] repository, or give the clone an
  origin remote")` (with `GitLab` in the GitLab text).
- `for_repository(self, repository: str) -> ForgeAdapterInterface`: the same adapter bound to
  that repository (on GitHub, `replace(self, repository=repository)`, `forge_github.py:45-46`).
  A bound GitHub adapter inserts `--repo <name>` right after the subcommand and its positional
  argument (`pr list --repo o/r ...`, `pr comment 3 --repo o/r ...`).
- `open_change_request_branches(self, *, limit: int) -> tuple[tuple[ChangeRequest, ...], str]`.
  GitHub (bound): `pr list --repo <R> --state open --limit <limit> --json
  number,headRefName,isCrossRepository`; every dict item with an int `number` becomes
  `ChangeRequest(number, head_ref=headRefName or "", head_sha="", base_ref="",
  cross_repository=bool(isCrossRepository))`; a `null` answer is `((), "")`. Forgejo: paged
  `repos/{R}/pulls?state=open`; GitLab: paged `projects/{P}/merge_requests?state=opened`.
- `update_change_request_branch(self, number: int) -> tuple[bool, str]`. GitHub:
  `api repos/<R>/pulls/<n>/update-branch --method PUT`; exit 0 → `(True, "")`; otherwise
  `(False, <the last line of the stripped stderr, or "refused" when there is none>)`. Forgejo:
  POST `repos/{R}/pulls/{n}/update?style=merge`. GitLab: the NotSupported answer in behaviour 9.
- `comment_on_change_request(self, number: int, body: str) -> tuple[bool, str]`. GitHub:
  `pr comment <n> [--repo <R>] --body <body>`. Forgejo: POST `repos/{R}/issues/{n}/comments`;
  GitLab: POST `projects/{P}/merge_requests/{n}/notes`.
- `close_change_request(self, number: int) -> tuple[bool, str]`. GitHub:
  `pr close <n> [--repo <R>]`. Forgejo: PATCH the pull with `{"state": "closed"}`; GitLab: PUT
  the merge request with `{"state_event": "close"}`.
- `delete_branch(self, branch: str) -> tuple[bool, str]`. GitHub:
  `api repos/<R>/git/refs/heads/<branch> --method DELETE`. Forgejo: DELETE
  `repos/{R}/branches/{branch}`; GitLab: DELETE `projects/{P}/repository/branches/{branch}`.
- `ChangeRequest` (`vibey_gh/forge.py`): `ChangeRequest(number: int, head_ref: str, head_sha:
  str, base_ref: str, title: str = "", body: str = "", state: str = "", cross_repository: bool
  = False)`, frozen.

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`).
  Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass `forge=`. Never `monkeypatch.setattr` a module or
  class attribute (`subprocess.run`, `github_state.gh_json`, a module function), never
  `mock.patch`, `MagicMock` or `AsyncMock`. `monkeypatch.setenv/delenv/chdir` are fine.
- `RecordingForge` (`test/forge_doubles.py`, import with `from forge_doubles import
  RecordingForge`; pytest puts `test/` on `sys.path`) is the in-memory fake of
  `ForgeAdapterInterface`. It is scripted per verb by keyword: `RecordingForge(delete_branch=(True,
  ""), ...)`. Each scripted verb returns its value, or, when the value is callable, calls it with
  the verb's own arguments and returns what it returns. `repository_name()` defaults to
  `("o/r", "")` and can be scripted like any verb. `for_repository(name)` records the call and
  returns the same double. `.calls` lists `(verb, *args, *sorted(kwargs.items()))`, so
  `open_change_request_branches(limit=100)` is recorded as
  `("open_change_request_branches", ("limit", 100))`. An unscripted verb raises
  `AttributeError`. Whether `repository_name` itself appears in `.calls` is the double's
  business: every assertion in this spec filters it out.
- GitHub argv proofs use the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real
  `gh` executable put first on `PATH`. `fake_gh.script({...})` replaces every answer, keyed by
  the argv joined with single spaces, each answer an object with optional `out`, `err`, `code`
  (`{}` is a silent success); an unscripted argv exits 3 with `no scripted answer` on stderr.
  `fake_gh.invocations()` lists `{"argv": [...], "cwd": <dir>, "stdin": None}` per run,
  `fake_gh.calls()` the joined argv, `fake_gh.forget()` clears both records. Build the adapter
  as `GitHubForge(root=tmp_path)` and compare `cwd` with `str(tmp_path.resolve())`.
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch
  `test/conftest.py`.

**C8 — the formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
and the root `ruff format`. Keep lines at or under 100 columns (95 with nested calls); bind long
comparisons to a local before asserting; no implicit string concatenation that would fit on one
line; one argument per line with a trailing comma in multi-line calls; no backslash
continuations. If the two formatters fight over a line, restructure the line; never alternate.

**Depends on:** forge-0g, split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve, split-334-1-labelled-listings, split-334-2-open-branches, split-334-3-wait-for-checks, split-335-1-create-edit-merge, split-335-2-ready-close-comment, split-335-3-labels
- forge-0g: the end of wave 1 (#338); this lane starts from a branch where every wave-1 lane has merged.
- split-332-1-transport-seams: `NotSupported` (GitLab's update-branch answer) and the Forgejo transport that reads an empty 2xx answer, so a DELETE reads as success.
- split-332-2-adapter-paging: the paged Forgejo/GitLab listing behind `open_change_request_branches`, and `test/forge_doubles.py`.
- split-332-3-repository-name: `repository_name()`, `delete_branch()`, and the GitHub `_scoped`/`_read`/`_run` helpers that keep the argv byte-identical.
- split-332-4-selector-resolve: `ForgeSelector.resolve` and the `RecordingForge` double.
- split-334-1-labelled-listings: nothing called here; it appends to the same adapter files, so it lands first.
- split-334-2-open-branches: `open_change_request_branches(limit=)` and `ChangeRequest.cross_repository`.
- split-334-3-wait-for-checks: nothing called here; it lands first for the same reason.
- split-335-1-create-edit-merge: nothing called here; it lands first for the same reason.
- split-335-2-ready-close-comment: `update_change_request_branch`, `comment_on_change_request`, `close_change_request`.
- split-335-3-labels: nothing called here; it lands first for the same reason.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
