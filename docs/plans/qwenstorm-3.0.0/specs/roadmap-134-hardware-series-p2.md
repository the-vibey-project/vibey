## Title
refactor(gh): the fit journal becomes a declared class — one writer and one reader of its lines, which the fit loop and the hardware series share

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, "Proposed child issues" 4: "keep a rolling series
in the fit journal"). The fit journal is the JSONL file at `$VIBEY_GH_FIT_JOURNAL`, else
`~/.local/state/vibey-gh/fit.jsonl` (`src/vibey_tools/gh/vibey_gh/fitloop.py:64-65`, `:173-178`).
Today its only writer is a private method of `FitLoop` (`FitLoop._write`, `fitloop.py:294-304`) and
its only reader is `recorded_observations` (`:74-110`), which reads one kind (`observation`). The
hardware series (`roadmap-134-hardware-series-p3`) must append and read back its own kind,
`hardware_sample`. Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`) forbids a second
writer of the same file: the capability gap is closed by teaching ours, so the write moves, whole,
into a class both callers use. 9.b (`doctrines.md:349`): that class has an interface beside it and
an in-memory fake from the first day. 7.c (`doctrines.md:82-91`): the journal stays append-only;
nothing here rewrites a line.

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **`FitJournal`** in `vibey_gh/fitloop.py`, inserted directly before `class FitLoop` (after
   `DEFAULT_WINDOW = 64`, `:115`), and added to `__all__` (`:57`) in sorted position:
   ```python
   class FitJournal(FitJournalInterface):
       """The fit journal on disk: one JSON object per line, appended and never rewritten.

       `FitLoop` writes its `observation` and `decision` entries through this, and the
       estimate's hardware series writes and reads its `hardware_sample` entries through it,
       so the file has one writer and one line format (sub-doctrine 10.e). `path=None` is a
       journal that keeps nothing, which is what `--no-journal` asks for.
       """

       def __init__(self, path: Path | None) -> None:
           self.path = path

       def append(self, entry: Mapping[str, object]) -> None:
           if self.path is None:
               return
           try:
               self.path.parent.mkdir(parents=True, exist_ok=True)
               with self.path.open("a", encoding="utf-8") as handle:
                   handle.write(json.dumps(dict(entry), sort_keys=True) + "\n")
           except OSError:
               # A journal that cannot be written must never take the admission down with
               # it. Losing the record is bad; refusing the work because of it is worse.
               pass

       def entries(self, kind: str, *, last: int | None = None) -> list[dict[str, Any]]:
           """Every entry of `kind`, oldest first -- or only the `last` of them. A missing,
           unreadable or partly corrupt journal yields what it can, as
           `recorded_observations` does."""
           if self.path is None:
               return []
           try:
               lines = self.path.read_text(encoding="utf-8").splitlines()
           except OSError:
               return []
           found: list[dict[str, Any]] = []
           for line in lines:
               try:
                   entry = json.loads(line)
               except json.JSONDecodeError:
                   continue
               if isinstance(entry, dict) and entry.get("kind") == kind:
                   found.append(entry)
           if last is None:
               return found
           return found[-last:] if last > 0 else []
   ```
   Imports: add `Any` (`from typing import Any`) and
   `from vibey_gh.interfaces.fit_journal_interface import FitJournalInterface`.
2. **`FitLoop._write`** (`:294-304`) keeps its name and signature; its body becomes exactly
   `FitJournal(self.journal).append(payload)` (the comment moves into `FitJournal.append` above).
   Every existing `FitLoop` behaviour and journal line is byte-identical: same keys, `sort_keys=True`,
   one line per entry.
3. **New interface `vibey_gh/interfaces/fit_journal_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`): a `runtime_checkable`
   `FitJournalInterface(Protocol)` declaring a read-only property `path -> Path | None` ("Where
   the journal lives, or `None` for one that keeps nothing"), `append(self, entry: Mapping[str, object]) -> None`
   ("Append one entry as one line; never raises, never rewrites") and
   `entries(self, kind: str, *, last: int | None = None) -> list[dict[str, Any]]` ("Every entry of
   `kind`, oldest first, or only the `last` of them; a damaged journal yields what it can"). It
   imports only the standard library (it must not import `vibey_gh.fitloop`, which
   `.importlinter`'s `vibey-gh-interfaces-declare-only` forbids).
4. **Fake** appended to `test/fakes.py`:
   ```python
   class InMemoryFitJournal:
       """A fit journal held in a list, keeping every entry it is given (#134)."""

       def __init__(self, path: Path | None = None) -> None:
           self.path = path
           self.lines: list[dict[str, Any]] = []

       def append(self, entry: Mapping[str, object]) -> None:
           self.lines.append(dict(entry))

       def entries(self, kind: str, *, last: int | None = None) -> list[dict[str, Any]]:
           found = [dict(line) for line in self.lines if line.get("kind") == kind]
           if last is None:
               return found
           return found[-last:] if last > 0 else []
   ```
   Register `FitJournalInterface` → `InMemoryFitJournal` in `test/test_port_parity.py` the way
   `ScriptedGitRunner` is registered.

## Where to change
- New: `vibey_gh/interfaces/fit_journal_interface.py`.
- Edit with `edit_file` (`fitloop.py` is 326 lines): `vibey_gh/fitloop.py` (behaviours 1-2).
- Tests: append to `test/test_fitloop.py` (add `FitJournal` to its
  `from vibey_gh.fitloop import DEFAULT_JOURNAL, JOURNAL_ENV, FitLoop` line, `:12`, and
  `from vibey_gh.interfaces.fit_journal_interface import FitJournalInterface` to the top import
  block); append to `test/fakes.py` and `test/test_fakes.py`; one entry in `test/test_port_parity.py`.

## Acceptance criteria
- [ ] Every existing `test/test_fitloop.py`, `test/test_fit.py` and `test/test_operation_estimate.py`
      test passes unmodified: the journal's lines are byte-identical.
- [ ] `grep -n "open(\"a\"" vibey_gh/fitloop.py` finds exactly one writer, inside `FitJournal.append`.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
Append to `test/test_fitloop.py`:
- `test_the_journal_declares_its_seam` — `isinstance(FitJournal(None), FitJournalInterface)`.
- `test_the_journal_appends_one_sorted_line_per_entry` — `FitJournal(tmp_path / "deep" / "fit.jsonl")`
  appends `{"kind": "hardware_sample", "b": 2, "a": 1}`; the file text is exactly
  `'{"a": 1, "b": 2, "kind": "hardware_sample"}\n'` (the parent directory was created).
- `test_the_journal_reads_back_one_kind_and_skips_damage` — a file holding, one per line, an
  `observation`, three `hardware_sample` entries (`"n": 1`, `2`, `3`), the text `not json` and
  `[1, 2]`: `entries("hardware_sample")` is the three in order; `last=2` gives `n` 2 and 3;
  `last=0` gives `[]`; `entries("decision")` gives `[]`.
- `test_a_journal_that_cannot_be_read_or_written_never_raises` — `FitJournal(tmp_path)` (a
  directory): `append({"kind": "x"})` returns `None` and `entries("x") == []`.
- `test_no_journal_keeps_nothing` — `FitJournal(None).append({"kind": "x"})` then
  `FitJournal(None).entries("x") == []`.
- `test_the_fit_loop_writes_through_the_journal` — `FitLoop("m", journal=tmp_path / "j.jsonl").observe(1024, 1.5, 1)`;
  `FitJournal(tmp_path / "j.jsonl").entries("observation")[0]["elapsed_s"] == 1.5`, and
  `fitloop.recorded_observations(tmp_path / "j.jsonl", "m")` still returns that one observation.

Append to `test/test_fakes.py`:
- `test_fit_journal_fake_keeps_entries_and_filters_by_kind` — two kinds appended; `entries` of one
  kind, with and without `last`, and `last=0` is `[]`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_fitloop.py test/test_fit.py test/test_operation_estimate.py test/test_fakes.py test/test_port_parity.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- `recorded_observations` (it keeps its own tolerant reader for the `observation` kind; nothing
  about it changes), the hardware series itself (`roadmap-134-hardware-series-p3`), `vibey_gh/cli.py`.
- Journal rotation or size limits.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
