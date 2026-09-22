## Title
feat(gh): forge-snapshot captures repository metadata and commit comments, with declared redaction of credential fields

## Why
Issue #136 (rewrite: `issue-audit/updates/136.md`, "Proposed child issues" 2, slice S3) asks
for two classes the snapshot names as excluded today:
`("commit-comment", "Comments on commits are not read.")` and
`("repository-metadata", "The repository object and its settings are not read.")`
(`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:148` and `:156`). #145 wants settings
"read back" to detect drift against the declared profile (`issue-audit/updates/145.md`, Scope
§3). The coordinator places every capture of both issues here, in the snapshot.

Ratified law: 7.c, "What the ledger does not hold is a gap to be closed", and "secrets,
credentials and people's private details are redacted where they would appear, and the
redaction is itself recorded — never a silent omission" (`src/vibey_tools/gh/docs/doctrines.md:82-91`);
10.f, a class the forge would not answer for is "could not look", never "nothing there"
(`doctrines.md:419`); 12.c, declared and configurable (`doctrines.md:455`). GitHub's
repository object carries `temp_clone_token` (a short-lived clone credential) for private
repositories, so the class declares that field redacted: the key stays in the record and its
value reads `"[REDACTED]"`, the same marker vibey's ledger writes
(`src/vibey/infrastructure/ledger/redact.py:15`). Later capture lanes declare their own fields
the same way. No host-specific code: the suite runs unchanged on Arch Linux and macOS (8.h,
`doctrines.md:326-333`).

## Required behaviour
All in `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` unless named otherwise.
1. `import copy` (before `import hashlib`, `:31`). A module constant, after `RESUME = "resume"`
   (`:73`):
   ```python
   # The marker vibey's own ledger writes where it redacts (vibey/infrastructure/ledger/redact.py),
   # so a record redacted here reads the same there.
   REDACTED = "[REDACTED]"
   ```
   and `"REDACTED",` in `__all__` directly after `"RECORD_SCHEMA",`.
2. `ForgeClass` (`:78-95`) gains a last field `redact: tuple[str, ...] = ()` with a one-line
   comment: dotted paths into the forge's JSON whose values never reach a record (7.c).
   `vibey_gh/interfaces/class_contracts.py` `ForgeClassInterface` (`:204-224`) gains, after
   the `cursor` property:
   ```python
       @property
       def redact(self) -> tuple[str, ...]: ...
   ```
3. `CLASSES` gains two entries at its end. Anchor: replace the three lines
   `)\n\nEXCLUDED: tuple[tuple[str, str], ...] = (` (the close of `CLASSES`, `:138-140`) with
   the two entries followed by the same three lines:
   ```python
       ForgeClass(
           "repository-metadata", "repository", "repos/{repository}", redact=("temp_clone_token",)
       ),
       ForgeClass(
           "commit-comment", "commit_comment", "repos/{repository}/comments?per_page={per_page}"
       ),
   ```
   Both are walked whole every capture (no `since`, no `cursor`).
4. `EXCLUDED`: delete exactly the two lines
   `    ("commit-comment", "Comments on commits are not read."),` and
   `    ("repository-metadata", "The repository object and its settings are not read."),`.
5. `GithubForgeReader.read` (`:227-239`): directly above the two lines
   `        path = spec.endpoint.format(repository=self.repository, per_page=self._per_page)`
   / `        if spec.since and since is not None:` insert
   ```python
           if spec.name == "repository-metadata":
               return self._repository(spec)
   ```
   `commit-comment` needs no branch: the generic listing (`_listing`, `:241-250`) walks it.
6. New `GithubForgeReader` methods, directly above `    @staticmethod\n    def _observed(` (`:311-312`):
   ```python
       def _object(self, path: str) -> tuple[dict[str, Any], str]:
           """One JSON object the forge serves whole, or why it could not be read."""
           value, problem = self._transport.survey(["api", path])
           if problem:
               return {}, problem
           if not isinstance(value, dict):
               return {}, f"`api {path}` did not answer with a JSON object"
           return value, ""

       def _repository(self, spec: ForgeClass) -> ForgeRead:
           value, problem = self._object(spec.endpoint.format(repository=self.repository))
           if problem:
               return ForgeRead(spec.name, spec.native_class, problem=problem)
           return self._observed(spec, [value], None)

       @staticmethod
       def _redacted(payload: Mapping[str, Any], paths: Sequence[str]) -> dict[str, Any]:
           """A copy of `payload` with the value at each dotted path replaced by `REDACTED`.

           7.c's floor: a credential or a person's private detail never reaches a record, and
           the redaction stays visible in it, because the key is kept and its value says what
           happened. A path that is absent, or whose value is null, is left as the forge sent it.
           """
           copied: dict[str, Any] = copy.deepcopy(dict(payload))
           for path in paths:
               *parents, leaf = path.split(".")
               node: Any = copied
               for key in parents:
                   node = node.get(key) if isinstance(node, dict) else None
               if isinstance(node, dict) and node.get(leaf) is not None:
                   node[leaf] = REDACTED
           return copied
   ```
