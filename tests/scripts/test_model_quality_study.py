# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/model_quality_study.py`: tasks, fresh workspaces, event tallies, hidden-test scoring,
the digest-chained ledger, resumption, Wilson summaries and the preregistered decision rule.

Every outside thing (the runner, Ollama, the shell) is a fake, so each decision is exercised
without a model. Module-level test functions rather than a class with an interface beside it
(ADR-0016): pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from scripts import model_quality_study as mq

REPO = Path(__file__).resolve().parents[2]
SETTINGS = mq.Settings.load(REPO / mq.DEFAULT_CONFIG)


def make_task(root: Path, task_id: str, tier: str = "t1", language: str = "python") -> Path:
    directory = root / task_id
    (directory / "seed").mkdir(parents=True)
    (directory / "hidden").mkdir()
    (directory / "plan.md").write_text(f"Do {task_id}.\n")
    (directory / "seed" / "README.md").write_text("seed\n")
    (directory / "hidden" / "test_hidden.py").write_text("def test_x():\n    assert True\n")
    (directory / "task.toml").write_text(
        f'id = "{task_id}"\ntier = "{tier}"\nlanguage = "{language}"\n'
        'expected_files = ["out.py"]\n'
        '[[check]]\nname = "hidden"\nargv = ["python", "-m", "pytest", "-q", "hidden"]\n'
        '[[check]]\nname = "lint"\nargv = ["ruff", "check", "."]\n'
    )
    return directory


class Result:
    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


