# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Changelog fragments: written one file per change, folded in at release, checked per PR.

Every pull request used to edit the same unreleased lines, and GitHub's mergeability never
ran the `merge=union` driver meant to absorb that, so concurrent pull requests conflicted on
every merge. These pin the three halves that replace it: the fold, the release cut, and the
pull request's check -- each against the failure that would bring the conflicts back.
"""

from __future__ import annotations

import argparse
import dataclasses
import subprocess
from datetime import date
from pathlib import Path

import pytest
import yaml

from vibey_gh import cli
from vibey_gh.changelog import NEW_CHANGELOG, Changelog
from vibey_gh.config import (
    DEFAULT_CHANGELOG_TYPES,
    ChangelogConfig,
    ChangelogFileConfig,
    GhConfig,
    load_config,
)
from vibey_gh.install import WORKFLOWS, render_workflow
from vibey_gh.interfaces.changelog_interface import (
    ChangelogFinding,
    ChangelogInterface,
    Fragment,
)

KINDS = [kind for kind, _ in DEFAULT_CHANGELOG_TYPES]
TITLES = dict(DEFAULT_CHANGELOG_TYPES)
DAY = date(2026, 10, 1)

ROOT_LOG = """# Changelog

Intro prose.

## [Unreleased]

### Bug Fixes

* **engines:** an existing fix.

## [1.0.0] (2026-09-01)

### Features

