# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh ci-areas` and `ci-matrix`: a diff becomes areas, a tier and matrices.

The rule under test is FAIL SAFE: a skipped required check counts as passing on GitHub, so
every doubt (an unmapped file, an empty diff, a failed git, an unknown event) is the full
tier, never a skip. Most tests run against the repository's REAL maps, because the maps are
the thing being shipped; a few use small synthetic ones to pin a rule in isolation.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
import yaml

from vibey_gh.ci_areas import AreaDecision, CiAreas, CiAreasCommand
from vibey_gh.cli import main
from vibey_gh.interfaces.ci_areas_interface import CiAreasCommandInterface, CiAreasInterface
from vibey_gh.interfaces.command_runner_interface import CommandResult, CommandRunnerInterface

ROOT = Path(__file__).resolve().parents[4]
AREAS_TOML = ROOT / ".github" / "ci-areas.toml"
MATRICES_TOML = ROOT / ".github" / "ci-matrices.toml"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"

pytestmark = pytest.mark.skipif(
    not AREAS_TOML.is_file(), reason="the repository's CI maps are not beside this tenant"
)

PR = {"event": "pull_request", "base_ref": "develop"}
PATHS = (ROOT, AREAS_TOML, MATRICES_TOML)
TOOLS_DIRS = {
    "vibey-gh": "src/vibey_tools/gh",
    "vibey-skills": "src/vibey_tools/skills",
    "vibey-bootstrap": "src/vibey_tools/bootstrap",
    "vibey-runners-common": "src/vibey_runners/common",
    "claudeloop": "src/vibey_runners/claude",
    "codexloop": "src/vibey_runners/codex",
    "qwenloop": "src/vibey_runners/qwen",
}


def real() -> CiAreas:
    return CiAreas.load(AREAS_TOML, MATRICES_TOML)


def classify(*paths: str, **kwargs: str) -> AreaDecision:
    return real().classify(list(paths), **({**PR, **kwargs}))


def packages(decision: AreaDecision, job: str = "tools") -> list[str]:
    return [row["package"] for row in real().matrix(job, decision)["include"]]


class FakeRunner(CommandRunnerInterface):
    """Answers every command with one canned result and remembers what it was asked."""

    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = "") -> None:
        self.result = CommandResult(returncode, stdout, stderr)
        self.calls: list[tuple[list[str], Path]] = []

    def run(
        self, argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None
    ) -> CommandResult:
        self.calls.append((list(argv), cwd))
        return self.result


def run_areas(runner: FakeRunner, capsys, **overrides: Any) -> tuple[int, dict[str, str], str]:
    args: dict[str, Any] = {
        "base": "a" * 40,
        "head": "b" * 40,
        "event": "pull_request",
        "base_ref": "develop",
        "fmt": "github-output",
        "paths": PATHS,
    }
    status = CiAreasCommand(runner=runner).areas(**{**args, **overrides})
    captured = capsys.readouterr()
    lines = dict(line.split("=", 1) for line in captured.out.splitlines() if "=" in line)
    return status, lines, captured.err


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


# ----------------------------------------------------------------------- areas and tier


def test_a_docs_only_diff_yields_docs_and_tier_pr() -> None:
    decision = classify("docs/guides/x.md")
    assert decision.areas == {"docs"}
    assert not decision.full
    assert decision.reasons == ()
    assert real().outputs(decision)["tier"] == "pr"


def test_python_source_yields_python() -> None:
    decision = classify("src/vibey/domain/x.py", "tests/domain/test_x.py")
    assert decision.areas == {"python"}
    assert not decision.full


def test_a_tenant_path_yields_tools_and_selects_its_row_and_its_dependants() -> None:
    decision = classify("src/vibey_tools/gh/vibey_gh/x.py")
    assert decision.areas == {"tools"}
    assert not decision.full
    assert sorted(packages(decision)) == ["vibey-bootstrap", "vibey-gh"]
    for row in real().matrix("tools", decision)["include"]:
        assert (row["python"], row.get("os")) == ("3.12", None)


# A package's row plus every row that (transitively) installs it, derived from `install`.
CLOSURES = {
    "src/vibey_runners/common/x.py": {
        "vibey-runners-common",
        "vibey-gh",
        "claudeloop",
        "codexloop",
        "vibey-bootstrap",
    },
    "src/vibey_tools/gh/vibey_gh/x.py": {"vibey-gh", "vibey-bootstrap"},
    "src/vibey_tools/bootstrap/x.py": {"vibey-bootstrap"},
    "src/vibey_tools/skills/x.py": {"vibey-skills"},
    "src/vibey_runners/qwen/x.py": {"qwenloop"},
    "src/vibey_runners/claude/x.py": {"claudeloop"},
    "src/vibey_runners/codex/x.py": {"codexloop"},
}


@pytest.mark.parametrize(("path", "expected"), sorted(CLOSURES.items()))
def test_a_changed_package_selects_exactly_itself_and_what_installs_it(
    path: str, expected: set[str]
) -> None:
    assert set(packages(classify(path))) == expected
    assert len(packages(classify(path))) == len(expected)


def test_the_derived_dependency_edges_are_exactly_the_known_set() -> None:
    # A new tenant install edge must change this test knowingly.
    assert real().dependencies("tools") == {
        "vibey-gh": {"vibey-runners-common"},
        "vibey-bootstrap": {"vibey-gh"},
        "claudeloop": {"vibey-runners-common"},
        "codexloop": {"vibey-runners-common"},
        "vibey-skills": set(),
        "qwenloop": set(),
        "vibey-runners-common": set(),
    }


def tools_job(install_by_package: dict[str, Any]) -> CiAreas:
    """A synthetic tools matrix: package -> (dir, install) with one row each."""
    rows = [
        {"package": name, "dir": f"d/{name}", **({"install": text} if text is not None else {})}
        for name, text in install_by_package.items()
    ]
    job = {
        "areas": ["tools"],
        "owner_key": "dir",
        "name_key": "package",
        "full": rows,
        "pr": rows,
    }
    areas = {"areas": {"tools": {"paths": ["d/**"]}}, "full": {"paths": []}}
    return CiAreas(areas, {"tools": job})


def test_a_row_whose_install_has_no_editable_path_is_a_leaf_never_an_error() -> None:
    ci = tools_job({"a": 'pip install -e ".[dev]"', "b": "pip install pytest", "c": None})
    assert ci.dependencies("tools") == {"a": set(), "b": set(), "c": set()}
    assert ci.classify(["d/a/x.py"], **PR).owners == {"d/a"}


