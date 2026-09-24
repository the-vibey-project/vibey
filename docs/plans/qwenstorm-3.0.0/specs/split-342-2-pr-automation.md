<!-- split of #342: child 2 of 4; audit: issue-audit/updates/342.md -->

## Title
feat(gh): PR automation reads, readies, labels and records through the adapter

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) makes self-hosted Forgejo the
default forge, with GitHub and GitLab declared-only, and `[platform] kind` defaults to `forgejo`
(`vibey_gh/config.py:288`). `vibey_gh/pr_automation.py` still reads and mutates pull requests
with raw `gh`: `fetch_pr` runs `pr view N --json <18 fields>` through the alias
`_gh_json = github_state.gh_json` (`pr_automation.py:469-484`), `ready_draft` runs `gh pr ready`
(513-518), `exhausted_pull_requests` runs `pr list --repo R --state open --label
vibey-gh:repair-exhausted --json number` (582-596), `self_heal` runs `pr edit N --repo R
--remove-label vibey-gh:repair-exhausted` (634-647) and `ensure_labels` runs `label create NAME
--color C --description D --force` four times (651-673), so PR automation ignores `[platform]`.
These are live: `vibey-gh pr-automation` calls every one of them (`cli.py:327-351`). 8.b routes
every forge call through `ForgeAdapterInterface` (`doctrines.md:168-184`), and sub-doctrine 9.b
(`doctrines.md:349`: "Substitution happens at the declared seam, never by patching an import")
moves the tests off the `monkeypatch.setattr` of `pa.fetch_pr`, `pa.upsert_state` and
`pa._gh_json` and off the faked `subprocess.run`, onto the `forge=` seam.

## Required behaviour
Every path is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package `vibey_gh`).
This lane starts after child lane `split-342-1-state-comment`, so `pr_automation.upsert_state`
already takes `*, forge=None` and passes it to `github_state.upsert_comment`, and
`pr_automation.py` already imports `ForgeAdapterInterface`.

1. Delete `_gh_json = github_state.gh_json` (`pr_automation.py:469`). `cast` becomes unused:
   `from typing import Any, cast` (17) becomes `from typing import Any`. Add
   `from vibey_gh.forge_selector import ForgeSelector` between
   `from vibey_gh.config import GhConfig, normalise_actor` and
   `from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface`.
   `import subprocess` and `import re` stay (`mirror_fork` and the workflow parsers use them).
2. `fetch_pr` (472-484):
   ```python
   def fetch_pr(number: int, *, forge: ForgeAdapterInterface | None = None) -> dict[str, Any]:
       forge = ForgeSelector().resolve(forge)
       facts, problem = forge.change_request_with_thread(number)
       if problem or facts is None:
           raise RuntimeError(problem)
       return facts
   ```
3. `evaluate_pr(number, head_sha, cfg, *, forge=None)` (487-489): first
   `forge = ForgeSelector().resolve(forge, cfg)`, then `pr = fetch_pr(number, forge=forge)`; the
   rest is unchanged.
4. `ready_draft(number, head_sha, cfg, *, forge=None)` (492-518): first
   `forge = ForgeSelector().resolve(forge, cfg)`, then `pr = fetch_pr(number, forge=forge)`; the
   checks and the `evaluate` call are unchanged; the `gh pr ready` call and its return-code
   check (513-517) become
   ```python
   ok, problem = forge.mark_ready(number)
   if not ok:
       raise RuntimeError(f"could not mark PR ready: {problem}")
   ```
   Unbound, as today (`gh pr ready N` carries no `--repo`).
5. `record(number, payload, kind, *, forge=None)` (566-579): first
   `forge = ForgeSelector().resolve(forge)`, then `pr = fetch_pr(number, forge=forge)` and
   `upsert_state(number, state, summary, list(pr.get("comments") or []), forge=forge)`; the
   summary logic is unchanged.
6. `exhausted_pull_requests(cfg, *, forge=None)` (582-596) resolves and binds (C6.2):
   ```python
   forge = ForgeSelector().resolve(forge, cfg)
   name, problem = forge.repository_name()
   if problem:
       raise RuntimeError(problem)
   bound = forge.for_repository(name)
   numbers, problem = bound.labelled_open_change_request_numbers(label=EXHAUSTED_LABEL)
   if problem:
       raise RuntimeError(problem)
   return list(numbers)
   ```
   The docstring stays.
