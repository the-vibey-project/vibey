# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Renewing a long session's context and noticing a stall."""

import json

from qwenloop.domain.model import ChatMessage
from qwenloop.domain.session_health import (
    KEEP_RECENT_MESSAGES,
    RENEWAL_NOTE_PREFIX,
    StallDetector,
    call_signature,
    renew_transcript,
    work_summary,
)


def _call(call_id: str, name: str, **arguments: object) -> ChatMessage:
    return ChatMessage(
        "assistant",
        "",
        tool_calls=(
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments)},
            },
        ),
    )


def _result(call_id: str, text: str) -> ChatMessage:
    return ChatMessage("tool", text, tool_call_id=call_id)


def test_a_call_signature_is_the_tool_and_exactly_its_arguments() -> None:
    assert call_signature("shell", {"b": 1, "a": 2}) == call_signature("shell", {"a": 2, "b": 1})
    assert call_signature("shell", {"a": 1}) != call_signature("read_file", {"a": 1})
    assert call_signature("shell", {"a": 1}) != call_signature("shell", {"a": 2})


def test_the_summary_lists_what_was_written_edited_and_read_and_how_commands_ended() -> None:
    dropped = [
        _call("1", "write_file", path="src/a.ts", content="x"),
        _result("1", "wrote 1 characters"),
        _call("2", "edit_file", path="src/b.ts"),
        _result("2", "edited"),
        _call("3", "read_file", path="src/c.ts"),
        _result("3", "content"),
        _call("4", "shell", argv=["npm", "run", "build"]),
        _result("4", "exit 1 - error TS2304\nsecond line"),
        _call("5", "shell", argv="echo hi"),
        _call("6", "search", pattern="x"),
        ChatMessage("assistant", "thinking"),
    ]

    summary = work_summary(dropped)

    assert summary.startswith(RENEWAL_NOTE_PREFIX)
    assert "Files you wrote: src/a.ts" in summary
    assert "Files you edited: src/b.ts" in summary
    assert "Files you read: src/c.ts" in summary
    assert "Ran `npm run build` -> exit 1 - error TS2304 second line" in summary
    assert "Ran `echo hi`" in summary and "Ran `echo hi` ->" not in summary
    assert "search" not in summary


def test_a_call_with_unreadable_arguments_is_skipped_not_fatal() -> None:
    broken = ChatMessage(
        "assistant",
        "",
        tool_calls=(
            {"id": "1", "function": {"name": "write_file", "arguments": "{not json"}},
            {"id": "2", "function": {"name": "write_file", "arguments": "[1]"}},
            {"id": "3", "function": "nope"},
        ),
    )

    summary = work_summary([broken])

    assert summary.startswith(RENEWAL_NOTE_PREFIX)
    assert "Files you wrote" not in summary


def test_the_summary_names_each_file_once_and_keeps_the_newest_commands() -> None:
    dropped: list[ChatMessage] = []
    for n in range(12):
        dropped.append(_call(f"c{n}", "shell", argv=[f"cmd{n}"]))
    dropped += [_call("w1", "write_file", path="a"), _call("w2", "write_file", path="a")]

    summary = work_summary(dropped)

    assert "Files you wrote: a\n" in summary + "\n"
    assert "cmd11" in summary and "cmd4" in summary and "cmd3" not in summary


def test_an_earlier_summary_is_carried_into_the_next() -> None:
    first = work_summary([_call("1", "write_file", path="old.ts")])

    second = work_summary([ChatMessage("user", first), _call("2", "write_file", path="new.ts")])

    assert "Files you wrote: new.ts" in second
    assert "Before that: Files you wrote: old.ts" in second


def _transcript(extra: int) -> list[ChatMessage]:
    messages = [ChatMessage("system", "sys"), ChatMessage("user", "plan")]
    for n in range(extra):
        messages += [_call(f"c{n}", "read_file", path=f"f{n}"), _result(f"c{n}", "y" * 400)]
    return messages


def test_a_transcript_under_the_threshold_is_untouched() -> None:
    transcript = _transcript(3)

    assert renew_transcript(transcript, 100_000) == (transcript, 0)


def test_renewal_off_leaves_any_transcript_alone() -> None:
    transcript = _transcript(30)

    assert renew_transcript(transcript, 0) == (transcript, 0)


def test_a_transcript_too_short_to_split_is_untouched() -> None:
    transcript = _transcript(2)  # 6 messages after the head: nothing older to replace

    assert renew_transcript(transcript, 1) == (transcript, 0)


def test_renewal_keeps_the_head_and_newest_messages_and_replaces_the_rest() -> None:
    transcript = _transcript(10)  # 2 + 20 messages

    renewed, replaced = renew_transcript(transcript, 100)

    assert renewed[:2] == transcript[:2]
    assert renewed[2].role == "user" and renewed[2].content.startswith(RENEWAL_NOTE_PREFIX)
    assert renewed[3:] == transcript[-KEEP_RECENT_MESSAGES:]
    assert replaced == len(transcript) - 2 - KEEP_RECENT_MESSAGES
    assert "f0" in renewed[2].content


def test_the_kept_tail_never_starts_on_a_tool_result_whose_call_was_dropped() -> None:
    transcript = _transcript(10)
    transcript.insert(-5, _result("x", "orphan-candidate"))  # the cut would land on a tool

    renewed, _ = renew_transcript(transcript, 100)

    assert renewed[3].role != "tool"


def test_a_cut_that_would_leave_nothing_to_replace_changes_nothing() -> None:
    transcript = [ChatMessage("system", "s"), ChatMessage("user", "p")]
    transcript += [ChatMessage("tool", "y" * 4000)] * (KEEP_RECENT_MESSAGES + 1)

    assert renew_transcript(transcript, 1) == (transcript, 0)


def test_new_calls_never_stall() -> None:
    detector = StallDetector(3)

    assert [detector.observe([f"call-{n}"]) for n in range(10)] == [False] * 10


def test_the_same_call_again_and_again_stalls_at_the_limit() -> None:
    detector = StallDetector(3)

    results = [detector.observe(["echo done"]) for _ in range(5)]

    # the first sighting is novel; then three turns with nothing new reach the limit
    assert results == [False, False, False, True, True]
    assert detector.stalled_turns == 4


def test_turns_with_no_call_at_all_count_as_stalled() -> None:
    detector = StallDetector(2)

    assert [detector.observe([]) for _ in range(2)] == [False, True]


def test_one_new_call_resets_the_count() -> None:
    detector = StallDetector(2)
    detector.observe(["a"])
    detector.observe(["a"])

    assert detector.observe(["b"]) is False
    assert detector.stalled_turns == 0


def test_a_limit_of_zero_never_stalls() -> None:
    detector = StallDetector(0)

    assert not any(detector.observe([]) for _ in range(50))


def test_a_call_made_long_ago_is_novel_again() -> None:
    detector = StallDetector(2, memory=3)
    for signature in ("a", "b", "c", "d"):
        detector.observe([signature])

    assert detector.observe(["a"]) is False  # "a" has left the 3-call memory
