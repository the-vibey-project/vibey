# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The driver failover's infrastructure against real files, git and processes (ADR-0070)."""

import json
import plistlib
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vibey.application.interfaces.driver import DriverLedgerPort, DriverWorkspacePort, ProcessPort
from vibey.domain.effort import Effort
from vibey.domain.failover import FailoverKind, FailoverSettings
from vibey.infrastructure.driver.file_ledger import GENESIS, JsonlDriverLedger
from vibey.infrastructure.driver.interfaces.file_ledger_interface import (
    JsonlDriverLedgerInterface,
)
from vibey.infrastructure.driver.interfaces.processes_interface import SubprocessPortInterface
from vibey.infrastructure.driver.interfaces.settings_loader_interface import (
    FailoverSettingsLoaderInterface,
)
from vibey.infrastructure.driver.interfaces.timer_units_interface import (
    TimerUnitRendererInterface,
)
from vibey.infrastructure.driver.interfaces.workspace_interface import (
    LocalDriverWorkspaceInterface,
)
from vibey.infrastructure.driver.processes import (
    MISSING_BINARY_EXIT,
    TIMEOUT_EXIT,
    SubprocessPort,
)
from vibey.infrastructure.driver.settings_loader import FailoverSettingsLoader
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.driver.workspace import LocalDriverWorkspace

T0 = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)


def test_the_classes_satisfy_their_interfaces_and_ports(tmp_path: Path) -> None:
    ledger = JsonlDriverLedger(tmp_path / "l.jsonl")
    assert isinstance(ledger, JsonlDriverLedgerInterface) and isinstance(ledger, DriverLedgerPort)
    workspace = LocalDriverWorkspace()
    assert isinstance(workspace, LocalDriverWorkspaceInterface)
    assert isinstance(workspace, DriverWorkspacePort)
    processes = SubprocessPort()
    assert isinstance(processes, SubprocessPortInterface) and isinstance(processes, ProcessPort)
    assert isinstance(FailoverSettingsLoader(), FailoverSettingsLoaderInterface)
    assert isinstance(TimerUnitRenderer(), TimerUnitRendererInterface)


def test_the_ledger_appends_a_hash_chain_and_reads_it_back(tmp_path: Path) -> None:
    path = tmp_path / "d" / "ledger.jsonl"
    ledger = JsonlDriverLedger(path)
    assert ledger.records() == () and ledger.verify_chain()
    ledger.append(FailoverKind.FAILED_OVER, at=T0, payload={"run_id": "r"})
    ledger.append(FailoverKind.PROBED, at=T0 + timedelta(minutes=1), payload={"ok": True})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["seq"] for row in rows] == [1, 2] and rows[0]["prev"] == GENESIS
    assert ledger.verify_chain()
    records = ledger.records()
    assert [r.kind for r in records] == [FailoverKind.FAILED_OVER, FailoverKind.PROBED]
    assert records[0].payload == {"run_id": "r"}


def test_a_tampered_or_garbled_ledger_is_detected_and_skipped(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = JsonlDriverLedger(path)
    ledger.append(FailoverKind.FAILED_OVER, at=T0, payload={})
    ledger.append(FailoverKind.PROBED, at=T0, payload={"ok": False})
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[1], lines[0]]) + "\n")
    assert not ledger.verify_chain()
    path.write_text(lines[0] + "\nnot json\n[1]\n\n")
    assert len(ledger.records()) == 1


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_the_workspace_reads_git_and_the_transcript(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(
        tmp_path,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "one",
    )
    workspace = LocalDriverWorkspace()
    first = workspace.repo(str(tmp_path))
    assert first.branch == "main" and len(first.head_sha) == 40 and first.dirty_paths == ()
    (tmp_path / "work.py").write_text("x = 1\n")
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"a": 1}\n{"b": 2}\n')
    assert workspace.digest(str(tmp_path / "missing")) is None
    digest = workspace.digest(str(transcript))
    assert digest is not None and digest.lines == 2 and len(digest.sha256) == 64
    copy = workspace.copy_transcript(str(transcript), str(tmp_path), "c.jsonl")
    assert workspace.digest(copy) == digest
    brief = workspace.write_brief(str(tmp_path), "b.md", "hello")
    assert Path(brief).read_text() == "hello"
    ignore = tmp_path / ".vibey" / "driver" / ".gitignore"
    assert ignore.read_text() == "*\n"
    workspace.write_brief(str(tmp_path), "b2.md", "again")
    assert ignore.read_text() == "*\n"
    dirty = workspace.repo(str(tmp_path)).dirty_paths
    assert "work.py" in dirty and "t.jsonl" in dirty
    assert not any(p.startswith(".vibey/driver") for p in dirty)
    _git(
        tmp_path,
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "two",
    )
    assert [c.split(" ", 1)[1] for c in workspace.commits_since(str(tmp_path), first.head_sha)] == [
        "two"
    ]
    assert workspace.commits_since(str(tmp_path), "") == ()