7. `self_heal(number, cfg, *, forge=None)` (599-648): first
   `forge = ForgeSelector().resolve(forge, cfg)`, then `pr = fetch_pr(number, forge=forge)`; the
   budget logic is unchanged; the `upsert_state` call (633) gains `forge=forge`; then the
   `gh pr edit --remove-label` call (634-647) becomes a bind at that site
   followed by the label removal, whose result is ignored as today:
   ```python
   name, problem = forge.repository_name()
   if problem:
       raise RuntimeError(problem)
   forge.for_repository(name).remove_label(number, EXHAUSTED_LABEL)
   ```
   The binding stays after the state is persisted, exactly where `github_state.repository()` ran
   today (641).
8. `ensure_labels(*, forge=None)` (651-673): `forge = ForgeSelector().resolve(forge)`; the
   `definitions` dict is unchanged; for each `name, (colour, description)`:
   `forge.create_label(name, colour=colour, description=description, update_existing=True)`,
   results ignored. Unbound, as today (`gh label create` carries no `--repo`).
9. `mirror_fork` (676-761) is not touched: it still calls `fetch_pr(number)` with no forge and
   runs its own `gh` (child lane `split-342-3-fork-mirror`).
10. Every function changed here stays module-level and carries this reason directly above its
    `def` (9.b, `doctrines.md:349`):
    ```python
    # Module-level (ADR-0016): cli.py calls this module's functions by name; the module
    # converges on a class in its own lane.
    ```
