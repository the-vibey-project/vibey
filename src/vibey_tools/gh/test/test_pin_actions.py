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
from vibey_gh.interfaces.pin_actions_interface import ActionUse, PinActionsInterface
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
