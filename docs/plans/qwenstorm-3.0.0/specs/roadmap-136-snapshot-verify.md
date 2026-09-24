## Title
feat(gh): `forge-snapshot --verify DIR` checks every seal, link and manifest head, and names the first break in each file

## Why
Issue #136 (rewrite: `issue-audit/updates/136.md`, "Proposed child issues" 1; slice S2 of the
roadmap in `src/vibey_tools/gh/docs/forge-snapshot.md:324-325`) asks for a verify walk. A
snapshot is sealed so that a removed, reordered or edited line is detectable, but nothing
in the tool detects it:

- The store checks a chain only as a side effect of appending, and refuses by raising on the
  first bad line (`src/vibey_tools/gh/vibey_gh/forge_snapshot.py:429-496`, `_load`/`_parse`).
  It never compares a chain's head with the manifest's (`manifest()` at `:360-374` reads
  only `schema`, `forge` and `repository`).
- The docs promise the walk as "the next slice" (`docs/forge-snapshot.md:230-231`), and the
  only independent chain check is a test helper (`test/test_forge_snapshot.py:378-393`).
- The CLI has no verify mode: `--out` is required (`vibey_gh/cli.py:1564`) and
  `_forge_snapshot` (`cli.py:573-634`) always builds a reader and asks the forge.

Ratified law: 7.c, the ledger holds what happened and "stays append-only"
(`src/vibey_tools/gh/docs/doctrines.md:82-91`); 10.f, a claim is "tied to observable ...
evidence" and a check that did not complete is unknown, never success (`doctrines.md:419`);
9.b, the method is declared on the interface beside the class (`doctrines.md:349`). The walk
reads bytes on disk only: no forge, no network, and no host-specific code, so the suite runs
unchanged on Arch Linux and macOS (8.h, `doctrines.md:326-333`).

## Required behaviour
1. `vibey_gh/interfaces/forge_snapshot_interface.py` gains, directly after `ChainHeadInterface`
   (`:76-82`):
   ```python
   @dataclass(frozen=True)
   class ChainVerdict:
       """What a verify walk found in one file of a snapshot.

       `records` counts the lines that verified, in order, before the first break, and `head`
       is the seal of the last of them (`None` when none did). `problem` is empty exactly
       when the whole file verified and agrees with the manifest; otherwise it names the
       first break, and the walk of that file stopped there.
       """

       file: str
       records: int
       head: str | None
       problem: str = ""


   @runtime_checkable
   class ChainVerdictInterface(Protocol):
       @property
       def file(self) -> str: ...

       @property
       def records(self) -> int: ...

       @property
       def head(self) -> str | None: ...

       @property
       def problem(self) -> str: ...
   ```
   and `ForgeSnapshotInterface` (`:170-187`) gains, after `capture`:
   ```python
       def verify(self, directory: Path) -> tuple[ChainVerdict, ...]:
           """Check a snapshot on disk against itself, asking the forge nothing.

           One verdict per class this snapshot supports, in table order, preceded by one for
           `manifest.json` only when the manifest is missing or unreadable. Never raises for
           anything on disk: a missing or damaged file is a verdict with a problem.
           """
           ...
   ```
2. `vibey_gh/interfaces/__init__.py`: add `ChainVerdictInterface` to the
   `from vibey_gh.interfaces.forge_snapshot_interface import (...)` block (`:110-114`) and to
   `__all__`, directly after `"ChainHeadInterface",` (`:134`).