class ScriptedRunner:
    """Answers each argv by its first matching prefix; records what it was asked."""

    def __init__(self, answers: Mapping[str, Result] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[tuple[str, ...]] = []

    def run(
        self, argv: Sequence[str], *, cwd: str | None = None, timeout: float, env: Any = None
    ) -> Result:
        self.calls.append(tuple(argv))
        for key, result in self.answers.items():
            if key in " ".join(argv):
                return result
        return Result()


def test_loader_reads_tasks_sorted_and_rejects_a_malformed_one(tmp_path: Path) -> None:
    make_task(tmp_path, "b-task", "t2")
    make_task(tmp_path, "a-task", "t1")
    tasks = mq.TaskLoader().load_all(tmp_path)
    assert [task.id for task in tasks] == ["a-task", "b-task"]
    assert tasks[0].checks[0].name == "hidden"

    (tmp_path / "a-task" / "task.toml").write_text('id = "a-task"\n')
    with pytest.raises(ValueError, match="a-task"):
        mq.TaskLoader().load_all(tmp_path)


def test_loader_refuses_a_task_with_no_hidden_tests(tmp_path: Path) -> None:
    directory = make_task(tmp_path, "lonely")
    (directory / "hidden" / "test_hidden.py").unlink()
    with pytest.raises(ValueError, match="hidden"):
        mq.TaskLoader().load_all(tmp_path)


def test_split_is_seeded_balanced_and_disjoint(tmp_path: Path) -> None:
    for tier in ("t1", "t2", "t3"):
        for index in range(4):
            make_task(tmp_path, f"{tier}-{index}", tier)
    tasks = mq.TaskLoader().load_all(tmp_path)
    first = mq.TaskLoader().split(tasks, screening=6, seed=7)
    again = mq.TaskLoader().split(tasks, screening=6, seed=7)
    screening, confirmation = first
    assert [t.id for t in screening] == [t.id for t in again[0]]
    assert len(screening) == 6 and len(confirmation) == 6
    assert not {t.id for t in screening} & {t.id for t in confirmation}
    assert {t.tier for t in screening} == {"t1", "t2", "t3"}


def test_workspace_is_a_fresh_repo_without_the_hidden_tests(tmp_path: Path) -> None:
    task = mq.TaskLoader().load_all(_one(tmp_path / "tasks"))[0]
    work = mq.Workspace().create(task, tmp_path / "trials")
    assert (work / "README.md").is_file() and (work / "plan.md").is_file()
    assert not (work / "hidden").exists() and not (work / "test_hidden.py").exists()
    log = subprocess.run(["git", "log", "--oneline"], cwd=work, capture_output=True, text=True)
    assert log.returncode == 0 and len(log.stdout.splitlines()) == 1
    second = mq.Workspace().create(task, tmp_path / "trials")
    assert second != work


def _one(root: Path) -> Path:
    make_task(root, "only")
    return root


EVENTS = "\n".join(
    json.dumps(event)
    for event in (
        {"type": "tool.call", "name": "write_file"},
        {"type": "turn.completed", "turn": 1},
        {"type": "turn.retried", "reason": "tool_call_parse_error"},
        {"type": "tool.call", "name": "shell"},
        {"type": "tool.call", "name": "shell"},
        {"type": "turn.completed", "turn": 2},
        {"type": "completed", "turn": 2},
    )
)


def test_event_tally_counts_turns_calls_and_parse_retries() -> None:
    tally = mq.EventTally.parse(EVENTS + "\nnot json\n")
    assert tally.turns == 2 and tally.tool_calls == 3 and tally.parse_retries == 1
    assert tally.tools == {"write_file": 1, "shell": 2}
    assert tally.finished is True
    assert tally.parse_rate == pytest.approx(3 / 4)


def test_event_tally_of_an_empty_run_has_no_parse_rate() -> None:
    tally = mq.EventTally.parse("")
    assert tally.turns == 0 and tally.parse_rate is None and tally.finished is False


def test_scorer_solves_only_when_every_check_passes(tmp_path: Path) -> None:
    task = mq.TaskLoader().load_all(_one(tmp_path / "tasks"))[0]
    work = mq.Workspace().create(task, tmp_path / "trials")
    (work / "out.py").write_text("x = 1\n")
    scorer = mq.TrialScorer(ScriptedRunner(), timeout=30)
    score = scorer.score(task, work)
    assert score["solved"] is True and score["failure"] is None
    assert (work / "hidden" / "test_hidden.py").is_file()  # copied in only at scoring time


@pytest.mark.parametrize(
    ("answers", "failure"),
    [
        ({"pytest": Result(1)}, "wrong_behaviour"),
        ({"ruff": Result(1)}, "lint"),
        ({"pytest": Result(124)}, "check_timeout"),
    ],
)
def test_scorer_classifies_the_failure(
    tmp_path: Path, answers: Mapping[str, Result], failure: str
) -> None:
    task = mq.TaskLoader().load_all(_one(tmp_path / "tasks"))[0]
    work = mq.Workspace().create(task, tmp_path / "trials")
    (work / "out.py").write_text("x = 1\n")
    score = mq.TrialScorer(ScriptedRunner(answers), timeout=30).score(task, work)
    assert score["solved"] is False and score["failure"] == failure


def test_scorer_reports_missing_files_before_running_a_check(tmp_path: Path) -> None:
    task = mq.TaskLoader().load_all(_one(tmp_path / "tasks"))[0]
    work = mq.Workspace().create(task, tmp_path / "trials")
    runner = ScriptedRunner()
    score = mq.TrialScorer(runner, timeout=30).score(task, work)
    assert score["failure"] == "no_files" and score["solved"] is False
    assert runner.calls == []


def test_the_models_own_passing_tests_count_for_nothing(tmp_path: Path) -> None:
    task = mq.TaskLoader().load_all(_one(tmp_path / "tasks"))[0]
    work = mq.Workspace().create(task, tmp_path / "trials")
    (work / "out.py").write_text("x = 1\n")
    (work / "test_mine.py").write_text("def test_mine():\n    assert True\n")
    score = mq.TrialScorer(ScriptedRunner({"pytest": Result(1)}), timeout=30).score(task, work)
    assert score["solved"] is False


def trial(
    model: str, task: str, number: int, solved: bool, tier: str = "t1", secs: float = 60
) -> dict[str, Any]:
    return {
        "model": model,
        "task": task,
        "trial": number,
        "tier": tier,
        "set": "confirmation",
        "solved": solved,
        "seconds": secs,
        "failure": None if solved else "wrong_behaviour",
    }


def test_ledger_chains_trials_and_resume_skips_what_is_recorded(tmp_path: Path) -> None:
    ledger = mq.StudyLedger(tmp_path / "ledger.jsonl")
    ledger.append(trial("m", "a", 1, True))
    ledger.append(trial("m", "a", 2, False))
    assert [row["trial"] for row in ledger.read()] == [1, 2]
    assert mq.StudyLedger(tmp_path / "ledger.jsonl").done() == {("m", "a", 1), ("m", "a", 2)}

    lines = (tmp_path / "ledger.jsonl").read_text().splitlines()
    lines[0] = lines[0].replace('"solved":true', '"solved":false')
    (tmp_path / "ledger.jsonl").write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError, match="digest"):
        mq.StudyLedger(tmp_path / "ledger.jsonl").read()


