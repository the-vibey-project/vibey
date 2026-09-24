## Title
feat(gh): forge-snapshot captures check runs and commit statuses for the head of every captured change request

## Why
Issue #136 (rewrite: `issue-audit/updates/136.md`, "Proposed child issues" 3, slice S3) names
"check runs and statuses" among the artifacts a forge holds, and asks for them "bounded to
the head SHAs of captured change requests, so the walk stays proportional". Today both are
excluded: `("check-run", "Check runs belong to commits.")` and
`("commit-status", "Commit statuses belong to commits.")`
(`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:149-150` at integration `4317cff6`).

The pattern to copy already exists: reviews are listed once per change request, from the one
cached walk of change requests (`_reviews`, `forge_snapshot.py:281-309`, reusing
`_pull_requests`' cache at `:252-279`). Check runs and statuses are listed once per distinct
head commit of that same walk. GitHub wraps check runs in an object
(`{"total_count": n, "check_runs": [...]}`), so `gh api --paginate --slurp` returns a list of
page objects, which `_listing` (`:241-250`) refuses; a small wrapped-listing reader is needed.
`filter=all` is passed because the endpoint's default returns only the latest run per name.

Ratified law: 7.c, the ledger holds "as much of what happened as can be recorded"
(`src/vibey_tools/gh/docs/doctrines.md:82-91`); 10.f, "could not look" is never "nothing
there" (`doctrines.md:419`); 9.b (`doctrines.md:349`). No host-specific code: the suite runs
unchanged on Arch Linux and macOS (8.h, `doctrines.md:326-333`).

## Required behaviour
All in `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` unless named otherwise. This lane runs
after `roadmap-136-capture-repo-metadata`; every anchor below is text, not a line number.
1. After `_MAX_PER_PAGE = 100` add `_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")`.
2. `CLASSES`: replace the three lines `)\n\nEXCLUDED: tuple[tuple[str, str], ...] = (` with
   ```python
       ForgeClass(
           "check-run",
           "check_run",
           "repos/{repository}/commits/{sha}/check-runs?filter=all&per_page={per_page}",
           cursor=True,
       ),
       ForgeClass(
           "commit-status",
           "status",
           "repos/{repository}/commits/{sha}/statuses?per_page={per_page}",
           cursor=True,
       ),
   )

   EXCLUDED: tuple[tuple[str, str], ...] = (
   ```
   Both are resumable the way reviews are: a capture from a moment reads the heads of the
   change requests updated since then.
3. `EXCLUDED`: delete exactly `    ("check-run", "Check runs belong to commits."),` and
   `    ("commit-status", "Commit statuses belong to commits."),`.
4. `GithubForgeReader.read`: directly above the two lines
   `        path = spec.endpoint.format(repository=self.repository, per_page=self._per_page)` /
   `        if spec.since and since is not None:` insert
   ```python
           if spec.name == "check-run":
               return self._for_heads(spec, since, "check_runs")
           if spec.name == "commit-status":
               return self._for_heads(spec, since, None)
   ```
5. Two new methods, directly above `    @staticmethod\n    def _observed(`:
   ```python
       def _wrapped(self, path: str, key: str) -> tuple[list[dict[str, Any]], str]:
           """Every page of a listing GitHub wraps in an object, its items under `key`."""
           value, problem = self._transport.survey(["api", path, "--paginate", "--slurp"])
           if problem:
               return [], problem
           if not isinstance(value, list) or not all(
               isinstance(page, dict) and isinstance(page.get(key), list) for page in value
           ):
               return [], f"`api {path}` did not answer with pages holding `{key}`"
           items = [item for page in value for item in page[key]]
           if not all(isinstance(item, dict) for item in items):
               return [], f"`api {path}` listed something that is not a JSON object"
           return items, ""

       def _for_heads(self, spec: ForgeClass, since: str | None, key: str | None) -> ForgeRead:
           """One class listed for the head commit of every change request walked since `since`.

           Bounded to those heads, so the walk stays proportional to the change requests a
           capture reads. A check re-run on a head whose change request did not change is
           caught by the next full capture, not by a resume.
           """
           pulls = self._pull_requests(ForgeClass.named("change-request"), since)
           if pulls.problem:
               return ForgeRead(
                   spec.name,
                   spec.native_class,
                   problem=(
                       "the change requests whose head commits these belong to could not be"
                       f" listed: {pulls.problem}"
                   ),
               )
           shas: list[str] = []
           for native_id, pull in pulls.observations:
               head = pull.get("head")
               sha = head.get("sha") if isinstance(head, dict) else None
               if not isinstance(sha, str) or not _SHA.fullmatch(sha):
                   return ForgeRead(
                       spec.name,
                       spec.native_class,
                       problem=(
                           f"change request {native_id} has no head commit sha to list its"
                           f" {spec.name} records by"
                       ),
                   )
               if sha not in shas:
                   shas.append(sha)
           items: list[dict[str, Any]] = []
           for sha in shas:
               path = spec.endpoint.format(
                   repository=self.repository, sha=sha, per_page=self._per_page
               )
               if key is None:
                   found, problem = self._listing(path)
               else:
                   found, problem = self._wrapped(path, key)
               if problem:
                   return ForgeRead(spec.name, spec.native_class, problem=problem)
               items.extend(found)
           return self._observed(spec, items, pulls.high_water)
   ```
6. `src/vibey_tools/gh/docs/forge-snapshot.md` (rows only; the schema-document test,
   `test/test_forge_snapshot.py:1143-1153`, owns them):
   - replace `\n\nA few things about GitHub that the files keep rather than hide:` with a
     newline, these two rows, and the same text:
     ```
     | `check-run.jsonl` | `check-run` | `check_run` | `/repos/{repo}/commits/{sha}/check-runs?filter=all`, for each captured change request's head | `id` | yes |
     | `commit-status.jsonl` | `commit-status` | `status` | `/repos/{repo}/commits/{sha}/statuses`, for each captured change request's head | `id` | yes |
     ```
   - delete the rows
     `| `check-run` | Check runs and suites belong to commits, and are listed one commit at a time. |`
     and `| `commit-status` | Commit statuses belong to commits, and are listed one commit at a time. |`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` (behaviour 1-5).
- `src/vibey_tools/gh/docs/forge-snapshot.md` (behaviour 6, four rows only).
- `src/vibey_tools/gh/test/test_forge_snapshot.py` — fixture edits, then append the tests.
  Each anchor is unique; use `edit_file`:
  1. `World` fields: directly above `\n    @classmethod\n    def seeded(cls, per_page: int = 100) -> World:` insert
     `    check_runs: dict[str, list[dict[str, Any]]] = field(default_factory=dict)` and
     `    statuses: dict[str, list[dict[str, Any]]] = field(default_factory=dict)`.
  2. `World.seeded`: directly above `        return world\n\n    # -- the command lines a capture makes` insert
     (the key is a local name, not `"a" * 40`, because black and ruff format a multiplied
     dict key differently and both formatters gate this tenant)
     ```python
             head = "a" * 40
             world.check_runs = {
                 head: [
                     {
                         "id": 3001,
                         "node_id": "CR_3001",
                         "head_sha": "a" * 40,
                         "name": "gates",
                         "status": "completed",
                         "conclusion": "success",
                         "started_at": "2026-09-02T10:00:00Z",
                         "completed_at": "2026-09-02T10:05:00Z",
                         "output": {"title": "Gates", "summary": "All green.", "text": None},
                         "check_suite": {"id": 3101},
                         "app": {"id": 15368, "slug": "github-actions", "name": "GitHub Actions"},
                         "pull_requests": [{"number": 2, "id": 2002}],
                         "url": f"{API}/check-runs/3001",
                     },
                 ]
             }
             world.statuses = {
                 head: [
                     {
                         "id": 3501,
                         "node_id": "SC_3501",
                         "state": "success",
                         "context": "ci/external",
                         "description": "Passed",
                         "target_url": "https://ci.example.invalid/runs/1",
                         "creator": ada,
                         "created_at": "2026-09-02T10:06:00Z",
                         "updated_at": "2026-09-02T10:06:00Z",
                         "url": f"{API}/statuses/{'a' * 40}",
                     },
                 ]
             }
     ```
  3. `World.answers`: directly above its last line `        return out` insert
     ```python
             heads = [pull.get("head") for pull in self.pulls]
             shas = [h["sha"] for h in heads if isinstance(h, dict) and isinstance(h.get("sha"), str)]
             for sha in dict.fromkeys(shas):
                 runs = self.check_runs.get(sha, [])
                 out[self.listing(self.path("check-run", sha=sha))] = {
                     "out": json.dumps(
                         [{"total_count": len(runs), "check_runs": page} for page in self._pages(runs)]
                     )
                 }
                 out[self.listing(self.path("commit-status", sha=sha))] = {
                     "out": json.dumps(self._pages(self.statuses.get(sha, [])))
                 }
     ```
  4. `test_a_full_capture_writes_every_class_verbatim_and_chained`: replace
     `    }\n    for name, items in expected.items():` with
     `        "check-run": world.check_runs["a" * 40],\n        "commit-status": world.statuses["a" * 40],\n    }\n    for name, items in expected.items():`,
     and replace `    }\n    assert manifest["resume_since"] == floor` with
     `        "check-run": floor,\n        "commit-status": floor,\n    }\n    assert manifest["resume_since"] == floor`.
  5. `test_a_capture_resumes_from_its_cursor_and_continues_every_chain`: replace
     `    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")` with
     `        "check-run": (1, 0, 1),\n        "commit-status": (1, 0, 1),\n    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")`.
  Change no other existing test.
- Then run `python -m black vibey_gh test` and `isort vibey_gh test` from `src/vibey_tools/gh`.

## Acceptance criteria
- [ ] `check-run` and `commit-status` are captured classes, gone from `EXCLUDED`, and in the
      docs table; the exclusion-honesty and schema-document tests pass.
- [ ] Check runs are read with `filter=all`, once per distinct head commit of the change
      requests the capture walked, and only for those (a resume reads only the heads of change
      requests updated since the moment).
- [ ] One walk of the change requests serves change-request, review, check-run and commit-status.
- [ ] A missing head sha, an unlistable change request walk, and a failed or malformed listing
      are each `could-not-look` with the exact message, and nothing is written.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% line and branch floor
      (`pyproject.toml:64-70`).

## Tests to write first (TDD)
No test leaves the machine or patches an import: every test drives the reader through the file's `World` and the `fake_gh` fixture, a scripted `gh` executable behind the `GhTransport` injected into `GithubForgeReader` (`test/conftest.py:87-156`). No `mock.patch`, no `monkeypatch.setattr`, no `MagicMock`.
Append to `src/vibey_tools/gh/test/test_forge_snapshot.py`, after `HEAD = "a" * 40`:
- `test_check_runs_and_statuses_are_read_for_each_change_request_head` —
  `capture(classes=["check-run", "commit-status"])`: the payloads of `check-run.jsonl` equal
  `world.check_runs[HEAD]`, those of `commit-status.jsonl` equal `world.statuses[HEAD]`, and
  both `World.listing(world.path("check-run", sha=HEAD))` (which contains `filter=all`) and
  `World.listing(world.path("commit-status", sha=HEAD))` are in `fake_gh.calls()`.
- `test_two_change_requests_on_one_head_list_its_checks_once` — append
  `{**world.pulls[0], "id": 2003, "number": 3}`; the check-run listing appears exactly once in
  `fake_gh.calls()`.
- `test_only_the_heads_of_change_requests_walked_since_the_moment_are_read` — append a pull
  `{**world.pulls[0], "id": 2003, "number": 3, "head": {"ref": "feat/x", "sha": "e" * 40},
  "updated_at": "2026-09-05T00:00:00Z"}`; `capture(classes=["check-run"],
  since="2026-09-04T00:00:00Z")` lists the check runs of `"e" * 40` and not those of `HEAD`.
- `test_a_change_request_with_no_head_sha_is_could_not_look` — `world.pulls[0] =
  {**world.pulls[0], "head": {"ref": "fix/crash"}}`; for both classes `problem ==
  f"change request 2002 has no head commit sha to list its {name} records by"`.
- `test_check_runs_whose_change_requests_could_not_be_listed_say_so` —
  `answers[world.page(1)] = {"err": "HTTP 500\n", "code": 1}`; the check-run problem is
  `"the change requests whose head commits these belong to could not be listed:"
  f" `gh api {world.page(1)[4:]}` failed: HTTP 500"`.
- `test_a_check_run_listing_that_fails_or_is_malformed_is_could_not_look` — parametrized over
  the check-run listing answering `{"err": "HTTP 403\n", "code": 1}` (problem ends with
  `"failed: HTTP 403"`), `{"out": json.dumps([{"total_count": 0}])}` (ends with
  ``"did not answer with pages holding `check_runs`"``) and
  `{"out": json.dumps([{"total_count": 1, "check_runs": [1]}])}` (ends with
  `"listed something that is not a JSON object"`); status `could-not-look`, no file.
- `test_one_walk_of_the_change_requests_serves_every_class_that_needs_them` —
  `capture(classes=["change-request", "review", "check-run", "commit-status"])` makes exactly
  one call starting with `"api repos/acme/widgets/pulls?"`.

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh, black, isort, yaml" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_snapshot.py test/test_forge_adapters.py
python -m pytest -q          # the whole suite; pyproject.toml:64-70 fails it under 100% line+branch
python -m black --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
uv run ruff check . && uv run ruff format --check .
uv run lint-imports
git diff --stat              # only the three files above
```

## Out of scope
- Check suites, annotations and workflow runs (`roadmap-145-capture-workflow-runs`); checks
  of commits that head no captured change request (a later decision, after the ledger lands).
- `ForgeAdapterReader` and the adapter move (the gaps.md §L8 lane).
- Any prose in `docs/forge-snapshot.md` beyond the four rows: the docs wave. CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
