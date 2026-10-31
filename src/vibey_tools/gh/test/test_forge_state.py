# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh forge-state`: an object's state as of a moment, from a snapshot's own records (#1574).

Nothing here asks a forge. The snapshots are made by the real capture over the scripted
`fake_gh`, at two moments with one issue edited between them, so every answer is checked
against what the capture actually wrote.
"""

from __future__ import annotations

import json
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from test_forge_snapshot import REPO, Ticks, World, lines, snapshot

from vibey_gh.cli import main
from vibey_gh.forge_snapshot import (
    ForgeStateQuery,
    JsonlSnapshotStore,
    SnapshotStoreError,
    moment,
)
from vibey_gh.interfaces.forge_snapshot_interface import (
    STATE_BEFORE_FIRST,
    STATE_FOUND,
    STATE_UNKNOWN,
    SnapshotQueryInterface,
    StateAsOf,
)

FIRST = "2026-09-10T00:00:00Z"
SECOND = "2026-09-11T00:00:00Z"


@pytest.fixture
def history(fake_gh, tmp_path) -> Path:
    """A snapshot taken twice: issue 1 (native id 1001) was retitled in between."""
    world = World.seeded()
    fake_gh.script(world.answers())
    out = tmp_path / "snap"
    snapshot(out, clock=Ticks(FIRST)).capture()
    world.issues[0] = {
        **world.issues[0],
        "title": "Crash on start (macOS)",
        "updated_at": "2026-09-10T10:00:00Z",
    }
    fake_gh.script(world.answers())
    fake_gh.forget()
    snapshot(out, clock=Ticks(SECOND)).capture()
    return out


def query(root: Path) -> ForgeStateQuery:
    return ForgeStateQuery(JsonlSnapshotStore(root, forge="github", repository=REPO))


def title(found: StateAsOf) -> str:
    assert found.record is not None
    return str(found.record["payload"]["title"])


def moments(root: Path) -> tuple[str, str]:
    versions = [r for r in lines(root / "issue.jsonl") if r["native_id"] == "1001"]
    assert len(versions) == 2
    return versions[0]["captured_at"], versions[1]["captured_at"]


def test_the_query_satisfies_its_declared_seam(history):
    assert isinstance(query(history), SnapshotQueryInterface)


def test_between_two_captures_it_is_the_earlier_state(history):
    first, second = moments(history)
    found = query(history).state("issue", "1001", "2026-09-10T12:00:00Z")
    assert (found.status, title(found)) == (STATE_FOUND, "Crash on start")
    assert found.record is not None and found.record["captured_at"] == first < second
    assert found.native_id == "1001"


def test_after_the_last_record_it_is_the_latest_state(history):
    found = query(history).state("issue", "1001", "2030-01-01")
    assert (found.status, title(found)) == (STATE_FOUND, "Crash on start (macOS)")


def test_at_the_exact_moment_of_a_record_that_record_counts(history):
    first, second = moments(history)
    assert title(query(history).state("issue", "1001", first)) == "Crash on start"
    assert title(query(history).state("issue", "1001", second)) == "Crash on start (macOS)"


def test_before_the_first_record_is_not_absent_and_not_deleted(history):
    found = query(history).state("issue", "1001", "2020-01-01T00:00:00Z")
    assert found.status == STATE_BEFORE_FIRST
    assert found.record is None and found.native_id == "1001"


def test_an_object_never_recorded_is_unknown_not_deleted(history):
    found = query(history).state("issue", "999999", "2030-01-01")
    assert found.status == STATE_UNKNOWN and found.record is None
    assert query(history).state("label", "no-such-id", "2030-01-01").status == STATE_UNKNOWN


def test_a_moment_is_compared_as_a_moment_not_as_a_string(history):
    # The same instant written with another offset selects the same record, and one second
    # earlier selects none, though the strings would sort the other way round.
    first, _ = moments(history)
    instant = moment(first)
    plus_two = instant.astimezone(timezone(timedelta(hours=2)))
    found = query(history).state("issue", "1001", plus_two.isoformat())
    assert found.status == STATE_FOUND and found.record is not None
    assert found.record["captured_at"] == first
    earlier = (plus_two - timedelta(seconds=1)).isoformat()
    assert query(history).state("issue", "1001", earlier).status == STATE_BEFORE_FIRST


def test_it_reports_when_the_snapshot_was_last_captured(history, tmp_path):
    found = query(history).state("issue", "1001", "2030-01-01")
    manifest = json.loads((history / "manifest.json").read_text(encoding="utf-8"))
    assert found.last_capture == manifest["captured_at"] != FIRST
    bare = JsonlSnapshotStore(tmp_path / "empty", forge="github", repository=REPO)
    assert ForgeStateQuery(bare).state("issue", "1", "2030-01-01") == StateAsOf(STATE_UNKNOWN, "1")


def test_equal_captured_at_resolves_to_the_later_line(tmp_path):
    store = JsonlSnapshotStore(tmp_path, forge="github", repository=REPO)
    stamp = "2026-09-10T00:00:00Z"
    store.append("label", "label", stamp, [("7", {"name": "old"})])
    store.append("label", "label", stamp, [("7", {"name": "new"})])
    found = ForgeStateQuery(store).state("label", "7", stamp)
    assert found.record is not None and found.record["payload"] == {"name": "new"}


def test_lookup_by_number_agrees_with_lookup_by_native_id(history):
    by_number = query(history).issue(1, "2026-09-10T12:00:00Z")
    by_id = query(history).state("issue", "1001", "2026-09-10T12:00:00Z")
    assert by_number == by_id and title(by_number) == "Crash on start"


def test_a_pull_requests_issue_side_is_found_and_marked_by_its_payload(history):
    found = query(history).issue(2, "2030-01-01")
    assert found.status == STATE_FOUND and found.record is not None
    assert "pull_request" in found.record["payload"]


def test_an_issue_number_nobody_recorded_is_unknown(history):
    found = query(history).issue(404, "2030-01-01")
    assert found.status == STATE_UNKNOWN and found.native_id == ""
    assert found.last_capture is not None


def test_one_number_under_two_native_ids_is_refused_not_guessed(tmp_path):
    store = JsonlSnapshotStore(tmp_path, forge="github", repository=REPO)
    stamp = "2026-09-10T00:00:00Z"
    store.append("issue", "issue", stamp, [("1", {"number": 5}), ("2", {"number": 5})])
    with pytest.raises(SnapshotStoreError, match="several native ids: 1, 2"):
        ForgeStateQuery(store).issue(5, "2030-01-01")


def test_a_tampered_class_file_is_refused_before_answering(history):
    path = history / "issue.jsonl"
    original = path.read_text(encoding="utf-8").splitlines()
    forged = json.loads(original[0])
    forged["payload"]["title"] = "forged"
    original[0] = json.dumps(forged, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(original) + "\n", encoding="utf-8")
    with pytest.raises(SnapshotStoreError):
        query(history).state("issue", "1001", "2030-01-01")
    with pytest.raises(SnapshotStoreError):
        query(history).issue(1, "2030-01-01")


def test_a_bad_moment_or_class_is_the_callers_mistake(history):
    with pytest.raises(ValueError):
        query(history).state("issue", "1001", "last tuesday")
    with pytest.raises(ValueError):
        query(history).issue(1, "last tuesday")
    with pytest.raises(ValueError, match="unknown artifact class"):
        query(history).state("nonsense", "1", "2030-01-01")


def test_the_store_reads_records_in_file_order_and_nothing_for_a_missing_class(history):
    store = JsonlSnapshotStore(history, forge="github", repository=REPO)
    assert [r["payload"]["title"] for r in store.records("issue") if r["native_id"] == "1001"] == [
        "Crash on start",
        "Crash on start (macOS)",
    ]
    assert (
        list(
            JsonlSnapshotStore(history / "nowhere", forge="github", repository=REPO).records("tag")
        )
        == []
    )


# ----------------------------------------------------------------------------- the command


def state(history: Path, *argv: str) -> int:
    return main(["forge-state", str(history), *argv])


def test_the_command_prints_the_payload_and_the_facts_and_exits_zero(history, capsys):
    assert state(history, "--issue", "1", "--as-of", "2026-09-10T12:00:00Z") == 0
    printed = capsys.readouterr()
    assert json.loads(printed.out)["title"] == "Crash on start"
    assert "issue 1001 as of 2026-09-10T12:00:00Z: captured_at 2026-09-10" in printed.err
    assert "seal " in printed.err and "latest capture began 2026-09-11" in printed.err


def test_the_command_finds_by_class_and_native_id(history, capsys):
    assert state(history, "--class", "issue", "--native-id", "1001", "--as-of", "2030-01-01") == 0
    assert json.loads(capsys.readouterr().out)["title"] == "Crash on start (macOS)"


def test_the_command_exits_one_and_says_it_does_not_know_that_it_never_existed(history, capsys):
    assert state(history, "--issue", "1", "--as-of", "2020-01-01") == 1
    err = capsys.readouterr().err
    assert (
        "recorded, but first at a later moment" in err and "nothing about whether it existed" in err
    )
    assert state(history, "--issue", "404", "--as-of", "2030-01-01") == 1
    assert "is not in this snapshot" in capsys.readouterr().err


def test_the_command_exits_two_for_a_bad_moment_or_a_missing_native_id(history, capsys):
    assert state(history, "--issue", "1", "--as-of", "yesterday-ish") == 2
    assert state(history, "--class", "issue", "--as-of", "2030-01-01") == 2
    assert "--class needs --native-id" in capsys.readouterr().err
    assert state(history, "--class", "nonsense", "--native-id", "1", "--as-of", "2030-01-01") == 2


def test_the_command_exits_one_on_a_directory_with_no_manifest_or_a_damaged_file(
    history, tmp_path, capsys
):
    assert (
        main(["forge-state", str(tmp_path / "nothing"), "--issue", "1", "--as-of", "2030-01-01"])
        == 1
    )
    assert "holds no readable snapshot manifest" in capsys.readouterr().err
    path = history / "issue.jsonl"
    path.write_text(path.read_text(encoding="utf-8").replace("Crash", "Smash", 1), encoding="utf-8")
    assert state(history, "--issue", "1", "--as-of", "2030-01-01") == 1


def test_the_command_needs_one_way_to_name_the_object(history):
    with pytest.raises(SystemExit) as raised:
        state(history, "--as-of", "2030-01-01")
    assert raised.value.code == 2
    with pytest.raises(SystemExit) as raised:
        state(history, "--issue", "1", "--class", "issue", "--as-of", "2030-01-01")
    assert raised.value.code == 2


def test_the_command_is_read_only(history):
    before = {p.name: p.read_bytes() for p in history.iterdir()}
    state(history, "--issue", "1", "--as-of", "2030-01-01")
    assert {p.name: p.read_bytes() for p in history.iterdir()} == before
