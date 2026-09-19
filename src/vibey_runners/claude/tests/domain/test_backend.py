# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""domain/backend.py — backend profiles, identities, and the runtime overlay."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from claudeloop.domain.backend import (
    BACKEND_MISCONFIGURED_PREFIX,
    DEFAULT_LOCAL_AUTH_TOKEN,
    DEFAULT_PROFILE_NAME,
    EXIT_BACKEND_MISCONFIGURED,
    PROFILE_OWNED_ENV_KEYS,
    BackendIdentity,
    BackendProfile,
    BackendRuntime,
)
from claudeloop.domain.errors import BackendProfileError
from claudeloop.domain.interfaces import (
    BackendIdentityInterface,
    BackendProfileInterface,
    BackendRuntimeInterface,
)

OLLAMA = "http://127.0.0.1:11434"


def _local(**overrides: object) -> BackendProfile:
    fields: dict[str, object] = {
        "name": "local",
        "base_url": OLLAMA,
        "model_low": "qwen2.5-coder:14b",
        "model_medium": "qwen2.5-coder:14b",
        "model_high": "qwen2.5-coder:32b",
    }
    fields.update(overrides)
    return BackendProfile(**fields)  # type: ignore[arg-type]


# --- the default profile changes nothing ---


def test_default_profile_is_anthropic_and_adds_no_environment() -> None:
    profile = BackendProfile()
    assert profile.name == DEFAULT_PROFILE_NAME
    assert profile.is_local is False
    assert profile.effective_cost_mode == "reported"
    assert profile.effective_pass_effort is True
    assert profile.effective_disable_nonessential_traffic is False
    assert profile.effective_small_fast_model == ""
    assert profile.env_overlay(auth_token="ignored") == {}
    assert profile.runtime(auth_token="") == BackendRuntime()


def test_default_profile_keeps_top_level_tiers() -> None:
    assert BackendProfile().tier_models(low="a", medium="b", high="c") == ("a", "b", "c")


def test_default_profile_accepts_any_model() -> None:
    BackendProfile().check_model("claude-opus-4-6")
    BackendProfile().check_tools(web_search=True, deep_research=True)


def test_constants_are_what_the_cli_and_docs_promise() -> None:
    assert EXIT_BACKEND_MISCONFIGURED == 78
    assert BACKEND_MISCONFIGURED_PREFIX == "backend misconfigured"
    assert DEFAULT_LOCAL_AUTH_TOKEN == "ollama"
    assert {
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_API_KEY",
    } == PROFILE_OWNED_ENV_KEYS


# --- a local profile ---


def test_local_profile_defaults_are_the_free_ones() -> None:
    profile = _local()
    assert profile.is_local is True
    assert profile.effective_cost_mode == "zero"
    assert profile.effective_pass_effort is False
    assert profile.effective_disable_nonessential_traffic is True
    assert profile.effective_small_fast_model == "qwen2.5-coder:14b"
    assert profile.effective_done_marker_fallback is False
    assert profile.runtime(auth_token="t").done_marker_fallback is False


def test_done_marker_fallback_defaults_on_for_anthropic_and_can_be_overridden() -> None:
    assert BackendProfile().effective_done_marker_fallback is True
    assert BackendProfile().runtime(auth_token="").done_marker_fallback is True
    assert _local(done_marker_fallback=True).effective_done_marker_fallback is True
    assert BackendProfile(name="x", done_marker_fallback=False).effective_done_marker_fallback is (
        False
    )


def test_local_env_points_claude_code_at_the_backend_and_blanks_the_paid_key() -> None:
    env = _local().env_overlay(auth_token="ollama")
    assert env == {
        "ANTHROPIC_BASE_URL": OLLAMA,
        "ANTHROPIC_AUTH_TOKEN": "ollama",
        # An empty value, not an absent one: the SDK merges options.env over the
        # inherited environment, so only an explicit "" can override a paid key.
        "ANTHROPIC_API_KEY": "",
        "ANTHROPIC_DEFAULT_SONNET_MODEL": "qwen2.5-coder:14b",
        "ANTHROPIC_DEFAULT_OPUS_MODEL": "qwen2.5-coder:14b",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": "qwen2.5-coder:14b",
        "ANTHROPIC_SMALL_FAST_MODEL": "qwen2.5-coder:14b",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    }


def test_local_env_carries_every_optional_key_when_set() -> None:
    env = _local(
        small_fast_model="qwen2.5-coder:1.5b",
        subagent_model="qwen2.5-coder:7b",
        context_window=32768,
        max_output_tokens=8192,
        extra_env=(("CLAUDE_CODE_MAX_RETRIES", "2"), ("OLLAMA_KEEP_ALIVE", "30m")),
    ).env_overlay(auth_token="t")
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "qwen2.5-coder:1.5b"
    assert env["ANTHROPIC_SMALL_FAST_MODEL"] == "qwen2.5-coder:1.5b"
    assert env["CLAUDE_CODE_SUBAGENT_MODEL"] == "qwen2.5-coder:7b"
    assert env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == "32768"
    assert env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == "32768"
    assert env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "8192"
    assert env["CLAUDE_CODE_MAX_RETRIES"] == "2"
    assert env["OLLAMA_KEEP_ALIVE"] == "30m"


