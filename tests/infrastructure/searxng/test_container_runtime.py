# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`ContainerRuntime`: podman, else docker, found only in vibey's trusted folders (never the PATH),
vetted again at every use, run only with the fixed argv `SearxngPlan` builds, and removing only a
container vibey started for this user (ADR-0102). Every runtime call here is faked: nothing is
pulled, run or removed for real; the "runtimes" are files in a temporary folder."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from vibey.domain.searxng import SEARXNG_IMAGE, TRUSTED_RUNTIME_DIRS
from vibey.infrastructure.acp.acp_command_runner import STILL_RUNNING, TIMED_OUT
from vibey.infrastructure.postgres import PostgresCommandResult
from vibey.infrastructure.searxng.container_runtime import (
    CONTAINER_VARIABLES,
    DAEMON_VARIABLES,
    ContainerRuntime,
    RuntimeProblem,
)
from vibey.infrastructure.searxng.interfaces.container_runtime_interface import (
    ContainerRuntimeInterface,
)

IMAGE = SEARXNG_IMAGE
_REAL_LOOKUP = ContainerRuntime.__dict__["_lookup"]
"""Read at import, before the suite's guard stands in for it."""


@pytest.fixture(autouse=True)
def _real_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ContainerRuntime, "_lookup", _REAL_LOOKUP)


class FakeRunner:
    def __init__(self, *results: PostgresCommandResult) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._results = list(results) or [PostgresCommandResult(0)]

    def __call__(self, argv: tuple[str, ...]) -> PostgresCommandResult:
        self.calls.append(argv)
        return self._results.pop(0) if len(self._results) > 1 else self._results[0]

    @staticmethod
    def still_running(result: PostgresCommandResult) -> bool:
        return result.returncode == STILL_RUNNING

    @staticmethod
    def password_refused(argv: tuple[str, ...], result: PostgresCommandResult) -> bool:
        return False


class Trusted:
    """Two trusted folders under a temporary root, and a project's `bin/` outside them."""

    def __init__(self, tmp_path: Path) -> None:
        self.root = tmp_path / "trusted"
        self.first = self.root / "first"
        self.second = self.root / "second"
        self.outside = tmp_path / "project" / "bin"
        for folder in (self.first, self.second, self.outside):
            folder.mkdir(parents=True)

    def binary(self, folder: Path, name: str, mode: int = 0o755) -> str:
        path = folder / name
        path.write_text("#!/bin/sh\n", "utf-8")
        path.chmod(mode)
        return str(path)

    def runtime(
        self,
        runner: FakeRunner | None = None,
        puller: FakeRunner | None = None,
        *,
        uid: int | None = None,
    ) -> ContainerRuntime:
        return ContainerRuntime(
            runner=runner or FakeRunner(),
            pull_runner=puller or FakeRunner(),
            dirs=(str(self.first), str(self.second)),
            roots=(f"{self.root}/",),
            uid=(lambda: uid) if uid is not None else os.getuid,
        )


@pytest.fixture
def trusted(tmp_path: Path) -> Trusted:
    return Trusted(tmp_path)


def test_the_runtime_is_its_interface(trusted: Trusted) -> None:
    assert isinstance(trusted.runtime(), ContainerRuntimeInterface)


def test_podman_is_preferred_over_docker_in_folder_order(trusted: Trusted) -> None:
    docker = trusted.binary(trusted.first, "docker")
    podman = trusted.binary(trusted.second, "podman")
    assert trusted.runtime().find() == podman
    os.unlink(podman)
    assert trusted.runtime().find() == docker
    os.unlink(docker)
    assert trusted.runtime().find() is None


def test_the_runtime_is_looked_for_once(trusted: Trusted) -> None:
    runtime = trusted.runtime()
    assert runtime.find() is None
    trusted.binary(trusted.first, "docker")
    assert runtime.find() is None  # kept from the first look


def test_a_project_bin_on_the_path_is_never_a_runtime(
    trusted: Trusted, monkeypatch: pytest.MonkeyPatch
) -> None:
    trusted.binary(trusted.outside, "docker")
    monkeypatch.setenv("PATH", f"{trusted.outside}{os.pathsep}{os.environ.get('PATH', '')}")
    assert trusted.runtime().find() is None
    mine = trusted.binary(trusted.second, "docker")
    assert trusted.runtime().find() == mine


def test_a_homebrew_link_into_its_cellar_is_a_runtime(trusted: Trusted) -> None:
    cellar = trusted.root / "Cellar" / "docker" / "27.0" / "bin"
    cellar.mkdir(parents=True)
    real = trusted.binary(cellar, "docker")
    (trusted.first / "docker").symlink_to(real)
    runtime = trusted.runtime()
    assert runtime.find() == str(trusted.first / "docker")
    assert runtime.vet(str(trusted.first / "docker")) is None


