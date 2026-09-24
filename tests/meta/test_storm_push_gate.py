# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for the storm's push gate: one push at a time, and a hung one is reaped by rule.

Parallel lanes push through one shared lock so that only one pre-push gate run happens at a
time. On 2026-09-24 one push's pytest froze for 39 minutes at 0% CPU while it held that
lock, every other push queued behind it, and a human had to kill it. These tests pin the
two halves of the fix:

  * the lock is code with an owner record, so "who holds it and what is it doing" has an
    answer, and only its owner can release it;
  * the reaper acts only on a measured condition -- the holder is gone, the owner's own
    process group used less than a declared CPU budget over a declared window, or it passed
    a declared wall ceiling -- and it kills nothing but that group, after writing evidence.

Most tests drive the classes with a fake process table, a fake signaller and a fake clock,
so every condition is exact and instant. The last few spawn real children under a real lock
and let the real reaper find them, with thresholds of a second or two.

The tools are addressed by path for the reason `test_storm_check_parser.py` gives: they are
scripts, not a package. Delete this in the same commit that deletes them.
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, filename: str):  # noqa: ANN202 - a module object
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec and spec.loader, f"the storm tool is missing: {TOOLS / filename}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


push_gate = _load("push_gate", "push_gate.py")
Owner = push_gate.Owner
Proc = push_gate.Proc
PushGateConfig = push_gate.PushGateConfig

HOLDER = 4242  # the process holding the lock (the `run` wrapper)
GROUP = 4300  # the push's own process group, which `run` creates
STRANGER = 777  # somebody else's group: never to be touched
UID = os.getuid()


# --- fakes -------------------------------------------------------------------------------


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.t = start

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


@dataclass
class FakeTable:
    """A process table the test writes: who is alive, and each group's members."""

    alive_pids: set[int] = field(default_factory=lambda: {HOLDER})
    groups: dict[int, list] = field(default_factory=dict)
    leaders: set[int] = field(default_factory=lambda: {GROUP})
    readable: bool = True
    cwds: dict[int, str] = field(default_factory=dict)

    def alive(self, pid: int) -> bool:
        return pid in self.alive_pids

    def group_alive(self, pgid: int) -> bool:
        return bool(self.groups.get(pgid))

    def members(self, pgid: int) -> list | None:
        if not self.readable:
            return None
        return list(self.groups.get(pgid, []))

    def listing(self) -> str | None:
        if not self.readable:
            return None
        return "\n".join(
            f"{p.pid} {p.ppid} {p.pgid} {p.cpu_seconds} {p.command}"
            for group in self.groups.values()
            for p in group
        )

    def session_leader(self, pgid: int) -> bool:
        return pgid in self.leaders

    def processes(self) -> list | None:
        if not self.readable:
            return None
        return [p for group in self.groups.values() for p in group]

    def cwd(self, pid: int) -> str | None:
        return self.cwds.get(pid)

    def burn(self, pgid: int, seconds: float) -> None:
        """Every member of `pgid` spends `seconds` of CPU, shared out evenly."""
        group = self.groups[pgid]
        self.groups[pgid] = [
            dataclasses.replace(p, cpu_seconds=p.cpu_seconds + seconds / len(group)) for p in group
        ]


@dataclass
class FakeSignaller:
    """Records every signal. A group dies on the first signal in `lethal` it receives."""

    table: FakeTable
    lethal: tuple[int, ...] = (signal.SIGTERM, signal.SIGKILL)
    sent: list[tuple[str, int, int]] = field(default_factory=list)
    before_kill: object = None

    def send_group(self, pgid: int, sig: int) -> None:
        if sig in (signal.SIGTERM, signal.SIGKILL) and self.before_kill:
            self.before_kill()  # type: ignore[operator]
            self.before_kill = None
        self.sent.append(("group", pgid, sig))
        if sig in self.lethal:
            self.table.groups.pop(pgid, None)

    def send_process(self, pid: int, sig: int) -> None:
        self.sent.append(("process", pid, sig))


def config(tmp_path: Path, **overrides: object) -> PushGateConfig:
    values: dict[str, object] = {
        "lock": tmp_path / ".push-lock",
        "state_dir": tmp_path / "gate",
        "reap_log": tmp_path / "gate" / "reaps.jsonl",
        "idle_cpu_seconds": 2.0,
        "idle_window_seconds": 600.0,
        "wall_ceiling_seconds": 3600.0,
        "grace_seconds": 30.0,
        "poll_seconds": 20.0,
        "log_tail_lines": 50,
        "stack_wait_seconds": 0.0,
        "protected": ("ollama", "vibey-runner"),
        "ownerless_match_seconds": 5.0,
        "worktree_roots": (tmp_path,),
    }
    values.update(overrides)
    return PushGateConfig(**values)  # type: ignore[arg-type]


@dataclass
class Rig:
    cfg: PushGateConfig
    clock: FakeClock
    table: FakeTable
    signaller: FakeSignaller
    lock: object
    reaper: object


def rig(tmp_path: Path, **overrides: object) -> Rig:
    cfg = config(tmp_path, **overrides)
    clock = FakeClock()
    table = FakeTable()
    signaller = FakeSignaller(table)
    lock = push_gate.PushLock(cfg, clock)
    evidence = push_gate.EvidenceCollector(cfg, table, signaller, clock, which=lambda name: None)
    killer = push_gate.GroupKiller(cfg, table, signaller, clock)
    reaper = push_gate.Reaper(cfg, lock, table, evidence, killer, clock)
    return Rig(cfg, clock, table, signaller, lock, reaper)


def owner(clock: FakeClock, tmp_path: Path, **overrides: object) -> Owner:
    # Where `run` writes it: the gate reads a push log from nowhere else (#1105-2).
    token = str(overrides.get("token", "tok-1"))
    log = tmp_path / "gate" / "logs" / f"{token}.log"
    if not log.exists():
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("".join(f"gate line {n}\n" for n in range(100)), encoding="utf-8")
    values: dict[str, object] = {
        "token": "tok-1",
        "pid": HOLDER,
        "pgid": GROUP,
        "dedicated": True,
        "uid": UID,
        "branch": "feat/some-lane",
        "worktree": str(tmp_path / "lane"),
        "started_at": clock.now(),
        "command": ["git", "push", "origin", "HEAD:feat/some-lane"],
        "log": str(log),
        "stacks": None,
    }
    values.update(overrides)
    return Owner(**values)  # type: ignore[arg-type]


