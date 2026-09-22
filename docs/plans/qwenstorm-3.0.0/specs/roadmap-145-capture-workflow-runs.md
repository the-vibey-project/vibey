## Title
feat(gh): forge-snapshot captures workflow runs, resumable by creation, and a run still in progress holds the resume point

## Why
Issue #145 (rewrite: `issue-audit/updates/145.md`, "Proposed child issues" 4, and Scope §3
"actions / workflow runs") asks for a `workflow-run` class read from
`/repos/{repo}/actions/runs`, "resumable by `created`"; #136 lists "workflow-run records"
among the classes it must capture (`issue-audit/updates/136.md`, the original text). The
coordinator places every capture of both issues in the snapshot. Today:
`("workflow-run", "Actions workflow runs are a slice of their own.")`
(`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:151` at integration `4317cff6`).

Four facts of GitHub's API shape the class:
- The listing is wrapped (`{"total_count": n, "workflow_runs": [...]}`); `_wrapped`
  (added by `roadmap-136-capture-checks`) reads it.
- The only moment filter is `created` (`created=>=MOMENT`, sent URL-encoded as
  `created=%3E%3DMOMENT`). A run created before the resume point but still running when it
  was captured would never be walked again, and its outcome would be lost. So the reader
  reports a `hold`: the creation time of the earliest unfinished run. `ForgeSnapshot` never
  moves a cursor past a hold (today's rule, `_cursor`, `forge_snapshot.py:614-620`, takes the
  latest of the prior cursor, the high water and the clock floor, with nothing to hold it).
- GitHub returns at most 1,000 runs for a `created` filter. A resumed walk that reaches that
  cap may be partial, so it is `could-not-look` with the reason, never a silent truncation.
- Each run carries `head_commit.author.email` and `head_commit.committer.email`; the class
  declares both redacted (SD-01 §1, `src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md:26`;
  7.c, `src/vibey_tools/gh/docs/doctrines.md:82-91`), through the `redact` mechanism of
  `roadmap-136-capture-repo-metadata`.

Also 10.f, a partial walk is never reported as complete (`doctrines.md:419`); 8.g, runs are
the measurements of every pipeline (`doctrines.md:316`). No host-specific code: the suite runs
unchanged on Arch Linux and macOS (8.h, `doctrines.md:326-333`).

## Required behaviour
This lane runs after `roadmap-136-capture-timelines`; anchors are text.
1. `src/vibey_tools/gh/vibey_gh/interfaces/forge_snapshot_interface.py`:
   - `ForgeRead` (`:30-47`) gains a last field `hold: str | None = None`, and its docstring a
     paragraph: "`hold` is the earliest moment a later capture of this class must still walk
     from, because something walked was not finished (a workflow run still in progress);
     `None` when nothing holds the class's cursor back."
   - `ForgeReadInterface` (`:50-65`) gains, after `problem`:
     ```python
         @property
         def hold(self) -> str | None: ...
     ```
