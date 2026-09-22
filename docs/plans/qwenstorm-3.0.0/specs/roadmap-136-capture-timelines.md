## Title
feat(gh): forge-snapshot captures issue and change-request timelines, one call per issue, bounded by the resume cursor

## Why
Issue #136 (rewrite: `issue-audit/updates/136.md`, "Proposed child issues" 4, slice S3) names
"timeline events" first among what a forge holds and the snapshot drops. Today:
`("timeline-event", "Issue and change-request timelines are not read.")`
(`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:141` at integration `4317cff6`), and the docs
say "The state their events produced is inside the captured payloads; the sequence of events
is not" (`src/vibey_tools/gh/docs/forge-snapshot.md:283`).

GitHub serves a timeline per issue (`GET /repos/{repo}/issues/{number}/timeline`), and its
issue listing returns pull requests too (`docs/forge-snapshot.md:142-145`), so one class covers
both. The walk copies the reviews pattern (`_reviews`, `forge_snapshot.py:281-309`): list the
parent once, cached per moment like `_pull_requests` (`:252-279`), then one call per parent.
Two facts shape the records:
- Several event kinds carry no `id` (`committed` has a `sha`; `cross-referenced` and
  `line-commented` have neither), and ids of different kinds come from different tables. So a
  record's native id is `{number}/{event}/{id}`, else `{number}/{event}/{sha}`, else
  `{number}/{event}/{content digest}`: unique, stable across captures, and a rerun appends nothing.
- `committed` events carry `author.email` and `committer.email`. SD-01 §1 forbids relaying
  people's private details (`src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md:26`),
  and 7.c redacts them visibly (`src/vibey_tools/gh/docs/doctrines.md:82-91`), so the class
  declares both paths in `redact` (the mechanism of `roadmap-136-capture-repo-metadata`).

Also 10.f (`doctrines.md:419`): a timeline that could not be read is "could not look". No
host-specific code: the suite runs unchanged on Arch Linux and macOS (8.h, `doctrines.md:326-333`).

## Required behaviour
All in `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` unless named otherwise. This lane runs
after `roadmap-136-capture-checks`; anchors are text.
1. `CLASSES`: replace `)\n\nEXCLUDED: tuple[tuple[str, str], ...] = (` with
   ```python
       ForgeClass(
           "timeline-event",
           "timeline_event",
           "repos/{repository}/issues/{number}/timeline?per_page={per_page}",
           cursor=True,
           redact=("author.email", "committer.email"),
       ),
   )

   EXCLUDED: tuple[tuple[str, str], ...] = (
   ```
2. `EXCLUDED`: delete exactly `    ("timeline-event", "Issue and change-request timelines are not read."),`.
3. `GithubForgeReader.__init__`: after `        self._change_requests: dict[str | None, ForgeRead] = {}`
   add `        self._issue_reads: dict[str | None, ForgeRead] = {}`.
4. `read`: the generic tail moves into a method. Replace these seven lines (the end of `read`,
   immediately followed by `\n    def _listing(`):
   ```python
           path = spec.endpoint.format(repository=self.repository, per_page=self._per_page)
           if spec.since and since is not None:
               path += f"&since={since}"
           items, problem = self._listing(path)
           if problem:
               return ForgeRead(spec.name, spec.native_class, problem=problem)
           return self._observed(spec, items, self._high_water(items) if spec.cursor else None)
   ```
   with
   ```python
           if spec.name == "issue":
               return self._issues(spec, since)
           if spec.name == "timeline-event":
               return self._timelines(spec, since)
           return self._walk(spec, since)

       def _walk(self, spec: ForgeClass, since: str | None) -> ForgeRead:
           """One plain listing, filtered by GitHub's `since` where the class allows it."""
           path = spec.endpoint.format(repository=self.repository, per_page=self._per_page)
           if spec.since and since is not None:
               path += f"&since={since}"
           items, problem = self._listing(path)
           if problem:
               return ForgeRead(spec.name, spec.native_class, problem=problem)
           return self._observed(spec, items, self._high_water(items) if spec.cursor else None)
   ```
   (End both `old_string` and `new_string` with the blank line and the line
   `    def _listing(self, path: str) -> tuple[list[dict[str, Any]], str]:` that follow, so the
   match is unique.) Every later lane inserts its `read` branches directly above
   `        return self._walk(spec, since)`.
