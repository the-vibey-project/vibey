<!-- split of #333: child 2 of 3; audit: issue-audit/updates/333.md -->

## Title
feat(gh): the forge adapter reads a change request's facts, thread and check results

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge
(`src/vibey_tools/gh/docs/doctrines.md:138`), and every forge call must go through
`ForgeAdapterInterface` (`docs/doctrines.md:168-176`). Three reads the merge train and PR
automation make are still raw `gh`:

- the merge train's facts for a pull request, `gh pr view N --json <16 fields>`
  (`vibey_gh/merge_train.py:250`, fields at `:237-246`);
- PR automation's facts plus its conversation, `gh pr view N --json <18 fields>`
  (`vibey_gh/pr_automation.py:472-484`, fields at `:480-482`);
- the check runs on an exact head, `gh api repos/R/commits/SHA/check-runs`
  (`vibey_gh/merge_train.py:304-313`), which only counts a run whose `status` is `completed`.

The adapter's existing `get_check_results` answers bare dicts and ignores whether a check finished
(`vibey_gh/forge_github.py:199-221`), and its GitLab route is wrong
(`vibey_gh/forge_gitlab.py:183-185` asks `projects/:id/commits/:sha/statuses`; GitLab's API is
`projects/:id/repository/commits/:sha/statuses`). The previous lane added the translators that
turn Forgejo and GitLab objects into the mapping the decisions read; this lane adds the verbs
that fetch those objects.

## Required behaviour
1. `vibey_gh/forge_github.py` gains, after `GH_DEFAULT_HOST = "github.com"` (integration line 34)
   and before the class, the two field lists, each built from a tuple so no line is long:
   ```python
   # `gh pr view --json` fields in the order the merge train asks for them
   # (`merge_train.py:237-246`), so the argv stays byte for byte what it runs today.
   _CHANGE_REQUEST_FACT_FIELD_NAMES = (
       "number",
       "title",
       "state",
       "isDraft",
       "mergeable",
       "mergeStateStatus",
       "reviewDecision",
       "statusCheckRollup",
       "author",
       "labels",
       "headRefOid",
       "headRefName",
       "baseRefName",
       "isCrossRepository",
       "body",
       "changedFiles",
   )
   CHANGE_REQUEST_FACT_FIELDS = ",".join(_CHANGE_REQUEST_FACT_FIELD_NAMES)
   # The fields PR automation asks for (`pr_automation.py:480-482`), in its order.
   _THREADED_CHANGE_REQUEST_FIELD_NAMES = (
       "number",
       "title",
       "state",
       "isDraft",
       "mergeable",
       "mergeStateStatus",
       "reviewDecision",
       "statusCheckRollup",
       "author",
       "labels",
       "comments",
       "headRefOid",
       "headRefName",
       "headRepository",
       "headRepositoryOwner",
       "isCrossRepository",
       "baseRefName",
       "body",
   )
   THREADED_CHANGE_REQUEST_FIELDS = ",".join(_THREADED_CHANGE_REQUEST_FIELD_NAMES)
   ```
2. `vibey_gh/interfaces/forge_adapter_interface.py`: the `vibey_gh.forge` import gains
   `CheckResult`; `get_check_results` (integration lines 86-88) is reshaped, and two verbs are
   declared directly after it:
   ```python
       def get_check_results(self, head_sha: str) -> tuple[tuple[CheckResult, ...], str]:
           """One `CheckResult` per check on the commit, and a problem."""
           ...

       # --- Change-request reads ---

       def change_request_facts(self, number: int) -> tuple[dict[str, Any] | None, str]:
           """A change request's facts, keyed as `forge.CHANGE_REQUEST_FACT_KEYS`."""
           ...

       def change_request_with_thread(self, number: int) -> tuple[dict[str, Any] | None, str]:
           """Its facts and conversation, keyed as `THREADED_CHANGE_REQUEST_FACT_KEYS`."""
           ...
   ```
   All three adapters implement all three (mypy treats an unimplemented protocol member of an
   explicit subclass as abstract).
