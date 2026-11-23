# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Indexing the skills a set of plugins holds, from `skills/*/SKILL.md` frontmatter: a skill
that cannot be read safely is skipped with a named reason, never a crash (SP-LOOPS Task 4,
Review Focus 2 and 5)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fakes import RecordingReader

from vibey_runners.common.capabilities.git_folder_guard import GitFolderGuard
from vibey_runners.common.capabilities.interfaces.skill_index_interface import (
    SkillIndexInterface,
)
from vibey_runners.common.capabilities.manifest import MarketplaceManifest
from vibey_runners.common.capabilities.skill_entry import SkillEntry
from vibey_runners.common.capabilities.skill_index import (
    INSIDE_GIT,
    MAX_SKILLS_PER_PLUGIN,
    OUTSIDE,
    SKILL_MAX_BYTES,
    SkillIndex,
)

SHIPPED = Path(__file__).resolve().parents[4] / "vibey_tools" / "skills"
VALID = "---\nname: {name}\ndescription: Does {name}.\n---\n\n# Body\n"


def _skill(plugin: Path, folder: str, text: str) -> Path:
    path = plugin / "skills" / folder / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _plugin(tmp_path: Path, name: str = "linting") -> Path:
    plugin = tmp_path / "market" / "plugins" / name
    plugin.mkdir(parents=True)
    return plugin


def _only_skip(plugin: Path, reader: RecordingReader | None = None) -> tuple[Path, str]:
    catalog = SkillIndex(reader).build([plugin])
    assert catalog.skills == ()
    assert len(catalog.skipped) == 1
    return catalog.skipped[0]


def test_a_valid_skill_yields_its_name_and_description(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    path = _skill(plugin, "lint", VALID.format(name="lint"))
    catalog = SkillIndex().build([plugin])
    assert catalog.skills == (SkillEntry("linting", "lint", "Does lint.", path.resolve()),)
    assert catalog.skipped == ()
    assert SKILL_MAX_BYTES == 64 * 1024
    assert isinstance(SkillIndex(), SkillIndexInterface)


def test_skills_are_listed_in_plugin_order_then_folder_order(tmp_path: Path) -> None:
    second = _plugin(tmp_path, "b-plugin")
    first = _plugin(tmp_path, "a-plugin")
    _skill(second, "zeta", VALID.format(name="zeta"))
    _skill(second, "alpha", VALID.format(name="alpha"))
    _skill(first, "only", VALID.format(name="only"))
    names = [(s.plugin, s.name) for s in SkillIndex().build([second, first]).skills]
    assert names == [("b-plugin", "alpha"), ("b-plugin", "zeta"), ("a-plugin", "only")]


def test_a_skills_folder_symlinked_out_of_the_marketplace_is_skipped(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    _skill(outside, "steal", VALID.format(name="steal"))
    plugin = _plugin(tmp_path)
    (plugin / "skills").symlink_to(outside / "skills")
    reader = RecordingReader()
    path, reason = _only_skip(plugin, reader)
    assert (path, reason) == (plugin / "skills", OUTSIDE)
    assert OUTSIDE == "outside the marketplace"
    assert reader.paths == []


def test_one_skill_folder_symlinked_out_is_skipped(tmp_path: Path) -> None:
    outside = tmp_path / "outside" / "steal"
    outside.mkdir(parents=True)
    (outside / "SKILL.md").write_text(VALID.format(name="steal"), encoding="utf-8")
    plugin = _plugin(tmp_path)
    (plugin / "skills").mkdir()
    (plugin / "skills" / "steal").symlink_to(outside)
    reader = RecordingReader()
    assert _only_skip(plugin, reader)[1] == OUTSIDE
    assert reader.paths == []


def test_a_skill_file_symlinked_out_is_skipped(tmp_path: Path) -> None:
    secret = tmp_path / "secret.md"
    secret.write_text(VALID.format(name="steal"), encoding="utf-8")
    plugin = _plugin(tmp_path)
    (plugin / "skills" / "steal").mkdir(parents=True)
    (plugin / "skills" / "steal" / "SKILL.md").symlink_to(secret)
    reader = RecordingReader()
    assert _only_skip(plugin, reader)[1] == OUTSIDE
    assert reader.paths == []


def test_an_oversized_skill_file_is_skipped_with_its_size_reason(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    path = _skill(plugin, "huge", VALID.format(name="huge") + "x" * SKILL_MAX_BYTES)
    skipped_path, reason = _only_skip(plugin)
    assert skipped_path == path.resolve()
    assert f"larger than {SKILL_MAX_BYTES} bytes" in reason


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("---\ndescription: No name.\n---\n", "no name"),
        ("---\nname: lint\n---\n", "no description"),
        ("---\nname: lint\ndescription: '   '\n---\n", "no description"),
        ("# Just a body\n", "does not start with frontmatter"),
        ("---\nname: lint\ndescription: never closed\n", "frontmatter is not closed"),
        ('---\nname: lint\ndescription: "bad \\q escape"\n---\n', "description"),
        ("---\nname: lint\ndescription: 'unterminated\n---\n", "description"),
        ("---\nname: ../../escape\ndescription: x\n---\n", "not a plain name"),
        ("---\n  indented: first\nname: lint\n---\n", "malformed frontmatter"),
        ("---\nname: lint\nthis line has no colon\n---\n", "malformed frontmatter"),
    ],
)
def test_a_malformed_frontmatter_is_skipped_with_a_reason(
    tmp_path: Path, text: str, reason: str
) -> None:
    plugin = _plugin(tmp_path)
    _skill(plugin, "lint", text)
    assert reason in _only_skip(plugin)[1]


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ('"Quoted: with a colon and \\"escapes\\"."', 'Quoted: with a colon and "escapes".'),
        ("'It''s single-quoted.'", "It's single-quoted."),
        (">\n  Folded over\n  two lines.\n", "Folded over two lines."),
        ("|\n  Kept\n  lines.\n", "Kept\nlines."),
        ("Plain text\n  continued here.", "Plain text continued here."),
        ('"Double quoted\n  over two lines."', "Double quoted over two lines."),
    ],
)
def test_the_yaml_forms_skills_use_are_read(
    tmp_path: Path, description: str, expected: str
) -> None:
    plugin = _plugin(tmp_path)
    text = f"---\nname: lint\nlicense: MIT\ndescription: {description}\n---\nbody\n"
    _skill(plugin, "lint", text)
    assert SkillIndex().build([plugin]).skills[0].description == expected


