# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The runner code behind every capability a loop's descriptor claims (SP-LOOPS Task 1).

One `RunnerFact` per claim: the loop, the `EngineAffordances` field it proves, the file that
implements it (a path from the repository root) and a literal string that file contains.
`tests/meta/test_loop_capability_evidence.py` reads every descriptor against this table, so a
descriptor can claim a capability only where a fact here shows the code, and a fact goes stale
the moment its needle leaves the file.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunnerFact:
    """`source` (a path from the repository root) contains `needle`, the code that implements
    `capability` for `loop`."""

    loop: str
    capability: str
    source: str
    needle: str


_CLAUDE = "src/vibey_runners/claude/src/claudeloop"
_CLAUDE_RUN = f"{_CLAUDE}/cli/commands/run.py"
_CLAUDE_PROMPT = f"{_CLAUDE}/cli/commands/prompt.py"
_CLAUDE_RESOURCES = f"{_CLAUDE}/infrastructure/resources/adapter.py"
# SP-LOOPS Phase 4: the overlay that lays the run's snapshot over every connect, and the MCP
# transports its servers are given.
_CLAUDE_OVERLAY = f"{_CLAUDE}/infrastructure/agent/capability_overlay.py"
_CLAUDE_MCP = f"{_CLAUDE}/domain/mcp_config.py"
_CODEX_ARGV = "src/vibey_runners/codex/src/codexloop/infrastructure/agent/argv.py"
_CODEX_PROMPT = "src/vibey_runners/codex/src/codexloop/cli/commands/prompt.py"
_LOCAL_TOOLS = "src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py"
_LOCAL_RUNNER = "src/vibey_runners/qwen/src/qwenloop/application/runner.py"
# SP-LOOPS Phase 5: the flag the local runner takes its snapshot by, and the MCP client in common
# its servers are reached through -- the HTTP transport's session and the scrubbed launcher argv
# a stdio server is started with.
_LOCAL_APP = "src/vibey_runners/qwen/src/qwenloop/cli/app.py"
_COMMON_MCP = "src/vibey_runners/common/src/vibey_runners/common/mcp"
_COMMON_HTTP = f"{_COMMON_MCP}/http_transport.py"
_COMMON_TRANSPORTS = f"{_COMMON_MCP}/mcp_transport_factory.py"
# `plugins: skills-context` is vibey's own code, not a runner's: the BUILD handler appends the
# vibey-skills context packet to the plan's text, whichever engine then runs it.
_SKILLS_CONTEXT_SOURCE = "src/vibey/application/build_implement_handler.py"
_SKILLS_CONTEXT_NEEDLE = 'prompt = f"{prompt.rstrip()}\\n\\n{context.markdown.lstrip()}"'


def _claudeloop(loop: str) -> tuple[RunnerFact, ...]:
    """claudeloop's facts; claudeloop-local is the same binary on a local profile and takes the
    same snapshot (SP-LOOPS Phase 4, R11). Neither claims web search (R4), so neither has a fact
    for it."""
    return (
        RunnerFact(loop, "files", _CLAUDE_RUN, '"--capabilities"'),
        RunnerFact(loop, "files", _CLAUDE_RESOURCES, "attachments_dir"),
        RunnerFact(loop, "paste_text", _CLAUDE_PROMPT, '"--at-break"'),
        RunnerFact(loop, "plugins", _CLAUDE_RUN, '"--capabilities"'),
        RunnerFact(loop, "plugins", _CLAUDE_OVERLAY, 'merged["setting_sources"] = []'),
        RunnerFact(loop, "plugins", _CLAUDE_OVERLAY, '{"type": "local", "path": folder}'),
        RunnerFact(loop, "mcp", _CLAUDE_RUN, '"--capabilities"'),
        RunnerFact(loop, "mcp", _CLAUDE_MCP, '"type": "stdio"'),
        RunnerFact(loop, "mcp", _CLAUDE_MCP, '"type": "http"'),
        RunnerFact(loop, "skills", _CLAUDE_RUN, '"--capabilities"'),
        RunnerFact(loop, "skills", _CLAUDE_OVERLAY, 'merged["skills"] = self._skills('),
    )


def _local_runner(loop: str) -> tuple[RunnerFact, ...]:
    """The local runner's facts; gptossloop and qwenloop are one package (ADR-0064) and take the
    same snapshot as the vibey bundle (SP-LOOPS Phase 5)."""
    return (
        RunnerFact(loop, "files", _LOCAL_TOOLS, 'if name == "write_file":'),
        RunnerFact(loop, "paste_text", _LOCAL_RUNNER, 'ChatMessage("user", plan)'),
        RunnerFact(loop, "plugins", _LOCAL_APP, '"--capabilities"'),
        RunnerFact(loop, "plugins", _LOCAL_TOOLS, 'if name in {"skills_list", "skill_read"}:'),
        RunnerFact(loop, "skills", _LOCAL_APP, '"--capabilities"'),
        RunnerFact(loop, "skills", _LOCAL_TOOLS, 'if name in {"skills_list", "skill_read"}:'),
        RunnerFact(loop, "mcp", _LOCAL_APP, '"--capabilities"'),
        RunnerFact(loop, "mcp", _LOCAL_TOOLS, 'if name in {"mcp_list", "mcp_call"}:'),
        RunnerFact(loop, "mcp", _COMMON_HTTP, "Mcp-Session-Id"),
        RunnerFact(loop, "mcp", _COMMON_TRANSPORTS, "launch.argv(server)"),
        RunnerFact(loop, "web_search", _LOCAL_TOOLS, 'if name in {"web_search", "web_fetch"}:'),
    )


RUNNER_FACTS: tuple[RunnerFact, ...] = (
    *_claudeloop("claudeloop"),
    *_claudeloop("claudeloop-local"),
    RunnerFact("codexloop", "files", _CODEX_ARGV, '"--add-dir"'),
    RunnerFact("codexloop", "paste_text", _CODEX_PROMPT, '"--next-turn"'),
    RunnerFact("codexloop", "plugins", _SKILLS_CONTEXT_SOURCE, _SKILLS_CONTEXT_NEEDLE),
    *_local_runner("gptossloop"),
    *_local_runner("qwenloop"),
)
