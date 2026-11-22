# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SearXNG vibey provisions, its pure half (ADR-0102): the pinned image, the provision
record, the settings it writes and the exact container command line."""

from __future__ import annotations

import re

import pytest

from vibey.domain.interfaces.searxng_interface import SearxngPlanInterface
from vibey.domain.searxng import (
    IMAGE_REF,
    MARKER,
    SEARXNG_IMAGE,
    SearxngPlan,
    SearxngProvision,
)
from vibey.domain.supervisor import SupervisorPaths, SupervisorPlanner, SupervisorSettings

PLAN = SearxngPlan()
DIGEST = "sha256:" + "ab" * 32
IMAGE = SEARXNG_IMAGE
OTHER = f"docker.io/searxng/searxng@{DIGEST}"
SHORT = SEARXNG_IMAGE.rpartition(":")[2][:12]
MARK = "vibey-" + "0f" * 16
SECRET = "5e" * 32
PROVISION = SearxngProvision(
    image=IMAGE, port=28180, marker=MARK, label="dev.vibey.searxng", runtime="/usr/bin/podman"
)
SETTINGS = "/home/op/.config/vibey/searxng/settings.yml"


def test_the_plan_is_its_interface() -> None:
    assert isinstance(PLAN, SearxngPlanInterface)


def test_the_pinned_image_is_searxng_by_digest_and_never_a_tag() -> None:
    assert IMAGE_REF.fullmatch(SEARXNG_IMAGE)
    assert re.fullmatch(r"docker\.io/searxng/searxng@sha256:[0-9a-f]{64}", SEARXNG_IMAGE)


@pytest.mark.parametrize(
    "image",
    [
        OTHER,
        "docker.io/searxng/searxng:latest",
        "searxng/searxng@" + DIGEST,
        "docker.io/searxng/searxng@sha256:" + "AB" * 32,
        "docker.io/searxng/searxng@sha256:" + "ab" * 31,
        "docker.io/evil/searxng@" + DIGEST,
        "ghcr.io/searxng/searxng@" + DIGEST,
        IMAGE + "\n",
        IMAGE + " --privileged",
        "--privileged",
    ],
)
def test_only_a_searxng_digest_reference_is_an_image(image: str) -> None:
    with pytest.raises(ValueError, match="image"):
        PLAN.check(SearxngProvision(image, 28180, MARK, "dev.vibey.searxng", "/usr/bin/podman"))


def test_the_record_round_trips() -> None:
    data = PLAN.record(PROVISION)
    assert data == {
        "image": IMAGE,
        "port": 28180,
        "marker": MARK,
        "label": "dev.vibey.searxng",
        "runtime": "/usr/bin/podman",
    }
    assert PLAN.parse(data) == PROVISION


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        {},
        {**PLAN.record(PROVISION), "port": "28180"},
        {**PLAN.record(PROVISION), "port": True},
        {**PLAN.record(PROVISION), "port": 0},
        {**PLAN.record(PROVISION), "port": 65536},
        {**PLAN.record(PROVISION), "marker": "vibey-xyz"},
        {**PLAN.record(PROVISION), "marker": MARK + "\nx: 1"},
        {**PLAN.record(PROVISION), "label": "a;b $(id)"},
        {**PLAN.record(PROVISION), "runtime": "podman"},
        {**PLAN.record(PROVISION), "runtime": "/bin/sh"},
        {**PLAN.record(PROVISION), "runtime": "/tmp/x/podman\n"},
        {**PLAN.record(PROVISION), "runtime": "/Users/x/project/bin/docker"},
        {**PLAN.record(PROVISION), "runtime": "/usr/bin/../../tmp/docker"},
        {**PLAN.record(PROVISION), "image": OTHER},
        {**PLAN.record(PROVISION), "image": "docker.io/searxng/searxng:latest"},
    ],
)
def test_a_record_that_is_not_one_vibey_wrote_is_refused(data: object) -> None:
    with pytest.raises(ValueError):
        PLAN.parse(data)


def test_the_settings_are_loopback_private_and_answer_json() -> None:
    text = PLAN.settings_text(secret_key=SECRET, marker=MARK)
    lines = text.splitlines()
    assert "use_default_settings: true" in lines
    assert f'  secret_key: "{SECRET}"' in lines
    assert f'  instance_name: "{MARK}"' in lines
    assert "  limiter: false" in lines
    assert "  public_instance: false" in lines
    assert '  bind_address: "0.0.0.0"' in lines
    assert "  port: 8080" in lines
    assert "  donation_url: false" in lines
    assert "  contact_url: false" in lines
    assert "  enable_metrics: false" in lines
    assert lines[lines.index("  formats:") + 1 :][:2] == ["    - html", "    - json"]


@pytest.mark.parametrize(
    ("secret", "marker"),
    [
        ("short", MARK),
        (SECRET + '"\nserver: {}', MARK),
        (SECRET, 'vibey-x"\nui: {}'),
        (SECRET, "someone-else"),
    ],
)
def test_the_settings_refuse_a_value_that_could_change_their_shape(
    secret: str, marker: str
) -> None:
    with pytest.raises(ValueError):
        PLAN.settings_text(secret_key=secret, marker=marker)


def test_a_marker_and_a_secret_come_from_random_hex() -> None:
    assert MARKER.fullmatch(PLAN.new_marker("0f" * 16))
    with pytest.raises(ValueError):
        PLAN.new_marker("not hex")


GOLDEN_PODMAN = (
    "/usr/bin/podman",
    "run",
    "--rm",
    "--name",
    "vibey-searxng-501",
    "--label",
    "vibey.searxng.owner=501",
    "--label",
    f"vibey.searxng.image={SHORT}",
    "--pull=never",
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--pids-limit",
    "256",
    "--memory",
    "512m",
    "--userns=keep-id",
    "--user",
    "501:20",
    "--publish",
    "127.0.0.1:28180:8080",
    "--volume",
    f"{SETTINGS}:/etc/searxng/settings.yml:ro",
    "--tmpfs",
    "/etc/searxng",
    "--tmpfs",
    "/var/cache/searxng",
    "--tmpfs",
    "/tmp",
    IMAGE,
)


def test_the_container_command_line_is_this_and_nothing_more() -> None:
    argv = PLAN.run_argv(PROVISION, settings_path=SETTINGS, uid=501, gid=20)
    assert argv == GOLDEN_PODMAN


def test_docker_gets_the_same_flags_without_podmans_user_namespace() -> None:
    docker = SearxngProvision(IMAGE, 28180, MARK, "dev.vibey.searxng", "/usr/local/bin/docker")
    argv = PLAN.run_argv(docker, settings_path=SETTINGS, uid=1000, gid=1000)
    expected = tuple(
        "/usr/local/bin/docker" if part == "/usr/bin/podman" else part
        for part in GOLDEN_PODMAN
        if part != "--userns=keep-id"
    )
    swapped = {
        "501:20": "1000:1000",
        "vibey-searxng-501": "vibey-searxng-1000",
        "vibey.searxng.owner=501": "vibey.searxng.owner=1000",
    }
    assert argv == tuple(swapped.get(part, part) for part in expected)


def test_the_container_never_gets_the_host_or_its_secrets() -> None:
    argv = PLAN.run_argv(PROVISION, settings_path=SETTINGS, uid=501, gid=20)
    joined = " ".join(argv)
    for banned in ("--privileged", "--network", "host", "--env", "-e", "--env-file"):
        assert banned not in argv
    assert "--privileged" not in joined and "docker.sock" not in joined
    published = argv[argv.index("--publish") + 1]
    assert published.startswith("127.0.0.1:")
    volumes = [argv[i + 1] for i, part in enumerate(argv) if part == "--volume"]
    assert volumes == [f"{SETTINGS}:/etc/searxng/settings.yml:ro"]


@pytest.mark.parametrize(
    "path",
    ["relative/settings.yml", "/home/a:b/settings.yml", "/home/a,b/settings.yml", "/x/\nsettings"],
)
def test_a_settings_path_the_mount_syntax_could_misread_is_refused(path: str) -> None:
    with pytest.raises(ValueError, match="settings"):
        PLAN.run_argv(PROVISION, settings_path=path, uid=501, gid=20)


@pytest.mark.parametrize(("uid", "gid"), [(0, 20), (501, -1), (True, 20)])
def test_the_container_never_runs_as_root_or_an_odd_user(uid: int, gid: int) -> None:
    with pytest.raises(ValueError, match="user"):
        PLAN.run_argv(PROVISION, settings_path=SETTINGS, uid=uid, gid=gid)


def test_the_runtime_commands_are_fixed() -> None:
    assert PLAN.pull_argv(PROVISION.runtime, IMAGE) == ("/usr/bin/podman", "pull", IMAGE)
    assert PLAN.image_argv(PROVISION.runtime, IMAGE) == (
        "/usr/bin/podman",
        "image",
        "inspect",
        "--format",
        "{{.Id}}",
        IMAGE,
    )
    assert PLAN.remove_argv(PROVISION.runtime, 501) == (
        "/usr/bin/podman",
        "rm",
        "-f",
        "vibey-searxng-501",
    )
    assert PLAN.labels_argv(PROVISION.runtime, 501) == (
        "/usr/bin/podman",
        "container",
        "inspect",
        "--format",
        "{{json .Config.Labels}}",
        "vibey-searxng-501",
    )
    with pytest.raises(ValueError, match="never root"):
        PLAN.remove_argv(PROVISION.runtime, 0)
    assert PLAN.remove_image_argv(PROVISION.runtime, IMAGE) == ("/usr/bin/podman", "rmi", IMAGE)
    with pytest.raises(ValueError):
        PLAN.pull_argv("/bin/sh", IMAGE)
    with pytest.raises(ValueError):
        PLAN.pull_argv(PROVISION.runtime, "docker.io/searxng/searxng:latest")


def test_the_short_digest_is_its_first_twelve_hex() -> None:
    assert PLAN.short(IMAGE) == SHORT and len(SHORT) == 12


def test_only_the_pinned_image_is_accepted_and_a_plan_can_pin_another() -> None:
    other = SearxngPlan(pinned=OTHER)
    assert other.short(OTHER) == "ab" * 6
    with pytest.raises(ValueError, match="pins"):
        PLAN.short(OTHER)
    with pytest.raises(ValueError, match="pinned image"):
        SearxngPlan(pinned="docker.io/searxng/searxng:latest")
    with pytest.raises(ValueError, match="prefix"):
        SearxngPlan(prefix="a b")
    assert SearxngPlan(prefix="vibey-searxng-test").container_name(7) == "vibey-searxng-test-7"


def test_the_marker_is_read_back_from_settings_vibey_wrote() -> None:
    text = PLAN.settings_text(secret_key=SECRET, marker=MARK)
    assert PLAN.marker_in(text) == MARK
    assert PLAN.marker_in(text.replace(MARK, "someone")) is None
    assert PLAN.marker_in("") is None


# --- the unit `vibey acp` loads for it (ADR-0101's planner) ---------------------------------

PATHS = SupervisorPaths(
    vibey="/opt/vibey/bin/vibey",
    python="/opt/vibey/bin/python",
    repo="/home/op/.config/vibey",
    env_file="/home/op/.config/vibey/supervisor.env",
    log_dir="/home/op/.local/state/vibey/logs",
)


def test_the_searxng_unit_runs_the_pinned_launcher_and_no_environment_file() -> None:
    (unit,) = SupervisorPlanner().acp_services(
        SupervisorSettings(), PATHS, names=("searxng",), restart="always"
    )
    assert (unit.name, unit.label, unit.restart) == ("searxng", "dev.vibey.searxng", "always")
    # Never through `supervisor exec --env-file`: that file holds the database URL, and the
    # container gets no secret but its own.
    assert unit.argv == ("/opt/vibey/bin/vibey", "searxng", "serve")
    assert unit.log_path == "/home/op/.local/state/vibey/logs/searxng.log"


def test_a_record_of_an_earlier_pin_parses_installed_but_never_runs() -> None:
    """Review 2 (R1): read to recognise and update it, refused for anything that runs it."""
    earlier = SearxngProvision(OTHER, 28180, MARK, "dev.vibey.searxng", "/usr/bin/podman")
    data = SearxngPlan(pinned=OTHER).record(earlier)
    assert PLAN.parse_installed(data) == earlier
    with pytest.raises(ValueError, match="pins"):
        PLAN.parse(data)
    with pytest.raises(ValueError, match="pins"):
        PLAN.run_argv(earlier, settings_path=SETTINGS, uid=501, gid=20)
    assert not PLAN.pinned(OTHER) and PLAN.pinned(IMAGE)
    assert PLAN.digest_of(OTHER) == "ab" * 6
    with pytest.raises(ValueError, match="digest"):
        PLAN.digest_of("docker.io/searxng/searxng:latest")
    with pytest.raises(ValueError, match="digest"):
        PLAN.parse_installed({**data, "image": "docker.io/evil/searxng@sha256:" + "ab" * 32})