3. `vibey_gh/forge_snapshot.py`: import `ChainVerdict` in the interface import block (`:42-50`,
   alphabetical: after `ChainHead`). `ForgeSnapshot` (`:506`) gains four static methods,
   placed directly above `    @staticmethod\n    def _select(` (`:594-595`). `verify` is static
   because it needs neither a reader nor a store: it trusts nothing but the bytes in
   `directory`, the way the documented stdlib check does (`docs/forge-snapshot.md:216-228`),
   so a store that wrote a broken chain cannot also vouch for it. Say that in its docstring.
   ```python
       @staticmethod
       def verify(directory: Path) -> tuple[ChainVerdict, ...]:
           entries, problem = ForgeSnapshot._manifest_entries(directory)
           verdicts = [ChainVerdict(MANIFEST_NAME, 0, None, problem)] if problem else []
           for spec in CLASSES:
               verdicts.append(
                   ForgeSnapshot._verify_file(directory, spec.name, entries.get(spec.name))
               )
           return tuple(verdicts)

       @staticmethod
       def _manifest_entries(directory: Path) -> tuple[Mapping[str, Any], str]:
           path = directory / MANIFEST_NAME
           if not path.is_file():
               return {}, f"there is no {MANIFEST_NAME}, so no chain head could be checked against it"
           try:
               value = json.loads(path.read_text(encoding="utf-8"))
           except ValueError:
               value = None
           classes = (
               value.get("classes")
               if isinstance(value, dict) and value.get("schema") == MANIFEST_SCHEMA
               else None
           )
           if not isinstance(classes, dict):
               return {}, f"{MANIFEST_NAME} is not a {MANIFEST_SCHEMA} manifest"
           return classes, ""

       @staticmethod
       def _verify_file(directory: Path, name: str, entry: object) -> ChainVerdict:
           path = directory / f"{name}.jsonl"
           records = 0
           head: str | None = None
           if path.is_file():
               with path.open("rb") as handle:
                   for number, line in enumerate(handle, start=1):
                       reason, seal = ForgeSnapshot._first_break(line, name, head)
                       if reason:
                           return ChainVerdict(path.name, records, head, f"line {number} {reason}")
                       records, head = records + 1, seal
           if isinstance(entry, dict) and (entry.get("records"), entry.get("head")) != (
               records,
               head,
           ):
               return ChainVerdict(
                   path.name,
                   records,
                   head,
                   f"{MANIFEST_NAME} records {entry.get('records')} record(s) ending at"
                   f" {entry.get('head') or 'none'}; the file holds {records} ending at"
                   f" {head or 'none'}",
               )
           return ChainVerdict(path.name, records, head)

       @staticmethod
       def _first_break(line: bytes, name: str, previous: str | None) -> tuple[str, str]:
           """Why `line` breaks its chain (empty when it does not), and its seal."""
           try:
               record = json.loads(line)
           except ValueError:
               record = None
           if (
               not isinstance(record, dict)
               or record.get("schema") != RECORD_SCHEMA
               or record.get("class") != name
               or not isinstance(record.get("sha256"), str)
               or not isinstance(record.get("payload_sha256"), str)
               or "payload" not in record
           ):
               return f"is not a {RECORD_SCHEMA} {name} record", ""
           if canonical_bytes(record) != line.removesuffix(b"\n"):
               return "is not in canonical form", ""
           seal: str = record["sha256"]
           body = {key: value for key, value in record.items() if key != "sha256"}
           if digest(body) != seal:
               return "has an invalid sha256", ""
           if digest(record["payload"]) != record["payload_sha256"]:
               return "has an invalid payload_sha256", ""
           if record.get("prev") != previous:
               return "does not link to the preceding record", ""
           return "", seal
   ```
   The checks run in the store's own order (`_parse`, `:466-495`), and every reason is the
   store's wording, so the two never disagree about a line.
