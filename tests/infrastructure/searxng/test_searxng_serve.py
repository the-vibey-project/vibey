# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`SearxngServe`: what the SearXNG unit runs checks the person's record and the image, never
pulls, and execs the one fixed command line with a minimal environment (ADR-0102). `execve` and
the runtime are faked: nothing runs."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

import pytest

from vibey.domain.searxng import SEARXNG_IMAGE
from vibey.infrastructure.searxng.container_runtime import RuntimeOutcome
from vibey.infrastructure.searxng.interfaces.searxng_serve_interface import SearxngServeInterface
from vibey.infrastructure.searxng.searxng_files import SearxngFiles
from vibey.infrastructure.searxng.searxng_serve import EXIT_CONFIG, SearxngServe


class Runtime:
    def __init__(self) -> None:
        self.present = True
        self.removed = RuntimeOutcome(ok=True)
        self.calls: list[str] = []

    def find(self) -> str | None:
        return None

    def image_present(self, runtime: str, image: str) -> bool:
        self.calls.append("inspect")
        return self.present

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        self.calls.append("pull")
        return RuntimeOutcome(ok=True)

    def remove_container(self, runtime: str) -> RuntimeOutcome:
        self.calls.append("rm")
        return self.removed

    def remove_image(self, runtime: str, image: str) -> RuntimeOutcome:
        self.calls.append("rmi")
        return RuntimeOutcome(ok=True)


class World:
    def __init__(self, tmp_path: Path) -> None:
        self.runtime_path = tmp_path / "bin" / "podman"
        self.runtime_path.parent.mkdir()
        self.runtime_path.write_text("#!/bin/sh\n", "utf-8")
        self.runtime_path.chmod(0o755)
        self.files = SearxngFiles(tmp_path / "config" / "searxng")
        self.runtime = Runtime()
        self.execs: list[tuple[str, list[str], dict[str, str]]] = []
        self.said: list[str] = []
        self.environ = {
            "HOME": "/home/op",
            "XDG_RUNTIME_DIR": "/run/user/501",
            "VIBEY_PG_URL": "postgresql://secret",
            "VIBEY_BRAVE_API_KEY": "fake-brave-key",
            "PATH": "/tmp/evil:/usr/bin",
        }

    def install(self) -> None:
        self.files.ensure(
            image=SEARXNG_IMAGE,
            port=28180,
            label="dev.vibey.searxng",
            runtime=str(self.runtime_path),
        )

    def serve(self) -> int:
        def execve(path: str, argv: list[str], env: Mapping[str, str]) -> None:
            self.execs.append((path, argv, dict(env)))

        return SearxngServe(
            self.files,
            self.runtime,
            execve=execve,
            environ=self.environ,
            uid=lambda: 501,
            gid=lambda: 20,
            say=self.said.append,
        ).run()


def test_serve_is_its_interface(tmp_path: Path) -> None:
    assert isinstance(SearxngServe(SearxngFiles(tmp_path), Runtime()), SearxngServeInterface)


def test_serve_execs_the_one_command_line_with_a_minimal_environment(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()

    assert world.serve() == 0

    ((path, argv, env),) = world.execs
    assert path == str(world.runtime_path) == argv[0]
    assert argv[1:3] == ["run", "--rm"] and argv[-1] == SEARXNG_IMAGE
    assert "--pull=never" in argv and "127.0.0.1:28180:8080" in argv
    assert f"{world.files.settings_path}:/etc/searxng/settings.yml:ro" in argv
    assert env["HOME"] == "/home/op" and env["XDG_RUNTIME_DIR"] == "/run/user/501"
    assert "VIBEY_PG_URL" not in env and "VIBEY_BRAVE_API_KEY" not in env
    assert "/tmp/evil" not in env["PATH"]
    assert env["PATH"].split(os.pathsep)[0] == str(world.runtime_path.parent)
    assert world.runtime.calls == ["inspect", "rm"]  # a leftover container goes first; no pull


def test_nothing_installed_is_a_configuration_refusal(tmp_path: Path) -> None:
    world = World(tmp_path)
    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and "vibey searxng install" in world.said[0]


def test_a_missing_image_is_an_error_and_never_a_download(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.runtime.present = False

    assert world.serve() == 1
    assert world.execs == [] and "pull" not in world.runtime.calls
    assert "never downloads" in world.said[0]


def test_a_record_vibey_would_not_write_runs_nothing(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    record = world.files.folder / "provision.json"
    data = json.loads(record.read_text("utf-8"))
    data["runtime"] = "/bin/sh"
    record.write_text(json.dumps(data), "utf-8")

    assert world.serve() == EXIT_CONFIG
    assert world.execs == [] and world.runtime.calls == []


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
    assert "is gone" in world.said[0]


def test_a_leftover_container_that_will_not_go_runs_nothing(tmp_path: Path) -> None:
    world = World(tmp_path)
    world.install()
    world.runtime.removed = RuntimeOutcome(ok=False, detail="daemon down")

    assert world.serve() == 1 and world.execs == []
    assert "daemon down" in world.said[0]


@pytest.mark.parametrize("uid", [0])
def test_serve_never_runs_the_container_as_root(tmp_path: Path, uid: int) -> None:
    world = World(tmp_path)
    world.install()
    serve = SearxngServe(world.files, world.runtime, execve=lambda *a: None, uid=lambda: uid)
    with pytest.raises(ValueError, match="root"):
        serve.run()
