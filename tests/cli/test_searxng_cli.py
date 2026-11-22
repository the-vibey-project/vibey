# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey searxng`: install (asked, then pull, write, load, wait), status, uninstall [--purge],
serve, and doctor's `searxng` line (ADR-0102). Every runtime, service-manager and network call is
faked. Module-level test functions (ADR-0016)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from vibey.application.acp.dto import SearxngOffer, SearxngPrepared, UnitOutcome
from vibey.bootstrap import AcpMachine
from vibey.cli.interfaces.searxng_interface import SearxngCommandInterface
from vibey.cli.main import app
from vibey.cli.searxng import SearxngCommand
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.config import ConfigError
from vibey.domain.searxng import SEARXNG_IMAGE, SearxngProvision

LABEL = "dev.vibey.searxng"
UNIT = "/home/op/Library/LaunchAgents/dev.vibey.searxng.plist"
RUNTIME = "/opt/homebrew/bin/podman"
RECORD = SearxngProvision(SEARXNG_IMAGE, 28180, "vibey-" + "1" * 32, LABEL, RUNTIME)
USER = Path("/home/op/.config/vibey/vibey.toml")
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


class Provisioner:
    def __init__(self, **found: Any) -> None:
        values = {
            "runtime": RUNTIME,
            "own_url": None,
            "answering": False,
            "provisioned": False,
            "short": "fc1d81d7e9d0",
            "port": 28180,
            **found,
        }
        self.found = SearxngOffer(**values)
        self.kept: SearxngProvision | None = RECORD if self.found.provisioned else None
        self.prepared = SearxngPrepared(True, "Downloaded searxng/searxng@sha256:fc1d81d7e9d0.")
        self.answers = True
        self.present = True
        self.removed = ""
        self.purged: list[str] = []
        self.calls: list[str] = []

    def offer(self) -> SearxngOffer:
        self.calls.append("offer")
        return self.found

    def provisioned(self) -> bool:
        return self.kept is not None

    def record(self) -> SearxngProvision | None:
        return self.kept

    def image_present(self) -> bool:
        self.calls.append("inspect")
        return self.present

    def prepare(self) -> SearxngPrepared:
        self.calls.append("prepare")
        if self.prepared.ok:
            self.kept = RECORD
        return self.prepared

    def answering(self) -> bool:
        self.calls.append("answering")
        return self.answers

    def remove_container(self) -> str:
        self.calls.append("rm")
        return self.removed

    def purge(self) -> list[str]:
        self.calls.append("purge")
        self.kept = None
        return self.purged


class Units:
    def __init__(self, action: str = "created") -> None:
        self.action = action
        self.writes: list[tuple[tuple[str, ...], str]] = []
        self.removed: list[str] = []
        self.remove_action = "removed"
        self.label_error = False

    def write(self, names: tuple[str, ...], restart: str) -> tuple[UnitOutcome, ...]:
        self.writes.append((names, restart))
        if self.action == "raise":
            raise ValueError("[acp] service_workdir /x is not a folder")
        return (UnitOutcome(LABEL, UNIT, self.action, "disk full"),)  # type: ignore[arg-type]

    def remove(self, label: str) -> UnitOutcome:
        self.removed.append(label)
        return UnitOutcome(label, UNIT, self.remove_action)  # type: ignore[arg-type]

    def label(self, name: str) -> str:
        if self.label_error:
            raise ValueError("[supervisor] must be a table")
        return f"dev.vibey.{name}"


class Loader:
    def __init__(self, *, available: bool = True, running: bool = False) -> None:
        self.is_available = available
        self.running = running
        self.calls: list[tuple[str, str]] = []
        self.refusal = ""
        self.fail = False
        self.unload_fails = False
        self.reload_fails = False

    def refused(self) -> str:
        return self.refusal

    def available(self) -> bool:
        return self.is_available

    def state(self, label: str) -> str:
        return "running" if self.running else "not loaded"

    def load(self, label: str, unit: str) -> UnitOutcome:
        self.calls.append(("load", label))
        return UnitOutcome(label, unit, "failed" if self.fail else "loaded", "EIO")

    def restart(self, label: str) -> UnitOutcome:
        self.calls.append(("restart", label))
        return UnitOutcome(label, UNIT, "restarted")

    def unload(self, label: str) -> UnitOutcome:
        self.calls.append(("unload", label))
        if self.unload_fails:
            return UnitOutcome(label, "", "failed", "bootout exited 5")
        return UnitOutcome(label, "", "unloaded")

    def forget_unit_files(self) -> UnitOutcome:
        self.calls.append(("forget", ""))
        return UnitOutcome("", "", "failed" if self.reload_fails else "unchanged", "no bus")

    def unload_commands(self, labels: Iterable[str]) -> tuple[str, ...]:
        return tuple(f"launchctl bootout gui/501/{label}" for label in labels)

    def domain(self) -> str:
        return "launchd gui/501"


