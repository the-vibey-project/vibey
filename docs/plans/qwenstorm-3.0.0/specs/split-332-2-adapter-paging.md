<!-- split of #332: child 2 of 4; audit: issue-audit/updates/332.md -->

## Title
fix(gh): the Forgejo and GitLab adapters page every listing and read Forgejo's real field names

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge
(`src/vibey_tools/gh/docs/doctrines.md:138`), and vibey-gh's own default is
`[platform] kind = "forgejo"` (`vibey_gh/config.py:288`). The clean-repo survey already asks the
Forgejo adapter for open heads and releases (`vibey_gh/tidy.py:130`, `:151`), and that adapter
reads the wrong fields and never pages:

- `ForgejoForge.open_change_request_heads` reads `head.branch` (`vibey_gh/forge_forgejo.py:72`),
  but Forgejo's field is `head.ref`, so the survey never excludes an open pull request's head.
- `releases` never marks a draft (`forge_forgejo.py:85`).
- `get_change_request` and `get_issue` read the global `id` instead of the per-repository
  `number` (`forge_forgejo.py:102`, `:123`), and `get_change_request` reads `head.branch`
  (`:103`).
- `get_issue_thread` falls back to `repos/{R}/pulls/{n}/comments` (`forge_forgejo.py:136-139`),
  a route Forgejo does not have; pull-request comments live under `issues/{n}/comments`.
- No listing pages. Forgejo answers at most `[api] MAX_RESPONSE_ITEMS` (50 by default) per page
  whatever `limit` asks (`forge_forgejo.py:66`, `:79`), and GitLab caps `per_page` at 100
  (`vibey_gh/forge_gitlab.py:66`, `:79`) while tidy asks for 200 heads.

Every later forge lane builds on the paging helper, the 404 test and the routed test double this
lane adds, and on the adapter knowing its host (the selector knows it at
`vibey_gh/forge_selector.py:75`, `:84` and drops it).

## Required behaviour
1. `ForgejoForge` (`vibey_gh/forge_forgejo.py:26-32`) gains three dataclass fields after
   `transport`, with `host` the **last** field:
   ```python
   page_size: int = 50
   max_pages: int = 100
   host: str = "forgejo.local"
   ```
   `GitLabForge` (`vibey_gh/forge_gitlab.py:26-32`) gains:
   ```python
   page_size: int = 100
   max_pages: int = 100
   host: str = "gitlab.com"
   ```
   The page size and page cap are fields, not literals, because a forge's page limit is the
   instance's own setting (sub-doctrine 12.c: a value that could be configured must be).
2. `ForgeSelector._gitlab` (`vibey_gh/forge_selector.py:80`) and `ForgeSelector._forgejo`
   (`:89`) pass `host=host` to the adapter they build, written as a multi-line call with one
   argument per line and a trailing comma:
   ```python
           return ForgejoForge(
               root=cfg.root,
               repository=_repository(cfg),
               transport=transport,
               host=host,
           )
   ```
   (the same shape with `GitLabForge`). `ForgeSelector().select(GhConfig(root=tmp))` still equals
   `ForgejoForge(root=tmp, transport=ForgejoTransport(host="forgejo.local", token=""))`, because
   every new field keeps its default.
3. `ForgejoForge._pages`, added at the end of the class:
   ```python
       def _pages(self, path: str, *, most: int | None = None) -> tuple[list[dict[str, Any]], str]:
           """Every object of a paged listing (the first `most` of them), and a problem.

           Forgejo caps `limit` at its own `[api] MAX_RESPONSE_ITEMS`, so a page shorter than
           `page_size` may not be the last one: only an empty page ends the listing.
           """
           separator = "&" if "?" in path else "?"
           items: list[dict[str, Any]] = []
           for page in range(1, self.max_pages + 1):
               paged = f"{path}{separator}page={page}&limit={self.page_size}"
               value, problem = self.transport.survey([paged], cwd=self.root)
               if problem:
                   return [], problem
               if not isinstance(value, list):
                   return [], f"Forgejo answered {path} with something other than a list"
               if not value:
                   return items, ""
               items.extend(item for item in value if isinstance(item, dict))
               if most is not None and len(items) >= most:
                   return items[:most], ""
           incomplete = f"Forgejo listed more than {self.max_pages} pages of {path}"
           return [], f"{incomplete}; the listing is incomplete"
   ```
   `path` in both problem sentences is the argument as given, without the page query.