@pytest.mark.parametrize(
    ("spoil", "reason"),
    [
        ("link-outside", RuntimeProblem.LEADS_OUTSIDE),
        ("world-writable", RuntimeProblem.SHARED_WRITE),
        ("group-writable", RuntimeProblem.SHARED_WRITE),
        ("not-executable", RuntimeProblem.NOT_EXECUTABLE),
        ("a-folder", RuntimeProblem.NOT_EXECUTABLE),
        ("someone-else", RuntimeProblem.FOREIGN_OWNER),
        ("gone", RuntimeProblem.GONE),
    ],
)
def test_a_candidate_that_fails_a_check_is_skipped_and_vetted_out(
    trusted: Trusted, spoil: str, reason: RuntimeProblem
) -> None:
    """Task 11b (review 2 N2-5): `vet` says why as a typed reason, not only as English text, so
    a caller telling "gone" apart never matches a wording."""
    candidate = trusted.first / "podman"
    uid = None
    if spoil == "link-outside":
        candidate.symlink_to(trusted.binary(trusted.outside, "podman"))
    elif spoil == "world-writable":
        trusted.binary(trusted.first, "podman", 0o777)
    elif spoil == "group-writable":
        trusted.binary(trusted.first, "podman", 0o775)  # 9d N-e: refused, as the docs say
    elif spoil == "not-executable":
        trusted.binary(trusted.first, "podman", 0o644)
    elif spoil == "a-folder":
        candidate.mkdir()
    elif spoil == "gone":
        candidate.symlink_to(trusted.root / "nowhere")
    else:
        if os.getuid() == 0:
            pytest.skip("root owns everything")
        trusted.binary(trusted.first, "podman")
        uid = os.getuid() + 1
    runtime = trusted.runtime(uid=uid)
    assert runtime.find() is None
    refusal = runtime.vet(str(candidate))
    assert refusal is not None and refusal.reason is reason and refusal.runtime == str(candidate)
    assert str(refusal) == f"{candidate} {reason.value}"


def test_every_command_refuses_a_recorded_runtime_outside_the_trusted_folders(
    trusted: Trusted,
) -> None:
    trusted.binary(trusted.first, "docker")
    evil = trusted.binary(trusted.outside, "docker")
    runner = FakeRunner()
    runtime = trusted.runtime(runner, runner)
    for run in (
        lambda: runtime.image_present(evil, IMAGE),
        lambda: runtime.pull(evil, IMAGE),
        lambda: runtime.remove_container(evil, 501),
        lambda: runtime.remove_image(evil, IMAGE),
    ):
        with pytest.raises(ValueError, match="trusted folders"):
            run()
    assert runner.calls == []


@pytest.mark.parametrize(
    "later",
    [
        ("second", "podman"),  # `brew install podman` beside Docker Desktop: podman is preferred
        ("first", "docker"),  # a Homebrew docker CLI ahead of Docker Desktop's
    ],
)
def test_a_runtime_installed_later_never_stops_the_recorded_one(
    trusted: Trusted, later: tuple[str, str]
) -> None:
    """Review 2 (R2): `vet` is the trust checks only; `find` chooses the runtime at install."""
    recorded = trusted.binary(
        trusted.second if later == ("first", "docker") else trusted.first, "docker"
    )
    trusted.binary(getattr(trusted, later[0]), later[1])
    runner = FakeRunner(PostgresCommandResult(0))
    runtime = trusted.runtime(runner)
    assert runtime.find() != recorded
    asked = len(runner.calls)  # with both found, `find` asks the first whether it answers
    assert runtime.vet(recorded) is None
    assert runtime.image_present(recorded, IMAGE)
    assert runtime.remove_image(recorded, IMAGE).ok
    assert [call[0] for call in runner.calls[asked:]] == [recorded, recorded]


def test_image_present_asks_inspect_and_downloads_nothing(trusted: Trusted) -> None:
    podman = trusted.binary(trusted.first, "podman")
    runner, puller = FakeRunner(PostgresCommandResult(0)), FakeRunner()
    assert trusted.runtime(runner, puller).image_present(podman, IMAGE)
    assert runner.calls == [(podman, "image", "inspect", "--format", "{{.Id}}", IMAGE)]
    assert puller.calls == []
    missing = trusted.runtime(FakeRunner(PostgresCommandResult(1, stderr="no such image")))
    assert not missing.image_present(podman, IMAGE)


def test_pull_runs_on_the_install_bound_runner(trusted: Trusted) -> None:
    podman = trusted.binary(trusted.first, "podman")
    runner, puller = FakeRunner(), FakeRunner(PostgresCommandResult(0))
    assert trusted.runtime(runner, puller).pull(podman, IMAGE).ok
    assert puller.calls == [(podman, "pull", IMAGE)] and runner.calls == []