2. `src/vibey_tools/gh/vibey_gh/forge_snapshot.py`:
   - Before `_SHA = re.compile(` add
     `# GitHub lists at most this many workflow runs for a `created` filter (its documented cap).`
     and `_RUN_FILTER_CAP = 1000`.
   - `CLASSES`: replace `)\n\nEXCLUDED: tuple[tuple[str, str], ...] = (` with
     ```python
         ForgeClass(
             "workflow-run",
             "workflow_run",
             "repos/{repository}/actions/runs?per_page={per_page}",
             cursor=True,
             redact=("head_commit.author.email", "head_commit.committer.email"),
         ),
     )

     EXCLUDED: tuple[tuple[str, str], ...] = (
     ```
   - `EXCLUDED`: delete exactly `    ("workflow-run", "Actions workflow runs are a slice of their own."),`.
   - `read`: directly above `        return self._walk(spec, since)` insert
     ```python
             if spec.name == "workflow-run":
                 return self._workflow_runs(spec, since)
     ```
   - Two new methods, directly above `    @staticmethod\n    def _observed(`:
     ```python
         def _workflow_runs(self, spec: ForgeClass, since: str | None) -> ForgeRead:
             """Actions runs, resumable by when they were created.

             A run still in progress when it is walked holds the class's cursor at its creation,
             so the resume after it finishes walks it again and records how it ended. A re-run of
             a run created before the resume point is caught by the next full capture.
             """
             path = spec.endpoint.format(repository=self.repository, per_page=self._per_page)
             if since is not None:
                 path += f"&created=%3E%3D{since}"
             items, problem = self._wrapped(path, "workflow_runs")
             if problem:
                 return ForgeRead(spec.name, spec.native_class, problem=problem)
             if since is not None and len(items) >= _RUN_FILTER_CAP:
                 return ForgeRead(
                     spec.name,
                     spec.native_class,
                     problem=(
                         f"GitHub lists at most {_RUN_FILTER_CAP} workflow runs for a `created`"
                         f" filter and the walk from {since} reached it, so it may be partial;"
                         " a full capture (no --since) reads every run"
                     ),
                 )
             read = self._observed(spec, items, self._high_water(items))
             if read.problem:
                 return read
             return ForgeRead(
                 read.forge_class,
                 read.native_class,
                 read.observations,
                 read.high_water,
                 hold=self._unfinished(items),
             )

         @staticmethod
         def _unfinished(items: Iterable[Mapping[str, Any]]) -> str | None:
             """The creation of the earliest run not yet completed: a resume must walk from there."""
             moments: list[datetime] = []
             for item in items:
                 created = item.get("created_at")
                 if item.get("status") == "completed" or not isinstance(created, str):
                     continue
                 try:
                     moments.append(moment(created))
                 except ValueError:
                     continue
             return stamp(min(moments)) if moments else None
     ```
   - `ForgeSnapshot.capture`: replace
     `self._cursor(prior, since, read.high_water, floor) if spec.cursor else None,` with
     `self._cursor(prior, since, read.high_water, floor, read.hold) if spec.cursor else None,`
     (black then wraps it in parentheses).
   - `ForgeSnapshot._cursor` becomes:
     ```python
         @staticmethod
         def _cursor(
             prior: str | None,
             since: str | None,
             high_water: str | None,
             floor: str,
             hold: str | None = None,
         ) -> str | None:
             if since is not None and (prior is None or moment(since) > moment(prior)):
                 return prior
             latest = ForgeSnapshot._latest(prior, high_water, floor)
             if hold is not None and latest is not None and moment(hold) < moment(latest):
                 return hold
             return latest
     ```
     A hold can only pull a cursor back, never push it forward; `resume_since` (the earliest
     cursor) then starts every class of the next resume at the hold.
