# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every tracked Python file is ruff-checked AND type-checked, or is recorded as not being.

A tracked `.py` that no gate sees is one nobody is checking (the reason `scripts/` and the
storm tools joined `[tool.ruff] include`). The rule, per file from `git ls-files '*.py'`:

  (a) it is under a `[tool.ruff] include` glob, AND
  (b) it is under a tree checked with `mypy --strict`: `src/vibey` (`[tool.mypy]`), a
      `[[tool.vibey.static_gates]]` path, or a tenant tree named by the `static` command of its
      `tools` rows in `.github/ci-matrices.toml`,

or it is under a prefix recorded in `tests/meta/ungated_python.toml` with a reason. The list is
a ratchet: a prefix that matches no tracked file, or only files that are now gated, fails, and
`CEILING` (a constant here, so the list cannot move its own limit) must equal its length. It
counts prefixes, not files, so a new test file under a recorded tree does not move it; a new
tree outside every gate does. The census is a class so it can be run on synthetic input.
"""

import re
import subprocess
import tomllib
from collections.abc import Iterable, Mapping
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXEMPTIONS = Path(__file__).with_name("ungated_python.toml")

CEILING = 23
"""The most prefixes that may be recorded as ungated. Lower it in the same change that gates a
tree; never raise it without a written reason in review."""


class GateCensus:
    """Which tracked Python files are outside every gate and not recorded as such."""

    def __init__(
        self,
        files: Iterable[str],
        ruff_globs: Iterable[str],
        gated_roots: Iterable[str],
        exempt: Mapping[str, str],
    ) -> None:
        self.files = sorted(files)
        self.ruff = [self.glob_regex(glob) for glob in ruff_globs]
        self.roots = [root.rstrip("/") + "/" for root in gated_roots]
        self.exempt = dict(exempt)

    @staticmethod
    def glob_regex(glob: str) -> re.Pattern[str]:
        """A ruff-style glob as a regex: `**/` spans directories, `*` stays in one."""
        out = ""
        i = 0
        while i < len(glob):
            if glob.startswith("**/", i):
                out += "(?:.*/)?"
                i += 3
            elif glob[i] == "*":
                out += "[^/]*"
                i += 1
            else:
                out += re.escape(glob[i])
                i += 1
        return re.compile(out + "\\Z")

    def linted(self, path: str) -> bool:
        return any(pattern.match(path) for pattern in self.ruff)

    def type_checked(self, path: str) -> bool:
        return any(path.startswith(root) for root in self.roots)

    def gated(self, path: str) -> bool:
        return self.linted(path) and self.type_checked(path)

    def exempted(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.exempt)

    def ungated(self) -> list[str]:
        return [f for f in self.files if not self.gated(f) and not self.exempted(f)]

    def unused_exemptions(self) -> list[str]:
        """Prefixes that match no tracked file."""
        return sorted(p for p in self.exempt if not any(f.startswith(p) for f in self.files))

    def exemptions_for_gated_files(self) -> list[str]:
        """Prefixes whose every file is already gated: the exemption has nothing left to say."""
        return sorted(
            p
            for p in self.exempt
            if (hits := [f for f in self.files if f.startswith(p)]) and all(map(self.gated, hits))
        )

    def reasonless(self) -> list[str]:
        return sorted(p for p, reason in self.exempt.items() if not reason.strip())


# ------------------------------------------------------------------- reading the repository


def tracked_python() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if (REPO / line).is_file()]


def tenant_trees(matrices: Mapping[str, object]) -> set[str]:
    """`<dir>/<path>` for each path a tenant's `static` command hands to mypy."""
    trees: set[str] = set()
    tools = matrices["tools"]
    assert isinstance(tools, dict)
    for rows in tools.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for segment in row.get("static", "").split("&&"):
                tokens = segment.split()
                if "mypy" not in tokens:
                    continue
                for token in tokens[tokens.index("mypy") + 1 :]:
                    if not token.startswith("-"):
                        trees.add(f"{row['dir']}/{token.rstrip('/')}")
    return trees


def gated_roots() -> set[str]:
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    mypy = project["tool"]["mypy"]
    roots = {f"{mypy['mypy_path']}/{package}" for package in mypy["packages"]}
    for gate in project["tool"]["vibey"]["static_gates"]:
        roots.update(gate["paths"])
    matrices = tomllib.loads((REPO / ".github" / "ci-matrices.toml").read_text(encoding="utf-8"))
    return roots | tenant_trees(matrices)


def ruff_globs() -> list[str]:
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return list(project["tool"]["ruff"]["include"])


def recorded() -> dict[str, str]:
    table = tomllib.loads(EXEMPTIONS.read_text(encoding="utf-8"))
    return {row["prefix"]: row["reason"] for row in table["ungated"]}


def committed() -> GateCensus:
    return GateCensus(tracked_python(), ruff_globs(), gated_roots(), recorded())


