# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/first_hour.py`: the measurement, the guide block, the survey and the check.

The steps are driven through a fake runner, so nothing is cloned or installed: every decision
the script makes about a failed step, an old record or a late comment is exercised without
the machine.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts import first_hour as fh
from scripts.interfaces import first_hour_interface as contracts

REPO = Path(__file__).resolve().parents[2]
SETTINGS = fh.FirstHourSettings.load(REPO / fh.DEFAULT_CONFIG)


class FakeRunner:
    """Answers each declared step by name; records every argv and cwd it was given."""

    def __init__(self, fail: str = "", head: str = "a" * 40, seconds: float = 10.0) -> None:
        self.fail = fail
        self.head = head
        self.seconds = seconds
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, argv: Sequence[str], *, cwd: Path, timeout: float, env: Mapping[str, str]):
        self.calls.append((list(argv), cwd))
        if list(argv)[:2] == ["git", "rev-parse"]:
            return fh.StepOutcome(0, 0.1, self.head)
        failed = self.fail != "" and self.fail in " ".join(argv)
        if list(argv)[:2] == ["git", "clone"] and not failed:
            Path(argv[-1]).mkdir(parents=True)
        return fh.StepOutcome(1 if failed else 0, self.seconds, "boom" if failed else "")


class FixedClock:
    def now(self) -> str:
        return "2026-10-28T09:00:00Z"


def project(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "first_hour.toml").write_text((REPO / fh.DEFAULT_CONFIG).read_text())
    (tmp_path / "CONTRIBUTING.md").write_text(f"intro\n\n{fh.BEGIN}\n{fh.END}\n\nrest\n")
    return tmp_path


def measure(tmp_path: Path, runner: FakeRunner, run_id: str = "1"):
    workdir = tmp_path / "w"
    workdir.mkdir()
    return fh.FirstHourMeasurer(SETTINGS, runner, FixedClock()).measure(
        workdir, run_id, {}
    ), workdir


# ------------------------------------------------------------------ contracts and settings


def test_the_classes_implement_their_declared_contracts():
    ledger = fh.FirstHourLedger(Path("x"), "run_id")
    measurer = fh.FirstHourMeasurer(SETTINGS, FakeRunner(), FixedClock())
    declared = [
        (ledger, contracts.FirstHourLedgerInterface),
        (measurer, contracts.FirstHourMeasurerInterface),
        (fh.GuideRenderer(SETTINGS), contracts.GuideRendererInterface),
        (fh.SurveyCollector(SETTINGS, ledger), contracts.SurveyCollectorInterface),
    ]
    for instance, interface in declared:
        assert interface in type(instance).__mro__


def test_the_declared_steps_are_the_guides_and_the_owner_is_named():
    names = [step["name"] for step in SETTINGS["steps"]]
    assert names == ["clone", "setup", "version", "first test", "chaos test"]
    assert SETTINGS["owner"]
    guide = (REPO / SETTINGS["guide"]).read_text()
    for step in SETTINGS["steps"][1:]:
        assert " ".join(step["argv"]) in guide, step["name"]


@pytest.mark.parametrize("key", fh.REQUIRED)
def test_a_missing_key_is_an_error_not_a_default(key):
    table = {k: v for k, v in SETTINGS.table.items() if k != key}
    with pytest.raises(ValueError, match=key):
        fh.FirstHourSettings(table)


def test_a_missing_survey_key_is_an_error():
    survey = {k: v for k, v in SETTINGS["survey"].items() if k != "months"}
    with pytest.raises(ValueError, match="months"):
        fh.FirstHourSettings({**SETTINGS.table, "survey": survey})


def test_a_step_missing_a_key_or_with_a_bad_cwd_is_an_error():
    with pytest.raises(ValueError, match="argv"):
        fh.FirstHourSettings(
            {**SETTINGS.table, "steps": [{"name": "a", "guide_step": "1", "cwd": "clone"}]}
        )
    bad = {"name": "a", "guide_step": "1", "cwd": "elsewhere", "argv": ["x"]}
    with pytest.raises(ValueError, match="cwd"):
        fh.FirstHourSettings({**SETTINGS.table, "steps": [bad]})
    with pytest.raises(ValueError, match="no steps"):
        fh.FirstHourSettings({**SETTINGS.table, "steps": []})


# ---------------------------------------------------------------------------- the ledger


def test_the_ledger_appends_once_per_identity_and_never_rewrites(tmp_path):
    ledger = fh.FirstHourLedger(tmp_path / "a" / "r.jsonl", "run_id")
    assert ledger.read() == []
    assert ledger.append({"run_id": "1", "x": 1}) is True
    assert ledger.append({"run_id": "1", "x": 2}) is False
    assert ledger.append({"run_id": "2"}) is True
    assert [r["run_id"] for r in ledger.read()] == ["1", "2"]
    assert json.loads(ledger.path.read_text().splitlines()[0])["x"] == 1


