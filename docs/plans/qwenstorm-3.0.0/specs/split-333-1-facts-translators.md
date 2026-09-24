<!-- split of #333: child 1 of 3; audit: issue-audit/updates/333.md -->

## Title
feat(gh): Forgejo and GitLab change-request facts translate into the merge train's mapping

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge
(`src/vibey_tools/gh/docs/doctrines.md:138`), and vibey-gh's own default is
`[platform] kind = "forgejo"` (`vibey_gh/config.py:288`). The merge train decides on a change
request's full state with `merge_train.judge(pr, cfg)` (`vibey_gh/merge_train.py:124-234`), and
PR automation does the same with `pr_automation.evaluate`. Both read a dict whose keys are
`gh pr view --json` field names (`merge_train.py:237-246`, `vibey_gh/pr_automation.py:480-482`),
and their tests (thousands of lines) build those dicts.

For the default forge to reach these decisions, a Forgejo pull request (and a GitLab merge
request) must be translated into a mapping with those keys and values. This lane adds that
translation as two pure classes, the first step before the adapter verbs (child lanes 2 and 3)
use it.

Keeping GitHub's key spellings is a deliberate, transitional deviation from 8.b's "the protocol is
vibey's" (`docs/doctrines.md:168-176`). It is recorded in the wave's appendix for the operator;
converting the decision functions to neutral records is a later follow-up, not this lane.

## Required behaviour
1. `vibey_gh/forge.py` gains two tuple constants, placed after `__all__` and before
   `class ForgeKind`, both added to `__all__` in its sorted order (`"CHANGE_REQUEST_FACT_KEYS"`
   first, before `"ChangeRequest"`; `"THREADED_CHANGE_REQUEST_FACT_KEYS"` last, after
   `"ProtectedRef"`). Write each one element per line with a trailing comma:
   - `CHANGE_REQUEST_FACT_KEYS = ("number", "title", "body", "state", "isDraft", "mergeable",
     "mergeStateStatus", "reviewDecision", "statusCheckRollup", "author", "labels", "headRefOid",
     "headRefName", "baseRefName", "isCrossRepository", "changedFiles")`
   - `THREADED_CHANGE_REQUEST_FACT_KEYS = ("number", "title", "body", "state", "isDraft",
     "mergeable", "mergeStateStatus", "reviewDecision", "statusCheckRollup", "author", "labels",
     "headRefOid", "headRefName", "baseRefName", "isCrossRepository", "comments",
     "headRepository", "headRepositoryOwner")`: the same keys without `"changedFiles"`, followed
     by `"comments", "headRepository", "headRepositoryOwner"`.
2. The value schema, which every translator below produces:

   | key | value |
   |---|---|
   | `number` | int |
   | `title`, `body` | str |
   | `state` | `"OPEN"` \| `"CLOSED"` \| `"MERGED"` |
   | `isDraft` | bool |
   | `mergeable` | `"MERGEABLE"` \| `"CONFLICTING"` \| `"UNKNOWN"` |
   | `mergeStateStatus` | `"BEHIND"` or `"UNKNOWN"` |
   | `reviewDecision` | `"APPROVED"` \| `"CHANGES_REQUESTED"` \| `""` |
   | `statusCheckRollup` | list of `{"name", "status": "COMPLETED"\|"IN_PROGRESS", "conclusion": "SUCCESS"\|"FAILURE"\|"NEUTRAL"\|"SKIPPED"\|"CANCELLED"\|None, "startedAt", "completedAt", "detailsUrl"}` |
   | `author` | `{"login": str}` |
   | `labels` | list of `{"name": str}` |
   | `headRefOid`, `headRefName`, `baseRefName` | str |
   | `isCrossRepository` | bool |
   | `changedFiles` | int. **Omit the key** when the forge gives no count: the protected-paths guard then refuses rather than guesses. |
   | `comments` (threaded only) | list of `{"id": str, "url": str, "body": str, "author": {"login": str}, "createdAt": str}`. GitLab adds `"noteable_type"` and `"noteable_iid"`. |
   | `headRepository` / `headRepositoryOwner` (threaded only) | `{"name": str}` / `{"login": str}`, with empty strings when unknown |

   Every translator reads its input with `.get(key)` and a default, never `raw[key]`, so a
   missing field gives the empty value of its type and never raises. Strings are
   `str(value or "")`; `number` is `int(value or 0)`.
