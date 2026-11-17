# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh pin-actions`: every `uses:` pinned to a commit, the tag kept as a comment.

The forge is a fake that answers `GET repos/{owner}/{repo}/commits/{ref}` from a dict and
remembers what it was asked, so a test can say which endpoint was used and that check mode
never asked at all.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import cli
from vibey_gh.interfaces.pin_actions_interface import ActionUse, PinActionsInterface, PinnedUse
from vibey_gh.pin_actions import PinActions

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
PATH = Path("w.yml")


class FakeForge:
    """Answers the commits endpoint from `commits`, keyed by the path after `repos/`."""

    def __init__(self, commits: dict[str, Any] | None = None) -> None:
        self.commits = commits or {}
        self.calls: list[list[str]] = []

    def json(self, args: list[str], **_: Any) -> Any:
        self.calls.append(list(args))
        if args[0] != "api":
            raise AssertionError(f"unexpected call {args}")
        key = args[1].removeprefix("repos/")
        if key not in self.commits:
            raise RuntimeError(f"gh {' '.join(args)}: HTTP 404")
        return self.commits[key]


def pinner(forge: FakeForge | None = None) -> PinActions:
    return PinActions(transport=forge or FakeForge())  # type: ignore[arg-type]


def test_it_satisfies_its_interface() -> None:
    assert isinstance(pinner(), PinActionsInterface)


def test_unpinned_finds_tag_branch_and_latest_refs() -> None:
    text = (
        "steps:\n"
        "  - uses: actions/checkout@v4\n"
        "  - uses: owner/repo@release/v1\n"
        '  - uses: "owner/other@latest"\n'
        "    uses: a/b/sub@main\n"
    )
    assert pinner().unpinned(text, PATH) == [
        ActionUse(PATH, 2, "actions/checkout", "v4"),
        ActionUse(PATH, 3, "owner/repo", "release/v1"),
        ActionUse(PATH, 4, "owner/other", "latest"),
        ActionUse(PATH, 5, "a/b/sub", "main"),
    ]


def test_unpinned_ignores_pinned_local_docker_and_non_uses_text() -> None:
    text = (
        "steps:\n"
        f"  - uses: actions/checkout@{SHA_A} # v4\n"
        "  - uses: ./.github/actions/local\n"
        "  - uses: docker://alpine:3.20\n"
        "  - uses: owner/no-ref\n"
        "  # uses: commented/out@v1\n"
        "  - run: |\n"
        "      echo\n"
        "      uses: in/a-run-block@v1\n"
        "\n"
        "      - uses: still/in-block@v2\n"
        "  - name: after the block\n"
        "    run: echo uses: inline/text@v1\n"
        "  - uses: real/one@v9 # a comment about uses: x@v1\n"
    )
    assert pinner().unpinned(text, PATH) == [ActionUse(PATH, 14, "real/one", "v9")]


def test_a_block_scalar_ends_at_the_next_key_of_the_same_or_lower_indent() -> None:
    text = "  - run: >-\n      uses: a/b@v1\n  - uses: c/d@v2\n"
    assert [u.action for u in pinner().unpinned(text, PATH)] == ["c/d"]


def test_a_reusable_workflow_reference_is_unpinned_like_an_action() -> None:
    text = "jobs:\n  call:\n    uses: o/r/.github/workflows/x.yml@v2\n"
    assert pinner().unpinned(text, PATH) == [
        ActionUse(PATH, 3, "o/r/.github/workflows/x.yml", "v2")
    ]


def test_resolve_asks_the_commits_endpoint_so_an_annotated_tag_gives_its_commit() -> None:
    forge = FakeForge({"actions/checkout/commits/v4": {"sha": SHA_A}})
    assert pinner(forge).resolve("actions/checkout", "v4") == SHA_A
    assert forge.calls == [["api", "repos/actions/checkout/commits/v4"]]
    assert not any("git/ref" in part for call in forge.calls for part in call)


def test_resolve_uses_the_repository_of_a_reusable_workflow_and_keeps_a_slashed_ref() -> None:
    forge = FakeForge({"o/r/commits/release/v1": {"sha": SHA_B}})
    assert pinner(forge).resolve("o/r/.github/workflows/x.yml", "release/v1") == SHA_B
    assert forge.calls == [["api", "repos/o/r/commits/release/v1"]]


