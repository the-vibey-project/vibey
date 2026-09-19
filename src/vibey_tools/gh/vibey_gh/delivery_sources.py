# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Source adapters for the continuous delivery forecast.

The reader deliberately keeps a failed source call as a problem on the
snapshot.  An empty GitHub answer and an unreachable GitHub answer are not the
same observation, and the forecast must not turn the latter into a confident
zero-work result.
"""

from __future__ import annotations

import hashlib
import json
import subprocess  # nosec B404 - fixed argv, never shell=True
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, TypeAlias

from vibey_gh.delivery_estimate import (
    CommitObservation,
    IssueObservation,
    PullRequestObservation,
)
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.delivery_estimate_interface import (
    DeliverySourceReaderInterface,
    DeliverySourceSnapshotInterface,
)
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface

__all__ = ["DeliverySourceReader", "DeliverySourceSnapshot"]

GitRunner: TypeAlias = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

# ``gh issue list`` returns issue-only rows; pull requests are queried separately below.
# The parser still accepts a pullRequest-shaped row from alternate forge transports.
_ISSUE_FIELDS: Final = "number,state,labels"
_PR_FIELDS: Final = "number,state,mergedAt,labels"


@dataclass(frozen=True, slots=True)
class DeliverySourceSnapshot(DeliverySourceSnapshotInterface):
    issues: tuple[IssueObservation, ...] = ()
    pull_requests: tuple[PullRequestObservation, ...] = ()
    commits: tuple[CommitObservation, ...] = ()
    source_revision: str = "unknown"
    problems: tuple[str, ...] = ()

    @property
    def fingerprint(self) -> str:
        document = {
            "revision": self.source_revision,
            "issues": [self._issue(i) for i in self.issues],
            "pull_requests": [self._pr(p) for p in self.pull_requests],
            "commits": [self._commit(c) for c in self.commits],
        }
        encoded = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _issue(issue: IssueObservation) -> dict[str, object]:
        return {
            "number": issue.number,
            "state": issue.state,
            "is_pull_request": issue.is_pull_request,
            "labels": issue.labels,
        }

    @staticmethod
    def _pr(pull: PullRequestObservation) -> dict[str, object]:
        return {
            "number": pull.number,
            "state": pull.state,
            "merged_at": pull.merged_at,
            "labels": pull.labels,
        }

    @staticmethod
    def _commit(commit: CommitObservation) -> dict[str, object]:
        return {"sha": commit.sha, "committed_at": commit.committed_at}


class DeliverySourceReader(DeliverySourceReaderInterface):
    """Reads GitHub issue/PR state and the local complete git history."""

    def __init__(
        self,
        *,
        transport: GhTransportInterface | None = None,
        git_run: GitRunner | None = None,
    ) -> None:
        self._transport = transport or GhTransport()
        self._git_run = git_run or _run_git

    def read(self, repository: str, *, root: Path, limit: int = 1000) -> DeliverySourceSnapshot:
        if limit < 1:
            raise ValueError("delivery history limit must be positive")
        problems: list[str] = []
        issue_rows, issue_problem = self._transport.survey(
            [
                "issue",
                "list",
                "--repo",
                repository,
                "--state",
                "all",
                "--limit",
                str(limit),
                "--json",
                _ISSUE_FIELDS,
            ],
            cwd=root,
        )
        if issue_problem:
            problems.append(f"issues: {issue_problem}")
        pr_rows, pr_problem = self._transport.survey(
            [
                "pr",
                "list",
                "--repo",
                repository,
                "--state",
                "all",
                "--limit",
                str(limit),
                "--json",
                _PR_FIELDS,
            ],
            cwd=root,
        )
        if pr_problem:
            problems.append(f"pull requests: {pr_problem}")
        commit_rows, revision, git_problems = self._git_history(root)
        problems.extend(git_problems)
        return DeliverySourceSnapshot(
            issues=self._issues(issue_rows),
            pull_requests=self._pull_requests(pr_rows),
            commits=commit_rows,
            source_revision=revision,
            problems=tuple(problems),
        )

    @staticmethod
    def _issues(value: list[Any] | dict[str, Any]) -> tuple[IssueObservation, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(
            IssueObservation(
                number=number,
                state=str(row.get("state", "")),
                is_pull_request=isinstance(row.get("pullRequest"), Mapping),
                labels=_labels(row.get("labels")),
            )
            for row in value
            if isinstance(row, Mapping) and (number := _integer(row.get("number"))) is not None
        )

    @staticmethod
    def _pull_requests(value: list[Any] | dict[str, Any]) -> tuple[PullRequestObservation, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(
            PullRequestObservation(
                number=number,
                state=str(row.get("state", "")),
                merged_at=_optional_text(row.get("mergedAt")),
                labels=_labels(row.get("labels")),
            )
            for row in value
            if isinstance(row, Mapping) and (number := _integer(row.get("number"))) is not None
        )

    def _git_history(
        self, root: Path
    ) -> tuple[tuple[CommitObservation, ...], str, tuple[str, ...]]:
        problems: list[str] = []
        # The integration checkout is the work history.  ``--all`` would count stale
        # feature refs and double-count commits that are reachable through more than one
        # local branch, making throughput depend on checkout clutter rather than delivery.
        log = self._git_run(("log", "--format=%H%x09%cI", "HEAD"), root)
        commits: list[CommitObservation] = []
        if log.returncode:
            problems.append(
                f"git history: {(log.stderr or log.stdout).strip() or 'git log failed'}"
            )
        else:
            for line in log.stdout.splitlines():
                sha, separator, committed_at = line.partition("\t")
                if separator and sha and committed_at:
                    commits.append(CommitObservation(sha=sha, committed_at=committed_at))
        revision_run = self._git_run(("rev-parse", "HEAD"), root)
        if revision_run.returncode:
            problems.append(
                f"git revision: {(revision_run.stderr or revision_run.stdout).strip() or 'git rev-parse failed'}"
            )
            revision = "unknown"
        else:
            revision = revision_run.stdout.strip() or "unknown"
        return tuple(commits), revision, tuple(problems)


# A module-level adapter is the only place this source uses subprocess directly.  The
# caller supplies argv and cwd; no shell, interpolation or user text reaches the child.
def _run_git(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _labels(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        str(item.get("name"))
        for item in value
        if isinstance(item, Mapping) and isinstance(item.get("name"), str)
    )
