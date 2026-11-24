# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every capability a loop's descriptor claims is pinned to the runner code that implements it.

`EngineAffordances.evidence` says in prose where a claim comes from; prose cannot fail when the
code moves. This reads each claim -- a field that is `True` or names a `PluginSystem` --
against `RUNNER_FACTS`: a fact for that loop and field must exist, and its needle must still be
in its file. A claim with no runner code behind it is not a claim: the field is `None`
(unknown), never `True`.
"""

from dataclasses import fields
from pathlib import Path

import pytest

from vibey.domain.engine import EngineAffordances, EngineDescriptor, EngineId, PluginSystem
from vibey.infrastructure.engines.descriptors import ALL_DESCRIPTORS, BY_ENGINE_ID

from .loop_runner_facts import RUNNER_FACTS, RunnerFact

REPO = Path(__file__).resolve().parents[2]
FIELDS = tuple(f.name for f in fields(EngineAffordances) if f.name != "evidence")


def _claims(descriptor: EngineDescriptor) -> list[str]:
    affordances = descriptor.affordances
    return [
        name
        for name in FIELDS
        if getattr(affordances, name) is True
        or isinstance(getattr(affordances, name), PluginSystem)
    ]


def _facts(loop: str, capability: str) -> list[RunnerFact]:
    return [f for f in RUNNER_FACTS if f.loop == loop and f.capability == capability]


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_every_true_claim_has_a_matching_runner_fact(descriptor: EngineDescriptor) -> None:
    loop = descriptor.engine_id.value
    for capability in _claims(descriptor):
        facts = _facts(loop, capability)
        assert facts, f"{loop} claims {capability} and no RunnerFact shows the code"
        for fact in facts:
            text = (REPO / fact.source).read_text(encoding="utf-8")
            assert fact.needle in text, f"{loop} {capability}: {fact.needle!r} not in {fact.source}"


def test_a_capability_without_runner_code_is_not_claimed() -> None:
    """codexloop mounts no MCP server: nothing under `src/vibey_runners/codex/` passes one to
    Codex, so there is no fact, and the descriptor says unknown rather than yes."""
    assert not _facts(EngineId.CODEXLOOP.value, "mcp")
    assert BY_ENGINE_ID[EngineId.CODEXLOOP].affordances.mcp is None


SNAPSHOT_NEEDLES = {
    '"--capabilities"',
    'merged["setting_sources"] = []',
    '"type": "stdio"',
    '"type": "http"',
    "attachments_dir",
}
"""The code a claudeloop run's capability snapshot goes through (SP-LOOPS Phase 4): the flag
that names the document, the overlay that switches Claude Code's own settings off, the MCP
transports, and the attachments folder `gateway_payload` gives the agent."""


def test_claudeloop_and_claudeloop_local_share_every_snapshot_fact() -> None:
    """The same binary on a local profile takes the same snapshot (R11): every fact for one is a
    fact for the other, file and needle alike, and claudeloop's web search rests on the
    `vibey-web` connector in that snapshot (SP-LOOPS Phase 6, Task 6)."""
    claude = {(f.capability, f.source, f.needle) for f in RUNNER_FACTS if f.loop == "claudeloop"}
    local = {
        (f.capability, f.source, f.needle) for f in RUNNER_FACTS if f.loop == "claudeloop-local"
    }
    assert claude == local
    assert {needle for _, _, needle in claude} >= SNAPSHOT_NEEDLES
    web = {needle for capability, _, needle in claude if capability == "web_search"}
    assert {'"--capabilities"', '"type": "stdio"', 'WEB_CONNECTOR_NAME: Final = "vibey-web"'} <= web


LOCAL_SNAPSHOT_NEEDLES = {
    '"--capabilities"',
    'if name in {"skills_list", "skill_read"}:',
    'if name in {"mcp_list", "mcp_call"}:',
    "Mcp-Session-Id",
    "launch.argv(server)",
}
"""The code a local run's capability snapshot goes through (SP-LOOPS Phase 5): the flag that
names the document, the two skill tools, the two MCP tools, the HTTP transport's session header
and the stdio transport's scrubbed launcher argv."""


def test_gptossloop_and_qwenloop_share_every_snapshot_fact() -> None:
    """One runner package serves both engines (ADR-0064), so both take the same snapshot: every
    fact for one is a fact for the other, each snapshot claim rests on the `--capabilities` flag,
    and the plugins they claim are the snapshot's, no longer the skills-context packet in vibey's
    own BUILD handler."""
    gptoss = {(f.capability, f.source, f.needle) for f in RUNNER_FACTS if f.loop == "gptossloop"}
    qwen = {(f.capability, f.source, f.needle) for f in RUNNER_FACTS if f.loop == "qwenloop"}
    assert gptoss == qwen
    assert {needle for _, _, needle in gptoss} >= LOCAL_SNAPSHOT_NEEDLES
    for capability in ("plugins", "skills", "mcp"):
        needles = {needle for cap, _, needle in gptoss if cap == capability}
        assert '"--capabilities"' in needles, capability
    assert all(not source.startswith("src/vibey/") for cap, source, _ in gptoss if cap == "plugins")
    for engine in (EngineId.GPTOSSLOOP, EngineId.QWENLOOP):
        assert BY_ENGINE_ID[engine].affordances.plugins is PluginSystem.VIBEY_BUNDLE


def test_every_fact_names_a_claim_a_descriptor_makes() -> None:
    """A fact for a capability no descriptor claims is a stale row: it would let a later
    claim pass on code read for a different one."""
    claimed = {(d.engine_id.value, name) for d in ALL_DESCRIPTORS for name in _claims(d)}
    for fact in RUNNER_FACTS:
        assert (fact.loop, fact.capability) in claimed, fact
        assert fact.needle.strip(), fact