@pytest.mark.parametrize(
    ("result", "still"),
    [
        (PostgresCommandResult(125, stderr="podman did not finish; it may still be running"), True),
        (PostgresCommandResult(TIMED_OUT, stderr="podman pull did not finish, stopped"), False),
        (PostgresCommandResult(1, stderr="first\nError: \x1b[31mdenied\x1b[0m\n\n"), False),
    ],
)
def test_a_failed_pull_says_its_last_line_cleaned(
    trusted: Trusted, result: PostgresCommandResult, still: bool
) -> None:
    podman = trusted.binary(trusted.first, "podman")
    outcome = trusted.runtime(puller=FakeRunner(result)).pull(podman, IMAGE)
    assert not outcome.ok and outcome.still_running is still
    assert "\x1b" not in outcome.detail and "\n" not in outcome.detail and outcome.detail


def test_a_failure_with_nothing_said_names_its_exit_code(trusted: Trusted) -> None:
    docker = trusted.binary(trusted.first, "docker")
    outcome = trusted.runtime(puller=FakeRunner(PostgresCommandResult(3))).pull(docker, IMAGE)
    assert outcome.detail == "docker exited 3"


def _labels(uid: str) -> PostgresCommandResult:
    return PostgresCommandResult(0, stdout=json.dumps({"vibey.searxng.owner": uid}) + "\n")


def test_only_a_container_carrying_this_users_owner_label_is_removed(trusted: Trusted) -> None:
    podman = trusted.binary(trusted.first, "podman")
    runner = FakeRunner(_labels("501"), PostgresCommandResult(0))
    assert trusted.runtime(runner).remove_container(podman, 501).ok
    assert runner.calls == [
        (
            podman,
            "container",
            "inspect",
            "--format",
            "{{json .Config.Labels}}",
            "vibey-searxng-501",
        ),
        (podman, "rm", "-f", "vibey-searxng-501"),
    ]


@pytest.mark.parametrize(
    "labels",
    [
        _labels("502"),
        PostgresCommandResult(0, stdout="null\n"),
        PostgresCommandResult(0, stdout="{}\n"),
        PostgresCommandResult(0, stdout="not json"),
        PostgresCommandResult(0, stdout=""),
    ],
)
def test_a_container_of_that_name_vibey_did_not_start_is_left(
    trusted: Trusted, labels: PostgresCommandResult
) -> None:
    podman = trusted.binary(trusted.first, "podman")
    runner = FakeRunner(labels)
    outcome = trusted.runtime(runner).remove_container(podman, 501)
    assert not outcome.ok and "vibey did not start" in outcome.detail
    assert [call[1] for call in runner.calls] == ["container"]  # never an rm


def test_an_absent_container_is_removed_already(trusted: Trusted) -> None:
    podman = trusted.binary(trusted.first, "podman")
    runner = FakeRunner(PostgresCommandResult(1, stderr="Error: no such container x"))
    outcome = trusted.runtime(runner).remove_container(podman, 501)
    assert outcome.ok and outcome.detail == "nothing to remove"
    down = FakeRunner(PostgresCommandResult(1, stderr="cannot connect to the daemon"))
    assert not trusted.runtime(down).remove_container(podman, 501).ok


def test_remove_image_runs_rmi_and_counts_a_missing_image_as_removed(trusted: Trusted) -> None:
    docker = trusted.binary(trusted.first, "docker")
    runner = FakeRunner(PostgresCommandResult(1, stderr="Error: No such image: x"))
    assert trusted.runtime(runner).remove_image(docker, IMAGE).ok
    assert runner.calls == [(docker, "rmi", IMAGE)]


def test_the_default_folders_are_the_platforms_and_never_the_path() -> None:
    mac = ContainerRuntime(runner=FakeRunner(), pull_runner=FakeRunner(), platform="darwin")
    linux = ContainerRuntime(runner=FakeRunner(), pull_runner=FakeRunner(), platform="linux")
    assert mac._dirs == TRUSTED_RUNTIME_DIRS["darwin"]  # type: ignore[attr-defined]
    assert linux._dirs == TRUSTED_RUNTIME_DIRS["linux"]  # type: ignore[attr-defined]
    assert "/opt/homebrew/bin" in TRUSTED_RUNTIME_DIRS["darwin"]


def test_the_runtime_sees_no_daemon_variable_and_no_secret() -> None:
    assert {"XDG_RUNTIME_DIR", "HOME"} <= set(CONTAINER_VARIABLES)
    for name in (*DAEMON_VARIABLES, "VIBEY_PG_URL", "VIBEY_BRAVE_API_KEY", "PATH"):
        assert name not in CONTAINER_VARIABLES


