# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading a marketplace's `.claude-plugin/marketplace.json`: every plugin folder stays inside
the marketplace, or nothing is read (SP-LOOPS Task 4, Review Focus 1 and 2)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from fakes import RecordingReader, symlink_loop, unsearchable

from vibey_runners.common.capabilities.git_folder_guard import GitFolderGuard
from vibey_runners.common.capabilities.interfaces.manifest_interface import (
    MarketplaceManifestInterface,
)
from vibey_runners.common.capabilities.manifest import (
    MANIFEST_MAX_BYTES,
    MAX_PLUGINS,
    MISSING_FOLDER,
    MarketplaceManifest,
)
from vibey_runners.common.capabilities.manifest_error import ManifestError

SHIPPED = Path(__file__).resolve().parents[4] / "vibey_tools" / "skills"


def _marketplace(root: Path, plugins: Any, *, make: tuple[str, ...] = ()) -> Path:
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "acme", "plugins": plugins}), encoding="utf-8"
    )
    for folder in make:
        (root / folder).mkdir(parents=True, exist_ok=True)
    return root


def _read(root: Path, reader: RecordingReader) -> Any:
    return MarketplaceManifest(reader).read(root)


def _refused(root: Path, reader: RecordingReader) -> ManifestError:
    with pytest.raises(ManifestError) as caught:
        _read(root, reader)
    return caught.value


def test_a_valid_manifest_lists_each_plugin_folder(tmp_path: Path, reader: RecordingReader) -> None:
    root = _marketplace(
        tmp_path / "acme",
        [
            {"name": "linting", "source": "./plugins/linting", "description": "Lints."},
            {"name": "whole", "source": "./"},
        ],
        make=("plugins/linting",),
    )
    catalog = _read(root, reader)
    assert sorted(catalog.plugins) == ["linting", "whole"]
    linting = catalog.plugins["linting"]
    assert linting.name == "linting"
    assert linting.directory == (root / "plugins" / "linting").resolve()
    assert linting.description == "Lints."
    assert catalog.plugins["whole"].directory == root.resolve()
    assert catalog.plugins["whole"].description == ""
    assert catalog.skipped == ()
    assert reader.paths == [(root / ".claude-plugin" / "marketplace.json").resolve()]
    assert isinstance(MarketplaceManifest(), MarketplaceManifestInterface)