def test_the_ledger_repairs_a_missing_final_newline_without_touching_earlier_lines(tmp_path):
    path = tmp_path / "r.jsonl"
    path.write_text('{"run_id": "1"}')
    fh.FirstHourLedger(path, "run_id").append({"run_id": "2"})
    assert path.read_text() == '{"run_id": "1"}\n{"run_id": "2"}\n'


def test_a_malformed_or_repeated_line_names_its_number(tmp_path):
    path = tmp_path / "r.jsonl"
    path.write_text('{"run_id": "1"}\n\nnot json\n')
    with pytest.raises(ValueError, match=r"r.jsonl:3"):
        fh.FirstHourLedger(path, "run_id").read()
    path.write_text('{"run_id": "1"}\n{"run_id": "1"}\n')
    with pytest.raises(ValueError, match="appears twice"):
        fh.FirstHourLedger(path, "run_id").read()
    path.write_text('{"other": 1}\n')
    with pytest.raises(ValueError, match=r"r.jsonl:1"):
        fh.FirstHourLedger(path, "run_id").read()


# ------------------------------------------------------------------------ the measurement


def test_a_complete_run_times_every_step_and_records_the_commit(tmp_path):
    runner = FakeRunner(seconds=12.34)
    record, workdir = measure(tmp_path, runner)
    assert record["complete"] is True
    assert record["commit"] == "a" * 40
    assert record["total_seconds"] == 61.5
    assert [s["status"] for s in record["steps"]] == ["passed"] * 5
    assert record["runner"] == SETTINGS["runner"]
    assert record["substitutions"] == list(SETTINGS["substitutions"])
    clone_argv, clone_cwd = runner.calls[0]
    assert clone_argv[-1] == str(workdir / "vibey") and clone_cwd == workdir
    assert runner.calls[1][1] == workdir / "vibey"


def test_a_failed_step_ends_the_run_and_the_rest_are_marked_not_run(tmp_path):
    record, _ = measure(tmp_path, FakeRunner(fail="vibey-gh setup"))
    assert record["complete"] is False
    statuses = {s["name"]: s["status"] for s in record["steps"]}
    assert statuses == {
        "clone": "passed",
        "setup": "failed",
        "version": "skipped",
        "first test": "skipped",
        "chaos test": "skipped",
    }
    assert "exit 1: boom" in record["steps"][1]["reason"]
    assert "'setup' failed" in record["steps"][2]["reason"]
    assert record["total_seconds"] == 10.0


def test_a_clone_that_never_happened_records_no_commit(tmp_path):
    runner = FakeRunner(fail="git clone")
    record, _ = measure(tmp_path, runner)
    assert record["commit"] == ""
    assert not any(argv[:2] == ["git", "rev-parse"] for argv, _ in runner.calls)


def test_an_unreadable_head_records_no_commit(tmp_path):
    class NoHead(FakeRunner):
        def run(self, argv, *, cwd, timeout, env):
            if list(argv)[:2] == ["git", "rev-parse"]:
                return fh.StepOutcome(128, 0.0, "fatal")
            return super().run(argv, cwd=cwd, timeout=timeout, env=env)

    record, _ = measure(tmp_path, NoHead())
    assert record["commit"] == ""


