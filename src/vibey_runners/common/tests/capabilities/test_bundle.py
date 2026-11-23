# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The loop capability bundle: what a `[loops]` table may say, refused by key path when it says
anything else (SP-LOOPS Task 3)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from vibey_runners.common.capabilities.bundle import (
    MAX_ENTRIES,
    MAX_TEXT,
    BundleSpec,
)
from vibey_runners.common.capabilities.bundle_error import BundleError
from vibey_runners.common.capabilities.defaults import (
    DEFAULT_MARKETPLACE_NAME,
    DEFAULT_RESEARCH_PLUGINS,
)
from vibey_runners.common.capabilities.interfaces.bundle_interface import BundleSpecInterface
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.plugin_spec import PluginSpec

FULL: Mapping[str, Any] = {
    "marketplaces": [
        {"name": "acme", "source": "https://example.test/acme.git", "ref": "v1.2.0"},
        {"name": "local-one", "source": "/home/person/plugins"},
    ],
    "plugins": ["currency-research@vibey", "linting@acme"],
    "mcp_servers": [
        {
            "name": "files",
            "trust": "local",
            "command": ["fake-mcp", "--stdio"],
            "env_allow": ["HOME", "LANG"],
        },
        {"name": "tickets", "trust": "remote", "url": "https://mcp.example.test/v1"},
    ],
    "skills": ["research-search-and-source-quality"],
    "disable": ["old-skill"],
}


def _with(**changes: Any) -> dict[str, Any]:
    raw = dict(FULL)
    raw.update(changes)
    return raw


def _refusal(raw: Mapping[str, Any]) -> BundleError:
    with pytest.raises(BundleError) as caught:
        BundleSpec.from_mapping(raw)
    return caught.value


def test_a_full_valid_table_reads_every_entry() -> None:
    bundle = BundleSpec.from_mapping(FULL)
    assert bundle.marketplaces == (
        MarketplaceSpec("acme", "https://example.test/acme.git", "v1.2.0"),
        MarketplaceSpec("local-one", "/home/person/plugins", None),
    )
    assert bundle.plugins == (
        PluginSpec("currency-research", "vibey"),
        PluginSpec("linting", "acme"),
    )
    assert bundle.mcp_servers == (
        McpServerSpec("files", "local", ("fake-mcp", "--stdio"), None, ("HOME", "LANG")),
        McpServerSpec("tickets", "remote", None, "https://mcp.example.test/v1", ()),
    )
    assert bundle.skills == ("research-search-and-source-quality",)
    assert bundle.disabled == frozenset({"old-skill"})
    assert isinstance(bundle, BundleSpecInterface)


def test_no_table_is_the_default_bundle_with_the_research_plugins() -> None:
    bundle = BundleSpec.from_mapping({})
    assert bundle.marketplaces == ()
    assert bundle.plugins == tuple(
        PluginSpec(name, DEFAULT_MARKETPLACE_NAME) for name in DEFAULT_RESEARCH_PLUGINS
    )
    assert DEFAULT_RESEARCH_PLUGINS == ("currency-research",)
    assert bundle.mcp_servers == ()
    assert bundle.skills == ()
    assert bundle.disabled == frozenset()
    assert BundleSpec.default() == bundle


def test_an_explicit_empty_plugin_list_is_no_plugins() -> None:
    assert BundleSpec.from_mapping({"plugins": []}).plugins == ()


def test_the_persons_own_disable_list_removes_a_default_plugin() -> None:
    bundle = BundleSpec.from_mapping({"disable": ["currency-research"]})
    assert bundle.plugins == ()
    assert "currency-research" in bundle.disabled


def test_a_remote_server_without_a_url_is_refused_at_its_key_path() -> None:
    servers = [{"name": "tickets", "trust": "remote"}]
    error = _refusal(_with(mcp_servers=servers))
    assert error.path == "loops.mcp_servers[0].url"
    assert str(error).startswith("loops.mcp_servers[0].url: ")


def test_a_local_server_without_a_command_is_refused_at_its_key_path() -> None:
    servers = [{"name": "files", "trust": "local"}]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].command"