3. **GitHub** (`vibey_gh/forge_github.py`; the `vibey_gh.forge` import gains `CheckResult`).
   Append at the end of the class:
   ```python
       def change_request_facts(self, number: int) -> tuple[dict[str, Any] | None, str]:
           return self._change_request(number, CHANGE_REQUEST_FACT_FIELDS)

       def change_request_with_thread(self, number: int) -> tuple[dict[str, Any] | None, str]:
           return self._change_request(number, THREADED_CHANGE_REQUEST_FIELDS)

       def _change_request(self, number: int, fields: str) -> tuple[dict[str, Any] | None, str]:
           """`gh pr view <n> [--repo R] --json <fields>` as an object, and a problem."""
           args = self._scoped(["pr", "view", str(number)], ["--json", fields])
           value, problem = self._read(args)
           if problem:
               return None, problem
           if not isinstance(value, dict):
               return None, "`gh pr view` returned JSON that is not an object"
           return value, ""
   ```
   A JSON `null` or empty output is also "not an object". Replace `get_check_results` in place
   (the argv is unchanged, read through `_read` now; the two shape problems are kept word for
   word; a conclusion counts only when the run's `status` is `completed`):
   ```python
       def get_check_results(self, head_sha: str) -> tuple[tuple[CheckResult, ...], str]:
           name, problem = self.repository_name()
           if problem:
               return (), problem
           val, problem = self._read(["api", f"repos/{name}/commits/{head_sha}/check-runs"])
           if problem:
               return (), problem
           if not isinstance(val, dict):
               return (), "Expected object for check-runs"
           runs = val.get("check_runs", [])
           if not isinstance(runs, list):
               return (), "check_runs field is not a list"
           results: list[CheckResult] = []
           for entry in runs:
               if not isinstance(entry, dict):
                   continue
               finished = entry.get("status") == "completed"
               conclusion = str(entry.get("conclusion") or "") if finished else ""
               results.append(CheckResult(str(entry.get("name") or ""), head_sha, conclusion))
           return tuple(results), ""
   ```
4. **Forgejo** (`vibey_gh/forge_forgejo.py`; imports gain `CheckResult` from `vibey_gh.forge` and
   `from vibey_gh.forge_forgejo_facts import ForgejoFacts`). Implement and test it first (8.b).
   Append at the end of the class:
   ```python
       def change_request_facts(self, number: int) -> tuple[dict[str, Any] | None, str]:
           pull, statuses, reviews, problem = self._pull_reads(number)
           if problem:
               return None, problem
           return ForgejoFacts().change_request(pull, statuses, reviews), ""

       def change_request_with_thread(self, number: int) -> tuple[dict[str, Any] | None, str]:
           pull, statuses, reviews, problem = self._pull_reads(number)
           if problem:
               return None, problem
           # ONE request, never _pages: Forgejo's issues/{index}/comments takes no page or limit
           # and answers every comment at once. `_comments` is split-332-2's helper.
           comments, problem = self._comments(number)
           if problem:
               return None, problem
           return ForgejoFacts().threaded(pull, statuses, reviews, comments), ""

       def _object(self, path: str) -> tuple[dict[str, Any] | None, str]:
           """The one JSON object the forge answers `path` with, and a problem."""
           value, problem = self.transport.survey([path], cwd=self.root)
           if problem:
               return None, problem
           if not isinstance(value, dict):
               return None, f"Forgejo answered {path} with something other than an object"
           return value, ""

       def _pull_reads(
           self, number: int
       ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
           """A pull request, its head's commit statuses and its reviews, and a problem."""
           repository = self._repository()
           pull, problem = self._object(f"repos/{repository}/pulls/{number}")
           if pull is None:
               return {}, [], [], problem
           sha = str((pull.get("head") or {}).get("sha") or "")
           statuses, problem = self._pages(f"repos/{repository}/commits/{sha}/statuses")
           if problem:
               return {}, [], [], problem
           reviews, problem = self._pages(f"repos/{repository}/pulls/{number}/reviews")
           if problem:
               return {}, [], [], problem
           return pull, statuses, reviews, ""
   ```
   Replace `get_check_results` in place (the old `"Check results are not a list"` branch goes:
   `_pages` reports a non-list page):
   ```python
       def get_check_results(self, head_sha: str) -> tuple[tuple[CheckResult, ...], str]:
           path = f"repos/{self._repository()}/commits/{head_sha}/statuses"
           statuses, problem = self._pages(path)
           if problem:
               return (), problem
           facts = ForgejoFacts()
           return tuple(facts.check_result(status, head_sha) for status in statuses), ""
   ```
5. **GitLab** (`vibey_gh/forge_gitlab.py`; imports gain `CheckResult` from `vibey_gh.forge` and
   `from vibey_gh.forge_gitlab_facts import GitLabFacts`). Append at the end of the class:
   ```python
       def change_request_facts(self, number: int) -> tuple[dict[str, Any] | None, str]:
           mr, statuses, approvals, problem = self._merge_request_reads(number)
           if problem:
               return None, problem
           return GitLabFacts().change_request(mr, statuses, approvals), ""

       def change_request_with_thread(self, number: int) -> tuple[dict[str, Any] | None, str]:
           mr, statuses, approvals, problem = self._merge_request_reads(number)
           if problem:
               return None, problem
           notes_path = f"projects/{self._project()}/merge_requests/{number}/notes?sort=asc"
           notes, problem = self._pages(notes_path)
           if problem:
               return None, problem
           source: dict[str, Any] = {}
           source_id = mr.get("source_project_id")
           if source_id != mr.get("target_project_id"):
               found, problem = self._object(f"projects/{source_id}")
               if found is None:
                   return None, problem
               source = found
           return GitLabFacts().threaded(mr, statuses, approvals, notes, source), ""

       def _object(self, path: str) -> tuple[dict[str, Any] | None, str]:
           """The one JSON object the forge answers `path` with, and a problem."""
           value, problem = self.transport.survey([path], cwd=self.root)
           if problem:
               return None, problem
           if not isinstance(value, dict):
               return None, f"GitLab answered {path} with something other than an object"
           return value, ""

       def _merge_request_reads(
           self, number: int
       ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], str]:
           """A merge request, its head's commit statuses and its approvals, and a problem."""
           project = self._project()
           mr, problem = self._object(f"projects/{project}/merge_requests/{number}")
           if mr is None:
               return {}, [], {}, problem
           sha = str(mr.get("sha") or "")
           statuses_path = f"projects/{project}/repository/commits/{sha}/statuses"
           statuses, problem = self._pages(statuses_path)
           if problem:
               return {}, [], {}, problem
           approvals_path = f"projects/{project}/merge_requests/{number}/approvals"
           approvals, problem = self._object(approvals_path)
           if approvals is None:
               return {}, [], {}, problem
           return mr, statuses, approvals, ""
   ```
   Replace `get_check_results` in place, on the corrected route:
   ```python
       def get_check_results(self, head_sha: str) -> tuple[tuple[CheckResult, ...], str]:
           path = f"projects/{self._project()}/repository/commits/{head_sha}/statuses"
           statuses, problem = self._pages(path)
           if problem:
               return (), problem
           facts = GitLabFacts()
           return tuple(facts.check_result(status, head_sha) for status in statuses), ""
   ```
6. `test/test_forge_adapters.py` follows the reshape (it drives adapters through a
   `ScriptedTransport` that has only `survey`, so the GitHub read, now through `_read` and
   `transport.json`, moves to `fake_gh` in the new test file):
   - in `test_github_reads_and_writes_every_neutral_verb`, delete the four statements that start
     at `checks = {"check_runs": [{"name": "CI", "conclusion": "success"}, "ignored"]}` and end at
     the `"check_runs field is not a list"` assertion (integration lines 117-125);
   - in `test_gitlab_adapter_covers_list_and_mutation_paths`, the block from
     `statuses = [{"name": "CI", "status": "success"}]` through the
     `get_check_results("abc") == ((), "down")` assertion (integration lines 228-237) becomes:
     ```python
         statuses = [{"name": "CI", "status": "success"}]
         checks = _gitlab(ScriptedTransport((statuses, ""))).get_check_results("abc")
         assert checks == ((CheckResult("CI", "abc", "success"),), "")
         odd = _gitlab(ScriptedTransport(({}, ""))).get_check_results("abc")
         path = "projects//repository/commits/abc/statuses"
         assert odd == ((), f"GitLab answered {path} with something other than a list")
         assert _gitlab(ScriptedTransport(([], "down"))).get_check_results("abc") == ((), "down")
     ```
   - in `test_forgejo_adapter_covers_list_and_mutation_paths`, the block from
     `statuses = [{"context": "CI", "state": "success"}]` through the
     `get_check_results("abc") == ((), "down")` assertion (integration lines 336-344) becomes:
     ```python
         statuses = [{"context": "CI", "state": "success"}]
         checks = _forgejo(ScriptedTransport((statuses, ""))).get_check_results("abc")
         assert checks == ((CheckResult("CI", "abc", "success"),), "")
         odd = _forgejo(ScriptedTransport(({}, ""))).get_check_results("abc")
         path = "repos//commits/abc/statuses"
         assert odd == ((), f"Forgejo answered {path} with something other than a list")
         assert _forgejo(ScriptedTransport(([], "down"))).get_check_results("abc") == ((), "down")
     ```
   - the file's `from vibey_gh.forge import ForgeReview` becomes
     `from vibey_gh.forge import CheckResult, ForgeReview`.
7. Nothing else changes: no consumer (`merge_train.py`, `pr_automation.py`) moves in this lane.

## Where to change
Every path in this spec is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package
`vibey_gh`) unless it starts with `src/` or `.github/`; the check block starts with
`cd src/vibey_tools/gh`. The adapter modules and `test/test_forge_adapters.py` were edited by the
four foundation lanes before this one, so their line numbers have moved: find each anchor by the
method or assertion text given here (the integration branch line, at `4317cff6`, is given for
reference), and read the file's tail before appending.

