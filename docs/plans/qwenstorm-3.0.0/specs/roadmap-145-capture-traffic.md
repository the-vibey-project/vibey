## Title
feat(gh): forge-snapshot captures GitHub traffic (views, clones, referrers, popular paths) before the fourteen-day window discards it

## Why
Issue #145 (rewrite: `issue-audit/updates/145.md`, "Proposed child issues" 6, and Scope §3
"insights (traffic, clones and referrers, a rolling 14-day window, so it must be captured on a
schedule or it is lost)") asks for a `traffic` class. Today it is excluded:
`("traffic", "Traffic views are a rolling fourteen-day window.")`
(`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:167` at integration `4317cff6`). Every day
not captured is gone for good, which is the gap 7.c names: "What the ledger does not hold is a
gap to be closed" (`src/vibey_tools/gh/docs/doctrines.md:82-91`). Traffic is a GitHub-only
surface (a declared paid relay under 8.b, `doctrines.md:138`, `:179-186`), so only
`GithubForgeReader` serves it; any other reader answers "could not look" for it.

GitHub serves four answers, all needing push permission: `traffic/views?per=day` and
`traffic/clones?per=day` (objects with fourteen daily buckets and window totals, which daily
buckets cannot rebuild, so each is kept whole), and `traffic/popular/referrers` and
`traffic/popular/paths` (lists, kept one record per referrer or path). A token without push is
"could not look" with the reason (10.f, `doctrines.md:419`). This lane is the class and its
selection through the existing `--classes` flag (`vibey_gh/cli.py:1566-1569`); scheduling the
capture as a workflow belongs to the template design of the gaps.md §L8 lane and #138. No
host-specific code: the suite runs unchanged on Arch Linux and macOS (8.h, `doctrines.md:326-333`).

## Required behaviour
All in `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` unless named otherwise. This lane runs
after `roadmap-145-capture-rules`; anchors are text.
1. `CLASSES`: replace `)\n\nEXCLUDED: tuple[tuple[str, str], ...] = (` with
   ```python
       ForgeClass("traffic", "traffic", "repos/{repository}/traffic"),
   )

   EXCLUDED: tuple[tuple[str, str], ...] = (
   ```
   Walked whole every capture (no cursor): the forge's own window is the bound.
2. `EXCLUDED`: delete exactly `    ("traffic", "Traffic views are a rolling fourteen-day window."),`.
3. `read`: directly above `        return self._walk(spec, since)` insert
   ```python
           if spec.name == "traffic":
               return self._traffic(spec)
   ```
4. Two new methods, directly above `    @staticmethod\n    def _observed(` (`_object` is from
   `roadmap-136-capture-repo-metadata`):
   ```python
       def _traffic(self, spec: ForgeClass) -> ForgeRead:
           """Views, clones, referrers and popular paths, each as GitHub serves it.

           GitHub keeps a rolling fourteen days and discards the rest, so only a capture on a
           schedule keeps them at all. Reading them needs push permission; a token without it
           is a named could-not-look.
           """
           base = spec.endpoint.format(repository=self.repository)
           observations: list[Observation] = []
           for name in ("views", "clones"):
               value, problem = self._object(f"{base}/{name}?per=day")
               if problem:
                   return self._no_traffic(spec, problem)
               observations.append((name, value))
           for name, key in (("referrers", "referrer"), ("paths", "path")):
               path = f"{base}/popular/{name}"
               listed, problem = self._transport.survey(["api", path])
               if problem:
                   return self._no_traffic(spec, problem)
               if not isinstance(listed, list) or not all(
                   isinstance(item, dict) and isinstance(item.get(key), str) for item in listed
               ):
                   return self._no_traffic(
                       spec, f"`api {path}` did not answer with a list of objects naming a `{key}`"
                   )
               observations.extend((f"{key}:{item[key]}", item) for item in listed)
           return ForgeRead(spec.name, spec.native_class, tuple(observations))

       @staticmethod
       def _no_traffic(spec: ForgeClass, problem: str) -> ForgeRead:
           return ForgeRead(
               spec.name,
               spec.native_class,
               problem=f"could not read traffic (reading it needs push permission): {problem}",
           )
   ```
   Native ids: `views`, `clones`, `referrer:<referrer>`, `path:<path>`. A window that moved is
   a new record of that id; one that did not is `unchanged`.