def test_git_failures_read_as_empty(tmp_path: Path) -> None:
    assert LocalDriverWorkspace().repo(str(tmp_path)).head_sha == ""
    assert LocalDriverWorkspace(git="no-such-git-binary").repo(str(tmp_path)).branch == ""


def test_processes_run_spawn_and_fail_honestly(tmp_path: Path) -> None:
    port = SubprocessPort()
    done = port.run([sys.executable, "-c", "print('hi')"], cwd=str(tmp_path), timeout=30)
    assert done.exit_code == 0 and done.stdout.strip() == "hi"
    assert (
        port.run(["no-such-binary-xyz"], cwd=str(tmp_path), timeout=5).exit_code
        == MISSING_BINARY_EXIT
    )
    slow = port.run(
        [sys.executable, "-c", "import time; time.sleep(5)"], cwd=str(tmp_path), timeout=0.2
    )
    assert slow.exit_code == TIMEOUT_EXIT
    marker = tmp_path / "spawned"
    port.spawn([sys.executable, "-c", f"open({str(marker)!r}, 'w').write('ok')"], cwd=str(tmp_path))
    for _ in range(100):
        if marker.exists():
            break
        subprocess.run([sys.executable, "-c", "import time; time.sleep(0.05)"], check=True)
    assert marker.read_text() == "ok"
    assert (tmp_path / ".vibey" / "driver" / "processes.log").exists()


def test_settings_default_when_absent_and_read_every_key(tmp_path: Path) -> None:
    loader = FailoverSettingsLoader()
    assert loader.load(tmp_path / "vibey.toml") == FailoverSettings()
    toml = tmp_path / "vibey.toml"
    toml.write_text(
        "[failover]\n"
        "enabled = false\n"
        'target_engine = "qwenloop"\n'
        'target_effort = "max"\n'
        "probe_interval_seconds = 60\n"
        'sovereign_argv = ["q", "{brief}"]\n'
        'sovereign_wind_down_argv = ["q", "stop"]\n'
        'probe_argv = ["p"]\n'
        'resume_argv = ["r", "{session_id}"]\n'
    )
    settings = loader.load(toml)
    assert settings == FailoverSettings(
        enabled=False,
        target_engine="qwenloop",
        target_effort=Effort.MAX,
        probe_interval=timedelta(seconds=60),
        sovereign_argv=("q", "{brief}"),
        sovereign_wind_down_argv=("q", "stop"),
        probe_argv=("p",),
        resume_argv=("r", "{session_id}"),
    )
    (tmp_path / "empty.toml").write_text("[other]\n")
    assert loader.load(tmp_path / "empty.toml") == FailoverSettings()


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("failover = 1\n", "must be a table"),
        ("[failover]\nbogus = 1\n", "unknown keys: bogus"),
        ("[failover]\nenabled = 1\n", "enabled must be a bool"),
        ("[failover]\nprobe_interval_seconds = true\n", "must be a int"),
        ('[failover]\ntarget_effort = "huge"\n', "not an effort"),
        ("[failover]\nprobe_argv = []\n", "non-empty list of strings"),
        ('[failover]\nprobe_argv = "claude"\n', "non-empty list of strings"),
        ("[failover]\nprobe_argv = [1]\n", "non-empty list of strings"),
    ],
)
def test_settings_refuse_bad_keys_by_name(tmp_path: Path, body: str, message: str) -> None:
    toml = tmp_path / "vibey.toml"
    toml.write_text(body)
    with pytest.raises(ValueError, match=message):
        FailoverSettingsLoader().load(toml)


def test_the_launchd_agent_is_a_valid_plist() -> None:
    units = TimerUnitRenderer()
    text = units.launchd(
        argv=["vibey", "driver", "probe", "--cwd", "/a&b"], cwd="/a&b", interval_seconds=900
    )
    plist = plistlib.loads(text.encode())
    assert plist["Label"] == units.label("/a&b") and plist["Label"].startswith("dev.vibey.")
    assert plist["ProgramArguments"][-1] == "/a&b"
    assert plist["StartInterval"] == 900 and plist["WorkingDirectory"] == "/a&b"
    assert plist["StandardOutPath"] == "/a&b/.vibey/driver/probe.log"


def test_the_systemd_units_quote_and_schedule() -> None:
    units = TimerUnitRenderer()
    service, timer = units.systemd(argv=["vibey", 'say "hi" 100%'], cwd="/w", interval_seconds=60)
    assert 'ExecStart="vibey" "say \\"hi\\" 100%%"' in service
    assert "Type=oneshot" in service and 'WorkingDirectory="/w"' in service
    assert "OnUnitActiveSec=60s" in timer and f"Unit={units.label('/w')}.service" in timer