def test_an_unparseable_or_unresolvable_install_widens_never_raises() -> None:
    for bad in ('pip install -e "../x', "pip install -e", "pip install -e ../nowhere"):
        ci = tools_job({"a": "pip install pytest", "b": bad})
        # b cannot say what it depends on, so a change to ANY package selects it.
        owners = ci.classify(["d/a/x.py"], **PR).owners
        assert owners == {"d/a", "d/b"}, bad


def test_a_job_without_owners_has_no_dependency_edges() -> None:
    assert real().dependencies("postgres-compatibility") == {}
    with pytest.raises(ValueError, match="no matrix job"):
        real().dependencies("nope")


def test_two_tenants_that_install_each_other_do_not_loop() -> None:
    ci = tools_job({"a": "pip install -e ../b", "b": "pip install -e ../a"})
    assert ci.classify(["d/a/x.py"], **PR).owners == {"d/a", "d/b"}


def test_two_packages_select_the_union_of_their_closures() -> None:
    decision = classify("src/vibey_tools/gh/a.py", "src/vibey_runners/qwen/b.py")
    assert sorted(packages(decision)) == ["qwenloop", "vibey-bootstrap", "vibey-gh"]


def test_an_unowned_path_under_the_tools_trees_selects_every_pr_row() -> None:
    decision = classify("src/vibey_tools/brand-new-tenant/x.py")
    assert decision.areas == {"tools"}
    assert sorted(packages(decision)) == sorted(TOOLS_DIRS)


def test_a_python_only_pr_selects_no_tenant_row() -> None:
    # No tenant imports the root package `vibey`; the full tier still runs them at the queue.
    decision = classify("src/vibey/x.py")
    assert packages(decision) == []
    assert real().outputs(decision)["tools_any"] == "false"


def test_python_plus_a_tenant_selects_only_the_tenants_closure() -> None:
    decision = classify("src/vibey/x.py", "src/vibey_tools/skills/a.py")
    assert packages(decision) == ["vibey-skills"]


def test_a_docs_change_selects_the_vibey_gh_row_and_its_dependants() -> None:
    # The vibey-gh suite reads root docs (README.md, docs/index.md, a runbook).
    for path in ("docs/runbooks/sovereign-review-runner.md", "README.md", "docs/index.md"):
        decision = classify(path)
        assert decision.areas == {"docs"}
        assert sorted(packages(decision)) == ["vibey-bootstrap", "vibey-gh", "vibey-skills"], path
        assert real().outputs(decision)["tools_any"] == "true"


def test_select_on_is_declared_in_the_toml() -> None:
    # vibey-skills too: its tools/check_links.py needs docs/context-microslices.md to exist.
    assert real()._jobs["tools"]["select_on"] == {"docs": ["vibey-gh", "vibey-skills"]}


def test_a_core_change_yields_vscode_and_app() -> None:
    decision = classify("packages/vibey-core/src/index.ts")
    assert decision.areas == {"vscode", "app"}
    assert not decision.full


@pytest.mark.parametrize(
    ("path", "area"),
    [
        ("clients/vscode/src/x.ts", "vscode"),
        ("clients/app/src/x.ts", "app"),
        ("clients/krypton-app/x.py", "krypton_app"),
        ("clients/desktop/src/main.c", "desktop"),
        ("deploy/helm/vibey/values.yaml", "deploy"),
        ("docs/a/b/c.md", "docs"),
        ("docs-src/explorer.ts", "docs"),
        ("docs-theme/main.html", "docs"),
        ("properdocs.yml", "docs"),
        ("src/vibey/x.py", "python"),
    ],
)
def test_each_area_claims_its_paths(path: str, area: str) -> None:
    decision = classify(path)
    assert decision.areas == {area}
    assert not decision.full


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "SUPPORT.md",
        "CHANGELOG.md",
        "CLAUDE.md",
        "AGENTS.md",
        "GEMINI.md",
    ],
)
def test_the_root_markdown_is_docs_by_exact_name(path: str) -> None:
    decision = classify(path)
    assert decision.areas == {"docs"}
    assert not decision.full


def test_a_nested_readme_is_not_a_root_markdown_file() -> None:
    # `clients/app/README.md` is the app's, not docs: a bare `*.md` must not cross `/`.
    assert classify("clients/app/README.md").areas == {"app"}
    # And a nested markdown file no area owns is unmapped, so full, not silently docs.
    decision = classify("somewhere/README.md")
    assert decision.full
    assert any("somewhere/README.md is in no area" in reason for reason in decision.reasons)


def test_a_new_root_markdown_file_is_a_decision_not_a_skip() -> None:
    decision = classify("NEWFILE.md")
    assert decision.full
    assert decision.areas == frozenset()


# ----------------------------------------------------------------------------- globs


def synthetic(areas: Mapping[str, list[str]], full: list[str]) -> CiAreas:
    return CiAreas(
        {
            "areas": {name: {"paths": paths} for name, paths in areas.items()},
            "full": {"paths": full},
        },
        {},
    )


def test_glob_semantics_star_stays_in_a_directory_and_double_star_crosses() -> None:
    ci = synthetic(
        {"a": ["*.md", "deep/**", "mid/**/leaf.txt", "q?.txt", "k/*/z"]},
        [],
    )

    def hit(path: str) -> bool:
        return not ci.unmapped([path])

    assert hit("r.md") and not hit("d/r.md")
    assert hit("deep/x") and hit("deep/a/b/c.md") and not hit("deep")
    assert hit("mid/leaf.txt") and hit("mid/a/leaf.txt") and hit("mid/a/b/leaf.txt")
    assert hit("qa.txt") and not hit("q/.txt") and not hit("qab.txt")
    assert hit("k/a/z") and not hit("k/a/b/z")
    # A pattern is anchored to the whole path, and a regex metacharacter is a literal.
    assert not hit("xr.md/extra") and not hit("rxmd")
    assert not synthetic({"a": ["a+b.txt"]}, []).unmapped(["a+b.txt"])
    assert synthetic({"a": ["a+b.txt"]}, []).unmapped(["aab.txt"]) == ["aab.txt"]


def test_a_path_in_an_area_and_on_the_full_list_is_full_and_keeps_its_area() -> None:
    ci = synthetic({"docs": ["docs/**"]}, ["docs/generated/**"])
    decision = ci.classify(["docs/generated/a.md"], **PR)
    assert decision.full
    assert decision.areas == {"docs"}
    assert (
        "docs/generated/a.md matches the always-full pattern docs/generated/**" in decision.reasons
    )


