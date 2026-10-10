# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The backlog splitter: which issues it cuts, along what, and that it files each slice once."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts import backlog_killer as bk
from scripts import backlog_splitter as sp

KILLER: dict[str, Any] = {
    "max_issue_chars": 200,
    "skip_labels": ["operator", "epic"],
    "skip_authors": ["github-actions[bot]"],
    "split_label": "vibey-gh:split-child",
    "agent_labels": ["go"],
    "split_parent_allow_labels": ["epic"],
}
SETTINGS: dict[str, Any] = {
    "enabled": True,
    "max_children": 3,
    "max_parents_per_run": 2,
}
TASKS = (
    "Intro that is long enough. " * 10 + "\n- [ ] add the flag\n- [x] done already\n- [ ] test it\n"
)


def issue(number: int, body: str, *labels: str, **extra: Any) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"issue {number}",
        "labels": [{"name": name} for name in labels],
        "body": body,
        "createdAt": f"2026-09-{number:02d}T00:00:00Z",
        "author": {"login": extra.pop("author", "owner")},
        "authorAssociation": extra.pop("association", "OWNER"),
    }


class Source:
    def __init__(self, issues: list[dict[str, Any]]) -> None:
        self.issues = issues

    def open_issues(self) -> list[dict[str, Any]]:
        return self.issues

    def open_pull_requests(self) -> list[dict[str, Any]]:
        return []


