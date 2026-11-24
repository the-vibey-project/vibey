# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[loops]`: the person's own `vibey.toml` is the bundle; a project's may only disable
(SP-LOOPS Task 3, ADR-0101's trust rule). The trust rule is pure: the tables come through the
`TrustedTableReaderInterface` port, here an in-memory fake."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from vibey_runners.common.capabilities.bundle import MAX_ENTRIES, BundleSpec
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.plugin_spec import PluginSpec

from vibey.application.interfaces.loops_bundle_settings_interface import (
    LoopsBundleSettingsInterface,
)
from vibey.application.interfaces.trusted_table_reader_interface import (
    TrustedTableReaderInterface,
)
from vibey.application.loops_bundle_settings import (
    MAX_NOTICE_KEY_CHARS,
    MAX_NOTICES,
    LoopsBundleSettings,
)
from vibey.domain.config import ConfigError

USER = Path("/home/person/.config/vibey/vibey.toml")
PROJECT = Path("/work/repo/vibey.toml")
MINE: Mapping[str, Any] = {
    "plugins": ["currency-research@vibey", "linting@acme"],
    "skills": ["research-search-and-source-quality"],
    "marketplaces": [
        {"name": "acme", "source": "https://example.test/acme.git", "ref": "v1.2.0"},
    ],
    "mcp_servers": [{"name": "files", "trust": "local", "command": ["fake-mcp", "--stdio"]}],
}


class FakeTables:
    """The port, in memory: a path maps to its `[loops]` table, or is absent."""

    def __init__(self, tables: Mapping[Path, Mapping[str, Any]], *, same: bool = False) -> None:
        self._tables = tables
        self._same = same
        self.read: list[tuple[Path, str]] = []

    def read_table(self, path: Path, table: str) -> Mapping[str, object] | None:
        self.read.append((path, table))
        return self._tables.get(path)

    def same_file(self, first: Path, second: Path) -> bool:
        return self._same or first == second


def _load(
    mine: Mapping[str, Any] | None = MINE,
    project: Mapping[str, Any] | None = None,
    *,
    project_path: Path | None = PROJECT,
    same: bool = False,
) -> tuple[BundleSpec, tuple[str, ...]]:
    tables: dict[Path, Mapping[str, Any]] = {}
    if mine is not None:
        tables[USER] = mine
    if project is not None:
        tables[PROJECT] = project
    loaded = LoopsBundleSettings(FakeTables(tables, same=same)).load(USER, project_path)
    return loaded.bundle, loaded.notices


def test_the_persons_own_table_is_the_bundle() -> None:
    bundle, notices = _load()
    assert bundle.marketplaces == (
        MarketplaceSpec("acme", "https://example.test/acme.git", "v1.2.0"),
    )
    assert bundle.plugins == (
        PluginSpec("currency-research", "vibey"),
        PluginSpec("linting", "acme"),
    )
    assert [server.name for server in bundle.mcp_servers] == ["files"]
    assert notices == ()
    assert isinstance(LoopsBundleSettings(FakeTables({})), LoopsBundleSettingsInterface)
    assert isinstance(FakeTables({}), TrustedTableReaderInterface)


def test_reading_asks_for_the_loops_table_of_each_file() -> None:
    tables = FakeTables({USER: MINE, PROJECT: {"disable": ["files"]}})
    LoopsBundleSettings(tables).load(USER, PROJECT)
    assert tables.read == [(USER, "loops"), (PROJECT, "loops")]


def test_no_file_and_no_table_are_the_default_bundle() -> None:
    assert _load(None, project_path=None) == (BundleSpec.default(), ())
    assert _load({}, project_path=None) == (BundleSpec.default(), ())


def test_a_project_table_adding_a_marketplace_is_ignored_with_a_notice() -> None:
    project = {
        "marketplaces": [{"name": "evil", "source": "https://evil.test/x.git"}],
        "mcp_servers": [{"name": "x", "trust": "remote", "url": "https://evil.test/"}],
    }
    bundle, notices = _load(project=project)
    assert bundle == _load()[0]
    assert len(notices) == 2
    assert "[loops] 'marketplaces' is ignored" in notices[0]
    assert "[loops] 'mcp_servers' is ignored" in notices[1]
    assert str(PROJECT) in notices[0] and str(USER) in notices[0]


def test_a_project_disable_list_narrows_the_bundle() -> None:
    bundle, notices = _load(project={"disable": ["currency-research"]})
    assert bundle.plugins == (PluginSpec("linting", "acme"),)
    assert "currency-research" in bundle.disabled
    assert notices == ()


def test_a_project_may_disable_and_still_not_add() -> None:
    bundle, notices = _load(project={"disable": ["files"], "plugins": ["more@vibey"]})
    assert bundle.mcp_servers == ()
    assert bundle.plugins == _load()[0].plugins
    assert len(notices) == 1 and "[loops] 'plugins' is ignored" in notices[0]


def test_a_project_cannot_widen_a_token_budget() -> None:
    """The two capability budgets (SP-LOOPS Phase 5, R8) are the person's alone: a cloned
    repository's `[loops]` is not heard on them, and the notice names each key."""
    project = {"capability_prompt_tokens": 4096, "capability_answer_tokens": 8192}
    bundle, notices = _load(project=project)
    assert (bundle.capability_prompt_tokens, bundle.capability_answer_tokens) == (3072, 3000)
    assert bundle == _load()[0]
    assert len(notices) == 2
    assert "[loops] 'capability_answer_tokens' is ignored" in notices[0]
    assert "[loops] 'capability_prompt_tokens' is ignored" in notices[1]
    mine, none = _load({**MINE, "capability_prompt_tokens": 4096}, project_path=None)
    assert (mine.capability_prompt_tokens, none) == (4096, ())


def test_an_absent_project_file_or_none_changes_nothing() -> None:
    assert _load(project=None) == _load(project_path=None)


def test_the_persons_own_file_opened_as_the_project_is_not_a_project() -> None:
    assert _load(project={"plugins": ["x@vibey"]}, same=True) == _load(project_path=None)


@pytest.mark.parametrize(
    "mine",
    [
        {"mcp_servers": [{"name": "t", "trust": "remote"}]},
        {"mcp_servers": [{"name": "t", "trust": "remote", "url": "https://[::1/x"}]},
        {"mcp_servers": [{"name": "t", "trust": "remote", "url": "https://[zz]/"}]},
    ],
)
def test_a_malformed_user_bundle_is_a_config_error_naming_the_file_and_key(
    mine: Mapping[str, Any],
) -> None:
    with pytest.raises(ConfigError) as caught:
        _load(mine, project_path=None)
    assert caught.value.path == str(USER)
    assert "loops.mcp_servers[0].url" in caught.value.message


@pytest.mark.parametrize(
    "disable",
    [
        "currency-research",
        [3],
        ["../escape"],
        ["\x1b[2J"],
        ["a", "a"],
        [f"n{i}" for i in range(MAX_ENTRIES + 1)],
    ],
)
def test_a_project_disable_gets_the_same_rule_as_the_persons_own(disable: object) -> None:
    with pytest.raises(ConfigError) as caught:
        _load(project={"disable": disable})
    assert caught.value.path == str(PROJECT)
    assert "loops.disable" in caught.value.message
    with pytest.raises(ConfigError):  # the person's own list is held to the same rule
        _load({"disable": disable}, project_path=None)


@pytest.mark.parametrize("key", ["\x1b[2Jx", "line\nbreak", "‮evil", "k" * 500])
def test_a_project_key_reaches_the_notice_escaped_and_bounded(key: str) -> None:
    _, notices = _load(project={key: 1})
    (notice,) = notices
    assert notice.isascii() and notice.isprintable()
    assert "\x1b" not in notice and "\n" not in notice
    quoted = notice.split("[loops] ", 1)[1].split(" is ignored", 1)[0]
    assert len(quoted) <= MAX_NOTICE_KEY_CHARS


def test_the_number_of_notices_is_bounded() -> None:
    project = {f"key{i:03d}": 1 for i in range(MAX_NOTICES + 5)}
    _, notices = _load(project=project)
    assert len(notices) == MAX_NOTICES + 1
    assert notices[-1].endswith("and 5 more [loops] keys are ignored")