11. On GitHub the argv is unchanged byte for byte: `pr view <n> --json
    number,title,state,isDraft,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,author,labels,comments,headRefOid,headRefName,headRepository,headRepositoryOwner,isCrossRepository,baseRefName,body`,
    `pr ready <n>`, `pr list --repo <R> --state open --label vibey-gh:repair-exhausted --json
    number`, `pr edit <n> --repo <R> --remove-label vibey-gh:repair-exhausted`, and `label create
    <name> --color <colour> --description <description> --force` four times. The deliberate
    differences: **D1** these ran in the process's working directory and now run in the
    adapter's root (`cfg.root` where the function has a `cfg`, else the root `load_config()`
    finds; same repository for `gh`); **D5** a missing `gh` or unreadable output now surfaces as
    `RuntimeError(problem)` where a result was used, and is ignored like any other refusal where
    the result was ignored (`self_heal`'s label removal, `ensure_labels`), instead of letting
    `FileNotFoundError` escape.
12. On Forgejo (the default) and GitLab the same code runs; the adapter's threaded facts carry
    exactly the keys `evaluate` reads (C5).

## Where to change
- `vibey_gh/pr_automation.py` (761 lines: `edit_file` only, never `write_file`): imports
  (17-22), 469, `fetch_pr` 472-484, `evaluate_pr` 487-489, `ready_draft` 492-518, `record`
  566-579, `exhausted_pull_requests` 582-596, `self_heal` 599-648, `ensure_labels` 651-673. The
  pattern to copy for obtaining a forge is `vibey_gh/tidy.py:128-129` (the clean-repo survey),
  with `ForgeSelector().resolve(forge, cfg)` in place of its `if forge is None` test.
- Tests: `test/test_pr_automation.py` only (`edit_file` per test).
- Once the edits are in, format the touched files once from `src/vibey_tools/gh`:
  `python -m black --line-length 100 vibey_gh/pr_automation.py test/test_pr_automation.py` then
  `isort vibey_gh/pr_automation.py test/test_pr_automation.py`; then run the check block. If `ruff format --check` still
  disagrees on a line, restructure that line (C8); never alternate formatters.
- No new class, so no new interface.

## Acceptance criteria
- [ ] `cd src/vibey_tools/gh && grep -nE '_gh_json|github_state\.(gh_json|repository)|cast\(' vibey_gh/pr_automation.py`
  prints nothing.
- [ ] `grep -c '"gh"' vibey_gh/pr_automation.py` prints `4`: the four in `mirror_fork`, which
  child lane `split-342-3-fork-mirror` moves.
- [ ] `grep -c 'monkeypatch.setattr' test/test_pr_automation.py` is exactly 23 lower than before
  this lane (the tests at 375-433, 602-656 and 954-987 at `4317cff6` lose all 23 of their
  patches; no new test adds one).
- [ ] `grep -nE 'setattr\(pa, "(fetch_pr|upsert_state|_gh_json)"' test/test_pr_automation.py`
  prints exactly the three `fetch_pr` patches inside `test_mirror_fork_success_and_failures`
  (child lane `split-342-3-fork-mirror` converts that test).
- [ ] `test/test_gh_cli.py`'s pr-automation tests replace functions by name and pass unmodified.
- [ ] `python -m pytest -q` passes at 100% line and branch coverage of `vibey_gh`; black, isort,
  mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
All in `test/test_pr_automation.py`. Substitution happens only at declared seams (C7): `forge=`,
the conftest `fake_gh` fixture, `monkeypatch.setenv/delenv`. Add
`from forge_doubles import RecordingForge` after `import pytest` (10), unless it is already
there; `from vibey_gh.forge_github import GitHubForge` is already imported (child lane
`split-342-1-state-comment` added it). A verb a test expects never to be reached is left
unscripted: reaching it raises `AttributeError`.

**A state comment is a mapping.** Where a fixture pull request carries a state comment, write it
as `comments=[{"body": pa.state_body(state, "x")}]`, not as a bare string: the real
`upsert_state` now runs, and its search reads `comment.get("body")`.

**Converted tests (replace each in place; keep its name and docstring).**
- `test_a_spent_repair_budget_can_be_refilled_a_bounded_number_of_times` (375-411):
  ```python
  def test_a_spent_repair_budget_can_be_refilled_a_bounded_number_of_times(tmp_path):
      """A budget that never refills turns a transient outage into a permanent stop; one
      that refills forever is no budget. So the refill is itself budgeted."""
      from vibey_gh.config import BranchSyncConfig

      config = GhConfig(root=tmp_path, owner="owner", branch_sync=BranchSyncConfig(max_self_heals=2))
      state = pa.AutomationState("abc", "abc", attempts=3)
      exhausted = [{"name": pa.EXHAUSTED_LABEL}]
      current = pr(labels=exhausted, comments=[{"body": pa.state_body(state, "x")}])
      saved: list = []
      forge = RecordingForge(
          change_request_with_thread=(current, ""),
          update_comment=lambda comment, body: (saved.append(body) or True, ""),
          remove_label=(True, ""),
      )

      first = pa.self_heal(12, config, forge=forge)
      assert first["healed"] and first["heal"] == 1
      healed = pa.parse_state([saved[0]])
      assert healed is not None
      assert healed.attempts == 0 and healed.heals == 1
      assert healed.review_sha is None and healed.review_passed is None
      assert [h["kind"] for h in healed.history][-1] == "self-heal"
      assert ("remove_label", 12, pa.EXHAUSTED_LABEL) in forge.calls

      # The refill count rides in the same durable state, so it survives to bound the next.
      spent = pa.AutomationState("abc", "abc", attempts=3, heals=2)
      spent_pr = pr(labels=exhausted, comments=[{"body": pa.state_body(spent, "x")}])
      spent_forge = RecordingForge(change_request_with_thread=(spent_pr, ""))
      refused = pa.self_heal(12, config, forge=spent_forge)
      assert not refused["healed"] and "budget of 2 is spent" in refused["reason"]

      idle = RecordingForge(change_request_with_thread=(pr(), ""))
      expected = {"pr": 12, "healed": False, "reason": "not exhausted"}
      assert pa.self_heal(12, config, forge=idle) == expected
  ```
- `test_self_heal_starts_a_lineage_when_no_state_exists` (414-421):
  ```python
  def test_self_heal_starts_a_lineage_when_no_state_exists(tmp_path):
      written: list = []
      forge = RecordingForge(
          change_request_with_thread=(pr(labels=[{"name": pa.EXHAUSTED_LABEL}]), ""),
          comment_on_change_request=lambda number, body: (written.append(body) or True, ""),
          remove_label=(True, ""),
      )
      assert pa.self_heal(12, GhConfig(root=tmp_path), forge=forge)["healed"]
      started = pa.parse_state([written[0]])
      assert started is not None and started.lineage_sha == "abc"
  ```
- `test_exhausted_pull_requests_are_listed_by_label` (424-433) becomes a GitHub argv proof:
  ```python
  def test_exhausted_pull_requests_are_listed_by_label(monkeypatch, tmp_path, fake_gh):
      monkeypatch.setenv("GH_REPO", "o/r")
      forge = GitHubForge(root=tmp_path)
      listing = f"pr list --repo o/r --state open --label {pa.EXHAUSTED_LABEL} --json number"
      fake_gh.script({listing: {"out": '[{"number": 4}, {"number": 9}]'}})
      assert pa.exhausted_pull_requests(GhConfig(root=tmp_path), forge=forge) == [4, 9]
      expected = [{"argv": listing.split(), "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == expected
      fake_gh.script({listing: {"out": "null"}})
      assert pa.exhausted_pull_requests(GhConfig(root=tmp_path), forge=forge) == []
  ```
- `test_github_helpers_and_state_persistence` (the version child lane
  `split-342-1-state-comment` wrote at 558 onwards): the alias it exercised is gone, so delete
  exactly these five lines and nothing else:
  ```python
              "repo view": named,
  ```
  ```python
      assert pa._gh_json("repo", "view") == {"nameWithOwner": "o/r"}
  ```
  ```python
      fake_gh.script({"api x": {"err": "boom", "code": 1}})
      with pytest.raises(RuntimeError, match="gh api"):
          pa._gh_json("api", "x")
  ```
  The final `with pytest.raises(RuntimeError, match="persist")` block still fails as intended:
  `pr comment 1 --repo explicit/repository --body <body>` has no scripted answer. (`gh_json`
  itself stays covered by `test/test_gh_transport.py`.)
- `test_fetch_evaluate_record_and_labels` (602-613):
  ```python
  def test_fetch_evaluate_record_and_labels(tmp_path):
      written: list = []
      forge = RecordingForge(
          change_request_with_thread=(pr(), ""),
          comment_on_change_request=lambda number, body: (written.append(body) or True, ""),
          create_label=(True, ""),
      )
      assert pa.fetch_pr(12, forge=forge)["number"] == 12
      assert pa.evaluate_pr(12, "abc", cfg(tmp_path), forge=forge).state == "pending"
      payload = {"head_sha": "abc", "pass": True, "summary": "ok"}
      state = pa.record(12, payload, "review", forge=forge)
      assert state.review_passed and written
      pa.ensure_labels(forge=forge)
      labels = [call for call in forge.calls if call[0] == "create_label"]
      assert len(labels) == 4 and all(call[-1] == ("update_existing", True) for call in labels)
  ```
- `test_ready_draft_unstable_states_are_noops` (626-630; the parametrize block at 616-625
  stays): drop the `monkeypatch` parameter; build
  `forge = RecordingForge(change_request_with_thread=(pr(**changes), ""))`; call
  `pa.ready_draft(12, "abc", cfg(tmp_path), forge=forge)`; keep both assertions; add
  `assert not any(call[0] == "mark_ready" for call in forge.calls)`.
- `test_ready_draft_promotes_green_trusted_or_reviewable_head` (634-645; the parametrize line
  stays): drop `monkeypatch`; keep `draft`; build
  `forge = RecordingForge(change_request_with_thread=(draft, ""), mark_ready=(True, ""))`;
  `assert pa.ready_draft(12, "abc", cfg(tmp_path), forge=forge)["promoted"] is True`;
  `assert ("mark_ready", 12) in forge.calls`.
- `test_ready_draft_reports_github_failure` (648-656):
  ```python
  def test_ready_draft_reports_github_failure(tmp_path):
      draft = pr(isDraft=True, isCrossRepository=False, statusCheckRollup=[check()])
      forge = RecordingForge(change_request_with_thread=(draft, ""), mark_ready=(False, "denied"))
      with pytest.raises(RuntimeError, match="could not mark PR ready: denied"):
          pa.ready_draft(12, "abc", cfg(tmp_path), forge=forge)
  ```
- `test_a_self_heal_clears_the_recorded_repairability` (954-966):
  ```python
  def test_a_self_heal_clears_the_recorded_repairability(tmp_path):
      state = pa.AutomationState(
          "abc", "abc", attempts=3, review_sha="abc", review_passed=False, review_repairable=False
      )
      exhausted = [{"name": pa.EXHAUSTED_LABEL}]
      current = pr(labels=exhausted, comments=[{"body": pa.state_body(state, "x")}])
      saved: list = []
      forge = RecordingForge(
          change_request_with_thread=(current, ""),
          update_comment=lambda comment, body: (saved.append(body) or True, ""),
          remove_label=(True, ""),
      )
      assert pa.self_heal(12, GhConfig(root=tmp_path, owner="owner"), forge=forge)["healed"]
      cleared = pa.parse_state([saved[0]])
      assert cleared is not None and cleared.review_repairable is None
  ```
- `test_a_split_review_headlines_both_lanes_summaries` (969-987); the state body ends with the
  summary line (`github_state.render_body` returns
  `f"<!-- {marker}:{encoded} -->\n## {heading}\n\n{summary.strip()}\n"`):
  ```python
  def test_a_split_review_headlines_both_lanes_summaries():
      """The diff half's `summary` is the sovereign lane's words and `wider_summary` the paid
      lane's; the state comment's headline carries both. A review answered whole reads as it
      always did."""
      written: list = []
      forge = RecordingForge(
          change_request_with_thread=(pr(), ""),
          comment_on_change_request=lambda number, body: (written.append(body) or True, ""),
      )
      split = {"head_sha": "abc", "summary": "Diff fine.", "wider_summary": "Docs fine."}
      pa.record(12, split, "review", forge=forge)
      pa.record(12, {"head_sha": "abc", "summary": "Whole review."}, "review", forge=forge)
      pa.record(12, {"head_sha": "abc"}, "review", forge=forge)

      assert [body.splitlines()[-1] for body in written] == [
          "Diff fine. Docs fine.",
          "Whole review.",
          "Recorded review for `abc`.",
      ]
  ```

**New tests (append at the end of the file):**
```python
def test_ready_draft_raises_the_forges_problem(tmp_path):
    missing = "the GitHub CLI (`gh`) is not installed"
    unread = RecordingForge(change_request_with_thread=(None, missing))
    with pytest.raises(RuntimeError) as raised:
        pa.ready_draft(12, "abc", cfg(tmp_path), forge=unread)
    assert str(raised.value) == missing
    assert not any(call[0] == "mark_ready" for call in unread.calls)

    draft = pr(isDraft=True, isCrossRepository=False, statusCheckRollup=[check()])
    refused = RecordingForge(
        change_request_with_thread=(draft, ""),
        mark_ready=(False, "HTTP 403"),
    )
    with pytest.raises(RuntimeError) as raised:
        pa.ready_draft(12, "abc", cfg(tmp_path), forge=refused)
    assert str(raised.value) == "could not mark PR ready: HTTP 403"


def test_self_heal_binds_before_removing_the_label(tmp_path):
    exhausted = pr(labels=[{"name": pa.EXHAUSTED_LABEL}])
    forge = RecordingForge(
        change_request_with_thread=(exhausted, ""),
        comment_on_change_request=(True, ""),
        remove_label=(True, ""),
    )
    assert pa.self_heal(12, GhConfig(root=tmp_path), forge=forge)["healed"]
    tail = [call for call in forge.calls if call[0] in {"for_repository", "remove_label"}]
    assert tail[-2:] == [("for_repository", "o/r"), ("remove_label", 12, pa.EXHAUSTED_LABEL)]

    # The state is persisted first (one binding inside `upsert_state`); the label removal
    # then binds on its own, and a forge that cannot name the repository by then stops it.
    names = iter([("o/r", ""), ("", "no repository")])
    nameless = RecordingForge(
        change_request_with_thread=(exhausted, ""),
        comment_on_change_request=(True, ""),
        repository_name=lambda: next(names),
    )
    with pytest.raises(RuntimeError, match="no repository"):
        pa.self_heal(12, GhConfig(root=tmp_path), forge=nameless)
    assert not any(call[0] == "remove_label" for call in nameless.calls)


def test_exhausted_listing_raises_when_the_forge_cannot_list(tmp_path):
    config = GhConfig(root=tmp_path)
    down = RecordingForge(labelled_open_change_request_numbers=((), "the forge is down"))
    with pytest.raises(RuntimeError, match="the forge is down"):
        pa.exhausted_pull_requests(config, forge=down)
    nameless = RecordingForge(repository_name=("", "no repository"))
    with pytest.raises(RuntimeError, match="no repository"):
        pa.exhausted_pull_requests(config, forge=nameless)
    assert not any(call[0] == "labelled_open_change_request_numbers" for call in nameless.calls)


def test_ensure_labels_updates_existing_definitions():
    forge = RecordingForge(create_label=(True, ""))
    pa.ensure_labels(forge=forge)
    definitions = [
        (pa.EXTERNAL_REPAIR_LABEL, "5319E7", "Repository-owned continuation of a fork PR"),
        (pa.REPAIRING_LABEL, "FBCA04", "Automated scan repair is in progress"),
        (pa.EXHAUSTED_LABEL, "D93F0B", "Automated repair budget is exhausted"),
        (pa.BLOCKED_LABEL, "B60205", "Automation requires repository-operator action"),
    ]
    forced = ("update_existing", True)
    expected = [
        ("create_label", name, ("colour", colour), ("description", text), forced)
        for name, colour, text in definitions
    ]
    assert [call for call in forge.calls if call[0] == "create_label"] == expected
    assert not any(call[0] == "for_repository" for call in forge.calls)


def test_ready_draft_on_github_is_todays_argv(tmp_path, fake_gh):
    fields = (
        "number,title,state,isDraft,mergeable,mergeStateStatus,reviewDecision,"
        "statusCheckRollup,author,labels,comments,headRefOid,headRefName,headRepository,"
        "headRepositoryOwner,isCrossRepository,baseRefName,body"
    )
    draft = pr(isDraft=True, isCrossRepository=False, statusCheckRollup=[check()])
    view = ["pr", "view", "12", "--json", fields]
    fake_gh.script({" ".join(view): {"out": json.dumps(draft)}, "pr ready 12": {}})
    result = pa.ready_draft(12, "abc", cfg(tmp_path), forge=GitHubForge(root=tmp_path))
    assert result["promoted"] is True
    cwd = str(tmp_path.resolve())
    expected = [
        {"argv": view, "cwd": cwd, "stdin": None},
        {"argv": ["pr", "ready", "12"], "cwd": cwd, "stdin": None},
    ]
    assert fake_gh.invocations() == expected
```

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -m pytest -q --no-cov test/test_pr_automation.py test/test_github_state_forge.py test/test_gh_cli.py
python -c "import vibey_gh.pr_automation, vibey_gh.github_state, vibey_gh.cli, vibey_gh.forge_selector"
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
`src/vibey_tools/gh/vibey_gh/pr_automation.py` and `src/vibey_tools/gh/test/test_pr_automation.py`.
Nothing here is platform-specific: run the same block on macOS and on Arch Linux (8.h); CI's
`tools` job reruns it on Linux.

## Out of scope
- `mirror_fork` and `test_mirror_fork_success_and_failures`: child lane
  `split-342-3-fork-mirror`.
- `installation_notices` and its tests (`test/test_pr_automation.py:162-214`): child lane
  `split-342-4-install-notices`.
- `github_state.py` and `upsert_state` (child lane `split-342-1-state-comment`, already merged),
  `issue_automation.py` and `conversation.py` (#343), `vibey_gh/cli.py`,
  `vibey_gh/forge_snapshot.py`, every adapter file (`forge_*.py`, `interfaces/`),
  `test/forge_doubles.py`, `test/test_gh_cli.py`.
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
problem (10.f).

**C5 — comments are mappings.** A comment is `{"id": str, "url": str, "body": str, "author":
{"login": str}, "createdAt": str}`; GitHub comments may also carry `databaseId`; GitLab adds
`noteable_type` and `noteable_iid`. `update_comment` takes the comment dict exactly as found in
`comments`. The threaded facts `change_request_with_thread` answers carry exactly the keys
`evaluate` reads: `number`, `title`, `body`, `state` (`"OPEN"`/`"CLOSED"`/`"MERGED"`),
`isDraft`, `mergeable`, `mergeStateStatus`, `reviewDecision`, `statusCheckRollup`, `author`
(`{"login"}`), `labels` (list of `{"name"}`), `headRefOid`, `headRefName`, `baseRefName`,
`isCrossRepository`, `comments` (list of comment mappings), `headRepository` (`{"name"}`) and
`headRepositoryOwner` (`{"login"}`).

**C6 — how this module calls the adapter.**
1. Obtain: each changed public function gains a keyword-only last parameter
   `forge: ForgeAdapterInterface | None = None` and starts with
   `forge = ForgeSelector().resolve(forge, cfg)` when it has a `cfg`, or
   `forge = ForgeSelector().resolve(forge)` when it has none. `resolve(forge, cfg=None)` returns
   the injected `forge` when it is not `None`, else `self.select(cfg)` when `cfg` is given, else
   `self.select(load_config())`. Pass `forge=forge` down to `fetch_pr` and `upsert_state`.
2. Bind exactly where today's code called `github_state.repository()` (the exhausted listing
   and the label removal), once per call there:
   `name, problem = forge.repository_name()`; `if problem: raise RuntimeError(problem)`;
   `bound = forge.for_repository(name)`. `fetch_pr`, `mark_ready` and `create_label` stay
   unbound, as their `gh` calls carried no `--repo`.
3. A site that raised keeps raising, with its prefix; a site that ignored a result keeps
   ignoring it.

**V — the adapter verbs this lane calls** (all declared on `ForgeAdapterInterface` by wave 1).
- `repository_name(self) -> tuple[str, str]`. GitHub: the bound `self.repository`, else a
  non-empty `$GH_REPO`, else `gh repo view --json nameWithOwner` → its `nameWithOwner`; a `gh`
  failure answers `("", "gh repo view --json nameWithOwner: <stderr>")`, a missing `gh` answers
  ``("", "the GitHub CLI (`gh`) is not installed")``. Forgejo/GitLab: `(self.repository, "")`,
  or `("", "no Forgejo repository is named: set [platform] repository, or give the clone an
  origin remote")` (with `GitLab` in the GitLab text).
- `for_repository(self, repository: str) -> ForgeAdapterInterface`: the same adapter bound to
  that repository; a bound GitHub adapter inserts `--repo <name>` right after the subcommand and
  its positional argument.
- `change_request_with_thread(self, number: int) -> tuple[dict[str, Any] | None, str]`. GitHub:
  `pr view <n> [--repo <R>] --json <the 18 fields of behaviour 11>`; a gh failure answers
  `(None, "gh pr view <n> --json <fields>: <stderr>")`; a non-object answers ``(None, "`gh pr
  view` returned JSON that is not an object")``. Forgejo: the pull plus its paged statuses,
  reviews and issue comments, translated by `ForgejoFacts().threaded(...)`; GitLab: the merge
  request plus statuses, approvals, notes and (for a fork) the source project, translated by
  `GitLabFacts().threaded(...)`.
- `mark_ready(self, number: int) -> tuple[bool, str]`. GitHub: `pr ready <n> [--repo <R>]`;
  exit 0 → `(True, "")`, else `(False, <stripped stderr>)`. Forgejo strips a leading `WIP:` /
  `[WIP]` from the title with a PATCH; GitLab strips `Draft:` / `[Draft]` / `(Draft)` with a PUT.
- `labelled_open_change_request_numbers(self, *, label: str) -> tuple[tuple[int, ...], str]`.
  GitHub: `pr list [--repo <R>] --state open --label <label> --json number`; `null` →
  `((), "")`; a list → the int `number` of every dict item, in the order given; anything else →
  ``((), "`gh pr list` returned JSON that is not a list")``. Forgejo: paged open pulls whose
  labels include `label`, numbers sorted; GitLab: paged
  `projects/{P}/merge_requests?state=opened&labels=<label>`, iids sorted.
- `remove_label(self, number: int, label: str) -> tuple[bool, str]`. GitHub:
  `pr edit <n> [--repo <R>] --remove-label <label>`. Forgejo: finds the label's id in the paged
  `repos/{R}/labels` (absent → `(True, "")`), then DELETE `repos/{R}/issues/{n}/labels/{id}`;
  GitLab: PUT on the merge request with `{"remove_labels": label}`.
- `create_label(self, name: str, *, colour: str, description: str, update_existing: bool) ->
  tuple[bool, str]`. GitHub: `label create <name> [--repo <R>] --color <colour> --description
  <description>` plus `--force` when `update_existing`. Forgejo: an existing label is PATCHed
  when `update_existing`, else `(False, "label '<name>' already exists")`; an absent one is
  POSTed with `"color": "#<colour>"`. GitLab: POST, and a 409 with `update_existing` → PUT.
- Through `upsert_state` (child lane `split-342-1-state-comment`):
  `comment_on_change_request(self, number: int, body: str) -> tuple[bool, str]` for a new state
  comment and `update_comment(self, comment: Mapping[str, Any], body: str) -> tuple[bool, str]`
  for an existing one, both on the bound adapter.

**C7 — tests (amended for 9.b and the fakes standard).**
- 100% line and branch coverage of `vibey_gh` (`src/vibey_tools/gh/pyproject.toml:64-71`).
  Focused runs need `--no-cov`.
- Substitute only at a declared seam: pass `forge=`. Never `monkeypatch.setattr` a module or
  class attribute (`subprocess.run`, `github_state.gh_json`, `pa.fetch_pr`, `pa.upsert_state`,
  a module function), never `mock.patch`, `MagicMock` or `AsyncMock`.
  `monkeypatch.setenv/delenv/chdir` are fine.
- `RecordingForge` (`test/forge_doubles.py`, import with `from forge_doubles import
  RecordingForge`; pytest puts `test/` on `sys.path`) is the in-memory fake of
  `ForgeAdapterInterface`. It is scripted per verb by keyword:
  `RecordingForge(mark_ready=(True, ""), ...)`. Each scripted verb returns its value, or, when
  the value is callable, calls it with the verb's own arguments and returns what it returns.
  `repository_name()` defaults to `("o/r", "")` and can be scripted like any verb, including as
  a callable. `for_repository(name)` records the call and returns the same double. `.calls`
  lists `(verb, *args, *sorted(kwargs.items()))`, so `create_label("x", colour="C",
  description="D", update_existing=True)` is recorded as `("create_label", "x", ("colour", "C"),
  ("description", "D"), ("update_existing", True))`. An unscripted verb raises
  `AttributeError`. Whether `repository_name` itself appears in `.calls` is the double's
  business: every assertion in this spec filters it out or looks for specific entries.
- GitHub argv proofs use the conftest `fake_gh` fixture (`test/conftest.py:87-156`): a real
  `gh` executable put first on `PATH`. `fake_gh.script({...})` replaces every answer, keyed by
  the argv joined with single spaces, each answer an object with optional `out`, `err`, `code`
  (`{}` is a silent success); an unscripted argv exits 3 with `no scripted answer` on stderr.
  `fake_gh.invocations()` lists `{"argv": [...], "cwd": <dir>, "stdin": None}` per run. Build
  the adapter as `GitHubForge(root=tmp_path)` and compare `cwd` with `str(tmp_path.resolve())`.
- No test leaves the machine unless marked `network` (`test/conftest.py:22-40`). Never touch
  `test/conftest.py`.

**C8 — the formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
and the root `ruff format`. Keep lines at or under 100 columns (95 with nested calls); bind long
comparisons to a local before asserting; no implicit string concatenation that would fit on one
line; one argument per line with a trailing comma in multi-line calls; no backslash
continuations. If the two formatters fight over a line, restructure the line; never alternate.

**Depends on:** split-342-1-state-comment, forge-0g, split-333-1-facts-translators, split-333-2-change-request-reads, split-333-3-change-request-text, split-334-1-labelled-listings, split-334-2-open-branches, split-334-3-wait-for-checks, split-335-1-create-edit-merge, split-335-2-ready-close-comment, split-335-3-labels
- split-342-1-state-comment: `upsert_state(..., forge=)`, the `ForgeAdapterInterface` import in `pr_automation.py`, and the fake_gh version of `test_github_helpers_and_state_persistence` this lane trims.
- forge-0g: the end of wave 1 (#338); this lane starts from a branch where every wave-1 lane has merged.
- split-333-1-facts-translators: `ForgejoFacts`/`GitLabFacts`, which give Forgejo's and GitLab's threaded facts the keys `evaluate` reads.
- split-333-2-change-request-reads: `change_request_with_thread(number)`.
- split-333-3-change-request-text: nothing called here; it appends to the same adapter files, so it lands first.
- split-334-1-labelled-listings: `labelled_open_change_request_numbers(label=)`.
- split-334-2-open-branches: nothing called here; it lands first for the same reason.
- split-334-3-wait-for-checks: nothing called here; it lands first for the same reason.
- split-335-1-create-edit-merge: nothing called here; it lands first for the same reason.
- split-335-2-ready-close-comment: `mark_ready(number)` and `comment_on_change_request(number, body)`.
- split-335-3-labels: `remove_label(number, label)` and `create_label(name, *, colour, description, update_existing)`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
