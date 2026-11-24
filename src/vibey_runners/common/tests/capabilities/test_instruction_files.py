# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""capabilities/instruction_files.py — the repository's `CLAUDE.md` and `AGENTS.md` as
instruction text, read by every loop that is given a capability snapshot (SP-LOOPS Phase 4,
Task 6; R8; moved here from claudeloop in Phase 5, R12, with these tests unchanged). With a
standing budget (Phase 5, R9), a file that does not fit what remains is named, never cut."""

from __future__ import annotations

from pathlib import Path

from vibey_runners.common.capabilities.instruction_files import (
    InstructionFileReader,
    InstructionText,
)
from vibey_runners.common.capabilities.interfaces.instruction_file_reader_interface import (
    InstructionFileReaderInterface,
    InstructionTextInterface,
)

NAMES = ("CLAUDE.md", "AGENTS.md")
CAP = 65536


class _RefusingReader:
    """A reader whose open is refused, as it would be for a file swapped after the check or one
    the run's user may not read."""

    def open_regular(self, path: Path) -> int:
        raise PermissionError(13, "Permission denied", str(path))

    def read_text(self, path: Path, limit: int) -> str:
        raise AssertionError("the instruction reader opens descriptors; it never reads text")


def _repo(tmp_path: Path, **files: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    for name, body in files.items():
        (repo / name.replace("_", ".")).write_text(body, encoding="utf-8")
    return repo


def _block(name: str, body: str) -> str:
    return f"## Repository instructions ({name})\n\n{body}"


def test_the_reader_and_its_record_satisfy_their_interfaces() -> None:
    assert isinstance(InstructionFileReader(), InstructionFileReaderInterface)
    assert isinstance(InstructionText("", (), ()), InstructionTextInterface)


def test_claude_md_and_agents_md_are_inlined_in_order(tmp_path: Path) -> None:
    repo = _repo(tmp_path, CLAUDE_md="Claude rules.\n", AGENTS_md="Agents rules.\n")
    result = InstructionFileReader().read(repo, NAMES, CAP)
    both = _block("CLAUDE.md", "Claude rules.\n") + "\n\n" + _block("AGENTS.md", "Agents rules.\n")
    assert result == InstructionText(
        text=both,
        inlined=("CLAUDE.md", "AGENTS.md"),
        named=(),
    )
    reversed_order = InstructionFileReader().read(repo, ("AGENTS.md", "CLAUDE.md"), CAP)
    assert reversed_order.text.index("(AGENTS.md)") < reversed_order.text.index("(CLAUDE.md)")
    assert reversed_order.inlined == ("AGENTS.md", "CLAUDE.md")


def test_a_file_exactly_at_the_cap_is_inlined_whole(tmp_path: Path) -> None:
    body = "A" * 32
    repo = _repo(tmp_path, CLAUDE_md=body)
    result = InstructionFileReader().read(repo, NAMES, 32)
    assert result.text == _block("CLAUDE.md", body)
    assert result.inlined == ("CLAUDE.md",)


def test_a_file_over_the_cap_is_named_never_truncated(tmp_path: Path) -> None:
    body = "QZXPREFIX" + "b" * 40
    repo = _repo(tmp_path, CLAUDE_md=body, AGENTS_md="Agents rules.")
    result = InstructionFileReader().read(repo, NAMES, 32)
    line = (
        f"CLAUDE.md ({len(body)} bytes) is longer than the [loops] instruction_max_bytes of 32; "
        "read it from the repository before you start."
    )
    assert result.text == line + "\n\n" + _block("AGENTS.md", "Agents rules.")
    assert "QZX" not in result.text
    assert "## Repository instructions (CLAUDE.md)" not in result.text
    assert result.named == ("CLAUDE.md",)
    assert result.inlined == ("AGENTS.md",)


def test_a_symlinked_claude_md_is_refused_and_named(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere.md"
    target.write_text("SYMLINK-TARGET-BODY", encoding="utf-8")
    repo = _repo(tmp_path)
    (repo / "CLAUDE.md").symlink_to(target)
    result = InstructionFileReader().read(repo, NAMES, CAP)
    assert result.text == "CLAUDE.md is a symbolic link, which is never followed; it was not read."
    assert "SYMLINK-TARGET-BODY" not in result.text
    assert result.named == ("CLAUDE.md",)
    assert result.inlined == ()


def test_a_folder_in_place_of_a_file_is_named(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "CLAUDE.md").mkdir()
    result = InstructionFileReader().read(repo, NAMES, CAP)
    assert result.text == "CLAUDE.md is not a regular file; it was not read."
    assert result.named == ("CLAUDE.md",)


def test_bytes_that_are_not_utf8_are_named(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "AGENTS.md").write_bytes(b"NOTUTF8\xff\xfe")
    result = InstructionFileReader().read(repo, NAMES, CAP)
    assert result.text == "AGENTS.md is not UTF-8 text; it was not read."
    assert "NOTUTF8" not in result.text
    assert result.named == ("AGENTS.md",)


def test_a_file_that_cannot_be_opened_is_named(tmp_path: Path) -> None:
    repo = _repo(tmp_path, CLAUDE_md="Claude rules.")
    result = InstructionFileReader(_RefusingReader()).read(repo, NAMES, CAP)
    assert result.text == "CLAUDE.md could not be opened; it was not read."
    assert result.named == ("CLAUDE.md",)


def test_a_folder_that_cannot_be_looked_in_names_the_file(tmp_path: Path) -> None:
    not_a_folder = tmp_path / "file"
    not_a_folder.write_text("x", encoding="utf-8")
    result = InstructionFileReader().read(not_a_folder, ("CLAUDE.md",), CAP)
    assert result.text == "CLAUDE.md could not be opened; it was not read."
    assert result.named == ("CLAUDE.md",)


def test_a_missing_file_is_skipped_silently_and_counted_nowhere(tmp_path: Path) -> None:
    repo = _repo(tmp_path, AGENTS_md="Agents rules.")
    result = InstructionFileReader().read(repo, NAMES, CAP)
    assert result == InstructionText(
        text=_block("AGENTS.md", "Agents rules."), inlined=("AGENTS.md",), named=()
    )
    empty = InstructionFileReader().read(_repo(tmp_path / "bare"), NAMES, CAP)
    assert empty == InstructionText(text="", inlined=(), named=())


def test_a_nested_claude_md_is_not_read(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    for nested in ("sub", ".claude", "docs/deeper"):
        folder = repo / nested
        folder.mkdir(parents=True)
        (folder / "CLAUDE.md").write_text("NESTED-RULES", encoding="utf-8")
        (folder / "AGENTS.md").write_text("NESTED-RULES", encoding="utf-8")
    result = InstructionFileReader().read(repo, NAMES, CAP)
    assert result == InstructionText(text="", inlined=(), named=())


# -- within a loop's standing budget (Phase 5, R9 and R12) ------------------------------------


def _does_not_fit(name: str, size: int) -> str:
    return (
        f"{name} ({size} bytes) does not fit this loop's standing context "
        "([loops] capability_prompt_tokens); read it from the repository before you start."
    )


def test_a_file_that_does_not_fit_the_budget_is_named_never_cut(tmp_path: Path) -> None:
    claude = "Claude rules.\n" + "QZXBODY " * 40
    repo = _repo(tmp_path, CLAUDE_md=claude, AGENTS_md="Agents rules.")
    agents = _block("AGENTS.md", "Agents rules.")
    line = _does_not_fit("CLAUDE.md", len(claude.encode("utf-8")))
    # Room for the line, the joiner and the AGENTS.md block, but not for the CLAUDE.md block.
    budget = len(line) + 2 + len(agents)
    assert len(_block("CLAUDE.md", claude)) > budget
    result = InstructionFileReader().read(repo, NAMES, CAP, budget_chars=budget)
    assert result.text == line + "\n\n" + agents
    assert len(result.text) == budget
    assert "QZXBODY" not in result.text
    assert result.named == ("CLAUDE.md",)
    assert result.inlined == ("AGENTS.md",)


def test_a_file_that_fits_exactly_what_remains_is_inlined_whole(tmp_path: Path) -> None:
    repo = _repo(tmp_path, CLAUDE_md="Claude rules.", AGENTS_md="Agents rules.")
    whole = _block("CLAUDE.md", "Claude rules.") + "\n\n" + _block("AGENTS.md", "Agents rules.")
    exact = InstructionFileReader().read(repo, NAMES, CAP, budget_chars=len(whole))
    assert exact.text == whole
    assert exact.inlined == ("CLAUDE.md", "AGENTS.md")
    short = InstructionFileReader().read(repo, NAMES, CAP, budget_chars=len(whole) - 1)
    assert short.inlined == ("CLAUDE.md",)
    assert short.named == ("AGENTS.md",)
    assert short.text.endswith(_does_not_fit("AGENTS.md", len("Agents rules.")))


def test_the_named_lines_count_against_the_budget_too(tmp_path: Path) -> None:
    """A line that names a file (over the cap, a symlink) still takes its room, so a later file
    that would fit an empty budget is named once the room is gone."""
    repo = _repo(tmp_path, CLAUDE_md="C" * 64, AGENTS_md="Agents rules.")
    agents = _block("AGENTS.md", "Agents rules.")
    result = InstructionFileReader().read(repo, NAMES, 32, budget_chars=len(agents))
    assert result.named == ("CLAUDE.md", "AGENTS.md")
    assert result.inlined == ()
    assert "Agents rules." not in result.text


def test_without_a_budget_the_reader_is_claudeloops_unchanged(tmp_path: Path) -> None:
    big = "B" * 10_000
    repo = _repo(tmp_path, CLAUDE_md=big)
    assert InstructionFileReader().read(repo, NAMES, CAP).text == _block("CLAUDE.md", big)
    assert InstructionFileReader().read(repo, NAMES, CAP, budget_chars=None).inlined == (
        "CLAUDE.md",
    )