@pytest.mark.parametrize("answer", [{}, {"sha": "tag-object"}, {"sha": "ABC"}, ["x"], None])
def test_resolve_refuses_an_answer_that_is_not_a_commit(answer: Any) -> None:
    forge = FakeForge({"o/r/commits/v1": answer})
    with pytest.raises(RuntimeError, match=r"o/r@v1 does not name a commit"):
        pinner(forge).resolve("o/r", "v1")


def test_rewrite_appends_the_ref_as_a_comment_and_keeps_an_existing_comment() -> None:
    text = (
        "  - uses: a/b@v4\n"
        "  - uses: c/d@v1 # keep me\n"
        '  - uses: "e/f@v2"\n'
        "  - uses: g/h@v3   # spaced\n"
    )
    shas = {("a/b", "v4"): SHA_A, ("c/d", "v1"): SHA_B, ("e/f", "v2"): SHA_C, ("g/h", "v3"): SHA_A}
    assert pinner().rewrite(text, shas) == (
        f"  - uses: a/b@{SHA_A} # v4\n"
        f"  - uses: c/d@{SHA_B} # v1 # keep me\n"
        f'  - uses: "e/f@{SHA_C}" # v2\n'
        f"  - uses: g/h@{SHA_A} # v3 # spaced\n"
    )


def test_rewrite_leaves_unanswered_pinned_and_odd_lines_byte_for_byte() -> None:
    text = (
        f"  - uses: a/b@{SHA_A} # v4\n"
        "  - uses: unanswered/x@v1\n"
        "  - uses: ./local\n"
        "  - uses: odd/tail@v1 trailing words\n"
        "  - run: echo uses: x/y@v1\n"
    )
    shas = {("odd/tail", "v1"): SHA_B, ("a/b", "v4"): SHA_C}
    assert pinner().rewrite(text, shas) == text


def test_rewrite_is_idempotent() -> None:
    text = "  - uses: a/b@v4\n  - uses: c/d@v1 # note\n"
    shas = {("a/b", "v4"): SHA_A, ("c/d", "v1"): SHA_B}
    once = pinner().rewrite(text, shas)
    assert pinner().rewrite(once, shas) == once
    assert pinner().unpinned(once, PATH) == []


def test_check_mode_makes_no_network_call_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    original = "steps:\n  - uses: a/b@v4\n  - uses: c/d@main\n"
    workflow.write_text(original)
    forge = FakeForge()
    assert pinner(forge).run([workflow], apply=False) == 1
    out = capsys.readouterr().out
    assert f"{workflow}:2: a/b@v4 is not pinned" in out
    assert f"{workflow}:3: c/d@main is not pinned" in out
    assert forge.calls == []
    assert workflow.read_text() == original


def test_check_mode_exits_0_when_everything_is_pinned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{SHA_A} # v4\n")
    forge = FakeForge()
    assert pinner(forge).run([workflow], apply=False) == 0
    assert "every uses: is pinned" in capsys.readouterr().out
    assert forge.calls == []


def test_apply_resolves_each_pair_once_and_rewrites_every_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    one, two = tmp_path / "one.yml", tmp_path / "two.yml"
    one.write_text("  - uses: a/b@v4\n  - uses: c/d@v1\n")
    two.write_text("  - uses: a/b@v4\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": SHA_A}, "c/d/commits/v1": {"sha": SHA_B}})
    assert pinner(forge).run([one, two], apply=True) == 0
    assert len(forge.calls) == 2
    assert one.read_text() == f"  - uses: a/b@{SHA_A} # v4\n  - uses: c/d@{SHA_B} # v1\n"
    assert two.read_text() == f"  - uses: a/b@{SHA_A} # v4\n"
    assert "pinned 3 uses to 2 commits" in capsys.readouterr().out
    assert pinner(forge).run([one, two], apply=True) == 0
    assert len(forge.calls) == 2


def test_a_ref_that_does_not_resolve_fails_loudly_and_leaves_the_file_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good, bad = tmp_path / "good.yml", tmp_path / "bad.yml"
    good.write_text("  - uses: a/b@v4\n")
    bad.write_text("  - uses: gone/x@v1\n  - uses: also/gone@v2\n")
    before = (good.read_text(), bad.read_text())
    forge = FakeForge({"a/b/commits/v4": {"sha": SHA_A}})
    assert pinner(forge).run([good, bad], apply=True) == 1
    out = capsys.readouterr().out
    assert "HTTP 404" in out and "gone/x" in out and "also/gone" in out
    assert "nothing written" in out
    assert (good.read_text(), bad.read_text()) == before


