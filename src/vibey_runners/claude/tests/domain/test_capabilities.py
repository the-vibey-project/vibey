# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""domain/capabilities.py — what a run's capability snapshot gives one claudeloop session
(SP-LOOPS Phase 4, Task 4; R4, R11)."""

from __future__ import annotations

from claudeloop.domain.capabilities import (
    CLAUDE_BUILTIN_WEB_TOOLS,
    EXIT_CAPABILITIES_REFUSED,
    AppliedCapabilities,
)
from claudeloop.domain.errors import (
    AutoclaudeError,
    CapabilityFlagConflict,
    CapabilitySnapshotRefused,
)
from claudeloop.domain.interfaces import (
    AppliedCapabilitiesInterface,
    CapabilitySnapshotRefusedInterface,
)

DIGEST = "sha256:" + "ab" * 32


def _applied(**overrides: object) -> AppliedCapabilities:
    values: dict[str, object] = {
        "digest": DIGEST,
        "plugin_dirs": ("/runs/r1/plugins/a", "/runs/r1/plugins/b"),
        "skills": ("a:one", "b:two", "b:three"),
        "mcp_servers": {"docs": {"type": "http", "url": "https://example.invalid/mcp"}},
        "disallowed_tools": CLAUDE_BUILTIN_WEB_TOOLS,
        "add_dirs": ("/inputs/one",),
        "system_prompt_append": "## Repository instructions (CLAUDE.md)\nsecret text",
        "notices": ("builtin_web is ignored on a local backend",),
    }
    values.update(overrides)
    return AppliedCapabilities(**values)  # type: ignore[arg-type]


def test_the_builtin_web_tools_are_claude_codes_own_names() -> None:
    assert CLAUDE_BUILTIN_WEB_TOOLS == ("WebSearch", "WebFetch")


def test_a_refused_snapshot_exits_ex_config() -> None:
    """78, sysexits EX_CONFIG: distinct from 0, 1, 2, 75 and 130 so the conductor parks the job."""
    assert EXIT_CAPABILITIES_REFUSED == 78


def test_applied_capabilities_satisfies_its_interface() -> None:
    assert isinstance(_applied(), AppliedCapabilitiesInterface)


def test_the_event_payload_holds_counts_names_and_no_text() -> None:
    applied = _applied(instruction_files=("CLAUDE.md",))
    payload = applied.event_payload()
    assert payload == {
        "digest": DIGEST,
        "plugins": 2,
        "skills": 3,
        "mcp_servers": 1,
        "disallowed_tools": ["WebSearch", "WebFetch"],
        "instruction_files": ["CLAUDE.md"],
        "notices": ["builtin_web is ignored on a local backend"],
    }
    rendered = repr(payload)
    assert "secret text" not in rendered
    assert "example.invalid" not in rendered
    assert "/runs/r1" not in rendered


def test_instruction_files_default_to_none_inlined() -> None:
    assert _applied().instruction_files == ()
    assert _applied().event_payload()["instruction_files"] == []


def test_a_refused_snapshot_carries_its_reason() -> None:
    error = CapabilitySnapshotRefused("the capability document at /x was refused")
    assert isinstance(error, AutoclaudeError)
    assert not isinstance(error, ValueError)
    assert isinstance(error, CapabilitySnapshotRefusedInterface)
    assert error.reason == "the capability document at /x was refused"
    assert str(error) == error.reason


def test_a_flag_conflict_is_a_usage_error() -> None:
    error = CapabilityFlagConflict("--connector 'docs' clashes")
    assert isinstance(error, AutoclaudeError)
    assert isinstance(error, ValueError)