3. New `vibey_gh/forge_forgejo_facts.py`, class `ForgejoFacts(ForgejoFactsInterface)`. It is
   pure: no I/O and no state, a class for 9.b. Its inputs are Forgejo REST objects
   (`Mapping[str, Any]` / `Sequence[Mapping[str, Any]]`). Its public methods, exactly:
   - `state(self, raw: Mapping[str, Any]) -> str`: `"MERGED"` if `raw.get("merged")`, else
     `"OPEN"` if `raw.get("state") == "open"`, else `"CLOSED"`.
   - `draft(self, pull: Mapping[str, Any]) -> bool`: `pull["draft"]` when it is a bool.
     Otherwise true when the title, after leading whitespace and case-insensitively, starts with
     `WIP:` or `[WIP]` (`title.lstrip().lower().startswith(("wip:", "[wip]"))`).
   - `check_name(self, context: str) -> str`: strips one trailing ` (<event>)` matching
     `r" \([a-z_]+\)$"` (a module constant `_EVENT_SUFFIX = re.compile(r" \([a-z_]+\)$")`).
     Forgejo Actions appends the event, so `"PR evaluate / gate (pull_request)"` becomes
     `"PR evaluate / gate"`.
   - `rollup_entry(self, status: Mapping[str, Any]) -> dict[str, Any]`:
     - `name` = `check_name(str(status.get("context") or ""))`;
     - `status` = `"IN_PROGRESS"` if `status.get("state") == "pending"`, else `"COMPLETED"`;
     - `conclusion` from `{"success": "SUCCESS", "failure": "FAILURE", "error": "FAILURE",
       "warning": "NEUTRAL"}`, else `None`;
     - `startedAt` = `created_at`, `completedAt` = `updated_at`, `detailsUrl` = `target_url`.
       Each is the empty string when missing.
   - `check_result(self, status: Mapping[str, Any], sha: str) -> CheckResult`:
     `CheckResult(check_name(context), sha, {"success": "success", "failure": "failure",
     "error": "failure", "warning": "neutral"}.get(state, ""))`.
   - `review_decision(self, reviews: Sequence[Mapping[str, Any]]) -> str`: among reviews with
     `dismissed` not `True` and `state` in `{"APPROVED", "REQUEST_CHANGES"}`, take the latest one
     per `user.login`, in list order (a later review of the same user replaces an earlier one).
     Any latest `REQUEST_CHANGES` → `"CHANGES_REQUESTED"`, else any `APPROVED` → `"APPROVED"`,
     else `""`. A later `COMMENT` review does not cancel an approval.
   - `comment(self, raw: Mapping[str, Any]) -> dict[str, Any]`: `{"id": str(raw.get("id") or
     ""), "url": html_url or "", "body": body or "", "author": {"login": user.login or
     user.username or ""}, "createdAt": created_at or ""}`.
   - `change_request(self, pull: Mapping[str, Any], statuses: Sequence[Mapping[str, Any]],
     reviews: Sequence[Mapping[str, Any]]) -> dict[str, Any]`: every key of
     `CHANGE_REQUEST_FACT_KEYS`:
     - `number` from `number`, `title`, `body`, `state` = `self.state(pull)`, `isDraft` =
       `self.draft(pull)`;
     - `mergeable`: `True` → `"MERGEABLE"`, `False` → `"CONFLICTING"`, missing (or anything
       else) → `"UNKNOWN"`;
     - `mergeStateStatus` = `"UNKNOWN"` (Forgejo cannot say "behind");
     - `reviewDecision` = `self.review_decision(reviews)`;
     - `statusCheckRollup` = `[self.rollup_entry(status) for status in statuses]`;
     - `author` = `{"login": user.login or user.username or ""}` from `pull["user"]`;
     - `labels` = `[{"name": str(label.get("name") or "")}]` for each label that is a dict;
     - `headRefOid` / `headRefName` / `baseRefName` from `head.sha` / `head.ref` / `base.ref`;
     - `isCrossRepository` = `head.repo_id != base.repo_id` when both are ints, else `False`;
     - `changedFiles` only when `pull["changed_files"]` is an int and not a bool.
   - `threaded(self, pull, statuses, reviews, comments: Sequence[Mapping[str, Any]]) ->
     dict[str, Any]`: the threaded key set: `change_request(...)` without `changedFiles`, plus
     `comments` = `[self.comment(c) for c in comments]`, `headRepository = {"name":
     head.repo.name}` and `headRepositoryOwner = {"login": head.repo.owner.login}`, with empty
     strings when absent.