def test_the_default_paths_are_the_workflows_and_the_composite_actions(tmp_path: Path) -> None:
    for name in (
        ".github/workflows/b.yml",
        ".github/workflows/a.yml",
        ".github/actions/x/action.yml",
    ):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("")
    (tmp_path / ".github/workflows/notes.md").write_text("")
    assert PinActions.default_paths(tmp_path) == [
        tmp_path / ".github/workflows/a.yml",
        tmp_path / ".github/workflows/b.yml",
        tmp_path / ".github/actions/x/action.yml",
    ]


def test_declare_and_dispatch_run_the_check_over_explicit_and_default_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    parser = PinActions.declare(argparse.ArgumentParser())
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("  - uses: a/b@v4\n")
    explicit = tmp_path / "pinned.yml"
    explicit.write_text(f"  - uses: a/b@{SHA_A}\n")
    assert PinActions.dispatch(parser.parse_args([str(explicit)])) == 0
    monkeypatch.chdir(tmp_path)
    args = parser.parse_args([])
    assert args.apply is False and args.paths == []
    assert PinActions.dispatch(args) == 1
    assert "ci.yml:1: a/b@v4 is not pinned" in capsys.readouterr().out


def test_the_cli_registers_pin_actions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pinned = tmp_path / "w.yml"
    pinned.write_text(f"  - uses: a/b@{SHA_A}\n")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["pin-actions", str(pinned)]) == 0


def test_apply_fails_for_a_line_it_could_not_rewrite_and_still_writes_the_rest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text("  - uses: a/b@v4\n  - uses: odd/tail@v1 trailing words\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": SHA_A}, "odd/tail/commits/v1": {"sha": SHA_B}})
    assert pinner(forge).run([workflow], apply=True) == 1
    out = capsys.readouterr().out
    assert f"{workflow}:2: odd/tail@v1 could not be rewritten" in out
    assert "pinned" not in out.replace("could not be pinned", "")
    assert workflow.read_text() == (
        f"  - uses: a/b@{SHA_A} # v4\n  - uses: odd/tail@v1 trailing words\n"
    )


# --- refreshing the pins that already exist -------------------------------------------------
#
# A pin never moves by itself, and Dependabot cannot be told to skip only the managed files, so
# `--refresh` is the one path that moves the pins of the hand-written workflows. Every claim it
# prints has to be one it observed: a stale pin is named with both commits, a pin it cannot
# check is listed rather than skipped, and check mode never writes.

OLD = "1" * 40
NEW = "2" * 40
NEWER = "3" * 40


