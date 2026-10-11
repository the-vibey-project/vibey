# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey worker --auto-answer` says on stderr."""

from uuid import uuid4

from vibey.application.dto import AutoAnsweredGate, GateAutoAnswerReport
from vibey.cli.gate_auto_answer import auto_answer_lines, auto_answer_startup_line
from vibey.domain.gate_auto_answer import GateAutoAnswerPolicy


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


def test_the_original_flag_alone_keeps_its_original_startup_line() -> None:
    assert auto_answer_startup_line(GateAutoAnswerPolicy(limit=3)) == (
        "auto-answer: on, up to 3 answers; spending gates, approvals and reviews still wait for you"
    )


def test_the_startup_line_names_each_acceptance_and_what_never_gets_answered() -> None:
    both = auto_answer_startup_line(
        GateAutoAnswerPolicy(answer_retries=False, accept_review=True, finish_local=True)
    )
    review = auto_answer_startup_line(
        GateAutoAnswerPolicy(answer_retries=False, accept_review=True)
    )
    everything = auto_answer_startup_line(
        GateAutoAnswerPolicy(accept_review=True, finish_local=True)
    )

    assert "REVIEW approvals (accept), the deployment choice (local_only, never deploy)" in both
    assert "interview and retry gates" not in both
    assert "REVIEW approvals (accept)" in review and "deployment choice" not in review
    assert "the interview and retry gates, REVIEW approvals (accept)" in everything
    for line in (both, review, everything):
        assert "spending gates and every deployment gate still wait for you" in line


def test_finishing_local_alone_names_only_the_deployment_choice() -> None:
    line = auto_answer_startup_line(GateAutoAnswerPolicy(answer_retries=False, finish_local=True))

    assert "the deployment choice (local_only, never deploy)" in line
    assert "REVIEW approvals" not in line and "interview" not in line


def test_publishing_is_named_loudly_because_it_pushes_the_work_to_github() -> None:
    line = auto_answer_startup_line(GateAutoAnswerPolicy(answer_retries=False, publish=True))

    assert "the publish interview as proposed (this PUSHES the finished work to GitHub)" in line
    assert "spending gates and every deployment gate still wait for you" in line


def test_publishing_with_the_retry_flag_is_not_the_original_line() -> None:
    line = auto_answer_startup_line(GateAutoAnswerPolicy(publish=True))

    assert line.startswith("auto-answer: on, up to 30 answers: the interview and retry gates, ")
    assert "PUSHES" in line


def test_recording_research_gaps_is_named_and_leaves_the_original_wording_behind() -> None:
    line = auto_answer_startup_line(GateAutoAnswerPolicy(record_research_gaps=True))

    assert "DESIGN research gaps (the topic is recorded as not researched)" in line
    assert "the interview and retry gates" in line
    assert "spending gates and every deployment gate still wait for you" in line
