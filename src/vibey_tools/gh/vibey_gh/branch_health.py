# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Say out loud, in one issue, when a permanent branch's CI goes red (`[branch_health]`).

develop was red from 2026-09-28 to 09-29 -- an orphaned figure pin -- and four pull
requests merged over a failing `gates` while nothing said so. A red push run is visible to
whoever opens the Actions tab, which is nobody who is not already looking.

`branch-health.yml` runs this after every completed CI run on a push to the integration or
release branch. The run is judged by its jobs that are REQUIRED checks for that branch
(`[rulesets.*] required_checks`, or `[branch_health] checks`): the definition of green the
repository already declared, rather than a second one invented here.

* **red** -- a watched job failed or timed out, or the run could not start: the branch's
  one tracking issue is opened, or brought current, and the run is noted on it once.
* **green** -- every watched job present succeeded (skipped ones prove nothing and are not
  counted): the open issue, if any, is closed with a note.
* **unknown** -- cancelled, still running, or no watched job in the run: nothing changes.

A run is judged only while its commit is still the branch's tip. An older run finishing
after a newer one would otherwise close an alert the newer run just raised, or reopen one
it just closed -- and that is what makes a replay of this job, or two runs racing, safe.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from vibey_gh import github_state
from vibey_gh.config import GhConfig, load_config
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.branch_health_interface import BranchHealthInterface, BranchHealthVerdict
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.tracking_issue_interface import TrackingIssueInterface
from vibey_gh.tracking_issue import TrackingIssue

__all__ = ["BranchHealth"]

RED = frozenset({"failure", "timed_out", "startup_failure"})
PROVEN = frozenset({"success"})
NEUTRAL = frozenset({"skipped", "neutral"})


class BranchHealth(BranchHealthInterface):
    """Implements `BranchHealthInterface`."""

    def __init__(
        self,
        *,
        config: Callable[[], GhConfig] = load_config,
        transport: GhTransportInterface | None = None,
        tracker: TrackingIssueInterface | None = None,
        repository: Callable[[], str] = github_state.repository,
    ) -> None:
        self._config = config
        self._transport: GhTransportInterface = transport or GhTransport()
        self._tracker: TrackingIssueInterface = tracker or TrackingIssue(
            transport=self._transport, repository=repository
        )
        self._repository = repository

    @staticmethod
    def key(branch: str) -> str:
        """The tracking issue's key for `branch`."""
        return f"red-branch:{branch}"

    def judge(
        self, jobs: Sequence[Mapping[str, Any]], watched: Sequence[str], run_conclusion: str
    ) -> tuple[str, tuple[str, ...]]:
        present = [job for job in jobs if job.get("name") in watched]
        failed = tuple(
            sorted({str(job["name"]) for job in present if job.get("conclusion") in RED})
        )
        if failed:
            return "red", failed
        if not jobs and run_conclusion in RED:
            # A workflow that could not start has no jobs to blame, and is still red.
            return "red", ()
        conclusions = {job.get("conclusion") for job in present}
        if conclusions & PROVEN and conclusions <= PROVEN | NEUTRAL:
            return "green", ()
        return "unknown", ()

    def report(self, run_id: int) -> BranchHealthVerdict:
        cfg = self._config()
        repository = self._repository()
        run = self._transport.json(["api", f"repos/{repository}/actions/runs/{run_id}"])
        branch = str(run.get("head_branch") or "")
        sha = str(run.get("head_sha") or "")
        url = str(run.get("html_url") or "")
        if not cfg.branch_health.enabled:
            return BranchHealthVerdict("ignored", "[branch_health] is disabled")
        policies = {
            cfg.integration_branch: cfg.rulesets.integration,
            cfg.release_branch: cfg.rulesets.release,
        }
        if branch not in policies or run.get("event") != "push":
            return BranchHealthVerdict(
                "ignored", f"a {run.get('event')} run on {branch or 'no branch'} is not watched"
            )
        tip = self._transport.json(["api", f"repos/{repository}/branches/{branch}"])
        if str((tip.get("commit") or {}).get("sha") or "") != sha:
            return BranchHealthVerdict(
                "ignored", f"{sha[:12]} is no longer the tip of {branch}; a newer run decides"
            )
        watched = cfg.branch_health.checks or policies[branch].required_checks
        jobs = self._jobs(repository, run_id)
        state, failed = self.judge(jobs, watched, str(run.get("conclusion") or ""))
        key = self.key(branch)
        if state == "red":
            named = ", ".join(failed) if failed else "the workflow could not start"
            title = f"{branch} is red: {named}"
            body = (
                f"The CI run on `{branch}` at {sha} is red: {named}.\n\n"
                f"- Run: {url}\n"
                f"- Watched checks: {', '.join(watched)}\n\n"
                "Pull requests merging now merge over a failing branch. This issue closes "
                "itself when a later run on the branch's tip is green (vibey-gh "
                "`[branch_health]`)."
            )
            number, _ = self._tracker.raise_issue(
                key,
                title,
                body,
                event=f"Red at {sha[:12]}: {named} — {url}",
                event_key=f"run-{run_id}",
                labels=cfg.branch_health.labels,
            )
            return BranchHealthVerdict("red", title, number)
        if state == "green":
            closed = self._tracker.resolve(
                key, f"`{branch}` is green again at {sha} ({url}). Closing."
            )
            return BranchHealthVerdict("green", f"{branch} is green at {sha[:12]}", closed)
        return BranchHealthVerdict(
            "unknown", f"the run at {sha[:12]} proves neither red nor green; nothing changed"
        )

    def _jobs(self, repository: str, run_id: int) -> list[dict[str, Any]]:
        path = f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
        run = self._transport.run(["api", "--paginate", path, "--jq", ".jobs"])
        if run.returncode:
            raise RuntimeError(f"gh api {path}: {run.stderr.strip()}")
        return TrackingIssue.decode_pages(run.stdout)

    # ------------------------------------------------------------------ the command

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "--run-id", type=int, required=True, help="the completed CI run to judge"
        )
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        try:
            verdict = cls().report(args.run_id)
        except (RuntimeError, TypeError, ValueError) as exc:
            print(f"vibey-gh: {exc}")
            return 1
        issue = f" (#{verdict.issue})" if verdict.issue is not None else ""
        print(f"vibey-gh: {verdict.state} — {verdict.reason}{issue}")
        return 0