4. New `vibey_gh/forge_gitlab_facts.py`, class `GitLabFacts(GitLabFactsInterface)`, pure like
   `ForgejoFacts`, over GitLab REST objects. Its public methods, exactly: `state`, `draft`,
   `rollup_entry`, `check_result`, `review_decision`, `comment`, `change_request`, `threaded`
   (GitLab status names carry no event suffix, so there is no `check_name`):
   - `state(self, mr) -> str`: `"opened"` → `"OPEN"`, `"merged"` → `"MERGED"`, else `"CLOSED"`.
   - `draft(self, mr) -> bool` = `bool(mr.get("draft") or mr.get("work_in_progress"))`.
   - `review_decision(self, approvals: Mapping[str, Any]) -> str` = `"APPROVED"` if
     `approvals.get("approved")`, else `""`.
   - `rollup_entry(self, status) -> dict[str, Any]`, from a commit status:
     - `success` → COMPLETED/SUCCESS, `failed` → COMPLETED/FAILURE, `canceled` →
       COMPLETED/CANCELLED, `skipped` → COMPLETED/SKIPPED;
     - anything else → IN_PROGRESS/`None`;
     - `name` = `status.get("name")`, `startedAt` = `started_at or created_at`, `completedAt` =
       `finished_at`, `detailsUrl` = `target_url`, each `""` when missing.
   - `check_result(self, status, sha) -> CheckResult` maps `success` → `"success"`, `failed` →
     `"failure"`, `canceled` → `"cancelled"`, `skipped` → `"skipped"`, else `""`; the name is the
     status's `name`.
   - `comment(self, note) -> dict[str, Any]`: `{"id": str(id), "url": "", "body": body or "",
     "author": {"login": author.username or ""}, "createdAt": created_at or "",
     "noteable_type": str(noteable_type or ""), "noteable_iid": note.get("noteable_iid")}`.
     GitLab notes carry no web URL.
   - `change_request(self, mr, statuses, approvals: Mapping[str, Any]) -> dict[str, Any]`:
     - `number` = `iid`, `title`, `body` = `description or ""`, `state`, `isDraft`;
     - `mergeable` = `"CONFLICTING"` if `has_conflicts`, else `"MERGEABLE"`;
     - `mergeStateStatus` = `"BEHIND"` when `detailed_merge_status == "need_rebase"`, else
       `"UNKNOWN"`;
     - `reviewDecision` = `self.review_decision(approvals)`;
     - `statusCheckRollup` = `[self.rollup_entry(status) for status in statuses]`;
     - `author` = `{"login": author.username or ""}`;
     - `labels`: labels are strings on GitLab, so each becomes `{"name": str(label)}`;
     - `headRefOid` = `sha`, `headRefName` = `source_branch`, `baseRefName` = `target_branch`;
     - `isCrossRepository` = `source_project_id != target_project_id`;
     - `changedFiles` = `int(changes_count)` only when `changes_count` is a string of digits
       (`isinstance(count, str) and count.isdigit()`; GitLab may send `"1000+"`).
   - `threaded(self, mr, statuses, approvals, notes, source_project: Mapping[str, Any]) ->
     dict[str, Any]`: `change_request(...)` without `changedFiles`, plus `comments` =
     `[self.comment(n) for n in notes if n.get("system") is not True]` (notes with
     `system: true` are dropped), `headRepository = {"name": source_project.get("path") or ""}`
     and `headRepositoryOwner = {"login": (source_project.get("namespace") or
     {}).get("full_path") or ""}`. The caller passes `source_project={}` when the merge request
     is not cross-repository.
5. Interfaces (ADR-0016 / 9.b): `vibey_gh/interfaces/forge_forgejo_facts_interface.py`
   (`ForgejoFactsInterface`) and `vibey_gh/interfaces/forge_gitlab_facts_interface.py`
   (`GitLabFactsInterface`), each a `@runtime_checkable` `Protocol` declaring every public method
   of its class with the same signature and a one-line docstring, and a `...` body. They import
   only the standard library and `vibey_gh.forge` (for `CheckResult`), like
   `vibey_gh/interfaces/forge_adapter_interface.py:23-33`. Each class subclasses its interface.
   They need no export from `vibey_gh/interfaces/__init__.py` (the adapter interface is not
   exported either).
