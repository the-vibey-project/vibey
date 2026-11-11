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
from vibey_gh.interfaces.ci_areas_interface import CiAreasInterface
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


def test_a_tenant_path_yields_tools_and_selects_only_its_package_row() -> None:
    decision = classify("src/vibey_tools/gh/vibey_gh/x.py")
    assert decision.areas == {"tools"}
    assert not decision.full
    assert packages(decision) == ["vibey-gh"]
    row = real().matrix("tools", decision)["include"][0]
    assert (row["python"], row.get("os")) == ("3.12", None)


@pytest.mark.parametrize(("package", "directory"), sorted(TOOLS_DIRS.items()))
def test_every_package_directory_selects_exactly_its_own_row(package: str, directory: str) -> None:
    assert packages(classify(f"{directory}/sub/x.py")) == [package]


def test_two_packages_select_two_rows() -> None:
    decision = classify("src/vibey_tools/gh/a.py", "src/vibey_runners/qwen/b.py")
    assert sorted(packages(decision)) == ["qwenloop", "vibey-gh"]


def test_an_unowned_path_under_the_tools_trees_selects_every_pr_row() -> None:
    decision = classify("src/vibey_tools/brand-new-tenant/x.py")
    assert decision.areas == {"tools"}
    assert sorted(packages(decision)) == sorted(TOOLS_DIRS)


def test_a_python_only_pr_runs_all_seven_tenant_rows() -> None:
    decision = classify("src/vibey/x.py")
    assert sorted(packages(decision)) == sorted(TOOLS_DIRS)


def test_python_plus_a_tenant_still_runs_all_seven_rows() -> None:
    decision = classify("src/vibey/x.py", "src/vibey_tools/gh/a.py")
    assert sorted(packages(decision)) == sorted(TOOLS_DIRS)


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
        assert [*full, *[row for row in pr if row not in full]] == full, job
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
    outputs = real().outputs(classify("docs/guides/x.md"))
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
        "tools_matrix",
        "postgres_matrix",
    ]
    assert outputs["areas"] == '["python"]'
    assert (outputs["full"], outputs["tier"]) == ("false", "pr")
    assert json.loads(outputs["postgres_matrix"]) == {
        "include": [{"postgres": 14}, {"postgres": 18}]
    }
    assert len(json.loads(outputs["tools_matrix"])["include"]) == 7


def test_the_implementation_honours_its_interface() -> None:
    assert isinstance(real(), CiAreasInterface)


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


def test_a_clean_docs_diff_prints_the_pr_tier_and_no_matrix_for_a_skipped_job(capsys) -> None:
    status, lines, err = run_areas(FakeRunner(stdout="docs/a.md\0docs/b/c.md\0"), capsys)
    assert status == 0
    assert lines["areas"] == '["docs"]'
    assert (lines["full"], lines["tier"]) == ("false", "pr")
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
    assert lines["areas"] == "[]"
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
    assert document["areas"] == ["docs"] and document["full"] is True and document["tier"] == "full"
    assert document["reasons"] == ["mystery.bin is in no area and not on the always-full list"]
    assert document["outputs"]["tier"] == "full"


def test_a_broken_declaration_is_loud_but_still_prints_the_full_defaults(tmp_path, capsys) -> None:
    broken = tmp_path / "areas.toml"
    broken.write_text("[areas.docs]\npaths = 'not a list'\n[full]\npaths = []\n")
    cases = [
        (tmp_path / "missing.toml", MATRICES_TOML),
        (broken, MATRICES_TOML),
    ]
    garbled = tmp_path / "garbled.toml"
    garbled.write_text("this is = = not toml")
    cases.append((AREAS_TOML, garbled))
    for areas_path, matrices_path in cases:
        status, lines, err = run_areas(
            FakeRunner(stdout="docs/x.md\0"), capsys, paths=(ROOT, areas_path, matrices_path)
        )
        assert status == 1
        assert (lines["full"], lines["tier"]) == ("true", "full")
        assert "vibey-gh: ci-areas:" in err


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
    assert lines["areas"] == '["docs"]' and lines["full"] == "true"

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
