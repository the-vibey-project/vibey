# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The daily backlog killer: pick one open issue an agent can work today (ADR-0083).

    python scripts/backlog_killer.py pick            # today's issue, as the agent's evidence
    python scripts/backlog_killer.py pick --number   # only its number; empty when there is none
    python scripts/backlog_killer.py candidates      # the ranked window, read-only

Which issues it skips and how it ranks them are declared in `scripts/daily_lanes.toml`
`[backlog_killer]`. It never changes the forge: `.github/workflows/backlog-killer.yml` hands the
pick to the `backlog` continuation prompt, whose patch can only ever become one draft pull
request through the continuation lane's guarded job.

Stateless by design (the 12.g pattern of `backlog_cleanup.py`): the pick is recomputed from the
live backlog and the date, so a lost or cancelled run leaves nothing to repair, and the job that
dispatches and the agent that works compute the same issue on the same day.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.backlog_killer_interface import (
        BacklogKillerInterface,
        BacklogSourceInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.backlog_killer_interface import (  # type: ignore[import-not-found,no-redef]
        BacklogKillerInterface,
        BacklogSourceInterface,
    )

REPO = Path(__file__).resolve().parents[1]
CONFIG = "scripts/daily_lanes.toml"
# `#123` as a reference, not inside a longer token such as a colour or an anchor.
REFERENCE = re.compile(r"(?<![\w/])#(\d+)\b")


class GhBacklogSource(BacklogSourceInterface):
    """The forge through its CLI. Reads only; a failed read raises."""

    def _json(self, *args: str) -> list[dict[str, Any]]:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
        proc.check_returncode()
        data = json.loads(proc.stdout or "[]")
        assert isinstance(data, list)
        return data

    def open_issues(self) -> list[dict[str, Any]]:
        return self._json(
            "issue",
            "list",
            "--state",
            "open",
            "--limit",
            "1000",
            "--json",
            "number,title,labels,body,createdAt,author",
        )

    def open_pull_requests(self) -> list[dict[str, Any]]:
        return self._json(
            "pr", "list", "--state", "open", "--limit", "300", "--json", "number,title,body"
        )


class BacklogKiller(BacklogKillerInterface):
    """Ranks the workable open issues and rotates through the best of them by date."""

    def __init__(
        self,
        source: BacklogSourceInterface,
        settings: dict[str, Any],
        expectations: dict[str, Any],
    ) -> None:
        self._source = source
        self._window = max(1, int(settings.get("window", 7)))
        self._body_chars = int(settings.get("body_chars", 6000))
        self._priority = [str(x) for x in settings.get("priority_labels", [])]
        self._skip_labels = {str(x) for x in settings.get("skip_labels", [])}
        self._skip_authors = {str(x) for x in settings.get("skip_authors", [])}
        entries = expectations.get("issues", {})
        self._held = {
            int(number)
            for number, entry in (entries.items() if isinstance(entries, dict) else ())
            if isinstance(entry, dict) and entry.get("never_act")
        }
        self._self_closing = tuple(
            str(m) for m in expectations.get("self_closing_markers", []) if m
        )

    @staticmethod
    def _labels(issue: dict[str, Any]) -> list[str]:
        return [str(label.get("name")) for label in issue.get("labels") or []]

    def _rank(self, issue: dict[str, Any]) -> tuple[int, str, int]:
        labels = self._labels(issue)
        tier = min(
            (self._priority.index(name) for name in labels if name in self._priority),
            default=len(self._priority),
        )
        return tier, str(issue.get("createdAt", "")), int(issue["number"])

    def candidates(self) -> list[dict[str, Any]]:
        # An issue an open pull request already names is someone's work in flight.
        in_flight = {
            int(n)
            for pr in self._source.open_pull_requests()
            for n in REFERENCE.findall(f"{pr.get('title', '')}\n{pr.get('body') or ''}")
        }
        workable = []
        for issue in self._source.open_issues():
            number = int(issue["number"])
            body = str(issue.get("body") or "")
            author = str((issue.get("author") or {}).get("login", ""))
            if (
                number in in_flight
                or number in self._held
                or author in self._skip_authors
                or self._skip_labels.intersection(self._labels(issue))
                or any(marker in body for marker in self._self_closing)
            ):
                continue
            workable.append(issue)
        return sorted(workable, key=self._rank)

    def pick(self, today: date) -> dict[str, Any] | None:
        window = self.candidates()[: self._window]
        if not window:
            return None
        return window[today.toordinal() % len(window)]

    def brief(self, issue: dict[str, Any] | None) -> str:
        if issue is None:
            return "No open issue is workable today: every one is held, in flight, or skipped."
        body = str(issue.get("body") or "").strip()
        cut = ""
        if len(body) > self._body_chars:
            body = body[: self._body_chars]
            cut = (
                f"\n\n[cut at {self._body_chars} characters; read the rest with "
                f"`gh issue view {issue['number']}`]"
            )
        labels = ", ".join(self._labels(issue)) or "none"
        return (
            f"Today's backlog item: #{issue['number']} — {issue.get('title', '')}\n"
            f"Labels: {labels}. Opened: {issue.get('createdAt', 'unknown')}.\n"
            f"Read it in full with: gh issue view {issue['number']} --comments\n\n"
            f"{body}{cut}"
        )


def load(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """The `[backlog_killer]` settings and the backlog expectations they point at.

    Module-level: the CLI's one loader, shared by `main` and the tests by name."""
    settings = tomllib.loads((root / CONFIG).read_text(encoding="utf-8"))["backlog_killer"]
    path = root / str(settings.get("expectations", "scripts/backlog_expectations.json"))
    expectations = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return settings, expectations


def main(argv: list[str]) -> int:
    """Entry point: `pick [--number]` or `candidates`. Module-level as every script's is."""
    if not argv or argv[0] not in {"pick", "candidates"}:
        print(__doc__, file=sys.stderr)
        return 2
    settings, expectations = load(REPO)
    killer = BacklogKiller(GhBacklogSource(), settings, expectations)
    if argv[0] == "candidates":
        for candidate in killer.candidates():
            print(f"#{candidate['number']} {candidate.get('title', '')}")
        return 0
    issue = killer.pick(datetime.now(UTC).date())
    if argv[1:] == ["--number"]:
        print(issue["number"] if issue else "")
        return 0
    print(killer.brief(issue))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