5. Three new methods, directly above `    @staticmethod\n    def _observed(`:
   ```python
       def _issues(self, spec: ForgeClass, since: str | None) -> ForgeRead:
           """The issue walk, once per moment: the issue class and every timeline share it."""
           if since not in self._issue_reads:
               self._issue_reads[since] = self._walk(spec, since)
           return self._issue_reads[since]

       def _timelines(self, spec: ForgeClass, since: str | None) -> ForgeRead:
           """Every timeline event of every issue walked since `since`, one call per issue.

           GitHub's issue listing holds pull requests too, so this covers change-request
           timelines as well. An event that updates no issue (a cross-reference from elsewhere,
           say) is caught by the next full capture, not by a resume.
           """
           issues = self._issues(ForgeClass.named("issue"), since)
           if issues.problem:
               return ForgeRead(
                   spec.name,
                   spec.native_class,
                   problem=f"the issues these timelines belong to could not be listed: {issues.problem}",
               )
           observations: list[Observation] = []
           for native_id, issue in issues.observations:
               number = issue.get("number")
               if not isinstance(number, int) or isinstance(number, bool):
                   return ForgeRead(
                       spec.name,
                       spec.native_class,
                       problem=f"issue {native_id} has no number to list its timeline by",
                   )
               events, problem = self._listing(
                   spec.endpoint.format(
                       repository=self.repository, number=number, per_page=self._per_page
                   )
               )
               if problem:
                   return ForgeRead(spec.name, spec.native_class, problem=problem)
               for event in events:
                   payload = self._redacted(event, spec.redact)
                   observations.append((self._timeline_id(number, payload), payload))
           return ForgeRead(spec.name, spec.native_class, tuple(observations), issues.high_water)

       @staticmethod
       def _timeline_id(number: int, event: Mapping[str, Any]) -> str:
           """A timeline event's identity: its issue's number, its kind, then the forge's own id
           for it, its commit sha, or, for the kinds GitHub gives no identity (a
           cross-reference, a line-comment thread), the digest of its content."""
           kind = event.get("event")
           for key in ("id", "sha"):
               value = event.get(key)
               if isinstance(value, (int, str)) and not isinstance(value, bool) and value != "":
                   return f"{number}/{kind}/{value}"
           return f"{number}/{kind}/{digest(event)}"
   ```
   The digest is taken over the redacted payload, so no identity is derived from an address.
6. `src/vibey_tools/gh/docs/forge-snapshot.md` (rows only; the schema-document test
   `test/test_forge_snapshot.py:1143-1153` owns them):
   - replace `\n\nA few things about GitHub that the files keep rather than hide:` with a newline,
     this row, and the same text:
     ```
     | `timeline-event.jsonl` | `timeline-event` | `timeline_event` | `/repos/{repo}/issues/{number}/timeline`, for each captured issue | `{number}/{event}/{id}`, or its `sha`, or its content digest | yes |
     ```
   - delete the row beginning `| `timeline-event` | Issue and change-request timelines are one call per item.`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` (behaviour 1-5).
- `src/vibey_tools/gh/docs/forge-snapshot.md` (behaviour 6, two rows only).
- `src/vibey_tools/gh/test/test_forge_snapshot.py` — fixture edits, then append the tests.
  Use `edit_file`; each anchor is unique:
  1. `World` fields: directly above `\n    @classmethod\n    def seeded(cls, per_page: int = 100) -> World:` insert
     `    timelines: dict[int, list[dict[str, Any]]] = field(default_factory=dict)`.
  2. `World.seeded`: directly above `        return world\n\n    # -- the command lines a capture makes` insert
     ```python
             world.timelines = {
                 1: [
                     {
                         "id": 6001,
                         "node_id": "LE_6001",
                         "event": "labeled",
                         "actor": ada,
                         "label": {"name": "bug", "color": "d73a4a"},
                         "created_at": "2026-09-01T08:05:00Z",
                         "url": f"{API}/issues/events/6001",
                     },
                 ],
                 2: [
                     {
                         "event": "committed",
                         "sha": "a" * 40,
                         "node_id": "C_a",
                         "message": "Fix the crash",
                         "author": {"name": "Bo", "email": "bo@example.invalid"},
                         "committer": {"name": "Bo", "email": "bo@example.invalid"},
                         "html_url": f"https://github.com/{REPO}/commit/{'a' * 40}",
                     },
                 ],
             }
     ```
  3. `World.answers`: directly above its last line `        return out` insert
     ```python
             for issue in self.issues:
                 events = self.timelines.get(issue["number"], [])
                 out[self.listing(self.path("timeline-event", number=issue["number"]))] = {
                     "out": json.dumps(self._pages(events))
                 }
     ```
  4. `test_a_full_capture_writes_every_class_verbatim_and_chained`: replace
     `    }\n    assert manifest["resume_since"] == floor` with
     `        "timeline-event": floor,\n    }\n    assert manifest["resume_since"] == floor`.
     (Timeline events are not added to its `expected` dict: their native ids are composite.)
  5. `test_a_capture_resumes_from_its_cursor_and_continues_every_chain`: replace
     `    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")` with
     `        "timeline-event": (1, 0, 1),\n    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")`
     (the resume walks issue 1 only, whose one event is unchanged).
  Change no other existing test.
