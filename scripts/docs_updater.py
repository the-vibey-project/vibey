# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The daily documentation updater's book check (ADR-0083).

    python scripts/docs_updater.py book    # is the published develop book behind? (JSON)

The updater re-derives every generated part of the documentation, the paper and the book's
sources with `scripts/self_healer.py repair --lane docs_updater`; this answers the other half:
the book, the site and the paper PDF are published per channel by `release-surfaces.yml` after
each successful Release, so the develop channel is only as current as the newest develop
release whose surfaces rebuild succeeded. When that rebuild failed or never ran, the
updater dispatches it again from that release (`[docs_updater] republish_book`); when the
branch's tip has no successful release at all, it can only say so -- publishing a release is
never this lane's to do (12.d).

Status is evidence-bounded (10.f): the report names the release the book was built from, the
tip it was compared with, and the source (the Actions run history).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.docs_updater_interface import (
        BookChannelInterface,
        WorkflowRunsInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.docs_updater_interface import (  # type: ignore[import-not-found,no-redef]
        BookChannelInterface,
        WorkflowRunsInterface,
    )

REPO = Path(__file__).resolve().parents[1]
CONFIG = "scripts/daily_lanes.toml"


class GhWorkflowRuns(WorkflowRunsInterface):
    """The Actions API, by workflow file, filtered to the branch HERE rather than by the API:
    its `branch` filter answered with September's runs for an October question for runs a
    `workflow_run` event started (2026-10-06), and `gh run list --branch` goes through it too.
    A failed read raises: an unread history is not a current book."""

    def runs(self, workflow: str, branch: str) -> list[dict[str, Any]]:
        proc = subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "GET",
                f"repos/{{owner}}/{{repo}}/actions/workflows/{workflow}/runs",
                "-f",
                "per_page=100",
                "--jq",
                ".workflow_runs[] | {databaseId: .id, conclusion, headSha: .head_sha,"
                " createdAt: .created_at, branch: .head_branch} | @json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        proc.check_returncode()
        data = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        mine = [run for run in data if run.get("branch") == branch]
        return sorted(mine, key=lambda run: str(run.get("createdAt", "")), reverse=True)


class BookChannel(BookChannelInterface):
    """Compares the develop channel's last good rebuild with the newest good develop release."""

    def __init__(
        self,
        runs: WorkflowRunsInterface,
        branch: str,
        republish: bool,
        release: str = "vibey-engine.yml",
        surfaces: str = "release-surfaces.yml",
    ) -> None:
        self._runs = runs
        self._branch = branch
        self._republish = republish
        self._release = release
        self._surfaces = surfaces

    def assess(self, tip: str) -> dict[str, Any]:
        releases = self._runs.runs(self._release, self._branch)
        good = next((r for r in releases if r.get("conclusion") == "success"), None)
        if good is None:
            return {
                "rebuild_from": None,
                "built_from": None,
                "report": f"No successful {self._release} run on `{self._branch}` in the recent "
                "history: there is no release to build the book from.",
            }
        sha = str(good.get("headSha", ""))
        rebuilt = any(
            s.get("conclusion") == "success"
            and str(s.get("createdAt", "")) >= str(good.get("createdAt", ""))
            for s in self._runs.runs(self._surfaces, self._branch)
        )
        lag = ""
        if tip and not tip.startswith(sha[:7]) and sha != tip:
            newest = releases[0] if releases else {}
            lag = (
                f" The branch tip `{tip[:9]}` is newer: its newest {self._release} run "
                f"({newest.get('databaseId')}) ended `{newest.get('conclusion') or 'unfinished'}`,"
                " so the book will catch up only when a release on the tip succeeds."
            )
        if rebuilt:
            return {
                "rebuild_from": None,
                "built_from": sha,
                "report": f"The published `{self._branch}` book, site and paper are current with "
                f"the newest successful release (`{sha[:9]}`, run {good.get('databaseId')})." + lag,
            }
        rebuild = good.get("databaseId") if self._republish else None
        action = (
            "rebuilding them from it now"
            if rebuild
            else "left for the next release (`republish_book` is off)"
        )
        return {
            "rebuild_from": rebuild,
            "built_from": sha,
            "report": f"The published `{self._branch}` book, site and paper were not rebuilt "
            f"after the newest successful release (`{sha[:9]}`, run {good.get('databaseId')}): "
            f"{action}." + lag,
        }


def main(argv: list[str]) -> int:
    """Entry point. Module-level as every script's is."""
    if argv != ["book"]:
        print(__doc__, file=sys.stderr)
        return 2
    lane = tomllib.loads((REPO / CONFIG).read_text(encoding="utf-8"))["docs_updater"]
    branch = str(lane.get("branch", "develop"))
    tip = subprocess.run(
        ["git", "rev-parse", f"origin/{branch}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    channel = BookChannel(
        GhWorkflowRuns(),
        branch,
        bool(lane.get("republish_book", False)),
        str(lane.get("release_workflow", "vibey-engine.yml")),
        str(lane.get("surfaces_workflow", "release-surfaces.yml")),
    )
    print(json.dumps(channel.assess(tip)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
