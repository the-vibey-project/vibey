# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp` in a hostile project: the folder's `vibey.toml` never grants (ADR-0101).

An editor launches `vibey acp` in whatever folder it opened -- a repository someone else wrote.
These tests run the real command, the real settings loader and the real machine
(`acp_machine`) with such a project's `vibey.toml`, and hold that nothing it says reaches a unit,
a client config or the service manager, while a project that turns services off stops them.
Module-level test functions (ADR-0016)."""

from __future__ import annotations

import asyncio
import functools
import plistlib
import sys
from pathlib import Path
from typing import Any

import pytest

from vibey.application.acp.interfaces.acp_agent_interface import AcpAgentInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.bootstrap import acp_machine, running_vibey
from vibey.cli.acp import AcpCommand
from vibey.domain.acp.settings import AcpSettings
from vibey.infrastructure.supervisor import SupervisorHost

HOSTILE = """\
[acp]
auto_bootstrap = true
auto_services = true
auto_connect = true
install_postgres = "ask"
services = ["hub", "worker"]
service_workdir = "/etc"
hub_start_seconds = 1
probe_seconds = 5

[supervisor]
vibey = "/tmp/evil"
python = "/tmp/evil-python"
env_file = "/tmp/x"
log_dir = "/etc"
label_prefix = "a;b $(id)"
worker_args = ["--evil", "$(touch /tmp/pwned)"]

[hub]
state_dir = "/tmp/evil-state"
"""
MARKERS = ("/tmp/evil", "/tmp/x", "/etc", "a;b", "$(id)", "--evil", "pwned")


class _Transport:
    def guard(self) -> int:
        return 99

    async def reader(self, limit: int) -> asyncio.StreamReader:
        reader = asyncio.StreamReader(limit=limit)
        reader.feed_eof()
        return reader

    async def write_line(self, line: str) -> None:
        pass


class _Agent:
    async def handle_request(self, method: str, params: Any) -> Any:
        return {}

    async def handle_notification(self, method: str, params: Any) -> None:
        pass

    async def close(self) -> None:
        pass


def _run(project: Path, user: Path, home: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Run `vibey acp` in `project` with `user` as the user's own file; what it composed."""
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(sys, "platform", "darwin")
    # pytest's folders are under $TMPDIR, which the supervisor rightly calls volatile (10.h).
    monkeypatch.setattr(
        "vibey.bootstrap.SupervisorHost",
        functools.partial(SupervisorHost, temp_roots=lambda: (Path("/volatile"),)),
    )
    parts: dict[str, Any] = {}

    def builder(
        *, settings: AcpSettings, channel: ClientChannelInterface, **given: Any
    ) -> AcpAgentInterface:
        parts.update(given, settings=settings)
        return _Agent()  # type: ignore[return-value]

    def machine(settings: AcpSettings, *, user_config: Path) -> Any:
        return acp_machine(settings, user_config=user_config, launcher="/opt/vibey/bin/vibey")

    AcpCommand(
        transport=_Transport,  # type: ignore[arg-type]
        config_path=lambda: project / "vibey.toml",
        user_config=lambda: user,
        build_agent=builder,
        machine=machine,
        doctor_probes=(),
    ).run(no_bootstrap=False)
    return parts


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    folder = tmp_path / "cloned-repo"
    folder.mkdir()
    (folder / "vibey.toml").write_text(HOSTILE)
    return folder


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return home


def _user(home: Path, text: str = "") -> Path:
    user = home / "Library" / "Application Support" / "vibey" / "vibey.toml"
    user.parent.mkdir(parents=True, exist_ok=True)
    if text:
        user.write_text(text)
    return user


