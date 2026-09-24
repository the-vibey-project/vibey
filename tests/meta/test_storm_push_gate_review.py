# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Regression tests for the independent review of #1105 and #1107 (the push gate).

The review found that the reaper, which #1107 put on an unattended schedule, could release a
lock mid-push, write outside its own state, record kills it never observed, kill a protected
program, count laptop sleep as a hang, and signal a shell after the push it had judged had
finished. Each test here is named for its finding (#1105-N or #1107-N) and was written, and
seen to fail, before the fix. The reviewer's probes (r1107-probes/probes.py, probes2.py,
P1-P12) are each one of these tests.

Fakes where timing must be exact; real processes, real locks and a real `bash` where the bug
lived in what a real shell does.
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import importlib.util
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "docs/plans/qwenstorm-3.0.0/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, filename: str):  # noqa: ANN202 - a module object
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


push_gate = _load("push_gate", "push_gate.py")
Owner = push_gate.Owner
Proc = push_gate.Proc
PushGateConfig = push_gate.PushGateConfig

UID = os.getuid()
HOLDER = 4242
GROUP = 4300
PS_READABLE = push_gate.ProcessTable().processes() is not None


# --- fakes --------------------------------------------------------------------------------


class FakeClock:
    """Wall time `t`, awake time `a` (stops while the machine sleeps), and a boot id."""

    def __init__(self) -> None:
        self.t = 1_000_000.0
        self.a = 5_000.0
        self.boot = "boot-1"

    def now(self) -> float:
        return self.t

    def awake(self) -> float:
        return self.a

    def boot_id(self) -> str:
        return self.boot

    def sleep(self, seconds: float) -> None:
        self.t += seconds
        self.a += seconds

    def suspend(self, seconds: float) -> None:
        """The laptop lid closes: wall time passes, nothing runs."""
        self.t += seconds


@dataclass
class FakeTable:
    alive_pids: set[int] = field(default_factory=lambda: {HOLDER})
    groups: dict[int, list] = field(default_factory=dict)
    leaders: set[int] = field(default_factory=lambda: {GROUP})
    foreign: set[int] = field(default_factory=set)
    readable: bool = True
    cwds: dict[int, str] = field(default_factory=dict)
    starts: dict[int, float] = field(default_factory=dict)

    def alive(self, pid: int) -> bool:
        return pid in self.alive_pids

    def group_alive(self, pgid: int) -> bool:
        return bool(self.groups.get(pgid))

    def group_ours(self, pgid: int) -> bool:
        return bool(self.groups.get(pgid)) and pgid not in self.foreign

    def members(self, pgid: int) -> list | None:
        return None if not self.readable else list(self.groups.get(pgid, []))

    def processes(self) -> list | None:
        return None if not self.readable else [p for g in self.groups.values() for p in g]

    def listing(self) -> str | None:
        return None if not self.readable else "listing"

    def session_leader(self, pgid: int) -> bool:
        return pgid in self.leaders

    def cwd(self, pid: int) -> str | None:
        return self.cwds.get(pid)

    def started(self, pid: int) -> float | None:
        return self.starts.get(pid)

    def burn(self, pgid: int, seconds: float) -> None:
        group = self.groups[pgid]
        self.groups[pgid] = [
            dataclasses.replace(p, cpu_seconds=p.cpu_seconds + seconds / len(group)) for p in group
        ]


@dataclass
class FakeSignaller:
    table: FakeTable
    lethal: tuple[int, ...] = (signal.SIGTERM, signal.SIGKILL)
    sent: list[tuple[str, int, int]] = field(default_factory=list)

    def send_group(self, pgid: int, sig: int) -> bool:
        self.sent.append(("group", pgid, sig))
        if not self.table.groups.get(pgid):
            return False
        if sig in self.lethal:
            self.table.groups.pop(pgid, None)
        return True

    def send_process(self, pid: int, sig: int) -> bool:
        self.sent.append(("process", pid, sig))
        return True