7. `_observed` (`:311-329`): the append becomes
   `observations.append((str(native_id), GithubForgeReader._redacted(item, spec.redact)))`.
   Every class passes through it; a class with no `redact` gets an equal copy.
8. `src/vibey_tools/gh/docs/forge-snapshot.md`: `test/test_forge_snapshot.py:1143-1153`
   (`test_the_schema_document_names_every_class_and_every_exclusion`) makes two table rows a
   code-owned contract, so edit exactly these rows and no other text:
   - append two rows to the end of "The files" table (it ends with the `tag.jsonl` row, `:138`).
     Anchor: replace the text `\n\nA few things about GitHub that the files keep rather than hide:`
     (the blank line after the table's last row, `:139-140`) with a newline, the two rows, and
     that same text, so the rows follow the last row directly:
     ```
     | `repository-metadata.jsonl` | `repository-metadata` | `repository` | `/repos/{repo}` | `id` | no |
     | `commit-comment.jsonl` | `commit-comment` | `commit_comment` | `/repos/{repo}/comments` | `id` | no |
     ```
   - delete the rows `| `commit-comment` | Comments on commits are not read. |` (`:290`) and
     `| `repository-metadata` | Not read. The settings vibey-gh manages are declared in `[repository_profile]`. |` (`:298`).

## Where to change
- `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` (behaviour 1-7).
- `src/vibey_tools/gh/vibey_gh/interfaces/class_contracts.py` (behaviour 2, three lines).
- `src/vibey_tools/gh/docs/forge-snapshot.md` (behaviour 8, four table rows only).
- `src/vibey_tools/gh/test/test_forge_snapshot.py`: the fixture edits below, then append the
  tests. Add `REDACTED` to the `from vibey_gh.forge_snapshot import (` block (`:30-45`).
  Fixture edits (use `edit_file`; each anchor is unique):
  1. `World` fields: directly above `\n    @classmethod\n    def seeded(cls, per_page: int = 100) -> World:`
     insert
     `    repository: dict[str, Any] = field(default_factory=dict)` and
     `    commit_comments: list[dict[str, Any]] = field(default_factory=list)`.
  2. `World.seeded`: directly above `        return world\n\n    # -- the command lines a capture makes`
     insert
     ```python
             world.repository = {
                 "id": 42,
                 "node_id": "R_42",
                 "name": "widgets",
                 "full_name": REPO,
                 "private": False,
                 "owner": ada,
                 "description": "Widgets, made well.",
                 "default_branch": "develop",
                 "has_issues": True,
                 "has_wiki": False,
                 "allow_squash_merge": True,
                 "allow_rebase_merge": True,
                 "delete_branch_on_merge": True,
                 "topics": ["widgets"],
                 "temp_clone_token": None,
                 "created_at": "2026-08-01T00:00:00Z",
                 "updated_at": "2026-09-02T12:00:00Z",
                 "pushed_at": "2026-09-02T12:00:00Z",
                 "url": API,
             }
             world.commit_comments = [
                 {
                     "id": 4001,
                     "node_id": "CC_4001",
                     "user": bo,
                     "body": "Why this constant?",
                     "path": "src/app.py",
                     "position": 3,
                     "line": 12,
                     "commit_id": "c" * 40,
                     "author_association": "CONTRIBUTOR",
                     "created_at": "2026-09-02T13:00:00Z",
                     "updated_at": "2026-09-02T13:00:00Z",
                     "reactions": reactions(f"{API}/comments/4001"),
                     "url": f"{API}/comments/4001",
                 },
             ]
     ```
  3. `World.answers`: directly above its last line `        return out` (the only
     `return out` in the file) insert
     ```python
             out[f"api {self.path('repository-metadata')}"] = {"out": json.dumps(self.repository)}
             out[self.listing(self.path("commit-comment"))] = {
                 "out": json.dumps(self._pages(self.commit_comments))
             }
     ```
  4. `test_a_full_capture_writes_every_class_verbatim_and_chained`:
     - replace `    }\n    for name, items in expected.items():` with
       `        "repository-metadata": [world.repository],\n        "commit-comment": world.commit_comments,\n    }\n    for name, items in expected.items():`;
     - replace `    }\n    assert manifest["resume_since"] == floor` with
       `        "repository-metadata": None,\n        "commit-comment": None,\n    }\n    assert manifest["resume_since"] == floor`;
     - replace `    assert all(call.startswith("api repos/acme/widgets/") for call in fake_gh.calls())`
       with `    assert all(call.startswith("api repos/acme/widgets") for call in fake_gh.calls())`
       (the repository object is `repos/acme/widgets` itself, with no trailing `/`).
  5. `test_a_capture_resumes_from_its_cursor_and_continues_every_chain`: replace
     `    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")` with
     `        "repository-metadata": (1, 0, 1),\n        "commit-comment": (1, 0, 1),\n    }\n    for name in NAMES:\n        records = lines(snap / f"{name}.jsonl")`.
  Change no other existing test.
- Then run `python -m black vibey_gh test` and `isort vibey_gh test` from `src/vibey_tools/gh`.

## Acceptance criteria
- [ ] `repository-metadata` and `commit-comment` are in `CLASSES` and not in `EXCLUDED`;
      `test_every_class_the_issue_names_is_captured_or_excluded_with_a_reason` and
      `test_the_schema_document_names_every_class_and_every_exclusion` pass.
- [ ] A full capture writes one `repository-metadata` record (native id `"42"`, one plain
      `api repos/acme/widgets` call, no `--paginate`) and the commit comments verbatim.
- [ ] A `temp_clone_token` value is stored as `"[REDACTED]"`, never as the token; a null one stays null.
- [ ] A 404 on the repository object is `could-not-look` with the forge's words, and nothing is written.
- [ ] Every existing test passes with only the fixture edits listed above.
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% line and branch floor
      (`pyproject.toml:64-70`).

## Tests to write first (TDD)
No test leaves the machine or patches an import: every test drives the reader through the file's `World` and the `fake_gh` fixture, a scripted `gh` executable behind the `GhTransport` injected into `GithubForgeReader` (`test/conftest.py:87-156`). No `mock.patch`, no `monkeypatch.setattr`, no `MagicMock`.
Append to `src/vibey_tools/gh/test/test_forge_snapshot.py`:
- `test_repository_metadata_is_one_record_of_the_repository_object` —
  `capture(classes=["repository-metadata"])`: one record, `native_id == "42"`,
  `native_class == "repository"`, `payload == world.repository`, and
  `fake_gh.calls() == [f"api repos/{REPO}"]`.
- `test_a_temporary_clone_token_is_redacted_and_the_redaction_shows` — set
  `world.repository["temp_clone_token"] = "AAAA1111"`; the record's
  `payload["temp_clone_token"] == REDACTED`, every other key equals `world.repository`'s, and
  `"AAAA1111" not in (snap / "repository-metadata.jsonl").read_text(encoding="utf-8")`.
- `test_a_repository_the_token_cannot_read_is_a_named_could_not_look` — script
  `answers[f"api repos/{REPO}"] = {"err": "HTTP 404: Not Found\n", "code": 1}`: the entry is
  `could-not-look` with `problem == f"`gh api repos/{REPO}` failed: HTTP 404: Not Found"`, and
  `repository-metadata.jsonl` does not exist.
- `test_a_repository_answer_that_is_not_an_object_is_could_not_look` — answer
  `{"out": json.dumps([1, 2])}`: `problem == f"`api repos/{REPO}` did not answer with a JSON object"`.
- `test_commit_comments_are_walked_whole_and_written_only_when_changed` —
  `capture(classes=["commit-comment"])` twice: the second has `(observed, appended,
  unchanged) == (1, 0, 1)`; append `{**world.commit_comments[0], "id": 4002, "body": "And
  this one?"}`, re-script, capture again: `(2, 1, 1)`; `World.listing(world.path("commit-comment"))`
  is in `fake_gh.calls()`.
- `test_a_declared_redaction_replaces_only_values_that_are_there` —
  `payload = {"a": {"b": "x", "k": 1}, "c": None, "t": "tok"}`;
  `GithubForgeReader._redacted(payload, ("a.b", "c", "t", "d.e", "t.z"))` equals
  `{"a": {"b": REDACTED, "k": 1}, "c": None, "t": REDACTED}`, and `payload` still equals
  `{"a": {"b": "x", "k": 1}, "c": None, "t": "tok"}` (not mutated).

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
- Rulesets and branch protection (`roadmap-145-capture-rules`), check runs, timelines,
  workflow runs, traffic (their own lanes, which follow this one).
- Comparing the captured repository object with `[repository_profile]` for drift (#145's
  `vibey-gh check` criterion, a later lane).
- `ForgeAdapterReader` and moving the snapshot onto `ForgeAdapterInterface.list_artifacts`
  (the gaps.md §L8 lane, which must carry `redact` when it takes these classes over).
- Any prose in `docs/forge-snapshot.md` beyond the four rows (for example "the nine classes
  above", `:277`): the docs wave. CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