def test_the_subprocess_runner_reports_a_missing_tool_a_failure_and_a_timeout(tmp_path):
    runner = fh.SubprocessRunner()
    missing = runner.run(["definitely-not-a-tool-xyz"], cwd=tmp_path, timeout=5, env={})
    assert missing.returncode == 127
    ok = runner.run([sys.executable, "-c", "print('hi')"], cwd=tmp_path, timeout=30, env={})
    assert (ok.returncode, ok.tail) == (0, "hi")
    bad = runner.run(
        [sys.executable, "-c", "import sys; sys.stderr.write('no'); sys.exit(3)"],
        cwd=tmp_path,
        timeout=30,
        env={},
    )
    assert (bad.returncode, bad.tail) == (3, "no")
    slow = runner.run(
        [sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp_path, timeout=0.2, env={}
    )
    assert slow.returncode == 124 and "timed out" in slow.tail
    assert subprocess.run([sys.executable, "-c", "pass"], check=False).returncode == 0


def test_the_system_clock_stamps_utc_to_the_second():
    assert fh.SystemClock().now().endswith("Z") and len(fh.SystemClock().now()) == 20


# ------------------------------------------------------------------------------ the guide


def complete_record(run_id="1", at="2026-10-20T09:00:00Z", seconds=754.0, commit="b" * 40):
    return {
        "run_id": run_id,
        "measured_at": at,
        "commit": commit,
        "runner": "a runner",
        "substitutions": ["one thing stood in"],
        "complete": True,
        "total_seconds": seconds,
        "steps": [{"name": "clone", "guide_step": "1", "status": "passed", "seconds": seconds}],
    }


def test_durations_read_as_minutes_and_seconds():
    assert fh.GuideRenderer.duration(754) == "12 min 34 s"
    assert fh.GuideRenderer.duration(45.2) == "45 s"


def test_the_block_says_not_measured_when_no_run_completed():
    block = fh.GuideRenderer(SETTINGS).block([{**complete_record(), "complete": False}])
    assert "Not yet measured" in block and f"@{SETTINGS['owner']}" in block


def test_the_block_states_the_latest_complete_run_with_what_stood_in():
    older = complete_record("1", "2026-10-01T09:00:00Z", 600.0, "c" * 40)
    newest = complete_record("2", "2026-10-20T09:00:00Z", 754.0)
    failed = {**complete_record("3", "2026-10-27T09:00:00Z", 1.0), "complete": False}
    block = fh.GuideRenderer(SETTINGS).block([older, newest, failed])
    assert "12 min 34 s" in block and "`bbbbbbbb`" in block and "2026-10-20" in block
    assert "- one thing stood in" in block and "| 1 | clone | 12 min 34 s |" in block
    assert "10 min" not in block


def test_render_replaces_only_the_block_and_check_notices_drift():
    renderer = fh.GuideRenderer(SETTINGS)
    text = f"top\n{fh.BEGIN}\nold\n{fh.END}\nbottom\n"
    out = renderer.render(text, [complete_record()])
    assert out.startswith("top\n") and out.endswith("bottom\n") and "old" not in out
    assert renderer.problems(out, [complete_record()]) == []
    assert "out of step" in renderer.problems(text, [complete_record()])[0]


def test_a_guide_without_the_block_is_refused_by_render_and_check():
    renderer = fh.GuideRenderer(SETTINGS)
    with pytest.raises(ValueError, match="no '<!-- BEGIN"):
        renderer.render("nothing", [])
    assert "no '<!-- BEGIN" in renderer.problems("nothing", [])[0]


def test_the_committed_guide_is_in_step_with_the_committed_record():
    ledger = fh.FirstHourLedger(REPO / SETTINGS["record"], "run_id")
    text = (REPO / SETTINGS["guide"]).read_text()
    assert fh.GuideRenderer(SETTINGS).problems(text, ledger.read()) == []


# ---------------------------------------------------------------------------- the survey


def comment(cid, body="answer", kind="User"):
    return {
        "id": cid,
        "created_at": f"2026-10-0{cid % 9 + 1}T00:00:00Z",
        "html_url": f"https://x/{cid}",
        "body": body,
        "user": {"type": kind},
    }


def test_the_quarter_and_the_months_a_survey_opens_in():
    survey = fh.SurveyCollector(SETTINGS, fh.FirstHourLedger(Path("x"), "comment_id"))
    assert survey.quarter(datetime(2026, 10, 28, tzinfo=UTC)) == "2026-Q4"
    assert survey.quarter(datetime(2027, 1, 1, tzinfo=UTC)) == "2027-Q1"
    assert survey.due(datetime(2026, 10, 28, tzinfo=UTC)) is True
    assert survey.due(datetime(2026, 11, 3, tzinfo=UTC)) is False
    assert survey.title("2026-Q4") == "First-hour survey 2026-Q4"
    body = survey.body("2026-Q4")
    assert (
        "1. How long" in body
        and f"@{SETTINGS['owner']}" in body
        and "<!-- first-hour-survey 2026-Q4 -->" in body
    )


def test_every_answer_is_recorded_once_whatever_order_or_lateness(tmp_path):
    ledger = fh.FirstHourLedger(tmp_path / "s.jsonl", "comment_id")
    survey = fh.SurveyCollector(SETTINGS, ledger)
    assert survey.collect([comment(30), comment(10), comment(20, kind="Bot")], "2026-Q4") == 2
    # A comment that arrives late, with an id lower than one already recorded, is not skipped.
    assert survey.collect([comment(30), comment(15), comment(10)], "2026-Q4") == 1
    assert [r["comment_id"] for r in ledger.read()] == [10, 30, 15]
    assert all("user" not in r and r["schema"] == fh.SURVEY_SCHEMA for r in ledger.read())


# --------------------------------------------------------------------------------- the CLI


def run(tmp_path, *argv, environ=None):
    return fh.FirstHourCli(tmp_path, FixedClock()).run(list(argv), environ or {})


def test_check_and_render_work_end_to_end_on_a_project(tmp_path, capsys):
    root = project(tmp_path)
    assert run(root, "check") == 1
    assert run(root, "render") == 0
    assert run(root, "check") == 0
    fh.FirstHourLedger(root / SETTINGS["record"], "run_id").append(complete_record())
    assert run(root, "check") == 1
    assert "out of step" in capsys.readouterr().err
    assert run(root, "render") == 0 and run(root, "check") == 0
    assert "12 min 34 s" in (root / "CONTRIBUTING.md").read_text()


def test_check_fails_on_a_corrupt_survey_record(tmp_path, capsys):
    root = project(tmp_path)
    run(root, "render")
    (root / SETTINGS["survey_record"]).parent.mkdir(parents=True)
    (root / SETTINGS["survey_record"]).write_text("not json\n")
    assert run(root, "check") == 1
    assert "survey" in capsys.readouterr().err


def test_a_bad_config_exits_2_and_a_bad_source_exits_1(tmp_path, capsys):
    assert run(tmp_path, "check") == 2
    assert "first_hour.toml" in capsys.readouterr().err
    root = project(tmp_path)
    (root / "CONTRIBUTING.md").unlink()
    assert run(root, "check") == 1


def test_measure_records_a_complete_run_and_exits_0(tmp_path, monkeypatch, capsys):
    root = project(tmp_path)
    runner = FakeRunner()
    monkeypatch.setattr(fh, "SubprocessRunner", lambda: runner)
    assert run(root, "measure", "--workdir", str(root / "w"), "--run-id", "9") == 0
    assert "complete: 50 s" in capsys.readouterr().out
    assert run(root, "measure", "--workdir", str(root / "w2"), "--run-id", "9") == 0
    assert "already recorded" in capsys.readouterr().out
    assert len(fh.FirstHourLedger(root / SETTINGS["record"], "run_id").read()) == 1


def test_measure_keeps_a_failed_run_in_the_record_and_exits_1(tmp_path, monkeypatch, capsys):
    root = project(tmp_path)
    monkeypatch.setattr(fh, "SubprocessRunner", lambda: FakeRunner(fail="chaos"))
    assert run(root, "measure", "--workdir", str(root / "w"), "--run-id", "9") == 1
    assert "did not complete" in capsys.readouterr().out
    [record] = fh.FirstHourLedger(root / SETTINGS["record"], "run_id").read()
    assert record["complete"] is False
    assert run(root, "render") == 0
    assert "Not yet measured" in (root / "CONTRIBUTING.md").read_text()


def test_measure_refuses_a_directory_that_is_not_empty(tmp_path, capsys):
    root = project(tmp_path)
    (root / "w").mkdir()
    (root / "w" / "leftover").write_text("x")
    assert run(root, "measure", "--workdir", str(root / "w"), "--run-id", "9") == 1
    assert "starts from nothing" in capsys.readouterr().err


def test_the_survey_commands_print_decide_and_collect(tmp_path, capsys):
    root = project(tmp_path)
    assert run(root, "survey-due", "--today", "2026-10-28") == 0
    assert run(root, "survey-due", "--today", "2026-11-28") == 1
    assert run(root, "survey-title", "--today", "2026-10-28") == 0
    assert capsys.readouterr().out.strip() == "First-hour survey 2026-Q4"
    assert run(root, "survey-body", "--today", "2026-10-28") == 0
    assert "Quarter: 2026-Q4." in capsys.readouterr().out
    assert run(root, "survey-due") in (0, 1)
    comments = root / "c.json"
    comments.write_text(json.dumps([comment(5), comment(6)]))
    assert run(root, "survey-collect", "--comments", str(comments), "--quarter", "2026-Q4") == 0
    assert "recorded 2 new" in capsys.readouterr().out
    assert run(root, "survey-collect", "--comments", str(comments), "--quarter", "2026-Q4") == 0
    assert "recorded 0 new" in capsys.readouterr().out


def test_an_unreadable_comment_source_changes_nothing_and_fails(tmp_path, capsys):
    root = project(tmp_path)
    bad = root / "c.json"
    for text in ("not json", '{"a": 1}'):
        bad.write_text(text)
        assert run(root, "survey-collect", "--comments", str(bad), "--quarter", "2026-Q4") == 1
    assert (
        run(
            root, "survey-collect", "--comments", str(root / "missing.json"), "--quarter", "2026-Q4"
        )
        == 1
    )
    assert not (root / SETTINGS["survey_record"]).exists()


def test_the_committed_configuration_loads_from_the_repository_root(capsys):
    assert fh.FirstHourCli(REPO, FixedClock()).run(["check"], {}) == 0
