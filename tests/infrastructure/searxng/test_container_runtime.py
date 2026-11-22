# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`ContainerRuntime`: podman, else docker, found once on the PATH and run only with the fixed
argv `SearxngPlan` builds, through the ACP process-group runner (ADR-0102). Every runtime call
here is faked: nothing is pulled, run or removed for real."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from vibey.infrastructure.acp.acp_command_runner import STILL_RUNNING, TIMED_OUT
from vibey.infrastructure.postgres import PostgresCommandResult
from vibey.infrastructure.searxng.container_runtime import CONTAINER_VARIABLES, ContainerRuntime
from vibey.infrastructure.searxng.interfaces.container_runtime_interface import (
    ContainerRuntimeInterface,
)

IMAGE = "docker.io/searxng/searxng@sha256:" + "ab" * 32


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


def _which(found: dict[str, str]) -> Callable[..., str | None]:
    asked: list[str] = []

    def which(name: str, path: str | None = None) -> str | None:
        asked.append(name)
        return found.get(name)

    which.asked = asked  # type: ignore[attr-defined]
    return which


def _runtime(
    found: dict[str, str], runner: FakeRunner | None = None, puller: FakeRunner | None = None
) -> ContainerRuntime:
    return ContainerRuntime(
        runner=runner or FakeRunner(), pull_runner=puller or FakeRunner(), which=_which(found)
    )


def test_the_runtime_is_its_interface() -> None:
    assert isinstance(_runtime({}), ContainerRuntimeInterface)


def test_podman_is_preferred_over_docker() -> None:
    both = {"podman": "/opt/homebrew/bin/podman", "docker": "/usr/local/bin/docker"}
    assert _runtime(both).find() == "/opt/homebrew/bin/podman"
    assert _runtime({"docker": "/usr/local/bin/docker"}).find() == "/usr/local/bin/docker"
    assert _runtime({}).find() is None


def test_a_relative_find_is_never_a_runtime() -> None:
    assert _runtime({"podman": "bin/podman", "docker": "./docker"}).find() is None


def test_the_runtime_is_found_once() -> None:
    which = _which({"docker": "/usr/local/bin/docker"})
    runtime = ContainerRuntime(runner=FakeRunner(), pull_runner=FakeRunner(), which=which)
    runtime.find()
    runtime.find()
    assert which.asked == ["podman", "docker"]  # type: ignore[attr-defined]


def test_image_present_asks_inspect_and_downloads_nothing() -> None:
    runner, puller = FakeRunner(PostgresCommandResult(0)), FakeRunner()
    runtime = _runtime({}, runner, puller)
    assert runtime.image_present("/usr/bin/podman", IMAGE)
    assert runner.calls == [("/usr/bin/podman", "image", "inspect", "--format", "{{.Id}}", IMAGE)]
    assert puller.calls == []
    missing = _runtime({}, FakeRunner(PostgresCommandResult(1, stderr="no such image")))
    assert not missing.image_present("/usr/bin/podman", IMAGE)


def test_pull_runs_on_the_install_bound_runner() -> None:
    runner, puller = FakeRunner(), FakeRunner(PostgresCommandResult(0))
    outcome = _runtime({}, runner, puller).pull("/usr/bin/podman", IMAGE)
    assert outcome.ok
    assert puller.calls == [("/usr/bin/podman", "pull", IMAGE)]
    assert runner.calls == []


@pytest.mark.parametrize(
    ("result", "still"),
    [
        (PostgresCommandResult(125, stderr="podman did not finish; it may still be running"), True),
        (
            PostgresCommandResult(TIMED_OUT, stderr="podman pull did not finish and was stopped"),
            False,
        ),
        (PostgresCommandResult(1, stderr="first\nError: \x1b[31mdenied\x1b[0m\n\n"), False),
    ],
)
def test_a_failed_pull_says_its_last_line_cleaned(
    result: PostgresCommandResult, still: bool
) -> None:
    outcome = _runtime({}, puller=FakeRunner(result)).pull("/usr/bin/podman", IMAGE)
    assert not outcome.ok
    assert outcome.still_running is still
    assert "\x1b" not in outcome.detail and "\n" not in outcome.detail
    assert outcome.detail


def test_a_failure_with_nothing_said_names_its_exit_code() -> None:
    outcome = _runtime({}, puller=FakeRunner(PostgresCommandResult(3))).pull(
        "/usr/bin/docker", IMAGE
    )
    assert outcome.detail == "docker exited 3"


def test_remove_container_counts_an_absent_container_as_removed() -> None:
    runner = FakeRunner(PostgresCommandResult(1, stderr="Error: no such container vibey-searxng"))
    outcome = _runtime({}, runner).remove_container("/usr/bin/podman")
    assert outcome.ok
    assert runner.calls == [("/usr/bin/podman", "rm", "-f", "vibey-searxng")]
    failed = _runtime({}, FakeRunner(PostgresCommandResult(1, stderr="daemon down")))
    assert not failed.remove_container("/usr/bin/podman").ok


def test_remove_image_runs_rmi_and_counts_a_missing_image_as_removed() -> None:
    runner = FakeRunner(PostgresCommandResult(1, stderr="Error: No such image: x"))
    assert _runtime({}, runner).remove_image("/usr/bin/docker", IMAGE).ok
    assert runner.calls == [("/usr/bin/docker", "rmi", IMAGE)]


def test_a_runtime_or_image_vibey_would_not_run_is_refused_before_any_command() -> None:
    runner = FakeRunner()
    runtime = _runtime({}, runner, runner)
    with pytest.raises(ValueError):
        runtime.pull("/bin/sh", IMAGE)
    with pytest.raises(ValueError):
        runtime.image_present("/usr/bin/podman", "docker.io/searxng/searxng:latest")
    assert runner.calls == []


def test_the_runtime_keeps_only_what_finds_its_daemon() -> None:
    assert {"XDG_RUNTIME_DIR", "DOCKER_HOST", "CONTAINER_HOST", "HOME"} <= set(CONTAINER_VARIABLES)
    for secret in ("VIBEY_PG_URL", "VIBEY_BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY", "PATH"):
        assert secret not in CONTAINER_VARIABLES