6. No adapter, protocol or consumer changes in this lane.

## Where to change
Every path in this spec is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package
`vibey_gh`) unless it starts with `src/` or `.github/`; the check block starts with
`cd src/vibey_tools/gh`. Line anchors are those of the storm integration branch at `4317cff6`,
except `vibey_gh/forge.py`, which the forge foundation lanes already changed (read it again before
editing).

Five production files, because the lane adds two translator classes and each class has its
interface beside it:
- `vibey_gh/forge.py`: the two constants and `__all__`.
- New: `vibey_gh/forge_forgejo_facts.py`, `vibey_gh/forge_gitlab_facts.py`,
  `vibey_gh/interfaces/forge_forgejo_facts_interface.py`,
  `vibey_gh/interfaces/forge_gitlab_facts_interface.py`. Each file starts with the provenance
  header line, copied byte for byte from `vibey_gh/forge.py:1`:
  `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  then a module docstring, then `from __future__ import annotations`.
- Test: `test/test_forge_facts.py` (new).
- Only if `test/test_patching_ratchet.py` exists when you start (another storm lane adds the
  tenant's patching ratchet) and it fails on a test file this lane created: record that file in
  `test/patching_baseline.json` with its true counts, all zero (this lane adds no patch). Never
  raise a count. If the ratchet does not exist, skip this.
- Only if `test/test_port_parity.py` exists when you start (another storm lane adds the
  tenant's fakes registry) and it fails on the two new interfaces: add `ForgejoFactsInterface`
  and `GitLabFactsInterface` to its `EXEMPT` with the reason `"pure policy: a stateless
  translator that is its own in-memory implementation"`. If it does not exist, skip this.

## Acceptance criteria
- [ ] `set(ForgejoFacts().change_request(PULL, STATUSES, REVIEWS)) == set(CHANGE_REQUEST_FACT_KEYS)`
      for a fixture with `changed_files`. Without it, the result is the same set minus
      `"changedFiles"`. The same holds for GitLab, and for both `threaded(...)` against
      `THREADED_CHANGE_REQUEST_FACT_KEYS` (`test_fact_keys_are_exactly_the_schema`).
- [ ] `merge_train.judge(facts, GhConfig(root=tmp_path)).ready` is true for a green, mergeable,
      approved Forgejo fixture and a GitLab fixture
      (`test_the_facts_feed_the_unchanged_merge_judge`). This proves the schema feeds the
      unchanged judge.
- [ ] `python -m pytest -q` (run in `src/vibey_tools/gh`) passes with 100% line and branch
      coverage of `vibey_gh`. Formatters and type checks are clean (the check block below).

