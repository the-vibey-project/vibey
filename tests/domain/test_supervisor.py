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


# --- the state sync (ADR-0086) ----------------------------------------------------------

STATE_PATHS = SupervisorPaths(
    vibey=PATHS.vibey,
    python=PATHS.python,
    repo=PATHS.repo,
    env_file=PATHS.env_file,
    log_dir=PATHS.log_dir,
    state_env_file="/home/op/.config/vibey/state-sync.env",
)


def test_names_include_the_state_sync_when_it_is_supervised() -> None:
    planner = SupervisorPlanner()
    assert planner.names(SupervisorSettings(state_sync=True)) == (
        ("worker", "dev.vibey.worker"),
        ("delivery", "dev.vibey.delivery"),
        ("state-sync", "dev.vibey.state-sync"),
    )
    assert planner.names(SupervisorSettings(delivery=False, state_sync=True)) == (
        ("worker", "dev.vibey.worker"),
        ("state-sync", "dev.vibey.state-sync"),
    )
    services = planner.services(SupervisorSettings(state_sync=True), STATE_PATHS)
    assert planner.names(SupervisorSettings(state_sync=True)) == tuple(
        (s.name, s.label) for s in services
    )


def test_the_state_sync_runs_on_its_own_env_file_every_interval() -> None:
    settings = SupervisorSettings(
        state_sync=True,
        state_sync_interval_seconds=120,
        state_sync_args=("--no-push",),
        label_prefix="org.example",
    )
    worker, delivery, state_sync = SupervisorPlanner().services(settings, STATE_PATHS)
    assert worker.argv[:6] == LAUNCH and delivery.argv[:6] == LAUNCH
    assert state_sync.name == "state-sync"
    assert state_sync.label == "org.example.state-sync"
    assert state_sync.argv == (
        "/opt/vibey/bin/vibey",
        "supervisor",
        "exec",
        "--env-file",
        "/home/op/.config/vibey/state-sync.env",
        "--",
        "/opt/vibey/bin/vibey",
        "state",
        "sync",
        "--every",
        "120",
        "--no-push",
    )
    assert PATHS.env_file not in state_sync.argv
    assert state_sync.working_directory == "/srv/git/vibey"
    assert state_sync.log_path == "/home/op/.local/state/vibey/logs/state-sync.log"


def test_the_state_sync_without_the_bridge() -> None:
    settings = SupervisorSettings(delivery=False, state_sync=True)
    worker, state_sync = SupervisorPlanner().services(settings, STATE_PATHS)
    assert worker.name == "worker"
    assert state_sync.argv[-3:] == ("sync", "--every", "300")


def test_a_state_sync_interval_no_loop_could_keep_is_refused() -> None:
    with pytest.raises(ValueError, match="state_sync_interval_seconds"):
        SupervisorPlanner().services(
            SupervisorSettings(state_sync=True, state_sync_interval_seconds=0), STATE_PATHS
        )


def test_an_interval_is_only_checked_for_a_state_sync_that_runs() -> None:
    settings = SupervisorSettings(state_sync_interval_seconds=0)
    assert len(SupervisorPlanner().services(settings, PATHS)) == 2


def test_a_state_sync_without_its_env_file_is_refused() -> None:
    with pytest.raises(ValueError, match="state sync's environment file was not resolved"):
        SupervisorPlanner().services(SupervisorSettings(state_sync=True), PATHS)
