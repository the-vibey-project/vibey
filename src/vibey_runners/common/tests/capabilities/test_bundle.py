# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The loop capability bundle: what a `[loops]` table may say, refused by key path when it says
anything else (SP-LOOPS Task 3)."""

from __future__ import annotations

import contextlib
from collections.abc import Mapping
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vibey_runners.common.capabilities.bundle import (
    CAPABILITY_ANSWER_TOKENS_CEILING,
    CAPABILITY_ANSWER_TOKENS_FLOOR,
    CAPABILITY_PROMPT_TOKENS_CEILING,
    CAPABILITY_PROMPT_TOKENS_FLOOR,
    DEFAULT_CAPABILITY_ANSWER_TOKENS,
    DEFAULT_CAPABILITY_PROMPT_TOKENS,
    INSTRUCTION_FILES_MAX,
    INSTRUCTION_MAX_BYTES_CEILING,
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
        "https://fake-token@mcp.example.test/",
        "https://mcp.example.test/\n",
        "https://mcp.example.test/\x1b[2J",
        "https://[::1/x",
        "https://[zz]/",
        "https://exa mple.test/",
        "https://mcp.example.test:99999/",
        "https://mcp.example.test:0/",
        "https://mcp.example.test:port/",
        "https://mcp.example.test/" + "x" * MAX_TEXT,
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


@pytest.mark.parametrize(
    "disable",
    ["x", [3], ["../x"], ["\x1b[2J"], ["a", "a"], [f"n{i}" for i in range(MAX_ENTRIES + 1)]],
)
def test_a_disable_list_from_anywhere_gets_the_one_name_rule(disable: object) -> None:
    with pytest.raises(BundleError) as caught:
        BundleSpec.disable_names(disable)
    assert caught.value.path.startswith("loops.disable")


def test_a_valid_disable_list_is_its_names() -> None:
    assert BundleSpec.disable_names(["a", "b.c"]) == ("a", "b.c")


KEYS = [
    "marketplaces",
    "plugins",
    "mcp_servers",
    "skills",
    "disable",
    "name",
    "source",
    "ref",
    "trust",
    "command",
    "url",
    "env_allow",
    "builtin_web",
    "instruction_files",
    "instruction_max_bytes",
    "snapshot_max_age_days",
    "capability_prompt_tokens",
    "capability_answer_tokens",
]
_SCALARS = st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=40)
_VALUES = st.recursive(
    _SCALARS,
    lambda inner: (
        st.lists(inner, max_size=4)
        | st.dictionaries(st.sampled_from(KEYS) | st.text(max_size=8), inner, max_size=4)
    ),
    max_leaves=20,
)


@settings(max_examples=300, deadline=None)
@given(raw=st.dictionaries(st.sampled_from(KEYS), _VALUES, max_size=5))
def test_any_table_is_a_bundle_or_a_bundle_error(raw: dict[str, object]) -> None:
    with contextlib.suppress(BundleError):  # anything else escaping fails the property
        BundleSpec.from_mapping(raw)


@pytest.mark.parametrize(
    "name",
    [
        "VIBEY_HUB_TOKEN",
        "VIBEY_AGENT_TOKEN",
        "VIBEY_BRAVE_API_KEY",
        "BRAVE_SEARCH_API_KEY",
        "WEBSEARCH_BRAVE_API_KEY",
        "GITHUB_TOKEN",
        "github_token",
        "MY_SECRET_VALUE",
        "DB_PASSWORD",
        "OPENAI_API_KEY",
        "SIGNING_KEY",
        "brave_anything",
    ],
)
def test_env_allow_never_hands_a_server_a_secret(name: str) -> None:
    """A local MCP server's output reaches the model, so a loop's server may not keep the host or
    agent token, a Brave key or anything named like a secret (Global Constraint 3)."""
    servers = [{"name": "f", "trust": "local", "command": ["x"], "env_allow": ["HOME", name]}]
    refusal = _refusal(_with(mcp_servers=servers))
    assert refusal.path == "loops.mcp_servers[0].env_allow[1]"
    assert "secret" in refusal.reason


@pytest.mark.parametrize("name", ["HOME", "LANG", "PATH", "KEYBOARD_LAYOUT", "MONKEY"])
def test_env_allow_keeps_plain_names(name: str) -> None:
    servers = [{"name": "f", "trust": "local", "command": ["x"], "env_allow": [name]}]
    assert BundleSpec.from_mapping({"mcp_servers": servers}).mcp_servers[0].env_allow == (name,)


# -- what a loop is given besides plugins and servers (SP-LOOPS Phase 4, R4, R8, R10, R13) --------


def test_the_default_bundle_turns_builtin_web_off_and_names_claude_md_and_agents_md() -> None:
    bundle = BundleSpec.default()
    assert bundle.builtin_web is False
    assert bundle.instruction_files == ("CLAUDE.md", "AGENTS.md")
    assert bundle.instruction_max_bytes == 65536
    assert bundle.snapshot_max_age_days == 7
    assert BundleSpec.from_mapping({}).builtin_web is False


def test_the_new_keys_are_read_and_survive_narrowing() -> None:
    bundle = BundleSpec.from_mapping(
        {
            "builtin_web": True,
            "instruction_files": ["CLAUDE.md"],
            "instruction_max_bytes": 1,
            "snapshot_max_age_days": 1,
        }
    ).narrowed_by(["currency-research"])
    assert bundle.builtin_web is True
    assert bundle.instruction_files == ("CLAUDE.md",)
    assert bundle.instruction_max_bytes == 1
    assert bundle.snapshot_max_age_days == 1
    assert BundleSpec.from_mapping({"instruction_files": []}).instruction_files == ()
    ceiling = {"instruction_max_bytes": INSTRUCTION_MAX_BYTES_CEILING}
    assert BundleSpec.from_mapping(ceiling).instruction_max_bytes == 1048576


def test_a_bundle_built_by_hand_keeps_the_defaults() -> None:
    bundle = BundleSpec((), (), (), (), frozenset())
    assert bundle.builtin_web is False
    assert bundle.instruction_files == ("CLAUDE.md", "AGENTS.md")
    assert (bundle.instruction_max_bytes, bundle.snapshot_max_age_days) == (65536, 7)


@pytest.mark.parametrize("value", [1, 0, "true", None, [True]])
def test_builtin_web_must_be_a_bool(value: object) -> None:
    error = _refusal({"builtin_web": value})
    assert error.path == "loops.builtin_web"
    assert "true or false" in error.reason


@pytest.mark.parametrize(
    ("files", "path"),
    [
        (["docs/CLAUDE.md"], "loops.instruction_files[0]"),
        (["CLAUDE.md", "../AGENTS.md"], "loops.instruction_files[1]"),
        (["/etc/passwd"], "loops.instruction_files[0]"),
        (["CLAUDE.md", "CLAUDE.md"], "loops.instruction_files[1]"),
        ("CLAUDE.md", "loops.instruction_files"),
    ],
)
def test_an_instruction_file_with_a_slash_is_refused(files: object, path: str) -> None:
    assert _refusal({"instruction_files": files}).path == path


def test_at_most_sixteen_instruction_files_are_named() -> None:
    names = [f"FILE{i}.md" for i in range(INSTRUCTION_FILES_MAX + 1)]
    error = _refusal({"instruction_files": names})
    assert error.path == "loops.instruction_files"
    assert "at most 16" in error.reason
    assert len(BundleSpec.from_mapping({"instruction_files": names[:16]}).instruction_files) == 16


@pytest.mark.parametrize("value", [0, -1, 1048577, True, 1.5, "65536", None])
def test_instruction_max_bytes_outside_1_to_1048576_is_refused(value: object) -> None:
    error = _refusal({"instruction_max_bytes": value})
    assert error.path == "loops.instruction_max_bytes"
    assert "1 and 1048576" in error.reason


@pytest.mark.parametrize("value", [0, -7, False, True, 2.0, "7", None])
def test_snapshot_max_age_days_below_one_is_refused(value: object) -> None:
    error = _refusal({"snapshot_max_age_days": value})
    assert error.path == "loops.snapshot_max_age_days"
    assert "at least 1" in error.reason


# -- the two token budgets of a loop that lists its own capabilities (SP-LOOPS Phase 5, R8) ------


def test_the_default_bundle_gives_3072_prompt_tokens_and_3000_answer_tokens() -> None:
    bundle = BundleSpec.default()
    assert bundle.capability_prompt_tokens == DEFAULT_CAPABILITY_PROMPT_TOKENS == 3072
    assert bundle.capability_answer_tokens == DEFAULT_CAPABILITY_ANSWER_TOKENS == 3000
    by_hand = BundleSpec((), (), (), (), frozenset())
    assert (by_hand.capability_prompt_tokens, by_hand.capability_answer_tokens) == (3072, 3000)
    read = BundleSpec.from_mapping(
        {"capability_prompt_tokens": 512, "capability_answer_tokens": 8192}
    ).narrowed_by(["currency-research"])
    assert (read.capability_prompt_tokens, read.capability_answer_tokens) == (512, 8192)
    assert (CAPABILITY_PROMPT_TOKENS_FLOOR, CAPABILITY_PROMPT_TOKENS_CEILING) == (512, 4096)
    assert (CAPABILITY_ANSWER_TOKENS_FLOOR, CAPABILITY_ANSWER_TOKENS_CEILING) == (256, 8192)
    edges = {"capability_prompt_tokens": 4096, "capability_answer_tokens": 256}
    edge = BundleSpec.from_mapping(edges)
    assert (edge.capability_prompt_tokens, edge.capability_answer_tokens) == (4096, 256)


@pytest.mark.parametrize("value", [511, 4097, 0, -1, True, False, 3072.0, "3072", None])
def test_capability_prompt_tokens_outside_512_to_4096_is_refused(value: object) -> None:
    error = _refusal({"capability_prompt_tokens": value})
    assert error.path == "loops.capability_prompt_tokens"
    assert "between 512 and 4096" in error.reason


@pytest.mark.parametrize("value", [255, 8193, 0, -1, True, False, 3000.0, "3000", None])
def test_capability_answer_tokens_outside_256_to_8192_is_refused(value: object) -> None:
    error = _refusal({"capability_answer_tokens": value})
    assert error.path == "loops.capability_answer_tokens"
    assert "between 256 and 8192" in error.reason
