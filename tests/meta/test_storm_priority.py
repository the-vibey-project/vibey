# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The storm's priority lane: push an item and have it run next (ADR-0054).

The operator asked for one thing -- "push a priority item into the queue and have that run
next so that it doesn't have to wait for the other jobs in front of it" -- and ruled on who
may: the operator, and automation the operator declares in config. A GitHub label or an
issue from anyone else can never jump the queue (12.j). ADR-0054 is the contract both of
vibey's queues keep; this file holds the storm's queue to it:

1. "next" means next after whatever is running -- a running lane is never interrupted;
2. priority items run first, in the order they were pushed;
3. dependencies are respected and pulled forward, transitively, in dependency order;
4. only the operator or a declared source may push, bump or un-bump, and admission
   (storm_trust, 12.j) still judges a pushed issue at the moment its lane starts;
5. every push, bump, un-bump and refusal is one appended line, and replaying the log
   rebuilds the order;
6. un-bump returns an item to its queue.txt position;
7. pushing an item queue.txt does not yet carry appends it, with its dependencies.

The shell and the CLI must agree on what runs next, so the last group runs the REAL
`storm-queue.sh` in a throwaway storm whose model runner, admission and setup are stubs,
and compares the order it ran lanes in with the order `storm-priority.py list` predicted.

The tools are addressed by path for the reason `test_storm_check_parser.py` gives.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec and spec.loader, f"the storm tool is missing: {TOOLS / filename}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# storm_paths first, so the copy storm_queue imports by name is this one.
storm_paths = _load("storm_paths", "storm_paths.py")
storm_queue = _load("storm_queue", "storm_queue.py")

QUEUE = "a 1\nb 2\nc 3\nd 4 b\ne 5\n"


def storm(tmp_path: Path, queue: str = QUEUE, toml: str = "") -> Path:
    """A storm root: queue.txt, the two ledgers, and storm.toml when one is given."""
    root = tmp_path / "storm"
    (root / "lanes").mkdir(parents=True)
    (root / "queue.txt").write_text(queue, encoding="utf-8")
    (root / "integrated.txt").write_text("", encoding="utf-8")
    (root / "abandoned.txt").write_text("", encoding="utf-8")
    if toml:
        (root / "storm.toml").write_text(toml, encoding="utf-8")
    return root


def desk(root: Path, sources: tuple[str, ...] = ()) -> object:
    authority = storm_queue.Authority(root, sources=sources)
    return storm_queue.PriorityDesk.at(root, authority=authority)


def order(root: Path) -> list[str]:
    """The effective order the storm will run, slugs only, settled lanes left out."""
    rows = storm_queue.Resolver.at(root).plan().rows
    return [row.entry.slug for row in rows if row.state != "settled"]


def settle(root: Path, slug: str, ledger: str = "integrated.txt") -> None:
    with (root / ledger).open("a", encoding="utf-8") as handle:
        handle.write(slug + "\n")


def finish(root: Path, slug: str) -> None:
    state = root / "lanes" / slug / ".qwenstorm"
    state.mkdir(parents=True, exist_ok=True)
    (state / "result.json").write_text('{"completed": true}', encoding="utf-8")


def log_lines(root: Path) -> list[dict]:
    path = storm_paths.priority_log(root)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# --- 2. priority items run first, first pushed first -----------------------------------


def test_with_nothing_pushed_the_queue_runs_in_file_order(tmp_path: Path) -> None:
    root = storm(tmp_path)
    assert order(root) == ["a", "b", "c", "d", "e"]
    assert storm_queue.Resolver.at(root).plan().decision == "run a 1"


def test_pushed_items_run_first_in_the_order_they_were_pushed(tmp_path: Path) -> None:
    root = storm(tmp_path)
    priority = desk(root)
    priority.bump("e", None)
    priority.bump("c", None)
    assert order(root) == ["e", "c", "a", "b", "d"]
    assert storm_queue.Resolver.at(root).plan().decision == "run e 5"


def test_bumping_an_item_already_in_the_lane_keeps_its_first_place(tmp_path: Path) -> None:
    """FIFO is by first push: pushing again must not let an item overtake or fall behind."""
    root = storm(tmp_path)
    priority = desk(root)
    priority.bump("e", None)
    priority.bump("c", None)
    report = priority.bump("e", None)
    assert order(root)[:2] == ["e", "c"]
    assert any("already" in line for line in report)


# --- 3. dependencies are respected and pulled forward ----------------------------------