def test_summary_gives_wilson_intervals_per_model_and_tier() -> None:
    trials = [trial("good", "a", n, n <= 4) for n in range(1, 6)]
    trials += [trial("bad", "a", n, n == 1, tier="t2") for n in range(1, 6)]
    summary = mq.StudySummarizer().summarize(trials, z=1.96)
    good = summary["models"]["good"]
    assert good["solved"] == 4 and good["n"] == 5
    low, high = good["wilson"]
    assert 0.3 < low < 0.5 and 0.9 < high < 1.0
    assert summary["models"]["bad"]["tiers"]["t2"]["solved"] == 1


MODELS = [
    {"key": "open-best", "license_osi": True, "reference_only": False},
    {"key": "open-slow", "license_osi": True, "reference_only": False},
    {"key": "closed-better", "license_osi": False, "reference_only": True},
]


def test_decision_never_selects_a_non_osi_model_even_if_it_wins() -> None:
    trials = [trial("closed-better", "a", n, True) for n in range(1, 21)]
    trials += [trial("open-best", "a", n, n <= 12) for n in range(1, 21)]
    trials += [trial("open-slow", "a", n, n <= 4) for n in range(1, 21)]
    summary = mq.StudySummarizer().summarize(trials, z=1.96)
    verdict = mq.StudySummarizer().decide(summary, MODELS)
    assert verdict["default"] == "open-best"
    assert verdict["ranking"][0] == "closed-better"
    assert "licence" in verdict["reasons"]["closed-better"]


def test_speed_breaks_a_tie_only_when_the_intervals_overlap() -> None:
    fast = [trial("open-best", "a", n, n <= 3, secs=30) for n in range(1, 6)]
    slow = [trial("open-slow", "a", n, n <= 4, secs=300) for n in range(1, 6)]
    summary = mq.StudySummarizer().summarize(fast + slow, z=1.96)
    verdict = mq.StudySummarizer().decide(summary, MODELS[:2])
    assert verdict["default"] == "open-best"  # 3/5 vs 4/5 overlap, so the faster one wins
    assert "overlap" in verdict["reasons"]["open-best"]

    clear = [trial("open-best", "a", n, n <= 2, secs=30) for n in range(1, 41)]
    clear += [trial("open-slow", "a", n, True, secs=300) for n in range(1, 41)]
    summary = mq.StudySummarizer().summarize(clear, z=1.96)
    assert mq.StudySummarizer().decide(summary, MODELS[:2])["default"] == "open-slow"


def test_decision_with_no_open_model_says_so() -> None:
    summary = mq.StudySummarizer().summarize([trial("closed-better", "a", 1, True)], z=1.96)
    verdict = mq.StudySummarizer().decide(summary, MODELS[2:])
    assert verdict["default"] is None and "no OSI" in verdict["reasons"]["_"]


class FakeOllama:
    def __init__(self, capabilities: frozenset[str] | None, resident_gib: float) -> None:
        self.capabilities = capabilities
        self.resident_gib = resident_gib
        self.created: list[tuple[str, str]] = []

    def probe(self, tag: str) -> frozenset[str] | None:
        return self.capabilities

    def create(self, name: str, modelfile: str) -> None:
        self.created.append((name, modelfile))

    def resident_bytes(self, name: str) -> int:
        return int(self.resident_gib * 1024**3)


ENTRY = {"key": "m", "tag": "m:1", "license_spdx": "Apache-2.0", "license_osi": True}


def test_screen_passes_a_tool_calling_model_that_fits() -> None:
    verdict = mq.ModelPreparer(
        FakeOllama(frozenset({"completion", "tools"}), 12.0), SETTINGS
    ).screen(ENTRY)
    assert verdict["eligible"] is True and verdict["runnable"] is True
    assert verdict["reasons"] == []