## Tests to write first (TDD)
`test/test_forge_facts.py` (new; provenance header first) uses plain dict fixtures, with no
transport and no `gh`. Imports:
```python
from __future__ import annotations

import pytest

from vibey_gh.config import GhConfig
from vibey_gh.forge import (
    CHANGE_REQUEST_FACT_KEYS,
    THREADED_CHANGE_REQUEST_FACT_KEYS,
    CheckResult,
)
from vibey_gh.forge_forgejo_facts import ForgejoFacts
from vibey_gh.forge_gitlab_facts import GitLabFacts
from vibey_gh.interfaces.forge_forgejo_facts_interface import ForgejoFactsInterface
from vibey_gh.interfaces.forge_gitlab_facts_interface import GitLabFactsInterface
from vibey_gh.merge_train import judge
```
Fixtures (module constants):
```python
PULL = {
    "number": 7,
    "title": "Add a thing",
    "body": "Body",
    "state": "open",
    "mergeable": True,
    "user": {"login": "ada"},
    "labels": [{"name": "bug"}, "not-a-label"],
    "head": {
        "ref": "topic",
        "sha": "abc",
        "repo_id": 2,
        "repo": {"name": "fork-r", "owner": {"login": "fork-o"}},
    },
    "base": {"ref": "develop", "repo_id": 1},
    "changed_files": 3,
}
MR = {
    "iid": 7,
    "title": "Add a thing",
    "description": None,
    "state": "opened",
    "has_conflicts": False,
    "detailed_merge_status": "mergeable",
    "author": {"username": "ada"},
    "labels": ["bug"],
    "sha": "abc",
    "source_branch": "topic",
    "target_branch": "develop",
    "source_project_id": 2,
    "target_project_id": 1,
    "changes_count": "3",
}
NOTES = [
    {
        "id": 1,
        "body": "hi",
        "author": {"username": "bo"},
        "created_at": "2026-09-22T10:00:00Z",
        "system": False,
        "noteable_type": "MergeRequest",
        "noteable_iid": 7,
    },
    {"id": 2, "body": "added 1 commit", "author": {"username": "ada"}, "system": True},
]
```
Tests (build variants with `{**PULL, "key": value}`, and drop a key with
`{k: v for k, v in PULL.items() if k != "key"}`):
- `test_forgejo_facts_translate_a_pull_request`: `ForgejoFacts().change_request(PULL, [], [])`
  equals the full expected dict `{"number": 7, "title": "Add a thing", "body": "Body", "state":
  "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "mergeStateStatus": "UNKNOWN",
  "reviewDecision": "", "statusCheckRollup": [], "author": {"login": "ada"}, "labels": [{"name":
  "bug"}], "headRefOid": "abc", "headRefName": "topic", "baseRefName": "develop",
  "isCrossRepository": True, "changedFiles": 3}` (bind it to `expected` first). Then:
  - states: `"merged": True` → `"MERGED"`; `"state": "closed"` → `"CLOSED"`;
  - draft by flag: `"draft": True` → `True`; `"draft": False` with title `"WIP: x"` → `False`
    (the flag wins); no flag and title `"  wip: later"` → `True`; `"[WIP] x"` → `True`;
  - `mergeable`: `False` → `"CONFLICTING"`; key missing → `"UNKNOWN"`;
  - cross-repository: `base` with `repo_id: 2` → `False`; a head without `repo_id` → `False`;
  - `changed_files` absent → no `changedFiles` key; `changed_files: True` → no key;
  - author from `{"user": {"username": "bo"}}` → `{"login": "bo"}`; a pull with no `user`,
    `head`, `base` or `labels` still answers (author `{"login": ""}`, refs `""`, labels `[]`).
- `test_forgejo_facts_decide_the_review_and_the_rollup`:
  - `ForgejoFacts().check_name("PR evaluate / gate (pull_request)") == "PR evaluate / gate"`;
    `"Build (push)"` → `"Build"`; `"A (b) (push)"` → `"A (b)"`; `"CI"` and `"Upper (Push)"`
    unchanged;
  - `rollup_entry({"context": "CI (pull_request)", "state": "success", "created_at": "t1",
    "updated_at": "t2", "target_url": "u"}) == {"name": "CI", "status": "COMPLETED",
    "conclusion": "SUCCESS", "startedAt": "t1", "completedAt": "t2", "detailsUrl": "u"}`;
  - `{"context": "CI", "state": "pending"}` → `status "IN_PROGRESS"`, `conclusion None`, and
    `startedAt`, `completedAt`, `detailsUrl` all `""`;
  - `failure` → `FAILURE`, `error` → `FAILURE`, `warning` → `NEUTRAL`, an unknown state
    (`"skipped"`) → `COMPLETED` / `None`;
  - review decision: `[]` → `""`; `[{"user": {"login": "ada"}, "state": "APPROVED"},
    {"user": {"login": "bo"}, "state": "REQUEST_CHANGES", "dismissed": True}]` → `"APPROVED"`
    (a dismissed request is ignored); `[{"user": {"login": "ada"}, "state": "APPROVED"},
    {"user": {"login": "ada"}, "state": "COMMENT"}]` → `"APPROVED"` (a later comment keeps the
    approval); `[{"user": {"login": "ada"}, "state": "REQUEST_CHANGES"}, {"user": {"login":
    "ada"}, "state": "APPROVED"}]` → `"APPROVED"` (the latest review per user wins);
    `[{"user": {"login": "ada"}, "state": "APPROVED"}, {"user": {"login": "bo"}, "state":
    "REQUEST_CHANGES"}]` → `"CHANGES_REQUESTED"`.
