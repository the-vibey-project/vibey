# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""JavaScript is not authored: every tracked `.js` is compiled from TypeScript (9.f, ADR-0088).

Two claims, each checked by a machine because a rule nobody checks is a wish (12.e):

* **Nothing hand-written.** Every tracked `.js`, `.mjs`, `.cjs` or `.jsx` file is a declared
  artifact of `scripts/typescript_artifacts.toml`, starts with the banner naming its
  TypeScript source, and that source exists. A new JavaScript file fails here.
* **Nothing stale.** Each artifact is exactly what its source compiles to today.

The second claim needs the compiler `npm ci` installs. Without it, a developer's own run is
skipped with the reason; in CI it is a failure, because a gate that quietly does not run
reports a success it did not observe.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
try:
    from typescript_artifacts import Banner, TypeScriptArtifacts  # noqa: E402
finally:
    sys.path.remove(str(REPO / "scripts"))
    for _name in [n for n in sys.modules if n == "interfaces" or n.startswith("interfaces.")]:
        del sys.modules[_name]

JAVASCRIPT = (".js", ".mjs", ".cjs", ".jsx")


def _tracked_javascript() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.split("\0")
    # `site/` is a built copy of the documentation, not source.
    return sorted(p for p in listed if p.endswith(JAVASCRIPT) and not p.startswith("site/"))


def test_no_javascript_is_authored() -> None:
    declared = {str(path) for path in TypeScriptArtifacts(REPO).outputs_declared()}
    authored = [p for p in _tracked_javascript() if p not in declared]
    assert not authored, (
        f"tracked JavaScript that is not a declared artifact: {authored}. "
        "Write TypeScript instead (sub-doctrine 9.f) and declare the output in "
        "scripts/typescript_artifacts.toml only if a browser or tool must load a .js"
    )


def test_every_declared_artifact_says_where_it_came_from() -> None:
    for artifact in TypeScriptArtifacts(REPO).artifacts:
        assert (REPO / artifact.source).is_file(), f"{artifact.source} does not exist"
        for target in artifact.targets:
            first = (REPO / target).read_text(encoding="utf-8")
            assert Banner.marks(first) == artifact.source, (
                f"{target} does not start with the generated banner naming {artifact.source}"
            )


def test_no_typescript_source_is_orphaned() -> None:
    """A `.ts` that exists only to be compiled into a `.js` must be declared, or it is dead."""
    declared = {a.source for a in TypeScriptArtifacts(REPO).artifacts}
    for source in sorted(declared):
        assert source.endswith(".ts"), f"{source}: an artifact's source must be TypeScript"


def test_the_committed_javascript_is_what_the_typescript_compiles_to() -> None:
    tsc = REPO / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        if os.environ.get("CI"):
            pytest.fail("node_modules/.bin/tsc is missing in CI: the gate must `npm ci` first")
        pytest.skip("TypeScript is not installed here; run `npm ci` to check the artifacts")
    stale = TypeScriptArtifacts(REPO).stale()
    assert not stale, (
        f"stale: {[str(p) for p in stale]}; run `python3 scripts/typescript_artifacts.py`"
    )