def config(tmp_path: Path, **overrides: object) -> PushGateConfig:
    values: dict[str, object] = {
        "lock": tmp_path / ".push-lock",
        "state_dir": tmp_path / "gate",
        "reap_log": tmp_path / "gate" / "reaps.jsonl",
        "grace_seconds": 30.0,
        "stack_wait_seconds": 0.0,
        "protected": ("ollama", "vibey-runner"),
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
    evidence: object


def rig(tmp_path: Path, evidence_class: type | None = None, **overrides: object) -> Rig:
    cfg = config(tmp_path, **overrides)
    clock, table = FakeClock(), FakeTable()
    signaller = FakeSignaller(table)
    lock = push_gate.PushLock(cfg, clock)
    evidence = (evidence_class or push_gate.EvidenceCollector)(
        cfg, table, signaller, clock, which=lambda name: None
    )
    killer = push_gate.GroupKiller(cfg, table, signaller, clock)
    reaper = push_gate.Reaper(cfg, lock, table, evidence, killer, clock)
    return Rig(cfg, clock, table, signaller, lock, reaper, evidence)


def owner(r: Rig, **overrides: object) -> Owner:
    values: dict[str, object] = {
        "token": "tok-1",
        "pid": HOLDER,
        "pgid": GROUP,
        "dedicated": True,
        "uid": UID,
        "branch": "feat/x",
        "worktree": "/w",
        "started_at": r.clock.now(),
        "command": ["git", "push"],
    }
    values.update(overrides)
    return Owner(**values)  # type: ignore[arg-type]


def gate_tree(command: str = "git push origin HEAD:feat/x") -> list:
    return [
        Proc(GROUP, HOLDER, GROUP, 0.1, command),
        Proc(GROUP + 1, GROUP, GROUP, 50.0, "/v/bin/python3 /v/bin/pytest -q"),
    ]


def reap_log(r: Rig) -> list[dict]:
    if not r.cfg.reap_log.exists():
        return []
    return [json.loads(line) for line in r.cfg.reap_log.read_text().splitlines()]


def idle_reap(r: Rig) -> object:
    """Two passes a full idle window apart over an unchanging tree."""
    r.reaper.tick()
    r.clock.sleep(r.cfg.idle_window_seconds)
    return r.reaper.tick()


def forge(cfg: PushGateConfig, **record: object) -> None:
    """Write an owner.json by hand, as anything able to write the lock directory could."""
    cfg.lock.mkdir(parents=True)
    base = {"pid": 999_999, "pgid": None, "dedicated": True, "uid": UID, "branch": "b",
            "worktree": "/", "started_at": 0.0, "command": ["git", "push"]}  # fmt: skip
    base.update(record)
    (cfg.lock / push_gate.OWNER_FILE).write_text(json.dumps(base))


def tool(root: Path, *argv: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / "push_gate.py"), "--root", str(root), *argv],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def storm(tmp_path: Path, **keys: object) -> Path:
    root = tmp_path / "storm"
    root.mkdir()
    body = "".join(f"{key} = {value}\n" for key, value in keys.items())
    (root / "storm.toml").write_text(
        f'[push_gate]\nlock = "{tmp_path / ".push-lock"}"\n'
        f'state_dir = "{tmp_path / "gate"}"\n{body}'
    )
    return root


# --- #1105-1: the acquire recipe is released as stale mid-push --------------------------------


def test_1105_1_acquire_from_command_substitution_is_not_stale_mid_push(tmp_path: Path) -> None:
    """Probe P12: `$(push_gate.py acquire)` runs in a subshell that exits at once, so its
    parent pid is dead long before the push ends. The holder is the caller's group."""
    root = storm(tmp_path)
    cfg = PushGateConfig.declared(root)
    gate = f"{sys.executable} {TOOLS / 'push_gate.py'} --root {root}"
    marker = tmp_path / "pushed"
    script = f'tok=$({gate} acquire) || exit 9; sleep 4; touch {marker}; {gate} release "$tok"'
    shell = subprocess.Popen(["bash", "-c", script], start_new_session=True)
    try:
        lock = push_gate.PushLock(cfg, push_gate.Clock())
        deadline = time.monotonic() + 20
        while lock.state().owner is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert lock.state().owner is not None, "the recipe never took the lock"
        clock, table, signaller = push_gate.Clock(), push_gate.ProcessTable(), push_gate.Signaller()
        reaper = push_gate.Reaper(
            cfg,
            lock,
            table,
            push_gate.EvidenceCollector(cfg, table, signaller, clock),
            push_gate.GroupKiller(cfg, table, signaller, clock),
            clock,
        )
        decision = reaper.tick()
        assert decision.action not in {"released", "killed"}, decision
        assert cfg.lock.is_dir(), "the lock was released under a push that was still running"
        assert shell.wait(timeout=30) == 0
        assert marker.exists() and not cfg.lock.exists()
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(shell.pid, signal.SIGKILL)


def test_1105_1_the_acquire_holder_is_the_callers_group_leader(tmp_path: Path) -> None:
    root = storm(tmp_path)
    cfg = PushGateConfig.declared(root)
    gate = f"{sys.executable} {TOOLS / 'push_gate.py'} --root {root}"
    done = subprocess.run(
        ["bash", "-c", f'tok=$({gate} acquire --pid $$) && echo "$$ $tok"'],
        capture_output=True,
        text=True,
        timeout=60,
        start_new_session=True,
    )
    shell_pid, _ = done.stdout.split()
    record = json.loads((cfg.lock / push_gate.OWNER_FILE).read_text())
    assert record["pgid"] == int(shell_pid) and record["dedicated"] is False


def test_1105_1_release_of_a_free_lock_is_an_error(tmp_path: Path) -> None:
    root = storm(tmp_path)
    done = tool(root, "release", "never-taken")
    assert done.returncode == 1, done
    assert "free" in done.stderr


