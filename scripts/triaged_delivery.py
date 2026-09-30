# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deliver ordered, triaged GitHub issues through Vibey's durable delivery queue.

A bounded bridge, one project at a time. Each pass:

1. With a ticket store (``VIBEY_PG_URL``): returns expired ticket leases to ``ready``, then
   reconciles the open triaged issues, retiring a claimable ticket whose issue was closed.
2. Resumes before it selects. A dispatched project that is DONE is published; one that can
   move is driven again (bounded); one waiting on a person -- an open human gate, or a design
   waiting for ``vibey design accept`` -- holds the slot, and the pass selects nothing new.
3. Only with nothing in flight does it take the next issue: claims it by an idempotent GitHub
   comment (and a ticket lease), creates the normal Vibey project, and drives the worker.

Before it dispatches an issue it asks whose words the issue carries and who applied the labels
that queued it (`scripts/intake_trust.py`, the storm's own trust seam): an issue a stranger
wrote, edited or labelled is held for a person -- its ticket blocked, the reason recorded, and
one comment on the issue -- and never dispatched. An admitted issue reaches ``vibey new
--intake`` only quoted through PromptShield, so DESIGN reads it as data.

It never answers a human gate on a person's behalf unless told to. DESIGN interview gates
stay parked for a person by default; ``--answer-design-defaults`` (or
``VIBEY_TRIAGED_DELIVERY_ANSWER_DESIGN_DEFAULTS=1``) is the explicit opt-in to answer them
with their declared defaults and accept the design, and every such answer is recorded under
``--answer-by`` (``automation:triaged-delivery``), never under the account running it. Every
project it creates declares ``--design-default-scope narrowest``, so a declared default is
the answer that adds the least work beyond the issue, never the model's appetite. Likewise
a DESIGN research topic the provider cannot evidence parks a ``research_evidence`` gate for a
person by default; ``--record-research-gaps`` (or
``VIBEY_TRIAGED_DELIVERY_RECORD_RESEARCH_GAPS=1``) is the explicit opt-in to run the worker
with ``[design.research] on_unavailable = "record_gap"``, so such a topic is recorded as not
researched -- in the ledger and in the spec -- instead of invented or waited on. It
never edits a branch or routes around a gate: a finished project is pushed through the push
gate and opened as a draft pull request, which the PR automation promotes and the merge train
lands. Run with ``--once``, or ``--interval SECONDS`` for a local supervisor loop.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.intake_trust import IntakeFrame, IntakeTrust, Untrusted
    from scripts.interfaces.intake_trust_interface import (
        IntakeFrameInterface,
        IntakeTrustInterface,
    )
    from scripts.interfaces.triage_queue_interface import (
        ForgeInterface,
        TicketSourceInterface,
        TicketStoreInterface,
    )
    from scripts.interfaces.triaged_delivery_interface import (
        CommandResultInterface,
        CommandRunnerInterface,
        DeliveryEvidenceInterface,
    )
    from scripts.triage_queue import GhCli, GithubTicketSource, TriageQueue
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from intake_trust import (  # type: ignore[import-not-found,no-redef]
        IntakeFrame,
        IntakeTrust,
        Untrusted,
    )
    from interfaces.intake_trust_interface import (  # type: ignore[import-not-found,no-redef]
        IntakeFrameInterface,
        IntakeTrustInterface,
    )
    from interfaces.triage_queue_interface import (  # type: ignore[import-not-found,no-redef]
        ForgeInterface,
        TicketSourceInterface,
        TicketStoreInterface,
    )
    from interfaces.triaged_delivery_interface import (  # type: ignore[import-not-found,no-redef]
        CommandResultInterface,
        CommandRunnerInterface,
        DeliveryEvidenceInterface,
    )
    from triage_queue import (  # type: ignore[import-not-found,no-redef]
        GhCli,
        GithubTicketSource,
        TriageQueue,
    )

PRIORITIES = ("critical", "high", "medium", "low")
TRIAGED = "vibey-gh:triaged"
BUMPED = "vibey-gh:priority-bumped"
MARKER = "<!-- vibey-delivery-dispatch issue:{number} -->"
PUBLISHED_MARKER = "<!-- vibey-delivery-published issue:{number} -->"
HELD_MARKER = "<!-- vibey-delivery-held issue:{number} -->"
EVIDENCE_DIR = ".vibey/delivery-evidence"
DESIGN_QUESTION_KINDS = frozenset(
    {
        "context_free",
        "job_story",
        "laddering",
        "example_mapping",
        "walking_skeleton",
        "nfr_planguage",
        "premortem",
    }
)
# `queue_depth` states of a job that has not settled. While any DESIGN job is one of these
# the spec is not finished -- the interview's completion only queues research, synthesis
# and spec -- so the design is not ready to accept (`vibey design accept` refuses too).
UNSETTLED_JOB_STATES = ("ready", "leased", "awaiting_human", "awaiting_capacity")
# Outcomes after which the worker demonstrably ran a job or a job parked on a person: a
# lease left behind by a timed-out worker is no longer the thing holding the project up.
PROGRESS = frozenset({"done", "parked_at_gate", "worker_progress", "design_awaiting_acceptance"})
ENV = "VIBEY_TRIAGED_DELIVERY_"
# The worker's own `[design.research] on_unavailable` overlay (infrastructure/config_loader.py),
# set for the worker only when the bridge's `record_research_gaps` opt-in is on.
RESEARCH_POLICY_ENV = "VIBEY_DESIGN_RESEARCH_ON_UNAVAILABLE"
RECORD_GAP = "record_gap"
TRUE = frozenset({"1", "true", "yes", "on"})
FALSE = frozenset({"0", "false", "no", "off"})


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    bumped: bool
    priority: str
    created_at: str

    @property
    def rank(self) -> tuple[int, int, str, int]:
        return (
            0 if self.bumped else 1,
            PRIORITIES.index(self.priority),
            self.created_at,
            self.number,
        )


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class BridgeSettings:
    """Every knob the bridge has. Each one is a flag and an environment variable."""

    repo: Path
    repository: str = "the-vibey-project/vibey"
    database_url: str | None = None
    answer_design_defaults: bool = False
    # Off: a research topic with no evidence parks for a person. On: the worker records it
    # as not researched and DESIGN goes on. Never a fabricated source either way.
    record_research_gaps: bool = False
    answer_by: str = "automation:triaged-delivery"
    draft: bool = True
    base: str = "develop"
    provider: str = "gptossloop"
    vibey: tuple[str, ...] = ("uv", "run", "vibey")
    worker_timeout: float = 900.0
    max_steps: int = 100
    lease_seconds: int = 900
    owner: str = "triaged-delivery"
    branch_prefix: str = "delivery"
    max_dispatch_failures: int = 3
    storm_home: Path = Path.home() / "git" / "vibey-storm"
    push_gate: str = ""
    # Whose words may direct a delivery, and who may queue one. Empty: the lists the
    # repository declares in reviewed history -- `[unattended_approval] authors`, and those
    # plus `[merge_train] trusted_authors` and `owner` for the labels. A list given here
    # replaces the declared one (scripts/intake_trust.py).
    trusted_authors: tuple[str, ...] = ()
    label_curators: tuple[str, ...] = ()

    @classmethod
    def from_environ(cls, repo: Path, environ: Mapping[str, str]) -> BridgeSettings:
        default = cls(repo=repo)

        def logins(name: str) -> tuple[str, ...]:
            return tuple(environ.get(ENV + name, "").replace(",", " ").split())

        def flag(name: str, fallback: bool) -> bool:
            value = environ.get(ENV + name)
            if value is None or not value.strip():
                return fallback
            lowered = value.strip().lower()
            if lowered in TRUE:
                return True
            if lowered in FALSE:
                return False
            raise ValueError(f"{ENV}{name} must be one of 1/0, true/false, yes/no, on/off")

        return cls(
            repo=repo,
            repository=environ.get("VIBEY_GITHUB_REPOSITORY", default.repository),
            database_url=environ.get("VIBEY_PG_URL") or None,
            answer_design_defaults=flag("ANSWER_DESIGN_DEFAULTS", default.answer_design_defaults),
            record_research_gaps=flag("RECORD_RESEARCH_GAPS", default.record_research_gaps),
            answer_by=environ.get(ENV + "ANSWER_BY", default.answer_by),
            draft=flag("DRAFT", default.draft),
            base=environ.get(ENV + "BASE", default.base),
            provider=environ.get(ENV + "PROVIDER", default.provider),
            vibey=tuple(shlex.split(environ[ENV + "VIBEY"]))
            if environ.get(ENV + "VIBEY")
            else default.vibey,
            worker_timeout=float(environ.get(ENV + "WORKER_TIMEOUT", default.worker_timeout)),
            max_steps=int(environ.get(ENV + "MAX_STEPS", default.max_steps)),
            lease_seconds=int(environ.get(ENV + "LEASE_SECONDS", default.lease_seconds)),
            owner=environ.get(ENV + "OWNER", default.owner),
            branch_prefix=environ.get(ENV + "BRANCH_PREFIX", default.branch_prefix),
            max_dispatch_failures=int(
                environ.get(ENV + "MAX_DISPATCH_FAILURES", default.max_dispatch_failures)
            ),
            storm_home=Path(environ.get("VIBEY_STORM_HOME", str(default.storm_home))).expanduser(),
            push_gate=environ.get(
                "VIBEY_PUSH_GATE",
                str(repo / "docs" / "plans" / "qwenstorm-3.0.0" / "tools" / "push_gate.py"),
            ),
            trusted_authors=logins("TRUSTED_AUTHORS"),
            label_curators=logins("LABEL_CURATORS"),
        )


class SubprocessRunner:
    """Commands as child processes. Declared by `CommandRunnerInterface`.

    With a timeout the child runs in its own session, so a stop reaches the whole tree it
    started (a worker's engine and model processes), not just the child."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> CommandResultInterface:
        child_env = None if env is None else {**os.environ, **env}
        if timeout is None:
            done = subprocess.run(
                list(argv), capture_output=True, text=True, check=False, cwd=cwd, env=child_env
            )
            return CommandResult(done.returncode, done.stdout, done.stderr)
        process = subprocess.Popen(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=child_env,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._terminate(process)
            stdout, stderr = process.communicate()
            return CommandResult(process.returncode, stdout, stderr, timed_out=True)
        return CommandResult(process.returncode, stdout, stderr)

    def _descendants(self, pid: int) -> list[int]:
        try:
            children = subprocess.run(
                ["pgrep", "-P", str(pid)], capture_output=True, text=True, check=False
            ).stdout.split()
        except OSError:  # no pgrep, or not allowed to run it: the process group still goes
            return []
        result = [int(child) for child in children]
        return result + [grandchild for child in result for grandchild in self._descendants(child)]

    def _terminate(self, process: subprocess.Popen[str]) -> None:
        # The child leads its own session, so its process group is everything it started
        # that did not leave it; the descendant walk below catches the ones that did.
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGTERM)
        for pid in reversed(self._descendants(process.pid)):
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGTERM)
        with contextlib.suppress(ProcessLookupError):
            os.kill(process.pid, signal.SIGTERM)
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=2)
        if process.poll() is None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGKILL)
            for pid in reversed(self._descendants(process.pid)):
                with contextlib.suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
            with contextlib.suppress(ProcessLookupError):
                os.kill(process.pid, signal.SIGKILL)


class DeliveryEvidence:
    """The latest observed facts, one JSON file per project and per ticket. Declared by
    `DeliveryEvidenceInterface`. It records what was seen; it never manufactures completion."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def project(self, project_id: str, **values: object) -> None:
        self._merge(self._root / f"{project_id}.json", values)

    def ticket(self, issue_number: int, **values: object) -> None:
        self._merge(self._root / f"ticket-{issue_number}.json", values)

    def last_project(self, project_id: str) -> dict[str, object]:
        return self._read(self._root / f"{project_id}.json")

    def last_ticket(self, issue_number: int) -> dict[str, object]:
        return self._read(self._root / f"ticket-{issue_number}.json")

    def _read(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}

    def _merge(self, path: Path, values: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        prior = self._read(path)
        prior.update(values)
        prior["updated_at"] = time.time()
        path.write_text(json.dumps(prior, indent=2, sort_keys=True, default=str) + "\n")


class DeliveryBridge:
    """One triaged issue at a time, from dispatch to a published pull request. Declared by
    `DeliveryBridgeInterface`."""

    def __init__(
        self,
        settings: BridgeSettings,
        *,
        forge: ForgeInterface,
        runner: CommandRunnerInterface,
        evidence: DeliveryEvidenceInterface,
        trust: IntakeTrustInterface,
        frame: IntakeFrameInterface | None = None,
        store: TicketStoreInterface | None = None,
        source: TicketSourceInterface | None = None,
    ) -> None:
        if (store is None) != (source is None):
            raise ValueError("a ticket store and a ticket source come together or not at all")
        self._settings = settings
        self._forge = forge
        self._runner = runner
        self._evidence = evidence
        # Required, never defaulted: a bridge that could be built without it would be a
        # bridge that dispatches whoever wrote the issue (G10).
        self._trust = trust
        self._frame = frame or IntakeFrame()
        self._store = store
        self._source = source

    @classmethod
    def production(cls, settings: BridgeSettings) -> DeliveryBridge:
        forge = GhCli()
        store: TicketStoreInterface | None = None
        source: TicketSourceInterface | None = None
        if settings.database_url:
            store = TriageQueue(settings.database_url, settings.repository)
            source = GithubTicketSource(settings.repository, forge)
        trust = IntakeTrust.production(
            repo=settings.repo,
            repository=settings.repository,
            tools=Path(settings.push_gate).parent,
            authors=settings.trusted_authors,
            curators=settings.label_curators,
        )
        return cls(
            settings,
            forge=forge,
            runner=SubprocessRunner(),
            evidence=DeliveryEvidence(settings.repo / EVIDENCE_DIR),
            trust=trust,
            store=store,
            source=source,
        )

    # -- the pass ------------------------------------------------------------------------

    def run_once(self) -> int:
        issue_list: list[Issue] | None = None
        if self._store is not None and self._source is not None:
            reaped = self._store.reap()
            if reaped:
                print(f"reaped {reaped} expired ticket lease(s) back to ready")
            listing = self._source.tickets()
            retired = self._store.reconcile(listing.tickets, complete=listing.complete)
            for number in retired:
                self._evidence.ticket(
                    number,
                    outcome="retired",
                    state="blocked",
                    reason="the issue is no longer open with the triaged label",
                )
                print(f"retired #{number}: no longer an open triaged issue")
            if not listing.complete:
                print("the triaged listing reached its limit; no ticket retired this pass")
            in_flight = self._in_flight_from_store()
        else:
            issue_list = self.issues()
            in_flight = self._in_flight_from_markers(issue_list)
        for issue, project_id in in_flight:
            if self._settle(issue, project_id):
                return 0
        return self._start_next(issue_list)

    def _settle(self, issue: Issue, project_id: str) -> bool:
        """Deal with one dispatched project. True when it holds the one active slot."""
        status = self._status(project_id)
        phase = status.get("phase")
        if phase == "done":
            self._finish(issue, project_id)
            return False
        if phase == "abandoned":
            self._evidence.project(project_id, outcome="abandoned", status=status)
            if self._store is not None:
                self._store.set_state(issue.number, "blocked", project_id=project_id)
                self._evidence.ticket(
                    issue.number, outcome="blocked", reason="project abandoned", project=project_id
                )
            return False
        if phase is None:
            self._evidence.project(project_id, outcome="status_unreadable")
            print(f"project {project_id} status unreadable; waiting before selecting another")
            return True
        outcome = self._resume(project_id)
        if outcome == "done":
            self._finish(issue, project_id)
        return True

    def _resume(self, project_id: str) -> str:
        if self._evidence.last_project(project_id).get("reap_pending"):
            reap = self._runner.run(
                [*self._settings.vibey, "queue", "reap", "--project", project_id]
            )
            self._evidence.project(
                project_id,
                queue_reap_returncode=reap.returncode,
                queue_reap_output=(reap.stdout + reap.stderr).strip(),
            )
        outcome = self.drive(project_id)
        if outcome in PROGRESS:
            self._evidence.project(project_id, reap_pending=False)
        return outcome

    def _start_next(self, issue_list: list[Issue] | None) -> int:
        if self._store is not None:
            claimed = self._store.claim(self._settings.owner, self._settings.lease_seconds)
            if claimed is None:
                print("no claimable triaged ticket in PostgreSQL")
                return 1
            issue = Issue(
                number=int(str(claimed["issue_number"])),
                title=str(claimed["title"]),
                body=str(claimed["body"]),
                bumped=False,
                priority=PRIORITIES[int(str(claimed["priority_rank"]))],
                created_at="",
            )
            existing = self.dispatched_project(issue.number)
            if existing is not None and self._status(existing).get("phase") == "abandoned":
                # An abandoned project blocks its ticket (`_settle`), and nothing but an
                # operator moves a blocked ticket back to ready -- `reconcile` never
                # touches state. A ready ticket whose latest project was abandoned is
                # therefore a retry the operator asked for: dispatch a fresh project,
                # never re-adopt the dead one. An unreadable status is not "abandoned",
                # so it still adopts rather than risk dispatching the issue twice.
                self._evidence.ticket(
                    issue.number, outcome="redispatch_after_abandon", abandoned=existing
                )
                print(f"#{issue.number}: project {existing} was abandoned; dispatching afresh")
                existing = None
            if existing is not None:
                # Dispatched by an earlier pass whose ticket never left its lease: adopt the
                # project instead of dispatching the issue twice.
                self._store.set_state(issue.number, "dispatched", project_id=existing)
                self._evidence.ticket(issue.number, outcome="adopted", project=existing)
                print(f"adopted #{issue.number} -> existing project {existing}")
                return 0
        else:
            assert issue_list is not None
            candidate = next(
                (
                    i
                    for i in issue_list
                    if self.dispatched_project(i.number) is None and not self._held(i.number)
                ),
                None,
            )
            if candidate is None:
                print("no eligible triaged issue without a dispatch marker")
                return 1
            issue = candidate
        try:
            project_id = self.dispatch(issue)
        except Untrusted as refused:
            self._hold(issue, refused)
            return 0
        except Exception as exc:
            self._dispatch_failed(issue, exc)
            raise
        if self._store is not None:
            self._store.set_state(issue.number, "dispatched", project_id=project_id)
        print(f"dispatched #{issue.number} ({issue.priority}) -> project {project_id}")
        if self.drive(project_id) == "done":
            self._finish(issue, project_id)
        return 0

    def _dispatch_failed(self, issue: Issue, exc: Exception) -> None:
        failures = int(str(self._evidence.last_ticket(issue.number).get("dispatch_failures", 0)))
        failures += 1
        self._evidence.ticket(
            issue.number, outcome="dispatch_failed", error=str(exc), dispatch_failures=failures
        )
        if self._store is None:
            return
        if failures >= self._settings.max_dispatch_failures:
            self._store.set_state(issue.number, "blocked")
            print(f"#{issue.number} blocked after {failures} failed dispatches")
        else:
            # Handed back now rather than left leased: the next pass retries it.
            self._store.release(issue.number)

    def _hold(self, issue: Issue, refused: Untrusted) -> None:
        """A stranger wrote, edited or labelled the issue: never dispatched, and a person is
        asked, once. Sticky by design -- the history that refused it does not change."""
        self._evidence.ticket(
            issue.number,
            outcome="held_untrusted",
            state="blocked",
            reason=refused.reason,
            accounts=list(refused.accounts),
            grant=refused.grant,
        )
        if self._store is not None:
            self._store.set_state(issue.number, "blocked")
        if not self._held(issue.number):
            self._forge.gh(
                "issue",
                "comment",
                str(issue.number),
                "--body",
                f"{HELD_MARKER.format(number=issue.number)}\n\n"
                "Vibey's triaged delivery is holding this issue for a maintainer and has not "
                f"dispatched it: {refused.reason}.\n\n"
                "The delivery bridge dispatches an issue only when its author, everyone who "
                "edited it, and whoever applied its triage labels are named in the trust grant "
                f"this repository declares in reviewed history ({refused.grant}). To go ahead, "
                "a maintainer can review the request and re-file it under their own account, "
                "or name the account in a reviewed change to `.vibey-gh.toml`.",
            )
        print(f"held #{issue.number}: {refused.reason}")

    def _finish(self, issue: Issue, project_id: str) -> None:
        pull_request = self.publish(project_id, issue.number, issue.title)
        if pull_request is None:
            return
        if not self._published(issue.number):
            marker = PUBLISHED_MARKER.format(number=issue.number)
            self._forge.gh(
                "issue",
                "comment",
                str(issue.number),
                "--body",
                f"{marker}\n\nDelivery PR: {pull_request}",
            )
        if self._store is not None:
            self._store.set_state(issue.number, "completed", project_id=project_id)

    # -- what is in flight ---------------------------------------------------------------

    def _in_flight_from_store(self) -> list[tuple[Issue, str]]:
        assert self._store is not None
        result: list[tuple[Issue, str]] = []
        for row in self._store.in_flight():
            number = int(str(row["issue_number"]))
            project_id = row.get("project_id") or self.dispatched_project(number)
            issue = Issue(
                number=number,
                title=str(row["title"]),
                body=str(row["body"]),
                bumped=False,
                priority=PRIORITIES[int(str(row["priority_rank"]))],
                created_at="",
            )
            if project_id is None:
                self._evidence.ticket(
                    number, outcome="dispatched_without_project", reason="no project recorded"
                )
                continue
            result.append((issue, str(project_id)))
        return result

    def _in_flight_from_markers(self, issue_list: list[Issue]) -> list[tuple[Issue, str]]:
        result: list[tuple[Issue, str]] = []
        for issue in issue_list:
            project_id = self.dispatched_project(issue.number)
            if project_id is not None and not self._published(issue.number):
                result.append((issue, project_id))
        return result

    # -- GitHub --------------------------------------------------------------------------

    def issues(self) -> list[Issue]:
        raw = json.loads(
            self._forge.gh(
                "issue",
                "list",
                "--state",
                "open",
                "--label",
                TRIAGED,
                "--limit",
                "1000",
                "--json",
                "number,title,body,labels,createdAt",
            )
        )
        result: list[Issue] = []
        for item in raw:
            labels = {label["name"] for label in item.get("labels", [])}
            priority = next(
                (value for value in PRIORITIES if f"vibey-gh:priority-{value}" in labels),
                "low",
            )
            result.append(
                Issue(
                    number=int(item["number"]),
                    title=str(item.get("title") or ""),
                    body=str(item.get("body") or ""),
                    bumped=BUMPED in labels,
                    priority=priority,
                    created_at=str(item.get("createdAt") or ""),
                )
            )
        return sorted(result, key=lambda issue: issue.rank)

    def _comments(self, number: int) -> str:
        return self._forge.gh(
            "issue",
            "view",
            str(number),
            "--json",
            "comments",
            "--jq",
            '[.comments[].body] | join("\\n")',
        )

    def dispatched_project(self, number: int) -> str | None:
        """The project the LATEST dispatch marker names. An issue re-dispatched after its
        project was abandoned carries one marker per dispatch; the first names the dead
        project, so reading it would re-adopt what the operator abandoned."""
        found = re.findall(
            rf"{re.escape(MARKER.format(number=number))}.*?project `([0-9a-f-]{{36}})`",
            self._comments(number),
            re.DOTALL,
        )
        return str(found[-1]) if found else None

    def _published(self, number: int) -> bool:
        return PUBLISHED_MARKER.format(number=number) in self._comments(number)

    def _held(self, number: int) -> bool:
        return HELD_MARKER.format(number=number) in self._comments(number)

    def dispatch(self, issue: Issue) -> str:
        """Admit, frame, create. The trust check is here, not in the caller, so nothing --
        a pass, a test, a later caller -- can dispatch an issue it did not pass. The text
        dispatched is the text judged, never `issue.body` (the listing's copy)."""
        verdict = self._trust.admit(issue.number)
        self._evidence.ticket(
            issue.number,
            outcome="admitted",
            author=verdict.author,
            accounts=list(verdict.accounts),
            curators=list(verdict.curators),
            grant=verdict.grant,
            injection_heuristic=self._frame.suspicious(verdict),
        )
        marker = MARKER.format(number=issue.number)
        worktree = self._worktree(issue)
        output = self._runner.run(
            [
                *self._settings.vibey,
                "new",
                self._frame.name(verdict),
                "--repo",
                str(worktree),
                "--intake",
                self._frame.text(self._settings.repository, verdict),
                # Not a setting, on purpose. `--answer-design-defaults` accepts every
                # declared default unattended, and a default the model wrote is the
                # model's appetite: live on #998 a README insertion grew a script, tests
                # and a CI step, and the CI change ends at a person. Narrowest is the only
                # scope under which accepting defaults unattended stays bounded, so a key
                # that could widen it would be a key that removes the bound (12.d).
                "--design-default-scope",
                "narrowest",
            ]
        )
        if output.returncode:
            raise RuntimeError(output.stderr.strip() or output.stdout.strip() or "vibey new failed")
        match = re.search(r"project ([0-9a-f-]{36})", output.stdout)
        if match is None:
            raise RuntimeError(f"vibey new returned no project id: {output.stdout.strip()}")
        project_id = match.group(1)
        self._forge.gh(
            "issue",
            "comment",
            str(issue.number),
            "--body",
            f"{marker}\n\nVibey delivery dispatched: project `{project_id}`. DESIGN is queued; "
            "BUILD and REVIEW remain governed by the normal phase gates.",
        )
        return project_id

    def _worktree(self, issue: Issue) -> Path:
        """The checkout a fresh delivery starts from: detached at `base` as it is now.

        Only `dispatch` calls this, and only for an issue with no project yet, so a
        checkout already there is the leftover of an earlier dispatch that failed before
        vibey recorded a project. It may be far behind `base`, and BUILD cuts every new
        branch from this checkout's HEAD -- so it is moved to the current base when it is
        clean, and refused when it is not, never used as found."""
        target = self._settings.storm_home / f"triaged-{issue.number}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not (target / ".git").exists():
            added = self._runner.run(
                ["git", "worktree", "add", "--detach", str(target), self._settings.base],
                cwd=self._settings.repo,
            )
            if added.returncode:
                raise RuntimeError(added.stderr.strip() or "git worktree add failed")
            return target
        base = self._git_line(
            ["git", "-C", str(self._settings.repo), "rev-parse", "--verify"]
            + [f"{self._settings.base}^{{commit}}"]
        )
        if self._git_line(["git", "-C", str(target), "rev-parse", "--verify", "HEAD"]) == base:
            return target
        dirty = self._runner.run(["git", "-C", str(target), "status", "--porcelain"])
        if dirty.returncode or dirty.stdout.strip():
            raise RuntimeError(
                f"{target} is not at {self._settings.base} ({base}) and is not clean; "
                "refusing to start a fresh delivery on it"
            )
        moved = self._runner.run(
            ["git", "-C", str(target), "checkout", "--quiet", "--detach", base]
        )
        if moved.returncode:
            raise RuntimeError(moved.stderr.strip() or f"could not move {target} to {base}")
        return target

    def _git_line(self, argv: list[str]) -> str:
        """One line of a git command's output; a failure raises rather than reads as ''."""
        result = self._runner.run(argv)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "failed: " + " ".join(argv))
        return result.stdout.strip()

    # -- Vibey ---------------------------------------------------------------------------

    def _json(self, *args: str) -> dict[str, object]:
        result = self._runner.run([*self._settings.vibey, *args])
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "command failed: vibey " + " ".join(args))
        value = json.loads(result.stdout or "{}")
        if not isinstance(value, dict):
            raise RuntimeError("command did not return a JSON object: vibey " + " ".join(args))
        return value

    def _status(self, project_id: str) -> dict[str, object]:
        """The status document, or {} when it cannot be read -- never a guess."""
        try:
            return self._json("status", project_id, "--json")
        except (RuntimeError, json.JSONDecodeError):
            return {}

    def _observe(self, project_id: str) -> tuple[dict[str, object], list[dict[str, object]]]:
        status = self._json("status", project_id, "--json")
        raw_gates = self._json("gates", project_id, "--json").get("gates", [])
        gates = (
            [gate for gate in raw_gates if isinstance(gate, dict)]
            if isinstance(raw_gates, list)
            else []
        )
        cost = self._runner.run([*self._settings.vibey, "cost", project_id])
        self._evidence.project(
            project_id,
            status=status,
            gates=gates,
            cost=(cost.stdout + cost.stderr).strip(),
            review_observed=status.get("phase") in {"review", "done"},
        )
        return status, gates

    @staticmethod
    def _capacity_blocked(status: Mapping[str, object]) -> bool:
        queue = status.get("queue_depth")
        if isinstance(queue, dict) and int(queue.get("awaiting_capacity", 0)) > 0:
            return True
        circuits = status.get("circuits")
        if not isinstance(circuits, list):
            return False
        return any(
            isinstance(circuit, dict)
            and circuit.get("capacity_state") not in (None, "closed", "available")
            for circuit in circuits
        )

    @staticmethod
    def _unsettled_jobs(status: Mapping[str, object]) -> int:
        """Jobs the project still has in flight, from its status document."""
        queue = status.get("queue_depth")
        if not isinstance(queue, dict):
            return 0
        return sum(int(queue.get(state, 0)) for state in UNSETTLED_JOB_STATES)

    @staticmethod
    def _is_design_gate(gate: Mapping[str, object]) -> bool:
        return (
            str(gate.get("kind", "")) == "question"
            and str(gate.get("prompt", "")).split(":", 1)[0] in DESIGN_QUESTION_KINDS
        )

    def _worker(self, project_id: str) -> CommandResultInterface:
        env = None
        if self._settings.record_research_gaps:
            # The opt-in only, and said in the evidence: a spec that states research gaps
            # was produced under this policy, not by a person choosing to skip the reading.
            env = {RESEARCH_POLICY_ENV: RECORD_GAP}
            self._evidence.project(project_id, design_research_on_unavailable=RECORD_GAP)
        return self._runner.run(
            [
                *self._settings.vibey,
                "worker",
                "--once",
                "--project",
                project_id,
                "--provider",
                self._settings.provider,
            ],
            timeout=self._settings.worker_timeout,
            env=env,
        )

    def _answer_design(self, project_id: str, gates: list[dict[str, object]]) -> None:
        """The opt-in only: each DESIGN question answered with its declared defaults, under
        the automation's own name so the record never reads as a person's answer."""
        answered: list[str] = []
        for gate in gates:
            gate_id = str(gate["gate_id"])
            result = self._runner.run(
                [
                    *self._settings.vibey,
                    "answer",
                    gate_id,
                    "--defaults",
                    "--by",
                    self._settings.answer_by,
                ]
            )
            if result.returncode == 3:  # answered by someone else meanwhile; theirs stands
                continue
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or f"vibey answer {gate_id} failed")
            answered.append(gate_id)
        self._evidence.project(
            project_id, design_answered_by=self._settings.answer_by, design_answered=answered
        )

    def drive(self, project_id: str) -> str:
        """Run the worker until the project waits on a person, capacity, or a step's end.

        DESIGN gates stay parked for a person unless `answer_design_defaults` is set, and so
        does the design's acceptance. The returned outcome is also recorded as evidence."""
        worker_ran = False
        worker_returncode = 0
        for _ in range(self._settings.max_steps):
            status, gates = self._observe(project_id)
            phase = status.get("phase")
            if self._capacity_blocked(status):
                self._evidence.project(project_id, outcome="awaiting_capacity", status=status)
                print(f"project {project_id} paused: capacity evidence requires retry")
                return "awaiting_capacity"
            if phase in {"done", "abandoned"}:
                self._evidence.project(project_id, outcome=str(phase))
                return str(phase)
            design = [gate for gate in gates if self._is_design_gate(gate)]
            if design and len(design) == len(gates) and self._settings.answer_design_defaults:
                self._answer_design(project_id, design)
                worker_ran = False
                continue
            if gates:
                self._evidence.project(
                    project_id,
                    outcome="parked_at_gate",
                    parked_gates=[str(gate.get("gate_id")) for gate in gates],
                    design_gates_left_for_a_person=len(design),
                )
                print(f"project {project_id} parked at {len(gates)} human gate(s)")
                return "parked_at_gate"
            if worker_ran:
                if worker_returncode != 0:
                    self._evidence.project(
                        project_id, outcome="worker_failed", worker_returncode=worker_returncode
                    )
                    return "worker_failed"
                if phase == "design" and (unsettled := self._unsettled_jobs(status)):
                    # The design chain is still running: work it on the next pass, and
                    # never accept a spec its synthesis has not written yet.
                    self._evidence.project(
                        project_id,
                        outcome="worker_progress",
                        design_jobs_unsettled=unsettled,
                        status=status,
                    )
                    return "worker_progress"
                if phase == "design":
                    outcome = self._design_without_gate(project_id)
                    if outcome != "design_accepted":
                        return outcome
                    worker_ran = False
                    continue
                self._evidence.project(project_id, outcome="worker_progress", status=status)
                return "worker_progress"
            result = self._worker(project_id)
            if result.timed_out:
                print(
                    f"project {project_id} worker exceeded {self._settings.worker_timeout:g}s; "
                    "its job lease is left to expire, and the next pass runs `vibey queue "
                    "reap` for this project before it drives it again"
                )
                self._evidence.project(
                    project_id, outcome="worker_timeout", capacity_safe=True, reap_pending=True
                )
                return "worker_timeout"
            worker_ran = True
            worker_returncode = result.returncode
        raise RuntimeError(f"project {project_id} exceeded dispatch step limit")

    def _design_without_gate(self, project_id: str) -> str:
        """DESIGN with no open gate after a worker run: the spec waits on `design accept`."""
        if not self._settings.answer_design_defaults:
            self._evidence.project(
                project_id,
                outcome="design_awaiting_acceptance",
                next=f"a person runs `vibey design accept {project_id}` once the spec is ready",
            )
            print(f"project {project_id} design is waiting for a person to accept it")
            return "design_awaiting_acceptance"
        accepted = self._runner.run([*self._settings.vibey, "design", "accept", project_id])
        if accepted.returncode:
            self._evidence.project(
                project_id,
                outcome="design_accept_refused",
                error=(accepted.stderr or accepted.stdout).strip(),
            )
            return "design_accept_refused"
        print(accepted.stdout.strip())
        self._evidence.project(project_id, design_accepted_by=self._settings.answer_by)
        return "design_accepted"

    # -- publication ---------------------------------------------------------------------

    def publish(self, project_id: str, issue_number: int, title: str) -> str | None:
        """Publish the project's integration branch once the project is DONE."""
        status = self._json("status", project_id, "--json")
        if status.get("phase") != "done":
            self._evidence.project(project_id, outcome="not_done", status=status)
            return None
        # The branch is the one vibey names for this project, read from its status rather
        # than rebuilt here: a cycle-keyed `vibey/<cycle>/integration` is shared by every
        # project in the repository, and this bridge's worktrees share the main checkout's
        # refs, so rebuilding the name is how one delivery would publish another's history.
        branch = status.get("integration_branch")
        if not isinstance(branch, str) or not branch:
            raise RuntimeError(
                f"project {project_id} status names no integration branch; refusing to guess one"
            )
        worktree = Path(str(status["repo_path"]))
        listed = self._runner.run(["git", "-C", str(worktree), "worktree", "list", "--porcelain"])
        if listed.returncode:
            raise RuntimeError(listed.stderr.strip() or "git worktree list failed")
        match = re.search(
            rf"worktree (.+)\nHEAD [^\n]+\nbranch refs/heads/{re.escape(branch)}",
            listed.stdout,
        )
        if match is None:
            raise RuntimeError(f"project {project_id} has no integration worktree for {branch}")
        integration_path = Path(match.group(1))
        # The name alone is not the proof: BUILD records, beside every branch it creates,
        # the project that created it. A branch that does not name this project is not
        # this project's delivery, whatever it is called, and is never pushed as one.
        owner = self._runner.run(
            [
                "git",
                "-C",
                str(worktree),
                "config",
                "--local",
                "--get",
                f"branch.{branch}.vibey-project",
            ]
        )
        if owner.returncode or owner.stdout.strip() != project_id:
            raise RuntimeError(
                f"refusing to publish {branch}: it does not record project {project_id} "
                "as its creator"
            )
        # The remote branch names the issue and the project, so two deliveries never
        # collide on one remote name, and a second project never finds the first one's
        # pull request and is marked complete with it.
        head = f"{self._settings.branch_prefix}/{issue_number}-{project_id[:8]}"
        gate = Path(self._settings.push_gate)
        if gate.name != "push_gate.py":
            raise RuntimeError(f"VIBEY_PUSH_GATE must name a push_gate.py, not {gate}")
        pushed = self._runner.run(
            [
                "python3",
                str(gate.parent / "push_gate.py"),
                "run",
                "--",
                "git",
                "-C",
                str(integration_path),
                "push",
                "-u",
                "origin",
                f"{branch}:{head}",
            ]
        )
        if pushed.returncode:
            raise RuntimeError(pushed.stderr.strip() or f"push gate refused {branch}:{head}")
        base = self._settings.base
        existing = json.loads(
            self._forge.gh("pr", "list", "--head", head, "--base", base, "--json", "url")
        )
        if existing:
            pull_request = str(existing[0]["url"])
        else:
            create = [
                "pr",
                "create",
                "--base",
                base,
                "--head",
                head,
                "--title",
                f"delivery: #{issue_number} {title}",
                "--body",
                f"Automated delivery for GitHub issue #{issue_number}.\n\n"
                f"Vibey project: `{project_id}`.",
            ]
            if self._settings.draft:
                create.append("--draft")
            pull_request = self._forge.gh(*create).strip()
        pr = json.loads(
            self._forge.gh(
                "pr", "view", pull_request, "--json", "url,state,mergedAt,statusCheckRollup,isDraft"
            )
        )
        self._evidence.project(project_id, outcome="pr_created", status=status, pull_request=pr)
        if pr.get("state") == "MERGED":
            return pull_request
        if pr.get("isDraft"):
            # The merge train refuses a draft outright; the PR automation's `ready-draft`
            # promotes the exact head once its scans are stable, and the train lands it then.
            self._evidence.project(project_id, outcome="pr_draft_awaiting_promotion")
            print(f"project {project_id} PR is a draft; the PR automation promotes it when green")
            return pull_request
        checks = pr.get("statusCheckRollup")
        if (
            not isinstance(checks, list)
            or not checks
            or any(
                isinstance(check, dict) and check.get("conclusion") not in ("SUCCESS", "SKIPPED")
                for check in checks
            )
        ):
            print(f"project {project_id} PR is not merge-ready; evidence recorded")
            return pull_request
        merge_train = self._runner.run(
            ["uv", "run", "vibey-gh", "merge-train", "--pr", pull_request.rsplit("/", 1)[-1]]
        )
        self._evidence.project(
            project_id,
            merge_train_returncode=merge_train.returncode,
            merge_train_stdout=merge_train.stdout,
            merge_train_stderr=merge_train.stderr,
        )
        return pull_request