@pytest.mark.parametrize("command", [[], ["ok", ""], "fake-mcp --stdio", ["ok", 3]])
def test_a_local_command_must_be_a_nonempty_list_of_nonempty_strings(command: object) -> None:
    servers = [{"name": "files", "trust": "local", "command": command}]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].command"


def test_a_local_command_is_capped() -> None:
    command = ["x"] * (MAX_ENTRIES + 1)
    servers = [{"name": "files", "trust": "local", "command": command}]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].command"


def test_a_local_server_may_not_also_name_a_url() -> None:
    servers = [
        {"name": "files", "trust": "local", "command": ["x"], "url": "https://e.test/"},
    ]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].url"


def test_a_remote_server_may_not_also_name_a_command() -> None:
    servers = [
        {"name": "t", "trust": "remote", "url": "https://e.test/", "command": ["x"]},
    ]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].command"


@pytest.mark.parametrize(
    "url",
    [
        "http://mcp.example.test/",
        "file:///etc/passwd",
        "https://",
        "https://person:fake-secret@mcp.example.test/",
        "https://mcp.example.test/\n",
        7,
    ],
)
def test_a_remote_url_must_be_https_with_a_host(url: object) -> None:
    servers = [{"name": "t", "trust": "remote", "url": url}]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].url"


@pytest.mark.parametrize("trust", ["trusted", "", None, 1])
def test_trust_is_local_or_remote(trust: object) -> None:
    servers = [{"name": "t", "trust": trust, "url": "https://e.test/"}]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].trust"


def test_trust_is_required() -> None:
    servers = [{"name": "t", "url": "https://e.test/"}]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].trust"


@pytest.mark.parametrize("env_allow", [["1BAD"], ["OK", "with space"], "HOME", [3]])
def test_env_allow_names_environment_variables(env_allow: object) -> None:
    servers = [{"name": "f", "trust": "local", "command": ["x"], "env_allow": env_allow}]
    assert _refusal(_with(mcp_servers=servers)).path == "loops.mcp_servers[0].env_allow"


@pytest.mark.parametrize(
    ("raw", "path"),
    [
        ({"bogus": 1}, "loops.bogus"),
        (
            _with(marketplaces=[{"name": "a", "source": "s", "branch": "x"}]),
            "loops.marketplaces[0].branch",
        ),
        (
            _with(mcp_servers=[{"name": "f", "trust": "local", "command": ["x"], "cwd": "/"}]),
            "loops.mcp_servers[0].cwd",
        ),
    ],
)
def test_an_unknown_key_is_refused_at_its_path(raw: Mapping[str, Any], path: str) -> None:
    assert _refusal(raw).path == path


def test_the_first_unknown_key_in_sorted_order_is_named() -> None:
    assert _refusal({"zeta": 1, "alpha": 2}).path == "loops.alpha"


@pytest.mark.parametrize("key", ["marketplaces", "plugins", "mcp_servers", "skills", "disable"])
def test_each_list_key_must_be_a_list(key: str) -> None:
    assert _refusal(_with(**{key: "not-a-list"})).path == f"loops.{key}"


@pytest.mark.parametrize("key", ["marketplaces", "mcp_servers"])
def test_each_table_list_holds_tables(key: str) -> None:
    assert _refusal(_with(**{key: ["not-a-table"]})).path == f"loops.{key}[0]"


@pytest.mark.parametrize("key", ["plugins", "skills", "disable"])
def test_each_list_is_capped(key: str) -> None:
    too_many = [f"name-{i}" for i in range(MAX_ENTRIES + 1)]
    assert _refusal(_with(**{key: too_many})).path == f"loops.{key}"


@pytest.mark.parametrize(
    "name",
    ["", "..", ".hidden", "-flag", "has/slash", "has space", "a@b", "x" * 129, 5, None],
)
def test_a_name_is_a_plain_identifier(name: object) -> None:
    marketplaces = [{"name": name, "source": "s"}]
    assert _refusal(_with(marketplaces=marketplaces, plugins=[])).path == (
        "loops.marketplaces[0].name"
    )