def test_1105_1_the_stale_message_claims_only_what_it_checked(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r, dedicated=False, pgid=None))
    r.table.alive_pids.clear()
    decision = r.reaper.tick()
    assert decision.action == "released"
    assert "nothing of its push is left running" not in decision.detail


# --- #1105-2: owner.json and the log path are untrusted -----------------------------------------


def test_1105_2_a_forged_token_cannot_write_outside_the_state_dir(tmp_path: Path) -> None:
    """Probe P1: token "./../../OUTSIDE/clobbered" and log ~/.gitconfig."""
    cfg = config(tmp_path, grace_seconds=1.0)
    outside = tmp_path / "OUTSIDE"
    outside.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET-CONTENT\n")
    victim = subprocess.Popen(["sleep", "60"], start_new_session=True)
    try:
        forge(cfg, token="./../../OUTSIDE/clobbered", pid=victim.pid, pgid=victim.pid,
              log=str(secret))  # fmt: skip
        clock, table, signaller = push_gate.Clock(), push_gate.ProcessTable(), push_gate.Signaller()
        reaper = push_gate.Reaper(
            cfg,
            push_gate.PushLock(cfg, clock),
            table,
            push_gate.EvidenceCollector(cfg, table, signaller, clock),
            push_gate.GroupKiller(cfg, table, signaller, clock),
            clock,
        )
        decision = reaper.tick()
        assert decision.action == "unknown", decision
        written = [p for p in tmp_path.rglob("*") if "clobbered" in p.name]
        assert written == []
        for tail in tmp_path.rglob("push-log-tail.txt"):
            assert "SECRET-CONTENT" not in tail.read_text()
        assert victim.poll() is None, "a forged record got a process killed"
    finally:
        victim.kill()
        victim.wait()


def test_1105_2_an_owner_log_outside_the_gates_logs_is_never_read(tmp_path: Path) -> None:
    r = rig(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET-CONTENT\n")
    assert r.lock.acquire(owner(r, log=str(secret)))
    r.table.groups[GROUP] = gate_tree()
    assert idle_reap(r).action == "killed"
    [folder] = (r.cfg.state_dir / "evidence").iterdir()
    assert "SECRET-CONTENT" not in (folder / "push-log-tail.txt").read_text()
    assert "SECRET-CONTENT" not in push_gate.Status(r.cfg, r.lock, r.table, r.clock).render()


def test_1105_2_a_symlinked_owner_record_is_refused(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    elsewhere = tmp_path / "planted.json"
    elsewhere.write_text(json.dumps({"token": "tok-9", "pid": 1, "pgid": 1, "dedicated": True,
                                     "uid": UID, "branch": "b", "worktree": "/",
                                     "started_at": 0.0}))  # fmt: skip
    cfg.lock.mkdir()
    (cfg.lock / push_gate.OWNER_FILE).symlink_to(elsewhere)
    state = push_gate.PushLock(cfg, FakeClock()).state()
    assert state.kind == "untrusted" and state.owner is None


def test_1105_2_a_symlinked_lock_directory_is_refused(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    real = tmp_path / "real-lock"
    real.mkdir()
    cfg.lock.symlink_to(real)
    assert push_gate.PushLock(cfg, FakeClock()).state().kind == "untrusted"


def test_1105_2_a_lock_owned_by_another_uid_is_untrusted(tmp_path: Path, monkeypatch) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r))
    monkeypatch.setattr(push_gate.os, "getuid", lambda: UID + 1)
    assert r.lock.state().kind == "untrusted"
    r.table.groups[GROUP] = gate_tree()
    assert r.reaper.tick().action == "unknown"
    assert r.signaller.sent == []


def test_1105_2_the_state_dir_is_private(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r))
    assert stat.S_IMODE(r.cfg.state_dir.stat().st_mode) == 0o700


