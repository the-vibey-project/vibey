# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`ServiceLoader` and `ServiceManagerRunner`: the only code that loads or restarts a unit on
this computer (ADR-0101).

Every command they may issue starts with `launchctl` or `systemctl --user`, names the user's own
launchd domain (`gui/<uid>`), never the `system` one, never `sudo`, never a shell. The argv are
fixed lists built from a label checked against a closed alphabet and a unit path checked to be
the one the service manager reads. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from vibey.application.acp.interfaces.service_loader_interface import ServiceLoaderInterface
from vibey.infrastructure.acp.interfaces.service_manager_runner_interface import (
    ServiceManagerRunnerInterface,
)
from vibey.infrastructure.acp.service_loader import ServiceLoader
from vibey.infrastructure.acp.service_manager_runner import (
    OUTPUT_LIMIT,
    ServiceManagerRunner,
)
from vibey.infrastructure.supervisor import SupervisorHost


class Runner:
    """The service manager: `loaded` and `running` name labels; anything else is not loaded."""

    def __init__(
        self,
        *,
        loaded: set[str] | None = None,
        running: set[str] | None = None,
        fail: set[str] | None = None,
        bus: str = "running",
        error: OSError | None = None,
    ) -> None:
        self.loaded = loaded or set()
        self.running = running or set()
        self.fail = fail or set()
        self.bus = bus
        self.error = error
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.calls.append(tuple(argv))
        if self.error is not None:
            raise self.error
        verb = argv[1] if argv[0] == "launchctl" else argv[2]
        if verb in self.fail:
            return 5, "Bootstrap failed: 5: Input/output error"
        if argv[0] == "launchctl":
            if verb == "print":
                label = argv[2].split("/")[-1]
                if argv[2].count("/") == 1:
                    return (0, "domain") if self.bus == "running" else (113, "")
                if label in self.running:
                    return 0, "state = running"
                return (0, "state = waiting") if label in self.loaded else (113, "")
            return 0, ""
        if verb == "is-system-running":
            return (0 if self.bus == "running" else 1), self.bus
        if verb == "is-active":
            label = argv[3].removesuffix(".service")
            return (0, "active") if label in self.running else (3, "inactive")
        return 0, ""


def _loader(tmp_path: Path, platform: str, runner: Runner) -> ServiceLoader:
    host = SupervisorHost(
        platform, home=tmp_path, environ={}, uid=501, run=runner, temp_roots=lambda: ()
    )
    return ServiceLoader(host, runner, 501)


def _unit(tmp_path: Path, platform: str, label: str) -> str:
    folder = (
        tmp_path / "Library" / "LaunchAgents"
        if platform == "launchd"
        else tmp_path / ".config" / "systemd" / "user"
    )
    suffix = ".plist" if platform == "launchd" else ".service"
    return str(folder / f"{label}{suffix}")


def _assert_user_scoped(calls: list[tuple[str, ...]]) -> None:
    assert calls
    for argv in calls:
        assert argv[0] in ("launchctl", "systemctl") and "sudo" not in argv
        assert argv[0] != "systemctl" or argv[1] == "--user"
        assert not any(a.startswith("system/") or a == "system" for a in argv)
        assert argv[0] != "launchctl" or any(a.startswith("gui/501") for a in argv)


def test_the_loader_is_its_port(tmp_path: Path) -> None:
    assert isinstance(_loader(tmp_path, "launchd", Runner()), ServiceLoaderInterface)
    assert isinstance(ServiceManagerRunner(timeout_seconds=5), ServiceManagerRunnerInterface)


@pytest.mark.parametrize("platform", ["launchd", "systemd"])
def test_every_issued_argv_is_user_scoped_and_never_sudo(tmp_path: Path, platform: str) -> None:
    runner = Runner()
    loader = _loader(tmp_path, platform, runner)
    label = "dev.vibey.hub"

    loader.available()
    loader.state(label)
    loader.load(label, _unit(tmp_path, platform, label))
    loader.restart(label)

    _assert_user_scoped(runner.calls)