# ------------------------------------------------------------------- the repository


def test_every_tracked_python_file_is_gated_or_recorded_with_a_reason() -> None:
    assert committed().ungated() == [], (
        "these tracked Python files are outside the ruff include or every mypy --strict tree: "
        "bring them under a gate ([tool.ruff] include, [[tool.vibey.static_gates]]), or record "
        "their prefix in tests/meta/ungated_python.toml with the reason"
    )


def test_every_recorded_prefix_still_matches_a_tracked_file() -> None:
    assert committed().unused_exemptions() == [], (
        "these prefixes match no tracked file: delete them from tests/meta/ungated_python.toml"
    )


def test_a_prefix_whose_files_are_all_gated_leaves_the_list() -> None:
    assert committed().exemptions_for_gated_files() == [], (
        "every file under these prefixes is now gated: delete them from "
        "tests/meta/ungated_python.toml and lower CEILING"
    )


def test_every_recorded_prefix_carries_a_reason() -> None:
    assert committed().reasonless() == []


def test_the_ceiling_is_exactly_the_number_of_recorded_prefixes() -> None:
    assert len(recorded()) == CEILING, (
        f"CEILING is {CEILING} but {len(recorded())} prefixes are recorded: the list can only "
        "shrink, and CEILING falls with it (a rise needs a written reason in review)"
    )


def test_the_census_sees_the_trees_it_is_meant_to() -> None:
    roots = gated_roots()
    assert {"src/vibey", "scripts", "docs/plans/qwenstorm-3.0.0/tools"} <= roots
    assert "src/vibey_tools/gh/vibey_gh" in roots
    assert "src/vibey_runners/claude/src/claudeloop" in roots
    files = tracked_python()
    assert "scripts/typescript_artifacts.py" in files
    assert len(files) > 1500


# --------------------------------------------------------------- the census, on synthetic input

GLOBS = ["src/**/*.py", "tests/**/*.py", "scripts/**/*.py"]
ROOTS = ["src/vibey", "scripts"]


def census(files: list[str], exempt: dict[str, str] | None = None) -> GateCensus:
    return GateCensus(files, GLOBS, ROOTS, exempt or {})


def test_a_file_under_ruff_and_a_checked_tree_is_gated() -> None:
    assert census(["src/vibey/domain/x.py", "scripts/a/b.py"]).ungated() == []


def test_a_stray_file_at_the_root_is_reported() -> None:
    assert census(["scripts/a.py", "tmp_ungated.py"]).ungated() == ["tmp_ungated.py"]


def test_a_file_linted_but_not_type_checked_is_reported() -> None:
    assert census(["tests/unit/test_x.py"]).ungated() == ["tests/unit/test_x.py"]


def test_a_file_type_checked_but_outside_the_ruff_include_is_reported() -> None:
    files = ["scripts/ok.py", "scripts/notpython/x.txt.py"]
    narrow = GateCensus(files, ["scripts/*.py"], ROOTS, {})
    assert narrow.ungated() == ["scripts/notpython/x.txt.py"]


def test_a_recorded_prefix_covers_its_files_and_only_them() -> None:
    exempt = {"tests/": "linted, not typed"}
    assert census(["tests/unit/test_x.py", "clients/a.py"], exempt).ungated() == ["clients/a.py"]


def test_a_prefix_matching_nothing_is_reported_as_unused() -> None:
    exempt = {"tests/": "r", "gone/": "r"}
    assert census(["tests/a.py"], exempt).unused_exemptions() == ["gone/"]


def test_a_prefix_whose_files_are_all_gated_is_reported() -> None:
    exempt = {"scripts/": "r", "tests/": "r"}
    found = census(["scripts/a.py", "tests/a.py"], exempt).exemptions_for_gated_files()
    assert found == ["scripts/"]


def test_a_reasonless_prefix_is_reported() -> None:
    assert census(["tests/a.py"], {"tests/": "  "}).reasonless() == ["tests/"]


def test_a_glob_double_star_spans_directories_and_star_does_not() -> None:
    deep = GateCensus.glob_regex("src/**/*.py")
    assert deep.match("src/a/b/c.py") and deep.match("src/c.py")
    flat = GateCensus.glob_regex("scripts/*.py")
    assert flat.match("scripts/a.py") and not flat.match("scripts/d/a.py")


def test_tenant_trees_are_read_from_the_static_commands() -> None:
    matrices = {
        "tools": {
            "pr": [
                {"dir": "t/gh", "static": "python -m mypy vibey_gh"},
                {"dir": "t/b", "static": "python -m mypy vibey_b/ && python -m bandit -r vibey_b/"},
                {"dir": "t/c", "static": "mypy --strict src/c && lint-imports"},
                {"dir": "t/skills"},
            ],
            "select_on": {"docs": ["x"]},
        }
    }
    assert tenant_trees(matrices) == {"t/gh/vibey_gh", "t/b/vibey_b", "t/c/src/c"}
