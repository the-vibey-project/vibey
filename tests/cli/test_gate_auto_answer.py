# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey worker --auto-answer` says on stderr."""

from uuid import uuid4

from vibey.application.dto import AutoAnsweredGate, GateAutoAnswerReport
from vibey.cli.gate_auto_answer import auto_answer_lines


def test_an_empty_sweep_says_nothing() -> None:
    assert auto_answer_lines(GateAutoAnswerReport(project_id=None), limit=30) == []


def test_each_answer_failure_and_refusal_is_a_line_and_the_limit_is_said_last() -> None:
    gate = uuid4()
    report = GateAutoAnswerReport(
        project_id=uuid4(),
        answered=(
            AutoAnsweredGate(
                project_id=uuid4(),
                gate_id=gate,
                gate_kind="escalation_exhausted",
                answer={"max_attempts": 10},
                waited_seconds=1.0,
            ),
        ),
        failed=("gate g (question): db down",),
        refused=("open gates: down",),
        limit_reached=True,
    )
    lines = auto_answer_lines(report, limit=2)
    assert lines[0] == (
        f"auto-answer: answered escalation_exhausted gate {gate} with {{'max_attempts': 10}}"
    )
    assert lines[1] == "auto-answer: could not answer gate g (question): db down"
    assert lines[2] == "auto-answer: open gates: down"
    assert "limit of 2 answers is used up" in lines[3] and "vibey gates" in lines[3]
    assert len(lines) == 4
