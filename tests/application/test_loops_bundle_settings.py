# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[loops]`: the person's own `vibey.toml` is the bundle; a project's may only disable
(SP-LOOPS Task 3, ADR-0101's trust rule)."""

from pathlib import Path

import pytest
from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.plugin_spec import PluginSpec

from vibey.application.interfaces.loops_bundle_settings_interface import (
    LoopsBundleSettingsInterface,
)
from vibey.application.loops_bundle_settings import LoopsBundleSettings
from vibey.domain.config import ConfigError

USER = """
[project]
name = "mine"

[loops]
plugins = ["currency-research@vibey", "linting@acme"]
skills = ["research-search-and-source-quality"]

[[loops.marketplaces]]
name = "acme"
source = "https://example.test/acme.git"
ref = "v1.2.0"

[[loops.mcp_servers]]
name = "files"
trust = "local"
command = ["fake-mcp", "--stdio"]
"""


def _write(folder: Path, name: str, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def user(tmp_path: Path) -> Path:
    return _write(tmp_path / "config", "vibey.toml", USER)


def _load(user: Path, project: Path | None) -> tuple[BundleSpec, tuple[str, ...]]:
    loaded = LoopsBundleSettings().load(user, project)
    return loaded.bundle, loaded.notices


def test_the_persons_own_table_is_the_bundle(user: Path) -> None:
    bundle, notices = _load(user, None)
    assert bundle.marketplaces == (
        MarketplaceSpec("acme", "https://example.test/acme.git", "v1.2.0"),
    )
    assert bundle.plugins == (
        PluginSpec("currency-research", "vibey"),
        PluginSpec("linting", "acme"),
    )
    assert [server.name for server in bundle.mcp_servers] == ["files"]
    assert notices == ()
    assert isinstance(LoopsBundleSettings(), LoopsBundleSettingsInterface)


def test_no_file_is_the_default_bundle(tmp_path: Path) -> None:
    bundle, notices = _load(tmp_path / "absent.toml", None)
    assert bundle == BundleSpec.default()
    assert notices == ()


def test_a_file_without_a_loops_table_is_the_default_bundle(tmp_path: Path) -> None:
    mine = _write(tmp_path, "vibey.toml", '[project]\nname = "x"\n')
    assert _load(mine, None)[0] == BundleSpec.default()


def test_a_project_table_adding_a_marketplace_is_ignored_with_a_notice(
    user: Path, tmp_path: Path
) -> None:
    project = _write(
        tmp_path / "repo",
        "vibey.toml",
        '[[loops.marketplaces]]\nname = "evil"\nsource = "https://evil.test/x.git"\n'
        '[[loops.mcp_servers]]\nname = "x"\ntrust = "remote"\nurl = "https://evil.test/"\n',
    )
    bundle, notices = _load(user, project)
    assert bundle == _load(user, None)[0]
    assert len(notices) == 2
    assert "[loops] marketplaces is ignored" in notices[0]
    assert "[loops] mcp_servers is ignored" in notices[1]
    assert str(project) in notices[0]


def test_a_project_disable_list_narrows_the_bundle(user: Path, tmp_path: Path) -> None:
    project = _write(tmp_path / "repo", "vibey.toml", '[loops]\ndisable = ["currency-research"]\n')
    bundle, notices = _load(user, project)
    assert bundle.plugins == (PluginSpec("linting", "acme"),)
    assert "currency-research" in bundle.disabled
    assert notices == ()


def test_a_project_may_disable_and_still_not_add(user: Path, tmp_path: Path) -> None:
    project = _write(
        tmp_path / "repo",
        "vibey.toml",
        '[loops]\ndisable = ["files"]\nplugins = ["more@vibey"]\n',
    )
    bundle, notices = _load(user, project)
    assert bundle.mcp_servers == ()
    assert bundle.plugins == _load(user, None)[0].plugins
    assert len(notices) == 1 and "[loops] plugins is ignored" in notices[0]


def test_a_missing_project_file_changes_nothing(user: Path, tmp_path: Path) -> None:
    assert _load(user, tmp_path / "repo" / "vibey.toml") == _load(user, None)


def test_a_project_file_without_a_loops_table_changes_nothing(user: Path, tmp_path: Path) -> None:
    project = _write(tmp_path / "repo", "vibey.toml", '[project]\nname = "repo"\n')
    assert _load(user, project) == _load(user, None)


def test_the_persons_own_file_opened_as_the_project_is_not_a_project(user: Path) -> None:
    assert _load(user, user) == _load(user, None)


def test_a_malformed_user_bundle_is_refused_naming_the_file_and_key(tmp_path: Path) -> None:
    mine = _write(tmp_path, "vibey.toml", '[[loops.mcp_servers]]\nname = "t"\ntrust = "remote"\n')
    with pytest.raises(ConfigError) as caught:
        _load(mine, None)
    assert caught.value.path == str(mine)
    assert "loops.mcp_servers[0].url" in caught.value.message


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("loops = 3\n", "[loops] must be a table"),
        ("[loops\n", "is not valid TOML"),
    ],
)
def test_an_unreadable_user_table_is_refused(tmp_path: Path, text: str, expected: str) -> None:
    mine = _write(tmp_path, "vibey.toml", text)
    with pytest.raises(ConfigError, match=expected.replace("[", r"\[")):
        _load(mine, None)


def test_a_user_file_that_is_not_utf8_is_refused(tmp_path: Path) -> None:
    mine = tmp_path / "vibey.toml"
    mine.write_bytes(b"[loops]\nskills = ['\xff']\n")
    with pytest.raises(ConfigError, match="is not valid TOML"):
        _load(mine, None)


def test_a_user_path_that_cannot_be_read_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "vibey.toml"
    folder.mkdir()
    with pytest.raises(ConfigError, match="cannot be read"):
        _load(folder, None)


@pytest.mark.parametrize("disable", ['"currency-research"', "[3]"])
def test_a_malformed_project_disable_is_refused_naming_the_project(
    user: Path, tmp_path: Path, disable: str
) -> None:
    project = _write(tmp_path / "repo", "vibey.toml", f"[loops]\ndisable = {disable}\n")
    with pytest.raises(ConfigError) as caught:
        _load(user, project)
    assert caught.value.path == str(project)
    assert "[loops] disable" in caught.value.message
