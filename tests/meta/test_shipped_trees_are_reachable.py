# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Everything the wheel ships must be reachable by the two lists that depend on it.

ADR-0037 made `pyproject.toml`'s `[tool.hatch.build.targets.wheel]` the single answer to
"what reaches an installed user". Two other files have to agree with it, and neither had
anything holding it to that:

1. **`.vibey-gh.toml` `[version] content_paths`.** `_classify` matches a changed file
   against these prefixes with `str.startswith`, and a range that matches none derives
   "nothing to release". Left at `["src/vibey/"]` after nine more trees started shipping,
   a change to claudeloop or vibey_gh would publish nothing forever -- and `release.yml`
   would republish the current version into `skip-existing`, which is a GREEN run. There
   is no failure to notice. That is exactly the kind of drift a meta test exists for.

2. **`deploy/docker/Dockerfile`'s build context.** The final `uv sync` builds the project,
   and hatchling demands every declared path be present. A package root added to the
   wheel without a matching `COPY` fails the `image` job -- both arches -- with
   `FileNotFoundError: Forced include not found`, and takes `cluster-smoke` down with it.
   Failing here instead costs seconds and names the missing path.

Derived from the pyproject rather than enumerated, for the reason ADR-0018 gives: a
hard-coded copy of the list is the same defect one layer up, and it is the copy that goes
stale. Adding an eleventh package root is meant to fail this test until both consumers
know about it.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
following tests/meta/test_tools_matrix_covers_every_package.py: pytest collects `test_*`
functions, and the rule is about production code.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
VIBEY_GH_TOML = REPO / ".vibey-gh.toml"
DOCKERFILE = REPO / "deploy" / "docker" / "Dockerfile"


def _wheel_table() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["tool"]["hatch"]["build"]["targets"]["wheel"]


def _shipped_sources() -> list[str]:
    """Every repository-relative path whose content lands in the published wheel.

    Both shapes count. `packages` are the importable trees; `force-include` keys are the
    content that must land somewhere it does not live -- the plugins tree that has to stay
    at the repository root for Claude Code, and vibey-gh's release assets. A reader who
    only checked `packages` would miss four paths that ship, which is how
    `.claude-plugin/marketplace.json` came to be absent from `content_paths`.
    """
    wheel = _wheel_table()
    sources = [*wheel["packages"], *wheel.get("force-include", {})]
    assert len(sources) >= 10, f"only {len(sources)} shipped sources; the table moved"
    return sorted(sources)


def _version_prefixes() -> list[str]:
    with VIBEY_GH_TOML.open("rb") as handle:
        version = tomllib.load(handle)["version"]
    return [*version.get("content_paths", ()), *version.get("code_paths", ())]


def _copied_sources() -> list[str]:
    """Every build-context path a `COPY` in the build stage names, without `--from`."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    build_stage = text.split("FROM python:3.12-slim-bookworm AS runtime", 1)[0]
    copied: list[str] = []
    for line in build_stage.splitlines():
        match = re.match(r"\s*COPY\s+(?!--from)(.*)", line)
        if match:
            # The last token is the destination; everything before it is a source.
            copied.extend(source.rstrip("/") for source in match.group(1).split()[:-1])
    assert copied, "no COPY sources found in the Dockerfile build stage"
    return copied


@pytest.mark.parametrize("shipped", _shipped_sources())
def test_every_shipped_tree_can_derive_a_release(shipped: str) -> None:
    covered = [p for p in _version_prefixes() if shipped.startswith(p) or p.startswith(shipped)]
    assert covered, (
        f"{shipped} ships in the wheel but matches no `[version]` prefix in "
        ".vibey-gh.toml, so changing it derives 'nothing to release' and republishes "
        "the current version into skip-existing -- a green run that publishes nothing."
    )


@pytest.mark.parametrize("shipped", _shipped_sources())
def test_every_shipped_tree_is_in_the_container_build_context(shipped: str) -> None:
    copied = _copied_sources()
    assert any(shipped == c or shipped.startswith(c + "/") for c in copied), (
        f"{shipped} is declared in [tool.hatch.build.targets.wheel] but no Dockerfile "
        "COPY puts it in the build context. The final `uv sync` builds the project, so "
        "hatchling fails the `image` job on both arches looking for it."
    )


def test_the_root_manifest_itself_derives_a_release() -> None:
    """`pyproject.toml` decides what ships, so a change confined to it must release.

    Precedent: vibey-bootstrap's standalone `.vibey-gh.toml` carried `pyproject.toml` in
    its own `code_paths` before this repository did. That file was inert here and was
    removed under #189; `git show 4e9adf18:src/vibey_tools/bootstrap/.vibey-gh.toml`.
    """
    assert any("pyproject.toml".startswith(prefix) for prefix in _version_prefixes()), (
        "pyproject.toml now decides what ships but reaches no `[version]` prefix"
    )