def test_extra_env_is_applied_last_so_it_can_retune_a_derived_key() -> None:
    env = _local(extra_env=(("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "0"),)).env_overlay(
        auth_token="t"
    )
    assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "0"


def test_tri_state_overrides_win_over_the_local_defaults() -> None:
    profile = _local(cost_mode="reported", pass_effort=True, disable_nonessential_traffic=False)
    assert profile.effective_cost_mode == "reported"
    assert profile.effective_pass_effort is True
    assert "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" not in profile.env_overlay(auth_token="t")


def test_anthropic_profile_may_opt_into_optional_env_keys() -> None:
    profile = BackendProfile(
        name="tuned",
        small_fast_model="claude-haiku-4-5",
        subagent_model="claude-sonnet-4-5",
        disable_nonessential_traffic=True,
        pass_effort=False,
    )
    env = profile.env_overlay(auth_token="")
    assert "ANTHROPIC_BASE_URL" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "claude-haiku-4-5"
    assert env["CLAUDE_CODE_SUBAGENT_MODEL"] == "claude-sonnet-4-5"
    assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"
    assert profile.effective_pass_effort is False


def test_local_profile_tiers_replace_the_top_level_ones() -> None:
    assert _local().tier_models(low="a", medium="b", high="c") == (
        "qwen2.5-coder:14b",
        "qwen2.5-coder:14b",
        "qwen2.5-coder:32b",
    )


def test_required_models_are_deduplicated_in_tier_order() -> None:
    profile = _local(small_fast_model="qwen2.5-coder:1.5b", subagent_model="qwen2.5-coder:32b")
    assert profile.required_models() == (
        "qwen2.5-coder:14b",
        "qwen2.5-coder:32b",
        "qwen2.5-coder:1.5b",
    )


def test_runtime_bundles_what_the_gateway_needs() -> None:
    runtime = _local(cli_path=" /opt/claude ").runtime(auth_token="ollama")
    assert runtime.local is True
    assert runtime.cost_mode == "zero"
    assert runtime.pass_effort is False
    assert runtime.cli_path == "/opt/claude"
    assert runtime.environment()["ANTHROPIC_BASE_URL"] == OLLAMA
    assert BackendProfile().runtime(auth_token="").cli_path is None


def test_check_model_refuses_a_claude_id_on_a_local_backend() -> None:
    with pytest.raises(BackendProfileError, match="does not serve the Anthropic model"):
        _local().check_model("claude-opus-4-6")
    _local().check_model("qwen2.5-coder:32b")


@pytest.mark.parametrize(
    ("web_search", "deep_research", "named"),
    [(True, False, "web_search"), (False, True, "deep_research"), (True, True, "and")],
)
def test_check_tools_refuses_server_side_tools_on_a_local_backend(
    web_search: bool, deep_research: bool, named: str
) -> None:
    with pytest.raises(BackendProfileError, match=named):
        _local().check_tools(web_search=web_search, deep_research=deep_research)


def test_check_tools_allows_nothing_requested_on_a_local_backend() -> None:
    _local().check_tools(web_search=False, deep_research=False)


# --- validation ---


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": "  "}, "non-empty name"),
        ({"base_url": "127.0.0.1:11434"}, "http:// or https://"),
        ({"context_window": -1}, "context_window must be a non-negative integer"),
        ({"max_output_tokens": -5}, "max_output_tokens must be a non-negative integer"),
        ({"context_window": True}, "context_window must be a non-negative integer"),
        ({"cost_mode": "free"}, "cost_mode must be one of"),
        ({"auth_token_env": "NOT-A-VAR"}, "auth_token_env must name"),
        ({"extra_env": (("1BAD", "x"),)}, "is not an environment variable name"),
        ({"extra_env": (("ANTHROPIC_API_KEY", "sk-live"),)}, "may not set ANTHROPIC_API_KEY"),
        ({"model_high": ""}, "missing model_high"),
        ({"model_low": " ", "model_medium": ""}, "missing model_low, model_medium"),
        ({"model_medium": "claude-opus-4-6"}, "model_medium"),
        ({"small_fast_model": "Claude-Haiku-4-5"}, "small_fast_model"),
        ({"subagent_model": "claude-sonnet-4-5"}, "subagent_model"),
    ],
)
def test_invalid_local_profiles_are_refused(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(BackendProfileError, match=message):
        _local(**overrides)


def test_anthropic_profile_may_not_read_a_token_env_var() -> None:
    with pytest.raises(BackendProfileError, match="auth_token_env only applies"):
        BackendProfile(name="x", auth_token_env="MY_TOKEN")


def test_anthropic_profile_may_not_hide_real_spend() -> None:
    with pytest.raises(BackendProfileError, match="would hide real Anthropic spend"):
        BackendProfile(name="x", cost_mode="zero")


def test_https_base_url_is_accepted() -> None:
    assert _local(base_url="https://gpu.example.com").is_local is True


@given(st.integers(min_value=0, max_value=10**12), st.integers(min_value=0, max_value=10**12))
def test_property_token_limits_render_exactly_and_zero_means_unset(
    context_window: int, max_output_tokens: int
) -> None:
    """Every non-negative value is accepted and rendered as the exact decimal
    Claude Code parses; 0 leaves Claude Code's own default in place."""
    env = _local(context_window=context_window, max_output_tokens=max_output_tokens).env_overlay(
        auth_token="t"
    )
    if context_window:
        assert env["CLAUDE_CODE_MAX_CONTEXT_TOKENS"] == str(context_window)
        assert env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] == str(context_window)
    else:
        assert "CLAUDE_CODE_MAX_CONTEXT_TOKENS" not in env
        assert "CLAUDE_CODE_AUTO_COMPACT_WINDOW" not in env
    if max_output_tokens:
        assert env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == str(max_output_tokens)
    else:
        assert "CLAUDE_CODE_MAX_OUTPUT_TOKENS" not in env


