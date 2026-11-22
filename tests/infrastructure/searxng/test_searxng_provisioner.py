# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`SearxngProvisioner`: what is here, the download and the files, and the identity check, over
a faked runtime and the real files in a temporary folder (ADR-0102)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vibey.application.acp.interfaces.searxng_provisioner_interface import (
    SearxngProvisionerInterface,
)
from vibey.domain.searxng import SEARXNG_IMAGE
from vibey.infrastructure.searxng.container_runtime import RuntimeOutcome
from vibey.infrastructure.searxng.searxng_files import SearxngFiles
from vibey.infrastructure.searxng.searxng_provisioner import SearxngProvisioner

RUNTIME = "/opt/homebrew/bin/podman"


class Runtime:
    def __init__(
        self, found: str | None = RUNTIME, *, pulled: RuntimeOutcome | None = None
    ) -> None:
        self.found = found
        self.pulled = pulled or RuntimeOutcome(ok=True)
        self.calls: list[tuple[str, ...]] = []
        self.removed = RuntimeOutcome(ok=True)
        self.present = True

    def find(self) -> str | None:
        return self.found

    def image_present(self, runtime: str, image: str) -> bool:
        self.calls.append(("inspect", runtime, image))
        return self.present

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        self.calls.append(("pull", runtime, image))
        return self.pulled

    def remove_container(self, runtime: str) -> RuntimeOutcome:
        self.calls.append(("rm", runtime))
        return self.removed

    def remove_image(self, runtime: str, image: str) -> RuntimeOutcome:
        self.calls.append(("rmi", runtime, image))
        return self.removed


class Health:
    def __init__(self, *, answering: set[tuple[str, str | None]] | None = None) -> None:
        self.answering = answering or set()
        self.asked: list[tuple[str, str | None]] = []

    def __call__(self, url: str, marker: str | None) -> str | None:
        self.asked.append((url, marker))
        return (
            None
            if (url, marker) in self.answering
            else "could not be reached (ConnectionRefusedError)"
        )


def _provisioner(
    tmp_path: Path,
    runtime: Runtime | None = None,
    *,
    environ: dict[str, str] | None = None,
    health: Health | None = None,
) -> SearxngProvisioner:
    return SearxngProvisioner(
        runtime or Runtime(),
        SearxngFiles(tmp_path / "searxng"),
        label=lambda: "dev.vibey.searxng",
        environ=environ or {},
        health=health or Health(),
    )


def test_the_provisioner_is_its_port(tmp_path: Path) -> None:
    assert isinstance(_provisioner(tmp_path), SearxngProvisionerInterface)


def test_a_fresh_machine_offers_the_pinned_image_on_vibeys_port(tmp_path: Path) -> None:
    health = Health()
    found = _provisioner(tmp_path, health=health).offer()
    assert (found.runtime, found.own_url, found.answering, found.provisioned) == (
        RUNTIME,
        None,
        False,
        False,
    )
    assert found.port == 28180
    assert SEARXNG_IMAGE.split("sha256:")[1].startswith(found.short) and len(found.short) == 12
    assert health.asked == [("http://127.0.0.1:28180", None)]


def test_someone_elses_searxng_answering_on_the_port_means_no_install(tmp_path: Path) -> None:
    health = Health(answering={("http://127.0.0.1:28180", None)})
    assert _provisioner(tmp_path, health=health).offer().answering


@pytest.mark.parametrize("name", ["VIBEY_SEARXNG_URL", "WEBSEARCH_SEARXNG_URL"])
def test_the_persons_own_url_means_no_install_and_no_probe(tmp_path: Path, name: str) -> None:
    health = Health()
    found = _provisioner(tmp_path, environ={name: "http://127.0.0.1:9"}, health=health).offer()
    assert found.own_url == name and not found.answering and health.asked == []


def test_a_refused_search_setting_is_not_answering(tmp_path: Path) -> None:
    found = _provisioner(tmp_path, environ={"VIBEY_SEARCH_PROVIDER": "brave"}).offer()
    assert not found.answering


