# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The nightly full CI run: its watermark, and one tracking issue while it is red (SP1-B Task 4).

A pull request into the integration branch runs only what its diff can affect, on a small
matrix. Every night CI runs the FULL matrix against the integration branch's tip instead, so
a row the pull-request tier dropped is still proven somewhere every day. Two things here keep
that run honest and cheap:

* **The watermark** (`last-green`). The nightly has nothing to prove when its commit is the
  head of the last GREEN scheduled run, so it skips (`CiAreas.unchanged` decides; this reads
  the commit). The watermark is a position in the data, the commit the forge recorded, never
  a time, and only a successful run moves it: a red or cancelled nightly leaves it where it
  was, so the next night runs again. Any doubt -- a forge that cannot be asked, a filter the
  API ignored, a value that is not a commit id -- answers no watermark, and the nightly runs.
* **The report** (`report`). A red nightly is said out loud in ONE issue, through the
  family's tracking-issue primitive (`vibey_gh.tracking_issue`): opened, or brought current
  with a comment once per red run, and closed by the next green nightly. A cancelled or
  skipped run proves nothing and changes nothing.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable, Sequence
from typing import Any
from urllib.parse import quote

from vibey_gh import github_state
from vibey_gh.failure_evidence import RED
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.ci_nightly_interface import CiNightlyInterface, NightlyVerdict
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.tracking_issue_interface import TrackingIssueInterface
from vibey_gh.tracking_issue import TrackingIssue

__all__ = ["CiNightly"]

_COMMIT = re.compile(r"[0-9a-f]{40}")
_WORKFLOWS = "/.github/workflows/"
_WORKFLOW_FILE = re.compile(r"[A-Za-z0-9._-]+\.ya?ml")
# How many failed jobs the issue's title names before it counts the rest; the body lists all.
_TITLE_JOBS = 5


