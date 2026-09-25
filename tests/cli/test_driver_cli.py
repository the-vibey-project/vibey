# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey driver`, end to end: a real git worktree, the real driver ledger and real
processes, with the paid CLI and the sovereign engine played by small Python scripts
(ADR-0070)."""

import io
import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from vibey.cli.driver import DriverCommand, _UtcClock
from vibey.cli.interfaces.driver_interface import DriverCommandInterface, UtcClockInterface
from vibey.cli.main import app
from vibey.domain.failover import FailoverSettings
from vibey.infrastructure.driver.file_ledger import JsonlDriverLedger

runner = CliRunner()


def _worktree(tmp_path: Path, probe_json: str) -> tuple[Path, Path]:
    tree = tmp_path / "tree"
    tree.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feat/x"], cwd=tree, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "start",
        ],
        cwd=tree,
        check=True,
    )
    transcript = tmp_path / "session.jsonl"
    transcript.write_text('{"type": "user"}\n{"type": "assistant"}\n')
    py = sys.executable
    record = "import sys, pathlib; pathlib.Path(sys.argv[1]).write_text(' '.join(sys.argv[2:]))"
    argv = {
        "sovereign_argv": [py, "-c", record, f"{tmp_path}/sovereign", "{brief}", "{run_id}"],
        "sovereign_wind_down_argv": [py, "-c", "pass"],
        "probe_argv": [py, "-c", f"print({probe_json!r})"],
        "resume_argv": [py, "-c", record, f"{tmp_path}/resumed", "{session_id}", "{prompt}"],
    }
    lines = [f"{key} = {json.dumps(value)}" for key, value in argv.items()]
    (tree / "vibey.toml").write_text(
        "[failover]\n" + "\n".join(lines) + "\nprobe_interval_seconds = 1\n"
    )
    return tree, transcript


def _wait(path: Path) -> str:
    for _ in range(200):
        if path.exists() and path.read_text():
            return path.read_text()
        time.sleep(0.05)
    raise AssertionError(f"{path} was never written")


def _hook(tree: Path, transcript: Path, error: str) -> str:
    return json.dumps(
        {
            "hook_event_name": "StopFailure",
            "session_id": "sess-abcdef12",
            "transcript_path": str(transcript),
            "cwd": str(tree),
            "error": error,
            "error_details": None,
            "last_assistant_message": "API Error: Rate limit reached",
        }
    )


def test_interfaces() -> None:
    assert isinstance(DriverCommand(), DriverCommandInterface)
    clock = _UtcClock()
    assert isinstance(clock, UtcClockInterface) and clock.now().tzinfo is UTC


def test_hook_fails_over_then_probe_hands_back_to_the_same_session(tmp_path: Path) -> None:
    tree, transcript = _worktree(tmp_path, '{"is_error": false, "subtype": "success"}')
    out = runner.invoke(app, ["driver", "hook"], input=_hook(tree, transcript, "rate_limit"))
    assert out.exit_code == 0, out.output
    body = json.loads(out.output)
    assert body["result"] == "failed_over" and body["status"]["active"] is True
    sovereign = _wait(tmp_path / "sovereign")
    assert sovereign.startswith(body["brief_path"]) and body["detail"] in sovereign
    brief = Path(body["brief_path"]).read_text()
    assert "sha256" in brief and "gptossloop at effort ULTRA" in brief

    again = runner.invoke(app, ["driver", "hook"], input=_hook(tree, transcript, "rate_limit"))
    assert json.loads(again.output)["result"] == "already"

    early = runner.invoke(app, ["driver", "probe", "--cwd", str(tree)])
    assert json.loads(early.output)["result"] == "not_due"
    time.sleep(1.1)
    back = runner.invoke(app, ["driver", "probe", "--cwd", str(tree)])
    assert back.exit_code == 0, back.output
    body = json.loads(back.output)
    assert body["result"] == "handed_back" and body["status"]["active"] is False
    resumed = _wait(tmp_path / "resumed")
    assert resumed.startswith("sess-abcdef12 ") and body["brief_path"] in resumed

    ledger = JsonlDriverLedger(tree / ".vibey" / "driver" / "ledger.jsonl")
    assert ledger.verify_chain()
    assert [r.kind.value for r in ledger.records()] == [
        "EngineFailedOver",
        "EngineProbed",
        "EngineHandedBack",
    ]
    status = runner.invoke(app, ["driver", "status", "--cwd", str(tree)])
    state = json.loads(status.output)
    assert state["active"] is False and state["failover"]["kind"] == "EngineFailedOver"


def test_a_refused_probe_keeps_the_sovereign_engine_working(tmp_path: Path) -> None:
    tree, transcript = _worktree(tmp_path, '{"is_error": true}')
    runner.invoke(app, ["driver", "hook"], input=_hook(tree, transcript, "billing_error"))
    time.sleep(1.1)
    out = runner.invoke(app, ["driver", "probe", "--cwd", str(tree)])
    body = json.loads(out.output)
    assert body["result"] == "probe_failed" and body["status"]["active"] is True
    assert body["status"]["probe_ok"] is None
    assert not (tmp_path / "resumed").exists()


def test_hook_ignores_what_is_not_a_capacity_stopfailure(tmp_path: Path) -> None:
    tree, transcript = _worktree(tmp_path, "{}")
    for payload in ("not json", json.dumps({"hook_event_name": "Stop"}), "[]"):
        out = runner.invoke(app, ["driver", "hook"], input=payload)
        assert out.exit_code == 0 and json.loads(out.output)["result"] == "ignored"
    out = runner.invoke(app, ["driver", "hook"], input=_hook(tree, transcript, "overloaded"))
    assert json.loads(out.output)["result"] == "ignored"
    empty = DriverCommand().hook(io.StringIO(""), None)
    assert empty == 0


def test_an_unreadable_transcript_parks_with_exit_3(tmp_path: Path) -> None:
    tree, _ = _worktree(tmp_path, "{}")
    out = runner.invoke(
        app, ["driver", "hook"], input=_hook(tree, tmp_path / "gone.jsonl", "rate_limit")
    )
    assert out.exit_code == 3
    body = json.loads(out.output)
    assert body["result"] == "parked" and "PARKED-failover" in body["brief_path"]
    assert not (tmp_path / "sovereign").exists()


def test_timer_writes_units_for_each_platform(tmp_path: Path) -> None:
    tree, _ = _worktree(tmp_path, "{}")
    command = DriverCommand(which=lambda _name: "/usr/local/bin/vibey")
    assert command.timer(tree, "launchd", tmp_path / "units", None) == 0
    assert command.timer(tree, "systemd", tmp_path / "units", None) == 0
    assert command.timer(tree, "windows", tmp_path / "units", None) == 2
    names = sorted(p.suffix for p in (tmp_path / "units").iterdir())
    assert names == [".plist", ".service", ".timer"]
    out = runner.invoke(app, ["driver", "timer", "--cwd", str(tree), "--out", str(tmp_path / "u2")])
    assert out.exit_code == 0 and "wrote" in out.output
    plist = next((tmp_path / "units").glob("*.plist")).read_text()
    assert "<integer>1</integer>" in plist and "/usr/local/bin/vibey" in plist


def test_hook_config_prints_the_stopfailure_block() -> None:
    out = runner.invoke(app, ["driver", "hook-config"])
    block = json.loads(out.output)
    (entry,) = block["hooks"]["StopFailure"]
    assert entry["hooks"] == [{"type": "command", "command": "vibey driver hook"}]
    assert "matcher" not in entry


def test_an_explicit_config_path_is_read(tmp_path: Path) -> None:
    config = tmp_path / "elsewhere.toml"
    config.write_text("[failover]\nenabled = false\n")
    seen: list[FailoverSettings] = []

    class Service:
        def status(self) -> object:
            from vibey.domain.failover import FAILOVER_POLICY

            return FAILOVER_POLICY.status(())

    def make(cwd: Path, settings: FailoverSettings) -> Service:
        seen.append(settings)
        return Service()

    command = DriverCommand(make_service=make)  # type: ignore[arg-type]
    assert command.status(tmp_path, config) == 0
    assert seen == [FailoverSettings(enabled=False)]
    assert timedelta(0) < seen[0].probe_interval and datetime.now(UTC)
