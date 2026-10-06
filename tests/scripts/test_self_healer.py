# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/self_healer.py` against a fake forge and a fake runner.

Each case is a red develop the self-healer met for real on 2026-10-05: a lane that is red only
on an older run, a PR gate failing on develop because it was refusing a pull request, a flake
that passes on a second try, and a scripted repair that changed a path it had no business in.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from scripts import self_healer as sh

NOW = datetime(2026, 10, 6, 5, 17, tzinfo=UTC)


def run(rid: int, path: str, conclusion: str, created: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": rid,
        "name": Path(path).stem,
        "path": f".github/workflows/{path}",
        "event": extra.pop("event", "push"),
        "status": extra.pop("status", "completed"),
        "conclusion": conclusion,
        "run_attempt": extra.pop("attempt", 1),
        "created_at": created,
        "html_url": f"https://example/{rid}",
    }


class FakeForge:
    def __init__(self, runs: list[dict[str, Any]], refuse: set[int] | None = None) -> None:
        self._runs = runs
        self._refuse = refuse or set()
        self.since: datetime | None = None
        self.reran: list[int] = []

    def runs(self, branch: str, since: datetime) -> list[dict[str, Any]]:
        self.since = since
        return self._runs

    def rerun_failed(self, run_id: int) -> bool:
        if run_id in self._refuse:
            return False
        self.reran.append(run_id)
        return True