def test_launchd_loads_into_the_users_gui_domain(tmp_path: Path) -> None:
    runner = Runner()
    unit = _unit(tmp_path, "launchd", "dev.vibey.hub")

    outcome = _loader(tmp_path, "launchd", runner).load("dev.vibey.hub", unit)

    assert outcome.action == "loaded"
    assert ("launchctl", "bootstrap", "gui/501", unit) in runner.calls


def test_systemd_reloads_then_enables_and_starts_the_unit(tmp_path: Path) -> None:
    runner = Runner()

    outcome = _loader(tmp_path, "systemd", runner).load(
        "dev.vibey.hub", _unit(tmp_path, "systemd", "dev.vibey.hub")
    )

    assert outcome.action == "loaded"
    assert runner.calls[-2:] == [
        ("systemctl", "--user", "daemon-reload"),
        ("systemctl", "--user", "enable", "--now", "dev.vibey.hub.service"),
    ]


@pytest.mark.parametrize("platform", ["launchd", "systemd"])
def test_existing_loaded_label_is_left_alone(tmp_path: Path, platform: str) -> None:
    runner = Runner(loaded={"dev.vibey.hub"}, running={"dev.vibey.hub"})

    outcome = _loader(tmp_path, platform, runner).load(
        "dev.vibey.hub", _unit(tmp_path, platform, "dev.vibey.hub")
    )

    assert outcome.action == "already-loaded"
    assert not any(a[1] in ("bootstrap", "bootout") for a in runner.calls)
    assert not any("enable" in a or "daemon-reload" in a for a in runner.calls)


def test_a_launchd_label_loaded_but_waiting_is_left_alone_too(tmp_path: Path) -> None:
    runner = Runner(loaded={"dev.vibey.hub"})
    outcome = _loader(tmp_path, "launchd", runner).load(
        "dev.vibey.hub", _unit(tmp_path, "launchd", "dev.vibey.hub")
    )
    assert outcome.action == "already-loaded"
    assert not any(a[1] == "bootstrap" for a in runner.calls)


@pytest.mark.parametrize("platform", ["launchd", "systemd"])
def test_restart_kicks_the_users_own_unit(tmp_path: Path, platform: str) -> None:
    runner = Runner()
    outcome = _loader(tmp_path, platform, runner).restart("dev.vibey.worker")
    assert outcome.action == "restarted"
    expected = (
        ("launchctl", "kickstart", "-k", "gui/501/dev.vibey.worker")
        if platform == "launchd"
        else ("systemctl", "--user", "restart", "dev.vibey.worker.service")
    )
    assert runner.calls == [expected]


@pytest.mark.parametrize("verb", ["bootstrap", "kickstart"])
def test_a_refused_launchd_command_is_a_failed_outcome_with_its_answer(
    tmp_path: Path, verb: str
) -> None:
    loader = _loader(tmp_path, "launchd", Runner(fail={verb}))
    outcome = (
        loader.load("dev.vibey.hub", _unit(tmp_path, "launchd", "dev.vibey.hub"))
        if verb == "bootstrap"
        else loader.restart("dev.vibey.hub")
    )
    assert outcome.action == "failed"
    assert "Input/output error" in outcome.detail and "5" in outcome.detail


@pytest.mark.parametrize("verb", ["daemon-reload", "enable", "restart"])
def test_a_refused_systemd_command_is_a_failed_outcome(tmp_path: Path, verb: str) -> None:
    runner = Runner(fail={verb})
    loader = _loader(tmp_path, "systemd", runner)
    outcome = (
        loader.restart("dev.vibey.hub")
        if verb == "restart"
        else loader.load("dev.vibey.hub", _unit(tmp_path, "systemd", "dev.vibey.hub"))
    )
    assert outcome.action == "failed"
    if verb == "daemon-reload":
        assert not any("enable" in call for call in runner.calls)


