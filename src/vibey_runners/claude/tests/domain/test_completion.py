# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from claudeloop.domain.completion import (
    Blocked,
    Continue,
    Done,
    StructuredVerdict,
    evaluate,
)


def test_structured_complete_is_done():
    v = StructuredVerdict(complete=True, summary="all done")
    assert evaluate(structured=v, output_text="") == Done(summary="all done")


def test_structured_incomplete_is_continue_with_remaining_work():
    v = StructuredVerdict(complete=False, remaining_work=("thing a", "thing b"))
    assert evaluate(structured=v, output_text="") == Continue(remaining_work=("thing a", "thing b"))


def test_structured_blocked_outranks_complete_flag():
    v = StructuredVerdict(complete=True, blocked_on="waiting on MCP auth")
    assert evaluate(structured=v, output_text="") == Blocked(reason="waiting on MCP auth")


def test_fallback_marker_present_is_done():
    result = evaluate(structured=None, output_text="...\nCLAUDELOOP_TASK_FULLY_COMPLETE\n")
    assert result == Done(summary="")


def test_fallback_marker_absent_is_continue():
    result = evaluate(structured=None, output_text="still working on it")
    assert result == Continue(remaining_work=())


def test_fallback_uses_custom_marker():
    result = evaluate(structured=None, output_text="XYZ_DONE", done_marker="XYZ_DONE")
    assert result == Done(summary="")


def test_a_zero_cost_turn_that_generated_tokens_is_not_empty():
    """On a local backend every turn is recorded at $0 (cost_mode "zero"), so
    output tokens are what tell a tool-only turn from an empty response."""
    verdict = evaluate(
        structured=None, output_text="", cost_usd=0.0, output_tokens=412, empty_turn_streak=2
    )
    assert verdict == Continue(remaining_work=())


def test_a_zero_cost_zero_token_turn_is_still_empty():
    verdict = evaluate(
        structured=None, output_text="", cost_usd=0.0, output_tokens=0, empty_turn_streak=2
    )
    assert verdict == Blocked(reason="repeated empty model responses")


def test_without_the_marker_fallback_only_a_structured_verdict_completes():
    text = '{"name": "StructuredOutput"}\nCLAUDELOOP_TASK_FULLY_COMPLETE'
    assert evaluate(structured=None, output_text=text, marker_fallback=False) == Continue(
        remaining_work=()
    )
    assert evaluate(
        structured=StructuredVerdict(complete=True, summary="ok"),
        output_text=text,
        marker_fallback=False,
    ) == Done(summary="ok")