class FakeRunner:
    def __init__(self, answers: dict[str, tuple[int, str]] | None = None) -> None:
        self._answers = answers or {}
        self.calls: list[tuple[list[str], Path]] = []

    def run(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        self.calls.append((argv, cwd))
        return self._answers.get(argv[0], (0, "ok"))


SETTINGS: dict[str, Any] = {
    "branch": "develop",
    "window_hours": 24,
    "events": ["push", "schedule"],
    "rerun_workflows": ["ci.yml"],
    "max_attempts": 1,
    "max_reruns": 2,
    "repair": [
        {"name": "pages", "argv": ["python", "render.py"]},
        {"name": "npm", "cwd": "clients/app", "argv": ["npm", "audit", "fix"]},
    ],
    "guard": {"allowed_paths": [r"^docs/continuation/[^/]+\.md$", r"^uv\.lock$"]},
}


def healer(forge: FakeForge, runner: FakeRunner | None = None, **override: Any) -> sh.SelfHealer:
    return sh.SelfHealer(forge, runner or FakeRunner(), {**SETTINGS, **override}, Path("/repo"))


def test_only_the_newest_run_of_each_workflow_speaks_for_it() -> None:
    forge = FakeForge(
        [
            run(1, "ci.yml", "failure", "2026-10-05T16:00:00Z"),
            run(2, "ci.yml", "success", "2026-10-05T20:00:00Z"),
            run(3, "backlog-cleanup.yml", "success", "2026-10-05T10:00:00Z", event="schedule"),
            run(4, "backlog-cleanup.yml", "failure", "2026-10-06T03:20:00Z", event="schedule"),
        ]
    )
    assert [x["id"] for x in healer(forge).failing(NOW)] == [4]
    assert forge.since == datetime(2026, 10, 5, 5, 17, tzinfo=UTC)


def test_a_dispatch_on_develop_and_an_unfinished_run_are_not_develop_failing() -> None:
    """The PR review gate dispatches on develop for every pull request; its failures are it
    refusing a pull request, not develop being broken."""
    forge = FakeForge(
        [
            run(1, "pr-review.yml", "failure", "2026-10-06T01:00:00Z", event="workflow_dispatch"),
            run(2, "ci.yml", None, "2026-10-06T04:00:00Z", status="in_progress"),  # type: ignore[arg-type]
            run(3, "ci.yml", "cancelled", "2026-10-06T03:00:00Z"),
        ]
    )
    assert healer(forge).failing(NOW) == []


def test_timed_out_and_startup_failures_are_failures() -> None:
    forge = FakeForge(
        [
            run(1, "a.yml", "timed_out", "2026-10-06T01:00:00Z"),
            run(2, "b.yml", "startup_failure", "2026-10-06T01:00:00Z"),
        ]
    )
    lanes = healer(forge).failing(NOW)
    assert [(x["workflow"], x["conclusion"]) for x in lanes] == [
        ("a.yml", "timed_out"),
        ("b.yml", "startup_failure"),
    ]
    assert lanes[0]["url"] == "https://example/1"


def test_a_flake_on_the_allowlist_is_rerun_once_and_capped() -> None:
    lanes = [
        {"workflow": "ci.yml", "id": 1, "attempt": 1},
        {"workflow": "ci.yml", "id": 2, "attempt": 2},  # already re-run: a real failure
        {"workflow": "promote-to-main.yml", "id": 3, "attempt": 1},  # never re-run a release
        {"workflow": "ci.yml", "id": 4, "attempt": 1},
        {"workflow": "ci.yml", "id": 5, "attempt": 1},  # past the cap of 2
    ]
    forge = FakeForge([])
    done = healer(forge).rerun(lanes)
    assert [x["id"] for x in done] == [1, 4]
    assert forge.reran == [1, 4]


def test_a_refused_rerun_is_not_counted_as_done() -> None:
    forge = FakeForge([], refuse={1})
    done = healer(forge).rerun([{"workflow": "ci.yml", "id": 1, "attempt": 1}])
    assert done == [] and forge.reran == []


def test_every_repair_runs_in_order_in_its_directory_and_a_failure_does_not_stop_the_rest() -> None:
    runner = FakeRunner({"python": (1, "x" * 1000)})
    results = healer(FakeForge([]), runner).repair()
    assert [(argv[0], cwd) for argv, cwd in runner.calls] == [
        ("python", Path("/repo")),
        ("npm", Path("/repo/clients/app")),
    ]
    assert [(r["name"], r["code"]) for r in results] == [("pages", 1), ("npm", 0)]
    assert len(results[0]["tail"]) == 600


def test_a_repair_patch_outside_the_allowed_paths_is_refused() -> None:
    touched = [
        ("M", "docs/continuation/keep-green.md"),
        ("M", "uv.lock"),
        ("M", "scripts/self_healer.py"),
        ("A", "docs/continuation/x/nested.md"),
    ]
    assert healer(FakeForge([])).refused(touched) == [
        "docs/continuation/x/nested.md",
        "scripts/self_healer.py",
    ]


def test_a_rename_is_checked_on_both_sides() -> None:
    touched = [("D", "uv.lock"), ("A", ".github/workflows/ci.yml")]
    assert healer(FakeForge([])).refused(touched) == [".github/workflows/ci.yml"]


def test_the_repair_guard_fails_closed() -> None:
    assert healer(FakeForge([])).refused(None) == ["(a patch git cannot apply to HEAD)"]
    assert healer(FakeForge([])).refused([]) == ["(a patch that changes no path)"]


AUDIT = {
    "dependencies": [
        {
            "name": "multidict",
            "version": "6.7.1",
            "vulns": [{"id": "CVE-1", "fix_versions": ["6.9.1"]}],
        },
        {"name": "unfixed", "version": "1.0", "vulns": [{"id": "CVE-2", "fix_versions": []}]},
        {"name": "clean", "version": "2.0", "vulns": []},
    ]
}


def test_only_an_advisory_with_a_fixed_release_is_relocked(capsys) -> None:
    runner = FakeRunner({"uv": (1, "noise before\n" + json.dumps(AUDIT))})
    lock = sh.AdvisoryLock(runner, Path("/repo"))
    assert lock.fixable(json.dumps(AUDIT)) == ["multidict"]
    lock.run()
    assert runner.calls[-1][0] == ["uv", "lock", "--upgrade-package", "multidict"]
    assert "uv lock --upgrade-package multidict" in capsys.readouterr().out


def test_no_fixable_advisory_relocks_nothing() -> None:
    runner = FakeRunner({"uv": (0, json.dumps({"dependencies": []}))})
    assert sh.AdvisoryLock(runner, Path("/repo")).run() == 0
    assert len(runner.calls) == 1


def test_an_unreadable_audit_is_reported_not_passed() -> None:
    runner = FakeRunner({"uv": (2, "pip-audit: command not found")})
    assert sh.AdvisoryLock(runner, Path("/repo")).run() == 1


def test_the_survey_table_names_its_object_source_and_cutoff() -> None:
    since = datetime(2026, 10, 5, 5, 17, tzinfo=UTC)
    assert "Nothing failing in the window." in sh.table([], since, "develop")
    lane = {"name": "CI", "event": "push", "conclusion": "failure", "attempt": 1, "url": "u"}
    text = sh.table([lane], since, "develop")
    assert "newest run per workflow since 2026-10-05T05:17Z (Actions API)" in text
    assert "| CI | push | failure | 1 | [run](u) |" in text


def test_the_declared_settings_are_sound() -> None:
    """The real `[self_healer]` table: every repair runs a list of strings, the guard lets the
    files those repairs write through, and nothing under .github/ or src/ is allowed."""
    config = sh.settings(Path(__file__).resolve().parents[2])
    assert config["prompt"] == "keep-green"
    assert all(isinstance(a, str) for r in config["repair"] for a in r["argv"])
    forge = FakeForge([])
    real = sh.SelfHealer(forge, FakeRunner(), config, Path("/repo"))
    for allowed in ("uv.lock", "package-lock.json", "clients/app/package-lock.json"):
        assert real.refused([("M", allowed)]) == []
    for refused in (
        ".github/workflows/ci.yml",
        "src/vibey/__init__.py",
        ".vibey-gh.toml",
        "docs/continuation/keep-green.md",  # the documentation updater's, not this lane's
    ):
        assert real.refused([("M", refused)]) == [refused]


def test_the_documentation_lane_is_the_same_runner_with_its_own_table() -> None:
    config = sh.settings(Path(__file__).resolve().parents[2], "docs_updater")
    assert config["prompt"] == "docs"
    names = [r["name"] for r in config["repair"]]
    assert names[0].startswith("paper figures")
    assert any("{integration_sha}" in part for part in config["repair"][0]["argv"])
    docs = sh.SelfHealer(FakeForge([]), FakeRunner(), config, Path("/repo"))
    for allowed in (
        "docs/paper.md",
        "docs/llms.txt",
        "README.md",
        "src/vibey_tools/gh/docs/cli.md",
    ):
        assert docs.refused([("M", allowed)]) == []
    for refused in (
        "uv.lock",
        "properdocs.yml",
        "src/vibey_tools/gh/corpus-index.json",
        "docs/x.py",
    ):
        assert docs.refused([("M", refused)]) == [refused]


def test_the_integration_sha_is_resolved_once_and_substituted() -> None:
    runner = FakeRunner({"git": (0, "abc123\n")})
    repairs = [
        {"name": "figures", "argv": ["python", "fig.py", "--rev", "{integration_sha}"]},
        {"name": "again", "argv": ["python", "x.py", "{integration_sha}"]},
    ]
    healer(FakeForge([]), runner, repair=repairs).repair()
    assert [argv for argv, _ in runner.calls] == [
        ["git", "rev-parse", "origin/develop"],
        ["python", "fig.py", "--rev", "abc123"],
        ["python", "x.py", "abc123"],
    ]


def test_an_unresolvable_integration_sha_fails_that_repair_only() -> None:
    runner = FakeRunner({"git": (128, "fatal: bad revision")})
    repairs = [
        {"name": "figures", "argv": ["python", "fig.py", "--rev", "{integration_sha}"]},
        {"name": "plain", "argv": ["npm", "x"]},
    ]
    results = healer(FakeForge([]), runner, repair=repairs).repair()
    assert [(r["name"], r["code"]) for r in results] == [("figures", 1), ("plain", 0)]
    assert "bad revision" in results[0]["tail"]


def test_the_cli_reads_another_lanes_table(capsys) -> None:
    assert sh.main(["setting", "pull_request_branch", "--lane", "docs_updater"]) == 0
    assert capsys.readouterr().out.strip() == "docs/updater"


def test_the_cli_refuses_an_unknown_command(capsys) -> None:
    assert sh.main([]) == 2
    assert sh.main(["nope"]) == 2


def test_the_cli_reads_one_setting(capsys) -> None:
    assert sh.main(["setting", "pull_request_branch"]) == 0
    assert capsys.readouterr().out.strip() == "fix/self-healer"


def test_the_cli_guard_reads_the_patch_as_git_applies_it(tmp_path: Path, capsys) -> None:
    """Against this repository's own HEAD: a new file under an allowed path passes, one
    anywhere else is refused, and a patch git cannot apply is refused, never waved through."""

    def new_file(path: str) -> Path:
        patch = tmp_path / "p.patch"
        patch.write_text(
            f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n"
            f"+++ b/{path}\n@@ -0,0 +1 @@\n+x\n"
        )
        return patch

    page = "docs/continuation/zz self-healer test.md"
    assert sh.main(["guard", str(new_file(page)), "--lane", "docs_updater"]) == 0
    assert sh.main(["guard", str(new_file(page))]) == 1  # the self-healer's table: lockfiles
    assert f"a scripted repair changed {page}" in capsys.readouterr().out
    assert (
        sh.main(["guard", str(new_file("src/zz self healer test.py")), "--lane", "docs_updater"])
        == 1
    )
    assert "a scripted repair changed src/zz self healer test.py" in capsys.readouterr().out
    junk = tmp_path / "junk.patch"
    junk.write_text("diff --git a/uv.lock b/uv.lock\n")
    assert sh.main(["guard", str(junk)]) == 1
    assert "(a patch git cannot apply to HEAD)" in capsys.readouterr().out


def test_rerun_writes_what_is_left_for_keep_green(tmp_path: Path, monkeypatch, capsys) -> None:
    forge = FakeForge([])
    monkeypatch.setattr(sh, "GhRunForge", lambda: forge)
    lanes = [
        {"workflow": "ci.yml", "name": "CI", "id": 1, "attempt": 1},
        {
            "workflow": "continuation-prompts.yml",
            "name": "Continuation prompts",
            "id": 2,
            "attempt": 1,
        },
    ]
    (tmp_path / "failures.json").write_text(json.dumps(lanes))
    assert sh.main(["rerun", str(tmp_path)]) == 0
    remaining = json.loads((tmp_path / "remaining.json").read_text())
    assert [x["id"] for x in remaining] == [2]
    assert "Re-ran 1: CI." in capsys.readouterr().out


def test_survey_writes_the_failures_and_the_summary(tmp_path: Path, monkeypatch, capsys) -> None:
    forge = FakeForge(
        [run(9, "ci.yml", "failure", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))]
    )
    monkeypatch.setattr(sh, "GhRunForge", lambda: forge)
    assert sh.main(["survey", str(tmp_path / "out")]) == 0
    assert [x["id"] for x in json.loads((tmp_path / "out/failures.json").read_text())] == [9]
    assert "| ci | push | failure | 1 |" in capsys.readouterr().out


