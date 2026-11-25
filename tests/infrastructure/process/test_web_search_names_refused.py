# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A project's allow-list can never name vibey's own web search settings (SP-LOOPS Phase 6).

vibey reads every `VIBEY_*` search setting under a `WEBSEARCH_*` form too -- the local SearXNG's
address among them -- and the Brave key under `WEBSEARCH_BRAVE_API_KEY` and
`BRAVE_SEARCH_API_KEY`. No session and no gate may hold a SearXNG address or a Brave key, so a
project's `[engine_environment]` (for every engine or for one) or `[gates] env_allow` that names
any of them is refused when the worker is built, as the Brave aliases always were, and the refusal
says what to do instead. The person's own `vibey.toml` keeps its rules: a local MCP server's
`env_allow` may still keep such a name, and vibey still reads the `WEBSEARCH_*` forms as the
person's own settings. Every value here is a fake."""

from __future__ import annotations

import pytest
from vibey_runners.common.capabilities.bundle import BundleSpec

from vibey.infrastructure.build.gate_runner import SubprocessGateRunner
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.process import (
    GATE_FORBIDDEN,
    MODEL_SESSION_FORBIDDEN,
    ChildEnvironment,
    EnvironmentAllowList,
)
from vibey.infrastructure.searxng.searxng_provisioner import OWN_URL_NAMES
from vibey.infrastructure.web.search import WebSearchSettings

WEB_SEARCH_NAMES = (
    "WEBSEARCH_SEARXNG_URL",
    "WEBSEARCH_SEARXNG_INSTANCE",
    "WEBSEARCH_PROVIDER",
    "WEBSEARCH_TIMEOUT",
    "WEBSEARCH_RESULTS",
    "WEBSEARCH_IDENTITY_TTL",
    "WEBSEARCH_BRAVE_API_KEY",
    "WEBSEARCH_COMMAND",
)
"""Every `WEBSEARCH_*` name vibey reads or once told a session, by name."""

WEB_SEARCH_ENTRIES = (*WEB_SEARCH_NAMES, "WEBSEARCH_*", "WEBSEARCH_SEARXNG_*")
"""What a project might declare: each name, and prefixes that cover them."""

ADVICE = "another name in its own environment"


@pytest.mark.parametrize("entry", WEB_SEARCH_ENTRIES)
def test_a_projects_allow_list_for_every_engine_naming_one_is_refused(entry: str) -> None:
    with pytest.raises(ValueError, match=rf"engine_environment\.allow: {entry}") as refused:
        EngineEnvironmentPolicy.from_config({"engine_environment": {"allow": ["HOME", entry]}})
    assert "can never be passed to a child process" in str(refused.value)
    assert ADVICE in str(refused.value)


@pytest.mark.parametrize("entry", WEB_SEARCH_ENTRIES)
def test_a_projects_allow_list_for_one_engine_naming_one_is_refused(entry: str) -> None:
    config = {"engine_environment": {"engines": {"qwenloop": [entry]}}}
    with pytest.raises(ValueError, match=rf"engine_environment\.engines\.qwenloop: {entry}"):
        EngineEnvironmentPolicy.from_config(config)
    with pytest.raises(ValueError, match=ADVICE):
        EngineEnvironmentPolicy(allow=[entry])


@pytest.mark.parametrize("entry", WEB_SEARCH_ENTRIES)
def test_a_projects_gate_allow_list_naming_one_is_refused(entry: str) -> None:
    with pytest.raises(ValueError, match=rf"gates\.env_allow: {entry}") as refused:
        SubprocessGateRunner.from_config({"gates": {"env_allow": [entry]}})
    assert "can never be passed to a child process" in str(refused.value)
    assert ADVICE in str(refused.value)
    with pytest.raises(ValueError, match=ADVICE):
        SubprocessGateRunner(env_allow=[entry])


@pytest.mark.parametrize("forbidden", [MODEL_SESSION_FORBIDDEN, GATE_FORBIDDEN])
@pytest.mark.parametrize("name", WEB_SEARCH_NAMES)
def test_no_rule_admits_one_and_no_overlay_may_set_one(forbidden: object, name: str) -> None:
    allow = EnvironmentAllowList(["PATH"], ["WEB_", "WEBS_"], forbidden=forbidden)  # type: ignore[arg-type]
    assert not allow.admits(name)
    env = ChildEnvironment(allow, source={"PATH": "/bin", name: "http://127.0.0.1:9/fake"}).build()
    assert name not in env
    with pytest.raises(ValueError, match=f"{name} can never be passed"):
        ChildEnvironment(allow, overlay={name: "http://127.0.0.1:9/fake"})


@pytest.mark.parametrize("forbidden", [MODEL_SESSION_FORBIDDEN, GATE_FORBIDDEN])
def test_a_prefix_that_covers_them_is_refused(forbidden: object) -> None:
    for prefix in ("WEB", "WEBSEARCH", "W"):
        with pytest.raises(ValueError, match=f"{prefix}\\* can never be passed"):
            EnvironmentAllowList([], [prefix], forbidden=forbidden)  # type: ignore[arg-type]


@pytest.mark.parametrize("forbidden", [MODEL_SESSION_FORBIDDEN, GATE_FORBIDDEN])
def test_the_brave_aliases_say_the_same_and_other_refusals_do_not(forbidden: object) -> None:
    with pytest.raises(ValueError, match=ADVICE):
        EnvironmentAllowList(["BRAVE_SEARCH_API_KEY"], forbidden=forbidden)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="VIBEY_PG_URL can never be passed") as refused:
        EnvironmentAllowList(["VIBEY_PG_URL"], forbidden=forbidden)  # type: ignore[arg-type]
    assert ADVICE not in str(refused.value)


def test_a_name_that_only_looks_alike_is_still_admitted() -> None:
    allow = EnvironmentAllowList(["PROJECT_SEARXNG_URL", "MY_WEBSEARCH_URL"], ["SEARCH_"])
    source = {"PROJECT_SEARXNG_URL": "a", "MY_WEBSEARCH_URL": "b", "SEARCH_X": "c"}
    assert ChildEnvironment(allow, source=source).build() == source


# -- The person's own vibey.toml keeps its rules --------------------------------------------------


def test_a_persons_own_mcp_server_may_still_keep_one() -> None:
    servers = [
        {"name": "f", "trust": "local", "command": ["x"], "env_allow": ["WEBSEARCH_SEARXNG_URL"]}
    ]
    spec = BundleSpec.from_mapping({"mcp_servers": servers})
    assert spec.mcp_servers[0].env_allow == ("WEBSEARCH_SEARXNG_URL",)


def test_vibey_still_reads_the_websearch_forms_as_the_persons_own_settings() -> None:
    settings = WebSearchSettings.from_environment(
        {"WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:18089"}, provisioned=lambda: None
    )
    assert settings.searxng_url == "http://127.0.0.1:18089"
    assert settings.searxng_url_env == "WEBSEARCH_SEARXNG_URL"
    assert "WEBSEARCH_SEARXNG_URL" in OWN_URL_NAMES