* **cli:** the first feature.
"""


def fragment(kind: str, text: str, slug: str = "x") -> Fragment:
    return Fragment(f"changelog.d/{slug}.{kind}.md", slug, kind, text)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=T", "-c", "user.email=t@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def settings(**overrides) -> ChangelogConfig:
    values = {
        "enabled": True,
        "files": (
            ChangelogFileConfig("CHANGELOG.md"),
            ChangelogFileConfig("tool/CHANGELOG.md", unreleased="Unreleased", versioned=False),
        ),
        "require_for": ("src/*",),
    }
    values.update(overrides)
    return ChangelogConfig(**values)


def write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------------- configuration


def test_the_default_is_off_with_one_changelog_beside_its_fragments():
    default = ChangelogConfig()
    assert default.enabled is False
    assert default.files == (ChangelogFileConfig("CHANGELOG.md"),)
    assert default.files[0].fragments == "changelog.d"
    assert default.skip_label == "no-changelog"
    assert list(default.titles) == KINDS
    assert default.titles["fix"] == "Bug Fixes"


def test_fragments_default_to_a_directory_beside_their_changelog():
    entry = ChangelogFileConfig("src/tool/./CHANGELOG.md")
    assert (entry.changelog, entry.fragments) == ("src/tool/CHANGELOG.md", "src/tool/changelog.d")
    assert ChangelogFileConfig("CHANGELOG.md", fragments="notes/").fragments == "notes"


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"changelog": ""}, "non-empty repository-relative path"),
        ({"changelog": 7}, "non-empty repository-relative path"),
        ({"changelog": "/etc/CHANGELOG.md"}, "repository-relative path"),
        ({"changelog": "../CHANGELOG.md"}, "repository-relative path"),
        ({"changelog": "a\\CHANGELOG.md"}, "repository-relative path"),
        ({"changelog": "CHANGELOG.md", "fragments": "."}, "not the root"),
        ({"changelog": "CHANGELOG.md", "unreleased": " "}, "non-empty heading"),
        ({"changelog": "CHANGELOG.md", "unreleased": "a\nb"}, "single line"),
        ({"changelog": "CHANGELOG.md", "unreleased": "a\rb"}, "single line"),
        ({"changelog": "CHANGELOG.md", "versioned": "yes"}, "boolean"),
    ],
)
def test_a_changelog_entry_that_could_misfile_is_refused(values, message):
    with pytest.raises(ValueError, match=message):
        ChangelogFileConfig(**values)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"enabled": "yes"}, "enabled must be a boolean"),
        ({"enabled": True, "files": ()}, "at least one changelog"),
        (
            {"files": (ChangelogFileConfig("A.md"), ChangelogFileConfig("./A.md"))},
            "files.changelog entries must be unique",
        ),
        (
            {
                "files": (
                    ChangelogFileConfig("A.md", fragments="d"),
                    ChangelogFileConfig("B.md", fragments="d"),
                )
            },
            "files.fragments entries must be unique",
        ),
        ({"types": ()}, "at least one type"),
        ({"types": (("Fix", "Fixes"),)}, "lowercase words"),
        ({"types": (("fix.it", "Fixes"),)}, "lowercase words"),
        ({"types": (("fix", " "),)}, "one-line heading"),
        ({"types": (("fix", 3),)}, "one-line heading"),
        ({"types": (("fix", "A\nB"),)}, "one-line heading"),
        ({"types": (("fix", "Fixes"), ("bug", "fixes"))}, "headings must be unique"),
        ({"require_for": ("",)}, "non-empty"),
        ({"require_for": ("/src/*",)}, "without a leading '/'"),
        ({"skip_label": 3}, "skip_label"),
        ({"skip_label": "a\nb"}, "skip_label"),
        ({"release_heading": 3}, "single line"),
        ({"release_heading": "[{version}]\n"}, "single line"),
        ({"release_heading": "({date})"}, "must contain {version}"),
        ({"release_heading": "{version} {name}"}, "must contain {version}"),
    ],
)
def test_a_changelog_table_that_could_misfile_is_refused(values, message):
    with pytest.raises(ValueError, match=message):
        ChangelogConfig(**values)


def test_an_empty_skip_label_is_allowed_and_means_nothing_skips():
    assert ChangelogConfig(skip_label="").skip_label == ""


def test_the_table_reads_types_in_order_and_files_as_an_array():
    parsed = ChangelogConfig.from_table(
        {
            "enabled": True,
            "skip_label": "skip",
            "release_heading": "v{version}",
            "require_for": ["src/*"],
            "types": {"added": "Added", "fixed": "Fixed"},
            "files": [{"changelog": "CHANGELOG.md", "fragments": "news"}],
        }
    )
    assert parsed.types == (("added", "Added"), ("fixed", "Fixed"))
    assert parsed.files == (ChangelogFileConfig("CHANGELOG.md", fragments="news"),)
    assert (parsed.skip_label, parsed.release_heading) == ("skip", "v{version}")
    assert parsed.require_for == ("src/*",)
    assert ChangelogConfig.from_table({}) == ChangelogConfig()


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"fragment_dir": "x"}, "unknown key"),
        ({"require_for": "src/*"}, "list of strings"),
        ({"require_for": [1]}, "list of strings"),
        ({"types": ["fix"]}, "table of type = heading"),
        ({"files": {"changelog": "A.md"}}, "array of tables"),
        ({"files": ["A.md"]}, "array of tables"),
        ({"files": [{"changelog": "A.md", "dir": "d"}]}, "unknown key"),
        ({"files": [{"fragments": "d"}]}, "must name a changelog"),
    ],
)
def test_a_malformed_table_is_refused_when_the_configuration_loads(table, message):
    with pytest.raises(ValueError, match=message):
        ChangelogConfig.from_table(table)


def test_the_configuration_file_declares_it(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        '[changelog]\nenabled = true\nrequire_for = ["src/*"]\n'
        '[[changelog.files]]\nchangelog = "CHANGELOG.md"\n'
        '[[changelog.files]]\nchangelog = "tool/CHANGELOG.md"\nversioned = false\n',
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.changelog.enabled is True
    assert [entry.fragments for entry in cfg.changelog.files] == [
        "changelog.d",
        "tool/changelog.d",
    ]
    assert cfg.changelog.files[1].versioned is False


def test_doctor_knows_the_table():
    from vibey_gh.doctor import _SECTION_KEYS

    assert _SECTION_KEYS["changelog"] == {f.name for f in dataclasses.fields(ChangelogConfig)}


# ------------------------------------------------------------------------- fragments


def test_the_changelog_implements_its_seam():
    assert isinstance(Changelog(), ChangelogInterface)


@pytest.mark.parametrize(
    ("name", "text", "problem"),
    [
        ("fix.md", "* x", "<slug>.<type>.md"),
        ("-a.fix.md", "* x", "<slug>.<type>.md"),
        ("a.b.fix.md", "* x", "<slug>.<type>.md"),
        ("a.fix.txt", "* x", "<slug>.<type>.md"),
        ("a.bugfix.md", "* x", "unknown type 'bugfix'"),
        ("a.fix.md", " \n", "empty"),
        ("a.fix.md", "### Bug Fixes\n\n* x", "carries a heading"),
    ],
)
def test_a_malformed_fragment_is_named(name, text, problem):
    problems = Changelog().fragment_problems(name, text, KINDS)
    assert any(problem in found for found in problems), problems


def test_a_well_formed_fragment_has_no_problem_even_with_a_hash_in_a_code_fence():
    text = "* **gh:** a change\n\n  ```sh\n  # a comment, not a heading\n  ```\n"
    assert Changelog().fragment_problems("pr-1303_x.fix.md", text, KINDS) == ()


def test_fragments_are_read_in_name_order_and_refused_together(tmp_path):
    tool = Changelog()
    assert tool.fragments(tmp_path, "changelog.d", KINDS) == ()
    write(tmp_path, "changelog.d/b.fix.md", "* b\n")
    write(tmp_path, "changelog.d/a.feature.md", "* a\n")
    write(tmp_path, "changelog.d/.gitkeep", "")
    found = tool.fragments(tmp_path, "changelog.d", KINDS)
    assert [(f.path, f.slug, f.kind) for f in found] == [
        ("changelog.d/a.feature.md", "a", "feature"),
        ("changelog.d/b.fix.md", "b", "fix"),
    ]
    write(tmp_path, "changelog.d/nested/c.fix.md", "* c\n")
    write(tmp_path, "changelog.d/d.oops.md", "* d\n")
    with pytest.raises(ValueError) as caught:
        tool.fragments(tmp_path, "changelog.d", KINDS)
    assert "changelog.d/nested: fragments are files directly in changelog.d/" in str(caught.value)
    assert "changelog.d/d.oops.md: unknown type 'oops'" in str(caught.value)


# ------------------------------------------------------------------------- the fold


def test_a_fragment_joins_its_existing_heading_without_a_second_one():
    folded = Changelog().fold(
        ROOT_LOG, "[Unreleased]", [fragment("fix", "* **gh:** a new fix.\n  continued.\n")], TITLES
    )
    assert folded.count("### Bug Fixes") == 1
    assert "* **engines:** an existing fix.\n* **gh:** a new fix.\n  continued.\n\n## [1.0.0]" in (
        folded
    )
    # Nothing outside the unreleased section moves.
    assert folded.startswith("# Changelog\n\nIntro prose.\n\n## [Unreleased]\n\n")
    assert folded.endswith("### Features\n\n* **cli:** the first feature.\n")


def test_new_headings_take_their_configured_place():
    folded = Changelog().fold(
        ROOT_LOG,
        "[Unreleased]",
        [
            fragment("docs", "* the docs.", "d"),
            fragment("feature", "* the feature.", "f"),
            fragment("breaking", "* the break.", "b"),
        ],
        TITLES,
    )
    section = folded.split("## [Unreleased]\n")[1].split("## [1.0.0]")[0]
    order = [line for line in section.splitlines() if line.startswith("### ")]
    assert order == [
        "### BREAKING CHANGES",
        "### Features",
        "### Bug Fixes",
        "### Documentation",
    ]


def test_an_unknown_existing_heading_keeps_its_place():
    text = "## [Unreleased]\n\n### Added\n\n* old.\n\n### Documentation\n\n* doc.\n"
    folded = Changelog().fold(text, "[Unreleased]", [fragment("fix", "* fix.")], TITLES)
    assert [line for line in folded.splitlines() if line.startswith("###")] == [
        "### Added",
        "### Bug Fixes",
        "### Documentation",
    ]


def test_legacy_entries_without_a_heading_stay_first():
    text = "# Changelog\n\n## Unreleased\n\n- **Fix:** old.\n\n## Historical releases\n\nSee.\n"
    folded = Changelog().fold(
        text, "unreleased", [fragment("feature", "- **Feature:** new.")], TITLES
    )
    assert folded == (
        "# Changelog\n\n## Unreleased\n\n- **Fix:** old.\n\n### Features\n\n"
        "- **Feature:** new.\n\n## Historical releases\n\nSee.\n"
    )


def test_a_missing_section_is_created_above_the_newest_version():
    text = "# Changelog\nIntro.\n## [1.0.0]\n\n* old.\n"
    folded = Changelog().fold(text, "[Unreleased]", [fragment("fix", "* new.")], TITLES)
    assert folded == (
        "# Changelog\nIntro.\n\n## [Unreleased]\n\n### Bug Fixes\n\n* new.\n\n## [1.0.0]\n\n* old.\n"
    )
    spaced = Changelog().fold(
        "# C\n\n## [1.0.0]\n", "[Unreleased]", [fragment("fix", "* n")], TITLES
    )
    assert spaced == "# C\n\n## [Unreleased]\n\n### Bug Fixes\n\n* n\n\n## [1.0.0]\n"


def test_a_changelog_with_no_versions_grows_its_section_at_the_end():
    folded = Changelog().fold(NEW_CHANGELOG, "[Unreleased]", [fragment("fix", "* n")], TITLES)
    assert folded == "# Changelog\n\n## [Unreleased]\n\n### Bug Fixes\n\n* n\n"


def test_an_empty_heading_and_a_fenced_heading_survive_the_fold():
    text = (
        "## [Unreleased]\n\n### Features\n\n### Bug Fixes\n\n* a.\n\n```\n## not a heading\n```\n"
    )
    folded = Changelog().fold(text, "[Unreleased]", [fragment("docs", "* d.")], TITLES)
    assert "### Features\n\n### Bug Fixes\n\n* a." in folded
    assert "## not a heading" in folded and folded.endswith("### Documentation\n\n* d.\n")


def test_nothing_to_fold_changes_nothing():
    assert Changelog().fold(ROOT_LOG, "[Unreleased]", [], TITLES) is ROOT_LOG


def test_an_entry_with_no_heading_is_refused_rather_than_dropped():
    with pytest.raises(ValueError, match="no heading is configured for type"):
        Changelog().fold(ROOT_LOG, "[Unreleased]", [fragment("oops", "* x")], TITLES)


def test_the_unreleased_section_reads_normalised():
    tool = Changelog()
    assert tool.unreleased_section(ROOT_LOG, "[unreleased]") == (
        "### Bug Fixes\n\n* **engines:** an existing fix."
    )
    assert tool.unreleased_section("# C\n", "[Unreleased]") is None


# ------------------------------------------------------------------------- the cut


def test_a_release_turns_the_section_into_the_versions_own():
    cut = Changelog().cut(ROOT_LOG, "[Unreleased]", "[{version}] ({date})", "1.1.0", DAY)
    assert "## [Unreleased]\n\n## [1.1.0] (2026-10-01)\n\n### Bug Fixes\n\n* **engines:**" in cut
    # A second run, on any day, cuts nothing more.
    assert (
        Changelog().cut(cut, "[Unreleased]", "[{version}] ({date})", "1.1.0", date(2027, 1, 1))
        == cut
    )


def test_a_release_with_no_section_still_records_the_version():
    cut = Changelog().cut("# C\n\n## v1 x\n", "[Unreleased]", "v{version}", "2", DAY)
    assert cut == "# C\n\n## [Unreleased]\n\n## v2\n\n## v1 x\n"


# ------------------------------------------------------------------------- the files


def configured(root: Path, **overrides) -> GhConfig:
    return GhConfig(root=root, changelog=settings(**overrides))


def test_assemble_folds_both_changelogs_and_deletes_the_fragments(tmp_path):
    write(tmp_path, "CHANGELOG.md", ROOT_LOG)
    write(tmp_path, "changelog.d/a.fix.md", "* **gh:** fixed.\n")
    write(tmp_path, "tool/changelog.d/b.feature.md", "- **Feature:** new.\n")
    write(tmp_path, "tool/changelog.d/.keep", "")
    cfg = configured(tmp_path)
    touched = Changelog().assemble(cfg)
    assert touched == (
        "CHANGELOG.md",
        "changelog.d/a.fix.md",
        "tool/CHANGELOG.md",
        "tool/changelog.d/b.feature.md",
    )
    assert "* **gh:** fixed." in (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    # A changelog that did not exist starts as one.
    assert (tmp_path / "tool/CHANGELOG.md").read_text(encoding="utf-8") == (
        "# Changelog\n\n## Unreleased\n\n### Features\n\n- **Feature:** new.\n"
    )
    assert not (tmp_path / "changelog.d").exists()
    assert (tmp_path / "tool/changelog.d/.keep").exists()
    # Idempotent: nothing left to fold, nothing written.
    before = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert Changelog().assemble(cfg) == ()
    assert (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") == before


def test_one_malformed_fragment_folds_nothing_anywhere(tmp_path):
    write(tmp_path, "CHANGELOG.md", ROOT_LOG)
    write(tmp_path, "changelog.d/a.fix.md", "* fine.\n")
    write(tmp_path, "tool/changelog.d/b.nope.md", "* bad.\n")
    with pytest.raises(ValueError, match="unknown type 'nope'"):
        Changelog().assemble(configured(tmp_path))
    assert (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") == ROOT_LOG
    assert (tmp_path / "changelog.d/a.fix.md").exists()


def test_a_disabled_table_touches_nothing(tmp_path):
    write(tmp_path, "changelog.d/a.fix.md", "* x\n")
    cfg = GhConfig(root=tmp_path)
    assert Changelog().assemble(cfg) == ()
    assert Changelog().release(cfg, "1.0.0", DAY) == ()
    assert (tmp_path / "changelog.d/a.fix.md").exists()


def test_release_folds_then_cuts_only_the_versioned_changelogs(tmp_path):
    write(tmp_path, "CHANGELOG.md", ROOT_LOG)
    write(tmp_path, "tool/CHANGELOG.md", "# T\n\n## Unreleased\n\n- old.\n")
    write(tmp_path, "changelog.d/a.feature.md", "* **gh:** new.\n")
    cfg = configured(tmp_path)
    touched = Changelog().release(cfg, "1.1.0", DAY)
    assert touched == ("CHANGELOG.md", "changelog.d/a.feature.md")
    text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert text.index("## [Unreleased]") < text.index("## [1.1.0] (2026-10-01)")
    assert text.index("## [1.1.0] (2026-10-01)") < text.index("* **gh:** new.")
    assert (tmp_path / "tool/CHANGELOG.md").read_text(encoding="utf-8") == (
        "# T\n\n## Unreleased\n\n- old.\n"
    )
    # Released already: a second run writes nothing.
    assert Changelog().release(cfg, "1.1.0", DAY) == ()


def test_release_skips_a_versioned_changelog_that_does_not_exist(tmp_path):
    cfg = configured(tmp_path, files=(ChangelogFileConfig("CHANGELOG.md"),))
    assert Changelog().release(cfg, "1.0.0", DAY) == ()
    assert not (tmp_path / "CHANGELOG.md").exists()


# ------------------------------------------------------------------------- the check


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "develop")
    write(tmp_path, "CHANGELOG.md", ROOT_LOG)
    write(tmp_path, "tool/CHANGELOG.md", "# T\n\n## Unreleased\n\n- old.\n")
    write(tmp_path, "src/a.py", "a = 1\n")
    write(tmp_path, "docs/a.md", "a\n")
    write(tmp_path, "changelog.d/old.fix.md", "* old.\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "base")
    git(tmp_path, "tag", "base")
    return tmp_path


def change(root: Path, files: dict[str, str | None]) -> str:
    for path, text in files.items():
        if text is None:
            (root / path).unlink()
        else:
            write(root, path, text)
    git(root, "add", "-A")
    git(root, "commit", "-qm", "change")
    return git(root, "rev-parse", "HEAD")


def findings(root: Path, labels=(), **overrides) -> list[tuple[str, str]]:
    found = Changelog().check(configured(root, **overrides), "base", "HEAD", list(labels))
    return [(f.where, f.problem) for f in found]


def test_a_required_change_with_a_fragment_passes(repo):
    change(repo, {"src/a.py": "a = 2\n", "tool/changelog.d/pr-1.fix.md": "- **Fix:** a.\n"})
    assert findings(repo) == []


def test_a_change_outside_the_required_paths_needs_no_fragment(repo):
    change(repo, {"docs/a.md": "b\n", "changelog.d/old.fix.md": None})
    assert findings(repo) == []


def test_a_required_change_with_no_fragment_is_refused_unless_labelled(repo):
    change(
        repo, {f"src/{n}.py": "x\n" for n in "abcde"} | {"changelog.d/old.fix.md": "* edited.\n"}
    )
    found = findings(repo)
    assert len(found) == 1 and found[0][0] == "the pull request"
    assert "changes src/a.py, src/b.py, src/c.py and 2 more" in found[0][1]
    assert "changelog.d/ or tool/changelog.d/" in found[0][1]
    assert "label it 'no-changelog'" in found[0][1]
    assert findings(repo, labels=["no-changelog"]) == []
    unlabelled = findings(repo, labels=["no-changelog"], skip_label="")
    assert len(unlabelled) == 1 and "label it" not in unlabelled[0][1]


def test_a_malformed_or_misplaced_fragment_is_refused_whatever_the_label(repo):
    change(
        repo,
        {
            "changelog.d/bad.nope.md": "* x\n",
            "changelog.d/sub/a.fix.md": "* x\n",
            "changelog.d/.gitkeep": "",
            "docs/a.md": "c\n",
        },
    )
    found = findings(repo, labels=["no-changelog"])
    assert ("changelog.d/bad.nope.md", "unknown type 'nope'; one of " + ", ".join(KINDS)) in found
    assert ("changelog.d/sub/a.fix.md", "fragments are files directly in changelog.d/") in found
    assert len(found) == 2


def test_a_hand_edit_to_an_unreleased_section_is_refused(repo):
    edited = ROOT_LOG.replace("an existing fix.", "an existing fix.\n* **gh:** by hand.")
    change(repo, {"CHANGELOG.md": edited, "changelog.d/n.fix.md": "* n\n"})
    assert findings(repo) == [
        (
            "CHANGELOG.md",
            (
                "edits its `## [Unreleased]` section directly; write the entry as a fragment in "
                "changelog.d/ instead, which the release files under its heading"
            ),
        )
    ]


def test_deleting_a_changelog_is_a_hand_edit_too(repo):
    change(repo, {"tool/CHANGELOG.md": None})
    assert [where for where, _ in findings(repo)] == ["tool/CHANGELOG.md"]


def test_an_edit_elsewhere_in_a_changelog_is_not_a_section_edit(repo):
    change(repo, {"CHANGELOG.md": ROOT_LOG.replace("Intro prose.", "Better prose.")})
    assert findings(repo) == []


def test_a_release_cut_is_not_a_hand_edit(repo):
    root = repo
    cfg = configured(root)
    Changelog().release(cfg, "1.1.0", DAY)
    write(root, "src/a.py", "a = 3\n")  # the version bump's own files
    git(root, "add", "-A")
    git(root, "commit", "-qm", "chore(release): 1.1.0")
    assert findings(root) == []


def test_a_change_that_cannot_be_read_is_refused_not_passed(repo):
    found = Changelog().check(configured(repo), "no-such-ref", "HEAD", [])
    assert found[0].where == "no-such-ref...HEAD" and "could not be read" in found[0].problem

    class DiffFails(Changelog):
        def _run(self, root, *args):
            if args[0] == "diff":
                return subprocess.CompletedProcess(args, 128, "", "fatal: bad\n")
            return super()._run(root, *args)

    found = DiffFails().check(configured(repo), "base", "HEAD", [])
    assert found == (ChangelogFinding("base...HEAD", "could not be read: fatal: bad"),)


def test_the_check_reads_the_change_from_another_clone(repo, tmp_path_factory):
    elsewhere = tmp_path_factory.mktemp("trusted")
    change(repo, {"src/a.py": "a = 4\n"})
    cfg = GhConfig(root=elsewhere, changelog=settings())
    found = Changelog().check(cfg, "base", "HEAD", [], checkout=repo)
    assert [f.where for f in found] == ["the pull request"]


# ------------------------------------------------------------------------- the command


def declared(root: Path, *, enabled: bool = True) -> None:
    (root / ".vibey-gh.toml").write_text(
        f'[changelog]\nenabled = {"true" if enabled else "false"}\nrequire_for = ["src/*"]\n',
        encoding="utf-8",
    )


def test_the_command_is_wired_into_the_cli(repo, monkeypatch, capsys):
    declared(repo)
    monkeypatch.chdir(repo)
    assert cli.main(["changelog", "assemble"]) == 0
    out = capsys.readouterr().out
    assert "  CHANGELOG.md\n  changelog.d/old.fix.md\n" in out and "assembled 2 path(s)" in out
    assert cli.main(["changelog", "assemble"]) == 0
    assert "no changelog fragments to assemble" in capsys.readouterr().out
    # Committed by hand, the fold is an edit to the section, not a fragment.
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "folded by hand")
    assert cli.main(["changelog", "check", "--base", "base", "--label", "x"]) == 1
    out = capsys.readouterr().out
    assert "edits its `## [Unreleased]` section directly" in out and "::error::" in out


def test_the_check_command_reads_labels_as_json(repo, monkeypatch, capsys):
    declared(repo)
    monkeypatch.chdir(repo)
    change(repo, {"src/a.py": "a = 5\n"})
    argv = ["changelog", "check", "--base", "base", "--head", "HEAD"]
    assert cli.main([*argv, "--labels-json", '["no-changelog"]']) == 0
    assert "is in order" in capsys.readouterr().out
    assert cli.main([*argv, "--labels-json", "[]"]) == 1
    assert cli.main([*argv, "--labels-json", "{"]) == 1
    assert "is not JSON" in capsys.readouterr().out
    assert cli.main([*argv, "--labels-json", '{"a": 1}']) == 1
    assert "JSON array of label names" in capsys.readouterr().out


def test_a_disabled_table_makes_both_commands_say_so(repo, monkeypatch, capsys):
    declared(repo, enabled=False)
    monkeypatch.chdir(repo)
    assert cli.main(["changelog", "assemble"]) == 0
    assert cli.main(["changelog", "check", "--base", "base"]) == 0
    out = capsys.readouterr().out
    assert "nothing assembled" in out and "nothing checked" in out


def test_a_refused_assemble_exits_nonzero(repo, monkeypatch, capsys):
    declared(repo)
    write(repo, "changelog.d/bad.md", "* x\n")
    monkeypatch.chdir(repo)
    assert cli.main(["changelog", "assemble"]) == 1
    assert "::error::vibey-gh: nothing assembled: changelog.d/bad.md" in capsys.readouterr().out


def test_dispatch_routes_each_action():
    calls = []

    class Recording(Changelog):
        def run_assemble(self):
            calls.append("assemble")
            return 0

        def run_check(self, base, head, labels, labels_json="", checkout=None):
            calls.append((base, head, labels, labels_json, checkout))
            return 1

    parser = Changelog.declare(argparse.ArgumentParser())
    assert Recording.dispatch(parser.parse_args(["assemble"])) == 0
    args = parser.parse_args(["check", "--base", "b", "--label", "l", "--checkout", "c"])
    assert Recording.dispatch(args) == 1
    assert calls == ["assemble", ("b", "HEAD", ["l"], "", Path("c"))]


# ------------------------------------------------------------------------- the workflow


def rendered(cfg: GhConfig) -> tuple[str, dict]:
    text = render_workflow(WORKFLOWS / "changelog.yml", cfg)
    spec = yaml.safe_load(text)
    spec["on"] = spec.get("on", spec.get(True))
    return text, spec


def test_the_workflow_checks_pull_requests_into_the_integration_branch_only(tmp_path):
    cfg = GhConfig(root=tmp_path, integration_branch="trunk", changelog=settings())
    text, spec = rendered(cfg)
    assert spec["name"] == "Changelog"
    assert spec["on"]["pull_request"]["branches"] == ["trunk"]
    assert {"labeled", "unlabeled"} <= set(spec["on"]["pull_request"]["types"])
    assert "merge_group" not in spec["on"]
    assert spec["permissions"] == {"contents": "read"}
    job = spec["jobs"]["check"]
    assert job["name"] == "Changelog fragment" and job["if"] is True
    assert "vibey-gh changelog check" in text and "__VIBEY_GH_" not in text


def test_the_workflow_reads_its_rule_from_the_trusted_branch_and_labels_as_data(tmp_path):
    _, spec = rendered(GhConfig(root=tmp_path, changelog=settings()))
    steps = spec["jobs"]["check"]["steps"]
    assert steps[0]["with"]["ref"] == "${{ github.event.repository.default_branch }}"
    checkouts = [step for step in steps if "actions/checkout" in step.get("uses", "")]
    assert all(step["with"]["persist-credentials"] is False for step in checkouts)
    last = steps[-1]
    assert last["working-directory"] == "automation" and "--checkout ../target" in last["run"]
    assert last["env"]["LABELS"] == "${{ toJSON(github.event.pull_request.labels.*.name) }}"
    assert "${{" not in last["run"]


def test_a_disabled_table_renders_a_job_that_never_runs(tmp_path):
    _, spec = rendered(GhConfig(root=tmp_path))
    assert spec["jobs"]["check"]["if"] is False