class Settings:
    def __init__(self, error: bool = False) -> None:
        self.error = error
        self.read: list[Path] = []

    def load(self, path: Path) -> AcpSettings:
        self.read.append(path)
        if self.error:
            raise ConfigError(str(path), "[acp] searxng must be one of ask, never")
        return AcpSettings(bootstrap_timeout_seconds=3, live_poll_seconds=1.0)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class World:
    def __init__(
        self,
        provisioner: Provisioner | None = None,
        *,
        units: Units | None = None,
        loader: Loader | None = None,
        answer: bool = True,
        settings: Settings | None = None,
        services: bool = True,
    ) -> None:
        self.provisioner = provisioner or Provisioner()
        self.units = units or Units()
        self.loader = loader or Loader()
        self.settings = settings or Settings()
        self.said: list[str] = []
        self.asked: list[str] = []
        self.clock = Clock()
        self.served: list[Path] = []

        def machine(settings: AcpSettings, *, user_config: Path) -> AcpMachine:
            assert user_config == USER
            return AcpMachine(
                connector=None,  # type: ignore[arg-type]
                postgres=None,  # type: ignore[arg-type]
                lock=None,  # type: ignore[arg-type]
                units=self.units if services else None,  # type: ignore[arg-type]
                loader=self.loader,  # type: ignore[arg-type]
                searxng=self.provisioner,  # type: ignore[arg-type]
            )

        def confirm(question: str) -> bool:
            self.asked.append(question)
            return answer

        world = self

        class Serve:
            def __init__(self, settings: AcpSettings, *, user_config: Path) -> None:
                world.served.append(user_config)

            def run(self) -> int:
                return 0

        self.command = SearxngCommand(
            machine=machine,
            serve=Serve,
            settings=self.settings,  # type: ignore[arg-type]
            user_config=lambda: USER,
            echo=self.said.append,
            confirm=confirm,
            sleep=self.clock.sleep,
            clock=self.clock,
        )

    @property
    def text(self) -> str:
        return "\n".join(self.said)


def test_the_command_is_its_interface() -> None:
    assert isinstance(World().command, SearxngCommandInterface)


def test_install_asks_then_pulls_writes_loads_and_waits() -> None:
    world = World()

    assert world.command.install(yes=False) == 0

    (question,) = world.asked
    assert "searxng/searxng@sha256:fc1d81d7e9d0" in question and "127.0.0.1:28180" in question
    assert world.provisioner.calls[:2] == ["offer", "prepare"]
    assert world.units.writes == [(("searxng",), "always")]
    assert world.loader.calls == [("load", LABEL)]
    assert "launchctl bootout gui/501/dev.vibey.searxng" in world.text
    assert "answers as vibey's own" in world.text
    assert world.settings.read == [USER]  # the person's own file, never the folder it runs in


def test_yes_answers_in_advance_and_a_running_unit_is_restarted() -> None:
    world = World(loader=Loader(running=True))
    assert world.command.install(yes=True) == 0
    assert world.asked == [] and world.loader.calls == [("restart", LABEL)]


def test_declining_installs_nothing() -> None:
    world = World(answer=False)
    assert world.command.install(yes=False) == 1
    assert "prepare" not in world.provisioner.calls and world.units.writes == []
    assert "Nothing was installed" in world.text


@pytest.mark.parametrize(
    ("found", "said"),
    [
        ({"own_url": "VIBEY_SEARXNG_URL"}, "names your own SearXNG"),
        ({"runtime": None}, "found neither podman nor docker"),
        ({"answering": True}, "already answers"),
    ],
)
def test_install_refuses_what_it_should_not_install_over(found: dict[str, Any], said: str) -> None:
    world = World(Provisioner(**found))
    assert world.command.install(yes=True) == 1
    assert said in world.text and "prepare" not in world.provisioner.calls