4. The CLI (`vibey_gh/cli.py`):
   - In the parser (`:1564`) replace
     `    fs.add_argument("--out", required=True, help="the snapshot directory; created if missing")`
     with a required mutually exclusive group:
     ```python
         fs_target = fs.add_mutually_exclusive_group(required=True)
         fs_target.add_argument("--out", help="the snapshot directory; created if missing")
         fs_target.add_argument(
             "--verify",
             metavar="DIR",
             help="check every seal, link and manifest head of the snapshot in DIR;"
             " asks the forge nothing",
         )
     ```
   - In `_forge_snapshot`, directly after the line `    prefix = "vibey-gh forge-snapshot:"`
     (`:593`), insert:
     ```python
         if args.verify is not None:
             directory = Path(args.verify)
             verdicts = ForgeSnapshot.verify(directory)
             print(f"{prefix} verifying {directory}")
             for verdict in verdicts:
                 if verdict.problem:
                     print(f"  {verdict.file}: BROKEN: {verdict.problem}", file=sys.stderr)
                 else:
                     head = (verdict.head or "none")[:12]
                     print(f"  {verdict.file}: {verdict.records} record(s) verified, head {head}")
             broken = sum(1 for verdict in verdicts if verdict.problem)
             if broken:
                 print(f"{prefix} {broken} file(s) did not verify in {directory}", file=sys.stderr)
                 return 1
             print(f"{prefix} every chain and manifest head in {directory} verified")
             return 0
     ```
     Add one sentence to the function's docstring: "`--verify DIR` checks an existing
     snapshot instead, reading nothing from the forge, and exits 0 when every file verified
     and 1 when any did not."
   - Verify never resolves a repository and never runs `gh`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/interfaces/forge_snapshot_interface.py` (behaviour 1).
- `src/vibey_tools/gh/vibey_gh/interfaces/__init__.py` (behaviour 2; two one-line inserts).
- `src/vibey_tools/gh/vibey_gh/forge_snapshot.py` (behaviour 3).
- `src/vibey_tools/gh/vibey_gh/cli.py` (behaviour 4).
- `src/vibey_tools/gh/test/test_forge_snapshot.py`: add `ChainVerdict` and
  `ChainVerdictInterface` to the `from vibey_gh.interfaces.forge_snapshot_interface import (`
  block (`:47-53`), then append the tests below at the end of the file. Change no existing test.
- Every file keeps its first-line provenance header. All five files are long: use `edit_file`,
  never `write_file`. Then run `python -m black vibey_gh test` and `isort vibey_gh test` from
  `src/vibey_tools/gh` to format.

## Acceptance criteria
- [ ] `ForgeSnapshot.verify(DIR)` on a freshly captured snapshot returns one verdict per class,
      every `problem == ""`, and each `(records, head)` equals the manifest's entry.
- [ ] A removed line, two swapped lines, an edited payload (resealed or not), a line that is not
      a record, a non-canonical line and a manifest head that differs from the file are each
      named with the exact message of Required behaviour 3.
- [ ] A missing or unreadable `manifest.json` is its own leading verdict; the files are still walked.
- [ ] `vibey-gh forge-snapshot --verify DIR` exits 0 on an intact snapshot and 1 on a broken one,
      prints one line per file, and makes no `gh` call.
- [ ] `--out` and `--verify` are one or the other (argparse exits 2 for both or neither).
- [ ] `cd src/vibey_tools/gh && python -m pytest -q` passes with the 100% line and branch floor
      (`pyproject.toml:64-70`).

## Tests to write first (TDD)
No test leaves the machine or patches an import: every test drives the reader through the file's `World` and the `fake_gh` fixture, a scripted `gh` executable behind the `GhTransport` injected into `GithubForgeReader` (`test/conftest.py:87-156`). No `mock.patch`, no `monkeypatch.setattr`, no `MagicMock`.
Append to `src/vibey_tools/gh/test/test_forge_snapshot.py` (the `fake_gh`, `snap`, `World`,
`snapshot`, `NAMES` fixtures and helpers already in the file; `json`, `pytest`, `digest`,
`canonical_bytes`, `JsonlSnapshotStore`, `SnapshotStoreError`, `MANIFEST_NAME`, `main` are
already imported). Add this helper once, above the tests:
```python
def three_labels(fake_gh, snap: Path) -> tuple[dict[str, Any], list[bytes]]:
    """Capture three labels into `snap`; return the manifest and the file's lines."""
    world = World.seeded()
    world.labels.append({**world.labels[0], "id": 103, "name": "third"})
    fake_gh.script(world.answers())
    manifest = snapshot(snap).capture(classes=["label"])
    return manifest, (snap / "label.jsonl").read_bytes().splitlines(keepends=True)


def by_file(verdicts: tuple[ChainVerdict, ...]) -> dict[str, ChainVerdict]:
    return {verdict.file: verdict for verdict in verdicts}
```
- `test_verify_passes_an_intact_snapshot` — full capture of `World.seeded()`, then
  `fake_gh.forget()`; `ForgeSnapshot.verify(snap)`: the files are
  `[f"{n}.jsonl" for n in NAMES]` in order, every `problem == ""`, every
  `(records, head)` equals `manifest["classes"][name]`'s, `isinstance(verdicts[0],
  ChainVerdictInterface)`, and `fake_gh.calls() == []`.
- `test_verify_names_a_removed_line` — `three_labels`, write lines `[0, 2]`: the label verdict
  is `ChainVerdict("label.jsonl", 1, json.loads(lines[0])["sha256"], "line 2 does not link to
  the preceding record")`; every other verdict has `problem == ""`.
- `test_verify_names_two_swapped_lines` — write lines `[1, 0, 2]`: label verdict
  `ChainVerdict("label.jsonl", 0, None, "line 1 does not link to the preceding record")`.
- `test_verify_names_an_edited_payload` — parametrized `("reseal", "reason")` over
  `(False, "line 2 has an invalid sha256")` and `(True, "line 2 has an invalid payload_sha256")`:
  load line 2, set `payload["name"] = "forged"`; when `reseal`, `pop("sha256")` and set
  `record["sha256"] = digest(record)`; write every line back with `canonical_bytes(...) + b"\n"`.
  The label verdict's `problem == reason` and `records == 1`.
- `test_verify_names_a_manifest_head_that_is_not_the_files` — after `three_labels`, set
  `manifest["classes"]["label"]["head"] = "0" * 64` and rewrite `manifest.json`; the label
  problem is `f"manifest.json records 3 record(s) ending at {'0' * 64}; the file holds 3 ending
  at {head}"` where `head` is the original manifest head.
- `test_verify_reports_a_missing_or_unreadable_manifest` — parametrized over deleting
  `manifest.json` (message `"there is no manifest.json, so no chain head could be checked
  against it"`) and writing `"{"` to it (message `"manifest.json is not a
  vibey.forge-manifest/1 manifest"`): `verdicts[0] == ChainVerdict("manifest.json", 0, None,
  message)`, `len(verdicts) == len(NAMES) + 1`, and the label verdict has `problem == ""` and
  `records == 3`.
- `test_verify_names_a_line_that_is_not_a_record_or_not_canonical` — parametrized:
  append `b"{not json\n"` → `"line 4 is not a vibey.forge-record/1 label record"`, records 3;
  append `b"[]\n"` → the same message; replace line 2 by
  `lines[1].removesuffix(b"\n") + b" \n"` → `"line 2 is not in canonical form"`, records 1.
- `test_verify_agrees_with_the_store_on_every_tampered_chain` — parametrized over
  `("canonical", "record", "payload", "previous")`, tampering line 2 exactly as
  `test_the_store_refuses_a_tampered_chain_before_reading_the_forge` does (`:508-525`): the
  store's `chain("label")` raises `SnapshotStoreError`, and the label verdict's problem
  starts with `"line 2 "`.
- `test_the_command_verifies_a_snapshot_and_exits_zero` — full capture, `fake_gh.forget()`,
  `main(["forge-snapshot", "--verify", str(snap)]) == 0`; stdout contains
  `f"vibey-gh forge-snapshot: verifying {snap}"`, `"  label.jsonl: 2 record(s) verified, head "`
  and `f"vibey-gh forge-snapshot: every chain and manifest head in {snap} verified"`; stderr is
  empty; `fake_gh.calls() == []`.
- `test_the_command_exits_one_and_names_each_broken_file` — `three_labels`, write lines
  `[0, 2]`; `main([... "--verify", str(snap)]) == 1`; stderr contains
  `"  label.jsonl: BROKEN: line 2 does not link to the preceding record"` and
  `f"vibey-gh forge-snapshot: 1 file(s) did not verify in {snap}"`.
- `test_verify_and_out_are_one_or_the_other` — `pytest.raises(SystemExit)` with `.value.code
  == 2` for `main(["forge-snapshot", "--out", str(snap), "--verify", str(snap)])` and for
  `main(["forge-snapshot"])`.

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
git diff --stat              # only the five files above
```

## Out of scope
- Every capture class (lanes `roadmap-136-capture-*`, `roadmap-145-capture-*`), which follow
  this lane and extend `CLASSES`; `verify` walks whatever `CLASSES` holds.
- `GithubForgeReader`, `JsonlSnapshotStore` and `ForgeAdapterReader`; moving the snapshot onto
  `ForgeAdapterInterface.list_artifacts` (the gaps.md §L8 lane).
- `docs/forge-snapshot.md` ("A `--verify` walk ... is the next slice", `:230-231`; the S2 line
  `:324-325`) and every other doc: the docs wave owns them. CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
