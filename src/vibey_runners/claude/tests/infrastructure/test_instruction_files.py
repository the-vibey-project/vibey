# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""infrastructure/capabilities/instruction_files.py — the repository's `CLAUDE.md` and
`AGENTS.md` as instruction text when a capability snapshot switches Claude Code's own settings
off (SP-LOOPS Phase 4, Task 6; R8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from claude_agent_sdk import ClaudeAgentOptions
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore

from claudeloop.domain.mcp_config import McpConfigTranslator
from claudeloop.infrastructure.agent.autonomy import AUTONOMY_SYSTEM_PROMPT_FRAGMENT
from claudeloop.infrastructure.agent.options import build_turn_options
from claudeloop.infrastructure.capabilities.instruction_files import (
    InstructionFileReader,
    InstructionText,
)
from claudeloop.infrastructure.capabilities.snapshot_applier import CapabilitySnapshotApplier
from claudeloop.infrastructure.interfaces import (
    InstructionFileReaderInterface,
    InstructionTextInterface,
)
from tests.capability_documents import CapabilityDocumentWriter

NAMES = ("CLAUDE.md", "AGENTS.md")
CAP = 65536
VOICE_CONTRACT = "Voice contract (mandatory, with no exceptions)"
LAUNCHER = ("/usr/bin/python3", "-m", "vibey_runners.common.capabilities.scrubbed_exec")


class _SilentLogger:
    def bind(self, **kwargs: Any) -> _SilentLogger:
        del kwargs
        return self

    def debug(self, event: str, **kwargs: Any) -> None: ...

    def info(self, event: str, **kwargs: Any) -> None: ...

    def warning(self, event: str, **kwargs: Any) -> None: ...

    def error(self, event: str, **kwargs: Any) -> None: ...


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


# -- through the applier and onto the session's system prompt ----------------------------------


def _applier() -> CapabilitySnapshotApplier:
    return CapabilitySnapshotApplier(
        SnapshotDocumentStore(),
        local_backend=False,
        mcp=McpConfigTranslator(LAUNCHER),
        environ={},
        logger=_SilentLogger(),
        instructions=InstructionFileReader(),
    )


def _append(options: ClaudeAgentOptions) -> str:
    """The preset's `append`; `build_turn_options` always sets the preset form."""
    prompt = cast(dict[str, Any], options.system_prompt)
    return str(prompt["append"])


def test_the_document_names_which_files_are_read_and_the_cap(tmp_path: Path) -> None:
    repo = _repo(tmp_path, CLAUDE_md="Claude rules.", RULES_md="R" * 40)
    path = CapabilityDocumentWriter(tmp_path).write(
        instruction_files=("RULES.md", "CLAUDE.md"), instruction_max_bytes=16
    )
    applied = _applier().load(path, cwd=repo)
    assert applied.system_prompt_append == (
        "RULES.md (40 bytes) is longer than the [loops] instruction_max_bytes of 16; read it "
        "from the repository before you start.\n\n" + _block("CLAUDE.md", "Claude rules.")
    )
    assert applied.instruction_files == ("CLAUDE.md",)
    assert applied.event_payload()["instruction_files"] == ["CLAUDE.md"]
    assert "Claude rules." not in str(applied.event_payload())


def test_the_repository_text_follows_the_voice_contract(tmp_path: Path) -> None:
    repo = _repo(tmp_path, CLAUDE_md="Repository house rules.")
    applied = _applier().load(CapabilityDocumentWriter(tmp_path).write(), cwd=repo)
    options = build_turn_options(
        cwd=str(repo), system_prompt_append="The person's own words.", applied=applied
    )
    append = _append(options)
    voice = append.index(VOICE_CONTRACT)
    autonomy = append.index(AUTONOMY_SYSTEM_PROMPT_FRAGMENT)
    own = append.index("The person's own words.")
    repository = append.index("## Repository instructions (CLAUDE.md)")
    assert voice < autonomy < own < repository
    assert append.endswith(_block("CLAUDE.md", "Repository house rules."))


def test_without_repository_text_the_system_prompt_is_unchanged(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    applied = _applier().load(CapabilityDocumentWriter(tmp_path).write(), cwd=repo)
    assert applied.system_prompt_append == ""
    with_snapshot = build_turn_options(cwd=str(repo), applied=applied)
    without = build_turn_options(cwd=str(repo))
    assert _append(with_snapshot) == _append(without)