def test_an_installed_searxng_can_be_installed_again_to_update_it() -> None:
    world = World(Provisioner(answering=True, provisioned=True))
    assert world.command.install(yes=True) == 0
    assert "prepare" in world.provisioner.calls


def test_install_as_root_does_nothing() -> None:
    world = World()
    world.loader.refusal = "vibey acp does not load units as root"
    assert world.command.install(yes=True) == 1
    assert world.provisioner.calls == [] and "root" in world.text


def test_a_failed_download_writes_no_unit() -> None:
    world = World()
    world.provisioner.prepared = SearxngPrepared(False, "`podman pull` failed: denied")
    assert world.command.install(yes=True) == 1
    assert world.units.writes == [] and "denied" in world.text


@pytest.mark.parametrize(
    ("units", "loader", "said"),
    [
        (Units("kept-differing"), Loader(), "kept as you edited it"),
        (Units("failed"), Loader(), "was not written"),
        (Units("raise"), Loader(), "No unit was written"),
        (Units(), Loader(available=False), "vibey searxng serve"),
    ],
)
def test_a_unit_that_cannot_run_fails_the_install(units: Units, loader: Loader, said: str) -> None:
    world = World(units=units, loader=loader)
    assert world.command.install(yes=True) == 1
    assert said in world.text and world.loader.calls == []


def test_a_unit_that_will_not_load_fails_the_install() -> None:
    world = World()
    world.loader.fail = True
    assert world.command.install(yes=True) == 1
    assert "could not be started: EIO" in world.text


def test_a_searxng_that_never_answers_fails_within_the_bound() -> None:
    world = World()
    world.provisioner.answers = False
    assert world.command.install(yes=True) == 1
    assert "did not answer as vibey's own within 3 s" in world.text
    assert world.clock.now >= 3


def test_status_says_each_part() -> None:
    world = World(Provisioner(provisioned=True))
    assert world.command.status() == 0
    assert f"runtime     {RUNTIME}" in world.said
    assert any(line.startswith("installed   searxng/searxng@sha256:") for line in world.said)
    assert "image       here" in world.said and "unit        not loaded" in world.said
    assert "answering   yes (as vibey own)" in world.said


def test_status_before_any_install() -> None:
    world = World(Provisioner(runtime=None, own_url="VIBEY_SEARXNG_URL"))
    assert world.command.status() == 0
    assert any("none: install Podman or Docker" in line for line in world.said)
    assert any(line.startswith("your own") for line in world.said)
    assert any(line.startswith("installed   no") for line in world.said)
    assert "answering   no" in world.said


def test_status_says_an_older_image_and_an_unreachable_service_manager() -> None:
    provisioner = Provisioner(provisioned=True)
    provisioner.kept = SearxngProvision(
        "docker.io/searxng/searxng@sha256:" + "0" * 64, 28180, RECORD.marker, LABEL, RUNTIME
    )
    world = World(provisioner, loader=Loader(available=False))
    world.command.status()
    assert any(line.startswith("update") for line in world.said)
    assert "unit        unknown: no service manager to ask" in world.said


def test_uninstall_unloads_removes_and_keeps_the_files() -> None:
    world = World(Provisioner(provisioned=True))
    assert world.command.uninstall(purge=False) == 0
    assert world.loader.calls == [("unload", LABEL), ("forget", "")]
    assert world.units.removed == [LABEL] and "rm" in world.provisioner.calls
    assert "purge" not in world.provisioner.calls and "--purge removes them" in world.text


def test_uninstall_purge_removes_the_image_and_the_files() -> None:
    world = World(Provisioner(provisioned=True))
    assert world.command.uninstall(purge=True) == 0
    assert "purge" in world.provisioner.calls
    world.provisioner.purged = ["the image was kept: image in use"]
    assert world.command.uninstall(purge=True) == 1
    assert "image in use" in world.text


def test_uninstall_with_nothing_installed_uses_the_configured_label() -> None:
    world = World()
    assert world.command.uninstall(purge=False) == 0
    assert world.loader.calls[0] == ("unload", LABEL)