# Module-level rather than a method (ADR-0016's written reason): the script's entry point,
# which `python scripts/triaged_delivery.py` calls by name. It only reads flags and loops.
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--interval", type=float, default=300.0, help="Seconds between bounded dispatch attempts"
    )
    parser.add_argument(
        "--answer-design-defaults",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Opt in to answering DESIGN interview gates with their declared defaults and "
        "accepting the design. Off by default: those gates wait for a person. Also "
        f"{ENV}ANSWER_DESIGN_DEFAULTS.",
    )
    parser.add_argument(
        "--record-research-gaps",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Opt in to running the worker with [design.research] on_unavailable = "
        '"record_gap": a DESIGN research topic with no evidence is recorded as not researched, '
        "in the ledger and the spec, instead of parking for a person. Off by default. Also "
        f"{ENV}RECORD_RESEARCH_GAPS.",
    )
    parser.add_argument(
        "--answer-by",
        default=None,
        help="The name opt-in answers are recorded under (default automation:triaged-delivery; "
        f"also {ENV}ANSWER_BY).",
    )
    parser.add_argument(
        "--draft",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=f"Open delivery pull requests as drafts (default; also {ENV}DRAFT).",
    )
    parser.add_argument("--base", default=None, help=f"Target branch (default develop; {ENV}BASE)")
    parser.add_argument(
        "--provider", default=None, help=f"Worker provider (default gptossloop; {ENV}PROVIDER)"
    )
    parser.add_argument(
        "--worker-timeout",
        type=float,
        default=None,
        help=f"Seconds one worker run may take (default 900; {ENV}WORKER_TIMEOUT)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help=f"Worker steps one drive may take (default 100; {ENV}MAX_STEPS)",
    )
    parser.add_argument(
        "--lease-seconds",
        type=int,
        default=None,
        help=f"Ticket lease length (default 900; {ENV}LEASE_SECONDS)",
    )
    parser.add_argument(
        "--trusted-author",
        action="append",
        default=None,
        help="A login whose issues may be delivered; repeat for more. Replaces the reviewed "
        f"[unattended_approval] authors (the default; also {ENV}TRUSTED_AUTHORS).",
    )
    parser.add_argument(
        "--label-curator",
        action="append",
        default=None,
        help="A login whose triage labels may queue an issue; repeat for more. Replaces the "
        "reviewed authors plus [merge_train] trusted_authors and owner (the default; also "
        f"{ENV}LABEL_CURATORS).",
    )
    args = parser.parse_args(argv)
    settings = BridgeSettings.from_environ(args.repo.resolve(), os.environ)
    overrides = {
        "answer_design_defaults": args.answer_design_defaults,
        "record_research_gaps": args.record_research_gaps,
        "answer_by": args.answer_by,
        "draft": args.draft,
        "base": args.base,
        "provider": args.provider,
        "worker_timeout": args.worker_timeout,
        "max_steps": args.max_steps,
        "lease_seconds": args.lease_seconds,
        "trusted_authors": tuple(args.trusted_author) if args.trusted_author else None,
        "label_curators": tuple(args.label_curator) if args.label_curator else None,
    }
    settings = dataclasses.replace(
        settings, **{key: value for key, value in overrides.items() if value is not None}
    )
    bridge = DeliveryBridge.production(settings)
    if args.once:
        return bridge.run_once()
    while True:
        # A failed pass is reported and the loop goes on: the next pass reaps what this one
        # left leased, and a supervisor that dies on its first transient error delivers
        # nothing while looking installed.
        try:
            bridge.run_once()
        except Exception as exc:  # noqa: BLE001 - reported, then retried next interval
            print(f"pass failed: {exc}; next pass in {args.interval:g}s", file=sys.stderr)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