@pytest.mark.parametrize("skills", [[".."], ["a/b"], [3]])
def test_a_skill_name_is_a_plain_identifier(skills: object) -> None:
    assert _refusal(_with(skills=skills)).path == "loops.skills[0]"


@pytest.mark.parametrize("source", ["", "-uupload-pack=evil", 3, "x" * (MAX_TEXT + 1)])
def test_a_source_is_nonempty_bounded_and_never_an_option(source: object) -> None:
    marketplaces = [{"name": "acme", "source": source}]
    assert _refusal(_with(marketplaces=marketplaces, plugins=[])).path == (
        "loops.marketplaces[0].source"
    )


def test_a_source_is_required() -> None:
    marketplaces = [{"name": "acme"}]
    assert _refusal(_with(marketplaces=marketplaces, plugins=[])).path == (
        "loops.marketplaces[0].source"
    )


@pytest.mark.parametrize("ref", ["", "--force", 3])
def test_a_ref_is_nonempty_and_never_an_option(ref: object) -> None:
    marketplaces = [{"name": "acme", "source": "s", "ref": ref}]
    assert _refusal(_with(marketplaces=marketplaces, plugins=[])).path == (
        "loops.marketplaces[0].ref"
    )


def test_the_shipped_marketplace_name_is_reserved() -> None:
    marketplaces = [{"name": DEFAULT_MARKETPLACE_NAME, "source": "https://evil.test/x.git"}]
    assert _refusal(_with(marketplaces=marketplaces)).path == "loops.marketplaces[0].name"


@pytest.mark.parametrize("plugin", ["no-marketplace", "a@b@c", "@acme", "x@", 3])
def test_a_plugin_is_name_at_marketplace(plugin: object) -> None:
    assert _refusal(_with(plugins=[plugin])).path == "loops.plugins[0]"


def test_a_plugin_from_an_undeclared_marketplace_is_refused_by_name() -> None:
    error = _refusal(_with(plugins=["linting@nowhere"]))
    assert error.path == "loops.plugins[0]"
    assert "nowhere" in str(error)


@pytest.mark.parametrize(
    ("raw", "path"),
    [
        (
            _with(
                marketplaces=[{"name": "a", "source": "s"}, {"name": "a", "source": "t"}],
                plugins=[],
            ),
            "loops.marketplaces[1].name",
        ),
        (_with(plugins=["x@vibey", "x@acme"]), "loops.plugins[1]"),
        (
            _with(
                mcp_servers=[
                    {"name": "f", "trust": "local", "command": ["x"]},
                    {"name": "f", "trust": "remote", "url": "https://e.test/"},
                ]
            ),
            "loops.mcp_servers[1].name",
        ),
        (_with(skills=["a", "a"]), "loops.skills[1]"),
    ],
)
def test_a_duplicate_name_is_refused(raw: Mapping[str, Any], path: str) -> None:
    assert _refusal(raw).path == path


def test_narrowed_by_removes_plugins_servers_and_skills_by_name() -> None:
    bundle = BundleSpec.from_mapping(FULL)
    narrowed = bundle.narrowed_by(
        ["currency-research", "files", "research-search-and-source-quality"]
    )
    assert narrowed.plugins == (PluginSpec("linting", "acme"),)
    assert [server.name for server in narrowed.mcp_servers] == ["tickets"]
    assert narrowed.skills == ()
    assert narrowed.marketplaces == bundle.marketplaces
    assert narrowed.disabled == frozenset(
        {"old-skill", "currency-research", "files", "research-search-and-source-quality"}
    )
    assert bundle.plugins == BundleSpec.from_mapping(FULL).plugins  # the original is unchanged


def test_narrowing_by_nothing_is_the_same_bundle() -> None:
    bundle = BundleSpec.from_mapping(FULL)
    assert bundle.narrowed_by([]) == bundle


def test_a_bundle_error_carries_its_path_and_reason() -> None:
    error = BundleError("loops.x", "is wrong")
    assert (error.path, error.reason) == ("loops.x", "is wrong")
    assert str(error) == "loops.x: is wrong"
    assert isinstance(error, ValueError)