@pytest.mark.parametrize("trouble", ["unload", "reload", "remove", "rm", "label", "root"])
def test_uninstall_says_what_failed(trouble: str) -> None:
    world = World(Provisioner())
    if trouble == "unload":
        world.loader.unload_fails = True
    elif trouble == "reload":
        world.loader.reload_fails = True
    elif trouble == "remove":
        world.units.remove_action = "failed"
    elif trouble == "rm":
        world.provisioner.removed = "daemon down"
    elif trouble == "label":
        world.units.label_error = True
    else:
        world.loader.refusal = "as root"
    code = world.command.uninstall(purge=False)
    assert code == (0 if trouble == "label" else 1)
    if trouble == "label":
        assert world.loader.calls == []  # no label: nothing unloaded, the container still goes
        assert "rm" in world.provisioner.calls


def test_a_users_file_vibey_cannot_read_is_a_configuration_refusal() -> None:
    world = World(settings=Settings(error=True))
    for run in (
        world.command.serve,
        world.command.status,
        lambda: world.command.install(yes=True),
        lambda: world.command.uninstall(purge=True),
    ):
        assert run() == 78
    assert "searxng must be one of" in world.text
    assert world.command.doctor_line().startswith("UNKNOWN searxng")


def test_no_user_level_services_is_said() -> None:
    world = World(services=False)
    assert world.command.status() == 78
    assert "no user-level services" in world.text


def test_serve_runs_the_persons_own_serve() -> None:
    world = World()
    assert world.command.serve() == 0
    assert world.served == [USER]


# -- doctor's line ------------------------------------------------------------------------------


def test_doctor_warns_when_vibey_installed_none() -> None:
    line = World().command.doctor_line()
    assert line.startswith("WARN searxng") and "vibey searxng install" in line
    assert "podman found" in line
    none = World(Provisioner(runtime=None)).command.doctor_line()
    assert "no podman or docker on your PATH" in none


def test_doctor_says_unknown_for_the_persons_own() -> None:
    line = World(Provisioner(own_url="VIBEY_SEARXNG_URL")).command.doctor_line()
    assert line.startswith("UNKNOWN searxng") and "VIBEY_SEARXNG_URL" in line


def test_doctor_passes_vibeys_answering_searxng() -> None:
    line = World(Provisioner(provisioned=True), loader=Loader(running=True)).command.doctor_line()
    assert line.startswith("PASS searxng") and "127.0.0.1:28180" in line


@pytest.mark.parametrize("trouble", ["image", "unit", "answering", "older"])
def test_doctor_warns_with_the_first_thing_wrong(trouble: str) -> None:
    provisioner = Provisioner(provisioned=True)
    loader = Loader(running=trouble != "unit")
    if trouble == "image":
        provisioner.present = False
    if trouble == "answering":
        provisioner.answers = False
    if trouble == "older":
        provisioner.kept = SearxngProvision(
            "docker.io/searxng/searxng@sha256:" + "0" * 64, 28180, RECORD.marker, LABEL, RUNTIME
        )
    line = World(provisioner, loader=loader).command.doctor_line()
    assert line.startswith("WARN searxng")
    expected = {
        "image": "image is not here",
        "unit": "is not loaded",
        "answering": "does not answer",
        "older": "newer image",
    }
    assert expected[trouble] in line


def test_doctor_never_raises() -> None:
    world = World()

    def broken() -> SearxngOffer:
        raise RuntimeError("\x1b[2Jboom")

    world.provisioner.offer = broken  # type: ignore[method-assign]
    line = world.command.doctor_line()
    assert line.startswith("UNKNOWN searxng") and "\x1b" not in line


# -- the command line ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "called"),
    [
        (["searxng", "install", "--yes"], ("install", {"yes": True})),
        (["searxng", "install"], ("install", {"yes": False})),
        (["searxng", "status"], ("status", {})),
        (["searxng", "uninstall", "--purge"], ("uninstall", {"purge": True})),
        (["searxng", "serve"], ("serve", {})),
    ],
)
def test_the_commands_reach_the_command_object(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], called: tuple[str, dict[str, Any]]
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class Recorder:
        def __getattr__(self, name: str) -> Any:
            def method(**kwargs: Any) -> int:
                calls.append((name, kwargs))
                return 3

            return method

    monkeypatch.setattr("vibey.cli.searxng.SEARXNG_COMMAND", Recorder())
    result = runner.invoke(app, argv)
    assert result.exit_code == 3 and calls == [called]


def test_serve_is_hidden_from_help() -> None:
    result = runner.invoke(app, ["searxng", "--help"])
    assert result.exit_code == 0
    assert "install" in result.output and "uninstall" in result.output
    assert "serve" not in result.output