class FakeIssues:
    """Records the one tracking issue the freshness check keeps, or refuses to."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.raised: list[dict[str, Any]] = []
        self.resolved: list[tuple[str, str]] = []

    def find(self, key: str) -> int | None:
        return None

    def raise_issue(
        self,
        key: str,
        title: str,
        body: str,
        *,
        event: str = "",
        event_key: str = "",
        labels: Any = (),
    ) -> tuple[int, bool]:
        if self.fail:
            raise RuntimeError("gh issue: HTTP 403")
        self.raised.append({"key": key, "title": title, "body": body, "labels": list(labels)})
        return 7, True

    def resolve(self, key: str, comment: str) -> int | None:
        if self.fail:
            raise RuntimeError("gh issue: HTTP 403")
        self.resolved.append((key, comment))
        return 7


def refresher(
    forge: FakeForge | None = None,
    *,
    hold: tuple[str, ...] = (),
    issues: FakeIssues | None = None,
    labels: tuple[str, ...] = (),
) -> PinActions:
    return PinActions(
        transport=forge or FakeForge(),  # type: ignore[arg-type]
        issues=issues,  # type: ignore[arg-type]
        hold=hold,
        labels=labels,
    )


def test_pinned_reads_the_ref_from_the_trailing_comment() -> None:
    text = (
        "steps:\n"
        f"  - uses: actions/checkout@{OLD} # v4\n"
        f'  - uses: "o/r@{OLD}" # release/v1 # keep me\n'
        f"  - uses: o/bare@{OLD}\n"
        f"  - uses: o/words@{OLD} # !!\n"
        "  - uses: o/unpinned@v1\n"
        "  - uses: ./local\n"
        "  - uses: docker://alpine:3\n"
        "  - run: |\n"
        f"      uses: o/in-a-block@{OLD} # v1\n"
    )
    assert refresher().pinned(text, PATH) == [
        PinnedUse(PATH, 2, "actions/checkout", OLD, "v4"),
        PinnedUse(PATH, 3, "o/r", OLD, "release/v1"),
        PinnedUse(PATH, 4, "o/bare", OLD, None),
        PinnedUse(PATH, 5, "o/words", OLD, None),
    ]


def test_restamp_moves_only_the_sha_and_keeps_the_comment_and_the_quotes() -> None:
    text = (
        f"  - uses: a/b@{OLD} # v4\n"
        f'  - uses: "c/d@{OLD}" # v1 # keep me\n'
        f"  - uses: e/f@{OLD} # v2\n"
        f"  - uses: g/h@{NEW} # v3\n"
        "  - uses: i/j@v9\n"
    )
    shas = {("a/b", "v4"): NEW, ("c/d", "v1"): NEWER, ("g/h", "v3"): NEW}
    assert refresher().restamp(text, shas) == (
        f"  - uses: a/b@{NEW} # v4\n"
        f'  - uses: "c/d@{NEWER}" # v1 # keep me\n'
        f"  - uses: e/f@{OLD} # v2\n"
        f"  - uses: g/h@{NEW} # v3\n"
        "  - uses: i/j@v9\n"
    )


def test_restamp_is_idempotent() -> None:
    text = f"  - uses: a/b@{OLD} # v4\n"
    once = refresher().restamp(text, {("a/b", "v4"): NEW})
    assert refresher().restamp(once, {("a/b", "v4"): NEW}) == once


def test_refresh_moves_a_stale_pin_names_both_commits_and_is_idempotent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: actions/checkout@{OLD} # v4\n  - uses: c/d@{NEW} # v1\n")
    forge = FakeForge({"actions/checkout/commits/v4": {"sha": NEW}, "c/d/commits/v1": {"sha": NEW}})
    assert refresher(forge).refresh([workflow], write=True) == 0
    assert workflow.read_text() == (
        f"  - uses: actions/checkout@{NEW} # v4\n  - uses: c/d@{NEW} # v1\n"
    )
    out = capsys.readouterr().out
    assert f"{workflow}:1: actions/checkout (v4) {OLD} -> {NEW}" in out
    assert "refreshed 1 pin" in out
    assert refresher(forge).refresh([workflow], write=True) == 0
    assert "every pin is current" in capsys.readouterr().out


def test_refresh_asks_each_distinct_action_and_ref_once(tmp_path: Path) -> None:
    one, two = tmp_path / "one.yml", tmp_path / "two.yml"
    one.write_text(f"  - uses: a/b@{OLD} # v4\n  - uses: a/b@{OLD} # v4\n")
    two.write_text(f"  - uses: a/b@{OLD} # v4\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert refresher(forge).refresh([one, two], write=True) == 0
    assert forge.calls == [["api", "repos/a/b/commits/v4"]]
    assert two.read_text() == f"  - uses: a/b@{NEW} # v4\n"


def test_check_stale_writes_nothing_and_exits_1_with_the_stale_pins_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    original = f"  - uses: a/b@{OLD} # v4\n"
    workflow.write_text(original)
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert refresher(forge).refresh([workflow], write=False) == 1
    out = capsys.readouterr().out
    assert f"{workflow}:1: a/b (v4) {OLD} -> {NEW}" in out
    assert "1 stale pin" in out and "--refresh" in out
    assert workflow.read_text() == original


def test_a_pin_that_cannot_be_refreshed_is_listed_and_fails_but_the_rest_still_move(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(
        f"  - uses: a/b@{OLD} # v4\n"
        f"  - uses: no/comment@{OLD}\n"
        f"  - uses: gone/tag@{OLD} # v9\n"
        "  - uses: not/pinned@v1\n"
    )
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert refresher(forge).refresh([workflow], write=True) == 1
    out = capsys.readouterr().out
    assert f"{workflow}:2: no/comment could not be refreshed: no `# <ref>` comment" in out
    assert f"{workflow}:3: gone/tag could not be refreshed: " in out and "HTTP 404" in out
    assert f"{workflow}:4: not/pinned@v1 could not be refreshed: not pinned" in out
    assert "3 could not be refreshed" in out
    lines = workflow.read_text().splitlines()
    assert lines[0] == f"  - uses: a/b@{NEW} # v4"
    assert lines[1:3] == [f"  - uses: no/comment@{OLD}", f"  - uses: gone/tag@{OLD} # v9"]


def test_a_ref_that_names_an_expression_is_not_asked_about_and_is_listed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{OLD} # ${{{{ inputs.ref }}}}\n")
    forge = FakeForge()
    assert refresher(forge).refresh([workflow], write=True) == 1
    assert forge.calls == []
    assert "could not be refreshed: the ref is an expression" in capsys.readouterr().out


def test_a_held_action_is_reported_left_alone_and_never_counted_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    original = f"  - uses: a/b/sub@{OLD} # v4\n  - uses: c/d@{OLD} # v1\n"
    workflow.write_text(original)
    forge = FakeForge({"c/d/commits/v1": {"sha": OLD}})
    assert refresher(forge, hold=("a/b",)).refresh([workflow], write=False) == 0
    out = capsys.readouterr().out
    assert f"{workflow}:1: a/b/sub is held on {OLD}" in out
    assert "1 held" in out
    assert forge.calls == [["api", "repos/c/d/commits/v1"]]
    assert workflow.read_text() == original


def test_a_file_with_nothing_to_change_is_not_written_back(tmp_path: Path) -> None:
    current, stale = tmp_path / "current.yml", tmp_path / "stale.yml"
    current.write_bytes(f"  - uses: a/b@{NEW} # v4\r\n".encode())
    stale.write_text(f"  - uses: a/b@{OLD} # v4\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert refresher(forge).refresh([current, stale], write=True) == 0
    assert current.read_bytes() == f"  - uses: a/b@{NEW} # v4\r\n".encode()


def test_apply_does_not_rewrite_a_file_it_has_nothing_to_pin_in(tmp_path: Path) -> None:
    pinned, loose = tmp_path / "pinned.yml", tmp_path / "loose.yml"
    pinned.write_bytes(f"  - uses: a/b@{OLD} # v4\r\n".encode())
    loose.write_text("  - uses: c/d@v1\n")
    forge = FakeForge({"c/d/commits/v1": {"sha": NEW}})
    assert pinner(forge).run([pinned, loose], apply=True) == 0
    assert pinned.read_bytes() == f"  - uses: a/b@{OLD} # v4\r\n".encode()
    assert loose.read_text() == f"  - uses: c/d@{NEW} # v1\n"


def test_apply_pins_the_rest_and_lists_a_ref_that_is_an_expression(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text("  - uses: a/b@v4\n  - uses: x/y@${{ inputs.ref }}\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert pinner(forge).run([workflow], apply=True) == 1
    out = capsys.readouterr().out
    assert f"{workflow}:2: x/y@${{{{ cannot be pinned: the ref is an expression" in out
    assert forge.calls == [["api", "repos/a/b/commits/v4"]]
    assert workflow.read_text().startswith(f"  - uses: a/b@{NEW} # v4\n")


def test_apply_with_only_expression_refs_asks_nothing_and_fails(tmp_path: Path) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text("  - uses: x/y@${{ inputs.ref }}\n")
    forge = FakeForge()
    assert pinner(forge).run([workflow], apply=True) == 1
    assert forge.calls == []


class _BadJson:
    def json(self, args: list[str], **_: Any) -> Any:
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


def test_resolve_turns_an_undecodable_answer_into_the_error_the_callers_handle() -> None:
    with pytest.raises(RuntimeError, match=r"o/r@v1: .*Expecting value"):
        PinActions(transport=_BadJson()).resolve("o/r", "v1")  # type: ignore[arg-type]


def test_announce_opens_one_issue_for_stale_pins_and_exits_0(tmp_path: Path) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{OLD} # v4\n  - uses: gone/x@{OLD} # v9\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    issues = FakeIssues()
    tool = refresher(forge, issues=issues, labels=("ci-hygiene",))
    assert tool.announce([workflow]) == 0
    assert workflow.read_text() == f"  - uses: a/b@{OLD} # v4\n  - uses: gone/x@{OLD} # v9\n"
    (raised,) = issues.raised
    assert raised["key"] == "pin-freshness" and raised["labels"] == ["ci-hygiene"]
    assert f"{workflow}:1: a/b (v4) {OLD} -> {NEW}" in raised["body"]
    assert f"{workflow}:2: gone/x could not be refreshed" in raised["body"]
    assert "vibey-gh pin-actions --refresh" in raised["body"]
    assert issues.resolved == []


def test_announce_closes_the_issue_when_every_pin_is_current(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{NEW} # v4\n")
    issues = FakeIssues()
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert refresher(forge, issues=issues).announce([workflow]) == 0
    assert issues.raised == [] and issues.resolved[0][0] == "pin-freshness"
    assert "every pin is current" in capsys.readouterr().out


def test_announce_fails_when_the_issue_cannot_be_kept(tmp_path: Path) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{OLD} # v4\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert refresher(forge, issues=FakeIssues(fail=True)).announce([workflow]) == 1
    workflow.write_text(f"  - uses: a/b@{NEW} # v4\n")
    assert refresher(forge, issues=FakeIssues(fail=True)).announce([workflow]) == 1


def test_announce_builds_its_own_tracking_issue_when_none_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    built: list[object] = []

    class Built(FakeIssues):
        def __init__(self) -> None:
            super().__init__()
            built.append(self)

    monkeypatch.setattr("vibey_gh.pin_actions.TrackingIssue", Built)
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{NEW} # v4\n")
    forge = FakeForge({"a/b/commits/v4": {"sha": NEW}})
    assert PinActions(transport=forge).announce([workflow]) == 0  # type: ignore[arg-type]
    assert len(built) == 1


def test_the_flags_are_exclusive_and_dispatch_reads_hold_and_labels_from_the_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    parser = PinActions.declare(argparse.ArgumentParser())
    with pytest.raises(SystemExit):
        parser.parse_args(["--refresh", "--check-stale"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--apply", "--refresh"])
    (tmp_path / ".vibey-gh.toml").write_text('[pin_actions]\nhold = ["a/b"]\nlabels = ["x"]\n')
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{OLD} # v4\n")
    monkeypatch.chdir(tmp_path)
    seen: list[PinActions] = []
    real = PinActions.refresh

    def spy(self: PinActions, paths: Any, *, write: bool) -> int:
        seen.append(self)
        return real(self, paths, write=write)

    monkeypatch.setattr(PinActions, "refresh", spy)
    assert PinActions.dispatch(parser.parse_args(["--check-stale", str(workflow)])) == 0
    assert "is held" in capsys.readouterr().out
    assert PinActions.dispatch(parser.parse_args(["--refresh", str(workflow)])) == 0
    assert len(seen) == 2


def test_dispatch_announces_with_the_tracking_issue_flag_and_refuses_it_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    parser = PinActions.declare(argparse.ArgumentParser())
    workflow = tmp_path / "w.yml"
    workflow.write_text(f"  - uses: a/b@{NEW} # v4\n")
    monkeypatch.chdir(tmp_path)
    announced: list[list[Path]] = []

    def fake(self: PinActions, paths: Any) -> int:
        announced.append(list(paths))
        return 0

    monkeypatch.setattr(PinActions, "announce", fake)
    args = parser.parse_args(["--check-stale", "--tracking-issue", str(workflow)])
    assert PinActions.dispatch(args) == 0 and announced == [[workflow]]
    assert PinActions.dispatch(parser.parse_args(["--tracking-issue", str(workflow)])) == 2
    assert "--tracking-issue goes with --check-stale" in capsys.readouterr().out


def test_the_cli_registers_the_refresh_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pinned = tmp_path / "w.yml"
    pinned.write_text(f"  - uses: a/b@{SHA_A}\n")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["pin-actions", "--check-stale", str(pinned)]) == 1


def test_the_pin_actions_table_is_validated_and_loaded(tmp_path: Path) -> None:
    from vibey_gh.config import PinActionsConfig, load_config

    assert load_config(tmp_path).pin_actions == PinActionsConfig()
    (tmp_path / ".vibey-gh.toml").write_text('[pin_actions]\nhold = ["a/b"]\nlabels = ["x"]\n')
    assert load_config(tmp_path).pin_actions == PinActionsConfig(("a/b",), ("x",))
    for bad in (("a",), ("a/b", "a/b"), ("",), ("a/b/c",)):
        with pytest.raises(ValueError, match="pin_actions.hold"):
            PinActionsConfig(hold=bad)
    with pytest.raises(ValueError, match="pin_actions.labels"):
        PinActionsConfig(labels=("x", "x"))