def test_a_project_cannot_turn_services_on_that_the_user_turned_off(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home(tmp_path)
    user = _user(home, "[acp]\nauto_services = false\n")

    settings = _run(project, user, home, monkeypatch)["settings"]

    assert settings.auto_services is False
    assert settings.service_workdir == ""
    assert (settings.hub_start_seconds, settings.probe_seconds) == (60, 30)


def test_a_project_that_turns_services_off_stops_them(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home(tmp_path)
    folder = tmp_path / "repo"
    folder.mkdir()
    (folder / "vibey.toml").write_text(
        '[acp]\nauto_services = false\nauto_connect = false\ninstall_postgres = "never"\n'
    )

    settings = _run(folder, _user(home), home, monkeypatch)["settings"]

    assert settings.auto_services is False
    assert settings.auto_connect is False
    assert settings.install_postgres == "never"


def test_no_unit_mentions_anything_the_hostile_project_said(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home(tmp_path)
    parts = _run(project, _user(home), home, monkeypatch)
    monkeypatch.chdir(project)  # the folder the editor opened

    outcomes = parts["units"].write(("hub", "worker"), parts["settings"].restart)

    agents = home / "Library" / "LaunchAgents"
    assert [o.label for o in outcomes] == ["dev.vibey.hub", "dev.vibey.worker"]
    for outcome in outcomes:
        text = Path(outcome.path).read_text()
        assert not any(marker in text for marker in MARKERS), text
        argv = plistlib.loads(text.encode())["ProgramArguments"]
        assert argv[0] == argv[6] == "/opt/vibey/bin/vibey"
        assert Path(outcome.path).parent == agents
    assert parts["units"].label("hub") == "dev.vibey.hub"


def test_the_machine_lives_in_the_users_state_never_the_projects(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home(tmp_path)
    user = _user(home, f"[hub]\nstate_dir = '{home / 'state'}'\n")

    parts = _run(project, user, home, monkeypatch)

    assert parts["lock"]._path == home / "state" / "acp-bootstrap.lock"
    assert parts["connector"]._marker.parent == home / "state"
    assert parts["units"]._state_dir == home / "state"
    # A hub started without a service manager runs in the user's folder, reading their file.
    assert parts["units"]._start_hub.keywords == {"cwd": user.parent}


def test_the_connect_step_writes_the_running_install_into_client_configs(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home(tmp_path)
    monkeypatch.setenv("PATH", "/tmp/evil-bin")  # whatever PATH the editor handed over

    parts = _run(project, _user(home), home, monkeypatch)

    installer = parts["connector"]._installer
    assert installer._which("vibey") == "/opt/vibey/bin/vibey"
    assert installer._python_executable == sys.executable


def test_the_running_launcher_is_the_console_script_beside_this_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").write_text("")
    monkeypatch.setattr(sys, "executable", str(bin_dir / "python"))
    assert running_vibey() is None
    launcher = bin_dir / "vibey"
    launcher.write_text("#!/bin/sh\n")
    assert running_vibey() is None  # not executable
    launcher.chmod(0o755)
    assert running_vibey() == str(launcher)


def test_the_editors_gateway_finds_the_hub_through_the_users_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibey.bootstrap import build_acp_agent

    user = tmp_path / "user" / "vibey.toml"
    monkeypatch.setattr("vibey.bootstrap.acp_user_config", lambda: user)
    monkeypatch.chdir(tmp_path)

    class _Channel:
        client_capabilities: dict[str, Any] = {}

    agent = build_acp_agent(settings=AcpSettings(), channel=_Channel())  # type: ignore[arg-type]

    assert agent._hub._gateway._config_path() == user  # type: ignore[attr-defined]


def test_the_hub_unit_and_vibey_acp_read_the_same_vibey_toml(
    tmp_path: Path, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibey.bootstrap import build_acp_agent

    home = _home(tmp_path)
    user = _user(home, f"[hub]\nstate_dir = '{home / 'state'}'\n")
    parts = _run(project, user, home, monkeypatch)
    monkeypatch.setattr("vibey.bootstrap.acp_user_config", lambda: user)
    monkeypatch.chdir(project)

    (hub,) = parts["units"].write(("hub",), "always")
    agent = build_acp_agent(settings=parts["settings"], channel=_Channel())  # type: ignore[arg-type]

    # `vibey serve` reads `./vibey.toml` in its working directory; `vibey acp` reads `[hub]`
    # through its gateway's config path. Both are the user's own file, never the project's.
    working = plistlib.loads(Path(hub.path).read_bytes())["WorkingDirectory"]
    assert Path(working) / "vibey.toml" == user
    assert agent._hub._gateway._config_path() == user  # type: ignore[attr-defined]


class _Channel:
    client_capabilities: dict[str, Any] = {}
