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
from vibey.infrastructure.searxng.container_runtime import (
    ContainerRuntime,
    RuntimeOutcome,
    RuntimeProblem,
    RuntimeRefusal,
)
from vibey.infrastructure.searxng.searxng_files import SearxngFiles
from vibey.infrastructure.searxng.searxng_provisioner import SearxngProvisioner

RUNTIME = "/opt/homebrew/bin/podman"
_REAL_CONNECTS = SearxngProvisioner.__dict__["_connects"]
"""Read at import, before the suite's guard stands in for it."""


class Runtime:
    def __init__(
        self, found: str | None = RUNTIME, *, pulled: RuntimeOutcome | None = None
    ) -> None:
        self.found = found
        self.pulled = pulled or RuntimeOutcome(ok=True)
        self.calls: list[tuple[str, ...]] = []
        self.removed = RuntimeOutcome(ok=True)
        self.present = True
        self.refuse: RuntimeProblem | None = None
        self.shown: str | None = None
        """The name the refusal gives the runtime, when not the one asked about."""
        self.where: str | None = ""
        """What `endpoint` says: docker's context endpoint, "" for podman, None unreadable."""
        self.image_removed = RuntimeOutcome(ok=True)

    is_local = staticmethod(ContainerRuntime.is_local)

    def endpoint(self, runtime: str) -> str | None:
        self.calls.append(("context", runtime))
        return self.where

    def find(self) -> str | None:
        return self.found

    def vet(self, runtime: str) -> RuntimeRefusal | None:
        if self.refuse is None:
            return None
        return RuntimeRefusal(self.shown or runtime, self.refuse)

    def _checked(self, runtime: str) -> None:
        refusal = self.vet(runtime)
        if refusal is not None:
            raise ValueError(str(refusal))

    def image_present(self, runtime: str, image: str) -> bool:
        self._checked(runtime)
        self.calls.append(("inspect", runtime, image))
        return self.present

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        self._checked(runtime)
        self.calls.append(("pull", runtime, image))
        return self.pulled

    def remove_container(self, runtime: str, uid: int) -> RuntimeOutcome:
        self._checked(runtime)
        self.calls.append(("rm", runtime, str(uid)))
        return self.removed

    def remove_image(self, runtime: str, image: str) -> RuntimeOutcome:
        self._checked(runtime)
        self.calls.append(("rmi", runtime, image))
        return self.removed if not self.removed.ok else self.image_removed


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
    listening: bool = False,
    label: str = "dev.vibey.searxng",
) -> SearxngProvisioner:
    return SearxngProvisioner(
        runtime or Runtime(),
        SearxngFiles(tmp_path / "searxng"),
        label=lambda: label,
        environ=environ or {},
        health=health or Health(),
        listening=lambda port: listening,
        uid=lambda: 501,
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
    assert runtime.calls == [("context", RUNTIME), ("pull", RUNTIME, SEARXNG_IMAGE)]
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
    assert runtime.calls == [("rm", RUNTIME, "501")]
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


# -- fix round 1 ----------------------------------------------------------------------------------


def test_a_record_naming_another_label_is_not_believed(tmp_path: Path) -> None:
    _provisioner(tmp_path, label="dev.vibey.hub").prepare()
    provisioner = _provisioner(tmp_path)
    assert provisioner.record() is None and not provisioner.provisioned()
    assert "label dev.vibey.hub" in provisioner.refusal()


def test_the_refusal_names_a_runtime_vibey_will_not_run(tmp_path: Path) -> None:
    runtime = Runtime()
    provisioner = _provisioner(tmp_path, runtime)
    assert provisioner.refusal() == ""  # nothing installed
    provisioner.prepare()
    assert provisioner.refusal() == ""
    runtime.refuse, runtime.shown = RuntimeProblem.SHARED_WRITE, f"{RUNTIME}\x1b[2J"
    assert provisioner.refusal().startswith(f"{RUNTIME} is writable by anyone but its owner; ")
    assert "`vibey searxng uninstall --purge` and `vibey searxng install`" in (
        provisioner.refusal()
    )
    assert not provisioner.image_present()
    assert "writable" in provisioner.remove_container()
    assert provisioner.purge() == [f"the image was kept: {runtime.vet(RUNTIME)}"]
    assert ("rm", RUNTIME, "501") not in runtime.calls


def test_a_refused_runtime_pulls_nothing(tmp_path: Path) -> None:
    runtime = Runtime()
    runtime.refuse = RuntimeProblem.GONE
    prepared = _provisioner(tmp_path, runtime).prepare()
    assert not prepared.ok and prepared.detail == f"{RUNTIME} is not there"


@pytest.mark.parametrize("name", ["DOCKER_HOST", "CONTAINER_HOST"])
@pytest.mark.parametrize("value", ["ssh://user@elsewhere", "tcp://10.0.0.5:2376"])
def test_a_remote_daemon_installs_nothing(tmp_path: Path, name: str, value: str) -> None:
    runtime = Runtime()
    prepared = _provisioner(tmp_path, runtime, environ={name: value}).prepare()
    assert not prepared.ok and f"unset {name}" in prepared.detail and runtime.calls == []


def test_a_local_daemon_setting_is_said_to_be_ignored(tmp_path: Path) -> None:
    environ = {"DOCKER_HOST": "unix:///Users/x/.colima/docker.sock", "DOCKER_CONTEXT": "colima"}
    prepared = _provisioner(tmp_path, environ=environ).prepare()
    assert prepared.ok and "DOCKER_HOST, DOCKER_CONTEXT are ignored" in prepared.detail
    one = _provisioner(tmp_path, environ={"DOCKER_CONFIG": "/x"}).prepare()
    assert "DOCKER_CONFIG is ignored" in one.detail


def test_a_free_port_is_not_busy(tmp_path: Path) -> None:
    health = Health()
    assert _provisioner(tmp_path, health=health).busy() == ""
    assert health.asked == []  # nothing listens: nothing asked


def test_a_plain_listener_or_another_searxng_makes_the_port_busy(tmp_path: Path) -> None:
    said = _provisioner(tmp_path, listening=True).busy()
    assert "already listens on 127.0.0.1:28180" in said and "VIBEY_SEARXNG_URL" in said
    stranger = Health(answering={("http://127.0.0.1:28180", None)})
    assert "not vibey's" in _provisioner(tmp_path, listening=True, health=stranger).busy()


def test_vibeys_own_searxng_on_the_port_is_not_busy(tmp_path: Path) -> None:
    health = Health()
    provisioner = _provisioner(tmp_path, listening=True, health=health)
    provisioner.prepare()
    record = provisioner.record()
    assert record is not None
    health.answering.add(("http://127.0.0.1:28180", record.marker))
    assert provisioner.busy() == ""


def test_prepare_takes_away_a_stop_and_disable_puts_it_back(tmp_path: Path) -> None:
    provisioner = _provisioner(tmp_path)
    provisioner.disable()
    assert provisioner.disabled() and provisioner.offer().disabled
    provisioner.prepare()
    assert not provisioner.disabled()


def test_the_default_listening_probe_connects_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    monkeypatch.setattr(SearxngProvisioner, "_connects", _REAL_CONNECTS)
    asked: list[tuple[str, int]] = []

    class Conn:
        def __enter__(self) -> Conn:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def connect(address: tuple[str, int], timeout: float) -> Conn:
        asked.append(address)
        if address[1] == 1:
            raise ConnectionRefusedError
        return Conn()

    monkeypatch.setattr(socket, "create_connection", connect)
    assert SearxngProvisioner._connects(28180) and not SearxngProvisioner._connects(1)
    assert asked == [("127.0.0.1", 28180), ("127.0.0.1", 1)]


# -- fix round 2: an install from an earlier pin (review 2, R1) -----------------------------------

EARLIER = "docker.io/searxng/searxng@sha256:" + "ab" * 32


def _installed_earlier(tmp_path: Path) -> str:
    """What an earlier vibey, pinning `EARLIER`, wrote; its marker."""
    from vibey.domain.searxng import SearxngPlan

    earlier = SearxngFiles(tmp_path / "searxng", plan=SearxngPlan(pinned=EARLIER))
    return earlier.ensure(
        image=EARLIER, port=28180, label="dev.vibey.searxng", runtime=RUNTIME
    ).marker


def test_vibeys_own_searxng_from_an_earlier_pin_is_never_busy(tmp_path: Path) -> None:
    marker = _installed_earlier(tmp_path)
    health = Health(answering={("http://127.0.0.1:28180", marker)})
    provisioner = _provisioner(tmp_path, listening=True, health=health)

    assert provisioner.record() is None  # never run: it is not the pinned image
    assert provisioner.installed() is not None
    assert provisioner.busy() == ""
    found = provisioner.offer()
    assert found.answering and found.provisioned
    assert found.outdated == f"{'ab' * 6} -> {SEARXNG_IMAGE.rpartition(':')[2][:12]}"
    assert "a newer pinned image is available" in provisioner.refusal()
    assert provisioner.answering()


def test_an_update_keeps_the_marker_and_writes_the_pinned_image(tmp_path: Path) -> None:
    marker = _installed_earlier(tmp_path)
    provisioner = _provisioner(tmp_path)
    assert provisioner.prepare().ok
    record = provisioner.record()
    assert record is not None and record.image == SEARXNG_IMAGE and record.marker == marker
    assert provisioner.offer().outdated == "" and provisioner.refusal() == ""


def test_the_settings_marker_names_vibeys_instance_when_the_record_is_unreadable(
    tmp_path: Path,
) -> None:
    marker = _installed_earlier(tmp_path)
    (tmp_path / "searxng" / "provision.json").write_text("not json", "utf-8")
    health = Health(answering={("http://127.0.0.1:28180", marker)})
    assert _provisioner(tmp_path, listening=True, health=health).busy() == ""


def test_the_earlier_pins_record_alone_names_vibeys_instance(tmp_path: Path) -> None:
    import os

    marker = _installed_earlier(tmp_path)
    os.chmod(tmp_path / "searxng" / "settings.yml", 0o644)  # settings vibey cannot believe
    health = Health(answering={("http://127.0.0.1:28180", marker)})
    assert _provisioner(tmp_path, listening=True, health=health).busy() == ""


# -- Task 11a: the recorded runtime is the one an update, a removal and a purge use ----------------

DOCKER = "/usr/local/bin/docker"


class RecordedGone(Runtime):
    """The runtime vibey recorded no longer passes its checks; the one found now does."""

    def vet(self, runtime: str) -> RuntimeRefusal | None:
        return RuntimeRefusal(runtime, RuntimeProblem.GONE) if runtime == RUNTIME else None

    def _checked(self, runtime: str) -> None:
        refusal = self.vet(runtime)
        if refusal is not None:
            raise ValueError(str(refusal))


def test_an_update_pulls_with_the_recorded_runtime_not_the_one_found_now(tmp_path: Path) -> None:
    """9d N-h: podman recorded, docker found first now: the update stays with podman."""
    _installed_earlier(tmp_path)
    runtime = Runtime(found=DOCKER)
    provisioner = _provisioner(tmp_path, runtime)
    assert provisioner.offer().runtime == RUNTIME
    assert provisioner.prepare().ok
    assert runtime.calls == [
        ("context", RUNTIME),
        ("pull", RUNTIME, SEARXNG_IMAGE),
        ("rm", RUNTIME, "501"),
        ("rmi", RUNTIME, EARLIER),
    ]
    record = provisioner.record()
    assert record is not None and record.runtime == RUNTIME


def test_an_update_whose_recorded_runtime_vanished_pulls_nothing_and_says_how_to_fix(
    tmp_path: Path,
) -> None:
    _installed_earlier(tmp_path)
    runtime = RecordedGone(found=DOCKER)
    provisioner = _provisioner(tmp_path, runtime)
    prepared = provisioner.prepare()
    assert not prepared.ok and prepared.detail.startswith(f"{RUNTIME} is not there; ")
    assert "`vibey searxng uninstall --purge`" in prepared.detail
    assert runtime.calls == []
    assert provisioner.record() is None  # nothing was rewritten to the other runtime


def test_removal_and_purge_of_an_outdated_install_use_its_recorded_runtime(
    tmp_path: Path,
) -> None:
    """9d N-i: the container and image of an earlier pin live where it was installed."""
    _installed_earlier(tmp_path)
    runtime = Runtime(found=DOCKER)
    provisioner = _provisioner(tmp_path, runtime)
    assert provisioner.remove_container() == ""
    assert provisioner.purge() == []
    assert runtime.calls == [("rm", RUNTIME, "501"), ("rmi", RUNTIME, EARLIER)]


def test_doctor_says_how_to_fix_a_recorded_runtime_that_is_gone(tmp_path: Path) -> None:
    """9d N-j: the refusal doctor shows names the remedy."""
    runtime = Runtime()
    provisioner = _provisioner(tmp_path, runtime)
    provisioner.prepare()
    runtime.refuse = RuntimeProblem.GONE
    assert provisioner.refusal() == (
        f"{RUNTIME} is not there; vibey keeps its SearXNG with the runtime it was installed with: "
        "put that runtime back, or run `vibey searxng uninstall --purge` and then "
        "`vibey searxng install` to use the one vibey finds now"
    )


def test_the_remedy_follows_the_cause_and_gone_is_told_apart(tmp_path: Path) -> None:
    """Review 1 S-3: a runtime that is gone can be put back or replaced; one that is there but
    refused may still run the old container, so that is said first."""
    from vibey.infrastructure.searxng.searxng_provisioner import (
        RUNTIME_GONE_REMEDY,
        RUNTIME_REFUSED_REMEDY,
    )

    runtime = Runtime()
    provisioner = _provisioner(tmp_path, runtime)
    assert not provisioner.runtime_gone()  # nothing installed
    provisioner.prepare()
    assert not provisioner.runtime_gone()
    runtime.refuse = RuntimeProblem.GONE
    assert provisioner.refusal().endswith(RUNTIME_GONE_REMEDY)
    assert provisioner.runtime_gone()
    runtime.refuse = RuntimeProblem.SHARED_WRITE
    assert provisioner.refusal().endswith(RUNTIME_REFUSED_REMEDY)
    assert "chmod g-w,o-w" in provisioner.refusal()
    assert not provisioner.runtime_gone()
    prepared = provisioner.prepare()
    assert not prepared.ok and prepared.detail.endswith(RUNTIME_REFUSED_REMEDY)


def test_gone_is_told_apart_by_the_reason_never_by_the_wording(tmp_path: Path) -> None:
    """Review 2 N2-5: the remedy and `runtime_gone` follow `vet`'s typed reason. A refusal whose
    text happens to end as a gone one's does (a runtime named so), but whose reason is another,
    is never taken for gone."""
    from vibey.infrastructure.searxng.searxng_provisioner import RUNTIME_REFUSED_REMEDY

    runtime = Runtime()
    provisioner = _provisioner(tmp_path, runtime)
    provisioner.prepare()

    class Worded(RuntimeRefusal):
        def __str__(self) -> str:
            return f"{self.runtime} is not there"

    runtime.vet = lambda path: Worded(path, RuntimeProblem.FOREIGN_OWNER)  # type: ignore[method-assign]
    assert not provisioner.runtime_gone()
    assert provisioner.refusal().endswith(RUNTIME_REFUSED_REMEDY)


# -- SP-ACP Task 11b-ii: the earlier pin's image, and docker's context --------------------------


def test_an_update_removes_the_earlier_pins_container_then_its_image(tmp_path: Path) -> None:
    """P-9d-6: once the new image is pulled and recorded, the old container (which holds the
    old image) is removed -- the unit starts the new one -- and then the old image."""
    _installed_earlier(tmp_path)
    runtime = Runtime()
    prepared = _provisioner(tmp_path, runtime).prepare()
    assert prepared.ok
    assert runtime.calls[-2:] == [("rm", RUNTIME, "501"), ("rmi", RUNTIME, EARLIER)]
    assert f"The earlier image (sha256:{'ab' * 6}) was removed." in prepared.detail


def test_an_earlier_image_that_cannot_be_removed_is_said_and_the_update_stands(
    tmp_path: Path,
) -> None:
    _installed_earlier(tmp_path)
    runtime = Runtime()
    runtime.image_removed = RuntimeOutcome(ok=False, detail="image is in use")
    prepared = _provisioner(tmp_path, runtime).prepare()
    assert prepared.ok
    assert f"The earlier image (sha256:{'ab' * 6}) was kept (image is in use);" in prepared.detail
    assert f"`podman rmi {EARLIER}` removes it" in prepared.detail


def test_a_fresh_install_removes_nothing(tmp_path: Path) -> None:
    runtime = Runtime()
    assert _provisioner(tmp_path, runtime).prepare().ok
    assert [call[0] for call in runtime.calls] == ["context", "pull"]


@pytest.mark.parametrize("where", ["ssh://me@far.example", "tcp://10.0.0.2:2376"])
def test_a_docker_context_on_another_machine_installs_nothing(tmp_path: Path, where: str) -> None:
    """P-9d-8: the Docker CLI's current context points at another machine."""
    runtime = Runtime(found=DOCKER)
    runtime.where = where
    prepared = _provisioner(tmp_path, runtime).prepare()
    assert not prepared.ok
    assert prepared.detail == (
        f"docker's current context points at {where}, a daemon that is not a local socket; "
        "vibey runs SearXNG only on this computer's own runtime, so `docker context use "
        "default` (or another local context) to install it"
    )
    assert [call[0] for call in runtime.calls] == ["context"]


def test_a_docker_context_that_cannot_be_read_installs_nothing(tmp_path: Path) -> None:
    """Review 1 I-3: fail closed: a context vibey cannot read is never taken as local."""
    runtime = Runtime(found=DOCKER)
    runtime.where = None
    prepared = _provisioner(tmp_path, runtime).prepare()
    assert not prepared.ok and "could not be read" in prepared.detail
    assert [call[0] for call in runtime.calls] == ["context"]


@pytest.mark.parametrize("where", ["unix:///var/run/docker.sock", "npipe:////./pipe/docker", ""])
def test_a_local_docker_context_installs(tmp_path: Path, where: str) -> None:
    runtime = Runtime(found=DOCKER)
    runtime.where = where
    assert _provisioner(tmp_path, runtime).prepare().ok


def test_an_earlier_image_already_gone_is_never_said_to_be_removed(tmp_path: Path) -> None:
    """Review 1 I-4: `rmi` of an image that is not there counts as removed for an uninstall,
    but an update says what happened: it was not there."""
    _installed_earlier(tmp_path)
    runtime = Runtime()
    runtime.image_removed = RuntimeOutcome(ok=True, detail="nothing to remove")
    prepared = _provisioner(tmp_path, runtime).prepare()
    assert prepared.ok and "was removed" not in prepared.detail
    assert f"The earlier image (sha256:{'ab' * 6}) was not in podman any more." in prepared.detail
    assert runtime.calls[-1] == ("rmi", RUNTIME, EARLIER)  # with the runtime that pulled it