def test_pushing_an_item_pulls_its_dependencies_forward_and_says_so(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\nd 4 c\ne 5\n")
    report = desk(root).bump("d", None)
    # Transitively, in dependency order: b before c before d.
    assert order(root) == ["b", "c", "d", "a", "e"]
    assert log_lines(root)[-1]["moved"] == ["b", "c", "d"]
    assert any("b, c, d" in line for line in report), report


def test_an_integrated_dependency_is_not_pulled_forward(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\nd 4 c\ne 5\n")
    settle(root, "b")
    desk(root).bump("d", None)
    assert log_lines(root)[-1]["moved"] == ["c", "d"]
    assert order(root) == ["c", "d", "a", "e"]


def test_an_item_never_runs_before_its_dependencies_are_integrated(tmp_path: Path) -> None:
    """Even prioritised ahead of a dependency queue.txt gained later by hand, it waits."""
    root = storm(tmp_path, queue="a 1\nb 2\nc 3\n")
    desk(root).bump("c", None)
    (root / "queue.txt").write_text("a 1\nb 2\nc 3 b\n")
    plan = storm_queue.Resolver.at(root).plan()
    assert plan.decision == "run a 1"
    waiting = {row.entry.slug: row.status for row in plan.rows}
    assert "waiting on b" in waiting["c"]


def test_a_dependency_that_was_abandoned_refuses_the_push(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\n")
    settle(root, "b", "abandoned.txt")
    with pytest.raises(storm_queue.Invalid, match="abandoned"):
        desk(root).bump("c", None)


def test_an_unknown_dependency_refuses_the_push(tmp_path: Path) -> None:
    root = storm(tmp_path)
    with pytest.raises(storm_queue.Invalid, match="nowhere"):
        desk(root).push("z", "26", ("nowhere",), None)
    assert "z 26" not in (root / "queue.txt").read_text()


# --- 1. next means next after whatever is running --------------------------------------


def test_a_push_never_touches_a_running_lane(tmp_path: Path) -> None:
    """A lane running has a directory and no result yet. Pushing writes only the log, the
    progress line and (for a new item) queue.txt -- nothing under lanes/."""
    root = storm(tmp_path)
    running = root / "lanes" / "a" / ".qwenstorm"
    running.mkdir(parents=True)
    (running / "lane.log").write_text("attempt 1 in progress\n")
    before = sorted(p.relative_to(root) for p in (root / "lanes").rglob("*"))
    desk(root).push("z", "26", ("c",), None)
    assert sorted(p.relative_to(root) for p in (root / "lanes").rglob("*")) == before
    assert (running / "lane.log").read_text() == "attempt 1 in progress\n"


def test_the_runner_waits_for_the_running_lane_before_it_asks_what_is_next() -> None:
    """The wait (8.c, as many as this device measured) comes first in every pass; the
    resolver is asked after it, and how many is asked of vibey-gh before either."""
    script = (TOOLS / "storm-queue.sh").read_text()
    slots = script.index('SLOTS="$(slots)"')
    wait = script.index('while [ "$(running)" -ge "$SLOTS" ]')
    ask = script.index('"$PY" "$Q/tools/storm_queue.py" next')
    assert slots < wait < ask
    assert "-m vibey_gh slots allowed" in script


# --- 4. who may push: the operator, or a declared source (12.j) ------------------------


def test_the_operator_running_the_cli_locally_may_push(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).bump("e", None)
    assert log_lines(root)[-1]["by"].startswith("operator:")


def test_a_declared_source_may_push(tmp_path: Path) -> None:
    root = storm(tmp_path, toml='[priority]\nsources = ["nightly-triage"]\n')
    storm_queue.PriorityDesk.at(root).bump("e", "nightly-triage")
    assert log_lines(root)[-1]["by"] == "source:nightly-triage"
    assert order(root)[0] == "e"


@pytest.mark.parametrize("verb", ["push", "bump", "unbump"])
def test_an_undeclared_source_is_refused_recorded_and_reported(tmp_path: Path, verb: str) -> None:
    root = storm(tmp_path, toml='[priority]\nsources = ["nightly-triage"]\n')
    priority = storm_queue.PriorityDesk.at(root)
    priority.bump("c", None)  # so an un-bump has something to act on
    calls = {
        "push": lambda: priority.push("z", "26", (), "github-label"),
        "bump": lambda: priority.bump("e", "github-label"),
        "unbump": lambda: priority.unbump("c", "github-label"),
    }
    with pytest.raises(storm_queue.Unauthorised, match="github-label"):
        calls[verb]()
    refusal = log_lines(root)[-1]
    assert refusal["action"] == "refused"
    assert refusal["requested"] == verb
    assert refusal["by"] == "source:github-label"
    assert "refused" in (root / "progress.log").read_text().splitlines()[-1]
    assert order(root)[0] == "c"  # nothing moved
    assert "z 26" not in (root / "queue.txt").read_text()


def test_no_sources_are_declared_unless_the_config_names_them(tmp_path: Path) -> None:
    root = storm(tmp_path)
    with pytest.raises(storm_queue.Unauthorised):
        storm_queue.PriorityDesk.at(root).bump("e", "anything")


def test_a_local_account_that_does_not_own_the_storm_is_not_the_operator(tmp_path: Path) -> None:
    root = storm(tmp_path)
    stranger = storm_queue.Authority(root, sources=(), uid=os.getuid() + 1)
    with pytest.raises(storm_queue.Unauthorised, match="does not own"):
        storm_queue.PriorityDesk.at(root, authority=stranger).bump("e", None)
    assert log_lines(root)[-1]["by"] == f"account:{stranger.user}"


def test_a_declared_source_from_an_account_that_does_not_own_the_storm_is_refused(
    tmp_path: Path,
) -> None:
    """A source name is a label automation gives itself; the owner's uid is the check."""
    root = storm(tmp_path)
    stranger = storm_queue.Authority(root, sources=("nightly-triage",), uid=os.getuid() + 1)
    with pytest.raises(storm_queue.Unauthorised, match="does not own"):
        storm_queue.PriorityDesk.at(root, authority=stranger).bump("e", "nightly-triage")
    refusal = log_lines(root)[-1]
    assert refusal["action"] == "refused" and refusal["requested"] == "bump"
    assert order(root)[0] == "a"


def test_the_operators_name_comes_from_the_password_database_not_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pwd

    monkeypatch.setenv("USER", "root")
    monkeypatch.setenv("LOGNAME", "root")
    root = storm(tmp_path)
    desk(root).bump("e", None)
    assert log_lines(root)[-1]["by"] == f"operator:{pwd.getpwuid(os.getuid()).pw_name}"


def test_a_process_inside_a_lane_is_refused_and_recorded(tmp_path: Path) -> None:
    """Defence in depth only: a lane's commands carry the marker LaneEnvironment exports."""
    lane_environment = _load("lane_environment", "lane_environment.py")
    marker = lane_environment.LaneEnvironment.MARKER
    lane = tmp_path / "lanes" / "some-lane"
    lane.mkdir(parents=True)
    assert lane_environment.LaneEnvironment(lane).build({"PATH": "/usr/bin"})[marker] == "some-lane"
    root = storm(tmp_path)
    inside = storm_queue.Authority(root, sources=(), environ={marker: "some-lane"})
    with pytest.raises(storm_queue.Unauthorised, match=marker):
        storm_queue.PriorityDesk.at(root, authority=inside).bump("e", None)
    assert log_lines(root)[-1]["by"] == 'lane:"some-lane"'
    assert order(root)[0] == "a"


def test_sources_must_be_declared_as_a_list_of_names(tmp_path: Path) -> None:
    root = storm(tmp_path, toml='[priority]\nsources = "nightly-triage"\n')
    with pytest.raises(SystemExit, match="sources"):
        storm_queue.Authority.declared(root)


def test_admission_still_judges_a_pushed_lane_when_it_starts() -> None:
    """Priority chooses which lane is next; storm_trust still decides whether it may run."""
    script = (TOOLS / "storm-queue.sh").read_text()
    ask = script.index('"$PY" "$Q/tools/storm_queue.py" next')
    admit = script.index('"$PY" "$Q/tools/storm_trust.py" admit')
    # The lane itself is launched by `run_lane`, after admission, whatever the concurrency.
    run = script.index('touch "$L/.qwenstorm/running"')
    assert ask < admit < run < script.index('run_lane "$1" "$2"', run)


# --- 5. recorded, append-only, and replayable ------------------------------------------


def test_replaying_the_log_rebuilds_the_order(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\nd 4\ne 5\n")
    priority = desk(root)
    priority.bump("e", None)
    priority.bump("c", None)
    priority.push("z", "26", ("d",), None)
    priority.unbump("e", None)
    expected = ["b", "c", "d", "z"]
    replayed = storm_queue.PriorityLog(storm_paths.priority_log(root)).replay()
    assert replayed == expected
    assert order(root)[:4] == expected


def test_the_log_is_only_ever_appended_to(tmp_path: Path) -> None:
    root = storm(tmp_path)
    priority = desk(root)
    priority.bump("e", None)
    first = storm_paths.priority_log(root).read_bytes()
    priority.unbump("e", None)
    priority.push("z", "26", (), None)
    after = storm_paths.priority_log(root).read_bytes()
    assert after.startswith(first)
    assert [row["action"] for row in log_lines(root)] == ["bump", "unbump", "push"]


def test_every_change_is_a_plain_words_line_in_progress_log(tmp_path: Path) -> None:
    root = storm(tmp_path)
    priority = desk(root)
    priority.bump("e", None)
    priority.unbump("e", None)
    lines = (root / "progress.log").read_text().splitlines()
    assert len(lines) == 2
    assert all(" priority: " in line for line in lines)
    # storm-evidence counts " start " and " end " lines as lane starts and ends.
    assert not any(" start " in line or " end " in line for line in lines)


def test_the_log_is_declared_not_compiled_in(tmp_path: Path) -> None:
    elsewhere = tmp_path / "records" / "priority.jsonl"
    root = storm(tmp_path, toml=f'[priority]\nlog = "{elsewhere}"\n')
    assert storm_paths.priority_log(root) == elsewhere
    desk(root).bump("e", None)
    assert elsewhere.is_file()
    relative = storm(tmp_path / "second", toml='[priority]\nlog = "ledgers/prio.log"\n')
    assert storm_paths.priority_log(relative) == relative / "ledgers/prio.log"


def test_an_unreadable_log_stops_the_resolver_rather_than_ignoring_priority(
    tmp_path: Path,
) -> None:
    root = storm(tmp_path)
    storm_paths.priority_log(root).write_text('{"action": "bump", "moved": ["e"]}\nnot json\n')
    with pytest.raises(storm_queue.Unreadable):
        storm_queue.Resolver.at(root).plan()
    with pytest.raises(storm_queue.Unreadable):
        desk(root).bump("c", None)


def test_the_evidence_job_consumes_the_priority_log() -> None:
    evidence = _load("storm_evidence", "storm-evidence.py")
    name = storm_paths.priority_log(evidence.STORM)
    assert str(name.relative_to(evidence.STORM)) in evidence.STREAMS


# --- 6. un-bump returns an item to its queue.txt position ------------------------------


def test_unbump_returns_an_item_to_its_queue_position(tmp_path: Path) -> None:
    root = storm(tmp_path)
    priority = desk(root)
    priority.bump("e", None)
    priority.bump("c", None)
    priority.unbump("e", None)
    assert order(root) == ["c", "a", "b", "d", "e"]
    assert log_lines(root)[-1]["action"] == "unbump"


def test_unbumping_an_item_not_in_the_lane_is_an_error(tmp_path: Path) -> None:
    root = storm(tmp_path)
    with pytest.raises(storm_queue.Invalid, match="not prioritised"):
        desk(root).unbump("e", None)


# --- 7. pushing a new item -------------------------------------------------------------


def test_pushing_a_new_item_appends_it_with_its_dependencies_and_prioritises_it(
    tmp_path: Path,
) -> None:
    root = storm(tmp_path)
    desk(root).push("z", "26", ("c", "e"), None)
    assert (root / "queue.txt").read_text().splitlines()[-1] == "z 26 c,e"
    assert order(root)[:3] == ["c", "e", "z"]
    event = log_lines(root)[-1]
    assert event["action"] == "push" and event["appended"] is True


def test_a_queue_without_a_final_newline_still_gains_a_whole_line(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2")
    desk(root).push("z", "26", (), None)
    assert (root / "queue.txt").read_text() == "a 1\nb 2\nz 26\n"


def test_pushing_a_queued_slug_under_another_issue_is_an_error(tmp_path: Path) -> None:
    root = storm(tmp_path)
    with pytest.raises(storm_queue.Invalid, match="#5"):
        desk(root).push("e", "99", (), None)


@pytest.mark.parametrize("verb", ["push", "bump"])
@pytest.mark.parametrize("ledger", ["integrated.txt", "abandoned.txt"])
def test_pushing_a_settled_item_is_a_recorded_no_op(tmp_path: Path, verb: str, ledger: str) -> None:
    """ADR-0054 item 7: prioritising a finished item does nothing, says so, and succeeds."""
    root = storm(tmp_path)
    settle(root, "e", ledger)
    priority = desk(root)
    report = priority.push("e", "5", (), None) if verb == "push" else priority.bump("e", None)
    event = log_lines(root)[-1]
    assert event["action"] == verb and event["moved"] == [] and "settled" in event["noop"]
    assert any("nothing to do" in line for line in report), report
    assert "e" not in storm_queue.PriorityLog(storm_paths.priority_log(root)).replay()


def test_pushing_a_new_slug_that_is_already_settled_does_not_queue_it(tmp_path: Path) -> None:
    root = storm(tmp_path)
    settle(root, "z")
    desk(root).push("z", "26", (), None)
    assert "z 26" not in (root / "queue.txt").read_text()
    assert log_lines(root)[-1]["appended"] is False


def test_pushing_a_finished_item_is_a_recorded_no_op(tmp_path: Path) -> None:
    root = storm(tmp_path)
    finish(root, "e")
    report = desk(root).bump("e", None)
    assert "awaits review" in log_lines(root)[-1]["noop"]
    assert any("nothing to do" in line for line in report), report


def test_the_cli_exits_zero_for_a_no_op(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    settle(root, "b")
    done = priority_cli(root, env, "push", "b", "2")
    assert done.returncode == 0, done.stderr
    assert log_lines(root)[-1]["noop"]


# --- the resolver keeps storm-queue.sh's own rules --------------------------------------


def test_a_finished_lane_holds_the_storm_unless_unattended(tmp_path: Path) -> None:
    root = storm(tmp_path)
    finish(root, "a")
    assert storm_queue.Resolver.at(root).plan().decision == "review a"
    (root / "UNATTENDED").touch()
    assert storm_queue.Resolver.at(root).plan().decision == "run b 2"


def test_an_abandoned_dependency_blocks_its_lane_visibly(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="d 4 b\nb 2\n")
    settle(root, "b", "abandoned.txt")
    resolver = storm_queue.Resolver.at(root)
    # The shell's own sequence: this pass waits and marks d; the next holds for review of d.
    assert resolver.plan().decision == "wait"
    assert not (root / "lanes/d/.qwenstorm/result.json").exists()  # plan() writes nothing
    assert resolver.next() == "wait"
    assert resolver.plan().decision == "review d"
    assert json.loads((root / "lanes/d/.qwenstorm/result.json").read_text()) == {
        "completed": False,
        "blocked_on": "b",
    }
    assert "blocked d #4: dependency b was abandoned" in (root / "progress.log").read_text()


def test_the_queue_is_empty_when_everything_is_settled(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\n")
    settle(root, "a")
    assert storm_queue.Resolver.at(root).plan().decision == "empty"


def test_nothing_eligible_waits(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="c 3 b\n")
    assert storm_queue.Resolver.at(root).plan().decision == "wait"


def test_a_running_lane_is_never_chosen_again_and_keeps_the_storm_alive(tmp_path: Path) -> None:
    """With more than one lane at once (ADR-0058), the lane already running is skipped --
    never started twice -- and still counts as pending, so the storm is not "empty" while
    it runs beside the runner."""
    root = storm(tmp_path, queue="a 1\nb 2\n")
    (root / "lanes/a/.qwenstorm").mkdir(parents=True)
    (root / "lanes/a/.qwenstorm/running").touch()
    resolver = storm_queue.Resolver.at(root)
    assert resolver.ledger.running("a") and not resolver.ledger.running("b")
    assert resolver.plan().decision == "run b 2"
    assert [row.state for row in resolver.plan().rows][0] == "running"
    settle(root, "b")
    assert storm_queue.Resolver.at(root).plan().decision == "wait"


# --- the shape: classes, each with its interface beside it (ADR-0016, 9.b) --------------


def test_each_class_honours_the_interface_declared_beside_it(tmp_path: Path) -> None:
    declared = _load("storm_queue_interface", "interfaces/storm_queue_interface.py")
    cli = _load("storm_priority_cli", "storm-priority.py")
    root = storm(tmp_path)
    pairs = [
        (storm_queue.QueueFile(root), declared.QueueFileInterface),
        (storm_queue.Ledger(root), declared.LedgerInterface),
        (storm_queue.PriorityLog(root / "p.log"), declared.PriorityLogInterface),
        (storm_queue.Authority(root, sources=()), declared.AuthorityInterface),
        (storm_queue.Resolver.at(root), declared.ResolverInterface),
        (desk(root), declared.PriorityDeskInterface),
        (storm_queue.Names(), declared.NamesInterface),
        (storm_queue.PriorityLogs(), declared.PriorityLogsInterface),
        (cli.PriorityCli(root), declared.PriorityCliInterface),
    ]
    for instance, interface in pairs:
        assert isinstance(instance, interface), f"{type(instance).__name__} vs {interface}"
        for name, member in vars(interface).items():
            if name.startswith("_") or not callable(member):
                continue
            want = list(inspect.signature(member).parameters)
            have = ["self", *inspect.signature(getattr(instance, name)).parameters]
            assert have == want, f"{type(instance).__name__}.{name}: {have} != {want}"


def test_the_interface_declares_and_never_consumes() -> None:
    source = (TOOLS / "interfaces/storm_queue_interface.py").read_text(encoding="utf-8")
    imported = {
        line.split()[1].split(".")[0]
        for line in source.splitlines()
        if line.startswith(("import ", "from "))
    }
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}, imported


@pytest.mark.parametrize("filename", ["storm_queue.py", "storm-priority.py"])
def test_the_only_bare_function_is_the_cli_entry_point(filename: str) -> None:
    module = _load(filename.replace("-", "_").removesuffix(".py") + "_shape", filename)
    bare = [
        name
        for name, member in vars(module).items()
        if inspect.isfunction(member) and member.__module__ == module.__name__
    ]
    assert bare == ["main"]


# --- the shell and the CLI agree: the real storm-queue.sh, in a throwaway storm ---------

STUB_TRUST = """\
import json, sys
from pathlib import Path
state, number = Path(sys.argv[2]), sys.argv[3]
root = Path(__file__).absolute().parent.parent
refused = (root / "refuse.txt").read_text().split() if (root / "refuse.txt").exists() else []
if number in refused:
    (state / "result.json").write_text(json.dumps({"completed": False, "refused": "stranger"}))
    # Settled here only so the throwaway storm can reach "queue empty" and exit.
    with (root / "abandoned.txt").open("a") as h:
        h.write(state.parent.name + "\\n")
    print("the issue was opened by stranger, who is not in [unattended_approval] authors")
    sys.exit(1)
(state / "title.txt").write_text("t" + number)
(state / "issue.md").write_text("body")
print("admitted #" + number + " by operator (operator)")
"""

STUB_LANE = """\
import subprocess, sys
from pathlib import Path
lane = Path(sys.argv[1])
root = Path(__file__).absolute().parent.parent
with (root / "ran.txt").open("a") as h:
    h.write(lane.name + "\\n")
hook = root / "hooks" / lane.name
if hook.exists():
    subprocess.run(["bash", str(hook)], check=True)
(lane / ".qwenstorm" / "result.json").write_text('{"completed": true}')
with (root / "integrated.txt").open("a") as h:
    h.write(lane.name + "\\n")
"""


def throwaway_storm(tmp_path: Path, queue: str) -> tuple[Path, dict[str, str]]:
    """A storm whose runner, admission, setup and background loops are stubs, and whose
    `pgrep`/`ps` see nothing -- so the live storm on this machine can never hold it up."""
    root = storm(tmp_path, queue=queue)
    tools = root / "tools"
    tools.mkdir()
    for name in (
        "storm-queue.sh",
        "storm_paths.py",
        "storm_queue.py",
        "storm-priority.py",
        "lane_environment.py",
    ):
        shutil.copy2(TOOLS / name, tools / name)
    (tools / "storm_trust.py").write_text(STUB_TRUST)
    (tools / "qwenlane.py").write_text(STUB_LANE)
    (tools / "storm-merge.py").write_text("")
    (tools / "storm-cycle.py").write_text("")
    (tools / "lane-setup.sh").write_text(
        '#!/bin/bash\nmkdir -p "$(cd "$(dirname "$0")/.." && pwd)/lanes/$1/.qwenstorm"\n'
    )
    (tools / "lane-setup.sh").chmod(0o755)
    (root / "scratch").mkdir()
    (root / "hooks").mkdir()
    # vibey-gh is stubbed too: `slots allowed` answers $SLOTS_ANSWER (unset: nothing, which
    # the runner must read as one), and every other call is the real interpreter.
    python = tmp_path / "python"
    python.write_text(
        '#!/bin/bash\nif [ "$1 $2 $3" = "-m vibey_gh slots" ]; then\n'
        '  [ -n "$SLOTS_ANSWER" ] && echo "$SLOTS_ANSWER"; echo "stub vibey-gh" >&2; exit 0\nfi\n'
        f'exec "{sys.executable}" "$@"\n'
    )
    python.chmod(0o755)
    (root / "storm.toml").write_text(
        f'[paths]\nrepo = "{root}"\nslug = "owner/repo"\npython = "{python}"\n'
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # `gh` would record that it was asked: nothing here may consult the forge for priority.
    gh = f'echo "$@" >> "{tmp_path}/gh-was-called"; exit 1'
    for name, body in (("pgrep", "exit 1"), ("ps", "exit 0"), ("gh", gh)):
        (bin_dir / name).write_text(f"#!/bin/bash\n{body}\n")
        (bin_dir / name).chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "VIBEY_GH_SLOTS_DIR": str(tmp_path / "slots"),
        "STORM_POLL_SECONDS": "1",
    }
    return root, env


def run_storm(root: Path, env: dict[str, str], cwd: Path | None = None) -> list[str]:
    done = subprocess.run(
        ["bash", str(root / "tools/storm-queue.sh")],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=cwd,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "queue empty" in (root / "progress.log").read_text()
    return (root / "ran.txt").read_text().split()


def priority_cli(root: Path, env: dict[str, str], *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "tools/storm-priority.py"), *argv],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def test_the_shell_runs_lanes_in_the_order_the_cli_lists(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\nc 3\nd 4 b\ne 5\n")
    assert priority_cli(root, env, "bump", "e").returncode == 0
    assert priority_cli(root, env, "bump", "d").returncode == 0
    listed = priority_cli(root, env, "list")
    assert listed.returncode == 0, listed.stderr
    assert listed.stdout.splitlines()[0] == "next: e #5"
    predicted = [line.split()[1] for line in listed.stdout.splitlines() if line[:1].isdigit()]
    assert predicted == ["e", "b", "d", "a", "c"]
    assert run_storm(root, env) == predicted


def test_a_push_mid_lane_runs_next_after_it_and_never_interrupts_it(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\nc 3\nd 4\n")
    # While lane `a` is running, the operator pushes a new item that depends on `c`.
    (root / "hooks" / "a").write_text(
        f'"{sys.executable}" "{root}/tools/storm-priority.py" push z 26 --deps c\n'
    )
    ran = run_storm(root, env)
    assert ran == ["a", "c", "z", "b", "d"]
    assert ran.count("a") == 1  # never restarted, never interrupted
    assert json.loads((root / "lanes/a/.qwenstorm/result.json").read_text())["completed"]


def test_one_lane_at_a_time_unless_vibey_gh_answers_more(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    assert run_storm(root, env) == ["a", "b"]
    assert "concurrent lanes: 1" in (root / "progress.log").read_text()
    assert not list((root / "lanes").rglob("running"))


def test_two_lanes_run_at_once_when_this_device_measured_two(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    # Lane a finishes only once lane b has started: with one slot that never happens and
    # a records that it ran alone.
    (root / "hooks" / "a").write_text(
        f'for i in $(seq 100); do grep -qx b "{root}/ran.txt" && exit 0; sleep 0.1; done\n'
        f'touch "{root}/alone"\n'
    )
    ran = run_storm(root, {**env, "SLOTS_ANSWER": "2"})
    assert sorted(ran) == ["a", "b"] and not (root / "alone").exists()
    assert "concurrent lanes: 2" in (root / "progress.log").read_text()
    assert not list((root / "lanes").rglob("running"))


def test_a_requested_calibration_runs_when_the_queue_empties(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\n")
    (tmp_path / "slots").mkdir()
    (tmp_path / "slots" / "abc.request.json").write_text("{}")
    # The stubbed vibey-gh answers every `slots` call; the pool builder is the real tool,
    # which finds no lane records here and falls back to the storm's specs -- stubbed too.
    (root / "tools" / "storm_turn_pool.py").write_text(
        "import sys\nopen(sys.argv[sys.argv.index('--out') + 1], 'w').write('{}\\n')\n"
    )
    run_storm(root, env)
    log = (root / "progress.log").read_text()
    assert "calibrating concurrent lanes for this device (requested)" in log
    assert "calibration did not finish" not in log


def test_a_pushed_lane_whose_issue_admission_refuses_never_runs(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    (root / "refuse.txt").write_text("26\n")
    assert priority_cli(root, env, "push", "z", "26").returncode == 0
    ran = run_storm(root, env)
    assert ran == ["a", "b"]
    assert "refused z #26" in (root / "progress.log").read_text()


def test_the_cli_refuses_an_undeclared_source_with_a_nonzero_exit(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    done = priority_cli(root, env, "bump", "b", "--source", "github-label")
    assert done.returncode == 1
    assert "github-label" in done.stdout + done.stderr
    assert log_lines(root)[-1]["action"] == "refused"


# --- hardening after the post-merge review of #1089 --------------------------------------

FORGED = "b\n2026-09-24T05:00:00Z start forged #999 on integration@deadbee"


def progress(root: Path) -> list[str]:
    path = root / "progress.log"
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def test_a_forged_newline_never_reaches_progress_log_as_a_line_of_its_own(tmp_path: Path) -> None:
    """The reviewer's probe: a slug and a source carrying a newline and a fake `start` line."""
    root = storm(tmp_path, toml='[priority]\nsources = ["x"]\n')
    with pytest.raises(storm_queue.Invalid):
        storm_queue.PriorityDesk.at(root).bump(FORGED, "x end y")
    lines = progress(root)
    assert len(lines) == 1
    assert lines[0][:20].endswith("Z") and " priority: refused" in lines[0]
    assert not any(line.startswith("2026-09-24T05:00:00Z") for line in lines)
    # Recorded, escaped: one JSON line whose slug is the raw request, never raw bytes.
    raw = storm_paths.priority_log(root).read_text(encoding="utf-8")
    assert raw.count("\n") == 1
    assert json.loads(raw)["slug"] == FORGED


def test_progress_lines_carry_no_control_characters(tmp_path: Path) -> None:
    root = storm(tmp_path)
    storm_queue.Ledger(root).say("one\ntwo\rthree\x1b[31m four")
    lines = progress(root)
    assert len(lines) == 1
    assert all(ch.isprintable() for ch in lines[0])


def test_the_evidence_counts_starts_and_ends_only_from_progress_log(tmp_path: Path) -> None:
    evidence = _load("storm_evidence_counts", "storm-evidence.py")
    rows = [
        {
            "kind": "stream",
            "source": "progress.log",
            "line": "2026-09-24T01:00:00Z start a #1 on x",
        },
        {
            "kind": "stream",
            "source": "progress.log",
            "line": "2026-09-24T02:00:00Z end   a #1 exit=0",
        },
        {
            "kind": "stream",
            "source": "progress.log",
            "line": '2026-09-24T03:00:00Z priority: refused a bump of "b\\n2026-09-24T05:00:00Z start forged #999 on x"',
        },
        {"kind": "stream", "source": "priority.log", "line": '{"slug": "x start y end z"}'},
        {"kind": "stream", "source": "integrated.txt", "line": "a start b end"},
    ]
    summary = evidence.summarise(rows)
    assert (summary["starts"], summary["ends"]) == (1, 1)
    report = evidence.report(rows, "T", [])
    assert "lane starts logged: 1" in report and "lane ends logged: 1" in report


def test_the_forged_bump_leaves_the_evidence_counts_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = _load("storm_evidence_forged", "storm-evidence.py")
    root = storm(tmp_path, toml='[priority]\nsources = ["x"]\n')
    (root / "progress.log").write_text("2026-09-24T04:00:00Z start a #1 on integration@abc\n")
    for name, value in (
        ("STORM", root),
        ("LANES", root / "lanes"),
        ("EVIDENCE", tmp_path / "evidence"),
        ("LEDGER", tmp_path / "evidence/ledger.jsonl"),
        ("WATERMARK", tmp_path / "evidence/watermark.json"),
    ):
        monkeypatch.setattr(evidence, name, value)
    before = evidence.summarise(evidence.collect({"offsets": {}, "seen": []})[0])
    with pytest.raises(storm_queue.Invalid):
        storm_queue.PriorityDesk.at(root).bump(FORGED, "x end y")
    after = evidence.summarise(evidence.collect({"offsets": {}, "seen": []})[0])
    assert (after["starts"], after["ends"]) == (before["starts"], before["ends"]) == (1, 0)


@pytest.mark.parametrize("slug", ["../../escape", "a*", "x;y", "..", "a..b", "-a", ".hidden"])
def test_a_slug_outside_the_allow_list_is_refused_and_recorded(tmp_path: Path, slug: str) -> None:
    root = storm(tmp_path)
    before = (root / "queue.txt").read_text()
    with pytest.raises(storm_queue.Invalid, match="slug"):
        desk(root).push(slug, "26", (), None)
    assert (root / "queue.txt").read_text() == before
    assert log_lines(root)[-1]["action"] == "refused"
    assert log_lines(root)[-1]["slug"] == slug


def test_a_bad_dependency_name_or_issue_is_refused(tmp_path: Path) -> None:
    root = storm(tmp_path)
    with pytest.raises(storm_queue.Invalid, match="dependency"):
        desk(root).push("z", "26", ("../x",), None)
    with pytest.raises(storm_queue.Invalid, match="issue"):
        desk(root).push("z", "2 6", (), None)
    assert [row["action"] for row in log_lines(root)] == ["refused", "refused"]


def test_a_hand_edited_queue_line_outside_the_allow_list_is_skipped_loudly(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="../../escape 26\na* 27\nx;y 28\nok 29 ../bad\nfine x1\na 1\n")
    resolver = storm_queue.Resolver.at(root)
    plan = resolver.plan()
    assert [row.entry.slug for row in plan.rows] == ["a"]
    assert len(plan.warnings) == 5
    assert resolver.next() == "run a 1"
    said = (root / "progress.log").read_text()
    assert said.count("skipped") == 5 and '"../../escape 26"' in said
    resolver.next()  # said once per distinct warning, not once per pass
    assert (root / "progress.log").read_text().count("skipped") == 5


def test_every_request_is_recorded_whether_it_moved_something_or_not(tmp_path: Path) -> None:
    root = storm(tmp_path)
    priority = desk(root)
    priority.bump("e", None)
    priority.bump("e", None)  # moves nothing
    with pytest.raises(storm_queue.Invalid):
        priority.unbump("c", None)  # not prioritised
    with pytest.raises(storm_queue.Invalid):
        priority.bump("nowhere", None)  # not queued
    events = log_lines(root)
    assert [row["action"] for row in events] == ["bump", "bump", "refused", "refused"]
    assert events[1]["moved"] == []


# --- un-bump undoes exactly what the push or bump moved (ADR-0054) ----------------------


def test_unbump_takes_back_the_dependencies_its_bump_pulled_forward(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\nd 4 c\ne 5\n")
    priority = desk(root)
    priority.bump("d", None)
    report = priority.unbump("d", None)
    assert order(root) == ["a", "b", "c", "d", "e"]
    assert log_lines(root)[-1]["removed"] == ["b", "c", "d"]
    assert any("b, c, d" in line for line in report), report


def test_unbump_keeps_a_dependency_another_prioritised_lane_still_needs(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\nd 4 b\ne 5\n")
    priority = desk(root)
    priority.bump("c", None)  # pulls b
    priority.bump("d", None)  # b already prioritised
    priority.unbump("c", None)
    assert log_lines(root)[-1]["removed"] == ["c"]
    assert order(root)[:2] == ["b", "d"]


def test_unbump_keeps_a_dependency_that_was_pushed_in_its_own_right(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\n")
    priority = desk(root)
    priority.bump("c", None)  # pulls b
    priority.bump("b", None)  # and the operator also asks for b itself
    priority.unbump("c", None)
    assert log_lines(root)[-1]["removed"] == ["c"]
    assert order(root)[0] == "b"


def test_unbumping_a_lane_another_prioritised_lane_needs_is_refused(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\nc 3 b\nd 4 c\n")
    priority = desk(root)
    priority.bump("d", None)  # pulls b, c
    with pytest.raises(storm_queue.Invalid, match="d"):
        priority.unbump("b", None)
    refusal = log_lines(root)[-1]
    assert refusal["action"] == "refused" and refusal["requested"] == "unbump"
    assert order(root)[:3] == ["b", "c", "d"]


# --- replay refuses a malformed entry, and a missing log is not an empty one ------------


@pytest.mark.parametrize(
    "line",
    [
        pytest.param({"v": 1, "action": "bump", "slug": "e", "moved": ["../x"]}, id="bad-moved"),
        pytest.param({"v": 1, "action": "bump", "slug": "e", "moved": ["e"]}, id="no-by"),
        pytest.param(
            {"v": 2, "action": "bump", "slug": "e", "moved": ["e"], "by": "o", "at": "t"},
            id="unknown-version",
        ),
        pytest.param(
            {"v": 1, "action": "unbump", "slug": "e", "removed": "e", "by": "o", "at": "t"},
            id="removed-not-a-list",
        ),
        pytest.param({"v": 1, "action": "jump", "slug": "e", "by": "o", "at": "t"}, id="verb"),
    ],
)
def test_replay_refuses_a_malformed_entry(tmp_path: Path, line: dict) -> None:
    root = storm(tmp_path)
    storm_paths.priority_log(root).write_text(json.dumps(line) + "\n")
    with pytest.raises(storm_queue.Unreadable, match="line 1"):
        storm_queue.Resolver.at(root).plan()


def test_a_log_that_existed_and_is_gone_is_an_unknown_order_not_an_empty_one(
    tmp_path: Path,
) -> None:
    """The reviewer's probe: the log deleted after a push, its lock file left behind."""
    root = storm(tmp_path)
    desk(root).bump("e", None)
    storm_paths.priority_log(root).unlink()
    with pytest.raises(storm_queue.Unreadable, match="missing"):
        storm_queue.Resolver.at(root).plan()


def test_the_evidence_watermark_also_witnesses_the_log(tmp_path: Path) -> None:
    root = storm(tmp_path)
    watermark = tmp_path / "watermark.json"
    watermark.write_text(json.dumps({"offsets": {"priority.log": 120}}))
    log = storm_queue.PriorityLog(root / "priority.log", watermark, "priority.log")
    with pytest.raises(storm_queue.Unreadable, match="missing"):
        log.replay()
    fresh = storm_queue.PriorityLog(root / "priority.log", watermark, "other.log")
    assert fresh.replay() == []


def test_next_reports_prioritised_lanes_queue_txt_no_longer_carries(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).push("z", "26", (), None)
    (root / "queue.txt").write_text(QUEUE)
    storm_queue.Resolver.at(root).next()
    assert "z is prioritised but not in queue.txt" in (root / "progress.log").read_text()


# --- exit codes: a crash is not a refusal ------------------------------------------------


def test_exit_codes_separate_a_refusal_from_a_crash(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    assert priority_cli(root, env, "bump", "b", "--source", "nobody").returncode == 1
    assert priority_cli(root, env, "push", "a*", "9").returncode == 2
    (root / "storm.toml").write_text("[paths\nbroken")
    crashed = priority_cli(root, env, "bump", "b")
    assert crashed.returncode == 4, crashed.stderr
    resolver = subprocess.run(
        [sys.executable, str(root / "tools/storm_queue.py"), "next"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    assert resolver.returncode == 4


# --- the shell, again: no glob, no forge, and exit 3 is waited out ------------------------


def test_the_runner_never_word_splits_or_globs_the_decision() -> None:
    script = (TOOLS / "storm-queue.sh").read_text()
    assert "set -- $decision" not in script
    assert 'read -r verdict rest <<<"$decision"' in script


def test_a_globbing_queue_line_never_runs_even_where_it_would_match(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "qu* 7\na 1\n")
    assert (root / "queue.txt").exists()  # what `qu*` would expand to from the storm root
    ran = run_storm(root, env, cwd=root)
    assert ran == ["a"]
    assert '"qu* 7"' in (root / "progress.log").read_text()
    assert not (root / "lanes" / "queue.txt").exists()


def test_priority_never_consults_the_forge(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\nc 3\n")
    assert priority_cli(root, env, "bump", "c").returncode == 0
    assert priority_cli(root, env, "list").stdout.splitlines()[0] == "next: c #3"
    assert run_storm(root, env) == ["c", "a", "b"]
    assert not (tmp_path / "gh-was-called").exists()


def test_the_runner_waits_out_an_unreadable_priority_log_and_says_why(tmp_path: Path) -> None:
    import signal
    import time

    root, env = throwaway_storm(tmp_path, "a 1\n")
    storm_paths.priority_log(root).write_text("not json\n")
    runner = subprocess.Popen(
        ["bash", str(root / "tools/storm-queue.sh")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and "cannot decide" not in "\n".join(progress(root)):
            time.sleep(0.2)
        said = "\n".join(progress(root))
        assert "cannot decide what runs next (resolver exit 3)" in said
        assert runner.poll() is None  # still waiting, not exited as "queue empty"
        assert "queue empty" not in said
        assert not (root / "ran.txt").exists()
    finally:
        os.killpg(runner.pid, signal.SIGTERM)
        runner.wait(timeout=30)


# --- the review of #1092 (head 13bdf0b7) -------------------------------------------------


def witness(root: Path) -> Path:
    log = storm_paths.priority_log(root)
    return log.with_name("." + log.name + ".witness")


def test_the_witness_is_not_matched_by_a_priority_log_glob(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).bump("e", None)
    assert witness(root).is_file()
    assert witness(root) not in set(root.glob("priority.log*"))
    assert json.loads(witness(root).read_text())["length"] == (
        storm_paths.priority_log(root).stat().st_size
    )


def test_a_refusal_never_recreates_a_lost_log(tmp_path: Path) -> None:
    """The reviewer's probe 1: bump, lose the log, then an operator typo."""
    root = storm(tmp_path)
    desk(root).bump("c", None)
    log = storm_paths.priority_log(root)
    log.unlink()
    with pytest.raises(storm_queue.Unreadable, match="missing"):
        desk(root).bump("c d", None)
    assert not log.exists()
    assert "order unknown" in progress(root)[-1]
    with pytest.raises(storm_queue.Unreadable):
        storm_queue.Resolver.at(root).plan()


def test_a_lane_refusal_never_recreates_a_lost_log(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).bump("c", None)
    storm_paths.priority_log(root).unlink()
    inside = storm_queue.Authority(root, sources=(), environ={"VIBEY_STORM_LANE": "x"})
    with pytest.raises(storm_queue.Unreadable):
        storm_queue.PriorityDesk.at(root, authority=inside).bump("a", None)
    assert not storm_paths.priority_log(root).exists()


@pytest.mark.parametrize("keep", [0, 10])
def test_a_truncated_log_is_an_unknown_order(tmp_path: Path, keep: int) -> None:
    """The reviewer's probe 2: a log shorter than the witness recorded."""
    root = storm(tmp_path)
    desk(root).bump("c", None)
    log = storm_paths.priority_log(root)
    log.write_bytes(log.read_bytes()[:keep])
    with pytest.raises(storm_queue.Unreadable, match="truncated|not JSON"):
        storm_queue.Resolver.at(root).plan()


def test_a_request_meeting_an_unreadable_log_says_so_and_raises(tmp_path: Path) -> None:
    root = storm(tmp_path)
    storm_paths.priority_log(root).write_text("not json\n")
    with pytest.raises(storm_queue.Unreadable):
        desk(root).bump("c", None)
    assert "order unknown" in progress(root)[-1]


def test_a_typo_after_a_lost_log_still_exits_3_and_the_runner_waits(tmp_path: Path) -> None:
    """The reviewer's end-to-end probe."""
    import signal
    import time

    root, env = throwaway_storm(tmp_path, "a 1\nb 2\nc 3\n")
    assert priority_cli(root, env, "bump", "c").returncode == 0
    storm_paths.priority_log(root).unlink()
    assert priority_cli(root, env, "list").returncode == 3
    assert priority_cli(root, env, "bump", "c d").returncode == 3
    assert priority_cli(root, env, "list").returncode == 3
    runner = subprocess.Popen(
        ["bash", str(root / "tools/storm-queue.sh")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and "resolver exit 3" not in "\n".join(progress(root)):
            time.sleep(0.2)
        assert "resolver exit 3" in "\n".join(progress(root))
        assert runner.poll() is None
        assert not (root / "ran.txt").exists()
    finally:
        os.killpg(runner.pid, signal.SIGTERM)
        runner.wait(timeout=30)


# --- un-bump: the derived invariant (ADR-0054 item 6, both queues) ---------------------


def test_the_reviewers_orphan_sequence_returns_to_file_order(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="x 1\nd 2\na 3 d\nb 4 d\n")
    priority = desk(root)
    priority.bump("a", None)
    priority.bump("b", None)
    priority.unbump("a", None)
    priority.unbump("b", None)
    assert storm_queue.PriorityLog(storm_paths.priority_log(root)).replay() == []
    assert order(root) == ["x", "d", "a", "b"]


def test_unbumping_a_pulled_dependency_a_named_item_needs_is_refused(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="x 1\nd 2\na 3 d\n")
    priority = desk(root)
    priority.bump("a", None)
    with pytest.raises(storm_queue.Invalid, match="a"):
        priority.unbump("d", None)


@pytest.mark.parametrize("seed", range(40))
def test_unbumping_every_named_item_empties_the_lane(tmp_path: Path, seed: int) -> None:
    """Property: whatever was bumped, un-bumping every named item leaves no orphan."""
    import random

    rng = random.Random(seed)
    slugs = [f"s{i}" for i in range(8)]
    lines = []
    for i, slug in enumerate(slugs):
        deps = sorted(rng.sample(slugs[:i], k=min(i, rng.randint(0, 2))))
        lines.append(f"{slug} {i + 1}" + (f" {','.join(deps)}" if deps else ""))
    root = storm(tmp_path, queue="\n".join(lines) + "\n")
    priority = desk(root)
    for slug in rng.sample(slugs, k=rng.randint(1, 5)):
        priority.bump(slug, None)
    named = {e["slug"] for e in log_lines(root) if e["action"] == "bump"}
    while named:
        for slug in sorted(named):
            try:
                priority.unbump(slug, None)
            except storm_queue.Invalid:
                continue
            named.discard(slug)
            break
        else:
            pytest.fail(f"no named item could be un-bumped: {sorted(named)}")
    assert storm_queue.PriorityLog(storm_paths.priority_log(root)).replay() == []


# --- authorise before the lock; a refusal that cannot be written is still exit 1 -------


def test_another_uid_without_write_access_is_refused_not_crashed(tmp_path: Path) -> None:
    """The reviewer's probe 3, with a real non-writable storm."""
    root = storm(tmp_path)
    desk(root).bump("c", None)
    log = storm_paths.priority_log(root)
    frozen = [log, log.with_name(log.name + ".lock"), witness(root), root / "progress.log"]
    for path in frozen:
        path.chmod(0o444)
    root.chmod(0o555)
    try:
        stranger = storm_queue.Authority(root, sources=(), uid=os.getuid() + 1)
        with pytest.raises(storm_queue.Unauthorised) as refused:
            storm_queue.PriorityDesk.at(root, authority=stranger).bump("a", None)
        assert refused.value.recorded is False
    finally:
        root.chmod(0o755)
        for path in frozen:
            path.chmod(0o644)
    assert log_lines(root)[-1]["action"] == "bump"  # nothing was written


def test_the_cli_reports_an_unrecorded_refusal_with_exit_1(tmp_path: Path) -> None:
    cli = _load("storm_priority_unrecorded", "storm-priority.py")
    root = storm(tmp_path)
    root.chmod(0o555)
    try:
        code = cli.PriorityCli(root).run(["bump", "a", "--source", "nobody"])
    finally:
        root.chmod(0o755)
    assert code == 1


# --- the small ones ---------------------------------------------------------------------


@pytest.mark.parametrize("issue", ["٣", "²", "12٣"])
def test_an_issue_that_is_not_ascii_digits_is_refused(tmp_path: Path, issue: str) -> None:
    root = storm(tmp_path)
    with pytest.raises(storm_queue.Invalid, match="issue"):
        desk(root).push("z", issue, (), None)
    assert "z " not in (root / "queue.txt").read_text()


def test_a_queue_line_whose_issue_is_not_ascii_digits_is_skipped(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="z ٣\na 1\n")
    assert [row.entry.slug for row in storm_queue.Resolver.at(root).plan().rows] == ["a"]


def test_bumping_a_settled_lane_queue_txt_no_longer_carries_is_a_no_op(tmp_path: Path) -> None:
    root = storm(tmp_path, queue="a 1\nb 2\n")
    settle(root, "c")
    report = desk(root).bump("c", None)
    assert log_lines(root)[-1]["noop"]
    assert any("nothing to do" in line for line in report)


@pytest.mark.parametrize("filename", ["storm_queue.py", "storm-priority.py"])
def test_the_priority_tools_cannot_reach_the_forge(filename: str) -> None:
    import ast

    tree = ast.parse((TOOLS / filename).read_text())
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imported & {"subprocess", "urllib", "storm_forge", "http", "socket"}, imported


# --- the re-review of #1092 at 1792f572: a recorded way out of a lost log ---------------


def reset_cli(root: Path, env: dict[str, str], *extra: str) -> subprocess.CompletedProcess:
    return priority_cli(root, env, "reset", "--reason", "the log was lost in a disk move", *extra)


def test_the_order_unknown_message_names_the_way_out(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).bump("c", None)
    storm_paths.priority_log(root).unlink()
    with pytest.raises(storm_queue.Unreadable, match="storm-priority.py reset --reason"):
        storm_queue.Resolver.at(root).plan()


def test_reset_recovers_a_lost_log(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\nc 3\n")
    assert priority_cli(root, env, "bump", "c").returncode == 0
    recorded = storm_paths.priority_log(root).stat().st_size
    storm_paths.priority_log(root).unlink()
    assert priority_cli(root, env, "list").returncode == 3
    done = reset_cli(root, env)
    assert done.returncode == 0, done.stderr
    first = log_lines(root)[0]
    assert first["action"] == "reset" and first["abandons"] == recorded
    assert first["reason"] == "the log was lost in a disk move"
    assert "abandoned" in progress(root)[-1] and "reset" in progress(root)[-1]
    listed = priority_cli(root, env, "list")
    assert listed.returncode == 0 and listed.stdout.splitlines()[0] == "next: a #1"
    assert priority_cli(root, env, "bump", "b").returncode == 0
    assert run_storm(root, env) == ["b", "a", "c"]


@pytest.mark.parametrize("keep", [0, 10])
def test_reset_recovers_a_truncated_or_shorter_restored_log_and_keeps_it(
    tmp_path: Path, keep: int
) -> None:
    root = storm(tmp_path)
    priority = desk(root)
    priority.bump("c", None)
    priority.bump("e", None)
    log = storm_paths.priority_log(root)
    shorter = log.read_bytes()[:keep]
    log.write_bytes(shorter)
    with pytest.raises(storm_queue.Unreadable):
        storm_queue.Resolver.at(root).plan()
    priority.reset("restored from an old backup", None)
    kept = [p for p in root.iterdir() if p.name.startswith("priority.log.abandoned-")]
    assert len(kept) == 1 and kept[0].read_bytes() == shorter  # never deleted
    assert order(root) == ["a", "b", "c", "d", "e"]


def test_reset_recovers_a_fresh_root_holding_a_stale_evidence_watermark(tmp_path: Path) -> None:
    """The reviewer's probe 6: the tracked watermark carries an offset from an earlier root."""
    root = storm(tmp_path, queue="a 1\nb 2\n")
    watermark = tmp_path / "watermark.json"
    watermark.write_text(json.dumps({"offsets": {"priority.log": 812}}))
    log = storm_queue.PriorityLog(storm_paths.priority_log(root), watermark, "priority.log")
    priority = storm_queue.PriorityDesk(
        storm_queue.QueueFile(root),
        storm_queue.Ledger(root),
        log,
        storm_queue.Authority(root, sources=()),
    )
    with pytest.raises(storm_queue.Unreadable, match="reset"):
        priority.bump("b", None)
    priority.reset("a fresh storm root; the tracked watermark is from the last one", None)
    assert log.events()[0]["abandons"] == 812
    priority.bump("b", None)  # the stale offset no longer wedges the storm
    assert log.replay() == ["b"]


def test_reset_is_refused_while_the_log_is_readable(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    assert priority_cli(root, env, "bump", "b").returncode == 0
    done = reset_cli(root, env)
    assert done.returncode == 2
    assert "readable" in done.stderr
    assert log_lines(root)[-1]["action"] == "refused"
    assert log_lines(root)[-1]["requested"] == "reset"
    assert storm_queue.PriorityLog(storm_paths.priority_log(root)).replay() == ["b"]


def test_reset_of_a_storm_that_never_had_a_log_is_refused(tmp_path: Path) -> None:
    root = storm(tmp_path)
    with pytest.raises(storm_queue.Invalid, match="readable"):
        desk(root).reset("nothing to recover", None)


def test_reset_is_operator_only(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).bump("c", None)
    storm_paths.priority_log(root).unlink()
    inside = storm_queue.Authority(root, sources=(), environ={"VIBEY_STORM_LANE": "x"})
    with pytest.raises(storm_queue.Unauthorised):
        storm_queue.PriorityDesk.at(root, authority=inside).reset("from a lane", None)
    stranger = storm_queue.Authority(root, sources=(), uid=os.getuid() + 1)
    with pytest.raises(storm_queue.Unauthorised):
        storm_queue.PriorityDesk.at(root, authority=stranger).reset("another uid", None)
    root_env = storm(tmp_path / "declared", toml='[priority]\nsources = ["bot"]\n')
    desk(root_env).bump("c", None)
    storm_paths.priority_log(root_env).unlink()
    with pytest.raises(storm_queue.Unauthorised, match="operator"):
        storm_queue.PriorityDesk.at(root_env).reset("a declared source", "bot")
    assert not storm_paths.priority_log(root).exists()  # nothing restarted the log


def test_reset_needs_a_reason(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, "a 1\n")
    done = priority_cli(root, env, "reset", "--reason", "  ")
    assert done.returncode == 2


def test_a_reset_line_anywhere_but_first_is_malformed(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).bump("c", None)
    with storm_paths.priority_log(root).open("a") as handle:
        handle.write(
            json.dumps(
                {"v": 1, "action": "reset", "abandons": 5, "reason": "r", "by": "o", "at": "t"}
            )
            + "\n"
        )
    with pytest.raises(storm_queue.Unreadable, match="line 2"):
        storm_queue.Resolver.at(root).plan()


def test_the_evidence_job_rebases_a_reset_log_and_reports_the_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    evidence = _load("storm_evidence_reset", "storm-evidence.py")
    root = storm(tmp_path)
    for name, value in (
        ("STORM", root),
        ("LANES", root / "lanes"),
        ("EVIDENCE", tmp_path / "evidence"),
        ("LEDGER", tmp_path / "evidence/ledger.jsonl"),
        ("WATERMARK", tmp_path / "evidence/watermark.json"),
    ):
        monkeypatch.setattr(evidence, name, value)
    priority = desk(root)
    priority.bump("c", None)
    priority.bump("e", None)
    records, mark, gaps = evidence.collect(evidence.load_watermark())
    evidence.append(records, "T1")
    evidence.advance(mark, "T1", gaps)
    storm_paths.priority_log(root).unlink()
    priority.reset("lost in a disk move", None)
    priority.bump("b", None)
    records, mark, gaps = evidence.collect(evidence.load_watermark())
    assert any("reset" in gap and "lost in a disk move" in gap for gap in gaps), gaps
    lines = [r["line"] for r in records if r.get("source") == "priority.log"]
    assert any('"action": "reset"' in line for line in lines)  # read from the new start
    assert any('"slug": "b"' in line for line in lines)
    assert mark["offsets"]["priority.log"] == storm_paths.priority_log(root).stat().st_size
    assert "reset" in evidence.report(records, "T2", gaps)
    evidence.append(records, "T2")
    evidence.advance(mark, "T2", gaps)
    _, _, again = evidence.collect(evidence.load_watermark())
    assert not any("reset" in gap for gap in again)  # re-based once, not every run


# --- B: a read racing an append is never "truncated" -------------------------------------


@pytest.mark.parametrize("fresh", [False, True], ids=["existing-log", "fresh-storm"])
def test_a_read_racing_appends_never_reports_a_false_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh: bool
) -> None:
    """The reviewer's race2.py, with its injected delay, in threads. A fresh storm also races
    the log's creation: no log yet, then a log and its witness, must never read as lost."""
    import threading
    import time

    root = storm(tmp_path, queue="a 1\nb 2\nc 3\n")
    if not fresh:
        desk(root).bump("c", None)
    original = storm_queue.PriorityLog.recorded_length

    def slow(self: object) -> int:
        time.sleep(0.005)
        return original(self)  # type: ignore[arg-type]

    monkeypatch.setattr(storm_queue.PriorityLog, "recorded_length", slow)
    first_existed = storm_queue.PriorityLog.existed

    def late(self: object) -> bool:
        time.sleep(0.005)  # a reader descheduled between "no log" and "was there one?"
        return first_existed(self)  # type: ignore[arg-type]

    monkeypatch.setattr(storm_queue.PriorityLog, "existed", late)

    def writer() -> None:
        priority = desk(root)
        for i in range(40):
            priority.bump("c" if i % 2 else "b", None)

    writers = [threading.Thread(target=writer) for _ in range(3)]
    for thread in writers:
        thread.start()
    bad = reads = 0
    last = ""
    while any(thread.is_alive() for thread in writers):
        reads += 1
        try:
            storm_queue.PriorityLogs().at(root).replay()
        except storm_queue.Unreadable as exc:
            bad += 1
            last = str(exc)
    for thread in writers:
        thread.join()
    assert reads > 0
    assert bad == 0, last


# --- C: the witness survives a power loss ------------------------------------------------


def test_an_empty_witness_points_to_reset(tmp_path: Path) -> None:
    root = storm(tmp_path)
    desk(root).bump("c", None)
    witness(root).write_text("")
    with pytest.raises(storm_queue.Unreadable, match="storm-priority.py reset"):
        storm_queue.Resolver.at(root).plan()


def test_the_witness_is_fsynced_with_its_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = storm(tmp_path)
    synced: list[str] = []
    real = os.fsync

    def spy(fd: int) -> None:
        import stat as st

        mode = os.fstat(fd).st_mode
        synced.append("dir" if st.S_ISDIR(mode) else "file")
        real(fd)

    monkeypatch.setattr(storm_queue.os, "fsync", spy)
    desk(root).bump("c", None)
    # the log line, the pending witness, then the directory holding the rename
    assert synced.count("file") >= 2 and "dir" in synced


# --- the review of #1092 at bb5df834: a refusal never re-witnesses a shortened log --------

REVIEWED = "a 1\nb 2\nc 3\nd 4\n"


def _truncate_to_empty(log: Path) -> None:
    log.write_bytes(b"")


def _truncate_to_first_line(log: Path) -> None:
    log.write_bytes(log.read_bytes().splitlines(keepends=True)[0])


def _refuse_a_bad_name(root: Path) -> None:
    desk(root).bump("x y", None)


def _refuse_a_lane(root: Path) -> None:
    inside = storm_queue.Authority(root, sources=(), environ={"VIBEY_STORM_LANE": "l"})
    storm_queue.PriorityDesk.at(root, authority=inside).bump("a", None)


@pytest.mark.parametrize(
    "damage", [_truncate_to_empty, _truncate_to_first_line], ids=["to-empty", "to-first-line"]
)
@pytest.mark.parametrize(
    "refusal", [_refuse_a_bad_name, _refuse_a_lane], ids=["invalid-name", "lane-marker"]
)
def test_a_refusal_never_appends_to_a_truncated_log(
    tmp_path: Path, damage: object, refusal: object
) -> None:
    """The reviewer's probe7: a refusal met a shortened log, appended, and rewrote the
    witness to the new length -- so the resolver ran `a` (or lost d's bump) instead of
    exiting 3. Nothing may be written: not the log, not the witness."""
    root = storm(tmp_path, queue=REVIEWED)
    desk(root).bump("c", None)
    desk(root).bump("d", None)
    log = storm_paths.priority_log(root)
    damage(log)  # type: ignore[operator]
    with pytest.raises(storm_queue.Unreadable, match="truncated"):
        storm_queue.Resolver.at(root).plan()
    log_before, witness_before = log.read_bytes(), witness(root).read_bytes()
    with pytest.raises(storm_queue.Unreadable, match="truncated"):
        refusal(root)  # type: ignore[operator]
    assert "not recorded, order unknown" in progress(root)[-1]
    assert log.read_bytes() == log_before
    assert witness(root).read_bytes() == witness_before
    with pytest.raises(storm_queue.Unreadable, match="truncated"):
        storm_queue.Resolver.at(root).next()


@pytest.mark.parametrize("content", ["", "{not json", '{"length": "many"}'])
def test_a_refusal_never_rewrites_an_unreadable_witness(tmp_path: Path, content: str) -> None:
    root = storm(tmp_path, queue=REVIEWED)
    desk(root).bump("c", None)
    witness(root).write_text(content)
    log = storm_paths.priority_log(root)
    log_before = log.read_bytes()
    for refusal in (_refuse_a_bad_name, _refuse_a_lane):
        with pytest.raises(storm_queue.Unreadable):
            refusal(root)
        assert log.read_bytes() == log_before
        assert witness(root).read_text() == content
    with pytest.raises(storm_queue.Unreadable):
        storm_queue.Resolver.at(root).plan()


def test_the_cli_exits_3_for_a_refusal_meeting_a_truncated_log(tmp_path: Path) -> None:
    root, env = throwaway_storm(tmp_path, REVIEWED)
    assert priority_cli(root, env, "bump", "c").returncode == 0
    assert priority_cli(root, env, "bump", "d").returncode == 0
    _truncate_to_first_line(storm_paths.priority_log(root))
    before = witness(root).read_bytes()
    assert priority_cli(root, env, "bump", "x y").returncode == 3
    assert priority_cli(root, env, "list").returncode == 3
    assert witness(root).read_bytes() == before


def test_a_lane_refusal_of_reset_on_a_lost_log_says_the_log_is_lost(tmp_path: Path) -> None:
    """Not "no write access": the lane can write; the log is lost, so nothing is recorded."""
    root, env = throwaway_storm(tmp_path, "a 1\nb 2\n")
    assert priority_cli(root, env, "bump", "b").returncode == 0
    storm_paths.priority_log(root).unlink()
    done = reset_cli(root, {**env, "VIBEY_STORM_LANE": "x"})
    assert done.returncode == 1
    assert "no write access" not in done.stderr
    assert "could not be recorded" in done.stderr and "lost" in done.stderr
    assert not storm_paths.priority_log(root).exists()
