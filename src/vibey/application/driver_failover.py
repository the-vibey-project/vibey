# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The driver failover (ADR-0070): the Claude Code session steering the work runs out
of capacity, the work continues on the sovereign engine at ULTRA, and it comes back to
the same session once a probe of the paid model is recorded as successful.

`fail_over` is what Claude Code's `StopFailure` hook calls; `probe` is what the
launchd / systemd timer calls. Both are idempotent under replay: the state is read
from the driver's own append-only ledger each time, a second hook for an active
failover records nothing and starts nothing, and a record is appended *before* the
process it describes is started, so a crash between them re-reads rather than starts
a second engine on the same worktree.

Both directions go through the no-loss gate (`vibey/domain/driver_brief.py`): up to
three STRICT attempts, one FULL_TRANSCRIPT attempt with the transcript copied into the
worktree, then HUMAN -- the handoff parks, nothing is started, and the parked brief
is left in the worktree for a person. A gate is never skipped.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import replace
from typing import Final

from vibey.application.dto import DriverOutcome, DriverSignal
from vibey.application.interfaces.driver import (
    DriverLedgerPort,
    DriverWorkspacePort,
    ProcessPort,
)
from vibey.application.interfaces.system import Clock
from vibey.domain.driver_brief import (
    DRIVER_BRIEF_RENDERER,
    DRIVER_GATE,
    DriverBrief,
    DriverDirection,
)
from vibey.domain.failover import (
    CAPACITY_SIGNALS,
    FAILOVER_POLICY,
    FailoverKind,
    FailoverSettings,
    FailoverStatus,
)
from vibey.domain.handoff import GateMode, GateResult
from vibey.domain.interfaces.driver_brief_interface import (
    DriverBriefRendererInterface,
    DriverGateInterface,
)
from vibey.domain.interfaces.failover_interface import (
    CapacitySignalClassifierInterface,
    FailoverPolicyInterface,
)

MAX_STRICT_ATTEMPTS: Final = 3
PROBE_TIMEOUT_SECONDS: Final = 120.0
WIND_DOWN_TIMEOUT_SECONDS: Final = 60.0
FAILOVER_NEXT_ACTION: Final = (
    "Continue the work the transcript was doing when the paid model stopped. Commit "
    "each coherent step on the current branch with a Conventional Commit, and do not "
    "push, merge or open a pull request: the driver session reviews your commits when "
    "it comes back."
)
HANDBACK_NEXT_ACTION: Final = (
    "Review every commit listed above, as the sovereign engine made them unattended, "
    "then continue the work from where the transcript stopped."
)


