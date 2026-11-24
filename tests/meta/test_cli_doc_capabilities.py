# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `capabilities` row of `vibey loops` in the CLI reference names every capability.

`vibey loops --json` reports one key per `EngineAffordances` field; the reference's row was
written when there were six and went stale when `skills` and `web_search` joined. A field the
row does not name is a key a reader of the document has no description of.
"""

from dataclasses import fields
from pathlib import Path

from vibey_runners.common.capabilities.bundle import (
    CAPABILITY_ANSWER_TOKENS_CEILING,
    CAPABILITY_ANSWER_TOKENS_FLOOR,
    CAPABILITY_PROMPT_TOKENS_CEILING,
    CAPABILITY_PROMPT_TOKENS_FLOOR,
    DEFAULT_CAPABILITY_ANSWER_TOKENS,
    DEFAULT_CAPABILITY_PROMPT_TOKENS,
)

from vibey.domain.engine import EngineAffordances, PluginSystem

REPO = Path(__file__).resolve().parents[2]
CLI_DOC = REPO / "docs" / "reference" / "cli.md"
CONFIGURATION_DOC = REPO / "docs" / "reference" / "configuration.md"
ADR_0092 = (
    REPO
    / "docs"
    / "architecture"
    / "decisions"
    / "0092-large-tasks-are-sliced-into-the-cdd-layers-before-they-run.md"
)


def _row(doc: Path, prefix: str) -> str:
    rows = [
        line for line in doc.read_text(encoding="utf-8").splitlines() if line.startswith(prefix)
    ]
    assert len(rows) == 1, rows
    return rows[0]


def _capabilities_row() -> str:
    return _row(CLI_DOC, "| `capabilities` |")


def test_the_capabilities_row_names_every_affordance() -> None:
    row = _capabilities_row()
    missing = [
        f.name
        for f in fields(EngineAffordances)
        if f.name != "evidence" and f"`{f.name}`" not in row
    ]
    assert not missing, f"docs/reference/cli.md's capabilities row does not name {missing}"


def test_the_capabilities_row_names_its_evidence() -> None:
    assert "`evidence`" in _capabilities_row()


def test_the_cli_doc_names_builtin_web_and_the_capabilities_flag() -> None:
    """The per-loop row for claudeloop says what Phase 4 changed: web search is off unless
    `[loops] builtin_web` turns it on, and plugins, skills and MCP come from the snapshot
    `run --capabilities` names, not from a `--web-search` vibey passes."""
    rows = [
        line
        for line in CLI_DOC.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `claudeloop`, `claudeloop-local` |")
    ]
    assert len(rows) == 1, rows
    row = rows[0]
    assert "`[loops] builtin_web`" in row
    assert "`run --capabilities`" in row
    assert "--web-search" not in row


def test_the_cli_doc_names_vibey_bundle_and_the_local_runners_skill_tools() -> None:
    """SP-LOOPS Phase 5: the capabilities row names every plugin system, and the local runner's
    per-loop row says it takes the vibey bundle through its four capability tools, no longer the
    skills-context packet alone."""
    capabilities = _capabilities_row()
    missing = [s.value for s in PluginSystem if f"`{s.value}`" not in capabilities]
    assert not missing, f"the capabilities row does not name the plugin systems {missing}"

    row = _row(CLI_DOC, "| `gptossloop`, `qwenloop` |")
    for needle in (
        f"`{PluginSystem.VIBEY_BUNDLE.value}`",
        "`skills_list`",
        "`skill_read`",
        "`mcp_list`",
        "`mcp_call`",
        "`run --capabilities`",
    ):
        assert needle in row, f"the gptossloop, qwenloop row does not name {needle}"
    assert f"`{PluginSystem.SKILLS_CONTEXT.value}`" not in row
    assert "no skills" not in row


def test_the_configuration_doc_names_both_token_budgets_with_their_defaults() -> None:
    """The two person-only `[loops]` budgets (R8) are documented with the defaults and ranges
    the bundle reader enforces, and with the note that claudeloop ignores them."""
    for key, default, floor, ceiling in (
        (
            "capability_prompt_tokens",
            DEFAULT_CAPABILITY_PROMPT_TOKENS,
            CAPABILITY_PROMPT_TOKENS_FLOOR,
            CAPABILITY_PROMPT_TOKENS_CEILING,
        ),
        (
            "capability_answer_tokens",
            DEFAULT_CAPABILITY_ANSWER_TOKENS,
            CAPABILITY_ANSWER_TOKENS_FLOOR,
            CAPABILITY_ANSWER_TOKENS_CEILING,
        ),
    ):
        row = _row(CONFIGURATION_DOC, f"| `{key}` | `{default}` |")
        assert f"from {floor} to {ceiling}" in row, row
        assert "claudeloop ignores" in row, row
    assert (DEFAULT_CAPABILITY_PROMPT_TOKENS, DEFAULT_CAPABILITY_ANSWER_TOKENS) == (3072, 3000)


def test_adr_0092_carries_the_2026_11_25_amendment_and_marks_both_bullets() -> None:
    """ADR-0092's body is a record and is never rewritten: Phase 5 marks the two bullets it
    changes and adds its amendment at the foot, after the 2026-11-22 one."""
    text = ADR_0092.read_text(encoding="utf-8")
    lines = text.splitlines()

    first = next(
        i for i, line in enumerate(lines) if line.startswith("- `EngineAffordances` gains")
    )
    assert lines[first + 2] == (
        "  *(Amended 2026-11-25: `vibey-bundle` grants plugins too; see the second amendment at "
        "the foot.)*"
    )

    mcp = next(
        i for i, line in enumerate(lines) if line.startswith("- **The local runner reaches MCP**")
    )
    marker = (
        "  *(Superseded 2026-11-25 for a run given a capability snapshot: see the second amendment "
        "at the foot.)*"
    )
    following = lines[
        mcp + 1 : next(i for i in range(mcp + 1, len(lines)) if lines[i].startswith("- "))
    ]
    assert following[-1] == marker, following

    earlier = text.index("## Amendment, 2026-11-22: codexloop's MCP claim is withdrawn")
    amendment = text.index(
        "## Amendment, 2026-11-25: the local runner's plugins are the vibey bundle"
    )
    assert earlier < amendment
    foot = text[amendment:]
    for needle in (
        "`vibey-bundle` (`VIBEY_BUNDLE`)",
        "`full_access_gaps()` counts `claude-plugins` and `vibey-bundle`",
        "`run --capabilities PATH`",
        "`[loops] capability_answer_tokens`",
        "`[loops] capability_prompt_tokens`",
        "`tests/infrastructure/engines/test_descriptors.py`",
        "`tests/meta/loop_runner_facts.py`",
    ):
        assert needle in foot, needle