- `test_forgejo_check_result_and_comment`:
  - `check_result({"context": "CI (push)", "state": "error"}, "abc") == CheckResult("CI", "abc",
    "failure")`; `success` → `"success"`, `warning` → `"neutral"`, `pending` → `""`;
  - `comment({"id": 5, "html_url": "https://f/x#c5", "body": "hi", "user": {"login": "ada"},
    "created_at": "t1"}) == {"id": "5", "url": "https://f/x#c5", "body": "hi", "author":
    {"login": "ada"}, "createdAt": "t1"}`; `comment({"id": 6, "user": {"username": "bo"}}) ==
    {"id": "6", "url": "", "body": "", "author": {"login": "bo"}, "createdAt": ""}`;
  - `threaded(PULL, [], [], [{"id": 5, "user": {"login": "ada"}}])` has `headRepository ==
    {"name": "fork-r"}`, `headRepositoryOwner == {"login": "fork-o"}` and one comment; with a
    head that has no `repo`, both are `{"name": ""}` / `{"login": ""}`;
  - `isinstance(ForgejoFacts(), ForgejoFactsInterface)`.
- `test_gitlab_facts_translate_a_merge_request`:
  - `GitLabFacts().change_request(MR, [], {})` has `number 7`, `body ""`, `state "OPEN"`,
    `isDraft False`, `mergeable "MERGEABLE"`, `mergeStateStatus "UNKNOWN"`, `reviewDecision ""`,
    `author {"login": "ada"}`, `labels [{"name": "bug"}]`, refs `abc`/`topic`/`develop`,
    `isCrossRepository True`, `changedFiles 3`;
  - states: `"merged"` → `"MERGED"`, `"closed"` → `"CLOSED"`;
  - draft: `"draft": True` → `True`; `"work_in_progress": True` → `True`;
  - `"has_conflicts": True` → `"CONFLICTING"`;
  - `"detailed_merge_status": "need_rebase"` → `"BEHIND"`;
  - approvals `{"approved": True}` → `"APPROVED"`;
  - statuses: `rollup_entry({"name": "CI", "status": "success", "started_at": "t1",
    "finished_at": "t2", "target_url": "u"})` → COMPLETED/SUCCESS with those times;
    `{"name": "CI", "status": "running", "created_at": "t0"}` → IN_PROGRESS/`None`,
    `startedAt "t0"`, `completedAt ""`, `detailsUrl ""`; `failed` → FAILURE, `canceled` →
    CANCELLED, `skipped` → SKIPPED;
  - `check_result`: `success` → `"success"`, `failed` → `"failure"`, `canceled` →
    `"cancelled"`, `skipped` → `"skipped"`, `"running"` → `""`;
  - `changes_count` given as `"3"` → `changedFiles 3`, as `"1000+"` → no key, missing → no key;
  - `threaded(MR, [], {}, NOTES, {"path": "fork-r", "namespace": {"full_path": "fork-o"}})`: the
    system note is dropped, the one comment is `{"id": "1", "url": "", "body": "hi", "author":
    {"login": "bo"}, "createdAt": "2026-09-22T10:00:00Z", "noteable_type": "MergeRequest",
    "noteable_iid": 7}`, and the source project is read into `headRepository {"name": "fork-r"}`
    and `headRepositoryOwner {"login": "fork-o"}`; with `source_project={}` both are empty;
  - `isinstance(GitLabFacts(), GitLabFactsInterface)`.
- `test_fact_keys_are_exactly_the_schema`: set equality as in the acceptance criteria, for both
  forges, plain and threaded, with and without the change count (`PULL` without
  `changed_files`; `MR` with `changes_count "1000+"`).
- `test_the_facts_feed_the_unchanged_merge_judge`, exactly:
  ```python
  def test_the_facts_feed_the_unchanged_merge_judge(tmp_path):
      cfg = GhConfig(root=tmp_path)
      gates = ("PR evaluate / gate", "PR review / gate")
      pull = {
          "number": 7,
          "title": "Add a thing",
          "state": "open",
          "mergeable": True,
          "user": {"login": "ada"},
          "head": {"ref": "topic", "sha": "abc", "repo_id": 1},
          "base": {"ref": "develop", "repo_id": 1},
      }
      statuses = [{"context": f"{gate} (pull_request)", "state": "success"} for gate in gates]
      reviews = [{"user": {"login": "bo"}, "state": "APPROVED"}]
      assert judge(ForgejoFacts().change_request(pull, statuses, reviews), cfg).ready
      mr = {**MR, "source_project_id": 1, "target_project_id": 1}
      gitlab_statuses = [{"name": gate, "status": "success"} for gate in gates]
      facts = GitLabFacts().change_request(mr, gitlab_statuses, {"approved": True})
      assert judge(facts, cfg).ready
  ```
  With `GhConfig(root=tmp_path)` defaults, PR automation is enabled, so `judge` needs both gates
  `COMPLETED`/`SUCCESS` in the rollup; the base `develop` is not the release branch `main`; and no
  protected paths are configured.