@given(st.integers(max_value=-1))
def test_property_negative_token_limits_are_always_refused(value: int) -> None:
    with pytest.raises(BackendProfileError):
        _local(context_window=value)
    with pytest.raises(BackendProfileError):
        _local(max_output_tokens=value)


@given(st.text())
def test_property_a_local_backend_never_receives_a_paid_key(extra: str) -> None:
    """Whatever else a profile carries, its overlay blanks ANTHROPIC_API_KEY."""
    env = _local(extra_env=(("SOME_VAR", extra),)).env_overlay(auth_token="t")
    assert env["ANTHROPIC_API_KEY"] == ""


# --- identities ---


def test_identity_of_each_kind_and_its_text_form() -> None:
    assert str(BackendProfile().identity()) == "anthropic"
    gateway = BackendProfile().identity(ambient_base_url="https://proxy.corp/ ")
    assert str(gateway) == "gateway:https://proxy.corp"
    local = _local(base_url=OLLAMA + "/").identity(ambient_base_url="https://ignored")
    assert str(local) == f"local:{OLLAMA}"
    assert local.is_local is True
    assert gateway.is_local is False


@pytest.mark.parametrize("text", ["anthropic", "gateway:https://proxy.corp", f"local:{OLLAMA}"])
def test_identity_round_trips_through_its_text_form(text: str) -> None:
    assert str(BackendIdentity.parse(text)) == text


@pytest.mark.parametrize("text", ["", "anthropic:x", "local:", "gateway", "ollama:http://x"])
def test_identity_parse_refuses_anything_else(text: str) -> None:
    with pytest.raises(BackendProfileError, match="unrecognised backend identity"):
        BackendIdentity.parse(text)


def test_resume_refusal_names_both_backends() -> None:
    local = BackendIdentity(kind="local", url=OLLAMA)
    refusal = BackendIdentity().resume_refusal(local)
    assert refusal is not None
    assert f"local:{OLLAMA}" in refusal
    assert "anthropic" in refusal
    assert "--profile" in refusal


def test_resume_is_allowed_on_the_same_backend_or_unknown_history() -> None:
    local = BackendIdentity(kind="local", url=OLLAMA)
    assert local.resume_refusal(BackendIdentity.parse(f"local:{OLLAMA}/")) is None
    assert local.resume_refusal(None) is None


def test_live_run_guards_on_a_local_identity() -> None:
    local = BackendIdentity(kind="local", url=OLLAMA)
    with pytest.raises(BackendProfileError, match="does not serve the Anthropic model"):
        local.check_model(" Claude-Sonnet-4-5 ")
    local.check_model("high")
    with pytest.raises(BackendProfileError, match="server-side tools"):
        local.check_server_tools()


def test_live_run_guards_pass_on_anthropic() -> None:
    BackendIdentity().check_model("claude-sonnet-4-5")
    BackendIdentity().check_server_tools()


def test_every_backend_class_satisfies_its_declared_interface() -> None:
    assert isinstance(BackendIdentity(), BackendIdentityInterface)
    assert isinstance(BackendRuntime(), BackendRuntimeInterface)
    assert isinstance(BackendProfile(), BackendProfileInterface)
