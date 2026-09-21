# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json

from opencodeloop.domain.model import RunResult, RunStatus
from opencodeloop.infrastructure.run_store import FileRunStore


def test_file_run_store_writes_append_only_events_and_terminal_snapshot(tmp_path) -> None:  # type: ignore[no-untyped-def]
    run_dir = tmp_path / ".opencodeloop" / "runs" / "run-1"
    store = FileRunStore()
    store.begin(run_dir, "run-1", tmp_path, "session-1")
    store.append_event(run_dir, {"event_type": "text_delta", "text": "hello"})
    store.finish(run_dir, RunResult(RunStatus.FINISHED, 0, "session-1"))

    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    events = (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    snapshot = json.loads((run_dir / "snapshots" / "latest.json").read_text(encoding="utf-8"))
    assert meta["status"] == "finished"
    assert snapshot["schema_version"] == 1
    assert meta["done_marker"] == "OPENCODELOOP_TASK_FULLY_COMPLETE"
    assert len(events) == 1
    assert json.loads(events[0])["text"] == "hello"
    assert snapshot == {key: meta[key] for key in snapshot}


def test_file_run_store_records_failure_without_done_marker(tmp_path) -> None:  # type: ignore[no-untyped-def]
    run_dir = tmp_path / "run-2"
    store = FileRunStore()
    store.begin(run_dir, "run-2", tmp_path, None)
    store.finish(run_dir, RunResult(RunStatus.FAILED, 7, detail="provider failed"))
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "failed"
    assert meta["returncode"] == 7
    assert meta["done_marker"] is None
    assert meta["detail"] == "provider failed"