@pytest.mark.parametrize(
    ("caps", "gib", "entry", "fragment"),
    [
        (frozenset({"completion"}), 12.0, ENTRY, "tool-calling"),
        (frozenset({"tools"}), 30.0, ENTRY, "resident"),
        (None, 12.0, ENTRY, "tool-calling"),
        (frozenset({"tools"}), 12.0, {**ENTRY, "license_osi": False}, "licence"),
        (frozenset({"tools"}), 12.0, {**ENTRY, "license_spdx": ""}, "licence"),
    ],
)
def test_screen_names_every_reason_a_model_is_out(
    caps: frozenset[str] | None, gib: float, entry: Mapping[str, Any], fragment: str
) -> None:
    verdict = mq.ModelPreparer(FakeOllama(caps, gib), SETTINGS).screen(entry)
    assert fragment in " ".join(verdict["reasons"])
    assert verdict["eligible"] is False
    # A licence problem bars the default but not the measurement: a reference point still runs.
    assert verdict["runnable"] is (fragment == "licence")


def test_derive_builds_the_32k_tag_with_a_generated_modelfile() -> None:
    ollama = FakeOllama(frozenset({"tools"}), 12.0)
    name = mq.ModelPreparer(ollama, SETTINGS).derive(ENTRY, 32768)
    assert name == "mq-m-32768"
    assert ollama.created == [(name, "FROM m:1\nPARAMETER num_ctx 32768\n")]


def test_settings_declare_the_preregistered_values() -> None:
    assert SETTINGS.num_ctx == 32768 and SETTINGS.trials == 5
    assert SETTINGS.max_turns == 25 and SETTINGS.wall_s == 420
    keys = {model["key"] for model in SETTINGS.models}
    assert {"heretic-v2", "gpt-oss-stock"} <= keys
    gemma = next(model for model in SETTINGS.models if model["key"] == "gemma4-26b")
    assert gemma["reference_only"] is True and gemma["license_osi"] is False


class FakeIdle:
    def __init__(self, quiet_for: int) -> None:
        self.left = quiet_for

    def wait(self) -> tuple[bool, str, dict[str, Any]]:
        if self.left <= 0:
            return False, "host not idle", {}
        self.left -= 1
        return True, "", {"load1": 0.1}


class FakeTrialRunner:
    def run(self, *, workspace: Path, tag: str, plan: str) -> Mapping[str, Any]:
        (workspace / "out.py").write_text("x = 1\n")
        return {"exit": 0, "seconds": 5.0, "turns": 3, "tool_calls": 4}


def _study(
    tmp_path: Path, idle: FakeIdle
) -> tuple[mq.StudyRunner, mq.StudyLedger, tuple[Any, ...]]:
    root = tmp_path / "tasks"
    if not root.exists():
        _one(root)
    tasks = mq.TaskLoader().load_all(root)
    ledger = mq.StudyLedger(tmp_path / "ledger.jsonl")
    preparer = mq.ModelPreparer(FakeOllama(frozenset({"tools"}), 12.0), SETTINGS)
    runner = mq.StudyRunner(
        SETTINGS,
        ledger,
        FakeTrialRunner(),
        mq.TrialScorer(ScriptedRunner(), timeout=30),
        mq.Workspace(),
        preparer,
        idle,
        mq.SystemClock(),
        tmp_path / "trials",
    )
    return runner, ledger, tasks


def test_run_stops_when_the_host_is_busy_and_resumes_without_repeating(tmp_path: Path) -> None:
    runner, ledger, tasks = _study(tmp_path, FakeIdle(quiet_for=2))
    sets = {"screening": tasks}
    assert runner.run([ENTRY], sets, {"node": "h"}) == 2
    assert {key[2] for key in ledger.done()} == {1, 2}

    resumed, _, _ = _study(tmp_path, FakeIdle(quiet_for=99))
    assert resumed.run([ENTRY], sets, {"node": "h"}) == SETTINGS.trials - 2
    assert len(ledger.read()) == SETTINGS.trials
    assert all(row["solved"] for row in ledger.read())


def test_storm_home_refuses_volatile_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBEY_STORM_HOME", "/tmp/storm")
    with pytest.raises(SystemExit, match="volatile"):
        mq.Volatile.storm_home(SETTINGS)
    monkeypatch.setenv("VIBEY_STORM_HOME", str(Path.home() / "storm-home"))
    assert mq.Volatile.storm_home(SETTINGS).name == SETTINGS.trials_subdir