Keep every fixture line at or under 100 columns (write long dicts one key per line).

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_facts.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only vibey_gh/forge.py among tracked files
git status --short   # the five new files named under "Where to change", and nothing else new
```
If black or isort reports a file you touched, run `python -m black --line-length 100 <file>` and
`isort <file>` on that file only, then run the whole block again.

## Out of scope
- The adapters and the protocol (`vibey_gh/forge_github.py`, `vibey_gh/forge_forgejo.py`,
  `vibey_gh/forge_gitlab.py`, `vibey_gh/interfaces/forge_adapter_interface.py`): child lanes 2
  and 3 (`split-333-2-change-request-reads`, `split-333-3-change-request-text`) own them.
- `vibey_gh/merge_train.py`, `vibey_gh/pr_automation.py` and every other consumer: later forge
  lanes. `judge` is only called by the test, never changed.
- `vibey_gh/interfaces/__init__.py` and `vibey_gh/interfaces/class_contracts.py`.
- `test/conftest.py`, `test/forge_doubles.py` and every existing test file.
- The repository's `[platform] kind = "github"` declaration in the root `.vibey-gh.toml`
  (lines 18-19): never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  when done.

## Conventions this lane relies on (everything needed is here)
- **Neutral mapping schemas.** The decision functions that consume change requests
  (`merge_train.judge`, `pr_automation.evaluate`, the protected-paths guard) read dicts, and
  their tests build those dicts. To keep them untouched in this wave, the verbs that feed them
  return mappings whose keys are the ones those functions already read, the historical `gh`
  spellings. The adapters are what make the values forge-neutral. The two constants in
  `vibey_gh/forge.py` name those key sets; the table above is their value schema.
- **Pure translators.** `ForgejoFacts` and `GitLabFacts` hold no state and do no I/O, no clock and
  no network; they are classes (9.b) so each has its interface beside it (ADR-0016). A test
  builds them directly: `ForgejoFacts()`.
- **Tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
  (`pyproject.toml:64-71`). Focused runs need `--no-cov`; the whole-suite run must pass without
  it. Protocol classes are excluded from coverage (`class .*\bProtocol\):` in `exclude_lines`),
  so interface bodies need no tests. Substitute only at a declared seam: no `monkeypatch.setattr`
  of an import or of a module or class attribute, no `mock.patch`, no `MagicMock`/`AsyncMock`
  (sub-doctrine 9.b).
- **Editing.** Change `vibey_gh/forge.py` with `edit_file` only (never `write_file` on an existing
  file). Create the five new files with `write_file`.
- **The formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
  (profile black, `combine_as_imports`; CI job `tools-lint`, `.github/workflows/ci.yml:699-705`)
  and the root `ruff format --check .` (line length 100). They disagree on some wraps, so write
  lines neither wants to rewrap:
  - keep every line at or under 100 columns;
  - bind a long expected value to a local before the `assert`;
  - never use implicit string concatenation; use one literal, or an f-string built from locals;
  - never put a string literal inside an f-string's braces; bind it to a local first;
  - write multi-line calls and collections with one element per line and a trailing comma;
  - never use backslash continuations.

  If the two formatters fight over a line, restructure the line. Never alternate between them.
- **mypy.** The tenant runs `mypy vibey_gh` with `warn_return_any = true`: wrap a value read from
  a mapping in `str(...)`, `int(...)` or `bool(...)` before returning it where the signature
  says `str`, `int` or `bool`.

**Depends on:** split-332-1-transport-seams, split-332-2-adapter-paging, split-332-3-repository-name, split-332-4-selector-resolve
- split-332-1-transport-seams: `vibey_gh/forge.py` as it now stands (`NotSupported` in `__all__`),
  which this lane edits next.
- split-332-2-adapter-paging: lands first because the forge wave's first half is sequential; this
  lane uses nothing else from it.
- split-332-3-repository-name: lands first for the same reason; this lane uses nothing from it.
- split-332-4-selector-resolve: lands first for the same reason; this lane uses nothing from it.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