def test_1105_2_a_planted_symlink_is_never_written_through(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    target = tmp_path / "victim.txt"
    target.write_text("original\n")
    verdicts = cfg.state_dir / "verdicts"
    verdicts.mkdir(parents=True)
    (verdicts / ".tok-1.tmp").symlink_to(target)
    (verdicts / "tok-1.json").symlink_to(target)
    push_gate.Verdicts(cfg).write("tok-1", {"verdict": "reaped"})
    assert target.read_text() == "original\n"
    assert push_gate.Verdicts(cfg).read("tok-1") == {"verdict": "reaped"}


# --- #1105-3: kills recorded that were never observed -------------------------------------------


class EndsDuringEvidence(push_gate.EvidenceCollector):
    """Probe P3: the push finishes while py-spy (or the SIGUSR1 wait) runs."""

    def collect(self, owner, decision):  # noqa: ANN001, ANN201
        folder = super().collect(owner, decision)
        self._table.groups.pop(owner.pgid, None)
        return folder


def test_1105_3_a_group_that_ends_during_evidence_is_not_recorded_as_killed(tmp_path: Path) -> None:
    r = rig(tmp_path, evidence_class=EndsDuringEvidence)
    assert r.lock.acquire(owner(r))
    r.table.groups[GROUP] = gate_tree()
    decision = idle_reap(r)
    assert decision.action != "killed", decision
    assert [rec for rec in reap_log(r) if rec["action"] == "killed"] == []
    assert push_gate.Verdicts(r.cfg).read("tok-1") is None


def test_1105_3_a_group_of_another_uid_is_refused_not_killed(tmp_path: Path, monkeypatch) -> None:
    """Probe P4: EPERM from kill(0) means "not ours", never "alive and signalled"."""
    other = subprocess.Popen(["sleep", "30"], start_new_session=True)  # stands in for a stranger's
    real_killpg = os.killpg
    attempted: list[int] = []

    def eperm(pgid: int, sig: int) -> None:
        if pgid != other.pid:
            return real_killpg(pgid, sig)
        attempted.append(sig)
        raise PermissionError(1, "Operation not permitted")

    try:
        monkeypatch.setattr(push_gate.os, "killpg", eperm)
        cfg = config(tmp_path, grace_seconds=0.3)
        table = push_gate.ProcessTable()
        killer = push_gate.GroupKiller(cfg, table, push_gate.Signaller(), push_gate.Clock())
        result = killer.stop(other.pid, require_session=False)
        if table.members(other.pid) is None:
            assert result in {"refused", "gone"}  # no `ps` here: never "killed", never signalled
        else:
            assert result == "refused"
        assert signal.SIGTERM not in attempted and signal.SIGKILL not in attempted
        assert other.poll() is None
    finally:
        monkeypatch.undo()
        other.kill()
        other.wait()


def test_1105_3_killed_is_claimed_only_once_the_group_is_seen_gone(tmp_path: Path) -> None:
    r = rig(tmp_path)
    r.signaller.lethal = ()  # the group survives SIGTERM and SIGKILL alike
    assert r.lock.acquire(owner(r))
    r.table.groups[GROUP] = gate_tree()
    decision = idle_reap(r)
    assert decision.action != "killed", decision
    assert [s for _, _, s in r.signaller.sent] == [signal.SIGTERM, signal.SIGKILL]
    assert all(rec["action"] != "killed" for rec in reap_log(r))


def test_1105_3_run_honours_a_verdict_only_when_its_push_was_killed(
    tmp_path: Path, monkeypatch
) -> None:
    root = storm(tmp_path)
    cfg = PushGateConfig.declared(root)
    fixed = "0123456789abcdef0123456789abcdef"
    monkeypatch.setattr(push_gate.uuid, "uuid4", lambda: type("U", (), {"hex": fixed})())
    push_gate.Verdicts(cfg).write(fixed, {"verdict": "reaped", "condition": "idle"})
    runner = push_gate.PushRunner(
        cfg, push_gate.PushLock(cfg, push_gate.Clock()), push_gate.Clock()
    )
    code = runner.run([sys.executable, "-c", "raise SystemExit(1)"])
    assert code == 1, "an ordinary failure was reported as a reap"


# --- #1105-4: protected by substring; skipped when membership is unknown -----------------------


def test_1105_4_a_branch_named_after_a_protected_program_is_not_protected(tmp_path: Path) -> None:
    """Probe P2: `HEAD:fix/ollama-url` made the push unkillable forever."""
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r))
    r.table.groups[GROUP] = gate_tree("git push origin HEAD:fix/ollama-url")
    assert idle_reap(r).action == "killed"


def test_1105_4_the_protected_program_itself_is_never_killed(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r))
    r.table.groups[GROUP] = [
        *gate_tree(),
        Proc(GROUP + 7, GROUP, GROUP, 0.0, "/usr/local/bin/ollama serve"),
    ]
    decision = idle_reap(r)
    assert decision.action == "refused" and "ollama" in decision.detail


def test_1105_4_unknown_membership_at_the_ceiling_refuses(tmp_path: Path) -> None:
    """Probe P11: ps unreadable at the ceiling skipped the protected check and killed."""
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r))
    r.table.groups[GROUP] = [Proc(GROUP, HOLDER, GROUP, 0.0, "ollama serve")]
    r.table.readable = False
    r.clock.sleep(r.cfg.wall_ceiling_seconds + 1)
    decision = r.reaper.tick()
    assert decision.action == "refused", decision
    assert r.signaller.sent == []


# --- #1105-5: laptop sleep is not a hang ---------------------------------------------------------


def test_1105_5_laptop_sleep_does_not_count_toward_the_ceiling(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r, started_awake=r.clock.awake(), boot_id=r.clock.boot_id()))
    r.table.groups[GROUP] = gate_tree()
    r.clock.sleep(600)
    r.clock.suspend(8 * 3600)  # the lid was shut overnight
    r.table.burn(GROUP, 100)
    assert r.reaper.tick().action == "none"
    assert r.signaller.sent == []


