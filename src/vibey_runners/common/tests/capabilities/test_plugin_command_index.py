# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Indexing the commands a set of plugins holds, from `commands/*.md` (SP-LOOPS Phase 5, R10):
the same bounds and the same named reasons as the skill index, never a crash."""

from __future__ import annotations

import os
from pathlib import Path

from fakes import RecordingReader, symlink_loop, unsearchable

from vibey_runners.common.capabilities.command_entry import CommandEntry
from vibey_runners.common.capabilities.interfaces.plugin_command_index_interface import (
    PluginCommandIndexInterface,
)
from vibey_runners.common.capabilities.plugin_command_index import PluginCommandIndex
from vibey_runners.common.capabilities.resolver import DESCRIPTION_MAX_CHARS
from vibey_runners.common.capabilities.skill_index import (
    INSIDE_GIT,
    MAX_SKILLS_PER_PLUGIN,
    OUTSIDE,
    SKILL_MAX_BYTES,
)

SHIPPED_GH = Path(__file__).resolve().parents[4] / "vibey_tools" / "gh" / "plugins"


def _plugin(root: Path, name: str, **commands: str) -> Path:
    plugin = root / name
    (plugin / "commands").mkdir(parents=True, exist_ok=True)
    for stem, text in commands.items():
        (plugin / "commands" / f"{stem.replace('_', '-')}.md").write_text(text, encoding="utf-8")
    return plugin


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))


def test_the_index_satisfies_its_interface() -> None:
    assert isinstance(PluginCommandIndex(), PluginCommandIndexInterface)


def test_commands_are_indexed_from_commands_md_with_a_description(tmp_path: Path) -> None:
    alpha = _plugin(
        tmp_path,
        "alpha",
        verify="---\ndescription: Run the verification contract\n---\nRead CONTRIBUTING.md.\n",
        refresh_docs="---\ndescription: >\n  Refresh the docs\n  in place\n---\nBody.\n",
    )
    beta = _plugin(tmp_path, "beta", ship="---\ndescription: Ship it\n---\n")
    (alpha / "commands" / "notes.txt").write_text("not a command", encoding="utf-8")
    (alpha / "commands" / "nested").mkdir()
    (alpha / "commands" / "folder.md").mkdir()
    (alpha / "commands" / "dangling.md").symlink_to(tmp_path / "nowhere.md")
    (alpha / "commands" / "nested" / "deep.md").write_text("---\ndescription: x\n---\n")
    commands, skipped = PluginCommandIndex().build([alpha, beta])
    assert commands == (
        CommandEntry(
            "alpha",
            "refresh-docs",
            "Refresh the docs in place",
            _real(alpha / "commands" / "refresh-docs.md"),
        ),
        CommandEntry(
            "alpha",
            "verify",
            "Run the verification contract",
            _real(alpha / "commands" / "verify.md"),
        ),
        CommandEntry("beta", "ship", "Ship it", _real(beta / "commands" / "ship.md")),
    )
    assert skipped == ()


def test_the_family_commands_are_indexed() -> None:
    plugins = sorted(path for path in SHIPPED_GH.iterdir() if (path / "commands").is_dir())
    commands, skipped = PluginCommandIndex().build(plugins)
    assert skipped == ()
    assert {f"{entry.plugin}:{entry.name}" for entry in commands} == {
        "vibey-gh-development:verify",
        "vibey-gh-documentation:refresh-docs",
        "vibey-gh-pr-automation:evaluate-pr",
    }
    assert all(entry.description for entry in commands)


def test_a_command_without_frontmatter_takes_its_first_line(tmp_path: Path) -> None:
    plugin = _plugin(
        tmp_path,
        "alpha",
        plain="\n\n   Lint\tthe‮ tree.  \nSecond line.\n",
        nodesc="---\nname: nodesc\n---\n\n\nFirst body line.\nMore.\n",
        long="x" * (DESCRIPTION_MAX_CHARS * 2) + "\n",
    )
    commands, skipped = PluginCommandIndex().build([plugin])
    described = {entry.name: entry.description for entry in commands}
    assert described["plain"] == "Lint the tree."
    assert described["nodesc"] == "First body line."
    assert len(described["long"]) == DESCRIPTION_MAX_CHARS
    assert described["long"].endswith("...")
    assert skipped == ()


def test_a_command_with_no_text_or_a_bad_frontmatter_is_skipped_and_named(
    tmp_path: Path,
) -> None:
    plugin = _plugin(
        tmp_path,
        "alpha",
        empty="  \n\n",
        bare="---\nname: bare\n---\n\n",
        broken="---\ndescription: never closed\n",
    )
    (plugin / "commands" / "bad name.md").write_text("Body.\n", encoding="utf-8")
    commands, skipped = PluginCommandIndex().build([plugin])
    assert commands == ()
    folder = _real(plugin / "commands")
    assert dict(skipped) == {
        folder / "bad name.md": "the command name 'bad name' is not a plain name",
        folder / "bare.md": "has no description",
        folder / "broken.md": "frontmatter is not closed (no second --- line)",
        folder / "empty.md": "has no description",
    }


def test_a_command_that_escapes_its_plugin_or_sits_in_git_is_skipped_and_named(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("---\ndescription: SECRET-OUTSIDE\n---\n", encoding="utf-8")
    plugin = _plugin(tmp_path, "alpha", fine="Fine.\n")
    (plugin / "commands" / "escape.md").symlink_to(outside)
    (plugin / ".git").mkdir()
    (plugin / ".git" / "hidden.md").write_text("---\ndescription: HIDDEN\n---\n")
    (plugin / "commands" / "ingit.md").symlink_to(plugin / ".git" / "hidden.md")
    reader = RecordingReader()
    commands, skipped = PluginCommandIndex(reader=reader).build([plugin])
    assert [entry.name for entry in commands] == ["fine"]
    assert dict(skipped) == {
        _real(plugin / "commands") / "escape.md": OUTSIDE,
        _real(plugin / "commands") / "ingit.md": INSIDE_GIT,
    }
    assert reader.paths == [_real(plugin / "commands" / "fine.md")]


def test_a_commands_folder_outside_the_plugin_or_in_git_is_skipped(tmp_path: Path) -> None:
    elsewhere = _plugin(tmp_path / "other", "x", stolen="Stolen.\n")
    away = tmp_path / "away"
    away.mkdir()
    (away / "commands").symlink_to(elsewhere / "commands")
    ingit = tmp_path / "ingit"
    (ingit / ".git" / "commands").mkdir(parents=True)
    (ingit / ".git" / "commands" / "c.md").write_text("C.\n", encoding="utf-8")
    (ingit / "commands").symlink_to(ingit / ".git" / "commands")
    commands, skipped = PluginCommandIndex().build([away, ingit])
    assert commands == ()
    assert skipped == ((away / "commands", OUTSIDE), (ingit / "commands", INSIDE_GIT))


def test_a_plugin_without_commands_or_without_a_folder(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    not_a_folder = tmp_path / "file-plugin"
    (not_a_folder / "commands").parent.mkdir()
    (not_a_folder / "commands").write_text("a file, not a folder", encoding="utf-8")
    commands, skipped = PluginCommandIndex().build([empty, tmp_path / "absent", not_a_folder])
    assert commands == ()
    assert skipped == ((tmp_path / "absent", "the plugin folder does not exist"),)


def test_an_oversized_or_non_utf8_or_unreadable_command_is_skipped(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path, "alpha", fine="Fine.\n")
    folder = _real(plugin / "commands")
    (folder / "big.md").write_bytes(b"x" * (SKILL_MAX_BYTES + 1))
    (folder / "latin.md").write_bytes(b"caf\xe9\n")
    (folder / "locked.md").write_text("Locked.\n", encoding="utf-8")
    reader = RecordingReader(fail={folder / "locked.md": PermissionError(13, "Permission denied")})
    commands, skipped = PluginCommandIndex(reader=reader).build([plugin])
    assert [entry.name for entry in commands] == ["fine"]
    assert dict(skipped) == {
        folder / "big.md": f"is larger than {SKILL_MAX_BYTES} bytes",
        folder / "latin.md": "is not UTF-8",
        folder / "locked.md": "cannot be read: [Errno 13] Permission denied",
    }


def test_at_most_the_per_plugin_limit_is_read(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path, "alpha")
    for number in range(MAX_SKILLS_PER_PLUGIN + 2):
        (plugin / "commands" / f"c{number:04d}.md").write_text("C.\n", encoding="utf-8")
    commands, skipped = PluginCommandIndex().build([plugin])
    assert len(commands) == MAX_SKILLS_PER_PLUGIN
    assert skipped == (
        (
            _real(plugin / "commands"),
            f"2 more command files past the {MAX_SKILLS_PER_PLUGIN}-file limit of one plugin",
        ),
    )


def test_a_folder_that_cannot_be_looked_in_is_named(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path, "alpha", fine="Fine.\n")
    loop = symlink_loop(plugin / "commands" / "loop.md")
    commands, skipped = PluginCommandIndex().build([plugin])
    assert [entry.name for entry in commands] == ["fine"]
    assert [path for path, _ in skipped] == [loop]
    assert skipped[0][1].startswith("cannot be read: ")
    beta = _plugin(tmp_path, "beta", fine="Fine.\n")
    with unsearchable(beta / "commands"):
        commands, skipped = PluginCommandIndex().build([beta])
    assert commands == ()
    assert len(skipped) == 1
    assert skipped[0][1].startswith("cannot be read: ")


def test_a_command_that_disappears_between_listing_and_reading_is_named(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path, "alpha", gone="Gone.\n")

    class _VanishingProbe:
        """Lists the file, then says it is no longer a file when asked."""

        def real(self, path: Path) -> Path:
            return _real(path)

        def is_dir(self, path: Path) -> bool:
            return path.is_dir()

        def is_file(self, path: Path) -> bool:
            return False

    commands, skipped = PluginCommandIndex(probe=_VanishingProbe()).build([plugin])
    assert commands == ()
    assert skipped == ((_real(plugin / "commands" / "gone.md"), "is not a regular file"),)


def test_a_plugin_folder_that_cannot_be_looked_at_is_named(tmp_path: Path) -> None:
    plugin = _plugin(tmp_path, "alpha", fine="Fine.\n")
    with unsearchable(tmp_path):
        commands, skipped = PluginCommandIndex().build([plugin])
    assert commands == ()
    assert len(skipped) == 1
    assert skipped[0][0] == plugin
    assert skipped[0][1].startswith("cannot be read: ")
