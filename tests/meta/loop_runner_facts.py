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


_CLAUDE_RUN = "src/vibey_runners/claude/src/claudeloop/cli/commands/run.py"
_CLAUDE_PROMPT = "src/vibey_runners/claude/src/claudeloop/cli/commands/prompt.py"
_CLAUDE_RESOURCES = "src/vibey_runners/claude/src/claudeloop/infrastructure/resources/adapter.py"
_CODEX_ARGV = "src/vibey_runners/codex/src/codexloop/infrastructure/agent/argv.py"
_CODEX_PROMPT = "src/vibey_runners/codex/src/codexloop/cli/commands/prompt.py"
_LOCAL_TOOLS = "src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py"
_LOCAL_RUNNER = "src/vibey_runners/qwen/src/qwenloop/application/runner.py"
# `plugins: skills-context` is vibey's own code, not a runner's: the BUILD handler appends the
# vibey-skills context packet to the plan's text, whichever engine then runs it.
_SKILLS_CONTEXT_SOURCE = "src/vibey/application/build_implement_handler.py"
_SKILLS_CONTEXT_NEEDLE = 'prompt = f"{prompt.rstrip()}\\n\\n{context.markdown.lstrip()}"'


def _claudeloop(loop: str) -> tuple[RunnerFact, ...]:
    """claudeloop's facts; claudeloop-local is the same binary on a local profile."""
    return (
        RunnerFact(loop, "files", _CLAUDE_RUN, '"--add-folder"'),
        RunnerFact(loop, "paste_text", _CLAUDE_PROMPT, '"--at-break"'),
        RunnerFact(loop, "plugins", _CLAUDE_RUN, '"--plugin"'),
        RunnerFact(loop, "mcp", _CLAUDE_RUN, '"--connector"'),
        RunnerFact(loop, "skills", _CLAUDE_RUN, '"--skill"'),
    )


def _local_runner(loop: str) -> tuple[RunnerFact, ...]:
    """The local runner's facts; gptossloop and qwenloop are one package (ADR-0064)."""
    return (
        RunnerFact(loop, "files", _LOCAL_TOOLS, 'if name == "write_file":'),
        RunnerFact(loop, "paste_text", _LOCAL_RUNNER, 'ChatMessage("user", plan)'),
        RunnerFact(loop, "mcp", _LOCAL_TOOLS, 'if name in {"mcp_list", "mcp_call"}:'),
        RunnerFact(loop, "web_search", _LOCAL_TOOLS, 'if name in {"web_search", "web_fetch"}:'),
        RunnerFact(loop, "plugins", _SKILLS_CONTEXT_SOURCE, _SKILLS_CONTEXT_NEEDLE),
    )


RUNNER_FACTS: tuple[RunnerFact, ...] = (
    *_claudeloop("claudeloop"),
    RunnerFact("claudeloop", "web_search", _CLAUDE_RESOURCES, 'allowed.append("WebSearch")'),
    *_claudeloop("claudeloop-local"),
    RunnerFact("codexloop", "files", _CODEX_ARGV, '"--add-dir"'),
    RunnerFact("codexloop", "paste_text", _CODEX_PROMPT, '"--next-turn"'),
    RunnerFact("codexloop", "plugins", _SKILLS_CONTEXT_SOURCE, _SKILLS_CONTEXT_NEEDLE),
    *_local_runner("gptossloop"),
    *_local_runner("qwenloop"),
)
