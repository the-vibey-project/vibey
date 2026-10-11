# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey worker --auto-answer` says on stderr about the gates it answered."""

from vibey.application.dto import GateAutoAnswerReport
from vibey.domain.gate_auto_answer import GateAutoAnswerPolicy


def auto_answer_startup_line(policy: GateAutoAnswerPolicy) -> str:
    """Said once at startup: exactly which gates this worker will answer, so it is never a
    surprise, and which it never will."""
    if policy.answer_retries and not (
        policy.accept_review or policy.finish_local or policy.publish or policy.record_research_gaps
    ):
        # The original wording, for the original flag alone.
        return (
            f"auto-answer: on, up to {policy.limit} answers; spending gates,"
            " approvals and reviews still wait for you"
        )
    parts = []
    if policy.answer_retries:
        parts.append("the interview and retry gates")
    if policy.accept_review:
        parts.append("REVIEW approvals (accept)")
    if policy.finish_local:
        parts.append("the deployment choice (local_only, never deploy)")
    if policy.record_research_gaps:
        parts.append("DESIGN research gaps (the topic is recorded as not researched)")
    if policy.publish:
        parts.append("the publish interview as proposed (this PUSHES the finished work to GitHub)")
    return (
        f"auto-answer: on, up to {policy.limit} answers: {', '.join(parts)}; spending gates"
        " and every deployment gate still wait for you"
    )


def auto_answer_lines(report: GateAutoAnswerReport, *, limit: int) -> list[str]:
    """One line per answer, per failure, and one when the limit is used up."""
    lines = [
        f"auto-answer: answered {gate.gate_kind} gate {gate.gate_id} with {dict(gate.answer)}"
        for gate in report.answered
    ]
    lines += [f"auto-answer: could not answer {failure}" for failure in report.failed]
    lines += [f"auto-answer: {reason}" for reason in report.refused]
    if report.limit_reached:
        lines.append(
            f"auto-answer: the limit of {limit} answers is used up; every gate now waits for a"
            " person (vibey gates)"
        )
    return lines