@pytest.mark.parametrize("source", ["../outside", "./plugins/../../outside", "plugins/../.."])
def test_a_source_climbing_out_is_refused_and_never_read(
    tmp_path: Path, reader: RecordingReader, source: str
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("secret", encoding="utf-8")
    root = _marketplace(tmp_path / "acme", [{"name": "evil", "source": source}], make=("plugins",))
    error = _refused(root, reader)
    assert "evil" in str(error)
    assert reader.paths == [(root / ".claude-plugin" / "marketplace.json").resolve()]


def test_an_absolute_source_is_refused_and_never_read(
    tmp_path: Path, reader: RecordingReader
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = _marketplace(tmp_path / "acme", [{"name": "evil", "source": str(outside)}])
    assert "absolute" in str(_refused(root, reader))
    assert reader.paths == [(root / ".claude-plugin" / "marketplace.json").resolve()]


def test_a_home_relative_source_is_refused(tmp_path: Path, reader: RecordingReader) -> None:
    root = _marketplace(tmp_path / "acme", [{"name": "evil", "source": "~/plugins"}])
    _refused(root, reader)


def test_a_source_with_control_characters_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(tmp_path / "acme", [{"name": "evil", "source": "./plug\x00ins"}])
    assert "control characters" in str(_refused(root, reader))


def test_a_manifest_that_cannot_be_opened_is_refused(tmp_path: Path) -> None:
    root = _marketplace(tmp_path / "acme", [])
    manifest = (root / ".claude-plugin" / "marketplace.json").resolve()
    failing = RecordingReader(fail={manifest: PermissionError("denied")})
    assert "cannot be read" in str(_refused(root, failing))


def test_a_plugin_folder_symlinked_out_of_the_marketplace_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = _marketplace(tmp_path / "acme", [{"name": "evil", "source": "./plugins/evil"}])
    (root / "plugins").mkdir()
    (root / "plugins" / "evil").symlink_to(outside)
    assert "outside the marketplace" in str(_refused(root, reader))


def test_a_plugin_folder_symlinked_inside_the_marketplace_is_read(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(
        tmp_path / "acme", [{"name": "alias", "source": "./plugins/alias"}], make=("real",)
    )
    (root / "plugins").mkdir()
    (root / "plugins" / "alias").symlink_to(root / "real")
    assert _read(root, reader).plugins["alias"].directory == (root / "real").resolve()


def test_a_manifest_folder_symlinked_out_of_the_marketplace_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    elsewhere = _marketplace(tmp_path / "elsewhere", [])
    root = tmp_path / "acme"
    root.mkdir()
    (root / ".claude-plugin").symlink_to(elsewhere / ".claude-plugin")
    assert "outside the marketplace" in str(_refused(root, reader))
    assert reader.paths == []


def test_a_remote_plugin_source_is_skipped_with_a_reason(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(
        tmp_path / "acme",
        [{"name": "remote", "source": {"source": "github", "repo": "acme/x"}}],
    )
    catalog = _read(root, reader)
    assert catalog.plugins == {}
    assert catalog.skipped == (("remote", "its source is not a folder in the marketplace"),)


def test_a_missing_plugin_folder_is_skipped_with_a_reason(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(tmp_path / "acme", [{"name": "gone", "source": "./plugins/gone"}])
    assert _read(root, reader).skipped == (("gone", "its folder does not exist"),)


def test_a_manifest_over_the_cap_is_refused(tmp_path: Path, reader: RecordingReader) -> None:
    root = _marketplace(tmp_path / "acme", [])
    padding = " " * MANIFEST_MAX_BYTES
    (root / ".claude-plugin" / "marketplace.json").write_text(
        '{"plugins": []}' + padding, encoding="utf-8"
    )
    assert "bytes" in str(_refused(root, reader))


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("{not json", "is not JSON"),
        ("[]", "must be a JSON object"),
        ('{"name": "x"}', "plugins must be a list"),
        ('{"plugins": ["x"]}', "plugins[0] must be an object"),
        ('{"plugins": [{"name": "../x", "source": "./"}]}', "plugins[0].name"),
        ('{"plugins": [{"source": "./"}]}', "plugins[0].name"),
        (
            '{"plugins": [{"name": "a", "source": "./"}, {"name": "a", "source": "./"}]}',
            "plugins[1].name",
        ),
        (
            '{"plugins": [{"name": "a", "source": "./", "description": 3}]}',
            "plugins[0].description",
        ),
    ],
)
def test_a_malformed_manifest_is_refused_naming_what(
    tmp_path: Path, reader: RecordingReader, text: str, reason: str
) -> None:
    root = _marketplace(tmp_path / "acme", [])
    (root / ".claude-plugin" / "marketplace.json").write_text(text, encoding="utf-8")
    assert reason in str(_refused(root, reader))


def test_too_many_plugins_are_refused(tmp_path: Path, reader: RecordingReader) -> None:
    plugins = [{"name": f"p{i}", "source": "./"} for i in range(MAX_PLUGINS + 1)]
    root = _marketplace(tmp_path / "acme", plugins)
    assert f"at most {MAX_PLUGINS}" in str(_refused(root, reader))


def test_a_manifest_that_is_not_utf8_is_refused(tmp_path: Path, reader: RecordingReader) -> None:
    root = _marketplace(tmp_path / "acme", [])
    (root / ".claude-plugin" / "marketplace.json").write_bytes(b'{"plugins": ["\xff"]}')
    assert "UTF-8" in str(_refused(root, reader))


def test_a_marketplace_without_a_manifest_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = tmp_path / "acme"
    root.mkdir()
    assert "marketplace.json" in str(_refused(root, reader))


def test_a_missing_marketplace_root_is_refused(tmp_path: Path, reader: RecordingReader) -> None:
    assert "does not exist" in str(_refused(tmp_path / "absent", reader))


def test_the_marketplace_that_ships_with_vibey_reads_with_the_research_plugin() -> None:
    catalog = MarketplaceManifest().read(SHIPPED)
    assert "currency-research" in catalog.plugins
    assert catalog.plugins["currency-research"].directory.is_dir()
    assert catalog.skipped == ()


def test_a_source_inside_the_root_git_folder_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(
        tmp_path / "acme", [{"name": "hidden", "source": "./.git/stash"}], make=(".git/stash",)
    )
    assert "inside the marketplace's .git" in str(_refused(root, reader))


def test_a_plugin_folder_symlinked_into_the_root_git_folder_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(
        tmp_path / "acme", [{"name": "hidden", "source": "./plugins/hidden"}], make=(".git/x",)
    )
    (root / "plugins").mkdir()
    (root / "plugins" / "hidden").symlink_to(root / ".git" / "x")
    assert "inside the marketplace's .git" in str(_refused(root, reader))


def test_a_manifest_inside_the_root_git_folder_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    stored = _marketplace(tmp_path / "acme" / ".git" / "stored", [])
    root = tmp_path / "acme"
    (root / ".claude-plugin").symlink_to(stored / ".claude-plugin")
    assert "inside the marketplace's .git" in str(_refused(root, reader))
    assert reader.paths == []


def test_a_plugin_folder_that_is_the_git_folder_by_identity_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(
        tmp_path / "acme", [{"name": "hidden", "source": "./stash"}], make=(".git", "stash")
    )
    real = root.resolve()

    def aliasing(path: Path) -> os.stat_result:  # as a case-insensitive file system would
        return os.stat(real / ".git" if path == real / "stash" else path)

    manifest = MarketplaceManifest(reader, guard=GitFolderGuard(stat=aliasing))
    with pytest.raises(ManifestError, match="inside the marketplace's .git"):
        manifest.read(root)


def test_a_source_naming_a_case_variant_of_git_is_refused(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(
        tmp_path / "acme", [{"name": "hidden", "source": "./.GIT/stash"}], make=(".GIT/stash",)
    )
    assert "inside the marketplace's .git" in str(_refused(root, reader))


# -- a folder that cannot be searched: the same answer on Python 3.12, 3.13 and 3.14 ----------


def test_a_marketplace_folder_that_cannot_be_looked_at_is_named(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(tmp_path / "outer" / "acme", [])
    with unsearchable(tmp_path / "outer"):
        error = _refused(root, reader)
    assert "the marketplace folder" in str(error) and "cannot be read" in str(error)


def test_a_manifest_folder_that_cannot_be_searched_is_named_not_missing(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(tmp_path / "acme", [])
    with unsearchable(root / ".claude-plugin"):
        error = _refused(root, reader)
    assert ".claude-plugin/marketplace.json cannot be read" in str(error)
    assert "has no" not in str(error)


def test_a_plugins_folder_that_cannot_be_searched_is_named_not_skipped(
    tmp_path: Path, reader: RecordingReader
) -> None:
    plugins = [{"name": "linting", "source": "./plugins/linting"}]
    root = _marketplace(tmp_path / "acme", plugins, make=("plugins/linting",))
    with unsearchable(root / "plugins"):
        error = _refused(root, reader)
    assert "(linting): its folder cannot be read" in str(error)


# -- a symlink loop: the same exception type and message on Python 3.12, 3.13 and 3.14 --------


def test_a_marketplace_root_that_is_a_symlink_loop_does_not_exist(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = symlink_loop(tmp_path / "acme")
    error = _refused(root, reader)
    assert type(error) is ManifestError
    assert str(error) == f"the marketplace folder {root} does not exist"


def test_a_manifest_folder_that_is_a_symlink_loop_is_no_manifest(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = tmp_path / "acme"
    root.mkdir()
    symlink_loop(root / ".claude-plugin")
    error = _refused(root, reader)
    assert type(error) is ManifestError
    assert str(error) == f"{root} has no .claude-plugin/marketplace.json"
    assert reader.paths == []


def test_a_plugin_source_that_is_a_symlink_loop_is_one_missing_folder_row(
    tmp_path: Path, reader: RecordingReader
) -> None:
    plugins = [{"name": "x", "source": "./plugins/x"}, {"name": "ok", "source": "./plugins/ok"}]
    root = _marketplace(tmp_path / "acme", plugins, make=("plugins/ok",))
    symlink_loop(root / "plugins" / "x")
    catalog = _read(root, reader)
    assert list(catalog.plugins) == ["ok"]
    assert catalog.skipped == (("x", MISSING_FOLDER),)


def test_a_deeply_nested_manifest_is_a_manifest_error(
    tmp_path: Path, reader: RecordingReader
) -> None:
    root = _marketplace(tmp_path / "acme", [])
    (root / ".claude-plugin" / "marketplace.json").write_text(
        '{"plugins": ' + "[" * 1_000_000,
        encoding="utf-8",  # deep enough on 3.14's C stack too
    )
    error = _refused(root, reader)
    assert type(error) is ManifestError
    assert "nested too deeply" in str(error)