class CiNightly(CiNightlyInterface):
    """Implements `CiNightlyInterface` over the forge's REST API."""

    def __init__(
        self,
        *,
        transport: GhTransportInterface | None = None,
        tracker: TrackingIssueInterface | None = None,
        repository: Callable[[], str] = github_state.repository,
    ) -> None:
        self._transport: GhTransportInterface = transport or GhTransport()
        self._tracker: TrackingIssueInterface = tracker or TrackingIssue(
            transport=self._transport, repository=repository
        )
        self._repository = repository

    @staticmethod
    def key(branch: str) -> str:
        """The tracking issue's key for the nightly on `branch`."""
        return f"red-nightly:{branch}"

    @staticmethod
    def workflow_file(workflow_ref: str) -> str:
        """The workflow's file name from `github.workflow_ref`
        (`owner/repo/.github/workflows/ci.yml@refs/heads/develop`), or "" when it names none."""
        path = workflow_ref.split("@", 1)[0]
        if _WORKFLOWS not in path:
            return ""
        name = path.split(_WORKFLOWS, 1)[1]
        return name if _WORKFLOW_FILE.fullmatch(name) else ""

    # ------------------------------------------------------------------ the watermark

    def last_green(self, workflow: str, branch: str, event: str) -> str:
        path = (
            f"repos/{self._repository()}/actions/workflows/{workflow}/runs"
            f"?branch={quote(branch, safe='')}&event={quote(event, safe='')}"
            "&status=success&per_page=1"
        )
        answer = self._transport.json(["api", path])
        runs = answer.get("workflow_runs") if isinstance(answer, dict) else None
        if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict):
            return ""
        run: dict[str, Any] = runs[0]
        # The filters are asked for and then checked: an API that ignored one must not hand
        # over a red run's, another branch's or another event's commit as the watermark.
        sha = str(run.get("head_sha") or "")
        vouched = (
            run.get("conclusion") == "success"
            and run.get("head_branch") == branch
            and run.get("event") == event
            and _COMMIT.fullmatch(sha) is not None
        )
        return sha if vouched else ""

    def run_last_green(self, *, workflow_ref: str, branch: str, event: str) -> int:
        """Print `last_green=<commit>` for $GITHUB_OUTPUT, empty on any doubt; always exit 0.

        An empty watermark runs the nightly, so a failure here costs a run, never a skip."""
        workflow = self.workflow_file(workflow_ref)
        sha = ""
        if not workflow:
            print(
                f"vibey-gh: ci-nightly: {workflow_ref!r} names no workflow file; "
                "no watermark, the nightly runs",
                file=sys.stderr,
            )
        else:
            try:
                sha = self.last_green(workflow, branch, event)
            except (RuntimeError, TypeError, ValueError) as exc:
                print(
                    f"vibey-gh: ci-nightly: {exc}; no watermark, the nightly runs",
                    file=sys.stderr,
                )
            else:
                if not sha:
                    print(
                        f"vibey-gh: ci-nightly: no green {event} run of {workflow} on {branch} "
                        "on record; the nightly runs",
                        file=sys.stderr,
                    )
        print(f"last_green={sha}")
        return 0

    # ------------------------------------------------------------------ the report

    def report(
        self,
        run_id: int,
        result: str,
        *,
        ignore: Sequence[str] = (),
        labels: Sequence[str] = (),
    ) -> NightlyVerdict:
        if result != "success" and result not in RED:
            return NightlyVerdict(
                "unknown",
                f"a {result or 'missing'} result proves neither red nor green; nothing changed",
            )
        repository = self._repository()
        run = self._transport.json(["api", f"repos/{repository}/actions/runs/{run_id}"])
        run = run if isinstance(run, dict) else {}
        branch = str(run.get("head_branch") or "")
        sha = str(run.get("head_sha") or "")
        url = str(run.get("html_url") or "")
        key = self.key(branch)
        if result == "success":
            closed = self._tracker.resolve(
                key, f"The nightly on `{branch}` is green again at {sha} ({url}). Closing."
            )
            return NightlyVerdict(
                "green", f"the nightly on {branch} is green at {sha[:12]}", closed
            )
        failed, problem = self._failed(repository, run_id, ignore)
        names = [str(job.get("name")) for job in failed]
        title = f"Nightly CI is red on {branch}"
        if names:
            shown = ", ".join(names[:_TITLE_JOBS])
            extra = len(names) - _TITLE_JOBS
            title += f": {shown}" + (f" and {extra} more" if extra > 0 else "")
        if problem:
            listed = f"- Failed jobs: unknown: the job list could not be read ({problem})"
        elif not names:
            listed = "- Failed jobs: no job reported a failure; read the run"
        else:
            listed = "- Failed jobs:\n" + "\n".join(self._job_line(job) for job in failed)
        body = (
            f"The scheduled full CI run on `{branch}` at {sha} is red.\n\n"
            f"- Run: {url}\n{listed}\n\n"
            "The nightly runs the full matrix that pull requests no longer run, so this may be "
            "a row no pull request exercised. This issue is kept by `vibey-gh ci-nightly "
            "report`: one issue while the nightly is red, a comment for each red run, closed "
            "by the next green nightly."
        )
        number, _ = self._tracker.raise_issue(
            key,
            title,
            body,
            event=f"Red at {sha[:12]}: {', '.join(names) or 'see the run'} — {url}",
            event_key=f"run-{run_id}",
            labels=labels,
        )
        return NightlyVerdict("red", title, number)

    @staticmethod
    def _job_line(job: dict[str, Any]) -> str:
        """One failed job as a list item, linked to its log when the forge gave a link."""
        name = job.get("name")
        url = job.get("html_url")
        return f"  - [{name}]({url})" if url else f"  - {name}"

    def _failed(
        self, repository: str, run_id: int, ignore: Sequence[str]
    ) -> tuple[list[dict[str, Any]], str]:
        """The run's failed jobs, in the order the forge lists them, or why they are unknown."""
        path = f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
        done = self._transport.run(["api", "--paginate", path, "--jq", ".jobs"])
        if done.returncode:
            return [], done.stderr.strip()
        return [
            job
            for job in TrackingIssue.decode_pages(done.stdout)
            if job.get("conclusion") in RED and job.get("name") not in ignore
        ], ""

    # ------------------------------------------------------------------ the command

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        actions = parser.add_subparsers(dest="nightly_action", required=True)
        last = actions.add_parser(
            "last-green", help="print last_green=<commit>: the last green scheduled run's head"
        )
        last.add_argument(
            "--workflow-ref",
            required=True,
            help="`github.workflow_ref`: owner/repo/.github/workflows/<file>@<ref>",
        )
        last.add_argument("--branch", required=True, help="the branch the nightly runs on")
        last.add_argument("--event", default="schedule", help="the event whose runs count")
        report = actions.add_parser(
            "report", help="open, update or close the tracking issue for a red nightly"
        )
        report.add_argument("--run-id", type=int, required=True, help="this workflow run")
        report.add_argument(
            "--result", required=True, help="the aggregate result: success, failure, ..."
        )
        report.add_argument(
            "--ignore-job", action="append", default=[], help="a job name not to list as failed"
        )
        report.add_argument("--label", action="append", default=[], help="an existing label")
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        nightly = cls()
        if args.nightly_action == "last-green":
            return nightly.run_last_green(
                workflow_ref=args.workflow_ref, branch=args.branch, event=args.event
            )
        try:
            verdict = nightly.report(
                args.run_id, args.result, ignore=args.ignore_job, labels=args.label
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            print(f"vibey-gh: {exc}")
            return 1
        issue = f" (#{verdict.issue})" if verdict.issue is not None else ""
        print(f"vibey-gh: {verdict.state} — {verdict.reason}{issue}")
        return 0
