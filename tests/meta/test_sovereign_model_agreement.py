# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The qwenloop tenant cannot import vibey, so its default model is a copy; this pins the two."""

import ast
from pathlib import Path

from vibey.domain.sovereign_model import DEFAULT_SOVEREIGN_TAG

RUNNER_CONFIG = (
    Path(__file__).resolve().parents[2] / "src/vibey_runners/qwen/src/qwenloop/domain/config.py"
)


def test_the_runners_default_model_is_the_catalogues_default() -> None:
    tree = ast.parse(RUNNER_CONFIG.read_text(encoding="utf-8"))
    values = [
        node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "DEFAULT_ENDPOINT_MODEL" for t in node.targets)
        and isinstance(node.value, ast.Constant)
    ]
    assert values == [DEFAULT_SOVEREIGN_TAG]
