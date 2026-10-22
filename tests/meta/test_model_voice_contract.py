# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every model boundary carries ADR-0089's singular voice contract."""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CONTRACT = "Voice contract (mandatory, with no exceptions)"
DIRECT_ADDRESS = "direct speech"
NO_PLURAL_SELF = "for yourself alone"
RUNTIME_BOUNDARIES = (
    "scripts/continuation_prompts.py",
    "src/vibey/infrastructure/engines/ollama_chat.py",
    "src/vibey/infrastructure/engines/loop_process_adapter.py",
    "src/vibey_runners/claude/src/claudeloop/infrastructure/agent/options.py",
    "src/vibey_runners/codex/src/codexloop/application/runner.py",
    "src/vibey_runners/qwen/src/qwenloop/application/runner.py",
    "src/vibey_tools/gh/vibey_gh/local_review.py",
)
WORKFLOW_PROMPTS = (
    ".github/workflows/pr-review.yml",
    "src/vibey_tools/gh/.github/workflows/conversation.yml",
    "src/vibey_tools/gh/.github/workflows/documentation.yml",
    "src/vibey_tools/gh/.github/workflows/issue-automation.yml",
    "src/vibey_tools/gh/.github/workflows/pr-review.yml",
    "src/vibey_tools/gh/.github/workflows/release-repair.yml",
    "src/vibey_tools/gh/vibey_gh/templates/workflows/conversation.yml",
    "src/vibey_tools/gh/vibey_gh/templates/workflows/documentation.yml",
    "src/vibey_tools/gh/vibey_gh/templates/workflows/issue-automation.yml",
    "src/vibey_tools/gh/vibey_gh/templates/workflows/pr-review.yml",
    "src/vibey_tools/gh/vibey_gh/templates/workflows/release-repair.yml",
)


@pytest.mark.parametrize("relative", RUNTIME_BOUNDARIES)
def test_runtime_model_boundaries_carry_the_voice_contract(relative: str) -> None:
    # Pytest's collection contract requires a module-level function (ADR-0016 last resort).
    text = (REPO / relative).read_text(encoding="utf-8")
    assert CONTRACT in text, relative
    assert DIRECT_ADDRESS in text, relative
    assert "to the operator" in text, relative
    assert NO_PLURAL_SELF in text, relative


@pytest.mark.parametrize("relative", WORKFLOW_PROMPTS)
def test_every_literal_managed_workflow_prompt_opens_with_the_contract(relative: str) -> None:
    text = (REPO / relative).read_text(encoding="utf-8")
    starts = list(re.finditer(r"(?m)^(?P<indent>\s*)prompt: \|\s*$", text))
    assert starts, relative
    for start in starts:
        base = len(start.group("indent"))
        following = text[start.end() :].splitlines()
        block: list[str] = []
        for line in following[1:]:
            if line.strip() and len(line) - len(line.lstrip()) <= base:
                break
            block.append(line)
        prompt = "\n".join(block)
        assert CONTRACT in prompt, (relative, start.start())
        assert DIRECT_ADDRESS in prompt, (relative, start.start())
        assert NO_PLURAL_SELF in prompt, (relative, start.start())