@pytest.mark.parametrize("bad", [{"paths": "docs/**"}, {"paths": [1]}, {}])
def test_a_malformed_path_list_is_refused_not_read_as_empty(bad: dict) -> None:
    with pytest.raises(ValueError, match="needs `paths`"):
        CiAreas({"areas": {"docs": bad}, "full": {"paths": []}}, {})
    with pytest.raises(ValueError, match=r"\[full\] needs `paths`"):
        CiAreas({"areas": {}, "full": bad}, {})


# ---------------------------------------------------------------------------- always full


def full_samples() -> list[str]:
    patterns = real()._full  # the declared always-full globs, so a new entry is tested too
    return [pattern.replace("**", "a/b").replace("*", "a") for pattern, _ in patterns]


@pytest.mark.parametrize(
    "path",
    [
        *full_samples(),
        ".github/workflows/ci.yml",
        "scripts/x.py",
        ".claude/skills/x/SKILL.md",
        "package.json",
        ".agents/skills/x/SKILL.md",
        ".agent/rules/x.md",
        ".cursor/rules/x.mdc",
        "research/model-quality/x.jsonl",
        "changelog.d/1.md",
    ],
)
def test_each_always_full_path_forces_full(path: str) -> None:
    decision = classify(path)
    assert decision.full
    assert any(path in reason and "always-full" in reason for reason in decision.reasons)
    # The tier is full whatever else the diff holds.
    assert real().outputs(decision)["tier"] == "full"
    assert classify("docs/x.md", path).full


def test_the_always_full_list_covers_the_plans_named_paths() -> None:
    declared = {pattern for pattern, _ in real()._full}
    assert {
        ".github/**",
        "scripts/**",
        "pyproject.toml",
        "uv.lock",
        ".node-version",
        "package.json",
        "package-lock.json",
        ".importlinter",
        ".python-version",
        ".vibey-gh.toml",
        "design/**",
        "research/**",
        "changelog.d/**",
        ".claude/**",
        ".agent*/**",
        ".cursor/**",
        ".githooks/**",
        ".vibey/**",
    } <= declared


def test_an_unmapped_file_forces_full_with_a_reason_naming_it() -> None:
    decision = classify("docs/x.md", "mystery/dir/file.bin")
    assert decision.full
    assert decision.areas == {"docs"}
    assert "mystery/dir/file.bin is in no area and not on the always-full list" in decision.reasons


def test_an_empty_diff_forces_full() -> None:
    for paths in ([], [""]):
        decision = real().classify(paths, **PR)
        assert decision.full
        assert decision.areas == frozenset()
        assert any("diff is empty" in reason for reason in decision.reasons)


def test_a_long_list_of_reasons_is_capped_with_a_count() -> None:
    decision = classify(*[f"nowhere/{n}.bin" for n in range(25)])
    assert len(decision.reasons) == 21
    assert decision.reasons[-1] == "... and 5 more"


# ------------------------------------------------------------------------------ events


@pytest.mark.parametrize(
    ("event", "base_ref"),
    [
        ("merge_group", ""),
        ("merge_group", "develop"),
        ("workflow_dispatch", "develop"),
        ("schedule", ""),
        ("pull_request", "main"),
        ("push", "main"),
    ],
)
def test_each_full_event_forces_full(event: str, base_ref: str) -> None:
    decision = real().classify(["docs/x.md"], event=event, base_ref=base_ref)
    assert decision.full
    assert decision.areas == {"docs"}
    assert decision.reasons[0].startswith(f"the {event} event")


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_a_diff_event_into_the_integration_branch_is_decided_by_the_diff(event: str) -> None:
    decision = real().classify(["docs/x.md"], event=event, base_ref="develop")
    assert not decision.full


@pytest.mark.parametrize("event", ["", "check_suite", "release", "Pull_Request"])
def test_an_unknown_event_forces_full(event: str) -> None:
    decision = real().classify(["docs/x.md"], event=event, base_ref="develop")
    assert decision.full
    assert "not one the declaration recognises" in decision.reasons[0]


def test_a_pull_request_with_no_target_branch_forces_full() -> None:
    decision = real().classify(["docs/x.md"], event="pull_request", base_ref="")
    assert decision.full
    assert "names no target branch" in decision.reasons[0]


def test_the_event_table_is_declared_data_and_defaults_when_absent() -> None:
    custom = CiAreas(
        {
            "areas": {"docs": {"paths": ["docs/**"]}},
            "full": {"paths": []},
            "events": {
                "full": ["nightly"],
                "diff": ["pull_request"],
                "full_base_refs": ["release"],
            },
        },
        {},
    )
    assert custom.gate("nightly", "") and custom.gate("push", "develop")
    assert custom.gate("pull_request", "release")
    assert custom.gate("pull_request", "main") == ()
    defaults = synthetic({"docs": ["docs/**"]}, [])
    assert defaults.gate("merge_group", "") and defaults.gate("push", "main")
    assert defaults.gate("push", "develop") == ()


def test_the_full_decision_names_every_area_and_the_reasons_it_was_given() -> None:
    decision = real().full_decision("because", "and because")
    assert decision.full and decision.reasons == ("because", "and because")
    assert decision.areas == {
        "python",
        "tools",
        "vscode",
        "app",
        "krypton_app",
        "desktop",
        "deploy",
        "docs",
    }


# ----------------------------------------------------------------------------- matrices


def toml_rows(job: str, tier: str) -> list[dict[str, Any]]:
    return real().rows(job, tier)


def ci_yml_rows() -> dict[str, list[dict[str, Any]]]:
    jobs = yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"]
    return {
        "tools": jobs["tools"]["strategy"]["matrix"]["include"],
        "postgres-compatibility": [
            {"postgres": version}
            for version in jobs["postgres-compatibility"]["strategy"]["matrix"]["postgres"]
        ],
        "desktop": jobs["desktop"]["strategy"]["matrix"]["include"],
    }


def test_the_toml_full_rows_equal_the_ci_yml_matrix_rows() -> None:
    # The two cannot drift until the jobs read the TOML (a later task moves them).
    declared = ci_yml_rows()
    assert {job: len(rows) for job, rows in declared.items()} == {
        "tools": 24,
        "postgres-compatibility": 5,
        "desktop": 4,
    }
    for job, rows in declared.items():
        assert toml_rows(job, "full") == rows, job
    assert [row["postgres"] for row in toml_rows("postgres-compatibility", "full")] == [
        14,
        15,
        16,
        17,
        18,
    ]


