# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The repository's `CLAUDE.md` and `AGENTS.md` on claudeloop's system prompt when a capability
snapshot switches Claude Code's own settings off (SP-LOOPS Phase 4, Task 6; R8). The reader itself
moved to `vibey_runners.common.capabilities.instruction_files` (Phase 5, R12), and its own tests
moved with it to common's `tests/capabilities/test_instruction_files.py`; these are the ones that
need claudeloop's applier and prompt."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from claude_agent_sdk import ClaudeAgentOptions
from vibey_runners.common.capabilities.instruction_files import InstructionFileReader
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore

from claudeloop.domain.mcp_config import McpConfigTranslator
from claudeloop.infrastructure.agent.autonomy import AUTONOMY_SYSTEM_PROMPT_FRAGMENT
from claudeloop.infrastructure.agent.options import build_turn_options
from claudeloop.infrastructure.capabilities.snapshot_applier import CapabilitySnapshotApplier
from tests.capability_documents import CapabilityDocumentWriter

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


def _repo(tmp_path: Path, **files: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    for name, body in files.items():
        (repo / name.replace("_", ".")).write_text(body, encoding="utf-8")
    return repo


def _block(name: str, body: str) -> str:
    return f"## Repository instructions ({name})\n\n{body}"


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