3. `src/vibey_tools/gh/docs/forge-snapshot.md` (rows only; the schema-document test
   `test/test_forge_snapshot.py:1143-1153` owns them):
   - replace `\n\nA few things about GitHub that the files keep rather than hide:` with a newline,
     this row, and the same text:
     ```
     | `workflow-run.jsonl` | `workflow-run` | `workflow_run` | `/repos/{repo}/actions/runs`, from a moment by `created` | `id` | yes |
     ```
   - delete the row `| `workflow-run` | Actions runs, jobs, logs and artifacts: a slice of their own. |`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/interfaces/forge_snapshot_interface.py` (behaviour 1).
- `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` (behaviour 2).
- `src/vibey_tools/gh/docs/forge-snapshot.md` (behaviour 3, two rows only).
- `src/vibey_tools/gh/test/test_forge_snapshot.py` — fixture edits, then append the tests.
  Use `edit_file`; each anchor is unique:
  1. `World` fields: directly above `\n    @classmethod\n    def seeded(cls, per_page: int = 100) -> World:` insert
     `    workflow_runs: list[dict[str, Any]] = field(default_factory=list)`.
  2. `World.seeded`: directly above `        return world\n\n    # -- the command lines a capture makes` insert
     ```python
             world.workflow_runs = [
                 {
                     "id": 2701,
                     "node_id": "WFR_2701",
                     "name": "CI",
                     "event": "pull_request",
                     "status": "completed",
                     "conclusion": "success",
                     "workflow_id": 2601,
                     "run_number": 7,
                     "run_attempt": 1,
                     "head_branch": "fix/crash",
                     "head_sha": "a" * 40,
                     "actor": bo,
                     "triggering_actor": bo,
                     "head_commit": {
                         "id": "a" * 40,
                         "message": "Fix the crash",
                         "timestamp": "2026-09-02T09:00:00Z",
                         "author": {"name": "Bo", "email": "bo@example.invalid"},
                         "committer": {"name": "Bo", "email": "bo@example.invalid"},
                     },
                     "created_at": "2026-09-02T09:01:00Z",
                     "updated_at": "2026-09-02T09:08:00Z",
                     "run_started_at": "2026-09-02T09:01:00Z",
                     "url": f"{API}/actions/runs/2701",
                 },
             ]
     ```
  3. `World.answers`: the runs listing depends on the moment, so it goes inside the
     `for since in sinces or (None,):` loop. Directly after the two lines
     `                pages = self._pages(self._since(items, since))` /
     `                out[self.listing(self.path(name, since))] = {"out": json.dumps(pages)}`
     insert, at 12 spaces:
     ```python
                 runs = [
                     run
                     for run in self.workflow_runs
                     if since is None or moment(run["created_at"]) >= moment(since)
                 ]
                 runs_path = self.path("workflow-run")
                 if since is not None:
                     runs_path += f"&created=%3E%3D{since}"
                 out[self.listing(runs_path)] = {
                     "out": json.dumps(
                         [{"total_count": len(runs), "workflow_runs": page} for page in self._pages(runs)]
                     )
                 }
     ```
  4. `test_a_full_capture_writes_every_class_verbatim_and_chained`: replace
     `    }\n    assert manifest["resume_since"] == floor` with
     `        "workflow-run": floor,\n    }\n    assert manifest["resume_since"] == floor`.
     (Runs are not added to `expected`: their payload is redacted.)
  5. `test_a_capture_resumes_from_its_cursor_and_continues_every_chain`: replace
     `    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")` with
     `        "workflow-run": (0, 0, 0),\n    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")`
     (the seeded run was created before the resume point).
  Change no other existing test.
- Then run `python -m black vibey_gh test` and `isort vibey_gh test` from `src/vibey_tools/gh`.

## Acceptance criteria
- [ ] `workflow-run` is a captured class, gone from `EXCLUDED`, and in the docs table.
- [ ] A full capture reads `repos/{repo}/actions/runs?per_page=100` with no filter; a resume
      adds `&created=%3E%3D<resume point>`.
- [ ] A run still in progress sets the class's cursor, and the manifest's `resume_since`, to
      its creation; the resume after it completes walks it again and appends its new state.
- [ ] A hold never moves a cursor forward (`_cursor` unit test).
- [ ] Commit emails in a run are stored as `"[REDACTED]"`.
- [ ] A filtered walk that reaches 1,000 runs, a failed listing and a malformed one are each
      `could-not-look` with the exact message, and nothing is written.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% line and branch floor
      (`pyproject.toml:64-70`).

## Tests to write first (TDD)
No test leaves the machine or patches an import: every test drives the reader through the file's `World` and the `fake_gh` fixture, a scripted `gh` executable behind the `GhTransport` injected into `GithubForgeReader` (`test/conftest.py:87-156`). No `mock.patch`, no `monkeypatch.setattr`, no `MagicMock`.
Append to `src/vibey_tools/gh/test/test_forge_snapshot.py`:
- `test_workflow_runs_are_captured_with_commit_emails_redacted` — `capture(classes=["workflow-run"])`:
  native id `"2701"`; the payload equals the seeded run with `head_commit.author` and
  `head_commit.committer` both `{"name": "Bo", "email": REDACTED}`.