def test_the_vscode_extension_is_not_a_matrix_job_here() -> None:
    assert "vscode" not in real()._jobs
    assert "vscode-extension" not in real()._jobs


def test_the_union_of_pr_and_full_rows_is_the_full_set_and_pr_rows_are_a_subset() -> None:
    for job in ("tools", "postgres-compatibility", "desktop"):
        full, pr = toml_rows(job, "full"), toml_rows(job, "pr")
        assert pr, job
        assert all(row in full for row in pr), job
        assert len(full) > len(pr), job
    assert len(toml_rows("tools", "pr")) == 7
    assert {row["package"] for row in toml_rows("tools", "pr")} == set(TOOLS_DIRS)
    assert all(row["python"] == "3.12" and "os" not in row for row in toml_rows("tools", "pr"))
    assert [row["postgres"] for row in toml_rows("postgres-compatibility", "pr")] == [14, 18]
    assert [row["distro"] for row in toml_rows("desktop", "pr")] == ["ubuntu"]


def test_the_pr_tier_matrices_follow_the_areas() -> None:
    python = classify("src/vibey/x.py")
    assert [
        row["postgres"] for row in real().matrix("postgres-compatibility", python)["include"]
    ] == [
        14,
        18,
    ]
    assert real().matrix("desktop", python)["include"] == []
    desktop = classify("clients/desktop/src/x.c")
    assert [row["distro"] for row in real().matrix("desktop", desktop)["include"]] == ["ubuntu"]
    assert real().matrix("tools", desktop)["include"] == []


def test_a_full_decision_selects_every_full_row() -> None:
    decision = real().full_decision("x")
    assert len(real().matrix("tools", decision)["include"]) == 24
    assert len(real().matrix("postgres-compatibility", decision)["include"]) == 5
    assert len(real().matrix("desktop", decision)["include"]) == 4


def test_owners_that_select_no_row_never_empty_the_job() -> None:
    ghost = AreaDecision(frozenset({"tools"}), False, (), frozenset({"nowhere/at/all"}))
    assert len(real().matrix("tools", ghost)["include"]) == 7
    no_owners = AreaDecision(frozenset({"tools"}), False, ())
    assert len(real().matrix("tools", no_owners)["include"]) == 7


def test_an_unknown_job_or_tier_is_refused() -> None:
    with pytest.raises(ValueError, match="no matrix job 'nope'"):
        real().rows("nope", "full")
    with pytest.raises(ValueError, match="no tier 'weekly'"):
        real().rows("tools", "weekly")
    with pytest.raises(ValueError, match="no matrix job 'nope'"):
        real().matrix("nope", classify("docs/x.md"))


def test_an_empty_row_set_prints_the_any_output_false_and_no_matrix() -> None:
    outputs = real().outputs(classify("deploy/helm/vibey/values.yaml"))
    assert outputs["tools_any"] == outputs["postgres_any"] == outputs["desktop_any"] == "false"
    assert not [key for key in outputs if key.endswith("_matrix")]
    assert "include" not in "".join(outputs.values())


def test_outputs_are_the_plans_lines_in_order() -> None:
    outputs = real().outputs(classify("src/vibey/x.py"))
    assert list(outputs) == [
        "areas",
        "full",
        "tier",
        "tools_any",
        "postgres_any",
        "desktop_any",
        "postgres_matrix",
    ]
    assert outputs["areas"] == '["python"]'
    assert (outputs["full"], outputs["tier"]) == ("false", "pr")
    assert outputs["tools_any"] == "false"
    assert json.loads(outputs["postgres_matrix"]) == {
        "include": [{"postgres": 14}, {"postgres": 18}]
    }
    both = real().outputs(classify("src/vibey/x.py", "src/vibey_tools/gh/a.py"))
    assert len(json.loads(both["tools_matrix"])["include"]) == 2


ALL_AREAS = sorted({"python", "tools", "vscode", "app", "krypton_app", "desktop", "deploy", "docs"})


def test_a_full_decision_always_prints_every_declared_area() -> None:
    # Whatever made it full: git failing, an empty diff, an always-full path, an event.
    cases = [
        real().full_decision("x"),
        real().classify([], **PR),
        real().classify([".github/workflows/ci.yml"], **PR),
        real().classify(["docs/x.md", "scripts/y.py"], **PR),
        real().classify(["src/vibey/x.py"], event="merge_group", base_ref=""),
    ]
    for decision in cases:
        assert decision.full
        assert json.loads(real().outputs(decision)["areas"]) == ALL_AREAS


def test_a_small_decision_prints_only_its_own_areas() -> None:
    assert real().outputs(classify("docs/x.md"))["areas"] == '["docs"]'


def test_an_always_full_path_prints_all_areas_through_the_cli(capsys) -> None:
    _, lines, _ = run_areas(FakeRunner(stdout=".github/workflows/ci.yml\0"), capsys)
    assert lines["full"] == "true"
    assert json.loads(lines["areas"]) == ALL_AREAS