def test_blank_and_comment_lines_and_paragraphs_are_read(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    text = (
        "---\n\n# a comment\nname: lint\ndescription: >\n  First paragraph\n  goes on.\n\n"
        "  Second.\n---\n"
    )
    _skill(plugin, "lint", text)
    assert SkillIndex().build([plugin]).skills[0].description == (
        "First paragraph goes on.\nSecond."
    )


def test_crlf_line_endings_are_read(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    _skill(plugin, "lint", "---\r\nname: lint\r\ndescription: Windows.\r\n---\r\n")
    assert SkillIndex().build([plugin]).skills[0].description == "Windows."


def test_a_skill_file_that_is_not_utf8_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    path = plugin / "skills" / "lint" / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"---\nname: lint\ndescription: \xff\n---\n")
    assert "not UTF-8" in _only_skip(plugin)[1]


def test_a_skill_file_that_cannot_be_read_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    path = _skill(plugin, "lint", VALID.format(name="lint")).resolve()
    reader = RecordingReader(fail={path: PermissionError("denied")})
    assert "cannot be read" in _only_skip(plugin, reader)[1]


def test_a_skill_folder_without_a_skill_file_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    (plugin / "skills" / "empty").mkdir(parents=True)
    assert _only_skip(plugin)[1] == "has no SKILL.md"


def test_a_duplicate_skill_name_in_one_plugin_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    _skill(plugin, "a", VALID.format(name="same"))
    _skill(plugin, "b", VALID.format(name="same"))
    catalog = SkillIndex().build([plugin])
    assert [s.name for s in catalog.skills] == ["same"]
    assert catalog.skipped[0][1] == "names the skill same twice in linting"


def test_a_plugin_without_skills_and_stray_files_are_quietly_nothing(tmp_path: Path) -> None:
    bare = _plugin(tmp_path, "bare")
    plugin = _plugin(tmp_path)
    (plugin / "skills").mkdir()
    (plugin / "skills" / "README.md").write_text("not a skill", encoding="utf-8")
    catalog = SkillIndex().build([bare, plugin])
    assert catalog.skills == ()
    assert catalog.skipped == ()


def test_a_missing_plugin_folder_is_skipped(tmp_path: Path) -> None:
    gone = tmp_path / "gone"
    assert SkillIndex().build([gone]).skipped == ((gone, "the plugin folder does not exist"),)


def test_entries_past_the_limit_are_one_skipped_row_and_never_read(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    for index in range(MAX_SKILLS_PER_PLUGIN + 5):
        _skill(plugin, f"s{index:04d}", VALID.format(name=f"s{index:04d}"))
    reader = RecordingReader()
    catalog = SkillIndex(reader).build([plugin])
    assert len(catalog.skills) == MAX_SKILLS_PER_PLUGIN
    over = [(path, reason) for path, reason in catalog.skipped]
    assert over == [
        (
            (plugin / "skills").resolve(),
            f"5 more entries past the {MAX_SKILLS_PER_PLUGIN}-entry limit of one plugin",
        )
    ]
    assert len(reader.paths) == MAX_SKILLS_PER_PLUGIN


def test_the_shipped_research_plugin_indexes_cleanly() -> None:
    catalog = MarketplaceManifest().read(SHIPPED)
    research = catalog.plugins["currency-research"].directory
    index = SkillIndex().build([research])
    names = {skill.name for skill in index.skills}
    assert {
        "research-search-and-source-quality",
        "research-currency-audit-method",
        "research-editing-a-reference-skill",
    } <= names
    assert index.skipped == ()


def test_a_skills_folder_symlinked_into_git_metadata_is_skipped(tmp_path: Path) -> None:
    plugin = tmp_path / "market"  # a plugin whose folder is the marketplace root
    _skill(plugin / ".git" / "stash", "hidden", VALID.format(name="hidden"))
    (plugin / "skills").symlink_to(plugin / ".git" / "stash" / "skills")
    reader = RecordingReader()
    assert _only_skip(plugin, reader) == (plugin / "skills", INSIDE_GIT)
    assert reader.paths == []


def test_a_skill_folder_symlinked_into_git_metadata_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    hidden = plugin / ".git" / "hidden"
    hidden.mkdir(parents=True)
    (hidden / "SKILL.md").write_text(VALID.format(name="hidden"), encoding="utf-8")
    (plugin / "skills").mkdir()
    (plugin / "skills" / "hidden").symlink_to(hidden)
    reader = RecordingReader()
    assert _only_skip(plugin, reader)[1] == INSIDE_GIT
    assert reader.paths == []


def test_a_skill_file_symlinked_into_git_metadata_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    (plugin / ".git").mkdir()
    (plugin / ".git" / "SKILL.md").write_text(VALID.format(name="x"), encoding="utf-8")
    (plugin / "skills" / "x").mkdir(parents=True)
    (plugin / "skills" / "x" / "SKILL.md").symlink_to(plugin / ".git" / "SKILL.md")
    assert _only_skip(plugin)[1] == INSIDE_GIT


def test_a_skills_folder_that_is_the_git_folder_by_identity_is_skipped(tmp_path: Path) -> None:
    plugin = tmp_path / "market"  # a plugin whose folder is the marketplace root
    (plugin / ".git").mkdir(parents=True)
    _skill(plugin, "lint", VALID.format(name="lint"))
    real = plugin.resolve()

    def aliasing(path: Path) -> os.stat_result:  # as a case-insensitive file system would
        return os.stat(real / ".git" if path == real / "skills" else path)

    catalog = SkillIndex(guard=GitFolderGuard(stat=aliasing)).build([plugin])
    assert catalog.skills == ()
    assert catalog.skipped == ((plugin / "skills", INSIDE_GIT),)


def test_a_skill_folder_named_a_case_variant_of_git_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path)
    hidden = plugin / ".Git" / "hidden"
    hidden.mkdir(parents=True)
    (hidden / "SKILL.md").write_text(VALID.format(name="hidden"), encoding="utf-8")
    (plugin / "skills").mkdir()
    (plugin / "skills" / "hidden").symlink_to(hidden)
    assert _only_skip(plugin)[1] == INSIDE_GIT