- Then run `python -m black vibey_gh test` and `isort vibey_gh test` from `src/vibey_tools/gh`.

## Acceptance criteria
- [ ] `timeline-event` is a captured class, gone from `EXCLUDED`, and in the docs table.
- [ ] One issue walk serves both the issue class and the timelines (one `issues?` call).
- [ ] Records are named `1/labeled/6001`, `2/committed/<sha>`, and `1/cross-referenced/<digest>`
      for an event with no identity; a repeated capture appends nothing.
- [ ] Commit emails in timeline events are stored as `"[REDACTED]"`, never as the address.
- [ ] A resume reads only the timelines of issues updated since the resume point.
- [ ] An unlistable issue walk, an issue with no number, and a failed timeline listing are each
      `could-not-look` with the exact message, and nothing is written.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% line and branch floor
      (`pyproject.toml:64-70`).

## Tests to write first (TDD)
No test leaves the machine or patches an import: every test drives the reader through the file's `World` and the `fake_gh` fixture, a scripted `gh` executable behind the `GhTransport` injected into `GithubForgeReader` (`test/conftest.py:87-156`). No `mock.patch`, no `monkeypatch.setattr`, no `MagicMock`.
Append to `src/vibey_tools/gh/test/test_forge_snapshot.py` (`REDACTED`, `digest`, `Ticks`
are already imported or defined):
- `test_every_issue_timeline_is_read_once_per_issue` — `capture(classes=["issue",
  "timeline-event"])`: native ids are `["1/labeled/6001", f"2/committed/{'a' * 40}"]`, the first
  payload equals `world.timelines[1][0]`, both timeline listings are in `fake_gh.calls()`, and
  exactly one call starts with `"api repos/acme/widgets/issues?"`.
- `test_commit_emails_in_a_timeline_are_redacted_and_say_so` — the committed record's
  `author` and `committer` both equal `{"name": "Bo", "email": REDACTED}`, and
  `"bo@example.invalid"` is not in the file's text.
- `test_a_timeline_event_with_no_identity_is_named_by_its_content` — append
  `reference = {"event": "cross-referenced", "source": {"type": "issue", "issue": {"number": 9,
  "title": "Elsewhere"}}, "created_at": "2026-09-01T09:00:00Z"}` to `world.timelines[1]`;
  `f"1/cross-referenced/{digest(reference)}"` is a native id, and a second capture of the class
  has `appended == 0`.
- `test_a_resume_reads_only_the_timelines_of_issues_updated_since` — a full `capture()` first
  (so `resume_since` is set); then `world.issues[0] = {**world.issues[0], "updated_at":
  "2026-09-10T10:00:00Z"}`, script `world.answers(first["resume_since"])`, `fake_gh.forget()`,
  and `snapshot(snap, clock=Ticks("2026-09-11T00:00:00Z")).capture(classes=["issue",
  "timeline-event"], since="resume")`: issue 1's timeline listing is in the calls, issue 2's is not.
- `test_timelines_whose_issues_could_not_be_listed_say_so` — the issue listing answers
  `{"err": "HTTP 502: Bad Gateway\n", "code": 1}`; the timeline problem is
  `"the issues these timelines belong to could not be listed:"
  f" `gh api {world.path('issue')}` failed: HTTP 502: Bad Gateway"`.
- `test_an_issue_with_no_number_holds_its_timelines_back` — `world.issues[0] =
  {**world.issues[0], "number": None}`; `problem == "issue 1001 has no number to list its timeline by"`.
- `test_a_failed_timeline_listing_is_could_not_look` — issue 1's timeline listing answers
  `{"err": "HTTP 403\n", "code": 1}`; status `could-not-look`, problem ends with
  `"failed: HTTP 403"`, and `timeline-event.jsonl` does not exist.

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
- Reactions, edit history and review-thread resolution (still excluded; review threads need
  the GraphQL design, `roadmap-145-design-graphql-reads`).
- `ForgeAdapterReader` and the adapter move (the gaps.md §L8 lane, which must carry the
  composite ids and `redact` when it takes this class over).
- Any prose in `docs/forge-snapshot.md` beyond the two rows: the docs wave. CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