def test_the_maps_are_validated_at_load_naming_the_key() -> None:
    good = {"areas": {"docs": {"paths": ["docs/**"]}}, "full": {"paths": []}}
    row = {"package": "p", "dir": "d/p"}

    def job(**over: Any) -> dict[str, Any]:
        base = {"areas": ["docs"], "owner_key": "dir", "name_key": "package"}
        return {**base, "full": [row], "pr": [row], **over}

    no_pr = {k: v for k, v in job().items() if k != "pr"}
    cases: list[tuple[dict, dict, str]] = [
        ({"areas": {"docs": "x"}, "full": {"paths": []}}, {}, r"\[areas.docs\] must be a table"),
        ({"areas": {}, "full": ["x"]}, {}, r"\[full\] must be a table"),
        ({"areas": ["x"], "full": {"paths": []}}, {}, r"\[areas\] must be a table"),
        (good, {"j": job(areas=["ghost"])}, r"\[j\].*`areas`.*'ghost'"),
        (good, {"j": job(select_all_on=["ghost"])}, r"\[j\].*`select_all_on`.*'ghost'"),
        (good, {"j": job(select_on={"ghost": ["p"]})}, r"\[j\].*`select_on`.*'ghost'"),
        (good, {"j": job(select_on={"docs": ["nope"]})}, r"\[j\].*`select_on`.*'nope'"),
        (good, {"j": job(select_on={"docs": "p"})}, r"\[j\].*`select_on`"),
        (good, {"j": no_pr}, r"\[j\] needs a `pr` list"),
        (good, {"j": {"areas": ["docs"]}}, r"\[j\] needs a `full` list"),
        (good, {"j": job(pr=[{"package": "p"}])}, r"\[j\].*`pr`.*`dir`"),
        (good, {"j": job(full=[{"dir": "d/p"}], pr=[row])}, r"\[j\].*`full`.*`package`"),
        (good, {"j": job(owner_key="dir", name_key="nope")}, r"\[j\].*`nope`"),
        (good, {"j": job(areas="docs")}, r"\[j\] `areas` must be a list"),
        (good, {"j": {k: v for k, v in job().items() if k != "name_key"}}, r"\[j\].*`name_key`"),
        ({**good, "events": ["x"]}, {}, r"\[events\] must be a table"),
        (good, {"j": 1}, r"\[j\] must be a table"),
        (good, {"j": [job()]}, r"\[j\] must be a table"),
        (good, {"j": job(full=[], pr=[])}, r"\[j\] `full` must not be empty"),
        (good, {"j": job(pr=[])}, r"\[j\] `pr` must not be empty"),
        (good, {"j": job(pr=["p"])}, r"\[j\] a `pr` row must be a table"),
        (good, {"j": job(full=["p"])}, r"\[j\] a `full` row must be a table"),
        (good, {"j": job(full=[{"package": "p", "dir": 3}])}, r"\[j\] `dir` must be a string"),
        (
            good,
            {"j": job(pr=[{"package": ["p"], "dir": "d/p"}])},
            r"\[j\] `package` must be a string",
        ),
        (good, {"j": job(output=3)}, r"\[j\] `output` must be a string"),
        (good, {"j": job(owner_key=3)}, r"\[j\] `owner_key` must be a string"),
        (good, {"j": job(name_key=3)}, r"\[j\] `name_key` must be a string"),
    ]
    for areas, matrices, message in cases:
        with pytest.raises(ValueError, match=message):
            CiAreas(areas, matrices)
    CiAreas(good, {"j": job()})  # a valid map loads


def test_the_implementation_honours_its_interface() -> None:
    assert isinstance(real(), CiAreasInterface)
    assert isinstance(CiAreasCommand(), CiAreasCommandInterface)


# ------------------------------------------------------------- the repository's own maps


def tracked_files() -> list[str]:
    done = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return [path for path in done.stdout.split("\0") if path]


def coverage_failure(ci: CiAreasInterface, files: list[str]) -> str:
    """The failure message for files neither an area nor `[full]` claims, or '' when none."""
    missing = ci.unmapped(files)
    if not missing:
        return ""
    return (
        f"{len(missing)} tracked file(s) are in no area and not on the always-full list "
        f"(first 10: {missing[:10]}). Add each to an [areas.*] table or to [full] in "
        ".github/ci-areas.toml, and say why when it goes to [full]."
    )


def test_the_repository_config_covers_every_tracked_file() -> None:
    files = tracked_files()
    assert len(files) > 1000
    assert coverage_failure(real(), files) == ""


def test_the_coverage_failure_names_up_to_ten_files() -> None:
    stray = [f"unmapped-dir/{n}.txt" for n in range(12)]
    message = coverage_failure(real(), [*tracked_files()[:5], *stray])
    assert message.startswith("12 tracked file(s) are in no area")
    assert "unmapped-dir/9.txt" in message and "unmapped-dir/10.txt" not in message
    assert ".github/ci-areas.toml" in message


# ---------------------------------------------------------------------------- the command


def defaults_for_everything(lines: dict[str, str]) -> None:
    assert lines["full"] == "true" and lines["tier"] == "full"
    assert json.loads(lines["areas"]) == sorted(
        {"python", "tools", "vscode", "app", "krypton_app", "desktop", "deploy", "docs"}
    )
    assert (lines["tools_any"], lines["postgres_any"], lines["desktop_any"]) == ("true",) * 3
    assert len(json.loads(lines["tools_matrix"])["include"]) == 24
    assert len(json.loads(lines["postgres_matrix"])["include"]) == 5
    assert len(json.loads(lines["desktop_matrix"])["include"]) == 4


def test_the_cli_prints_github_output_lines_and_defaults_to_full_when_git_fails(capsys) -> None:
    runner = FakeRunner(returncode=128, stderr="fatal: bad revision")
    status, lines, err = run_areas(runner, capsys)
    assert status == 0
    defaults_for_everything(lines)
    assert "git diff" in err and "failed (128)" in err and "fatal: bad revision" in err
    assert len(runner.calls) == 1


def test_the_diff_command_is_three_dot_no_renames_z(capsys) -> None:
    runner = FakeRunner(stdout="docs/x.md\0")
    run_areas(runner, capsys, base="1" * 40, head="2" * 40)
    assert runner.calls == [
        (["git", "diff", "--name-only", "--no-renames", "-z", f"{'1' * 40}...{'2' * 40}"], ROOT)
    ]


def test_a_clean_docs_diff_prints_the_pr_tier_and_only_the_gh_dependants(capsys) -> None:
    status, lines, err = run_areas(FakeRunner(stdout="docs/a.md\0docs/b/c.md\0"), capsys)
    assert status == 0
    assert lines["areas"] == '["docs"]'
    assert (lines["full"], lines["tier"]) == ("false", "pr")
    assert (lines["postgres_any"], lines["desktop_any"]) == ("false", "false")
    assert lines["tools_any"] == "true"
    rows = json.loads(lines["tools_matrix"])["include"]
    assert sorted(row["package"] for row in rows) == [
        "vibey-bootstrap",
        "vibey-gh",
        "vibey-skills",
    ]
    assert "postgres_matrix" not in lines and "desktop_matrix" not in lines
    assert err == ""


def test_a_deploy_only_diff_prints_no_matrix_at_all(capsys) -> None:
    _, lines, err = run_areas(FakeRunner(stdout="deploy/helm/vibey/values.yaml\0"), capsys)
    assert (lines["tools_any"], lines["postgres_any"], lines["desktop_any"]) == ("false",) * 3
    assert not [key for key in lines if key.endswith("_matrix")]
    assert err == ""