class Sink:
    def __init__(self, children: list[dict[str, Any]] | None = None, link: bool = True) -> None:
        self.children, self.link = children or [], link
        self.created: list[tuple[str, str, list[str]]] = []
        self.labels: list[str] = []
        self.marked: list[tuple[int, str, str]] = []

    def split_children(self, label: str) -> list[dict[str, Any]]:
        return self.children

    def ensure_label(self, name: str, color: str, description: str) -> None:
        self.labels.append(name)

    def create_issue(self, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        self.created.append((title, body, labels))
        return {"id": 1000 + len(self.created), "number": 500 + len(self.created)}

    def link_sub_issue(self, parent: int, child_id: int) -> bool:
        return self.link

    def mark_parent(self, parent: int, label: str, comment: str) -> None:
        self.marked.append((parent, label, comment))


def splitter(issues, sink=None, killer=None, settings=None, expectations=None):
    return sp.BacklogSplitter(
        Source(issues),
        sink or Sink(),
        {**KILLER, **(killer or {})},
        {**SETTINGS, **(settings or {})},
        expectations or {},
    )


def test_it_cuts_on_task_items_then_numbered_steps_then_sections() -> None:
    s = splitter([])
    assert s.outline("- [ ] one\n  more of one\n- [x] done\n- [ ] two\n") == [
        ("one more of one", ""),
        ("two", ""),
    ]
    assert s.outline("1. first\n2) second **bold** [link](http://x)\n") == [
        ("first", ""),
        ("second bold link", ""),
    ]
    body = "## Background\nwhy\n## Parser\nread it\n### Writer\nwrite it\n## Notes\nx\n"
    assert s.outline(body) == [("Parser", "read it"), ("Writer", "write it")]


def test_one_item_is_not_a_structure_and_code_blocks_are_not_read() -> None:
    s = splitter([])
    assert s.outline("- [ ] only one\n") == []
    assert s.outline("```\n- [ ] a\n- [ ] b\n```\nplain prose") == []
    assert s.outline("") == []


def test_a_flush_left_line_ends_an_item() -> None:
    s = splitter([])
    assert s.outline("- [ ] a\n  of a\nnot of a\n  stray\n- [ ] b\n") == [("a of a", ""), ("b", "")]


def test_only_large_trusted_unheld_opted_in_issues_are_parents() -> None:
    big = TASKS
    issues = [
        issue(1, big, "go"),
        issue(2, "short", "go"),  # small: already workable
        issue(3, big, "go", "operator"),  # for a person
        issue(4, big, "go", author="stranger", association="NONE"),
        issue(5, big, "go", author="github-actions[bot]"),
        issue(6, big, "go"),  # held
        issue(7, big, "go", "vibey-gh:split"),  # already cut
        issue(8, big, "go", "vibey-gh:split-child"),
        issue(9, big, "go", "epic"),  # an epic is cut when opted in
        issue(10, big + "<!-- vibey-gh:split-child parent=1 key=0123456789ab -->", "go"),
        issue(11, big),  # not opted in: the lane never widens what the agent may touch
    ]
    held = {"issues": {"6": {"never_act": True}}}
    assert [i["number"] for i in splitter(issues, expectations=held).parents()] == [1, 9]


def test_what_a_reader_of_the_issue_cannot_see_is_not_a_slice() -> None:
    s = splitter([])
    assert s.outline("<!--\n- [ ] hidden one\n- [ ] hidden two\n-->\nplain") == []
    assert s.outline("~~~\n- [ ] a\n- [ ] b\n~~~\nplain") == []
    assert s.outline("text\n```\n- [ ] a\n- [ ] b\nnever closed") == []
    assert s.outline("<!-- never closed\n- [ ] a\n- [ ] b") == []


def test_a_marker_quoted_into_a_slice_cannot_re_parent_it_or_mask_a_sibling() -> None:
    forged = "<!-- vibey-gh:split-child parent=99 key=ffffffffffff -->"
    body = TASKS.replace("add the flag", f"add the flag {forged}")
    sink = Sink()
    splitter([issue(1, body, "go")], sink).run(apply=True)
    for _, text, _ in sink.created:
        assert "parent=99" not in text and "<!--" not in text.rsplit("\n", 2)[0]
        found = bk.SPLIT_CHILD.search(text)
        assert found and found.group(1) == "1"
    detail = "- [ ] a\n  " + forged + "\n- [ ] b\n"
    assert all("<!--" not in d for _, d in splitter([]).outline(detail))
    first = Sink()
    splitter([issue(1, TASKS, "go")], first).run(apply=True)
    quoted = {"number": 600, "body": "x\n" + forged + "\n" + first.created[0][1]}
    keys = splitter([], Sink(children=[quoted]))._filed()
    assert set(keys) == {(1, bk.SPLIT_CHILD.search(first.created[0][1]).group(2))}


def test_it_files_each_slice_once_and_marks_the_parent_last() -> None:
    sink = Sink()
    report = splitter([issue(1, TASKS, "go")], sink).run(apply=True)
    assert [c[0] for c in sink.created] == ["add the flag (part of #1)", "test it (part of #1)"]
    assert all(c[2] == ["vibey-gh:split-child"] for c in sink.created)
    assert all(bk.SPLIT_CHILD.search(c[1]) for c in sink.created)
    assert sink.marked[0][:2] == (1, "vibey-gh:split")
    assert "#501 add the flag" in sink.marked[0][2] and "#502 test it" in sink.marked[0][2]
    assert report[0] == "#1: 2 slice(s)" and "filed #501: add the flag" in report[1]
    assert {"vibey-gh:split-child", "vibey-gh:split"} <= set(sink.labels)


def test_a_replayed_run_files_nothing_twice() -> None:
    first = Sink()
    splitter([issue(1, TASKS, "go")], first).run(apply=True)
    existing = [{"number": 600 + n, "body": c[1]} for n, c in enumerate(first.created)]
    again = Sink(children=existing)
    report = splitter([issue(1, TASKS, "go")], again).run(apply=True)
    assert again.created == []
    assert "#600 exists: add the flag" in "\n".join(report)
    assert "#600 add the flag" in again.marked[0][2]  # the parent is still marked, children named


def test_a_dry_run_files_and_labels_nothing() -> None:
    sink = Sink()
    report = splitter([issue(1, TASKS, "go")], sink).run(apply=False)
    assert sink.created == sink.marked == sink.labels == []
    assert "  would file: add the flag (part of #1)" in report


def test_slices_over_the_cap_stay_on_the_parent() -> None:
    body = "x" * 250 + "\n" + "".join(f"- [ ] step {n}\n" for n in range(5))
    sink = Sink()
    report = splitter([issue(1, body, "go")], sink).run(apply=True)
    assert len(sink.created) == 3
    assert "2 left on it" in report[0] and "2 more slice(s) stay" in sink.marked[0][2]


def test_a_title_is_cut_and_duplicate_slices_are_filed_once() -> None:
    body = "x" * 250 + "\n- [ ] " + "long " * 40 + "\n- [ ] same\n- [ ] Same\n"
    sink = Sink()
    splitter([issue(1, body, "go")], sink).run(apply=True)
    assert len(sink.created) == 2
    assert "…" in sink.created[0][0] and len(sink.created[0][0]) < 125


def test_an_unlinked_slice_is_still_filed_and_says_so() -> None:
    sink = Sink(link=False)
    report = splitter([issue(1, TASKS, "go")], sink).run(apply=True)
    assert len(sink.created) == 2
    assert "not linked as a sub-issue" in "\n".join(report)


def test_an_issue_without_structure_is_reported_and_costs_no_quota() -> None:
    issues = [issue(n, "x" * 300 if n == 1 else TASKS, "go") for n in (1, 2, 3, 4)]
    report = splitter(issues, Sink()).run(apply=False)
    assert report[0] == "#1: too large, but no task list, steps or sections to cut on"
    assert report[1].startswith("#2: ") and any(line.startswith("#3: ") for line in report)
    assert "#4: waits for a later run (2 per run)" in report


def test_it_does_nothing_when_switched_off_or_when_nothing_is_large() -> None:
    sink = Sink()
    off = splitter([issue(1, TASKS, "go")], sink, settings={"enabled": False})
    assert "switched off" in off.run(apply=True)[0] and sink.created == []
    assert splitter([issue(1, "short", "go")]).run(apply=True) == [
        "No open issue is too large to hand an agent."
    ]


def test_the_cli_refuses_an_unknown_command(capsys) -> None:
    assert sp.main([]) == 2 and sp.main(["nope"]) == 2


def test_the_cli_plans_against_the_declared_settings(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sp.bk, "GhBacklogSource", lambda: Source([issue(1, "short", "go")]))
    monkeypatch.setattr(sp, "GhSplitSink", Sink)
    assert sp.main(["plan"]) == 0
    assert capsys.readouterr().out.strip() == "No open issue is too large to hand an agent."
    assert Path(sp.REPO / "scripts/daily_lanes.toml").is_file()


class _Proc:
    def __init__(self, out: str = "", code: int = 0, err: str = "") -> None:
        self.stdout, self.returncode, self.stderr = out, code, err


def test_the_gh_sink_speaks_the_forges_cli(monkeypatch) -> None:
    calls: list[tuple[tuple[str, ...], str | None]] = []
    answers = {"create": '{"id": 7, "number": 8}', "list": '{"number": 3, "body": "b"}\n\n'}

    def run(argv, input=None, capture_output=True, text=True, check=False):
        calls.append((tuple(argv), input))
        joined = " ".join(argv)
        if "sub_issues" in joined:
            return _Proc(code=1, err="nope") if "sub_issue_id=99" in joined else _Proc()
        if "-X POST repos/{owner}/{repo}/issues" in joined:
            return _Proc(answers["create"])
        return _Proc(answers["list"])

    monkeypatch.setattr(sp.subprocess, "run", run)
    sink = sp.GhSplitSink()
    assert sink.split_children("lab") == [{"number": 3, "body": "b"}]
    assert sink.create_issue("t", "b", ["lab"]) == {"id": 7, "number": 8}
    assert sink.link_sub_issue(1, 7) is True and sink.link_sub_issue(1, 99) is False
    sink.ensure_label("lab", "fff", "d")
    sink.mark_parent(1, "lab", "note")
    assert any("labels[]=lab" in a for a in calls[1][0])
    assert calls[-2][1] == "note" and calls[-1][0][:3] == ("gh", "issue", "edit")


def test_a_failed_write_raises_so_the_run_fails_visibly(monkeypatch) -> None:
    import pytest

    monkeypatch.setattr(sp.subprocess, "run", lambda *a, **k: _Proc(code=1, err="boom"))
    with pytest.raises(RuntimeError, match="boom"):
        sp.GhSplitSink().ensure_label("x", "fff", "d")


def test_a_wrapped_item_is_titled_by_its_whole_first_paragraph() -> None:
    body = "- [ ] first line of a long sentence\n  that wraps on\n\n  Then a second paragraph.\n- [ ] b\n"
    assert splitter([]).outline(body) == [
        ("first line of a long sentence that wraps on", "Then a second paragraph."),
        ("b", ""),
    ]