def test_1105_5_an_idle_window_that_spans_a_sleep_is_not_idle(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r, started_awake=r.clock.awake(), boot_id=r.clock.boot_id()))
    r.table.groups[GROUP] = gate_tree()
    r.reaper.tick()
    r.clock.sleep(200)
    r.clock.suspend(3600)
    r.reaper.tick()
    r.clock.sleep(r.cfg.idle_window_seconds)
    # The window from the first sample spans the sleep; from the second it is not yet whole.
    assert r.reaper.tick().action == "none"


def test_1105_5_samples_from_another_boot_are_dropped(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r))
    r.table.groups[GROUP] = gate_tree()
    r.reaper.tick()
    r.clock.boot, r.clock.a = "boot-2", 10.0  # a reboot: awake time starts again
    r.clock.t += r.cfg.idle_window_seconds
    assert r.reaper.tick().action == "none"


# --- #1105-6: two state_dirs on one lock -----------------------------------------------------


def test_1105_6_two_state_dirs_on_one_lock_share_the_mutex_and_the_reap_lock(
    tmp_path: Path,
) -> None:
    """Probe P8."""
    import fcntl

    a = config(tmp_path, state_dir=tmp_path / "a", reap_log=tmp_path / "a" / "r.jsonl")
    b = config(tmp_path, state_dir=tmp_path / "b", reap_log=tmp_path / "b" / "r.jsonl")
    assert push_gate.PushLock.mutex_path(a) == push_gate.PushLock.mutex_path(b)
    assert push_gate.PushLock.mutex_path(a).parent == a.lock.parent
    r = rig(tmp_path, state_dir=tmp_path / "b", reap_log=tmp_path / "b" / "r.jsonl")
    reap = push_gate.Reaper.reap_lock_path(a)
    reap.parent.mkdir(parents=True, exist_ok=True)
    with reap.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert r.reaper.tick().action == "busy"


# --- #1105-7: a reused holder pid ---------------------------------------------------------------


def test_1105_7_a_live_holder_pid_whose_group_is_long_gone_becomes_stale(tmp_path: Path) -> None:
    """Probe P10: the holder pid was reused, so it looks alive; its push group is gone."""
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r))  # GROUP has no members: the push is over
    first = r.reaper.tick()
    assert first.action == "none"
    r.clock.sleep(90)
    second = r.reaper.tick()
    assert second.action == "released" and second.condition == "stale", second


def test_1105_7_a_holder_pid_with_a_different_start_time_is_a_reuse(tmp_path: Path) -> None:
    r = rig(tmp_path)
    assert r.lock.acquire(owner(r, holder_started=1000.0))
    r.table.starts[HOLDER] = 2000.0  # the same pid, a different process
    assert r.reaper.tick().action == "released"


# --- #1105-8: a push-timeout kill is a reap like any other --------------------------------------


def test_1105_8_a_push_timeout_writes_evidence_and_a_reap_log_line(tmp_path: Path) -> None:
    root = storm(tmp_path, kill_grace_seconds=1)
    cfg = PushGateConfig.declared(root)
    done = tool(root, "run", "--push-timeout", "1", "--", sys.executable, "-c",
                "import time; time.sleep(60)")  # fmt: skip
    assert done.returncode == push_gate.PUSH_TIMEOUT_EXIT, done
    [record] = [json.loads(line) for line in cfg.reap_log.read_text().splitlines()]
    assert record["condition"] == "push-timeout"
    assert Path(record["evidence"]).is_dir()


def test_1105_8_the_docs_say_the_schedule_reaps_what_the_cycle_cannot() -> None:
    text = (TOOLS / "storm-cycle.py").read_text()
    assert "install-schedule" in text


# --- #1105-9: py-spy failing falls back to the suite's own dump ----------------------------------


def test_1105_9_a_failed_py_spy_falls_back_to_sigusr1(tmp_path: Path) -> None:
    r = rig(tmp_path)
    evidence = push_gate.EvidenceCollector(
        r.cfg, r.table, r.signaller, r.clock, which=lambda n: "/bin/py-spy",
        run=lambda argv: (1, "Permission denied (need root)"),
    )  # fmt: skip
    held = owner(r, stacks=str(r.cfg.state_dir / "stacks" / "tok-1"))
    r.table.groups[GROUP] = gate_tree()
    evidence.collect(held, push_gate.Decision("killed", "idle", "", {}))
    assert ("process", GROUP + 1, signal.SIGUSR1) in r.signaller.sent


# --- #1107-1: TOCTOU in the ownerless kill -------------------------------------------------------

SHELL, PUSH = 900, 901


def bare(r: Rig, tmp_path: Path) -> float:
    r.cfg.lock.mkdir()
    made = r.clock.now()
    os.utime(r.cfg.lock, (made, made))
    r.table.groups[SHELL] = [
        Proc(SHELL, 800, SHELL, 0.0, "/bin/bash -c mkdir x; git push", made - 1, UID),
        Proc(PUSH, SHELL, SHELL, 0.1, "git push origin HEAD:x", made + 1, UID),
    ]
    r.table.cwds[PUSH] = str(tmp_path / "lane")
    return made