def test_the_suite_refuses_to_run_a_real_container_runtime(tmp_path: Path) -> None:
    """The suite's guard (`tests/conftest.py`): no test can exec or spawn docker or podman."""
    import subprocess

    fake = tmp_path / "docker"
    fake.write_text("#!/bin/sh\nexit 0\n", "utf-8")
    fake.chmod(0o755)
    with pytest.raises(AssertionError, match="real container runtime"):
        subprocess.run([str(fake), "ps"], check=False)  # noqa: S603 - the guard refuses it
    with pytest.raises(AssertionError, match="real container runtime"):
        os.execve(str(fake), [str(fake)], {})


def test_the_bootstraps_stop_check_names_only_vibeys_searxng(tmp_path: Path) -> None:
    from vibey.bootstrap import searxng_stopped

    class Units:
        def __init__(self, error: bool = False) -> None:
            self.error = error

        def label(self, name: str) -> str:
            if self.error:
                raise ValueError("[supervisor] must be a table")
            return f"dev.vibey.{name}"

    class Searxng:
        def disabled(self) -> bool:
            return True

    assert searxng_stopped(Units(), Searxng(), "dev.vibey.searxng")  # type: ignore[arg-type]
    assert not searxng_stopped(Units(), Searxng(), "dev.vibey.hub")  # type: ignore[arg-type]
    assert not searxng_stopped(Units(True), Searxng(), "dev.vibey.searxng")  # type: ignore[arg-type]
    assert not searxng_stopped(None, Searxng(), "dev.vibey.searxng")  # type: ignore[arg-type]


def test_a_runtime_inside_a_trusted_root_but_not_a_trusted_folder_is_refused(
    trusted: Trusted,
) -> None:
    trusted.binary(trusted.first, "podman")
    cellar = trusted.root / "Cellar" / "bin"
    cellar.mkdir(parents=True)
    stray = trusted.binary(cellar, "podman")  # under the trusted root, in no trusted folder
    refusal = trusted.runtime().vet(stray)
    assert refusal is not None and refusal.reason is RuntimeProblem.UNTRUSTED_PLACE
    assert "trusted folders" in str(refusal)


# -- SP-ACP Task 11b-ii: a podman machine that is down, docker's context ----------------------


def test_a_podman_that_does_not_answer_falls_back_to_a_docker_that_does(trusted: Trusted) -> None:
    """P-9d-1: podman is found first, but its machine is stopped (`podman info` fails) while
    Docker's daemon answers: docker is the runtime."""
    docker = trusted.binary(trusted.first, "docker")
    podman = trusted.binary(trusted.second, "podman")
    runner = FakeRunner(
        PostgresCommandResult(125, stderr="Cannot connect to Podman"), PostgresCommandResult(0)
    )
    assert trusted.runtime(runner).find() == docker
    assert runner.calls == [(podman, "info"), (docker, "info")]


def test_podman_stays_the_choice_when_neither_answers(trusted: Trusted) -> None:
    trusted.binary(trusted.first, "docker")
    podman = trusted.binary(trusted.second, "podman")
    runner = FakeRunner(PostgresCommandResult(1))
    assert trusted.runtime(runner).find() == podman  # its own error then says what is wrong


def test_a_single_runtime_is_never_asked_whether_it_answers(trusted: Trusted) -> None:
    podman = trusted.binary(trusted.first, "podman")
    runner = FakeRunner(PostgresCommandResult(1))
    assert trusted.runtime(runner).find() == podman
    assert runner.calls == []


def test_dockers_context_endpoint_is_read_and_podmans_is_none(trusted: Trusted) -> None:
    """P-9d-8: the Docker CLI's current context (`~/.docker/config.json`) may point at another
    machine even with no `DOCKER_HOST`."""
    docker = trusted.binary(trusted.first, "docker")
    podman = trusted.binary(trusted.second, "podman")
    runner = FakeRunner(PostgresCommandResult(0, stdout="ssh://me@far.example\n"))
    runtime = trusted.runtime(runner)
    assert runtime.endpoint(docker) == "ssh://me@far.example"
    assert runtime.endpoint(podman) == ""
    assert runner.calls == [
        (docker, "context", "inspect", "--format", "{{.Endpoints.docker.Host}}")
    ]
    failing = trusted.runtime(FakeRunner(PostgresCommandResult(1, stderr="no contexts")))
    assert failing.endpoint(docker) == ""  # unknown: the pull says what is wrong
    hostile = trusted.runtime(FakeRunner(PostgresCommandResult(0, stdout="tcp://x\x1b[2J\n")))
    assert hostile.endpoint(docker) == "tcp://x"  # cleaned of terminal escapes
