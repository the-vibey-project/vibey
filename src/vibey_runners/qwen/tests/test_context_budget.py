# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The 32k acceptance (SP-LOOPS Phase 5, R8; Review Focus 5): whatever a run's snapshot holds, the
fixed context -- the system prompt with its capability block, and every tool schema -- leaves the
conversation the room the runner renews the transcript at.

The budget is `32_768 - DEFAULT_CONTEXT_RENEWAL_TOKENS`: the runner renews the transcript once it
passes `DEFAULT_CONTEXT_RENEWAL_TOKENS`, so the fixed context must fit in what a 32k-token model
has left beside it. Tokens are the family's one estimate (characters over four, rounded up)."""

import json
import os
from pathlib import Path

from fakes import (
    CapabilityDocumentWriter,
    MemoryCommandIndex,
    MemoryDocumentStore,
    MemorySkillIndex,
    memory_document,
)
from vibey_runners.common.capabilities.bundle import (
    CAPABILITY_PROMPT_TOKENS_CEILING,
    MAX_ENTRIES,
    BundleSpec,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.resolver import DESCRIPTION_MAX_CHARS
from vibey_runners.common.capabilities.skill_index import MAX_SKILLS_PER_PLUGIN, SkillIndex
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot
from vibey_runners.common.capabilities.snapshot_document import SnapshotDocument
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore
from vibey_runners.common.capabilities.token_estimate import TOKEN_ESTIMATE

from qwenloop.application.runner import _system_prompt
from qwenloop.domain.config import DEFAULT_CONTEXT_RENEWAL_TOKENS
from qwenloop.infrastructure.capability_loader import CapabilityLoader
from qwenloop.infrastructure.inference import _CODING_TOOLS

SHIPPED_RESEARCH = (
    Path(__file__).resolve().parents[3] / "vibey_tools" / "skills" / "plugins" / "currency-research"
)
#: A 32k-token model, less the transcript the runner keeps before renewing it.
FIXED_CONTEXT_TOKENS = 32_768 - DEFAULT_CONTEXT_RENEWAL_TOKENS
HOST = "macOS"


def _fixed_context(cwd: Path, capabilities: str) -> int:
    """The estimated tokens of the standing system prompt and every tool schema."""
    return TOKEN_ESTIMATE.tokens(_system_prompt(cwd, HOST, capabilities)) + TOKEN_ESTIMATE.tokens(
        json.dumps(_CODING_TOOLS)
    )


def test_the_acceptance_budget_is_8768_tokens() -> None:
    assert FIXED_CONTEXT_TOKENS == 8_768


def test_a_full_snapshot_leaves_the_conversation_its_room(tmp_path: Path) -> None:
    """A snapshot at every cap the bundle allows -- `MAX_ENTRIES` plugins of
    `MAX_SKILLS_PER_PLUGIN` skills, each with the longest description, as many commands, and 256
    MCP servers -- with the standing budget at its ceiling and a `CLAUDE.md` that fills what the
    listing leaves. The listing falls back to its count, and the whole still fits."""
    plugins = [f"plugin-{p:03d}" for p in range(MAX_ENTRIES)]
    described = [
        (f"skill-{s:03d}", "d" * DESCRIPTION_MAX_CHARS) for s in range(MAX_SKILLS_PER_PLUGIN)
    ]
    commands = [
        (f"command-{s:03d}", "c" * DESCRIPTION_MAX_CHARS) for s in range(MAX_SKILLS_PER_PLUGIN)
    ]
    servers = tuple(
        McpServerSpec(f"server-{n:03d}", "local", ("fake-mcp",), None, ()) for n in range(256)
    )
    document = memory_document(
        plugins=plugins,
        skills=tuple(f"{plugin}:{name}" for plugin in plugins for name, _ in described),
        mcp_servers=servers,
        capability_prompt_tokens=CAPABILITY_PROMPT_TOKENS_CEILING,
    )
    cwd = tmp_path / "worktree"
    cwd.mkdir()
    budget_chars = TOKEN_ESTIMATE.chars(CAPABILITY_PROMPT_TOKENS_CEILING)
    (cwd / "CLAUDE.md").write_text("r" * (budget_chars - 1024), "utf-8")
    loaded = CapabilityLoader(
        MemoryDocumentStore(document),
        skills=MemorySkillIndex(dict.fromkeys(plugins, described)),
        commands=MemoryCommandIndex(dict.fromkeys(plugins, commands)),
    ).load(tmp_path / "capabilities.json", cwd=cwd)
    assert len(loaded.shelf.entries) == 2 * MAX_ENTRIES * MAX_SKILLS_PER_PLUGIN
    assert loaded.listing_form == "count"
    assert loaded.instruction_files == ("CLAUDE.md",)
    assert TOKEN_ESTIMATE.tokens(loaded.prompt) <= CAPABILITY_PROMPT_TOKENS_CEILING
    assert TOKEN_ESTIMATE.tokens(loaded.prompt) > CAPABILITY_PROMPT_TOKENS_CEILING - 300
    assert _fixed_context(cwd, loaded.prompt) <= FIXED_CONTEXT_TOKENS
    # Whatever the block holds, the ceiling itself fits: the bound is the budget, not this text.
    assert _fixed_context(cwd, "x" * budget_chars) <= FIXED_CONTEXT_TOKENS


def test_the_default_bundle_fits_in_full(tmp_path: Path) -> None:
    """The default bundle -- the shipped `currency-research` plugin and every default `[loops]`
    setting -- is listed in full, and leaves the conversation its room."""
    writer = CapabilityDocumentWriter(tmp_path)
    plugin = writer.copy(Path(os.path.realpath(SHIPPED_RESEARCH)))
    bundle = BundleSpec.from_mapping({})
    snapshot = CapabilitySnapshot(
        (plugin,), SkillIndex().build([plugin]), (), "sha256:" + "ab" * 32, writer.run
    )
    path = SnapshotDocumentStore().write(SnapshotDocument.of(snapshot, bundle, []), writer.run)
    cwd = tmp_path / "worktree"
    cwd.mkdir()
    loaded = CapabilityLoader().load(path, cwd=cwd)
    assert bundle.plugins[0].name == "currency-research"
    assert loaded.listing_form == "full"
    assert len(loaded.shelf.entries) == 4
    assert TOKEN_ESTIMATE.tokens(loaded.prompt) <= bundle.capability_prompt_tokens
    assert _fixed_context(cwd, loaded.prompt) <= FIXED_CONTEXT_TOKENS
