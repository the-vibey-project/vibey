# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The driver's handoff brief and its no-loss gate (ADR-0070).

The driver is the Claude Code session steering the work. Its conversation lives in
Claude Code's transcript, not in vibey's ledger, so the driver's brief does not
restate it: it names the whole transcript -- path, line count and SHA-256 -- and the
repository state, and says what to do next. The gate then checks the brief against
the transcript as it stands, in the same three modes as every handoff
(handoff-protocol.md §6.4):

- **STRICT** -- the named digest must equal the transcript's digest now. A session
  still writing its last lines fails and is retried.
- **FULL_TRANSCRIPT** -- the transcript is copied into the worktree and the brief
  names the copy, whose digest must match. The receiving engine reads every line.
- **HUMAN** -- the handoff parks. Nothing is launched on a failed gate.

The same gate runs in both directions: failover (driver to sovereign engine) and
handback (sovereign engine to the same driver session).
"""

from dataclasses import dataclass
from enum import StrEnum

from vibey.domain.handoff import GateMode, GateResult, GateRule, Violation


class DriverDirection(StrEnum):
    FAILOVER = "failover"
    HANDBACK = "handback"


@dataclass(frozen=True, slots=True)
class DriverBrief:
    direction: DriverDirection
    session_id: str
    cwd: str
    transcript_path: str
    transcript_digest: str
    transcript_lines: int
    branch: str
    head_sha: str
    dirty_paths: tuple[str, ...]
    next_action: str
    cause: str
    target: str
    effort: str
    last_message: str = ""
    transcript_copy: str | None = None
    commits_since: tuple[str, ...] = ()


class DriverGate:
    """Verifies a driver brief. Pure: the caller supplies the digest it read now."""

    RULES: tuple[GateRule, ...] = (
        GateRule.R1_REMAINING,
        GateRule.R6_RANGE,
        GateRule.R7_ARTIFACTS,
        GateRule.R10_CONTAINMENT,
    )

    def verify(
        self,
        brief: DriverBrief,
        *,
        digest_now: str | None,
        mode: GateMode,
        attempts: int,
    ) -> GateResult:
        violations: list[Violation] = []
        if not brief.next_action.strip():
            violations.append(Violation(GateRule.R1_REMAINING, None, "no next action"))
        if mode is GateMode.FULL_TRANSCRIPT and not brief.transcript_copy:
            violations.append(
                Violation(GateRule.R6_RANGE, None, "full-transcript mode names no copy")
            )
        if digest_now is None:
            violations.append(Violation(GateRule.R6_RANGE, None, "transcript unreadable"))
        elif digest_now != brief.transcript_digest:
            violations.append(
                Violation(GateRule.R6_RANGE, None, "transcript changed after the brief")
            )
        if not brief.head_sha:
            violations.append(Violation(GateRule.R7_ARTIFACTS, None, "no repository head"))
        if not brief.session_id or not brief.cwd.startswith("/"):
            violations.append(
                Violation(GateRule.R10_CONTAINMENT, None, "no session id or relative cwd")
            )
        return GateResult(
            ok=not violations,
            mode=mode,
            attempts=attempts,
            violations=tuple(violations),
            rules_run=self.RULES,
        )


class DriverBriefRenderer:
    """The brief as the text the receiving engine reads first."""

    def render(self, brief: DriverBrief) -> str:
        source = brief.transcript_copy or brief.transcript_path
        lines = [
            f"# vibey driver {brief.direction.value} brief",
            "",
            f"- Session: `{brief.session_id}`",
            f"- Cause: {brief.cause}",
            f"- To: {brief.target} at effort {brief.effort}",
            f"- Worktree: `{brief.cwd}` on `{brief.branch}` at `{brief.head_sha}`",
            f"- Transcript: `{source}` ({brief.transcript_lines} lines, "
            f"sha256 `{brief.transcript_digest}`)",
            "",
            "Read the whole transcript before acting; it is the conversation so far and",
            "this brief does not restate it. Nothing in it is lost: the digest above is",
            "the one the no-loss gate verified.",
            "",
            "## Uncommitted paths",
            "",
        ]
        lines += [f"- `{path}`" for path in brief.dirty_paths] or ["- (none)"]
        if brief.direction is DriverDirection.HANDBACK:
            lines += ["", "## Commits made while you were away", ""]
            lines += [f"- {commit}" for commit in brief.commits_since] or ["- (none)"]
        if brief.last_message:
            lines += ["", "## Last message", "", brief.last_message]
        lines += ["", "## Next action", "", brief.next_action, ""]
        return "\n".join(lines)


DRIVER_GATE = DriverGate()
DRIVER_BRIEF_RENDERER = DriverBriefRenderer()