def pytest_tree(cpu: float = 100.0) -> list:
    """The shape of a pre-push gate: git, the hook's bash, pytest and two xdist workers."""
    return [
        Proc(GROUP, HOLDER, GROUP, 0.1, "git push origin HEAD:feat/some-lane"),
        Proc(GROUP + 1, GROUP, GROUP, 0.2, "bash -c uv run --extra dev pytest -q"),
        Proc(GROUP + 2, GROUP + 1, GROUP, cpu, "/x/.venv/bin/python3 /x/.venv/bin/pytest -q"),
        Proc(
            GROUP + 3,
            GROUP + 2,
            GROUP,
            cpu,
            "/x/.venv/bin/python3 -u -c import sys;exec(eval(sys.stdin.readline()))",
        ),
        Proc(
            GROUP + 4,
            GROUP + 2,
            GROUP,
            cpu,
            "/x/.venv/bin/python3 -u -c import sys;exec(eval(sys.stdin.readline()))",
        ),
    ]


def held(r: Rig, tmp_path: Path, **overrides: object) -> Owner:
    held_by = owner(r.clock, tmp_path, **overrides)
    assert r.lock.acquire(held_by)
    return held_by


def reap_log(r: Rig) -> list[dict]:
    if not r.cfg.reap_log.exists():
        return []
    return [json.loads(line) for line in r.cfg.reap_log.read_text().splitlines()]


# --- the lock, with an owner record --------------------------------------------------------


def test_acquire_is_an_atomic_mkdir_with_the_owner_recorded_inside(tmp_path: Path) -> None:
    r = rig(tmp_path)
    first = held(r, tmp_path)
    assert r.cfg.lock.is_dir()
    record = json.loads((r.cfg.lock / push_gate.OWNER_FILE).read_text())
    for key in ("pid", "pgid", "branch", "worktree", "started_at", "uid", "token"):
        assert key in record, key
    assert record["pid"] == HOLDER and record["pgid"] == GROUP
    assert record["branch"] == "feat/some-lane" and record["uid"] == UID
    # A second acquirer waits its turn; the first owner is untouched.
    assert not r.lock.acquire(owner(r.clock, tmp_path, token="tok-2", pid=5555))
    assert r.lock.state().owner == first