5. `src/vibey_tools/gh/docs/forge-snapshot.md` (rows only; the schema-document test
   `test/test_forge_snapshot.py:1143-1153` owns them):
   - replace `\n\nA few things about GitHub that the files keep rather than hide:` with a newline,
     this row, and the same text:
     ```
     | `traffic.jsonl` | `traffic` | `traffic` | `/repos/{repo}/traffic/views`, `/clones`, `/popular/referrers`, `/popular/paths` | `views`, `clones`, `referrer:{referrer}`, `path:{path}` | no |
     ```
   - delete the row `| `traffic` | A rolling fourteen-day window the forge discards. |`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` (behaviour 1-4).
- `src/vibey_tools/gh/docs/forge-snapshot.md` (behaviour 5, two rows only).
- `src/vibey_tools/gh/test/test_forge_snapshot.py` — fixture edits, then append the tests.
  Use `edit_file`; each anchor is unique:
  1. `World` fields: directly above `\n    @classmethod\n    def seeded(cls, per_page: int = 100) -> World:` insert
     `    traffic: dict[str, Any] = field(default_factory=dict)`.
  2. `World.seeded`: directly above `        return world\n\n    # -- the command lines a capture makes` insert
     ```python
             world.traffic = {
                 "views": {
                     "count": 14,
                     "uniques": 3,
                     "views": [{"timestamp": "2026-09-09T00:00:00Z", "count": 14, "uniques": 3}],
                 },
                 "clones": {
                     "count": 2,
                     "uniques": 1,
                     "clones": [{"timestamp": "2026-09-09T00:00:00Z", "count": 2, "uniques": 1}],
                 },
                 "referrers": [{"referrer": "github.com", "count": 9, "uniques": 2}],
                 "paths": [{"path": "/acme/widgets", "title": "acme/widgets", "count": 11, "uniques": 3}],
             }
     ```
  3. `World.answers`: directly above its last line `        return out` insert
     ```python
             traffic = f"api repos/{REPO}/traffic"
             out[f"{traffic}/views?per=day"] = {"out": json.dumps(self.traffic.get("views", {}))}
             out[f"{traffic}/clones?per=day"] = {"out": json.dumps(self.traffic.get("clones", {}))}
             for name in ("referrers", "paths"):
                 out[f"{traffic}/popular/{name}"] = {"out": json.dumps(self.traffic.get(name, []))}
     ```
  4. `test_a_full_capture_writes_every_class_verbatim_and_chained`: replace
     `    }\n    assert manifest["resume_since"] == floor` with
     `        "traffic": None,\n    }\n    assert manifest["resume_since"] == floor`.
  5. `test_a_capture_resumes_from_its_cursor_and_continues_every_chain`: replace
     `    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")` with
     `        "traffic": (4, 0, 4),\n    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")`.
  Change no other existing test.
- Then run `python -m black vibey_gh test` and `isort vibey_gh test` from `src/vibey_tools/gh`.

## Acceptance criteria
- [ ] `traffic` is a captured class, gone from `EXCLUDED`, and in the docs table.
- [ ] A capture writes four records (`views`, `clones`, `referrer:github.com`,
      `path:/acme/widgets`) whose payloads are GitHub's answers verbatim; the class has no cursor.
- [ ] A new day in the views window appends one record and leaves the other three unchanged.
- [ ] A 403 on any of the four answers, and a popular listing of the wrong shape, are
      `could-not-look` with the exact message, and nothing is written.
- [ ] `vibey-gh forge-snapshot --classes traffic` captures traffic alone and exits 0.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% line and branch floor
      (`pyproject.toml:64-70`).

## Tests to write first (TDD)
No test leaves the machine or patches an import: every test drives the reader through the file's `World` and the `fake_gh` fixture, a scripted `gh` executable behind the `GhTransport` injected into `GithubForgeReader` (`test/conftest.py:87-156`). No `mock.patch`, no `monkeypatch.setattr`, no `MagicMock`.
Append to `src/vibey_tools/gh/test/test_forge_snapshot.py`:
- `test_traffic_is_captured_as_views_clones_referrers_and_paths` — `capture(classes=["traffic"])`:
  native ids `["views", "clones", "referrer:github.com", "path:/acme/widgets"]`, payloads
  `[world.traffic["views"], world.traffic["clones"], world.traffic["referrers"][0],
  world.traffic["paths"][0]]`, and the class `cursor is None`.
- `test_a_new_day_of_traffic_appends_only_what_moved` — capture, then set `world.traffic["views"]`
  to `{"count": 20, "uniques": 4, "views": [<the old day>, {"timestamp":
  "2026-09-10T00:00:00Z", "count": 6, "uniques": 2}]}`, re-script, capture again:
  `(observed, appended, unchanged) == (4, 1, 3)`.
- `test_traffic_without_push_permission_is_a_named_could_not_look` — parametrized over
  `"views?per=day"`, `"clones?per=day"`, `"popular/referrers"`, `"popular/paths"`, answering
  `{"err": "HTTP 403: Must have push access to repository\n", "code": 1}`: status
  `could-not-look`, problem exactly `"could not read traffic (reading it needs push permission):"
  f" `gh api repos/{REPO}/traffic/{endpoint}` failed: HTTP 403: Must have push access to
  repository"`, and `traffic.jsonl` does not exist.
- `test_a_popular_listing_of_the_wrong_shape_is_could_not_look` — referrers answer
  `json.dumps({"referrer": "x"})`: problem exactly
  `"could not read traffic (reading it needs push permission):"
  f" `api repos/{REPO}/traffic/popular/referrers` did not answer with a list of objects naming a `referrer`"`.
- `test_the_command_captures_traffic_alone_when_asked` — `main(["forge-snapshot", "--out",
  str(snap), "--repo", REPO, "--classes", "traffic"]) == 0`; stdout contains
  `"  traffic: 4 observed, 4 appended, 0 unchanged"` and `"  issue: not selected"`.

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
- A scheduled workflow or cron for the capture: the workflow templates belong to the gaps.md
  §L8 lane and #138's template design. Changes to `cli.py` (the existing `--classes` flag
  already selects the class).
- Stargazers, watchers, forks (still excluded) and any other insight surface.
- `ForgeAdapterReader` (the gaps.md §L8 lane).
- Any prose in `docs/forge-snapshot.md` beyond the two rows, for example the read-access note
  at `:44-47`: the docs wave. CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
