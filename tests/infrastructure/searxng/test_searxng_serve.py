# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`SearxngServe`: what the SearXNG unit runs checks the person's record, the label, the settings,
the runtime (vetted against vibey's trusted folders and a fresh look) and the image, never pulls,
and execs the one fixed command line with a minimal environment (ADR-0102). `execve` and the
runtime's commands are faked: nothing runs."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

import pytest

from vibey.domain.searxng import SEARXNG_IMAGE, SearxngPlan
from vibey.infrastructure.searxng.container_runtime import ContainerRuntime, RuntimeOutcome
from vibey.infrastructure.searxng.interfaces.searxng_serve_interface import SearxngServeInterface
from vibey.infrastructure.searxng.searxng_files import SearxngFiles
from vibey.infrastructure.searxng.searxng_serve import EXIT_CONFIG, SearxngServe

LABEL = "dev.vibey.searxng"
_REAL_LOOKUP = ContainerRuntime.__dict__["_lookup"]


class Runtime(ContainerRuntime):
    """The real vetting over temporary trusted folders; the commands themselves faked."""

    def __init__(self, folder: Path) -> None:
        super().__init__(
            runner=None,  # type: ignore[arg-type]
            pull_runner=None,  # type: ignore[arg-type]
            dirs=(str(folder),),
            roots=(f"{folder.parent}/",),
        )
        self.present = True
        self.removed = RuntimeOutcome(ok=True)
        self.calls: list[str] = []
        self.where: str | None = ""
        """Docker's context endpoint as `endpoint` reads it ("" for podman, None unreadable)."""

    def endpoint(self, runtime: str) -> str | None:
        self._checked(runtime)
        self.calls.append("context")
        return self.where

    def image_present(self, runtime: str, image: str) -> bool:
        # Not vetted here, so the tests pin serve's own vetting (the real one vets again).
        self.calls.append("inspect")
        return self.present

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        self.calls.append("pull")
        return RuntimeOutcome(ok=True)

    def remove_container(self, runtime: str, uid: int) -> RuntimeOutcome:
        self._checked(runtime)
        self.calls.append(f"rm {uid}")
        return self.removed


@pytest.fixture(autouse=True)
def _real_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ContainerRuntime, "_lookup", _REAL_LOOKUP)


class World:
    def __init__(self, tmp_path: Path) -> None:
        self.bin = tmp_path / "trusted" / "bin"
        self.bin.mkdir(parents=True)
        self.runtime_path = self.bin / "podman"
        self.runtime_path.write_text("#!/bin/sh\n", "utf-8")
        self.runtime_path.chmod(0o755)
        self.plan = SearxngPlan(runtime_dirs=(str(self.bin),))
        self.files = SearxngFiles(tmp_path / "config" / "searxng", plan=self.plan)
        self.runtime = Runtime(self.bin)
        self.execs: list[tuple[str, list[str], dict[str, str]]] = []
        self.said: list[str] = []
        self.label = LABEL
        self.unit: str | None = None
        """The label the unit was loaded under (`--label`); None for a unit written before."""
        self.uid = 501
        self.environ = {
            "HOME": "/home/op",
            "XDG_RUNTIME_DIR": "/run/user/501",
            "VIBEY_PG_URL": "postgresql://secret",
            "VIBEY_BRAVE_API_KEY": "fake-brave-key",
            "DOCKER_HOST": "ssh://elsewhere",
            "CONTAINER_HOST": "ssh://elsewhere",
            "PATH": "/tmp/evil:/usr/bin",
        }

    def install(self, runtime: str | None = None) -> None:
        self.files.ensure(
            image=SEARXNG_IMAGE,
            port=28180,
            label=LABEL,
            runtime=runtime or str(self.runtime_path),
        )

    def serve(self) -> int:
        def execve(path: str, argv: list[str], env: Mapping[str, str]) -> None:
            self.execs.append((path, argv, dict(env)))

        return SearxngServe(
            self.files,
            self.runtime,
            label=lambda: self.label,
            unit=self.unit,
            plan=self.plan,
            execve=execve,
            environ=self.environ,
            uid=lambda: self.uid,
            gid=lambda: 20,
            say=self.said.append,
        ).run()

    def edit_record(self, **changes: object) -> None:
        record = self.files.folder / "provision.json"
        data = json.loads(record.read_text("utf-8"))
        data.update(changes)
        record.write_text(json.dumps(data), "utf-8")