4. `GitLabForge._pages`, added at the end of the class: the same code with `per_page` in place of
   `limit`, `GitLab` in place of `Forgejo` in both sentences, and a short page ending the listing.
   Its loop body after the `isinstance` check is:
   ```python
               items.extend(item for item in value if isinstance(item, dict))
               if most is not None and len(items) >= most:
                   return items[:most], ""
               if len(value) < self.page_size:
                   return items, ""
   ```
   (no separate empty-page test: an empty page is a short page). Its docstring says GitLab caps
   `per_page` at 100 and a page shorter than `page_size` raw items is the last one.
5. Both adapters gain, at the end of the class:
   ```python
       def _absent(self, problem: str) -> bool:
           """Whether `problem` is the transport's 404 sentence: the forge says it is not there."""
           return problem.startswith("Forgejo API error 404:")
   ```
   (GitLab: `"GitLab API error 404:"`). The transports word a 404 as
   `"Forgejo API error 404: Not Found"`, so this is true exactly for that sentence.
6. Forgejo fixes, each edited in place:
   - `open_change_request_heads` (`forge_forgejo.py:63-74`): `pulls, problem =
     self._pages(f"repos/{self._repository()}/pulls?state=open", most=limit)`, and the head is
     `pull.get("head", {}).get("ref", "")` (was `"branch"`). Keep only `str` heads, as today.
   - `releases` (`:76-90`): `rows, problem = self._pages(f"repos/{self._repository()}/releases",
     most=limit)`, and `draft=bool(row.get("draft"))` (was `False`).
   - `get_change_request` (`:92-111`): `number=int(val.get("number", 0))` (was `"id"`) and
     `head_ref=str(val.get("head", {}).get("ref", ""))` (was `"branch"`).
   - `get_issue` (`:113-129`): `number=int(val.get("number", 0))` (was `"id"`).
   - `get_issue_thread` (`:131-156`): reads only `comments, problem = self._comments(number)`; a
     problem answers `((), problem)`. The `pulls/{number}/comments` fallback (`:136-139`) and the
     `"Comments field is not a list"` branch go (`_comments` reports a non-list answer).
     **Issue comments are ONE GET, never `_pages`:** Forgejo's
     `GET /repos/{owner}/{repo}/issues/{index}/comments` declares only `since` and `before` (the
     Forgejo API 16.0.0-dev swagger at codeberg.org); it ignores `page`/`limit` and answers every
     comment at once, so `_pages`, which stops only at an empty page, would re-read the same
     comments until its 100-page cap and return them 100 times. Add this private method to
     `ForgejoForge`, right after `_pages`, and use it here (split-333-2 and split-333-3 reuse it):
     ```python
         def _comments(self, number: int) -> tuple[list[dict[str, Any]], str]:
             """An issue's comments, in ONE request: Forgejo's issues/{index}/comments takes no
             page or limit and answers every comment at once (see get_issue_thread)."""
             path = f"repos/{self._repository()}/issues/{number}/comments"
             value, problem = self.transport.survey([path], cwd=self.root)
             if problem:
                 return [], problem
             if not isinstance(value, list):
                 return [], f"Forgejo answered {path} with something other than a list"
             return [item for item in value if isinstance(item, dict)], ""
     ```
     A test routes `repos/o/r/issues/7/comments` to a two-comment list and asserts that
     `get_issue_thread(7)` answers exactly those two comments and that the transport was asked
     for that path exactly once; another routes it to a dict and asserts the "something other
     than a list" problem. Each comment's
     author is `user.login`, falling back to `user.username`, else `""`:
     ```python
             thread: list[ForgeComment] = []
             for comment in comments:
                 user = comment.get("user") or {}
                 author = str(user.get("login") or user.get("username") or "")
                 thread.append(
                     ForgeComment(
                         id=str(comment.get("id", "")),
                         author=author,
                         body=str(comment.get("body", "")),
                     )
                 )
             return tuple(thread), ""
     ```