- `test_a_resumed_capture_asks_for_runs_created_since_the_cursor` — full `capture()`, script
  `world.answers(resume)`, `fake_gh.forget()`, capture `since="resume"` with
  `clock=Ticks("2026-09-11T00:00:00Z")`: the call
  `World.listing(f"{world.path('workflow-run')}&created=%3E%3D{resume}")` was made.
- `test_a_run_still_in_progress_holds_the_resume_point_at_its_creation` — append
  `running = {**world.workflow_runs[0], "id": 2702, "status": "in_progress", "conclusion": None,
  "created_at": "2026-09-09T20:00:00Z", "updated_at": "2026-09-09T20:05:00Z"}`; a full capture
  (default `Ticks`) gives the class cursor and `resume_since` `"2026-09-09T20:00:00Z"`. Then
  replace it with `{**running, "status": "completed", "conclusion": "success", "updated_at":
  "2026-09-10T01:00:00Z"}`, script `world.answers("2026-09-09T20:00:00Z")`, `fake_gh.forget()`,
  and capture `since="resume"` with `clock=Ticks("2026-09-11T00:00:00Z")`: the filtered
  listing from `2026-09-09T20:00:00Z` was called, the class shows `observed == 1` and
  `appended == 1`, and its cursor is `"2026-09-10T23:55:01Z"`.
- `test_a_hold_never_moves_a_cursor_forward` — with `floor = "2026-09-10T00:00:00Z"`:
  `ForgeSnapshot._cursor(None, None, None, floor, "2026-09-09T20:00:00Z") ==
  "2026-09-09T20:00:00Z"`, `ForgeSnapshot._cursor(None, None, None, floor,
  "2026-09-12T00:00:00Z") == floor`, and `ForgeSnapshot._cursor(None, None, None, floor) == floor`.
- `test_unfinished_runs_without_a_readable_creation_hold_nothing` —
  `GithubForgeReader._unfinished([{"status": "queued", "created_at": "soon"}, {"status":
  "queued"}, {"status": "completed", "created_at": "2026-09-01T00:00:00Z"}]) is None`, and for
  `[{"status": "queued", "created_at": "2026-09-03T00:00:00Z"}, {"status": "in_progress",
  "created_at": "2026-09-02T00:00:00Z"}]` it is `"2026-09-02T00:00:00Z"`.
- `test_a_workflow_run_listing_that_fails_or_is_malformed_is_could_not_look` — parametrized
  over the unfiltered listing answering `{"err": "HTTP 403\n", "code": 1}` (problem ends
  `"failed: HTTP 403"`), `{"out": json.dumps([{"total_count": 1}])}` (ends
  ``"did not answer with pages holding `workflow_runs`"``) and
  `{"out": json.dumps([{"total_count": 1, "workflow_runs": [{"name": "no id"}]}])}` (ends
  ``"the forge listed a workflow_run with no `id`"``); status `could-not-look`, no file.
- `test_a_created_filter_that_reaches_githubs_cap_is_could_not_look` — 1,000 runs
  `{**template, "id": 30000 + n, "created_at": "2026-09-09T23:58:00Z"}`, script
  `world.answers("2026-09-09T00:00:00Z")`, `capture(classes=["workflow-run"],
  since="2026-09-09T00:00:00Z")`: `could-not-look` with problem exactly
  `"GitHub lists at most 1000 workflow runs for a `created` filter and the walk from
  2026-09-09T00:00:00Z reached it, so it may be partial; a full capture (no --since) reads every run"`.

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
git diff --stat              # only the four files above
```

## Out of scope
- Jobs, logs and artifacts of a run (still named in the docs' exclusion reasoning; a later lane).
- Rulesets, branch protection (`roadmap-145-capture-rules`), traffic (`roadmap-145-capture-traffic`).
- Forgejo Actions runs and `ForgeAdapterReader` (after the gaps.md §L8 lane).
- Any prose in `docs/forge-snapshot.md` beyond the two rows: the docs wave. CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
