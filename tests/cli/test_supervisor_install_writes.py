# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey supervisor install` writing through `SupervisorInstaller` (#1189, ADR-0101).

`tests/cli/test_supervisor_cli.py` pins the command's output and is unchanged; these cases are
what the shared installer adds: a unit it may not write is named and exits 1, and a value no
unit can carry writes nothing and exits 78. Module-level test functions (ADR-0016)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from vibey.cli.supervisor import EXIT_CONFIG, SupervisorCommand
from vibey.infrastructure.supervisor import SupervisorHost


def _no_manager(argv: Sequence[str]) -> tuple[int, str]:
    return 3, "inactive"


def _command(tmp_path: Path, path_env: str = "/opt/vibey/bin:/usr/bin") -> SupervisorCommand:
    def host(platform: str) -> SupervisorHost:
        return SupervisorHost(
            platform,
            home=tmp_path / "home",
            environ={},
            uid=501,
            run=_no_manager,
            temp_roots=lambda: (Path("/volatile"),),
        )

    return SupervisorCommand(
        host_factory=host,
        which=lambda name: "/opt/vibey/bin/vibey",
        python="/opt/vibey/bin/python",
        environ={"PATH": path_env},
        root=tmp_path,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "scripts" / "triaged_delivery.py").write_text("# the bridge\n")
    return checkout


def test_a_unit_that_is_a_link_is_named_and_the_install_exits_1(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    outside = tmp_path / "outside.plist"
    outside.write_text("not vibey's")
    (agents / "dev.vibey.worker.plist").symlink_to(outside)

    code = _command(tmp_path).install(platform="launchd", repo=repo, out=None, config=None)

    assert code == 1
    captured = capsys.readouterr()
    assert "dev.vibey.worker.plist: it is a symbolic link" in captured.err
    assert f"wrote {agents / 'dev.vibey.delivery.plist'}" in captured.out
    assert "load them with" not in captured.out
    assert outside.read_text() == "not vibey's"


def test_a_value_no_unit_can_carry_writes_nothing_and_exits_78(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = _command(tmp_path, path_env="/opt/bin\nExecStartPre=/bin/evil").install(
        platform="systemd", repo=repo, out=None, config=None
    )

    assert code == EXIT_CONFIG
    assert "control character" in capsys.readouterr().err
    assert not (tmp_path / "home" / ".config" / "systemd" / "user").exists() or not any(
        (tmp_path / "home" / ".config" / "systemd" / "user").iterdir()
    )


def test_installing_again_replaces_vibeys_own_units(tmp_path: Path, repo: Path) -> None:
    command = _command(tmp_path)
    assert command.install(platform="launchd", repo=repo, out=None, config=None) == 0
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.worker.plist"
    unit.write_text("edited")

    assert command.install(platform="launchd", repo=repo, out=None, config=None) == 0

    assert "<string>worker</string>" in unit.read_text()  # overwrite=True, as it always was