def test_repair_prints_each_result_and_the_tail_of_a_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sh, "SubprocessArgvRunner", lambda: FakeRunner({"npm": (1, "ERESOLVE")}))
    assert sh.main(["repair"]) == 0
    out = capsys.readouterr().out
    assert "| npm advisories (krypton app) | 1 |" in out
    assert "ERESOLVE" in out


def test_the_argv_runner_reports_a_missing_tool_as_a_failed_repair(tmp_path: Path) -> None:
    code, output = sh.SubprocessArgvRunner().run(["definitely-not-a-tool-1234"], tmp_path)
    assert code == 127 and output


@pytest.mark.parametrize("argv", [["python", "-c", "print('hi')"]])
def test_the_argv_runner_returns_the_output(tmp_path: Path, argv: list[str]) -> None:
    assert sh.SubprocessArgvRunner().run(argv, tmp_path) == (0, "hi\n")


def test_the_forge_filters_the_branch_itself_not_through_the_api(monkeypatch) -> None:
    """The API's `branch` filter answered with weeks-old runs for some events (2026-10-06)."""
    seen: list[list[str]] = []

    def fake_run(argv: list[str], **_: Any) -> Any:
        seen.append(argv)
        lines = [
            json.dumps({"id": 1, "head_branch": "develop"}),
            json.dumps({"id": 2, "head_branch": "feature/x"}),
        ]
        return type(
            "P",
            (),
            {"returncode": 0, "stdout": "\n".join(lines), "check_returncode": lambda self: None},
        )()

    monkeypatch.setattr(sh.subprocess, "run", fake_run)
    runs = sh.GhRunForge().runs("develop", NOW)
    assert [r["id"] for r in runs] == [1]
    assert not any(part.startswith("branch=") for part in seen[0])
    assert "created=>=2026-10-06T05:17:00Z" in seen[0]
