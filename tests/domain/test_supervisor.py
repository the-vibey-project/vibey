# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared supervisor's pure half (#1189): the services, and the environment file."""

import pytest

from vibey.domain.interfaces.supervisor_interface import (
    EnvFileParserInterface,
    SupervisorPlannerInterface,
)
from vibey.domain.supervisor import (
    EnvFileParser,
    SupervisorPaths,
    SupervisorPlanner,
    SupervisorSettings,
)

PATHS = SupervisorPaths(
    vibey="/opt/vibey/bin/vibey",
    python="/opt/vibey/bin/python",
    repo="/srv/git/vibey",
    env_file="/home/op/.config/vibey/supervisor.env",
    log_dir="/home/op/.local/state/vibey/logs",
)
LAUNCH = ("/opt/vibey/bin/vibey", "supervisor", "exec", "--env-file", PATHS.env_file, "--")


def test_the_classes_are_their_interfaces() -> None:
    assert isinstance(SupervisorPlanner(), SupervisorPlannerInterface)
    assert isinstance(EnvFileParser(), EnvFileParserInterface)


def test_the_default_plan_supervises_the_worker_and_the_delivery_bridge() -> None:
    worker, delivery = SupervisorPlanner().services(SupervisorSettings(), PATHS)

    assert worker.name == "worker"
    assert worker.label == "dev.vibey.worker"
    assert worker.argv == (*LAUNCH, "/opt/vibey/bin/vibey", "worker", "--all-projects")
    assert worker.working_directory == "/srv/git/vibey"
    assert worker.log_path == "/home/op/.local/state/vibey/logs/worker.log"

    assert delivery.label == "dev.vibey.delivery"
    assert delivery.argv == (
        *LAUNCH,
        "/opt/vibey/bin/python",
        "/srv/git/vibey/scripts/triaged_delivery.py",
        "--repo",
        "/srv/git/vibey",
        "--interval",
        "300",
    )
    assert delivery.log_path.endswith("/delivery.log")


def test_every_choice_is_a_key() -> None:
    settings = SupervisorSettings(
        label_prefix="org.example.vibey",
        delivery_interval_seconds=60,
        worker_args=("-j", "2", "--provider", "gptossloop"),
        delivery_args=("--answer-design-defaults",),
    )
    worker, delivery = SupervisorPlanner().services(settings, PATHS)
    assert worker.label == "org.example.vibey.worker"
    assert worker.argv[-4:] == ("-j", "2", "--provider", "gptossloop")
    assert delivery.argv[-3:] == ("--interval", "60", "--answer-design-defaults")


def test_the_bridge_can_be_left_unsupervised() -> None:
    (worker,) = SupervisorPlanner().services(SupervisorSettings(delivery=False), PATHS)
    assert worker.name == "worker"


def test_an_interval_no_loop_could_keep_is_refused() -> None:
    with pytest.raises(ValueError, match="delivery_interval_seconds"):
        SupervisorPlanner().services(SupervisorSettings(delivery_interval_seconds=0), PATHS)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/var/scratch", "/var/scratch"),
        ("/var/scratch/logs/vibey", "/var/scratch"),
        ("/var/scratchpad/logs", ""),
        ("/home/op/logs", ""),
    ],
)
def test_under_names_the_root_a_path_lies_in(path: str, expected: str) -> None:
    assert SupervisorPlanner().under(path, ("/nowhere", "/var/scratch/")) == expected


def test_the_env_file_reads_the_common_dialect() -> None:
    text = """
# the database
VIBEY_PG_URL=postgresql://vibey@localhost/vibey
export GH_TOKEN = 'example-token'
QUOTED="a value with spaces"
EMPTY=
UNPAIRED='left
SPACED = kept as written
VIBEY_PG_URL=postgresql://vibey@localhost/other
"""
    assert EnvFileParser().parse(text) == {
        "VIBEY_PG_URL": "postgresql://vibey@localhost/other",
        "GH_TOKEN": "example-token",
        "QUOTED": "a value with spaces",
        "EMPTY": "",
        "UNPAIRED": "'left",
        "SPACED": "kept as written",
    }


def test_nothing_in_the_env_file_is_expanded() -> None:
    assert EnvFileParser().parse("PATH=$HOME/bin:$PATH") == {"PATH": "$HOME/bin:$PATH"}


@pytest.mark.parametrize("line", ["NO_EQUALS_SIGN", "API KEY=hunter2", "1ST=x", "=x"])
def test_a_line_that_is_not_a_pair_is_refused_by_number_never_by_content(line: str) -> None:
    with pytest.raises(ValueError, match="line 2") as refused:
        EnvFileParser().parse(f"OK=1\n{line}\n")
    assert "hunter2" not in str(refused.value)


def test_names_are_the_services_labels_without_resolving_a_path() -> None:
    planner = SupervisorPlanner()
    assert planner.names(SupervisorSettings()) == (
        ("worker", "dev.vibey.worker"),
        ("delivery", "dev.vibey.delivery"),
    )
    assert planner.names(SupervisorSettings(delivery=False, label_prefix="x")) == (
        ("worker", "x.worker"),
    )
    services = planner.services(SupervisorSettings(), PATHS)
    assert planner.names(SupervisorSettings()) == tuple((s.name, s.label) for s in services)