def test_the_owner_releases_its_own_lock(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    assert r.lock.release("tok-1", UID) == "released"
    assert not r.cfg.lock.exists()
    assert r.lock.state().kind == "free"


def test_release_by_a_non_owner_is_refused(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    assert r.lock.release("somebody-else", UID) == "not-owner"
    assert r.lock.release("tok-1", UID + 1) == "not-owner"
    assert r.cfg.lock.is_dir()
    assert r.lock.state().owner.token == "tok-1"


def test_status_says_who_holds_the_lock_and_what_it_is_doing(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.clock.sleep(125)
    text = push_gate.Status(r.cfg, r.lock, r.table, r.clock).render()
    assert "feat/some-lane" in text
    assert str(HOLDER) in text and str(GROUP) in text
    assert "2m05s" in text  # how long it has held the lock
    assert "5 processes" in text and "300.3 CPU-s" in text
    assert "gate line 99" in text  # the push's own last words


def test_status_of_a_free_lock_says_free(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert "free" in push_gate.Status(r.cfg, r.lock, r.table, r.clock).render()


def test_a_bare_mkdir_lock_is_reported_and_never_reaped(tmp_path: Path) -> None:
    """The old recipe: `mkdir .push-lock`. There is no owner to measure, so nothing is done."""
    r = rig(tmp_path)
    r.cfg.lock.mkdir()
    r.clock.sleep(10 * 3600)
    decision = r.reaper.tick()
    assert decision.action == "unknown"
    assert "owner" in decision.detail
    assert r.cfg.lock.is_dir() and not r.signaller.sent
    assert reap_log(r) == []


# --- declared, not hard-coded (12.c) -------------------------------------------------------


def test_the_lock_is_keyed_by_a_declared_path(tmp_path: Path) -> None:
    root = tmp_path / "storm"
    root.mkdir()
    (root / "storm.toml").write_text(
        '[push_gate]\nlock = "/somewhere/else/.gate"\nidle_cpu_seconds = 5\n'
        "idle_window_seconds = 900\nwall_ceiling_seconds = 7200\n",
        encoding="utf-8",
    )
    declared = PushGateConfig.declared(root)
    assert declared.lock == Path("/somewhere/else/.gate")
    assert declared.idle_cpu_seconds == 5.0
    assert declared.idle_window_seconds == 900.0
    assert declared.wall_ceiling_seconds == 7200.0
    # The command line outranks the file, for one run.
    assert PushGateConfig.declared(root, lock=tmp_path / "x").lock == tmp_path / "x"


def test_every_threshold_has_a_sane_default(tmp_path: Path) -> None:
    root = tmp_path / "storm"
    root.mkdir()
    silent = PushGateConfig.declared(root)
    # Beside the storm root, where the lanes and the storm share one parent directory.
    assert silent.lock == tmp_path / ".push-lock"
    assert silent.idle_cpu_seconds == push_gate.IDLE_CPU_SECONDS == 2.0
    assert silent.idle_window_seconds == push_gate.IDLE_WINDOW_SECONDS == 600.0
    assert silent.wall_ceiling_seconds == push_gate.WALL_CEILING_SECONDS == 3600.0
    assert silent.grace_seconds > 0 and silent.poll_seconds > 0
    assert "ollama" in silent.protected


@pytest.mark.parametrize("value", ["0", "-1", '"soon"', "inf", "nan", "true"])
def test_a_threshold_that_is_not_a_positive_number_is_refused(tmp_path: Path, value: str) -> None:
    (tmp_path / "storm.toml").write_text(f"[push_gate]\nidle_window_seconds = {value}\n")
    with pytest.raises(SystemExit, match="idle_window_seconds"):
        PushGateConfig.declared(tmp_path)


# --- condition (a): the holder is gone ------------------------------------------------------


def test_a_stale_lock_whose_holder_is_gone_is_released(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.alive_pids.clear()  # the wrapper died; its push group is gone too
    decision = r.reaper.tick()
    assert (decision.action, decision.condition) == ("released", "stale")
    assert not r.cfg.lock.exists()
    assert r.signaller.sent == []  # nothing to kill: releasing is the whole remedy
    [record] = reap_log(r)
    assert record["condition"] == "stale" and record["owner"]["pid"] == HOLDER
    assert record["owner"]["branch"] == "feat/some-lane"
    assert Path(record["evidence"]).is_dir()


def test_a_dead_holder_whose_push_is_still_running_is_not_stale(tmp_path: Path) -> None:
    """Releasing here would let a second gate run start beside the first."""
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.alive_pids.clear()
    r.table.groups[GROUP] = pytest_tree()
    decision = r.reaper.tick()
    assert decision.action == "none"
    assert r.cfg.lock.is_dir() and r.signaller.sent == []


def test_a_live_holder_is_never_stale(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path, dedicated=False, pgid=None)
    r.clock.sleep(30)
    assert r.reaper.tick().action == "none"
    assert r.cfg.lock.is_dir()


# --- condition (b): the owner's tree is idle over the window --------------------------------


def test_an_idle_tree_over_the_whole_window_is_reaped(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    assert r.reaper.tick().action == "none"  # the first sample: nothing to compare yet
    r.clock.sleep(300)
    r.table.burn(GROUP, 0.5)
    assert r.reaper.tick().action == "none"  # half a window is not a window
    r.clock.sleep(300)
    r.table.burn(GROUP, 0.5)
    decision = r.reaper.tick()
    assert (decision.action, decision.condition) == ("killed", "idle")
    assert ("group", GROUP, signal.SIGTERM) in r.signaller.sent
    assert not r.cfg.lock.exists()
    [record] = reap_log(r)
    assert record["condition"] == "idle"
    assert record["detail"]["cpu_seconds"] == pytest.approx(1.0)
    assert record["detail"]["window_seconds"] == pytest.approx(600.0)


def test_idle_is_measured_across_passes_not_from_one_snapshot(tmp_path: Path) -> None:
    """A tree at 0% right now may be between two tests; only a window of samples decides."""
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    for _ in range(9):
        assert r.reaper.tick().action == "none"
        r.clock.sleep(59)
    assert r.cfg.lock.is_dir() and r.signaller.sent == []


def test_a_busy_tree_is_not_reaped_even_when_it_is_slow(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    # Fifty minutes of a slow but working suite: 30 CPU-s every ten minutes.
    for _ in range(5):
        assert r.reaper.tick().action == "none"
        r.clock.sleep(600)
        r.table.burn(GROUP, 30.0)
    assert r.reaper.tick().action == "none"
    assert r.cfg.lock.is_dir() and r.signaller.sent == []


def test_processes_coming_and_going_count_as_activity(tmp_path: Path) -> None:
    """A test that forks short-lived children spends CPU the survivors never show."""
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.reaper.tick()
    r.clock.sleep(300)
    r.table.groups[GROUP].append(Proc(GROUP + 9, GROUP + 3, GROUP, 0.0, "git status"))
    r.reaper.tick()
    r.clock.sleep(300)
    r.table.groups[GROUP].pop()
    assert r.reaper.tick().action == "none"
    assert r.signaller.sent == []


def test_an_unreadable_process_table_is_unknown_never_idle(tmp_path: Path) -> None:
    """`ps` is refused under the sandbox; a probe that failed is not a tree at 0% CPU."""
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.table.readable = False
    for _ in range(4):
        decision = r.reaper.tick()
        r.clock.sleep(600)
    assert decision.action == "unknown"
    assert r.signaller.sent == [] and r.cfg.lock.is_dir()


# --- condition (c): the wall ceiling --------------------------------------------------------


def test_the_wall_ceiling_is_reaped_even_while_busy(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.clock.sleep(3599)
    r.table.burn(GROUP, 500)
    assert r.reaper.tick().action == "none"
    r.clock.sleep(2)
    decision = r.reaper.tick()
    assert (decision.action, decision.condition) == ("killed", "ceiling")
    assert ("group", GROUP, signal.SIGTERM) in r.signaller.sent
    assert reap_log(r)[0]["condition"] == "ceiling"


# --- what is killed, and only that ----------------------------------------------------------


def test_nothing_outside_the_owners_group_is_ever_signalled(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path, stacks=str(tmp_path / "stacks"))
    r.table.groups[GROUP] = pytest_tree()
    r.table.groups[STRANGER] = [Proc(STRANGER, 1, STRANGER, 5.0, "python3 -m pytest -q")]
    r.table.leaders.add(STRANGER)
    r.reaper.tick()
    r.clock.sleep(600)
    assert r.reaper.tick().action == "killed"
    groups = {pgid for kind, pgid, _ in r.signaller.sent if kind == "group"}
    assert groups == {GROUP}
    members = {p.pid for p in pytest_tree()}
    processes = {pid for kind, pid, _ in r.signaller.sent if kind == "process"}
    assert processes <= members  # the stack-dump signal, to members only
    assert STRANGER in r.table.groups  # still running


def test_a_group_that_ignores_sigterm_is_killed_after_the_grace(tmp_path: Path) -> None:
    r = rig(tmp_path)
    r.signaller.lethal = (signal.SIGKILL,)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.reaper.tick()
    r.clock.sleep(600)
    started = r.clock.now()
    decision = r.reaper.tick()
    assert decision.action == "killed"
    signals = [sig for kind, pgid, sig in r.signaller.sent if kind == "group"]
    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert r.clock.now() - started >= r.cfg.grace_seconds


def test_a_push_without_a_group_of_its_own_is_never_killed(tmp_path: Path) -> None:
    """`acquire` from a shell: the group is the shell's, and may hold anything at all."""
    r = rig(tmp_path)
    held(r, tmp_path, dedicated=False)
    r.table.groups[GROUP] = pytest_tree()
    r.reaper.tick()
    r.clock.sleep(3601)
    decision = r.reaper.tick()
    assert decision.action == "refused"
    assert "group of its own" in decision.detail
    assert r.signaller.sent == [] and r.cfg.lock.is_dir()


def test_a_group_holding_a_protected_process_is_never_killed(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = [*pytest_tree(), Proc(GROUP + 7, GROUP, GROUP, 0.0, "ollama serve")]
    r.reaper.tick()
    r.clock.sleep(600)
    decision = r.reaper.tick()
    assert decision.action == "refused" and "ollama" in decision.detail
    assert r.signaller.sent == [] and r.cfg.lock.is_dir()


def test_a_group_that_no_longer_leads_its_session_is_never_signalled(tmp_path: Path) -> None:
    """Its id may have been reused by an unrelated process since the owner recorded it."""
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.table.leaders.clear()
    r.reaper.tick()
    r.clock.sleep(600)
    assert r.reaper.tick().action == "refused"
    assert r.signaller.sent == []


@pytest.mark.parametrize("pgid", [0, 1, os.getpgrp()])
def test_the_killer_refuses_groups_that_are_never_a_push(tmp_path: Path, pgid: int) -> None:
    r = rig(tmp_path)
    r.table.leaders.add(pgid)
    r.table.groups[pgid] = [Proc(pgid, 1, pgid, 0.0, "anything")]
    killer = push_gate.GroupKiller(r.cfg, r.table, r.signaller, r.clock)
    assert not killer.signallable(pgid)
    assert killer.stop(pgid) == "refused"
    assert r.signaller.sent == []


# --- evidence, the record and the verdict ---------------------------------------------------


def test_evidence_is_written_before_the_kill(tmp_path: Path) -> None:
    r = rig(tmp_path)
    # The directory `run` arms, under the gate's own state; no other is followed (#1105-2).
    held(r, tmp_path, stacks=str(r.cfg.state_dir / "stacks" / "tok-1"))
    r.table.groups[GROUP] = pytest_tree()
    seen: dict[str, object] = {}

    def at_the_kill() -> None:
        [folder] = (r.cfg.state_dir / "evidence").iterdir()
        seen["files"] = sorted(p.name for p in folder.iterdir())
        seen["tree"] = (folder / "process-tree.txt").read_text()
        seen["tail"] = (folder / "push-log-tail.txt").read_text()
        seen["verdict"] = (r.cfg.state_dir / "verdicts" / "tok-1.json").is_file()
        seen["dumped"] = [s for s in r.signaller.sent if s[0] == "process"]

    r.signaller.before_kill = at_the_kill
    r.reaper.tick()
    r.clock.sleep(600)
    assert r.reaper.tick().action == "killed"
    assert {"owner.json", "decision.json", "process-tree.txt", "push-log-tail.txt"} <= set(
        seen["files"]  # type: ignore[arg-type]
    )
    assert "pytest" in seen["tree"]  # type: ignore[operator]
    assert "gate line 99" in seen["tail"]  # type: ignore[operator]
    assert seen["verdict"] is True
    # py-spy is absent here, so the suite's own SIGUSR1 dump was asked of pytest and its
    # workers -- and of nothing else in the group.
    dumped = {pid for _, pid, sig in seen["dumped"] if sig == signal.SIGUSR1}  # type: ignore[union-attr]
    assert dumped == {GROUP + 2, GROUP + 3, GROUP + 4}


def test_py_spy_is_preferred_for_the_stacks_when_it_is_installed(tmp_path: Path) -> None:
    r = rig(tmp_path)
    ran: list[list[str]] = []

    def fake_run(argv: list[str]) -> tuple[int, str]:
        ran.append(argv)
        return 0, f"Thread 0x1 (idle): MainThread\n  sleep ({argv[-1]})"

    evidence = push_gate.EvidenceCollector(
        r.cfg, r.table, r.signaller, r.clock, which=lambda name: "/bin/py-spy", run=fake_run
    )
    held_by = held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    folder = evidence.collect(held_by, push_gate.Decision("killed", "idle", "", {}))
    assert [argv[:3] for argv in ran] == [["/bin/py-spy", "dump", "--pid"]] * 3
    assert "MainThread" in (folder / f"py-spy-{GROUP + 2}.txt").read_text()
    assert not [s for s in r.signaller.sent if s[0] == "process"]


def test_the_reap_log_is_append_only(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.alive_pids.clear()
    r.reaper.tick()
    first = r.cfg.reap_log.read_text()
    held(r, tmp_path, token="tok-2", pid=HOLDER + 1)
    r.reaper.tick()
    text = r.cfg.reap_log.read_text()
    assert text.startswith(first)
    assert [rec["owner"]["token"] for rec in reap_log(r)] == ["tok-1", "tok-2"]
    for record in reap_log(r):
        assert {"time", "condition", "action", "owner", "evidence"} <= set(record)


def test_the_pushing_lane_is_told_reaped_hang_not_a_test_failure(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.reaper.tick()
    r.clock.sleep(600)
    r.reaper.tick()
    verdict = push_gate.Verdicts(r.cfg).read("tok-1")
    assert verdict is not None
    assert push_gate.Verdicts.say(verdict).startswith("reaped: hang")
    # The owner's own release, arriving after the reap, reports the same thing.
    assert r.lock.release("tok-1", UID) == "free"


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.reaper.tick(dry_run=True)
    r.clock.sleep(600)
    decision = r.reaper.tick(dry_run=True)
    assert (decision.action, decision.condition) == ("would-kill", "idle")
    assert r.signaller.sent == [] and r.cfg.lock.is_dir()
    assert reap_log(r) == []
    assert not (r.cfg.state_dir / "verdicts").exists()


def test_a_free_lock_is_nothing_to_do(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.reaper.tick().action == "none"


def test_every_class_honours_the_interface_declared_beside_it(tmp_path: Path) -> None:
    """ADR-0016 / 9.b: each class has a Protocol beside it, and each conforms to it."""
    declared = _load("push_gate_interface", "interfaces/push_gate_interface.py")
    r = rig(tmp_path)
    table = push_gate.ProcessTable()
    signaller = push_gate.Signaller()
    clock = push_gate.Clock()
    pairs = [
        (r.cfg, declared.PushGateConfigInterface),
        (owner(r.clock, tmp_path), declared.OwnerInterface),
        (clock, declared.ClockInterface),
        (table, declared.ProcessTableInterface),
        (signaller, declared.SignallerInterface),
        (r.lock, declared.PushLockInterface),
        (push_gate.GroupKiller(r.cfg, table, signaller, clock), declared.GroupKillerInterface),
        (
            push_gate.EvidenceCollector(r.cfg, table, signaller, clock),
            declared.EvidenceCollectorInterface,
        ),
        (r.reaper, declared.ReaperInterface),
        (push_gate.Verdicts(r.cfg), declared.VerdictsInterface),
        (push_gate.Status(r.cfg, r.lock, table, clock), declared.StatusInterface),
        (push_gate.PushRunner(r.cfg, r.lock, clock), declared.PushRunnerInterface),
        (push_gate.OwnerlessHolder(r.cfg, table), declared.OwnerlessHolderInterface),
        (
            push_gate.Schedule(r.cfg, tmp_path, TOOLS / "push_gate.py", "python3"),
            declared.ScheduleInterface,
        ),
        # And the fakes above stand in for exactly those seams.
        (r.clock, declared.ClockInterface),
        (r.table, declared.ProcessTableInterface),
        (r.signaller, declared.SignallerInterface),
    ]
    for instance, interface in pairs:
        assert isinstance(instance, interface), interface.__name__


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("0:00.03", 0.03), ("12:34.56", 754.56), ("1:02:03", 3723.0), ("2-01:00:00", 176400.0)],
)
def test_ps_cpu_time_is_read_in_both_spellings(text: str, seconds: float) -> None:
    """macOS prints M:SS.ss; procps prints [D-]HH:MM:SS."""
    assert push_gate.ProcessTable.cpu_seconds(text) == pytest.approx(seconds)


def test_the_storm_cycle_runs_the_reaper_before_anything_that_can_take_long() -> None:
    """One scheduler, not two: the outer cycle that already runs the evidence job reaps."""
    source = (TOOLS / "storm-cycle.py").read_text(encoding="utf-8")
    assert '"push_gate.py"' in source and '"reap"' in source
    assert source.index('"push_gate.py"') < source.index('"lane-publish.py"')


# --- real processes -------------------------------------------------------------------------


def _storm(tmp_path: Path, **keys: object) -> Path:
    root = tmp_path / "storm"
    root.mkdir()
    body = "".join(f"{key} = {value}\n" for key, value in keys.items())
    (root / "storm.toml").write_text(
        f'[push_gate]\nlock = "{tmp_path / ".push-lock"}"\n'
        f'state_dir = "{tmp_path / "gate"}"\n{body}',
        encoding="utf-8",
    )
    return root


def _run(root: Path, *argv: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(TOOLS / "push_gate.py"), "--root", str(root), "run", "--", *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _wait_for_owner(cfg: PushGateConfig, timeout: float = 30.0) -> Owner:
    lock = push_gate.PushLock(cfg, push_gate.Clock())
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = lock.state()
        if state.owner is not None and state.owner.pgid is not None:
            return state.owner
        time.sleep(0.05)
    raise AssertionError("the push never took the lock")


def _real_reaper(cfg: PushGateConfig):  # noqa: ANN202 - a Reaper
    clock = push_gate.Clock()
    table = push_gate.ProcessTable()
    signaller = push_gate.Signaller()
    return push_gate.Reaper(
        cfg,
        push_gate.PushLock(cfg, clock),
        table,
        push_gate.EvidenceCollector(cfg, table, signaller, clock),
        push_gate.GroupKiller(cfg, table, signaller, clock),
        clock,
    )


SLEEPER = ["python3", "-c", "import time; print('gate running', flush=True); time.sleep(120)"]


def _reap_until_acted(cfg: PushGateConfig, limit: float = 30.0):  # noqa: ANN202 - a Decision
    reaper = _real_reaper(cfg)
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        decision = reaper.tick()
        # "unknown" is where a sandboxed pass sits until a condition that needs no `ps` holds.
        if decision.action not in {"none", "unknown"}:
            return decision
        time.sleep(0.2)
    raise AssertionError("the reaper never acted")


@pytest.mark.skipif(
    push_gate.ProcessTable().members(os.getpgrp()) is None,
    reason="`ps` cannot be run here (the sandbox refuses it), so CPU cannot be sampled",
)
def test_a_real_sleeping_push_under_the_lock_is_reaped_as_idle(tmp_path: Path) -> None:
    root = _storm(tmp_path, idle_cpu_seconds=0.5, idle_window_seconds=1.5, kill_grace_seconds=2)
    cfg = PushGateConfig.declared(root)
    push = _run(root, *SLEEPER)
    try:
        held_by = _wait_for_owner(cfg)
        decision = _reap_until_acted(cfg)
        assert (decision.action, decision.condition) == ("killed", "idle"), decision
        out, _ = push.communicate(timeout=30)
    finally:
        push.kill()
    assert push.returncode == push_gate.REAPED_EXIT, out
    assert "reaped: hang" in out and "gate running" in out
    assert not cfg.lock.exists()
    with pytest.raises(ProcessLookupError):
        os.killpg(held_by.pgid, 0)
    [record] = [json.loads(line) for line in cfg.reap_log.read_text().splitlines()]
    assert record["condition"] == "idle"
    assert "time.sleep(120)" in (Path(record["evidence"]) / "process-tree.txt").read_text()


def test_a_real_push_past_the_wall_ceiling_is_reaped(tmp_path: Path) -> None:
    root = _storm(tmp_path, wall_ceiling_seconds=1, kill_grace_seconds=2)
    cfg = PushGateConfig.declared(root)
    push = _run(root, *SLEEPER)
    try:
        held_by = _wait_for_owner(cfg)
        decision = _reap_until_acted(cfg)
        assert (decision.action, decision.condition) == ("killed", "ceiling"), decision
        out, _ = push.communicate(timeout=30)
    finally:
        push.kill()
    assert push.returncode == push_gate.REAPED_EXIT, out
    assert "reaped: hang" in out
    assert not cfg.lock.exists()
    with pytest.raises(ProcessLookupError):
        os.killpg(held_by.pgid, 0)


def test_run_passes_the_push_result_through_and_always_releases(tmp_path: Path) -> None:
    root = _storm(tmp_path)
    cfg = PushGateConfig.declared(root)
    push = _run(root, "python3", "-c", "print('pushed'); raise SystemExit(3)")
    out, _ = push.communicate(timeout=60)
    assert push.returncode == 3, out
    assert "pushed" in out and "reaped" not in out
    assert not cfg.lock.exists()
    [log] = (cfg.state_dir / "logs").iterdir()
    assert "pushed" in log.read_text()


def test_run_releases_the_lock_when_it_is_signalled(tmp_path: Path) -> None:
    root = _storm(tmp_path, kill_grace_seconds=2)
    cfg = PushGateConfig.declared(root)
    push = _run(root, *SLEEPER)
    try:
        held_by = _wait_for_owner(cfg)
        push.send_signal(signal.SIGTERM)
        out, _ = push.communicate(timeout=30)
    finally:
        push.kill()
    assert push.returncode == 128 + signal.SIGTERM, out
    assert not cfg.lock.exists()
    with pytest.raises(ProcessLookupError):
        os.killpg(held_by.pgid, 0)


def test_run_waits_for_a_held_lock_and_takes_it_when_released(tmp_path: Path) -> None:
    root = _storm(tmp_path, poll_seconds=0.1)
    cfg = PushGateConfig.declared(root)
    lock = push_gate.PushLock(cfg, push_gate.Clock())
    first = owner(push_gate.Clock(), tmp_path, pid=os.getpid(), pgid=None, dedicated=False)
    assert lock.acquire(first)
    push = _run(root, "python3", "-c", "print('second push')")
    try:
        time.sleep(1.0)
        assert push.poll() is None  # still waiting its turn
        assert lock.release(first.token, UID) == "released"
        out, _ = push.communicate(timeout=60)
    finally:
        push.kill()
    assert push.returncode == 0 and "second push" in out


def test_the_shell_recipe_acquires_and_releases_by_token(tmp_path: Path) -> None:
    root = _storm(tmp_path)
    cfg = PushGateConfig.declared(root)
    tool = [sys.executable, str(TOOLS / "push_gate.py"), "--root", str(root)]
    script = textwrap.dedent(
        f"""
        token=$({" ".join(tool)} acquire) || exit 9
        test -d {cfg.lock} || exit 8
        {" ".join(tool)} release nobody && exit 7
        {" ".join(tool)} release "$token"
        """
    )
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not cfg.lock.exists()


# --- a bare `mkdir` lock: find the push that holds it, by process ---------------------------

SHELL = 900  # the legacy recipe's shell: `until mkdir ...; do sleep 20; done; git push ...`
PUSH = 901  # the `git push` it started a second after it took the lock


def bare_lock(r: Rig) -> float:
    """Take the lock the old way, dated on the fake clock so the ceiling is measurable."""
    r.cfg.lock.mkdir()
    made = r.clock.now()
    os.utime(r.cfg.lock, (made, made))
    return made


def legacy_push(r: Rig, tmp_path: Path, made: float, **push: object) -> None:
    """The legacy recipe's process group: its shell, git push, the hook, pytest, workers."""
    lane = str(tmp_path / "lane")
    git = Proc(PUSH, SHELL, SHELL, 0.1, "git push origin HEAD:feat/old-recipe", started_at=made + 1)
    git = dataclasses.replace(git, **push)
    r.table.groups[SHELL] = [
        Proc(SHELL, 800, SHELL, 0.0, "/bin/bash -c until mkdir x; do sleep 20; done", made - 40),
        git,
        Proc(PUSH + 1, PUSH, SHELL, 0.2, "/bin/sh .git/hooks/pre-push origin", made + 2),
        Proc(
            PUSH + 2, PUSH + 1, SHELL, 50.0, "/x/.venv/bin/python3 /x/.venv/bin/pytest -q", made + 3
        ),
        Proc(
            PUSH + 3,
            PUSH + 2,
            SHELL,
            50.0,
            "/x/.venv/bin/python3 -u -c import sys;exec(eval(sys.stdin.readline()))",
            made + 4,
        ),
    ]
    # The agent that started the shell: another group, never a candidate, never touched.
    r.table.groups[800] = [Proc(800, 1, 800, 900.0, "node claude", made - 3600)]
    r.table.cwds[PUSH] = lane


def test_a_bare_mkdir_lock_is_traced_to_its_push_and_reaped_when_idle(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    assert r.reaper.tick().action == "none"
    r.clock.sleep(600)
    decision = r.reaper.tick()
    assert (decision.action, decision.condition) == ("killed", "idle"), decision
    assert {pgid for kind, pgid, _ in r.signaller.sent if kind == "group"} == {SHELL}
    assert 800 in r.table.groups  # the agent's own group is untouched
    assert not r.cfg.lock.exists()  # the shell that would have removed it is gone
    [record] = reap_log(r)
    assert record["ownerless"] is True
    assert record["owner"]["pid"] == PUSH and record["owner"]["pgid"] == SHELL
    assert "git push" in (Path(record["evidence"]) / "process-tree.txt").read_text()


def test_a_bare_mkdir_lock_past_the_ceiling_is_reaped(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    r.clock.sleep(3601)
    decision = r.reaper.tick()
    assert (decision.action, decision.condition) == ("killed", "ceiling"), decision


def test_a_busy_bare_mkdir_push_is_left_alone(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    for _ in range(5):
        assert r.reaper.tick().action == "none"
        r.clock.sleep(600)
        r.table.burn(SHELL, 40.0)
    assert r.signaller.sent == [] and r.cfg.lock.is_dir()


def _never_killed(r: Rig, reason: str) -> None:
    r.reaper.tick()
    r.clock.sleep(3601)
    decision = r.reaper.tick()
    assert decision.action == "unknown", decision
    assert reason in decision.detail, decision.detail
    assert r.signaller.sent == [] and r.cfg.lock.is_dir()
    assert reap_log(r) == []


def test_two_candidate_pushes_are_unknown_and_never_killed(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    r.table.groups[1200] = [Proc(1200, 1, 1200, 0.0, "git push origin HEAD:other", made + 2)]
    r.table.cwds[1200] = str(tmp_path / "other-lane")
    _never_killed(r, "2 pushes")


def test_a_push_that_started_well_after_the_lock_is_not_its_holder(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made, started_at=made + 30)
    _never_killed(r, "no push")


def test_a_push_outside_the_declared_worktrees_is_not_its_holder(tmp_path: Path) -> None:
    r = rig(tmp_path, worktree_roots=(tmp_path / "somewhere-else",))
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    _never_killed(r, "no push")


def test_a_push_whose_cwd_is_unreadable_is_not_its_holder(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    r.table.cwds.clear()
    _never_killed(r, "no push")


def test_git_dash_c_names_the_worktree_when_the_cwd_cannot_be_read(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made, command=f"git -C {tmp_path / 'lane'} push origin HEAD:x")
    r.table.cwds.clear()
    r.reaper.tick()
    r.clock.sleep(600)
    assert r.reaper.tick().action == "killed"


def test_a_group_holding_anything_but_the_push_recipe_is_never_killed(tmp_path: Path) -> None:
    """A shell's group can hold whatever that shell started; only the recipe is ours."""
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    r.table.groups[SHELL].append(Proc(990, SHELL, SHELL, 0.0, "node some-editor-server", made))
    _never_killed(r, "outside the push")


def test_a_bare_mkdir_lock_with_an_unreadable_table_is_unknown(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    r.table.readable = False
    _never_killed(r, "cannot be read")


def test_a_bare_mkdir_lock_under_dry_run_changes_nothing(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    r.reaper.tick(dry_run=True)
    r.clock.sleep(600)
    assert r.reaper.tick(dry_run=True).action == "would-kill"
    assert r.signaller.sent == [] and r.cfg.lock.is_dir() and reap_log(r) == []


def test_status_names_the_push_behind_a_bare_mkdir_lock(tmp_path: Path) -> None:
    r = rig(tmp_path)
    made = bare_lock(r)
    legacy_push(r, tmp_path, made)
    text = push_gate.Status(r.cfg, r.lock, r.table, r.clock).render()
    assert "no owner record" in text
    assert f"pid {PUSH}" in text and "git push origin HEAD:feat/old-recipe" in text


@pytest.mark.parametrize(
    ("command", "is_push"),
    [
        ("git push origin HEAD:x", True),
        ("/usr/bin/git push -u origin b", True),
        ("git -C /a/b push", True),
        ("git -c core.x=1 push", True),
        ("git pack-objects --stdout", False),
        ("/bin/sh .git/hooks/pre-push origin", False),
        ("git status push", False),
        ("python3 push.py", False),
    ],
)
def test_only_a_git_push_is_ever_a_candidate(command: str, is_push: bool) -> None:
    assert push_gate.OwnerlessHolder.is_git_push(command) is is_push


# --- overlapping passes -----------------------------------------------------------------------


def test_two_overlapping_reap_passes_never_act_twice(tmp_path: Path) -> None:
    r = rig(tmp_path)
    held(r, tmp_path)
    r.table.groups[GROUP] = pytest_tree()
    r.reaper.tick()
    r.clock.sleep(600)
    import fcntl

    r.cfg.state_dir.mkdir(parents=True, exist_ok=True)
    with (r.cfg.state_dir / push_gate.REAP_LOCK).open("a") as other:
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)  # a second pass, mid-flight
        decision = r.reaper.tick()
        assert decision.action == "none" and "another reap pass" in decision.detail
        assert r.signaller.sent == []
    assert r.reaper.tick().action == "killed"
    assert r.reaper.tick().action == "none"  # and again: nothing left to do
    assert len(reap_log(r)) == 1


# --- the schedule, declared as code ------------------------------------------------------------


@dataclass
class Commands:
    ran: list[list[str]] = field(default_factory=list)
    answers: dict[str, int] = field(default_factory=dict)

    def __call__(self, argv: list[str]) -> tuple[int, str]:
        self.ran.append(argv)
        return self.answers.get(argv[0], 0), ""


def schedule(tmp_path: Path, target: str, **overrides: object):  # noqa: ANN201 - a Schedule
    cfg = config(tmp_path, **overrides)
    commands = Commands()
    made = push_gate.Schedule(
        cfg,
        root=tmp_path / "storm",
        tool=TOOLS / "push_gate.py",
        python="/usr/bin/python3",
        target=target,
        home=tmp_path / "home",
        run=commands,
    )
    return made, commands, cfg


def test_the_default_schedule_runs_the_reaper_every_minute_or_two(tmp_path: Path) -> None:
    root = tmp_path / "storm"
    root.mkdir()
    assert 60 <= PushGateConfig.declared(root).schedule_seconds <= 120
    (root / "storm.toml").write_text("[push_gate]\nschedule_seconds = 75\n")
    assert PushGateConfig.declared(root).schedule_seconds == 75


def test_install_schedule_on_macos_writes_a_launch_agent_and_bootstraps_it(tmp_path: Path) -> None:
    import plistlib

    made, commands, cfg = schedule(tmp_path, "launchd")
    made.install()
    [plist] = (tmp_path / "home/Library/LaunchAgents").glob("*.plist")
    agent = plistlib.loads(plist.read_bytes())
    assert agent["Label"] == cfg.schedule_label
    assert agent["StartInterval"] == int(cfg.schedule_seconds)
    assert agent["ProgramArguments"][-1] == "reap"
    assert str(cfg.lock) in agent["ProgramArguments"]  # the lock the installer resolved
    assert agent["ProgramArguments"][:2] == ["/usr/bin/python3", str(TOOLS / "push_gate.py")]
    assert ["launchctl", "bootstrap", f"gui/{UID}", str(plist)] in commands.ran


def test_install_schedule_on_linux_writes_a_systemd_user_timer(tmp_path: Path) -> None:
    made, commands, cfg = schedule(tmp_path, "systemd")
    made.install()
    units = tmp_path / "home/.config/systemd/user"
    service = (units / f"{cfg.schedule_label}.service").read_text()
    timer = (units / f"{cfg.schedule_label}.timer").read_text()
    assert "reap" in service and "Type=oneshot" in service
    assert f"OnUnitActiveSec={int(cfg.schedule_seconds)}" in timer
    assert ["systemctl", "--user", "enable", "--now", f"{cfg.schedule_label}.timer"] in commands.ran


def test_install_schedule_dry_run_writes_and_runs_nothing(tmp_path: Path) -> None:
    made, commands, _ = schedule(tmp_path, "launchd")
    lines = made.install(dry_run=True)
    assert not (tmp_path / "home").exists() and commands.ran == []
    assert any("launchctl bootstrap" in line for line in lines)


def test_uninstall_schedule_removes_what_install_wrote(tmp_path: Path) -> None:
    for target in ("launchd", "systemd"):
        made, commands, _ = schedule(tmp_path / target, target)
        made.install()
        made.uninstall()
        assert not [p for p in (tmp_path / target / "home").rglob("*") if p.is_file()]


def test_schedule_status_says_installed_or_not(tmp_path: Path) -> None:
    made, commands, _ = schedule(tmp_path, "launchd")
    assert "not installed" in made.status()
    made.install()
    assert "installed" in made.status() and "not installed" not in made.status()
    commands.answers["launchctl"] = 113
    assert "not loaded" in made.status()


def test_the_cron_target_prints_a_line_and_touches_no_crontab(tmp_path: Path) -> None:
    made, commands, cfg = schedule(tmp_path, "cron")
    lines = made.install()
    assert commands.ran == []
    [line] = [line for line in lines if line.startswith("* * * * *")]
    assert "reap" in line and str(cfg.lock) in line


def test_the_schedule_templates_are_files_in_the_repository() -> None:
    """Everything-as-code (12.c): the units are tracked templates, not strings in a program."""
    templates = TOOLS / "templates"
    for name in ("push-gate-reaper.plist", "push-gate-reaper.service", "push-gate-reaper.timer"):
        assert (templates / name).is_file(), name


# --- every storm tool that pushes, pushes through the gate -------------------------------------


def test_no_storm_tool_pushes_around_the_gate() -> None:
    """A raw `git push` in a storm tool is a gate run the push lock never sees."""
    offenders = []
    for tool in sorted(TOOLS.glob("*.py")):
        if tool.name == "push_gate.py":
            continue
        text = tool.read_text(encoding="utf-8")
        if re.search(r"""\[\s*["']git["']\s*,\s*["']push["']""", text):
            offenders.append(tool.name)
    assert offenders == []
    for tool in ("lane-publish.py", "storm-snapshot.py"):
        text = (TOOLS / tool).read_text(encoding="utf-8")
        assert '"push_gate.py"' in text and '"run"' in text, tool


# --- which lock: declared, never guessed ---------------------------------------------------


def test_a_checkout_copy_with_no_declared_lock_refuses_rather_than_lock_alone(
    tmp_path: Path,
) -> None:
    """Run from a repository checkout, the derived lock would be private to that checkout."""
    checkout = tmp_path / "checkout"
    (checkout / "plans").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    tool = [sys.executable, str(TOOLS / "push_gate.py"), "--root", str(checkout / "plans")]
    env = {k: v for k, v in os.environ.items() if k != "VIBEY_PUSH_LOCK"}
    done = subprocess.run([*tool, "status"], capture_output=True, text=True, env=env, timeout=60)
    assert done.returncode == 2 and "VIBEY_PUSH_LOCK" in done.stderr
    env["VIBEY_PUSH_LOCK"] = str(tmp_path / "shared-lock")
    done = subprocess.run([*tool, "status"], capture_output=True, text=True, env=env, timeout=60)
    assert done.returncode == 0 and str(tmp_path / "shared-lock") in done.stdout


# --- a real legacy push, traced by process ---------------------------------------------------


@pytest.mark.skipif(
    push_gate.ProcessTable().processes() is None
    or push_gate.ProcessTable().cwd(os.getpid()) is None,
    reason="`ps` or the cwd probe cannot be run here (the sandbox refuses them)",
)
def test_a_real_bare_mkdir_push_is_traced_and_reaped(tmp_path: Path) -> None:
    lane = tmp_path / "lane"
    remote = tmp_path / "remote.git"
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", str(lane)], check=True)
    subprocess.run([*git, "-C", str(lane), "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    subprocess.run(["git", "-C", str(lane), "remote", "add", "origin", str(remote)], check=True)
    hook = lane / ".git/hooks/pre-push"
    hook.write_text("#!/bin/sh\nsleep 120\n")
    hook.chmod(0o755)
    root = _storm(
        tmp_path,
        idle_cpu_seconds=0.5,
        idle_window_seconds=1.5,
        kill_grace_seconds=2,
        worktree_roots=f'["{tmp_path}"]',
    )
    cfg = PushGateConfig.declared(root)
    recipe = f"mkdir {cfg.lock} && git push origin HEAD:main; rmdir {cfg.lock}"
    shell = subprocess.Popen(["bash", "-c", recipe], cwd=lane, start_new_session=True)
    try:
        decision = _reap_until_acted(cfg)
        assert (decision.action, decision.condition) == ("killed", "idle"), decision
        shell.wait(timeout=30)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(shell.pid, signal.SIGKILL)
    assert not cfg.lock.exists()
    [record] = [json.loads(line) for line in cfg.reap_log.read_text().splitlines()]
    assert record["ownerless"] is True