class PushFinishesDuringEvidence(push_gate.EvidenceCollector):
    """Probe P9: while evidence is written, the push ends and the recipe's rmdir runs."""

    def collect(self, owner, decision):  # noqa: ANN001, ANN201
        folder = super().collect(owner, decision)
        self._table.groups[SHELL] = [p for p in self._table.groups[SHELL] if p.pid != PUSH]
        with contextlib.suppress(OSError):
            self._config.lock.rmdir()
        return folder


def test_1107_1_the_ownerless_kill_rechecks_lock_and_push_before_signalling(tmp_path: Path) -> None:
    r = rig(tmp_path, evidence_class=PushFinishesDuringEvidence)
    bare(r, tmp_path)
    decision = idle_reap(r)
    assert decision.action != "killed", decision
    assert [s for s in r.signaller.sent if s[0] == "group"] == []


class SamePidNewProcess(push_gate.EvidenceCollector):
    def collect(self, owner, decision):  # noqa: ANN001, ANN201
        folder = super().collect(owner, decision)
        group = self._table.groups[SHELL]
        self._table.groups[SHELL] = [
            dataclasses.replace(p, started_at=(p.started_at or 0) + 3) if p.pid == PUSH else p
            for p in group
        ]
        return folder


def test_1107_1_a_push_replaced_under_the_same_pid_is_not_signalled(tmp_path: Path) -> None:
    r = rig(tmp_path, evidence_class=SamePidNewProcess)
    bare(r, tmp_path)
    decision = idle_reap(r)
    assert decision.action != "killed"
    assert [s for s in r.signaller.sent if s[0] == "group"] == []


# --- #1107-2: the tracer ignored uid --------------------------------------------------------------


def test_1107_2_another_users_push_is_never_the_holder(tmp_path: Path) -> None:
    r = rig(tmp_path)
    bare(r, tmp_path)
    r.table.groups[SHELL] = [dataclasses.replace(p, uid=UID + 1) for p in r.table.groups[SHELL]]
    assert idle_reap(r).action == "unknown"
    assert r.signaller.sent == []


def test_1107_2_ps_reports_the_uid_column() -> None:
    assert "uid=" in ",".join(push_gate.ProcessTable.PS)


# --- #1107-3: symlinked roots and relative -C ---------------------------------------------------


def test_1107_3_a_symlinked_worktree_root_matches(tmp_path: Path) -> None:
    """Probe P5: lsof reports the real path; the root was declared through a link."""
    real = tmp_path / "real" / "wt"
    real.mkdir(parents=True)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "real")
    cfg = config(tmp_path, worktree_roots=(link,))
    table = FakeTable(cwds={7: str(real.resolve())})
    holder = push_gate.OwnerlessHolder(cfg, table)
    assert holder._in_worktrees(Proc(7, 1, 7, 0.0, "git push origin x", 0.0, UID))


def test_1107_3_a_relative_dash_c_is_read_from_the_cwd(tmp_path: Path) -> None:
    lanes = tmp_path / "lanes"
    (lanes / "a").mkdir(parents=True)
    cfg = config(tmp_path, worktree_roots=(lanes,))
    table = FakeTable(cwds={7: "/"})
    table.cwds[8] = str(lanes)
    holder = push_gate.OwnerlessHolder(cfg, table)
    assert not holder._in_worktrees(
        Proc(7, 1, 7, 0.0, f"git -C {lanes / 'a'}/../../.. push", 0, UID)
    )
    assert holder._in_worktrees(Proc(8, 1, 8, 0.0, "git -C a push", 0.0, UID))


# --- #1107-4: schedule health -------------------------------------------------------------------


@dataclass
class Commands:
    answers: dict[str, tuple[int, str]] = field(default_factory=dict)
    ran: list[list[str]] = field(default_factory=list)

    def __call__(self, argv: list[str]) -> tuple[int, str]:
        self.ran.append(argv)
        for key, answer in self.answers.items():
            if key in " ".join(argv):
                return answer
        return 0, ""


def schedule(
    tmp_path: Path,
    target: str = "launchd",
    commands: Commands | None = None,
    python: str = "/usr/bin/python3",
    **kwargs: object,
):  # noqa: ANN201
    cfg = config(tmp_path)
    made = push_gate.Schedule(
        cfg, root=tmp_path / "storm", tool=TOOLS / "push_gate.py", python=python,
        target=target, home=tmp_path / "home", run=commands or Commands(),
        volatile=kwargs.pop("volatile", ()), linked_worktree=kwargs.pop("linked_worktree", lambda p: False),
    )  # fmt: skip
    return made, cfg