Four production files, because each verb is declared on the protocol and all three adapters must
implement it in the same change:
- `vibey_gh/interfaces/forge_adapter_interface.py`: the import, `get_check_results`, the two new
  declarations.
- `vibey_gh/forge_github.py`: the import, the field lists after `GH_DEFAULT_HOST`, the three
  methods appended, `get_check_results` replaced.
- `vibey_gh/forge_forgejo.py`: the imports, the four methods appended, `get_check_results`
  replaced.
- `vibey_gh/forge_gitlab.py`: the imports, the four methods appended, `get_check_results`
  replaced.
- Tests: `test/test_forge_change_request_reads.py` (new) and `test/test_forge_adapters.py` (the
  edits in behaviour 6).
- Only if `test/test_patching_ratchet.py` exists when you start (another storm lane adds the
  tenant's patching ratchet) and it fails on a test file this lane created: record that file in
  `test/patching_baseline.json` with its true counts, all zero (this lane adds no patch). Never
  raise a count. If the ratchet does not exist, skip this.

## Acceptance criteria
- [ ] For each of `change_request_facts`, `change_request_with_thread` and `get_check_results`, a
      `fake_gh` test pins the exact GitHub argv and cwd (`test_github_facts_ask_the_merge_trains_fields`,
      `test_github_thread_asks_pr_automations_fields`,
      `test_github_check_results_count_only_finished_checks`).
- [ ] `test_the_field_lists_are_todays_byte_for_byte` passes.
- [ ] `test_every_read_passes_a_problem_through_with_nothing_read` passes for every forge × verb.
- [ ] `grep -n '"projects/{self._project()}/commits/' vibey_gh/forge_gitlab.py` finds nothing
      (the wrong GitLab route is gone).
- [ ] `python -m pytest -q` (run in `src/vibey_tools/gh`) passes with 100% line and branch
      coverage of `vibey_gh`; black, isort, mypy, ruff check and ruff format --check are clean.

## Tests to write first (TDD)
New file `test/test_forge_change_request_reads.py` (provenance header first). GitHub tests use
the conftest `fake_gh` fixture; Forgejo and GitLab tests use `RoutedTransport`. Imports:
```python
from __future__ import annotations

import json

import pytest
from forge_doubles import RoutedTransport

from vibey_gh.forge import CheckResult
from vibey_gh.forge_forgejo import ForgejoForge
from vibey_gh.forge_forgejo_facts import ForgejoFacts
from vibey_gh.forge_github import (
    CHANGE_REQUEST_FACT_FIELDS,
    THREADED_CHANGE_REQUEST_FIELDS,
    GitHubForge,
)
from vibey_gh.forge_gitlab import GitLabForge
from vibey_gh.forge_gitlab_facts import GitLabFacts
```
Fixtures (module constants and two route builders):
```python
PULL = {
    "number": 7,
    "title": "Add a thing",
    "body": "Body",
    "state": "open",
    "mergeable": True,
    "user": {"login": "ada"},
    "head": {
        "ref": "topic",
        "sha": "abc",
        "repo_id": 1,
        "repo": {"name": "r", "owner": {"login": "o"}},
    },
    "base": {"ref": "develop", "repo_id": 1},
    "changed_files": 1,
}
STATUSES = [{"context": "CI (pull_request)", "state": "success"}]
REVIEWS = [{"user": {"login": "bo"}, "state": "APPROVED"}]
COMMENTS = [{"id": 1, "body": "hi", "user": {"login": "bo"}}]
MR = {
    "iid": 7,
    "title": "Add a thing",
    "description": "Body",
    "state": "opened",
    "has_conflicts": False,
    "author": {"username": "ada"},
    "sha": "abc",
    "source_branch": "topic",
    "target_branch": "develop",
    "source_project_id": 2,
    "target_project_id": 1,
}
GITLAB_STATUSES = [{"name": "CI", "status": "success"}]
APPROVALS = {"approved": True}
NOTES = [{"id": 1, "body": "hi", "author": {"username": "bo"}, "system": False}]
SOURCE = {"path": "fork-r", "namespace": {"full_path": "fork-o"}}
GITLAB_STATUSES_ROUTE = "projects/o%2Fr/repository/commits/abc/statuses?page=1&per_page=100"
GITLAB_NOTES_ROUTE = "projects/o%2Fr/merge_requests/7/notes?sort=asc&page=1&per_page=100"


def _forgejo_routes() -> dict[str, tuple[object, str]]:
    return {
        "repos/o/r/pulls/7": (PULL, ""),
        "repos/o/r/commits/abc/statuses?page=1&limit=50": (STATUSES, ""),
        "repos/o/r/commits/abc/statuses?page=2&limit=50": ([], ""),
        "repos/o/r/pulls/7/reviews?page=1&limit=50": (REVIEWS, ""),
        "repos/o/r/pulls/7/reviews?page=2&limit=50": ([], ""),
        "repos/o/r/issues/7/comments": (COMMENTS, ""),
    }


def _gitlab_routes() -> dict[str, tuple[object, str]]:
    return {
        "projects/o%2Fr/merge_requests/7": (MR, ""),
        GITLAB_STATUSES_ROUTE: (GITLAB_STATUSES, ""),
        "projects/o%2Fr/merge_requests/7/approvals": (APPROVALS, ""),
        GITLAB_NOTES_ROUTE: (NOTES, ""),
        "projects/2": (SOURCE, ""),
    }
```
Tests:
- `test_the_field_lists_are_todays_byte_for_byte`: `CHANGE_REQUEST_FACT_FIELDS ==
  ",".join(expected_facts)` and `THREADED_CHANGE_REQUEST_FIELDS == ",".join(expected_thread)`,
  where the two expected tuples are written out in the test, one name per line, in exactly the
  orders of behaviour 1 (so the test pins the literal order independently of the module).
- `test_github_facts_ask_the_merge_trains_fields(fake_gh, tmp_path)`:
  ```python
      fields = CHANGE_REQUEST_FACT_FIELDS
      fake_gh.script(
          {
              f"pr view 7 --json {fields}": {"out": '{"number": 7, "title": "T"}'},
              f"pr view 8 --json {fields}": {"out": "[]"},
              f"pr view 9 --json {fields}": {"err": "no pull request 9\n", "code": 1},
              f"pr view 10 --json {fields}": {"out": ""},
              f"pr view 7 --repo o/r --json {fields}": {"out": '{"number": 7}'},
          }
      )
      forge = GitHubForge(root=tmp_path)
      assert forge.change_request_facts(7) == ({"number": 7, "title": "T"}, "")
      argv = ["pr", "view", "7", "--json", fields]
      expected = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == expected
      not_object = "`gh pr view` returned JSON that is not an object"
      assert forge.change_request_facts(8) == (None, not_object)
      assert forge.change_request_facts(10) == (None, not_object)
      refused = f"gh pr view 9 --json {fields}: no pull request 9"
      assert forge.change_request_facts(9) == (None, refused)
      assert forge.for_repository("o/r").change_request_facts(7) == ({"number": 7}, "")
      bound = ["pr", "view", "7", "--repo", "o/r", "--json", fields]
      assert fake_gh.invocations()[-1]["argv"] == bound
  ```
- `test_github_thread_asks_pr_automations_fields(fake_gh, tmp_path)`: the same shape with
  `fields = THREADED_CHANGE_REQUEST_FIELDS` and `change_request_with_thread`: an object answer
  (`'{"number": 7, "comments": []}'`) comes back unchanged with the unbound argv
  `["pr", "view", "7", "--json", fields]` run in `str(tmp_path.resolve())`; `"null"` answers
  `(None, "`gh pr view` returned JSON that is not an object")`; the bound adapter's argv is
  `["pr", "view", "7", "--repo", "o/r", "--json", fields]`.
- `test_github_check_results_count_only_finished_checks(fake_gh, tmp_path, monkeypatch)`:
  ```python
      monkeypatch.setenv("GH_REPO", "o/r")
      runs = {
          "check_runs": [
              {"name": "CI", "status": "completed", "conclusion": "success"},
              {"name": "Lint", "status": "in_progress", "conclusion": None},
              {"name": "Docs", "status": "completed", "conclusion": None},
              "not-a-run",
          ]
      }
      key = "api repos/o/r/commits/abc/check-runs"
      fake_gh.script({key: {"out": json.dumps(runs)}})
      forge = GitHubForge(root=tmp_path)
      expected = (
          CheckResult("CI", "abc", "success"),
          CheckResult("Lint", "abc", ""),
          CheckResult("Docs", "abc", ""),
      )
      assert forge.get_check_results("abc") == (expected, "")
      argv = ["api", "repos/o/r/commits/abc/check-runs"]
      invoked = [{"argv": argv, "cwd": str(tmp_path.resolve()), "stdin": None}]
      assert fake_gh.invocations() == invoked
      fake_gh.script({key: {"out": "[]"}})
      assert forge.get_check_results("abc") == ((), "Expected object for check-runs")
      fake_gh.script({key: {"out": '{"check_runs": {}}'}})
      assert forge.get_check_results("abc") == ((), "check_runs field is not a list")
  ```
- `test_forgejo_reads_route_to_pulls_statuses_reviews_and_comments(tmp_path)`: with
  `transport = RoutedTransport(_forgejo_routes())` and a Forgejo adapter bound to `"o/r"`:
  `change_request_facts(7) == (ForgejoFacts().change_request(PULL, STATUSES, REVIEWS), "")`;
  `change_request_with_thread(7) == (ForgejoFacts().threaded(PULL, STATUSES, REVIEWS, COMMENTS),
  "")`; `get_check_results("abc") == ((ForgejoFacts().check_result(STATUSES[0], "abc"),), "")`;
  and `transport.calls[:5]` is exactly `[("repos/o/r/pulls/7",),
  ("repos/o/r/commits/abc/statuses?page=1&limit=50",),
  ("repos/o/r/commits/abc/statuses?page=2&limit=50",),
  ("repos/o/r/pulls/7/reviews?page=1&limit=50",), ("repos/o/r/pulls/7/reviews?page=2&limit=50",)]`
  (bind the expected list to a local).
- `test_forgejo_reads_stop_at_the_first_problem(tmp_path, missing)`: parametrised over `missing`
  in `"repos/o/r/pulls/7"`, `"repos/o/r/commits/abc/statuses?page=1&limit=50"`,
  `"repos/o/r/pulls/7/reviews?page=1&limit=50"`, `"repos/o/r/issues/7/comments"`.
  The routes are `_forgejo_routes()` without `missing`;
  `change_request_with_thread(7) == (None, f"no route for {missing}")`, and, unless `missing` is
  the comments route, `change_request_facts(7)` answers the same.
- `test_gitlab_reads_use_the_repository_commits_statuses_route(tmp_path)`: with
  `transport = RoutedTransport(_gitlab_routes())` and a GitLab adapter bound to `"o/r"`:
  `change_request_facts(7) == (GitLabFacts().change_request(MR, GITLAB_STATUSES, APPROVALS), "")`;
  `change_request_with_thread(7) == (GitLabFacts().threaded(MR, GITLAB_STATUSES, APPROVALS,
  NOTES, SOURCE), "")` (the merge request is cross-repository, so `projects/2` is read);
  `get_check_results("abc") == ((GitLabFacts().check_result(GITLAB_STATUSES[0], "abc"),), "")`;
  `(GITLAB_STATUSES_ROUTE,) in transport.calls`; and
  `all("projects/o%2Fr/commits/" not in call[0] for call in transport.calls)`. Then, with
  `same = {**MR, "source_project_id": 1}` routed as `"projects/o%2Fr/merge_requests/7"`,
  `change_request_with_thread(7)` equals `(GitLabFacts().threaded(same, GITLAB_STATUSES,
  APPROVALS, NOTES, {}), "")` and no call's path is `"projects/2"`.
- `test_gitlab_reads_stop_at_the_first_problem(tmp_path, missing)`: parametrised over `missing`
  in `"projects/o%2Fr/merge_requests/7"`, `GITLAB_STATUSES_ROUTE`,
  `"projects/o%2Fr/merge_requests/7/approvals"`, `GITLAB_NOTES_ROUTE`, `"projects/2"`. The routes
  are `_gitlab_routes()` without `missing`; `change_request_with_thread(7) == (None,
  f"no route for {missing}")`.
- `test_answers_that_are_not_objects_are_problems(tmp_path)`:
  - Forgejo, `"repos/o/r/pulls/7"` routed to `([], "")`: `change_request_facts(7) == (None,
    "Forgejo answered repos/o/r/pulls/7 with something other than an object")`;
  - GitLab, `"projects/o%2Fr/merge_requests/7/approvals"` routed to `([], "")`:
    `change_request_facts(7) == (None, "GitLab answered
    projects/o%2Fr/merge_requests/7/approvals with something other than an object")`;
  - GitLab, `"projects/2"` routed to `([], "")`: `change_request_with_thread(7) == (None,
    "GitLab answered projects/2 with something other than an object")`.
  Build each expected sentence from a path local with an f-string.
- `test_every_read_passes_a_problem_through_with_nothing_read`:
  ```python
  @pytest.mark.parametrize("kind", ["github", "forgejo", "gitlab"])
  @pytest.mark.parametrize(
      ("verb", "argument", "empty"),
      [
          ("change_request_facts", 7, None),
          ("change_request_with_thread", 7, None),
          ("get_check_results", "abc", ()),
      ],
  )
  def test_every_read_passes_a_problem_through_with_nothing_read(
      fake_gh, tmp_path, kind, verb, argument, empty
  ):
      forges = {
          "github": GitHubForge(root=tmp_path, repository="o/r"),
          "forgejo": ForgejoForge(root=tmp_path, repository="o/r", transport=RoutedTransport()),
          "gitlab": GitLabForge(root=tmp_path, repository="o/r", transport=RoutedTransport()),
      }
      value, problem = getattr(forges[kind], verb)(argument)
      assert value == empty
      if kind == "github":
          assert problem.endswith(": no scripted answer")
      else:
          assert problem.startswith("no route for ")
  ```
  (`fake_gh` has no answers here, so every `gh` call exits 3 with `no scripted answer`.)

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_change_request_reads.py test/test_forge_adapters.py test/test_forge_facts.py test/test_forge_foundation.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the files named under "Where to change"
git status --short   # the one new file, test/test_forge_change_request_reads.py, and nothing else new
```
If black or isort reports a file you touched, run `python -m black --line-length 100 <file>` and
`isort <file>` on that file only, then run the whole block again.

## Out of scope
- `change_request_text`, `change_request_comment_bodies`, `changed_paths`: child lane 3
  (`split-333-3-change-request-text`).
- `vibey_gh/forge_forgejo_facts.py`, `vibey_gh/forge_gitlab_facts.py` and their interfaces
  (child lane 1 owns them; use them as they are), `vibey_gh/forge.py`.
- `vibey_gh/merge_train.py`, `vibey_gh/pr_automation.py` and every other consumer: later forge
  lanes.
- Listings, writes, issues, releases and branch rules: later forge lanes.
- `test/conftest.py`, `test/forge_doubles.py`.
- The repository's `[platform] kind = "github"` declaration in the root `.vibey-gh.toml`
  (lines 18-19): never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  when done.

## Conventions this lane relies on (everything needed is here)
- **Shared rules for this lane and the next** (from the parent's plan):
  - Every verb answers `(value, problem)`, never raises, and returns the empty value with a
    one-sentence problem when it could not ask.
  - **Forgejo is the default adapter (8.b): implement and test it first.**
  - GitHub argv is copied byte for byte from the named call site. `self._scoped(head, tail)`
    inserts `--repo <bound name>` only when the adapter is bound.
  - `{R}` in a GitHub API path is `repository_name()`'s answer. Forgejo `{R}` =
    `quote(repository, safe="/")` (`self._repository()`), GitLab `{P}` =
    `quote(repository, safe="")` (`self._project()`).
  - GitHub tests use the conftest `fake_gh` fixture. Forgejo/GitLab tests use `RoutedTransport`
    from `test/forge_doubles.py`.
  - Append new methods to the end of each adapter module (the class is the module's last
    statement). Do not rewrite whole files.
- **The adapter contract (vibey-gh ADR 0001).** `problem` is `""` exactly when the forge
  answered; otherwise `value` is the empty value for its type (`None`, `()`, `frozenset()`,
  `False`, `[]`, `{}`) and `problem` is one sentence. No verb raises for a failed call, a missing
  client, a non-2xx status or unreadable output (`interfaces/forge_adapter_interface.py:9-16`).
- **What the foundation lanes built, and this lane calls:**
  - `GitHubForge.repository_name() -> tuple[str, str]`: the bound name, else `$GH_REPO`, else
    `gh repo view --json nameWithOwner`.
  - `GitHubForge._scoped(head: list[str], tail: list[str]) -> list[str]`: `head`, then
    `["--repo", self.repository]` only when bound, then `tail`.
  - `GitHubForge._read(args, *, stdin=None) -> tuple[Any, str]`: the decoded JSON, or `None` and
    a problem: `"gh <args joined>: <stderr>"` for a non-zero exit, ``"`gh <two words>` returned
    output that is not JSON"``, or ``"the GitHub CLI (`gh`) is not installed"``. Empty output
    decodes to `None`.
  - `ForgejoForge._pages(path, *, most=None)` / `GitLabForge._pages(...) -> tuple[list[dict[str,
    Any]], str]`: every dict of a paged listing. Forgejo appends `?`/`&` + `page=N&limit=50` and
    stops at an empty page; GitLab appends `page=N&per_page=100` and stops at a page shorter than
    100. A non-list page answers `([], "<Forgejo|GitLab> answered <path> with something other
    than a list")`; a transport problem passes through as `([], problem)`.
  - `ForgejoFacts().change_request(pull, statuses, reviews)`, `.threaded(pull, statuses, reviews,
    comments)`, `.check_result(status, sha) -> CheckResult`; `GitLabFacts().change_request(mr,
    statuses, approvals)`, `.threaded(mr, statuses, approvals, notes, source_project)`,
    `.check_result(status, sha) -> CheckResult` (child lane 1). They are pure; `threaded` drops
    GitLab system notes itself.
- **Neutral mapping schema.** The facts verbs return mappings keyed by the historical `gh`
  spellings (`vibey_gh.forge.CHANGE_REQUEST_FACT_KEYS`, and `THREADED_CHANGE_REQUEST_FACT_KEYS`
  for the thread), which `merge_train.judge` and `pr_automation.evaluate` already read. GitHub's
  answer is `gh`'s own object, returned unchanged.
- **`fake_gh`** (fixture at `test/conftest.py:151-156`; class `FakeGh` at
  `test/conftest.py:87-144`) puts a real `gh` executable first on `PATH` (through
  `monkeypatch.setenv`, a declared seam). `fake_gh.script({"<argv joined by single spaces>":
  {"out": "...", "err": "...", "code": 0}})` replaces every scripted answer; an argv with no answer
  exits 3 and prints `no scripted answer` on stderr. `fake_gh.invocations()` lists
  `{"argv": [...], "cwd": "<directory gh ran in>", "stdin": None}` per call, in order (compare
  `cwd` with `str(tmp_path.resolve())`). It does not set `GH_REPO`: every test whose argv holds a
  repository name sets or deletes `GH_REPO` itself.
- **`RoutedTransport`** (`test/forge_doubles.py`; `from forge_doubles import RoutedTransport`)
  answers keyed by `"<path>"` for a GET and `"<path> <METHOD>"` otherwise, returns the same routed
  answer every time, records every `args` tuple in `.calls`, and answers an unrouted request with
  `([], "no route for <key>")`.
- **Tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
  (`pyproject.toml:64-71`). Focused runs need `--no-cov`; the whole-suite run must pass without
  it. Substitute only at a declared seam: no `monkeypatch.setattr` of an import or of a module or
  class attribute, no `mock.patch`, no `MagicMock`/`AsyncMock` (sub-doctrine 9.b). Never touch
  `test/conftest.py`.
- **Working in the big files.** Each adapter class is the last statement of its module, so a new
  method is added at the end of the class: use `edit_file` with the class's current last method
  (read the tail with `tail -n 40 <file>`) as `old_string`, and that same method followed by the
  new methods (indented four spaces) as `new_string`. Replace an existing method with `edit_file`
  on that method alone. Read only the slices you need (`grep -n "def get_check_results"
  vibey_gh/forge_gitlab.py`, then `sed -n` around it). Never rewrite a whole module and never use
  `write_file` on an existing file.
- **The formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
  (profile black, `combine_as_imports`; CI job `tools-lint`, `.github/workflows/ci.yml:699-705`)
  and the root `ruff format --check .` (line length 100). They disagree on some wraps, so write
  lines neither wants to rewrap:
  - keep every line at or under 100 columns, and at or under 95 for anything with nested calls;
  - bind a long comparison, expected value or path to a local first;
  - never use implicit string concatenation; use one literal, or an f-string built from locals;
  - never put a string literal inside an f-string's braces; bind it to a local first;
  - write multi-line calls and collections with one element per line and a trailing comma;
  - never use backslash continuations.

  If the two formatters fight over a line, restructure the line. Never alternate between them.
- **Platforms (8.h).** The suite must pass on Arch Linux and macOS: no GNU-only tools in tests,
  and compare paths through `Path.resolve()`.

**Depends on:** split-333-1-facts-translators
- split-333-1-facts-translators: `ForgejoFacts`, `GitLabFacts` and the fact-key constants, and
  (through the four foundation lanes it depends on) `_pages`, `_read`, `_scoped`,
  `repository_name`, `RoutedTransport` and the `CheckResult`-free adapters this lane reshapes.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