def test_a_service_manager_that_cannot_be_run_is_failed_never_raised(tmp_path: Path) -> None:
    loader = _loader(tmp_path, "launchd", Runner(error=FileNotFoundError(2, "No such file")))
    assert loader.restart("dev.vibey.hub").action == "failed"
    assert loader.load("dev.vibey.hub", _unit(tmp_path, "launchd", "dev.vibey.hub")).action == (
        "failed"
    )
    assert loader.available() is False


def test_no_user_systemd_bus_is_reported_unavailable(tmp_path: Path) -> None:
    # `systemctl --user` with no user manager prints nothing on stdout and fails to connect.
    assert _loader(tmp_path, "systemd", Runner(bus="")).available() is False
    assert _loader(tmp_path, "systemd", Runner(bus="offline")).available() is False
    for state in ("running", "degraded", "starting"):
        assert _loader(tmp_path, "systemd", Runner(bus=state)).available() is True


def test_no_launchd_gui_domain_is_reported_unavailable(tmp_path: Path) -> None:
    # Over SSH, with nobody logged in at the screen, `gui/<uid>` does not exist.
    runner = Runner(bus="")
    assert _loader(tmp_path, "launchd", runner).available() is False
    assert runner.calls == [("launchctl", "print", "gui/501")]
    assert _loader(tmp_path, "launchd", Runner()).available() is True


@pytest.mark.parametrize(
    "label",
    ["", "dev vibey", "gui/0/x", "../x", "-x", "x\ny", "system/dev.vibey.hub", "a;b", "a" * 200],
)
def test_a_label_outside_the_closed_alphabet_issues_nothing(tmp_path: Path, label: str) -> None:
    runner = Runner()
    loader = _loader(tmp_path, "launchd", runner)

    assert loader.restart(label).action == "failed"
    # The label's own unit path, so only the label check can refuse it.
    assert loader.load(label, _unit(tmp_path, "launchd", label)).action == "failed"
    assert loader.state(label).startswith("unknown")
    assert runner.calls == []


@pytest.mark.parametrize(
    "unit",
    [
        "relative/dev.vibey.hub.plist",
        "/elsewhere/dev.vibey.hub.plist",
        "LAUNCH_AGENTS/dev.vibey.worker.plist",
        "LAUNCH_AGENTS/../dev.vibey.hub.plist",
    ],
)
def test_a_unit_path_the_service_manager_would_not_read_issues_nothing(
    tmp_path: Path, unit: str
) -> None:
    runner = Runner()
    agents = str(tmp_path / "Library" / "LaunchAgents")
    outcome = _loader(tmp_path, "launchd", runner).load(
        "dev.vibey.hub", unit.replace("LAUNCH_AGENTS", agents)
    )
    assert outcome.action == "failed"
    assert runner.calls == []


def test_the_loader_names_the_unload_commands(tmp_path: Path) -> None:
    loader = _loader(tmp_path, "launchd", Runner())
    assert loader.unload_commands(("dev.vibey.hub",)) == (
        "launchctl bootout gui/501/dev.vibey.hub",
    )
    assert loader.domain() == "launchd gui/501"
    assert _loader(tmp_path, "systemd", Runner()).domain() == "systemctl --user"


# -- the runner ---------------------------------------------------------------------------


class Completed:
    def __init__(self, returncode: int, stdout: str) -> None:
        self.returncode = returncode
        self.stdout = stdout


class Run:
    def __init__(self, answer: Any) -> None:
        self.answer = answer
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> Completed:
        self.calls.append((argv, kwargs))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer  # type: ignore[no-any-return]