def test_1107_4_status_reports_the_last_exit_and_how_old_the_log_is(tmp_path: Path) -> None:
    commands = Commands({"launchctl print": (0, "state = not running\n\tlast exit code = 2\n")})
    made, cfg = schedule(tmp_path, commands=commands)
    made.install()
    log = cfg.state_dir / "reaper.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("push-gate: none\n")
    old = time.time() - 3600
    os.utime(log, (old, old))
    text = made.status()
    assert "last exit 2" in text
    assert "STALE" in text and "1h00m" in text


def test_1107_4_the_schedule_renders_an_absolute_resolved_lock(tmp_path: Path, monkeypatch) -> None:
    """Probe P6: a relative --lock under launchd's cwd `/` watches nothing."""
    monkeypatch.chdir(tmp_path)
    cfg = PushGateConfig.declared(tmp_path, lock=Path("rel/.push-lock"))
    assert cfg.lock.is_absolute() and cfg.state_dir.is_absolute()
    made = push_gate.Schedule(cfg, tmp_path, TOOLS / "push_gate.py", "/usr/bin/python3",
                              target="launchd", home=tmp_path / "home", run=Commands(),
                              volatile=(), linked_worktree=lambda p: False)  # fmt: skip
    [text] = made.files().values()
    assert str((tmp_path / "rel/.push-lock").resolve()) in text


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        ({"volatile": ("TMP",)}, "temporary"),
        ({"linked_worktree": lambda p: "push_gate" in str(p)}, "worktree"),
        ({"python_version": "3 9"}, "3.11"),
    ],
)
def test_1107_4_install_refuses_volatile_paths_worktrees_and_old_pythons(
    tmp_path: Path, setup: dict, reason: str
) -> None:
    commands = Commands({"-c": (0, setup.pop("python_version", "3 12"))})
    volatile = tuple(tmp_path if v == "TMP" else v for v in setup.pop("volatile", ()))
    made, _ = schedule(tmp_path, commands=commands, volatile=volatile, **setup)
    lines = made.install()
    assert any(line.startswith("REFUSED") and reason in line for line in lines), lines
    assert not (tmp_path / "home").exists()
    assert not any(argv[0] == "launchctl" for argv in commands.ran)


def test_1107_4_contributing_names_no_volatile_storm_root() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text()
    section = text.split("## Pushing in this repository", 1)[1].split("\n## ", 1)[0]
    assert "/private/tmp/claude-501" not in section


# --- #1107-5: systemd quoting ------------------------------------------------------------------


def test_1107_5_values_systemd_cannot_quote_are_refused(tmp_path: Path) -> None:
    """Probe P6: `py" --evil "x\\nExecStartPre=/bin/true` became a second directive."""
    made, _ = schedule(tmp_path, target="systemd", python='py" --evil "x\nExecStartPre=/bin/true')
    lines = made.install()
    assert any(line.startswith("REFUSED") for line in lines), lines
    assert not (tmp_path / "home").exists()


# --- #1107-6: a pass that stands aside ------------------------------------------------------


def test_1107_6_a_pass_that_stands_aside_has_its_own_action_and_exit(tmp_path: Path) -> None:
    import fcntl

    r = rig(tmp_path)
    path = push_gate.Reaper.reap_lock_path(r.cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        decision = r.reaper.tick()
    assert decision.action == "busy"
    assert decision.exit_code() == 3
    assert push_gate.Decision("none", None, "", {}).exit_code() == 0


# --- #1107-7: lane-publish and exit 125 -------------------------------------------------------


def test_1107_7_lane_publish_reports_a_push_timeout_as_one() -> None:
    text = (TOOLS / "lane-publish.py").read_text()
    assert "code == 125" in text


# --- #1107-8: the bare-push scanner ----------------------------------------------------------

GATE = "push_gate.py"


def _words(node: ast.AST, consts: dict[str, object]) -> list[str]:
    """The argv a list/tuple expression builds, as far as it can be known statically."""
    out: list[str] = []
    elements = node.elts if isinstance(node, ast.List | ast.Tuple) else [node]
    for element in elements:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            out.append(element.value)
        elif isinstance(element, ast.Name) and isinstance(consts.get(element.id), str):
            out.append(consts[element.id])  # type: ignore[arg-type]
        elif isinstance(element, ast.Starred):
            inner = element.value
            if isinstance(inner, ast.List | ast.Tuple):
                out.extend(_words(inner, consts))
            elif isinstance(inner, ast.Name) and isinstance(consts.get(inner.id), list):
                out.extend(consts[inner.id])  # type: ignore[arg-type]
            else:
                out.append("*?")
        else:
            out.append("?")
    return out


def bare_pushes(source: str) -> list[int]:
    """Lines where a call runs `git ... push` without going through push_gate.py."""
    tree = ast.parse(source)
    consts: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                consts[node.targets[0].id] = value.value
            elif isinstance(value, ast.List | ast.Tuple) and all(
                isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts
            ):
                consts[node.targets[0].id] = [e.value for e in value.elts]  # type: ignore[union-attr]
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        shell = any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value
                    for k in node.keywords)  # fmt: skip
        system = isinstance(node.func, ast.Attribute) and node.func.attr == "system"
        for arg in [*node.args, *(k.value for k in node.keywords)]:
            texts = [
                n.value
                for n in ast.walk(arg)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            ]
            if any(t.endswith(GATE) for t in texts):
                continue
            if (shell or system) and any(re.search(r"\bgit\b.*\bpush\b", t) for t in texts):
                hits.append(node.lineno)
                continue
            if not isinstance(arg, ast.List | ast.Tuple):
                continue
            words = _words(arg, consts)
            if "git" in words:
                after = words[words.index("git") + 1 :]
                if "push" in after or "*?" in after:
                    hits.append(node.lineno)
    return hits


