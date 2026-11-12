"""Every tracked Python file is ruff-checked AND type-checked, or is recorded as not being.

A tracked `.py` that no gate sees is one nobody is checking (the reason `scripts/` and the
storm tools joined `[tool.ruff] include`). The rule, per file from `git ls-files '*.py'` plus
untracked files git does not ignore (so a new file fails locally, before CI):

  (a) ruff checks it: the set is whatever `ruff check --show-files .` lists, so the tenants' own
      `[tool.ruff]` tables (claudeloop excludes `legacy`; krypton-app has its own) are honoured
      rather than modelled, AND
  (b) it is under a tree checked with `mypy`: `src/vibey` (`[tool.mypy]`, strict), a
      `[[tool.vibey.static_gates]]` path (strict), or a tenant tree named by the `static` command
      of its `tools` rows in `.github/ci-matrices.toml` (the tenants' own mypy settings; gh and
      bootstrap are looser than `--strict`),

or it is under a prefix recorded in `tests/meta/ungated_python.toml` with a reason. A prefix ends
in `/` or names one tracked file, and its reason is at least `MIN_REASON` characters. The list is
a ratchet: a prefix that matches no tracked file, or only files that are now gated, fails, and
`CEILING` (a constant here, so the list cannot move its own limit) must equal its length. It
counts prefixes, not files, so a new test file under a recorded tree does not move it; a new
tree outside every gate (a new `tests/` subdirectory included) does. The census is a class so it
can be run on synthetic input.
"""

import subprocess
import sys
import tomllib
from collections.abc import Iterable, Mapping
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXEMPTIONS = Path(__file__).with_name("ungated_python.toml")

MIN_REASON = 20
"""A reason shorter than this says nothing a reviewer can weigh."""

CEILING = 41
"""The most prefixes that may be recorded as ungated. Lower it in the same change that gates a
tree; never raise it without a written reason in review."""


class GateCensus:
    """Which tracked Python files are outside every gate and not recorded as such."""

    def __init__(
        self,
        files: Iterable[str],
        linted: Iterable[str],
        gated_roots: Iterable[str],
        exempt: Mapping[str, str],
    ) -> None:
        self.files = sorted(files)
        self.ruff = set(linted)
        self.roots = [root.rstrip("/") + "/" for root in gated_roots]
        self.exempt = dict(exempt)

    def linted(self, path: str) -> bool:
        return path in self.ruff

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

    def malformed(self) -> list[str]:
        """Prefixes that are neither a directory (`.../`) nor exactly one tracked file."""
        return sorted(p for p in self.exempt if not p.endswith("/") and p not in self.files)

    def reasonless(self) -> list[str]:
        """Prefixes whose reason is too short to be one."""
        return sorted(p for p, reason in self.exempt.items() if len(reason.strip()) < MIN_REASON)


# ------------------------------------------------------------------- reading the repository


