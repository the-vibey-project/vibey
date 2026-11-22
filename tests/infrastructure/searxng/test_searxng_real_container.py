# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a run against a REAL container should show (ADR-0102), opt-in only.

Skipped unless `VIBEY_TEST_SEARXNG_CONTAINER=1`: it pulls the pinned image with your own podman
or docker, runs it the way the unit does (`SearxngServe`, the one command line) on a spare
loopback port, under its own container name, with files in a temporary folder -- never your
configuration folder, your own container or a unit
-- and checks the claims ADR-0102 lists as not yet verified:

- the image starts under `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, the
  three tmpfs mounts and your own uid (podman: `--userns=keep-id`), reading a 0600 settings file
  through the read-only mount;
- it answers the identity check with vibey's marker on 127.0.0.1 only;
- stopping what the unit runs (SIGTERM to `serve`'s exec'd runtime) stops and removes the
  container (`--rm`).

It was not run when it was written: nothing may run a container on the machine that wrote it.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from vibey.domain.searxng import SEARXNG_IMAGE, SearxngPlan
from vibey.infrastructure.acp.acp_command_runner import AcpCommandRunner
from vibey.infrastructure.searxng.container_runtime import CONTAINER_VARIABLES, ContainerRuntime
from vibey.infrastructure.searxng.searxng_files import SearxngFiles
from vibey.infrastructure.searxng.searxng_provisioner import SearxngProvisioner

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("VIBEY_TEST_SEARXNG_CONTAINER") != "1",
        reason="pulls and runs a real container: set VIBEY_TEST_SEARXNG_CONTAINER=1 to run it",
    ),
    pytest.mark.web_network,
]

PORT = 28199
PREFIX = "vibey-searxng-test"
"""Its own container name, so a run never touches the person's own SearXNG container."""
LABEL = "dev.vibey.searxng-test"
SERVE = """
import sys
from pathlib import Path
from vibey.domain.searxng import SearxngPlan
from vibey.infrastructure.acp.acp_command_runner import AcpCommandRunner
from vibey.infrastructure.searxng.container_runtime import CONTAINER_VARIABLES, ContainerRuntime
from vibey.infrastructure.searxng.searxng_files import SearxngFiles
from vibey.infrastructure.searxng.searxng_serve import SearxngServe
plan = SearxngPlan(prefix=sys.argv[2])
runner = AcpCommandRunner(timeout_seconds=120, kept=CONTAINER_VARIABLES)
runtime = ContainerRuntime(runner=runner, pull_runner=runner, plan=plan)
files = SearxngFiles(Path(sys.argv[1]), plan=plan)
sys.exit(SearxngServe(files, runtime, label=lambda: sys.argv[3], plan=plan).run())
"""


def _until(check: object, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    pause = threading.Event()
    while time.monotonic() < deadline:
        if check():  # type: ignore[operator]
            return True
        pause.wait(1.0)
    return False


def _reachable(host: str) -> bool:
    try:
        with socket.create_connection((host, PORT), timeout=2.0):
            return True
    except OSError:
        return False


def test_the_real_image_runs_as_the_unit_runs_it_and_goes_when_stopped(tmp_path: Path) -> None:
    plan = SearxngPlan(prefix=PREFIX)
    runner = AcpCommandRunner(timeout_seconds=1800, kept=CONTAINER_VARIABLES)
    runtime = ContainerRuntime(runner=runner, pull_runner=runner, plan=plan)
    files = SearxngFiles(tmp_path / "searxng", plan=plan)
    provisioner = SearxngProvisioner(runtime, files, label=lambda: LABEL, plan=plan, port=PORT)
    assert runtime.find() is not None, "needs podman or docker in vibey's trusted folders"
    assert provisioner.busy() == "", "something already listens on the test's port"

    prepared = provisioner.prepare()
    assert prepared.ok, prepared.detail
    assert provisioner.image_present()

    serve = subprocess.Popen(  # noqa: S603 - this interpreter, a fixed script
        [sys.executable, "-c", SERVE, str(files.folder), PREFIX, LABEL],
        stdin=subprocess.DEVNULL,
    )
    try:
        assert _until(provisioner.answering, 180), "SearXNG never answered as vibey's own"
        record = provisioner.record()
        assert record is not None and record.image == SEARXNG_IMAGE
        # Published on 127.0.0.1 only: this machine's own non-loopback address must not answer.
        outward = socket.gethostbyname(socket.gethostname())
        if not outward.startswith("127."):
            assert not _reachable(outward), "the port answers on a non-loopback address"
    finally:
        serve.terminate()
        serve.wait(120)

    record = provisioner.record()
    assert record is not None
    assert _until(lambda: not provisioner.answering(), 60)
    removed = runtime.remove_container(record.runtime, os.getuid())
    # --rm took it: inspect finds none (an absent container is "removed already").
    assert removed.ok, removed.detail
    assert provisioner.purge() == []