@pytest.mark.parametrize(
    "source",
    [
        'run(["git", "-C", tree, "push"])',
        'PUSH = ["push", "-u"]\nrun(["git", *PUSH])',
        'run(["git", *unknown])',
        'subprocess.run("git push", shell=True)',
        'os.system("git push origin x")',
        'GIT = "git"\nrun([GIT, "push"])',
        'run(["git",\n "push"])',
        'run(("git", "push"))',
    ],
)
def test_1107_8_the_bare_push_scanner_catches_every_spelling(source: str) -> None:
    """Probe P7: the regex missed all but the simplest spelling."""
    assert bare_pushes(source), source


def test_1107_8_a_push_through_the_gate_is_not_bare() -> None:
    assert not bare_pushes(
        'run([sys.executable, str(T / "push_gate.py"), "run", "--", "git", "push"])'
    )
    assert not bare_pushes('run(["git", "status"])')


#: Scripts allowed a bare push, each with its reason. Empty is the goal.
ALLOWED: dict[str, str] = {}

SHELL_PUSH = re.compile(r"^(?!\s*#).*\bgit\b(\s+-\S+(\s+\S+)?)*\s+push\b")


def test_1107_8_no_storm_tool_or_script_pushes_around_the_gate() -> None:
    offenders: list[str] = []
    python = [*TOOLS.glob("*.py"), *(ROOT / "scripts").rglob("*.py")]
    for path in python:
        if path.name == GATE:
            continue
        for line in bare_pushes(path.read_text(encoding="utf-8")):
            offenders.append(f"{path.relative_to(ROOT)}:{line}")
    shells = [*TOOLS.glob("*.sh"), *(ROOT / "scripts").rglob("*.sh")]
    for path in shells:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if SHELL_PUSH.search(line) and GATE not in line:
                offenders.append(f"{path.relative_to(ROOT)}:{number}")
    offenders = [o for o in offenders if o.split(":")[0] not in ALLOWED]
    assert offenders == []


def test_1107_8_the_shell_scan_sees_a_bare_push() -> None:
    assert SHELL_PUSH.search('git push -u origin "$BRANCH"')
    assert SHELL_PUSH.search("  git -C dir push")
    assert not SHELL_PUSH.search("# git push is documented here")


#: Findings whose fix lands in a later commit of this pull request. Each is a strict xfail:
#: it must fail until its fix lands, and the commit that fixes it deletes its line here.
PENDING = {
    "test_1105_5_laptop_sleep_does_not_count_toward_the_ceiling",
    "test_1105_5_an_idle_window_that_spans_a_sleep_is_not_idle",
    "test_1105_5_samples_from_another_boot_are_dropped",
    "test_1105_6_two_state_dirs_on_one_lock_share_the_mutex_and_the_reap_lock",
    "test_1105_7_a_live_holder_pid_whose_group_is_long_gone_becomes_stale",
    "test_1105_7_a_holder_pid_with_a_different_start_time_is_a_reuse",
    "test_1105_8_a_push_timeout_writes_evidence_and_a_reap_log_line",
    "test_1105_8_the_docs_say_the_schedule_reaps_what_the_cycle_cannot",
    "test_1105_9_a_failed_py_spy_falls_back_to_sigusr1",
    "test_1107_2_another_users_push_is_never_the_holder",
    "test_1107_3_a_symlinked_worktree_root_matches",
    "test_1107_3_a_relative_dash_c_is_read_from_the_cwd",
    "test_1107_4_status_reports_the_last_exit_and_how_old_the_log_is",
    "test_1107_4_the_schedule_renders_an_absolute_resolved_lock",
    "test_1107_4_install_refuses_volatile_paths_worktrees_and_old_pythons",
    "test_1107_4_contributing_names_no_volatile_storm_root",
    "test_1107_5_values_systemd_cannot_quote_are_refused",
    "test_1107_6_a_pass_that_stands_aside_has_its_own_action_and_exit",
    "test_1107_7_lane_publish_reports_a_push_timeout_as_one",
    "test_1107_8_no_storm_tool_or_script_pushes_around_the_gate",
}
for _name in PENDING:
    globals()[_name] = pytest.mark.xfail(strict=True, reason="fixed later in this PR")(
        globals()[_name]
    )