def test_serve_is_its_interface(tmp_path: Path) -> None:
    world = World(tmp_path)
    assert isinstance(
        SearxngServe(world.files, world.runtime, label=lambda: LABEL), SearxngServeInterface
    )


def test_serve_execs_the_one_command_line_with_a_minimal_environment(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()

    assert world.serve() == 0

    ((path, argv, env),) = world.execs
    assert path == str(world.runtime_path) == argv[0]
    assert argv[1:3] == ["run", "--rm"] and argv[-1] == SEARXNG_IMAGE
    assert "--pull=never" in argv and "127.0.0.1:28180:8080" in argv
    assert "vibey-searxng-501" in argv and "vibey.searxng.owner=501" in argv
    assert f"{world.files.settings_path}:/etc/searxng/settings.yml:ro" in argv
    assert env["HOME"] == "/home/op" and env["XDG_RUNTIME_DIR"] == "/run/user/501"
    for gone in ("VIBEY_PG_URL", "VIBEY_BRAVE_API_KEY", "DOCKER_HOST", "CONTAINER_HOST"):
        assert gone not in env
    assert "/tmp/evil" not in env["PATH"]
    assert env["PATH"].split(os.pathsep)[0] == str(world.runtime_path.parent)
    assert world.runtime.calls == ["context", "inspect", "rm 501"]  # leftover first; no pull


def test_nothing_installed_is_a_configuration_refusal(tmp_path: Path) -> None:
    world = World(tmp_path)
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and "vibey searxng install" in world.said[0]


def test_a_searxng_stopped_for_good_never_runs(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.files.disable()
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == [] and "for good" in world.said[0]


def test_a_missing_image_is_a_refusal_and_never_a_download(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.runtime.present = False

    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and "pull" not in world.runtime.calls
    assert "never downloads" in world.said[0]


@pytest.mark.parametrize(
    "changes",
    [
        {"runtime": "/bin/sh"},
        {"runtime": "/Users/x/project/bin/docker"},
        {"image": "docker.io/searxng/searxng@sha256:" + "ab" * 32},
        {"port": 0},
    ],
)
def test_a_record_vibey_would_not_write_runs_nothing(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    world = World(tmp_path)
    world.install()
    world.edit_record(**changes)
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == []


def test_a_record_naming_another_label_runs_nothing(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.edit_record(label="dev.vibey.hub")
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == [] and "label" in world.said[0]


def test_a_recorded_runtime_that_fails_its_vetting_runs_nothing(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.runtime_path.chmod(0o777)  # writable by anyone now
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == []
    assert "writable by anyone" in world.said[0]


def test_a_runtime_installed_later_does_not_stop_the_recorded_one(tmp_path: Path) -> None:
    """Review 2 (R2): podman beside the recorded docker (and preferred by `find`) changes
    nothing at login: the recorded runtime still passes the trust checks and is run."""
    world = World(tmp_path)
    docker = world.bin / "docker"
    docker.write_text("#!/bin/sh\n", "utf-8")
    docker.chmod(0o755)
    world.install(str(docker))  # podman is there too, and preferred
    assert world.serve() == 0
    assert world.execs[0][0] == str(docker)


def test_a_settings_file_swapped_for_a_link_runs_nothing(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.files.settings_path.unlink()
    world.files.settings_path.symlink_to(tmp_path / "anything")
    assert world.serve() == EXIT_CONFIG and world.execs == []


def test_a_runtime_that_is_gone_runs_nothing(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.runtime_path.unlink()
    assert world.serve() == EXIT_CONFIG and world.execs == []
    assert "is not there" in world.said[0]


def test_a_leftover_container_that_will_not_go_is_a_retry(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.runtime.removed = RuntimeOutcome(ok=False, detail="daemon down")
    assert world.serve() == 1 and world.execs == []
    assert "daemon down" in world.said[0]


def test_a_container_vibey_did_not_start_is_a_refusal(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.runtime.removed = RuntimeOutcome(ok=False, detail="... that vibey did not start ...")
    assert world.serve() == EXIT_CONFIG and world.execs == []


def test_serve_as_root_refuses_without_a_traceback(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.uid = 0
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and "never root" in world.said[-1]


def test_a_refusal_goes_to_standard_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    world = World(tmp_path)
    serve = SearxngServe(SearxngFiles(tmp_path / "none"), world.runtime, label=lambda: LABEL)
    assert serve.run() == EXIT_CONFIG
    assert "vibey searxng install" in capsys.readouterr().err


def test_a_record_of_an_earlier_pin_is_refused_with_the_update_path(tmp_path: Path) -> None:
    """Review 2 (R1): never silently run another image; say how to update."""
    world = World(tmp_path)
    world.install()
    world.edit_record(image="docker.io/searxng/searxng@sha256:" + "ab" * 32)
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == []
    assert "earlier pinned image (abababababab)" in world.said[0]
    assert "vibey searxng install" in world.said[0]


def test_a_unit_left_from_an_earlier_label_prefix_runs_nothing(tmp_path: Path) -> None:
    """SP-ACP Task 11b-ii, P-9d-5: after `[supervisor] label_prefix` changed, the unit loaded
    under the old label still runs serve. It is not this configuration's unit, so it refuses
    (78, under the unit's throttle) and says how to unload it, rather than starting a second
    container beside the current unit's."""
    world = World(tmp_path)
    world.install()
    world.unit = "old.prefix.searxng"
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == []
    assert world.said == [
        "vibey searxng serve: this unit is old.prefix.searxng, but your [supervisor] "
        f"label_prefix now makes vibey's SearXNG unit {LABEL}: it is left from an earlier "
        "prefix, so it runs nothing; unload it (`launchctl bootout gui/$(id -u)/"
        "old.prefix.searxng` on macOS, `systemctl --user disable --now old.prefix.searxng` on "
        "Linux) and remove its file"
    ]


def test_the_current_units_label_serves(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.unit = LABEL
    assert world.serve() == 0 and len(world.execs) == 1


@pytest.mark.parametrize("where", ["ssh://me@far.example", "tcp://10.0.0.2:2376", None])
def test_a_docker_context_moved_off_this_computer_since_install_runs_nothing(
    tmp_path: Path, where: str | None
) -> None:
    """Review 1 I-3: a later `docker context use <remote>` never starts SearXNG on another
    machine at login: serve reads the context again and refuses (78) before anything runs."""
    world = World(tmp_path)
    world.install()
    world.runtime.where = where
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == ["context"]
    assert "not this computer's own daemon" in world.said[0]


def test_the_run_is_pinned_to_the_local_context_it_was_checked_against(tmp_path: Path) -> None:
    """The context is read once and the run is pinned to it (`DOCKER_HOST`), so a context
    switched between the check and the exec cannot move it."""
    world = World(tmp_path)
    world.install()
    world.runtime.where = "unix:///Users/op/.docker/run/docker.sock"
    assert world.serve() == 0
    ((_, _, env),) = world.execs
    assert env["DOCKER_HOST"] == "unix:///Users/op/.docker/run/docker.sock"


def test_podman_runs_with_no_docker_host(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    assert world.serve() == 0
    ((_, _, env),) = world.execs
    assert "DOCKER_HOST" not in env
