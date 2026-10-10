# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey worker --auto-answer` says on stderr about the gates it answered."""

from vibey.application.dto import GateAutoAnswerReport


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
