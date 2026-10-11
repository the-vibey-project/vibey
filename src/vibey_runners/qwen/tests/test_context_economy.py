# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeping what a session sends the model small, without taking what it needs."""

import json

from qwenloop.domain.context_economy import (
    STUB_PREFIX,
    ContextEconomy,
    ResultDeduper,
    composition,
    expected_files,
    fold_shell_output,
    ledger_note,
    mask_transcript,
    shape_result,
    tool_name,
)
from qwenloop.domain.model import ChatMessage


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


BIG = "x" * 600


def _session(reads: int) -> list[ChatMessage]:
    messages = [ChatMessage("system", "sys"), ChatMessage("user", "plan")]
    for n in range(reads):
        messages += [_call(f"c{n}", "search", query=f"q{n}"), _result(f"c{n}", BIG)]
    return messages


def test_off_switches_everything_off() -> None:
    assert ContextEconomy.off() == ContextEconomy(0, False, 0, 0, False, False)


def test_short_shell_output_is_kept_whole() -> None:
    assert fold_shell_output("a\nb\nc", 20, 40) == "a\nb\nc"


def test_long_shell_output_keeps_the_start_and_more_of_the_end() -> None:
    text = "\n".join(f"line {n}" for n in range(200))

    folded = fold_shell_output(text, 5, 10)

    lines = folded.splitlines()
    assert lines[:5] == [f"line {n}" for n in range(5)]
    assert lines[5] == "... [185 lines omitted from the middle] ..."
    assert lines[-10:] == [f"line {n}" for n in range(190, 200)]


def test_folding_of_zero_lines_is_off() -> None:
    text = "\n".join(map(str, range(500)))

    assert fold_shell_output(text, 0, 0) == text


def test_shape_result_folds_only_shell_output() -> None:
    output = "\n".join(f"l{n}" for n in range(300))
    economy = ContextEconomy()

    shell = shape_result("shell", {"exit_code": 1, "output": output}, economy)
    other = shape_result("search", {"output": output}, economy)

    assert shell["exit_code"] == 1 and "omitted from the middle" in str(shell["output"])
    assert other == {"output": output}
    assert shape_result("shell", {"error": "denied"}, economy) == {"error": "denied"}


def test_a_namespaced_tool_name_is_its_last_segment() -> None:
    assert tool_name("repo_browser.open_file") == "open_file"
    assert tool_name("shell") == "shell"


def test_an_identical_read_with_an_unchanged_answer_is_folded() -> None:
    deduper = ResultDeduper()

    assert deduper.check("search", {"query": "a"}, "hits", 3) is None
    note = deduper.check("search", {"query": "a"}, "hits", 7)

    assert note == "[same result as turn 3: nothing has changed since]"


def test_a_read_whose_answer_changed_is_shown_and_becomes_the_new_baseline() -> None:
    deduper = ResultDeduper()
    deduper.check("search", {"query": "a"}, "old", 1)

    assert deduper.check("search", {"query": "a"}, "new", 2) is None
    assert deduper.check("search", {"query": "a"}, "new", 3) == (
        "[same result as turn 2: nothing has changed since]"
    )


def test_only_read_only_tools_are_folded() -> None:
    deduper = ResultDeduper()

    assert deduper.check("shell", {"argv": ["ls"]}, "x", 1) is None
    assert deduper.check("shell", {"argv": ["ls"]}, "x", 2) is None


def test_a_call_that_can_change_files_makes_earlier_reads_stale() -> None:
    deduper = ResultDeduper()
    deduper.check("open_file", {"path": "a"}, "text", 1)

    deduper.note_call("read_file")  # reading changes nothing
    assert deduper.check("open_file", {"path": "a"}, "text", 2) is not None

    deduper.note_call("edit_file")
    assert deduper.check("open_file", {"path": "a"}, "text", 3) is None


def test_old_long_results_become_stubs_and_the_newest_stay_whole() -> None:
    session = _session(8)

    masked = mask_transcript(session, 3)

    results = [m for m in masked if m.role == "tool"]
    assert [r.content.startswith(STUB_PREFIX) for r in results] == [True] * 5 + [False] * 3
    assert "search q0" in results[0].content and "600 characters" in results[0].content
    assert masked[:2] == session[:2]
    assert [m.tool_call_id for m in masked if m.role == "tool"] == [f"c{n}" for n in range(8)]


def test_a_short_result_and_an_existing_stub_are_left_alone() -> None:
    session = _session(6)
    session[3] = _result("c0", "short")

    masked = mask_transcript(mask_transcript(session, 2), 2)

    assert masked[3].content == "short"
    again = mask_transcript(masked, 2)
    assert again == masked


def test_the_last_shell_result_is_kept_whole_however_old() -> None:
    session = [ChatMessage("system", "s"), ChatMessage("user", "p")]
    session += [_call("sh", "shell", argv=["npm", "test"]), _result("sh", "FAIL " + BIG)]
    for n in range(6):
        session += [_call(f"r{n}", "search", query="q"), _result(f"r{n}", BIG)]

    masked = mask_transcript(session, 2)

    assert masked[3].content.startswith("FAIL")
    assert masked[5].content.startswith(STUB_PREFIX)