def tracked_python() -> list[str]:
    """Tracked `.py` files plus untracked ones git does not ignore."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted({line for line in out.splitlines() if (REPO / line).is_file()})


def ruff_files() -> set[str]:
    """The files ruff itself checks from the repository root, nested `[tool.ruff]` tables included."""
    out = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--show-files", "."],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    root = REPO.resolve()
    files: set[str] = set()
    for line in out.splitlines():
        path = Path(line).resolve()
        if path.suffix == ".py" and path.is_relative_to(root):
            files.add(path.relative_to(root).as_posix())
    return files


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


def recorded() -> dict[str, str]:
    table = tomllib.loads(EXEMPTIONS.read_text(encoding="utf-8"))
    return {row["prefix"]: row["reason"] for row in table["ungated"]}


def committed() -> GateCensus:
    return GateCensus(tracked_python(), ruff_files(), gated_roots(), recorded())


# ------------------------------------------------------------------- the repository


def test_every_tracked_python_file_is_gated_or_recorded_with_a_reason() -> None:
    assert committed().ungated() == [], (
        "these tracked Python files are outside ruff or every mypy-checked tree: "
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


def test_every_recorded_prefix_is_a_directory_or_one_tracked_file() -> None:
    assert committed().malformed() == [], (
        "a prefix must end in `/` or name exactly one tracked file: a bare string such as "
        "`tests` would also exempt `tests_new/` and every file that happens to start with it"
    )


def test_every_recorded_prefix_carries_a_real_reason() -> None:
    assert committed().reasonless() == [], f"a reason needs at least {MIN_REASON} characters"


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
    linted = ruff_files()
    assert "scripts/typescript_artifacts.py" in linted
    assert "clients/krypton-app/src/krypton_app/launcher.py" in linted, "a tenant's own [tool.ruff]"
    assert not any(f.startswith("src/vibey_runners/claude/legacy/") for f in linted), (
        "extend-exclude"
    )


# --------------------------------------------------------------- the census, on synthetic input

LINTED = [
    "src/vibey/domain/x.py",
    "scripts/a/b.py",
    "scripts/a.py",
    "tests/unit/test_x.py",
    "tests/a.py",
    "scripts/ok.py",
]
ROOTS = ["src/vibey", "scripts"]


def census(files: list[str], exempt: dict[str, str] | None = None) -> GateCensus:
    return GateCensus(files, LINTED, ROOTS, exempt or {})


REASON = "a reason that is long enough to be one"


def test_a_file_under_ruff_and_a_checked_tree_is_gated() -> None:
    assert census(["src/vibey/domain/x.py", "scripts/a/b.py"]).ungated() == []


def test_a_stray_file_at_the_root_is_reported() -> None:
    assert census(["scripts/a.py", "tmp_ungated.py"]).ungated() == ["tmp_ungated.py"]


def test_a_file_linted_but_not_type_checked_is_reported() -> None:
    assert census(["tests/unit/test_x.py"]).ungated() == ["tests/unit/test_x.py"]


def test_a_file_type_checked_but_not_listed_by_ruff_is_reported() -> None:
    """Under a mypy tree, yet a nested `extend-exclude` (claudeloop's `legacy`) keeps ruff off it."""
    assert census(["scripts/ok.py", "scripts/legacy/x.py"]).ungated() == ["scripts/legacy/x.py"]


def test_a_recorded_prefix_covers_its_files_and_only_them() -> None:
    exempt = {"tests/": REASON}
    assert census(["tests/unit/test_x.py", "clients/a.py"], exempt).ungated() == ["clients/a.py"]


def test_a_new_directory_beside_recorded_ones_is_reported() -> None:
    exempt = {"tests/unit/": REASON}
    assert census(["tests/unit/test_x.py", "tests/new/test_y.py"], exempt).ungated() == [
        "tests/new/test_y.py"
    ]


def test_a_prefix_matching_nothing_is_reported_as_unused() -> None:
    exempt = {"tests/": REASON, "gone/": REASON}
    assert census(["tests/a.py"], exempt).unused_exemptions() == ["gone/"]


def test_a_prefix_whose_files_are_all_gated_is_reported() -> None:
    exempt = {"scripts/": REASON, "tests/": REASON}
    found = census(["scripts/a.py", "tests/a.py"], exempt).exemptions_for_gated_files()
    assert found == ["scripts/"]


def test_a_short_reason_is_reported() -> None:
    assert census(["tests/a.py"], {"tests/": "  legacy  "}).reasonless() == ["tests/"]
    assert census(["tests/a.py"], {"tests/": REASON}).reasonless() == []


def test_a_bare_prefix_is_malformed_unless_it_is_one_tracked_file() -> None:
    files = ["tests/a.py", "tests_new/b.py", "tests/conftest.py"]
    exempt = {"tests": REASON, "tests/conftest.py": REASON, "tests/": REASON}
    assert census(files, exempt).malformed() == ["tests"]


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
