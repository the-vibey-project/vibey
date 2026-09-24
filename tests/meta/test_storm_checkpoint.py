# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A long measurement keeps each step as it finishes, and a restart resumes (10.h, ADR-0057).

The concurrency sweep lost on 2026-09-24 held its rows in memory and printed them once, at
the end; the llama-server benchmark truncated its results file every time it started. Either
way one reboot, one kill, or one crash costs the whole run. `tools/storm_checkpoint.py`'s
`StepJournal` is the fix both now use: one append-only JSON line per finished step, flushed
and fsynced before the next step starts, and a restart that asks the journal what is already
done and runs only the rest.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools"
BENCH = TOOLS.parent / "bench"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"missing: {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checkpoint = _load("storm_checkpoint", TOOLS / "storm_checkpoint.py")
StepJournal = checkpoint.StepJournal


def test_a_recorded_step_is_on_disk_before_record_returns(tmp_path: Path) -> None:
    journal = StepJournal(tmp_path / "sweep.jsonl")
    journal.record("A", {"tokens_per_second": 41.2})
    # Read by a second process, as a restart would: nothing may be sitting in a buffer.
    probe = "import json,sys; print(json.loads(open(sys.argv[1]).readline())['step'])"
    done = subprocess.run(
        [sys.executable, "-c", probe, str(tmp_path / "sweep.jsonl")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert done.stdout.strip() == "A"


def test_a_restart_runs_only_the_steps_not_yet_recorded(tmp_path: Path) -> None:
    path = tmp_path / "sweep.jsonl"
    first = StepJournal(path)
    first.record("A", {"fidelity": "8/8"})
    first.record("B", {"fidelity": "8/8"})
    # The process dies here. A new one starts over the same file.
    again = StepJournal(path)
    assert again.pending(["A", "B", "C", "D"]) == ["C", "D"]
    assert again.done()["B"]["fidelity"] == "8/8"


def test_the_journal_is_appended_to_never_rewritten(tmp_path: Path) -> None:
    path = tmp_path / "sweep.jsonl"
    StepJournal(path).record("A", {"n": 1})
    before = path.read_bytes()
    StepJournal(path).record("B", {"n": 2})
    assert path.read_bytes().startswith(before)


def test_a_step_recorded_twice_reads_as_its_latest_row(tmp_path: Path) -> None:
    journal = StepJournal(tmp_path / "sweep.jsonl")
    journal.record("A", {"n": 1})
    journal.record("A", {"n": 2})
    assert journal.done()["A"]["n"] == 2


def test_a_line_torn_by_a_crash_is_skipped_and_counted(tmp_path: Path) -> None:
    """A kill mid-write leaves half a line. It is not a finished step, and it must not glue
    itself to the next record and take that one down with it."""
    path = tmp_path / "sweep.jsonl"
    StepJournal(path).record("A", {"n": 1})
    with path.open("a", encoding="utf-8") as torn:
        torn.write('{"step": "B", "n": ')
    journal = StepJournal(path)
    assert journal.pending(["A", "B"]) == ["B"]
    assert journal.torn() == 1
    journal.record("B", {"n": 2})
    assert StepJournal(path).done()["B"]["n"] == 2
    assert StepJournal(path).torn() == 1


def test_every_row_carries_its_step_and_when_it_was_recorded(tmp_path: Path) -> None:
    path = tmp_path / "sweep.jsonl"
    StepJournal(path).record("C", {"wired_gb": 14.1})
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["step"] == "C"
    assert row["wired_gb"] == 14.1
    assert row["recorded_at"].endswith("Z")


def test_a_row_may_not_overwrite_the_step_it_belongs_to(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        StepJournal(tmp_path / "j.jsonl").record("A", {"step": "B"})


def test_the_interface_declared_beside_it_is_honoured(tmp_path: Path) -> None:
    declared = _load(
        "storm_checkpoint_interface", TOOLS / "interfaces/storm_checkpoint_interface.py"
    )
    assert isinstance(StepJournal(tmp_path / "j.jsonl"), declared.StepJournalInterface)


# --- the measurements that were lost now use it --------------------------------------------


def test_the_host_sweep_journals_each_configuration_as_it_finishes() -> None:
    source = (BENCH / "host-sweep.py").read_text(encoding="utf-8")
    assert "StepJournal" in source
    assert ".pending(" in source and ".record(" in source


def test_the_benchmark_runner_no_longer_truncates_its_results() -> None:
    source = (BENCH / "bench-run.sh").read_text(encoding="utf-8")
    assert ': > "$B/results.jsonl"' not in source, "a restart would erase every measurement"
    assert "skip" in source
