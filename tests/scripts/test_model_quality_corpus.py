# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The model-quality task corpus is itself under test (research/model-quality/PREREGISTRATION.md, 4).

A task is only a fair measurement if (1) the seed alone does NOT pass its hidden tests, so there
is something to do; (2) the seed plus a reference solution passes EVERY check, so the task can be
done and the lint and type gates are satisfiable; (3) the plan names every file the scorer
expects, so a model is never failed for a name it was not told; and (4) nothing the model sees
leaks a hidden test. The structure checks always run. The execution checks run every check of
every task twice, which takes minutes, so they run when MQ_VALIDATE_CORPUS=1 (TypeScript type
checks additionally need MQ_VALIDATE_TSC=1 and the network, for a pinned `tsc` through npx).

Module-level test functions rather than a class with an interface beside it (ADR-0016): pytest
collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import model_quality_study as mq

REPO = Path(__file__).resolve().parents[2]
SETTINGS = mq.Settings.load(REPO / mq.DEFAULT_CONFIG)
TASKS = mq.TaskLoader().load_all(REPO / SETTINGS.tasks)
EXECUTE = os.environ.get("MQ_VALIDATE_CORPUS") == "1"
TSC = os.environ.get("MQ_VALIDATE_TSC") == "1"
#: The preregistered shape: tier counts, section 4.
TIER_COUNTS = {"t1": 8, "t2": 8, "t3": 8, "t4": 6}


def _argv(argv: tuple[str, ...]) -> list[str]:
    """The task's own argv, with the three Python tools run through this interpreter."""
    head, rest = argv[0], list(argv[1:])
    if head == "python":
        return [sys.executable, *rest]
    if head in {"ruff", "mypy"}:
        return [sys.executable, "-m", head, *rest]
    return [head, *rest]


def _prepare(task: mq.Task, tmp_path: Path, *, reference: bool) -> Path:
    work = tmp_path / ("ref" if reference else "seed")
    shutil.copytree(task.directory / "seed", work)
    if reference:
        shutil.copytree(task.directory / "reference", work, dirs_exist_ok=True)
    shutil.copytree(task.directory / "hidden", work / "hidden")
    return work


def _run(task: mq.Task, work: Path) -> dict[str, bool]:
    outcome: dict[str, bool] = {}
    for check in task.checks:
        if check.name == "types" and task.language == "typescript" and not TSC:
            continue
        done = subprocess.run(  # noqa: S603 - argv comes from the task file in this repository
            _argv(check.argv), cwd=work, capture_output=True, text=True, timeout=300, check=False
        )
        outcome[check.name] = done.returncode == 0
    return outcome


def test_the_corpus_has_the_preregistered_shape() -> None:
    counts = {tier: sum(1 for task in TASKS if task.tier == tier) for tier in mq.TIERS}
    assert counts == TIER_COUNTS
    assert len({task.id for task in TASKS}) == len(TASKS)
    languages = {task.language for task in TASKS}
    assert languages == {"python", "typescript"}


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.id)
def test_the_plan_names_every_file_the_scorer_expects(task: mq.Task) -> None:
    plan = task.plan
    for name in task.expected_files:
        assert name in plan, f"{task.id}: plan.md never mentions {name}, which the scorer needs"
    assert task.expected_files, f"{task.id}: expected_files is empty, so no_files can never fire"


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.id)
def test_nothing_the_model_sees_leaks_a_hidden_test(task: mq.Task) -> None:
    hidden = [path for path in (task.directory / "hidden").rglob("*") if path.is_file()]
    seen = [task.directory / "plan.md", *(task.directory / "seed").rglob("*")]
    seen_names = {path.name for path in seen if path.is_file()}
    for path in hidden:
        assert path.name not in seen_names, f"{task.id}: {path.name} is also in the seed or plan"
    plan = task.plan
    assert "hidden" not in plan.lower(), f"{task.id}: plan.md mentions the hidden tests"


@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.id)
def test_a_task_has_a_reference_solution(task: mq.Task) -> None:
    reference = task.directory / "reference"
    assert reference.is_dir() and any(p.is_file() for p in reference.rglob("*"))
    for name in task.expected_files:
        assert (reference / name).is_file(), f"{task.id}: reference lacks {name}"


@pytest.mark.skipif(not EXECUTE, reason="set MQ_VALIDATE_CORPUS=1 to run every task's checks")
@pytest.mark.parametrize("task", TASKS, ids=lambda task: task.id)
def test_the_seed_alone_fails_and_the_reference_passes_every_check(
    task: mq.Task, tmp_path: Path
) -> None:
    seed = _run(task, _prepare(task, tmp_path, reference=False))
    assert seed.get("hidden") is False, f"{task.id}: the seed already passes the hidden tests"
    solved = _run(task, _prepare(task, tmp_path, reference=True))
    assert solved and all(solved.values()), f"{task.id}: reference fails {solved}"
