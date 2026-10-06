# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/docs_updater.py`: is the published develop book behind the release it is built from?

The cases are the ones the forge showed on 2026-10-06: a book current with yesterday's release
while the branch tip's own release failed on a registry outage, and a channel whose rebuild
never ran after its release.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
from typing import Any

from scripts import docs_updater as du


def run(rid: int, conclusion: str | None, created: str, sha: str = "a" * 40) -> dict[str, Any]:
    return {"databaseId": rid, "conclusion": conclusion, "createdAt": created, "headSha": sha}


class FakeRuns:
    def __init__(self, releases: list[dict[str, Any]], surfaces: list[dict[str, Any]]) -> None:
        self._by = {"vibey-engine.yml": releases, "release-surfaces.yml": surfaces}
        self.asked: list[tuple[str, str]] = []

    def runs(self, workflow: str, branch: str) -> list[dict[str, Any]]:
        self.asked.append((workflow, branch))
        return self._by[workflow]


TIP = "8329a74b5fdbf2f55383e39633ed8665076e9401"
GOOD = "3c66cc1466ae0cd70f3919e2df78afbab50067e0"


def test_a_book_rebuilt_after_its_release_is_current_and_says_how_the_tip_lags() -> None:
    releases = [
        run(3, "failure", "2026-10-06T10:50:24Z", TIP),
        run(2, "success", "2026-10-05T16:00:13Z", GOOD),
    ]
    surfaces = [
        run(9, "skipped", "2026-10-06T10:52:37Z"),
        run(8, "success", "2026-10-05T16:02:14Z"),
    ]
    verdict = du.BookChannel(FakeRuns(releases, surfaces), "develop", True).assess(TIP)
    assert verdict["rebuild_from"] is None and verdict["built_from"] == GOOD
    assert "current with the newest successful release (`3c66cc146`, run 2)" in verdict["report"]
    assert "The branch tip `8329a74b5` is newer" in verdict["report"]
    assert "ended `failure`" in verdict["report"]


def test_a_book_never_rebuilt_after_its_release_is_rebuilt_from_it() -> None:
    releases = [run(2, "success", "2026-10-05T16:00:13Z", GOOD)]
    surfaces = [
        run(8, "cancelled", "2026-10-05T16:02:14Z"),
        run(7, "success", "2026-10-04T09:00:00Z"),
    ]
    verdict = du.BookChannel(FakeRuns(releases, surfaces), "develop", True).assess(GOOD)
    assert verdict["rebuild_from"] == 2
    assert "rebuilding them from it now" in verdict["report"]
    assert "newer" not in verdict["report"]  # the tip IS the release


def test_with_republishing_off_a_stale_book_is_only_reported() -> None:
    releases = [run(2, "success", "2026-10-05T16:00:13Z", GOOD)]
    verdict = du.BookChannel(FakeRuns(releases, []), "develop", False).assess(GOOD)
    assert verdict["rebuild_from"] is None
    assert "`republish_book` is off" in verdict["report"]


def test_no_successful_release_means_nothing_to_build_from() -> None:
    verdict = du.BookChannel(
        FakeRuns([run(3, "failure", "2026-10-06T10:50:24Z")], []), "develop", True
    ).assess(TIP)
    assert verdict == {
        "rebuild_from": None,
        "built_from": None,
        "report": "No successful vibey-engine.yml run on `develop` in the recent history: "
        "there is no release to build the book from.",
    }


def test_the_workflows_are_read_by_file_on_the_declared_branch() -> None:
    runs = FakeRuns([run(2, "success", "2026-10-05T16:00:13Z")], [])
    du.BookChannel(runs, "develop", True, "rel.yml", "surf.yml")  # declared names are kept
    du.BookChannel(runs, "develop", True).assess("")
    assert runs.asked == [("vibey-engine.yml", "develop"), ("release-surfaces.yml", "develop")]


def test_the_forge_reader_filters_the_branch_itself(monkeypatch) -> None:
    seen: list[list[str]] = []

    def fake_run(argv: list[str], **_: Any) -> Any:
        seen.append(argv)
        lines = [
            json.dumps({"databaseId": 1, "createdAt": "2026-10-05", "branch": "develop"}),
            json.dumps({"databaseId": 2, "createdAt": "2026-10-06", "branch": "main"}),
            json.dumps({"databaseId": 3, "createdAt": "2026-10-06", "branch": "develop"}),
        ]
        return type(
            "P",
            (),
            {"returncode": 0, "stdout": "\n".join(lines), "check_returncode": lambda self: None},
        )()

    monkeypatch.setattr(du.subprocess, "run", fake_run)
    assert [
        r["databaseId"] for r in du.GhWorkflowRuns().runs("release-surfaces.yml", "develop")
    ] == [3, 1]
    assert "repos/{owner}/{repo}/actions/workflows/release-surfaces.yml/runs" in seen[0]
    assert not any(part.startswith("branch=") for part in seen[0])


def test_the_cli(monkeypatch, capsys) -> None:
    assert du.main([]) == 2
    monkeypatch.setattr(
        du,
        "GhWorkflowRuns",
        lambda: FakeRuns([run(2, "success", "2026-10-05T16:00:13Z", GOOD)], []),
    )
    assert du.main(["book"]) == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["rebuild_from"] == 2  # [docs_updater] republish_book is declared on