7. GitLab fixes, each edited in place: `open_change_request_heads` (`forge_gitlab.py:63-74`) reads
   `self._pages(f"projects/{self._project()}/merge_requests?state=opened", most=limit)` and
   `releases` (`:76-90`) reads `self._pages(f"projects/{self._project()}/releases", most=limit)`.
   Bind `project = self._project()` first if a line would pass 95 columns.
8. New `test/forge_doubles.py` holds `RoutedTransport`, exactly:
   ```python
   """Test doubles for the forge adapters, shared by every forge test module.

   Each stands in at a seam the production code declares (an adapter's `transport` field), so
   no test patches an import to use one (sub-doctrine 9.b). Import with
   `from forge_doubles import RoutedTransport`: pytest puts `test/` on `sys.path`.
   """

   from __future__ import annotations

   from collections.abc import Mapping, Sequence
   from typing import Any


   class RoutedTransport:
       """A forge transport that answers by route and records every request it is sent.

       A route is the API path for a GET and `"<path> <METHOD>"` for anything else, so a
       branch deletion is routed as `"repos/o/r/branches/x DELETE"`. Every request's `args`
       tuple is appended to `calls`, in order. A request with no route answers
       `([], "no route for <route>")`, so a test cannot pass by reaching a call it never named.
       """

       executable = "http (routed)"

       def __init__(self, routes: Mapping[str, tuple[Any, str]] | None = None) -> None:
           self.routes = dict(routes or {})
           self.calls: list[tuple[str, ...]] = []

       def survey(
           self,
           args: Sequence[str],
           *,
           cwd: Any = None,
           stdin: str | None = None,
       ) -> tuple[Any, str]:
           del cwd, stdin
           self.calls.append(tuple(args))
           path = args[0] if args else ""
           method = args[1].upper() if len(args) > 1 else "GET"
           route = path if method == "GET" else f"{path} {method}"
           return self.routes.get(route, ([], f"no route for {route}"))
   ```
   (the provenance header line goes above the docstring). A routed answer is returned every time
   it is asked for; nothing is consumed.
9. Nothing else changes. `list_artifacts`, `get_reviews`, `get_check_results`, the mutations and
   the GitHub adapter are untouched. `test/test_forge_github.py`, `test/test_tidy.py` and
   `test/test_platform.py` pass unmodified.

## Where to change
Every path in this spec is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package
`vibey_gh`) unless it starts with `src/` or `.github/`; the check block starts with
`cd src/vibey_tools/gh`. Line anchors are those of the storm integration branch at `4317cff6`;
child lane 1 (`split-332-1-transport-seams`) changed only the transports, `forge.py`, the
interfaces and the tests, so every anchor in the adapters and the selector still holds (test-file
anchors are handled where they are named).