def test_prepare_pulls_the_pinned_image_then_writes_the_files(tmp_path: Path) -> None:
    runtime = Runtime()
    provisioner = _provisioner(tmp_path, runtime)

    prepared = provisioner.prepare()

    assert prepared.ok and "podman" in prepared.detail
    assert runtime.calls == [("pull", RUNTIME, SEARXNG_IMAGE)]
    record = provisioner.record()
    assert record is not None
    assert (record.image, record.port, record.label, record.runtime) == (
        SEARXNG_IMAGE,
        28180,
        "dev.vibey.searxng",
        RUNTIME,
    )
    assert provisioner.provisioned() and provisioner.offer().provisioned


def test_a_failed_pull_writes_nothing(tmp_path: Path) -> None:
    runtime = Runtime(pulled=RuntimeOutcome(ok=False, detail="denied", still_running=True))
    provisioner = _provisioner(tmp_path, runtime)

    prepared = provisioner.prepare()

    assert not prepared.ok and prepared.still_running and "denied" in prepared.detail
    assert provisioner.record() is None and not (tmp_path / "searxng").exists()


def test_no_runtime_pulls_nothing(tmp_path: Path) -> None:
    runtime = Runtime(found=None)
    prepared = _provisioner(tmp_path, runtime).prepare()
    assert not prepared.ok and "podman" in prepared.detail and runtime.calls == []


def test_files_that_cannot_be_written_fail_the_prepare(tmp_path: Path) -> None:
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "searxng").symlink_to(tmp_path / "elsewhere")
    prepared = _provisioner(tmp_path).prepare()
    assert not prepared.ok and "could not be written" in prepared.detail


def test_answering_checks_vibeys_own_port_and_marker(tmp_path: Path) -> None:
    health = Health()
    provisioner = _provisioner(tmp_path, health=health)
    assert not provisioner.answering()  # nothing installed: nothing asked
    assert health.asked == []
    provisioner.prepare()
    record = provisioner.record()
    assert record is not None
    assert not provisioner.answering()
    health.answering.add(("http://127.0.0.1:28180", record.marker))
    assert provisioner.answering()
    found = provisioner.offer()
    assert found.answering and found.provisioned


def test_remove_container_uses_the_recorded_runtime(tmp_path: Path) -> None:
    runtime = Runtime()
    provisioner = _provisioner(tmp_path, runtime)
    assert provisioner.remove_container() == ""
    assert runtime.calls == [("rm", RUNTIME)]
    runtime.removed = RuntimeOutcome(ok=False, detail="daemon down")
    assert provisioner.remove_container() == "daemon down"
    assert _provisioner(tmp_path, Runtime(found=None)).remove_container() == ""


def test_purge_removes_the_image_and_the_files(tmp_path: Path) -> None:
    runtime = Runtime()
    provisioner = _provisioner(tmp_path, runtime)
    provisioner.prepare()
    assert provisioner.image_present()
    runtime.removed = RuntimeOutcome(ok=False, detail="image in use")

    assert provisioner.purge() == ["the image was kept: image in use"]
    assert ("rmi", RUNTIME, SEARXNG_IMAGE) in runtime.calls
    assert provisioner.record() is None and not provisioner.image_present()
    assert provisioner.purge() == []


def test_a_record_vibey_did_not_write_is_not_provisioned(tmp_path: Path) -> None:
    (tmp_path / "searxng").mkdir()
    (tmp_path / "searxng" / "provision.json").write_text("{}", "utf-8")
    assert not _provisioner(tmp_path).provisioned()


def test_the_default_identity_check_is_9cs_with_the_marker(tmp_path: Path) -> None:
    provisioner = SearxngProvisioner(
        Runtime(), SearxngFiles(tmp_path / "searxng"), label=lambda: "dev.vibey.searxng"
    )
    provisioner.prepare()
    # The suite refuses every connection the guarded opener makes: nothing answers.
    assert not provisioner.answering()


def test_purge_with_the_image_removed_keeps_nothing(tmp_path: Path) -> None:
    provisioner = _provisioner(tmp_path)
    provisioner.prepare()
    assert provisioner.purge() == [] and provisioner.record() is None
