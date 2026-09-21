# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `VibeyProject` CRD accepts exactly the engine ids vibey has.

The chart's `spec.engines` enum is a deployment-facing copy of the engine vocabulary.
A hand-kept list beside an enum in code drifts; this is the check that it has not.
"""

from __future__ import annotations

import re
from pathlib import Path

from vibey.domain.engine import EngineId

REPO = Path(__file__).resolve().parents[2]
CRD = REPO / "deploy" / "helm" / "vibey" / "templates" / "crd-vibeyproject.yaml"
ENGINES_ENUM = re.compile(r"^\s*engines:\n(?:\s+.*\n)*?\s+enum:\s*\[([^\]]*)\]", re.MULTILINE)


def test_the_crd_engine_enum_is_every_engine_id() -> None:
    match = ENGINES_ENUM.search(CRD.read_text(encoding="utf-8"))
    assert match is not None, f"no spec.engines enum found in {CRD.name}"
    declared = [name.strip() for name in match.group(1).split(",") if name.strip()]
    assert sorted(declared) == sorted(engine.value for engine in EngineId)