Three production files, because the host binding in the selector and the twin paging plumbing
of the two HTTP adapters are one behaviour that every later lane uses on both forges:
- `vibey_gh/forge_forgejo.py`: fields (lines 30-32), the five fixes (lines 63-156), and
  `_pages` / `_absent` appended after `_repository` (lines 269-270, the class's last method).
- `vibey_gh/forge_gitlab.py`: fields (lines 30-32), the two fixes (lines 63-90), and `_pages` /
  `_absent` appended after `_project` (lines 284-285, the class's last method).
- `vibey_gh/forge_selector.py:80` and `:89`: pass `host=host`.
- `test/forge_doubles.py` (new): `RoutedTransport`.
- `test/test_forge_foundation.py`: new imports in the top import block, new tests appended.
- `test/test_forge_adapters.py`: the Forgejo fixtures in
  `test_forgejo_adapter_covers_list_and_mutation_paths` (integration lines 286-291, 304-311, 317,
  322-333; child lane 1 added `import dataclasses` at the top, so each is one line lower now),
  as listed under the tests below.
- Only if `test/test_patching_ratchet.py` exists when you start (another storm lane adds the
  tenant's patching ratchet) and it fails on a test file this lane created: record that file in
  `test/patching_baseline.json` with its true counts, all zero (this lane adds no patch). Never
  raise a count. If the ratchet does not exist, skip this.

No new production class is added, so no new interface is needed. Every file you create starts
with the provenance header line, copied byte for byte from `vibey_gh/forge.py:1`:
`# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`

## Acceptance criteria
- [ ] `python -m pytest -q` (run in `src/vibey_tools/gh`) passes with 100% line and branch
      coverage of `vibey_gh`.
- [ ] `test/test_forge_github.py`, `test/test_tidy.py` and `test/test_platform.py` pass and
      `git diff --stat` shows none of them.
- [ ] `grep -n 'get("branch"' vibey_gh/forge_forgejo.py` shows only `get_protected_refs`
      (`b.get("branch", "")`), never a pull's head.
- [ ] `grep -n 'state=open&limit=\|releases?limit=\|state=opened&per_page=\|releases?per_page=' vibey_gh/forge_forgejo.py vibey_gh/forge_gitlab.py`
      finds nothing (heads and releases page through `_pages`; `list_artifacts` keeps its own
      `page`/`limit` query and is not this lane's).
- [ ] Every test named below passes.
- [ ] black, isort, mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
Forgejo and GitLab tests substitute only at the adapter's `transport` field, with
`RoutedTransport`. Never patch an import or a module attribute.

**`test/test_forge_foundation.py`.** Add these imports to the top import block (keep isort order;
`forge_doubles` is sorted as a third-party module, directly after `import pytest`):
```python
from forge_doubles import RoutedTransport

from vibey_gh.config import GhConfig, PlatformConfig
from vibey_gh.forge import ForgeKind, ForgeRelease, NotSupported
from vibey_gh.forge_forgejo import ForgejoForge
from vibey_gh.forge_gitlab import GitLabForge
from vibey_gh.forge_selector import ForgeSelector
from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface
```
(the `vibey_gh.forge` line replaces the existing one). Then append:
```python
def test_routed_transport_answers_by_route_and_records_every_request():
    transport = RoutedTransport({"a": ([1], ""), "a DELETE": ({}, "")})
    assert isinstance(transport, ForgeTransportInterface)
    assert transport.survey(["a"]) == ([1], "")
    assert transport.survey(["a", "delete", ""]) == ({}, "")
    assert transport.survey(["b", "POST", "{}"]) == ([], "no route for b POST")
    assert transport.calls == [("a",), ("a", "delete", ""), ("b", "POST", "{}")]


def test_forgejo_pages_until_an_empty_page_and_reports_an_endless_listing(tmp_path):
    base = "repos/o/r/pulls?state=open"
    routes = {
        f"{base}&page=1&limit=2": ([{"n": 1}, "not-a-dict"], ""),
        f"{base}&page=2&limit=2": ([{"n": 2}], ""),
        f"{base}&page=3&limit=2": ([], ""),
    }
    transport = RoutedTransport(routes)
    forge = ForgejoForge(root=tmp_path, repository="o/r", transport=transport, page_size=2)
    assert forge._pages(base) == ([{"n": 1}, {"n": 2}], "")
    assert len(transport.calls) == 3
    pages = {f"{base}&page={n}&limit=2": ([{"n": n}], "") for n in (1, 2, 3)}
    endless = RoutedTransport(pages)
    capped = ForgejoForge(root=tmp_path, transport=endless, page_size=2, max_pages=3)
    expected = f"Forgejo listed more than 3 pages of {base}; the listing is incomplete"
    assert capped._pages(base) == ([], expected)


def test_gitlab_pages_until_a_short_page_and_reports_an_endless_listing(tmp_path):
    base = "projects/o%2Fr/merge_requests?state=opened"
    routes = {
        f"{base}&page=1&per_page=2": ([{"n": 1}, "not-a-dict"], ""),
        f"{base}&page=2&per_page=2": ([{"n": 2}], ""),
    }
    transport = RoutedTransport(routes)
    forge = GitLabForge(root=tmp_path, repository="o/r", transport=transport, page_size=2)
    assert forge._pages(base) == ([{"n": 1}, {"n": 2}], "")
    assert len(transport.calls) == 2
    pages = {f"{base}&page={n}&per_page=1": ([{"n": n}], "") for n in (1, 2, 3)}
    endless = RoutedTransport(pages)
    capped = GitLabForge(root=tmp_path, transport=endless, page_size=1, max_pages=3)
    expected = f"GitLab listed more than 3 pages of {base}; the listing is incomplete"
    assert capped._pages(base) == ([], expected)


def test_pages_stop_once_they_hold_the_most_asked_for(tmp_path):
    three = [{"n": 1}, {"n": 2}, {"n": 3}]
    forgejo_transport = RoutedTransport({"repos/o/r/releases?page=1&limit=50": (three, "")})
    forgejo = ForgejoForge(root=tmp_path, repository="o/r", transport=forgejo_transport)
    assert forgejo._pages("repos/o/r/releases", most=2) == ([{"n": 1}, {"n": 2}], "")
    assert len(forgejo_transport.calls) == 1
    gitlab_routes = {"projects/o%2Fr/releases?page=1&per_page=100": (three, "")}
    gitlab_transport = RoutedTransport(gitlab_routes)
    gitlab = GitLabForge(root=tmp_path, repository="o/r", transport=gitlab_transport)
    assert gitlab._pages("projects/o%2Fr/releases", most=2) == ([{"n": 1}, {"n": 2}], "")
    assert len(gitlab_transport.calls) == 1


@pytest.mark.parametrize(
    ("forge_type", "name", "path", "query"),
    [
        (ForgejoForge, "Forgejo", "repos/o/r/releases", "page=1&limit=50"),
        (GitLabForge, "GitLab", "projects/o%2Fr/releases", "page=1&per_page=100"),
    ],
)
def test_pages_report_a_page_that_is_not_a_list_and_pass_a_problem_through(
    tmp_path, forge_type, name, path, query
):
    key = f"{path}?{query}"
    odd = forge_type(root=tmp_path, transport=RoutedTransport({key: ({}, "")}))
    expected = f"{name} answered {path} with something other than a list"
    assert odd._pages(path) == ([], expected)
    down = forge_type(root=tmp_path, transport=RoutedTransport({key: ([], "down")}))
    assert down._pages(path) == ([], "down")


def test_absent_recognises_only_the_404_sentence(tmp_path):
    forgejo = ForgejoForge(root=tmp_path)
    gitlab = GitLabForge(root=tmp_path)
    assert forgejo._absent("Forgejo API error 404: Not Found")
    assert not forgejo._absent("Forgejo API error 401: Unauthorized")
    assert not forgejo._absent("GitLab API error 404: Not Found")
    assert not forgejo._absent("")
    assert gitlab._absent("GitLab API error 404: Not Found")
    assert not gitlab._absent("GitLab API error 500: Internal Server Error")
    assert not gitlab._absent("Forgejo API error 404: Not Found")


def test_forgejo_heads_read_head_ref_and_releases_read_draft(tmp_path):
    pulls = [{"head": {"ref": "topic"}}, {"head": {"ref": None}}, {"head": {"ref": "other"}}]
    rows = [{"tag_name": "v2", "name": "Two", "draft": True}, {"tag_name": "v1", "name": "One"}]
    routes = {
        "repos/o/r/pulls?state=open&page=1&limit=50": (pulls, ""),
        "repos/o/r/pulls?state=open&page=2&limit=50": ([], ""),
        "repos/o/r/releases?page=1&limit=50": (rows, ""),
        "repos/o/r/releases?page=2&limit=50": ([], ""),
    }
    forge = ForgejoForge(root=tmp_path, repository="o/r", transport=RoutedTransport(routes))
    assert forge.open_change_request_heads(limit=200) == (frozenset({"topic", "other"}), "")
    assert forge.open_change_request_heads(limit=1) == (frozenset({"topic"}), "")
    expected = (ForgeRelease("v2", "Two", True), ForgeRelease("v1", "One", False))
    assert forge.releases(limit=100) == (expected, "")


def test_gitlab_heads_and_releases_page_past_the_per_page_cap(tmp_path):
    heads = ([{"source_branch": "topic"}], "")
    rows = ([{"tag_name": "v1", "name": "One"}], "")
    routes = {
        "projects/o%2Fr/merge_requests?state=opened&page=1&per_page=100": heads,
        "projects/o%2Fr/releases?page=1&per_page=100": rows,
    }
    forge = GitLabForge(root=tmp_path, repository="o/r", transport=RoutedTransport(routes))
    assert forge.open_change_request_heads(limit=200) == (frozenset({"topic"}), "")
    assert forge.releases(limit=100) == ((ForgeRelease("v1", "One", False),), "")


def test_forgejo_reads_number_and_head_ref_and_only_the_issue_comments(tmp_path):
    pull = {
        "id": 901,
        "number": 7,
        "head": {"ref": "topic", "sha": "abc"},
        "base": {"ref": "develop"},
    }
    comments = [
        {"id": 1, "user": {"login": "ada", "username": "a"}, "body": "hi"},
        {"id": 2, "user": {"username": "bo"}, "body": "yo"},
    ]
    routes = {
        "repos/o/r/pulls/7": (pull, ""),
        "repos/o/r/issues/8": ({"id": 902, "number": 8, "title": "Bug"}, ""),
        "repos/o/r/issues/8/comments": (comments, ""),
    }
    transport = RoutedTransport(routes)
    forge = ForgejoForge(root=tmp_path, repository="o/r", transport=transport)
    change, _ = forge.get_change_request(7)
    assert change is not None and (change.number, change.head_ref) == (7, "topic")
    found, _ = forge.get_issue(8)
    assert found is not None and found.number == 8
    thread, problem = forge.get_issue_thread(8)
    assert [comment.author for comment in thread] == ["ada", "bo"] and problem == ""
    assert all("pulls/8/comments" not in call[0] for call in transport.calls)
    unrouted = "no route for repos/o/r/issues/9/comments"
    assert forge.get_issue_thread(9) == ((), unrouted)


def test_selector_hands_the_host_to_the_adapter(tmp_path):
    platform = PlatformConfig(kind="forgejo", host="git.example.org")
    forgejo = ForgeSelector._forgejo(GhConfig(root=tmp_path, platform=platform))
    assert forgejo.host == "git.example.org"
    assert forgejo.transport.host == "git.example.org"
    assert ForgeSelector._forgejo(GhConfig(root=tmp_path)).host == "forgejo.local"
    assert ForgeSelector._gitlab(GhConfig(root=tmp_path)).host == "gitlab.com"
```

**`test/test_forge_adapters.py`**, inside `test_forgejo_adapter_covers_list_and_mutation_paths`
(edit these lines in place; keep every other assertion). The line numbers are the integration
branch's; child lane 1 added one import line at the top of the file, so find each by its text
(`grep -n '"branch": "topic"' test/test_forge_adapters.py`):
- line 287: the heads fixture `{"head": {"branch": "topic"}}` becomes `{"head": {"ref": "topic"}}`.
- lines 304-311: the `pr` fixture's `"id": 7` becomes `"number": 7`, and its
  `"head": {"branch": "topic", "sha": "abc"}` becomes `"head": {"ref": "topic", "sha": "abc"}`.
- line 317: the `issue` fixture `{"id": 8, "title": "Bug", "body": "Body", "state": "open"}`
  becomes `{"number": 8, "title": "Bug", "body": "Body", "state": "open"}`.
- lines 322-333 (the comments block, from `comments = [...]` through the
  `"Comments field is not a list"` assertion) become:
  ```python
      comments = [{"id": 1, "user": {"username": "ada"}, "body": "hi"}]
      assert _forgejo(ScriptedTransport((comments, ""))).get_issue_thread(8)[0][0].author == "ada"
      down = _forgejo(ScriptedTransport(([], "not issue"))).get_issue_thread(8)
      assert down == ((), "not issue")
      odd = _forgejo(ScriptedTransport(({}, ""))).get_issue_thread(8)
      expected = "Forgejo answered repos//issues/8/comments with something other than a list"
      assert odd == ((), expected)
  ```
  (the `_forgejo()` helper builds an adapter with no repository, hence `repos//`.)

The GitLab assertions in `test_gitlab_adapter_covers_list_and_mutation_paths` need no change:
`ScriptedTransport` answers `([], "")` once its script runs out, which ends a page walk.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_foundation.py test/test_forge_adapters.py test/test_platform.py test/test_forge_github.py test/test_tidy.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the files named under "Where to change"
git status --short   # the one new file, test/forge_doubles.py, and nothing else new
```
If black or isort reports a file you touched, run `python -m black --line-length 100 <file>` and
`isort <file>` on that file only, then run the whole block again.

## Out of scope
- `vibey_gh/forge_github.py`, `vibey_gh/forge.py`, the transports and everything under
  `vibey_gh/interfaces/`: other lanes own them.
- `repository_name`, `delete_branch`, the GitHub helpers: child lane 3
  (`split-332-3-repository-name`). The selector's GitHub binding, `current`, `resolve` and
  `RecordingForge`: child lane 4 (`split-332-4-selector-resolve`).
- `list_artifacts`, `get_reviews`, `get_check_results`, `create_comment` (including its own
  `pulls/{number}/comments` fallback), `update_change_request`, `merge_change_request`,
  `create_release`, `set_protected_ref`, `get_protected_refs`: later forge lanes.
- `test/conftest.py`, `test/test_forge_github.py`, `test/test_tidy.py`, `test/test_platform.py`.
- The repository's `[platform] kind = "github"` declaration in the root `.vibey-gh.toml`
  (lines 18-19): never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  when done.

## Conventions this lane relies on (everything needed is here)
- **The adapter contract (vibey-gh ADR 0001).** Every verb answers `(value, problem)`. `problem`
  is `""` exactly when the forge answered; otherwise `value` is the empty value for its type
  (`None`, `()`, `frozenset()`, `False`, `[]`, `{}`) and `problem` is one sentence. No verb raises
  for a failed call, a missing client, a non-2xx status or unreadable output
  (`vibey_gh/interfaces/forge_adapter_interface.py:9-16`).
- **Forgejo and GitLab plumbing.** A transport's `survey([path])` is a GET;
  `survey([path, "POST"|"PATCH"|"PUT"|"DELETE", body])` sends `body` (`json.dumps(payload)`, or
  `""` for no body). Forgejo's base URL is `https://{host}/api/v1/`, GitLab's is
  `https://{host}/api/v4/`. `{R}` for Forgejo is `quote(self.repository, safe="/")` (the existing
  `_repository()` helper); `{P}` for GitLab is `quote(self.repository, safe="")` (the existing
  `_project()` helper). After child lane 1, a 2xx answer with an empty body is `({}, "")`.
- **Tests.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
  (`pyproject.toml:64-71`). Focused runs need `--no-cov`; the whole-suite run must pass without
  it. Substitute only at a declared seam (a constructor argument or dataclass field): no
  `monkeypatch.setattr` of an import or of a module or class attribute, no `mock.patch`, no
  `MagicMock`/`AsyncMock` (sub-doctrine 9.b). Test files import only the double they need, and
  never touch `test/conftest.py`.
- **Working in the big files.** Each adapter class is the last statement of its module, so a new
  method is added at the end of the class: use `edit_file` with the class's current last method
  (read the tail with `tail -n 30 vibey_gh/forge_forgejo.py`) as `old_string`, and that same
  method followed by the new methods (indented four spaces) as `new_string`. Change an existing
  method with `edit_file` on that method alone. Read only the slices you need
  (`sed -n '60,160p' vibey_gh/forge_forgejo.py`). Never rewrite a whole module and never use
  `write_file` on an existing file. New test code goes at the end of the test file; new imports go
  into the file's top import block.
- **The formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
  (profile black, `combine_as_imports`; CI job `tools-lint`, `.github/workflows/ci.yml:699-705`)
  and the root `ruff format --check .` (line length 100). They disagree on some wraps, so write
  lines neither wants to rewrap:
  - keep every line at or under 100 columns, and at or under 95 for anything with nested calls;
  - bind a long comparison, expected value or path to a local first;
  - never use implicit string concatenation; use one literal, or an f-string built from locals;
  - never put a string literal inside an f-string's braces; bind it to a local first;
  - write multi-line calls with one argument per line and a trailing comma;
  - never use backslash continuations.

  If the two formatters fight over a line, restructure the line. Never alternate between them.
- **Platforms (8.h).** The suite must pass on Arch Linux and macOS: no GNU-only tools in tests,
  and compare paths through `Path.resolve()`.

**Depends on:** split-332-1-transport-seams
- split-332-1-transport-seams: the transports' `({}, "")` answer for an empty 2xx body, and the
  new `test/test_forge_foundation.py` this lane appends to.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