def test_a_python_diff_prints_the_small_matrices(capsys) -> None:
    status, lines, _ = run_areas(FakeRunner(stdout="src/vibey/x.py\0"), capsys)
    assert status == 0 and lines["tier"] == "pr"
    assert lines["postgres_any"] == "true"
    assert json.loads(lines["postgres_matrix"]) == {"include": [{"postgres": 14}, {"postgres": 18}]}
    assert lines["desktop_any"] == "false" and "desktop_matrix" not in lines


def test_a_full_event_never_runs_git(capsys) -> None:
    runner = FakeRunner(returncode=1)
    for event, base_ref in (
        ("merge_group", ""),
        ("workflow_dispatch", ""),
        ("pull_request", "main"),
    ):
        status, lines, err = run_areas(runner, capsys, event=event, base_ref=base_ref)
        assert status == 0
        defaults_for_everything(lines)
        assert f"the {event} event" in err
    status, lines, err = run_areas(runner, capsys, event="unheard_of")
    assert status == 0 and lines["full"] == "true" and "not one the declaration recognises" in err
    assert runner.calls == []


@pytest.mark.parametrize(
    ("base", "head", "why"),
    [
        ("", "b" * 40, "no usable base or head"),
        ("a" * 40, "", "no usable base or head"),
        ("0" * 40, "b" * 40, "no usable base or head"),
        ("--output=/tmp/x", "b" * 40, "looks like an option"),
        ("a" * 40, "--output=/tmp/x", "looks like an option"),
    ],
)
def test_an_unusable_base_or_head_is_full_without_calling_git(base, head, why, capsys) -> None:
    runner = FakeRunner(stdout="docs/x.md\0")
    status, lines, err = run_areas(runner, capsys, base=base, head=head)
    assert status == 0
    defaults_for_everything(lines)
    assert why in err
    assert runner.calls == []


def test_an_empty_diff_from_git_prints_the_full_defaults(capsys) -> None:
    status, lines, err = run_areas(FakeRunner(stdout=""), capsys)
    assert status == 0
    assert lines["full"] == "true" and lines["tier"] == "full"
    assert json.loads(lines["areas"]) == ALL_AREAS
    assert "diff is empty" in err


def test_a_path_with_spaces_and_non_ascii_survives_the_nul_separated_parse(capsys) -> None:
    name = 'dir with space/café ünïcode "quoted".md'
    status, lines, err = run_areas(FakeRunner(stdout=f"docs/a.md\0{name}\0"), capsys)
    assert status == 0 and lines["full"] == "true"
    assert f"{name} is in no area and not on the always-full list" in err


def test_the_json_format_prints_one_object_with_the_reasons(capsys) -> None:
    runner = FakeRunner(stdout="docs/a.md\0mystery.bin\0")
    status = CiAreasCommand(runner=runner).areas(
        base="a" * 40,
        head="b" * 40,
        event="pull_request",
        base_ref="develop",
        fmt="json",
        paths=PATHS,
    )
    document = json.loads(capsys.readouterr().out)
    assert status == 0
    assert document["areas"] == ALL_AREAS
    assert document["full"] is True and document["tier"] == "full"
    assert document["reasons"] == ["mystery.bin is in no area and not on the always-full list"]
    assert document["outputs"]["tier"] == "full"


def test_a_broken_map_widens_to_the_full_defaults_and_exits_zero(tmp_path, capsys) -> None:
    broken = tmp_path / "areas.toml"
    broken.write_text("[areas.docs]\npaths = 'not a list'\n[full]\npaths = []\n")
    garbled = tmp_path / "garbled.toml"
    garbled.write_text("this is = = not toml")
    ghost = tmp_path / "ghost.toml"
    ghost.write_text(
        MATRICES_TOML.read_text(encoding="utf-8").replace(
            'areas = ["desktop"]', 'areas = ["desktop", "no_such_area"]'
        )
    )
    no_full = tmp_path / "nofull.toml"
    no_full.write_text('[tools]\nareas = ["tools"]\n')
    not_a_table = tmp_path / "areas-list.toml"
    not_a_table.write_text('areas = ["docs"]\n[full]\npaths = []\n')
    runner = FakeRunner(stdout="docs/x.md\0")
    # The areas map is readable: every area name is still printed.
    for matrices_path in (garbled, ghost, no_full):
        status, lines, err = run_areas(runner, capsys, paths=(ROOT, AREAS_TOML, matrices_path))
        assert status == 0
        assert (lines["full"], lines["tier"]) == ("true", "full")
        assert json.loads(lines["areas"]) == ALL_AREAS
        assert "vibey-gh: ci-areas:" in err
    # The areas map is the broken one: say so, and print what can still be said.
    cases = ((tmp_path / "missing.toml", []), (broken, ["docs"]), (not_a_table, []))
    for areas_path, names in cases:
        status, lines, err = run_areas(runner, capsys, paths=(ROOT, areas_path, MATRICES_TOML))
        assert status == 0
        assert (lines["full"], lines["tier"]) == ("true", "full")
        assert json.loads(lines["areas"]) == names
        assert (lines["tools_any"], len(json.loads(lines["tools_matrix"])["include"])) == (
            "true",
            24,
        )
        assert "vibey-gh: ci-areas:" in err
    assert runner.calls == []


def test_ci_matrix_prints_one_tier_of_one_job(capsys) -> None:
    command = CiAreasCommand(runner=FakeRunner())
    assert command.matrix(job="postgres-compatibility", tier="pr", paths=PATHS) == 0
    assert capsys.readouterr().out.strip() == '{"include":[{"postgres":14},{"postgres":18}]}'
    assert command.matrix(job="tools", tier="full", paths=PATHS) == 0
    assert len(json.loads(capsys.readouterr().out)["include"]) == 24


def test_ci_matrix_refuses_an_unknown_job_and_a_broken_map(tmp_path, capsys) -> None:
    command = CiAreasCommand(runner=FakeRunner())
    assert command.matrix(job="nope", tier="pr", paths=PATHS) == 1
    assert "no matrix job 'nope'" in capsys.readouterr().err
    missing = (ROOT, tmp_path / "none.toml", MATRICES_TOML)
    assert command.matrix(job="tools", tier="pr", paths=missing) == 1
    assert "vibey-gh: ci-matrix:" in capsys.readouterr().err


# ----------------------------------------------------------- registration, and real git