def _runner(run: Run, **kw: Any) -> ServiceManagerRunner:
    return ServiceManagerRunner(
        timeout_seconds=7,
        run=run,
        which=lambda name, path: f"/usr/bin/{name}",
        environ={
            "HOME": "/home/op",
            "USER": "op",
            "XDG_RUNTIME_DIR": "/run/user/501",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/501/bus",
            "VIBEY_PG_URL": "postgresql://secret@x/y",
            "GH_TOKEN": "ghp_secret",
            "PATH": "/attacker/bin",
        },
        **kw,
    )


def test_the_runner_runs_an_absolute_binary_bounded_with_stdin_closed_and_no_secrets() -> None:
    run = Run(Completed(0, "state = running"))

    assert _runner(run)(("launchctl", "print", "gui/501/dev.vibey.hub")) == (0, "state = running")

    ((argv, kwargs),) = run.calls
    assert argv == ["/usr/bin/launchctl", "print", "gui/501/dev.vibey.hub"]
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["timeout"] == 7
    assert kwargs.get("shell", False) is False
    env = kwargs["env"]
    assert "VIBEY_PG_URL" not in env and "GH_TOKEN" not in env
    assert env["PATH"] == "/usr/bin:/bin:/usr/sbin:/sbin"
    assert env["XDG_RUNTIME_DIR"] == "/run/user/501"  # systemctl --user finds the user bus by it
    assert env["HOME"] == "/home/op"


@pytest.mark.parametrize(
    "argv",
    [
        ("sudo", "launchctl", "print", "gui/501"),
        ("systemctl", "restart", "x.service"),
        ("systemctl", "--system", "restart", "x.service"),
        ("launchctl", "bootstrap", "system", "/Library/LaunchDaemons/x.plist"),
        ("launchctl", "kickstart", "-k", "system/x"),
        ("sh", "-c", "launchctl print gui/501"),
        ("launchctl", "asuser", "501", "/bin/sh", "-c", "id"),
        ("launchctl", "submit", "-l", "x", "--", "/bin/sh"),
        ("launchctl", "bootout", "gui/501/dev.vibey.hub"),
        ("launchctl", "print", "sudo"),
        ("launchctl",),
        ("systemctl", "--user", "stop", "dev.vibey.hub.service"),
        ("systemctl", "--user"),
        (),
    ],
)
def test_the_runner_refuses_anything_but_a_user_scoped_service_manager_command(
    argv: tuple[str, ...],
) -> None:
    run = Run(Completed(0, ""))
    code, out = _runner(run)(argv)
    assert code != 0 and "refused" in out
    assert run.calls == []


def test_the_runner_bounds_what_it_reads() -> None:
    run = Run(Completed(0, "x" * (OUTPUT_LIMIT * 3)))
    _, out = _runner(run)(("launchctl", "print", "gui/501"))
    assert len(out) == OUTPUT_LIMIT


def test_a_command_that_overruns_is_124_never_raised() -> None:
    run = Run(subprocess.TimeoutExpired(["launchctl"], 7))
    assert _runner(run)(("launchctl", "print", "gui/501")) == (124, "")


def test_a_binary_that_is_not_found_raises_os_error_for_the_host_to_report() -> None:
    runner = ServiceManagerRunner(
        timeout_seconds=7, run=Run(Completed(0, "")), which=lambda name, path: None, environ={}
    )
    with pytest.raises(FileNotFoundError, match="launchctl"):
        runner(("launchctl", "print", "gui/501"))


def test_the_real_runner_finds_binaries_on_the_fixed_path_only() -> None:
    runner = ServiceManagerRunner(timeout_seconds=7)
    assert runner._which is not None
    assert runner._environ is not None


def test_the_loader_checks_every_argv_again_before_any_runner_sees_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Whatever runner it was given: a check that refuses stops the command before it runs.
    runner = Runner()
    loader = _loader(tmp_path, "launchd", runner)
    monkeypatch.setattr(ServiceManagerRunner, "refusal", staticmethod(lambda argv: "no"))

    assert loader.restart("dev.vibey.hub").action == "failed"
    assert runner.calls == []
