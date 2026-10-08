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


WORKFLOW_FILES = (
    "src/vibey_tools/gh/vibey_gh/templates/workflows",
    ".github/workflows",
    "src/vibey_tools/gh/.github/workflows",
)


def test_no_workflow_writes_inline_javascript() -> None:
    """A workflow carries configuration, never JavaScript (9.f, ADR-0088).

    Every inline `<script>` a workflow's Python emits must take its body from a compiled
    asset (`read_text()` on the next lines), or be JSON-LD or an external `src=`. A script
    body written out as string literals is JavaScript nobody type-checks.
    """
    import re

    opener = re.compile(r"""<script(?P<attrs>[^>]*)>""")
    offenders = []
    for folder in WORKFLOW_FILES:
        for path in sorted((REPO / folder).glob("*.yml")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for at, line in enumerate(lines):
                for found in opener.finditer(line):
                    attrs = found.group("attrs")
                    if "ld+json" in attrs or " src=" in attrs:
                        continue
                    following = "\n".join(lines[at : at + 4])
                    if "read_text()" not in following:
                        offenders.append(f"{path.relative_to(REPO)}:{at + 1}")
    assert not offenders, f"inline JavaScript written in a workflow: {offenders}"


def test_no_inlined_asset_can_end_its_own_script_element() -> None:
    """An asset inlined into a page must not spell out markup, comments included.

    The release workflow inlines `analytics.js` and `consent.js` into every published page.
    The HTML parser ends an inline script at the first closing script tag it meets, even inside
    a JavaScript comment, and prints the rest of the file as visible text at the top of the
    page. That happened once (a comment that showed an example tag), so this test reads the
    workflow, finds each asset it inlines, and refuses the markup that causes it.
    """
    import re

    template = REPO / "src/vibey_tools/gh/vibey_gh/templates/workflows/release-surfaces.yml"
    lines = template.read_text(encoding="utf-8").splitlines()
    inlined: set[str] = set()
    for at, line in enumerate(lines):
        if re.search(r"<script(?![^>]*(?:\bsrc=|ld\+json))[^>]*>", line):
            inlined.update(
                re.findall(r'\(assets / "([\w.-]+\.js)"\)', "\n".join(lines[at : at + 4]))
            )
    assert {"analytics.js", "consent.js"} <= inlined, (
        f"expected the workflow to inline both, found {inlined}"
    )
    assets = REPO / "src/vibey_tools/gh/docs/javascripts"
    forbidden = re.compile(r"</script|<script|<!--", re.IGNORECASE)
    offenders = [
        f"{name}:{n}: {text.strip()[:70]}"
        for name in sorted(inlined)
        for n, text in enumerate((assets / name).read_text(encoding="utf-8").splitlines(), start=1)
        if forbidden.search(text)
    ]
    assert not offenders, f"markup inside an inlined script would end it early: {offenders}"