def test_both_subcommands_are_registered_and_find_the_maps_from_the_root(
    monkeypatch, capsys
) -> None:
    monkeypatch.chdir(ROOT)
    assert main(["ci-areas", "--event", "workflow_dispatch"]) == 0
    defaults_for_everything(
        dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    )
    assert main(["ci-matrix", "--job", "desktop"]) == 0
    assert len(json.loads(capsys.readouterr().out)["include"]) == 4
    assert main(["ci-matrix", "--job", "desktop", "--tier", "pr"]) == 0
    assert [row["distro"] for row in json.loads(capsys.readouterr().out)["include"]] == ["ubuntu"]


def test_real_git_a_three_dot_diff_with_awkward_names_and_a_base_that_moved_on(
    tmp_path, capsys
) -> None:
    git(tmp_path, "init", "-q", "-b", "develop")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "README.md").write_text("base\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    fork = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "checkout", "-q", "-b", "topic")
    awkward = tmp_path / "dir with space"
    awkward.mkdir()
    (awkward / "café ünï.md").write_text("x\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("x\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "topic work")
    topic = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "checkout", "-q", "develop")
    (tmp_path / "src" / "vibey").mkdir(parents=True)
    (tmp_path / "src" / "vibey" / "newer.py").write_text("x = 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "the base moved on")
    moved = git(tmp_path, "rev-parse", "HEAD")
    assert moved != fork

    status = CiAreasCommand().areas(
        base=moved,
        head=topic,
        event="pull_request",
        base_ref="develop",
        fmt="github-output",
        paths=(tmp_path, AREAS_TOML, MATRICES_TOML),
    )
    captured = capsys.readouterr()
    assert status == 0
    # The topic's own two files are charged to it, whole; the base's newer file is not.
    assert "dir with space/café ünï.md is in no area" in captured.err
    assert "newer.py" not in captured.err
    lines = dict(line.split("=", 1) for line in captured.out.splitlines())
    assert json.loads(lines["areas"]) == ALL_AREAS and lines["full"] == "true"

    git(tmp_path, "checkout", "-q", "topic")
    git(tmp_path, "rm", "-q", "-r", "dir with space")
    git(tmp_path, "commit", "-q", "-m", "drop the awkward file")
    clean = CiAreasCommand().areas(
        base=moved,
        head=git(tmp_path, "rev-parse", "HEAD"),
        event="pull_request",
        base_ref="develop",
        fmt="github-output",
        paths=(tmp_path, AREAS_TOML, MATRICES_TOML),
    )
    out = capsys.readouterr().out
    assert clean == 0 and 'areas=["docs"]' in out and "full=false" in out and "tier=pr" in out


def test_real_git_a_path_with_a_newline_can_never_inject_an_output_line(tmp_path, capsys) -> None:
    git(tmp_path, "init", "-q", "-b", "develop")
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "README.md").write_text("base\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    base = git(tmp_path, "rev-parse", "HEAD")
    evil = "zz\nfull=false\ntier=pr\ntools_any=false.bin"
    (tmp_path / evil).write_text("x\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "a path with newlines")
    status = CiAreasCommand().areas(
        base=base,
        head=git(tmp_path, "rev-parse", "HEAD"),
        event="pull_request",
        base_ref="develop",
        fmt="github-output",
        paths=(tmp_path, AREAS_TOML, MATRICES_TOML),
    )
    captured = capsys.readouterr()
    assert status == 0
    # With -z the name arrives whole (git without -z would quote it), it is judged unmapped,
    # and it appears only on stderr: stdout holds one `key=value` line per output, once each.
    assert f"{evil} is in no area" in captured.err
    keys = [line.split("=", 1)[0] for line in captured.out.splitlines()]
    assert keys == [
        "areas",
        "full",
        "tier",
        "tools_any",
        "postgres_any",
        "desktop_any",
        "tools_matrix",
        "postgres_matrix",
        "desktop_matrix",
    ]
    assert "full=true" in captured.out.splitlines()
    assert "full=false" not in captured.out.splitlines()


# ------------------------------------------------------------------ fix round 2


@pytest.mark.parametrize("key", ["full", "diff", "full_base_refs"])
def test_an_events_list_given_as_a_string_is_refused_at_load(key: str, tmp_path, capsys) -> None:
    # `full_base_refs = "main"` used to become ('m', 'a', 'i', 'n') and let a promotion
    # pull request into main run the small tier.
    areas = {
        "areas": {"docs": {"paths": ["docs/**"]}},
        "full": {"paths": []},
        "events": {key: "main"},
    }
    with pytest.raises(ValueError, match=rf"\[events\] `{key}` must be a list of strings"):
        CiAreas(areas, {})
    with pytest.raises(ValueError, match=rf"\[events\] `{key}` must be a list"):
        CiAreas({**areas, "events": {key: ["ok", 3]}}, {})
    broken = tmp_path / "areas.toml"
    broken.write_text(
        f'[areas.docs]\npaths = ["docs/**"]\n[full]\npaths = []\n[events]\n{key} = "main"\n'
    )
    status, lines, err = run_areas(
        FakeRunner(stdout="docs/x.md\0"), capsys, paths=(ROOT, broken, MATRICES_TOML)
    )
    assert status == 0
    assert (lines["full"], lines["tier"]) == ("true", "full")
    assert json.loads(lines["areas"]) == ["docs"]
    assert f"`{key}` must be a list of strings" in err


def test_the_release_branch_is_always_a_full_base_ref() -> None:
    import tomllib

    release = tomllib.loads((ROOT / ".vibey-gh.toml").read_text(encoding="utf-8"))["branches"][
        "release"
    ]
    assert release in real()._full_base_refs
    assert real().classify(["docs/x.md"], event="pull_request", base_ref=release).full


def test_the_skills_row_follows_docs_and_nothing_else_does() -> None:
    decision = classify("docs/context-microslices.md")
    assert set(packages(decision)) == {"vibey-gh", "vibey-bootstrap", "vibey-skills"}
    assert len(packages(decision)) == 3
    others = real().outputs(decision)
    assert (others["postgres_any"], others["desktop_any"]) == ("false", "false")


def test_a_desktop_pr_list_of_strings_prints_the_all_full_fallback_and_exits_zero(
    tmp_path, capsys
) -> None:
    bad = tmp_path / "matrices.toml"
    bad.write_text(
        '[desktop]\noutput = "desktop"\nareas = ["desktop"]\npr = ["ubuntu"]\n'
        '[[desktop.full]]\ndistro = "ubuntu"\n'
    )
    status, lines, err = run_areas(
        FakeRunner(stdout="docs/x.md\0"), capsys, paths=(ROOT, AREAS_TOML, bad)
    )
    assert status == 0
    assert (lines["full"], lines["tier"]) == ("true", "full")
    assert json.loads(lines["areas"]) == ALL_AREAS
    assert lines["desktop_any"] == "true"
    assert json.loads(lines["desktop_matrix"]) == {"include": [{"distro": "ubuntu"}]}
    assert "a `pr` row must be a table" in err


def test_the_fallback_prints_only_job_keys_it_can_stand_behind(tmp_path, capsys) -> None:
    odd = tmp_path / "matrices.toml"
    odd.write_text(
        '[tools]\noutput = 3\nfull = [{ package = "x" }]\n'
        '[empty]\nfull = []\n[strings]\nfull = ["x"]\n[missing]\nareas = []\n'
    )
    _, lines, _ = run_areas(FakeRunner(), capsys, paths=(ROOT, AREAS_TOML, odd))
    assert lines["tools_any"] == "true" and json.loads(lines["tools_matrix"]) == {
        "include": [{"package": "x"}]
    }
    assert not [key for key in lines if key.startswith(("empty", "strings", "missing"))]


def test_an_unreadable_matrices_file_prints_no_job_keys(tmp_path, capsys) -> None:
    garbled = tmp_path / "garbled.toml"
    garbled.write_text("= = =")
    _, lines, _ = run_areas(FakeRunner(), capsys, paths=(ROOT, AREAS_TOML, garbled))
    assert list(lines) == ["areas", "full", "tier"]


def edges_of(install: str) -> dict[str, set[str]]:
    return tools_job({"a": install, "b": "pip install pytest"}).dependencies("tools")


@pytest.mark.parametrize(
    "install",
    [
        "pip install -e ../b",
        "pip install --editable ../b",
        "pip install --editable=../b",
        "pip install -e../b",
        "pip install ../b",
        'pip install "../b[dev]"',
        "pip install -r ../b/requirements.txt",
        "pip install --requirement ../b/requirements.txt",
        "pip install --requirement=../b/requirements.txt",
        "pip install -r../b/requirements.txt",
        "cd ../b && pip install .",
    ],
)
def test_every_install_form_that_reaches_another_row_is_an_edge(install: str) -> None:
    assert edges_of(install) == {"a": {"b"}, "b": set()}


@pytest.mark.parametrize(
    "install",
    [
        "pip install ../nowhere",
        "pip install -r ../nowhere/requirements.txt",
        "pip install --editable=../nowhere",
        "pip install -e../nowhere",
        "pip install https://example.com/x.whl",
        "pip install git+https://example.com/x.git",
        "pip install --index-url https://example.com/simple pytest",
        "pip install -r",
        "pip install -r../",
        "pip install -e $GITHUB_WORKSPACE/d/b",
        'pip install -e "${ROOT}/d/b"',
        "pip install -e ~/d/b",
        "pip install -e `pwd`/../b",
        3,
    ],
)
def test_a_path_like_token_that_resolves_nowhere_widens(install: Any) -> None:
    ci = tools_job({"a": "pip install pytest", "b": "pip install pytest", "c": install})
    assert ci.classify(["d/a/x.py"], **PR).owners == {"d/a", "d/c"}


def test_plain_requirements_and_options_are_leaves_and_never_widen() -> None:
    install = 'pip install -q --upgrade pytest "pyyaml>=6.0" -e ".[dev]" -r requirements.txt'
    assert edges_of(install) == {"a": set(), "b": set()}
    ci = tools_job({"a": install, "b": "pip install pytest"})
    assert ci.classify(["d/b/x.py"], **PR).owners == {"d/b"}


# ------------------------------------------------------------------ fix round 3


def test_a_shell_expansion_is_never_resolved_against_the_row_directory() -> None:
    # `-e .` and `.[dev]` are the row's own package and must stay leaves.
    for install in ("pip install -e .", 'pip install -e ".[dev]"', "pip install ."):
        assert edges_of(install) == {"a": set(), "b": set()}, install
        assert tools_job({"a": install, "b": "pip install pytest"}).classify(
            ["d/b/x.py"], **PR
        ).owners == {"d/b"}


@pytest.mark.parametrize(
    "install",
    [
        "pip install --index-url https://example.com/simple pytest",
        "pip install -e git+https://example.com/x.git",
        "pip install https://example.com/x.whl",
    ],
)
def test_a_url_install_widens_without_a_self_edge(install: str) -> None:
    ci = tools_job({"a": install, "b": "pip install pytest"})
    assert ci.dependencies("tools") == {"a": set(), "b": set()}
    assert ci.classify(["d/b/x.py"], **PR).owners == {"d/a", "d/b"}


def test_an_empty_pr_list_through_the_cli_prints_the_fallback_and_exits_zero(
    tmp_path, capsys
) -> None:
    bad = tmp_path / "matrices.toml"
    bad.write_text(
        '[desktop]\noutput = "desktop"\nareas = ["desktop"]\npr = []\n'
        '[[desktop.full]]\ndistro = "ubuntu"\n'
    )
    status, lines, err = run_areas(
        FakeRunner(stdout="clients/desktop/x.c\0"), capsys, paths=(ROOT, AREAS_TOML, bad)
    )
    assert status == 0
    assert (lines["full"], lines["tier"], lines["desktop_any"]) == ("true", "full", "true")
    assert "`pr` must not be empty" in err


def test_ci_matrix_gives_a_clean_error_for_a_malformed_select_on(tmp_path, capsys) -> None:
    text = MATRICES_TOML.read_text(encoding="utf-8").replace(
        'docs = ["vibey-gh", "vibey-skills"]', 'docs = [["x"]]'
    )
    assert 'docs = [["x"]]' in text
    bad = tmp_path / "matrices.toml"
    bad.write_text(text)
    status = CiAreasCommand(runner=FakeRunner()).matrix(
        job="tools", tier="pr", paths=(ROOT, AREAS_TOML, bad)
    )
    assert status == 1
    assert "vibey-gh: ci-matrix:" in capsys.readouterr().err


CLI_DOC = Path(__file__).resolve().parents[1] / "docs" / "cli.md"


def test_the_cli_reference_pins_the_consumer_contract() -> None:
    doc = CLI_DOC.read_text(encoding="utf-8")
    assert "consumers MUST test `full` before `areas`" in doc
    assert "`areas` is empty when the areas map is unreadable" in doc
    assert "`ci-matrix` is not a gating step" in doc
    assert "continue-on-error" in doc and "behind the defaults step" in doc