def test_a_stub_for_a_shell_call_names_the_command_and_an_unknown_call_still_stubs() -> None:
    session = [ChatMessage("system", "s"), ChatMessage("user", "p")]
    session += [_call("a", "shell", argv=["ls", "-la"]), _result("a", BIG)]
    session += [_call("b", "shell", argv=["pwd"]), _result("b", BIG)]
    session += [_result("ghost", BIG), _result("last", BIG)]

    masked = mask_transcript(session, 1)

    assert "shell ls -la" in masked[3].content
    assert masked[7].content == BIG  # the newest result
    assert masked[6].content.startswith(STUB_PREFIX) and "tool" in masked[6].content


def test_zero_keeps_everything_whole() -> None:
    session = _session(8)

    assert mask_transcript(session, 0) is session


def _write(call_id: str, path: str, body: str) -> ChatMessage:
    return _call(call_id, "write_file", path=path, content=body)


def test_the_body_of_an_old_write_goes_but_not_its_path_or_a_recent_one() -> None:
    body = "z" * 500
    session = [ChatMessage("system", "s"), ChatMessage("user", "p")]
    session += [_write("w1", "src/a.ts", body), _result("w1", "{'written': 500}")]
    session += [_write("w2", "src/b.ts", body), _result("w2", "{'written': 500}")]

    masked = mask_transcript(session, 1)

    old = json.loads(masked[2].tool_calls[0]["function"]["arguments"])
    new = json.loads(masked[4].tool_calls[0]["function"]["arguments"])
    assert old["path"] == "src/a.ts"
    assert old["content"] == "<500 characters omitted: the file on disk has them>"
    assert new["content"] == body


def test_a_failed_write_keeps_its_body_and_other_tools_are_untouched() -> None:
    body = "z" * 500
    session = [ChatMessage("system", "s"), ChatMessage("user", "p")]
    session += [_write("w1", "a", body), _result("w1", "{'error': 'refused'}")]
    session += [_call("s1", "search", query=body), _result("s1", "ok")]
    session += [_call("s2", "search", query="x"), _result("s2", "ok")]

    masked = mask_transcript(session, 1)

    assert json.loads(masked[2].tool_calls[0]["function"]["arguments"])["content"] == body
    assert json.loads(masked[4].tool_calls[0]["function"]["arguments"])["query"] == body


def test_a_write_with_malformed_arguments_is_left_as_it_is() -> None:
    broken = ChatMessage(
        "assistant",
        "",
        tool_calls=(
            {"id": "x", "function": {"name": "write_file", "arguments": "{bad"}},
            {"id": "y", "function": "not a mapping"},
        ),
    )
    session = [ChatMessage("system", "s"), ChatMessage("user", "p"), broken]
    session += [_call("n", "search", query="q"), _result("n", "ok")]

    masked = mask_transcript(session, 1)

    assert masked[2].tool_calls[0]["function"]["arguments"] == "{bad"
    assert masked[2].tool_calls[1] == {"id": "y", "function": "not a mapping"}


def test_disabling_write_stubbing_keeps_old_bodies() -> None:
    body = "z" * 500
    session = [ChatMessage("system", "s"), ChatMessage("user", "p")]
    session += [_write("w1", "a", body), _result("w1", "ok")]
    session += [_write("w2", "b", body), _result("w2", "ok")]

    masked = mask_transcript(session, 1, stub_writes=False)

    assert json.loads(masked[2].tool_calls[0]["function"]["arguments"])["content"] == body


_BRIEF = (
    "## Your work item: ws\n\nFiles you are expected to create or change (start there):\n"
    "- src/app/a/page.tsx\n- src/app/b/page.tsx\n- src/app/a/page.tsx\n\nMore text\n- not a file"
)


def test_the_planned_files_are_read_off_the_brief_once_each() -> None:
    assert expected_files(_BRIEF) == ("src/app/a/page.tsx", "src/app/b/page.tsx")


def test_a_files_list_may_end_the_plan() -> None:
    assert expected_files("Files you are expected to create or change:\n- only.ts") == ("only.ts",)


def test_a_plan_without_a_files_section_plans_no_files() -> None:
    assert expected_files("just do the thing") == ()
    assert expected_files("Files you are expected to create or change:\nnothing") == ()


def test_the_ledger_says_what_is_done_what_is_left_and_how_the_last_command_ended() -> None:
    note = ledger_note(("a", "b", "c"), ["a", "z"], "`npm test` exited 1")

    assert note is not None
    assert "1 of 3 planned files written" in note
    assert "Still to write: b, c" in note
    assert "Also written: z" in note
    assert "Last command: `npm test` exited 1" in note


def test_a_finished_ledger_points_at_verification() -> None:
    note = ledger_note(("a",), ["a"], None)

    assert note is not None and "run the verification commands" in note
    assert "Still to write" not in note and "Last command" not in note


def test_no_planned_files_means_no_ledger() -> None:
    assert ledger_note((), ["a"], "x") is None


def test_composition_splits_a_request_by_what_it_is() -> None:
    session = _session(2) + [ChatMessage("assistant", "y" * 400), _result("ghost", "q" * 40)]

    report = composition(session)

    assert report["tool_results"] == {"search": 300, "tool": 10}
    assert report["head"] == 2 and isinstance(report["assistant"], int)
    assert report["assistant"] > 100
    assert report["total"] == report["head"] + report["assistant"] + 310  # type: ignore[operator]