class DriverFailoverService:
    """Declared by `interfaces/driver.py::DriverFailoverServiceInterface`."""

    def __init__(
        self,
        *,
        settings: FailoverSettings,
        workspace: DriverWorkspacePort,
        ledger: DriverLedgerPort,
        processes: ProcessPort,
        clock: Clock,
        policy: FailoverPolicyInterface = FAILOVER_POLICY,
        signals: CapacitySignalClassifierInterface = CAPACITY_SIGNALS,
        gate: DriverGateInterface = DRIVER_GATE,
        renderer: DriverBriefRendererInterface = DRIVER_BRIEF_RENDERER,
    ) -> None:
        self._settings = settings
        self._workspace = workspace
        self._ledger = ledger
        self._processes = processes
        self._clock = clock
        self._policy = policy
        self._signals = signals
        self._gate = gate
        self._renderer = renderer

    def status(self) -> FailoverStatus:
        return self._policy.status(self._ledger.records())

    def fail_over(self, signal: DriverSignal) -> DriverOutcome:
        now = self._clock.now()
        capacity = self._signals.classify(signal.error, signal.detail)
        plan = self._policy.plan(capacity, now=now, settings=self._settings)
        if plan is None:
            return DriverOutcome("ignored", f"{signal.error!r} is not a capacity rejection")
        status = self.status()
        if status.active:
            return DriverOutcome("already", "a failover is already active", status=status)
        repo = self._workspace.repo(signal.cwd)
        brief = DriverBrief(
            direction=DriverDirection.FAILOVER,
            session_id=signal.session_id,
            cwd=signal.cwd,
            transcript_path=signal.transcript_path,
            transcript_digest="",
            transcript_lines=0,
            branch=repo.branch,
            head_sha=repo.head_sha,
            dirty_paths=repo.dirty_paths,
            next_action=FAILOVER_NEXT_ACTION,
            cause=plan.cause.value,
            target=plan.target_engine,
            effort=plan.effort.name,
            last_message=signal.last_message,
        )
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        brief, result = self._gated(brief, name=f"failover-{stamp}")
        if not result.ok:
            path = self._workspace.write_brief(
                signal.cwd, f"PARKED-failover-{stamp}.md", self._parked(brief, result)
            )
            return DriverOutcome("parked", self._violations(result), brief_path=path)
        text = self._renderer.render(brief)
        path = self._workspace.write_brief(signal.cwd, f"failover-{stamp}.md", text)
        run_id = f"driver-{signal.session_id[:8]}-{stamp}"
        self._ledger.append(
            FailoverKind.FAILED_OVER,
            at=now,
            payload={
                "session_id": signal.session_id,
                "cwd": signal.cwd,
                "transcript_path": signal.transcript_path,
                "transcript_digest": brief.transcript_digest,
                "head_sha": repo.head_sha,
                "error": signal.error,
                "cause": plan.cause.value,
                "target": plan.target_engine,
                "effort": plan.effort.name,
                "probe_not_before": plan.probe_not_before.isoformat(),
                "brief_path": path,
                "brief_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "gate_mode": result.mode.value,
                "gate_attempts": result.attempts,
                "run_id": run_id,
            },
        )
        self._processes.spawn(
            self._argv(
                self._settings.sovereign_argv,
                brief=path,
                cwd=signal.cwd,
                run_id=run_id,
                session_id=signal.session_id,
            ),
            cwd=signal.cwd,
        )
        return DriverOutcome("failed_over", run_id, brief_path=path, status=self.status())

    def probe(self, cwd: str) -> DriverOutcome:
        now = self._clock.now()
        status = self.status()
        if not status.active or status.failover is None:
            return DriverOutcome("idle", "no failover is active", status=status)
        if status.probe_ok is None:
            if not status.probe_due(now):
                return DriverOutcome("not_due", "the probe is scheduled later", status=status)
            outcome = self._processes.run(
                self._settings.probe_argv, cwd=cwd, timeout=PROBE_TIMEOUT_SECONDS
            )
            ok, detail = self._probe_ok(outcome.exit_code, outcome.stdout)
            self._ledger.append(
                FailoverKind.PROBED,
                at=now,
                payload={"ok": ok, "exit_code": outcome.exit_code, "detail": detail},
            )
            if not ok:
                return DriverOutcome("probe_failed", detail, status=self.status())
            status = self.status()
        return self._hand_back(status, cwd=cwd)

    def _hand_back(self, status: FailoverStatus, *, cwd: str) -> DriverOutcome:
        assert status.failover is not None and status.probe_ok is not None  # nosec B101
        now = self._clock.now()
        record = status.failover.payload
        session_id = str(record.get("session_id", ""))
        run_id = str(record.get("run_id", ""))
        repo = self._workspace.repo(cwd)
        brief = DriverBrief(
            direction=DriverDirection.HANDBACK,
            session_id=session_id,
            cwd=cwd,
            transcript_path=str(record.get("transcript_path", "")),
            transcript_digest="",
            transcript_lines=0,
            branch=repo.branch,
            head_sha=repo.head_sha,
            dirty_paths=repo.dirty_paths,
            next_action=HANDBACK_NEXT_ACTION,
            cause="a successful probe was recorded at " + status.probe_ok.at.isoformat(),
            target="the same Claude Code session",
            effort="unchanged",
            commits_since=self._workspace.commits_since(cwd, str(record.get("head_sha", ""))),
        )
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        brief, result = self._gated(brief, name=f"handback-{stamp}")
        if not result.ok:
            path = self._workspace.write_brief(
                cwd, f"PARKED-handback-{stamp}.md", self._parked(brief, result)
            )
            return DriverOutcome("parked", self._violations(result), brief_path=path)
        wind_down = self._processes.run(
            self._argv(
                self._settings.sovereign_wind_down_argv,
                brief="",
                cwd=cwd,
                run_id=run_id,
                session_id=session_id,
            ),
            cwd=cwd,
            timeout=WIND_DOWN_TIMEOUT_SECONDS,
        )
        if wind_down.exit_code != 0:
            # The sovereign engine may still be running: never start a second engine
            # on the same worktree. The next tick tries again.
            return DriverOutcome(
                "wind_down_failed", f"exit {wind_down.exit_code}", status=self.status()
            )
        text = self._renderer.render(brief)
        path = self._workspace.write_brief(cwd, f"handback-{stamp}.md", text)
        self._ledger.append(
            FailoverKind.HANDED_BACK,
            at=now,
            payload={
                "session_id": session_id,
                "brief_path": path,
                "brief_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "gate_mode": result.mode.value,
                "gate_attempts": result.attempts,
                "probe_at": status.probe_ok.at.isoformat(),
                "wind_down_exit": wind_down.exit_code,
            },
        )
        prompt = (
            f"Your usage is available again. Read the handback brief at {path} in full, "
            "then continue."
        )
        self._processes.spawn(
            self._argv(
                self._settings.resume_argv,
                brief=path,
                cwd=cwd,
                run_id=run_id,
                session_id=session_id,
                prompt=prompt,
            ),
            cwd=cwd,
        )
        return DriverOutcome("handed_back", session_id, brief_path=path, status=self.status())

    def _gated(self, brief: DriverBrief, *, name: str) -> tuple[DriverBrief, GateResult]:
        """STRICT up to three times, then FULL_TRANSCRIPT once, then HUMAN."""
        result: GateResult | None = None
        for attempt in range(1, MAX_STRICT_ATTEMPTS + 1):
            before = self._workspace.digest(brief.transcript_path)
            if before is not None:
                brief = replace(
                    brief, transcript_digest=before.sha256, transcript_lines=before.lines
                )
            now = self._workspace.digest(brief.transcript_path)
            result = self._gate.verify(
                brief,
                digest_now=None if now is None else now.sha256,
                mode=GateMode.STRICT,
                attempts=attempt,
            )
            if result.ok:
                return brief, result
        copy_path: str | None = None
        copied = None
        if self._workspace.digest(brief.transcript_path) is not None:
            copy_path = self._workspace.copy_transcript(
                brief.transcript_path, brief.cwd, f"{name}.jsonl"
            )
            copied = self._workspace.digest(copy_path)
        if copied is not None:
            brief = replace(
                brief,
                transcript_copy=copy_path,
                transcript_digest=copied.sha256,
                transcript_lines=copied.lines,
            )
        result = self._gate.verify(
            brief,
            digest_now=None if copied is None else copied.sha256,
            mode=GateMode.FULL_TRANSCRIPT,
            attempts=MAX_STRICT_ATTEMPTS + 1,
        )
        if result.ok:
            return brief, result
        return brief, replace(result, mode=GateMode.HUMAN)

    def _parked(self, brief: DriverBrief, result: GateResult) -> str:
        return (
            "# PARKED: the no-loss gate failed\n\n"
            "Nothing was started. A person decides what happens next.\n\n"
            f"Violations: {self._violations(result)}\n\n" + self._renderer.render(brief)
        )

    @staticmethod
    def _violations(result: GateResult) -> str:
        return "; ".join(f"{v.rule.value}: {v.detail}" for v in result.violations)

    @staticmethod
    def _probe_ok(exit_code: int, stdout: str) -> tuple[bool, str]:
        """Only an exit of 0 with a JSON result saying `is_error: false` is a success;
        anything else, a refusal included, is not (a status is evidence-bounded)."""
        if exit_code != 0:
            return False, f"exit {exit_code}"
        try:
            body = json.loads(stdout)
        except ValueError:
            return False, "the probe printed no JSON result"
        if not isinstance(body, dict) or body.get("is_error") is not False:
            return False, "the probe's result is an error"
        return True, str(body.get("subtype", "success"))

    @staticmethod
    def _argv(template: Sequence[str], **values: str) -> tuple[str, ...]:
        """Fills `{brief}`, `{cwd}`, `{run_id}`, `{session_id}` and `{prompt}`; any other
        text, braces included, is passed through as written."""
        out: list[str] = []
        for part in template:
            for key in ("brief", "cwd", "run_id", "session_id", "prompt"):
                part = part.replace("{" + key + "}", values.get(key, ""))
            out.append(part)
        return tuple(out)
