# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one local-engine resolver, and the one local endpoint setting (ADR-0038, ADR-0060)."""

from pathlib import Path

import pytest

from vibey.domain.config import ConfigError
from vibey.domain.engine import EngineId
from vibey.infrastructure.engines.descriptors import CLAUDELOOP, GPTOSSLOOP, QWENLOOP
from vibey.infrastructure.engines.interfaces import (
    LocalEndpointEnvironmentInterface,
    LocalEngineSettingsInterface,
)
from vibey.infrastructure.engines.local_engines import (
    LOCAL_ENGINE_SWITCHES,
    QWENLOOP_SWITCH_NOTICE,
    RUNNER_VARIABLES,
    LocalEndpointEnvironment,
    LocalEngineSettings,
)
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter
from vibey.infrastructure.interfaces import (
    LocalEngineSwitchInterface,
    LocalRunnerVariablesInterface,
)

GPTOSS_SWITCH = "VIBEY_FEATURE_GPTOSSLOOP"
QWEN_SWITCH = "VIBEY_FEATURE_QWENLOOP"
CLAUDE_LOCAL_SWITCH = "VIBEY_FEATURE_CLAUDELOOP_LOCAL"


def _settings(environ: dict[str, str] | None = None, **config: object) -> LocalEngineSettings:
    return LocalEngineSettings(environ=environ or {}, config=config)


# ── switches ────────────────────────────────────────────────────────────────


def test_there_is_one_switch_per_local_engine_named_after_its_feature_key() -> None:
    assert [
        (s.engine_id, s.feature_key, s.env_var, s.on_by_default) for s in LOCAL_ENGINE_SWITCHES
    ] == [
        (EngineId.GPTOSSLOOP, "gptossloop", GPTOSS_SWITCH, True),
        (EngineId.QWENLOOP, "qwenloop", QWEN_SWITCH, False),
        (EngineId.CLAUDELOOP_LOCAL, "claudeloop_local", CLAUDE_LOCAL_SWITCH, False),
    ]
    assert all(isinstance(s, LocalEngineSwitchInterface) for s in LOCAL_ENGINE_SWITCHES)


def test_only_gptossloop_is_on_by_default() -> None:
    """ADR-0060: the sovereign default engine ships on; every other local engine is opt-in."""
    settings = _settings()

    assert settings.enabled_engines == (EngineId.GPTOSSLOOP,)
    assert settings.any_enabled is True
    assert settings.on_by_default(EngineId.GPTOSSLOOP) is True
    assert settings.on_by_default(EngineId.QWENLOOP) is False
    assert settings.on_by_default(EngineId.CLAUDELOOP) is False


@pytest.mark.parametrize(
    ("environ", "config"),
    [({GPTOSS_SWITCH: "0"}, {}), ({}, {"features": {"gptossloop": False}})],
)
def test_gptossloop_is_switched_off_only_by_saying_so(
    environ: dict[str, str], config: dict[str, object]
) -> None:
    assert LocalEngineSettings(environ=environ, config=config).enabled_engines == ()


def test_the_features_table_switches_each_engine_on() -> None:
    settings = _settings(features={"qwenloop": True, "claudeloop_local": True})

    assert settings.enabled_engines == (
        EngineId.GPTOSSLOOP,
        EngineId.QWENLOOP,
        EngineId.CLAUDELOOP_LOCAL,
    )
    assert settings.any_enabled is True


def test_only_a_real_boolean_counts_in_the_config() -> None:
    """A value that is not a boolean leaves each engine at its default, as no key does."""
    assert _settings(features={"claudeloop_local": "true"}).enabled_engines == (
        EngineId.GPTOSSLOOP,
    )
    assert _settings(features={"gptossloop": "false"}).enabled_engines == (EngineId.GPTOSSLOOP,)
    assert _settings(features="qwenloop").enabled_engines == (EngineId.GPTOSSLOOP,)


def test_a_qwenloop_switch_is_told_what_it_now_means() -> None:
    """ADR-0060: an operator who switched qwenloop on for gpt-oss hears it is Qwen now."""
    assert _settings().notices == ()
    assert _settings({QWEN_SWITCH: "1"}).notices == (QWENLOOP_SWITCH_NOTICE,)
    assert _settings(features={"qwenloop": True}).notices == (QWENLOOP_SWITCH_NOTICE,)
    assert "gptossloop" in QWENLOOP_SWITCH_NOTICE


@pytest.mark.parametrize(
    "value, expected",
    [("1", True), ("true", True), (" YES ", True), ("on", True), ("0", False), ("nope", False)],
)
def test_the_environment_wins_whenever_it_is_set(value: str, expected: bool) -> None:
    on_in_config = _settings(
        {CLAUDE_LOCAL_SWITCH: value}, features={"claudeloop_local": not expected}
    )

    assert on_in_config.enabled(EngineId.CLAUDELOOP_LOCAL) is expected


def test_each_local_engine_is_switched_by_its_own_variable_and_a_paid_one_by_none() -> None:
    settings = _settings()

    assert settings.switch_for(EngineId.GPTOSSLOOP) == GPTOSS_SWITCH
    assert settings.switch_for(EngineId.QWENLOOP) == QWEN_SWITCH
    assert settings.switch_for(EngineId.CLAUDELOOP_LOCAL) == CLAUDE_LOCAL_SWITCH
    assert settings.switch_for(EngineId.CLAUDELOOP) is None


def test_a_paid_engine_has_no_switch_and_is_never_a_local_one() -> None:
    assert _settings({QWEN_SWITCH: "1"}).enabled(EngineId.CLAUDELOOP) is False


def test_doctor_reads_vibey_toml_under_the_environment(tmp_path: Path) -> None:
    toml = tmp_path / "vibey.toml"
    none = {GPTOSS_SWITCH: "0"}
    assert LocalEngineSettings.from_toml(toml, environ=none).enabled_engines == ()  # no file

    toml.write_text("[features]\nclaudeloop_local = true\n", encoding="utf-8")
    assert LocalEngineSettings.from_toml(toml, environ=none).enabled_engines == (
        EngineId.CLAUDELOOP_LOCAL,
    )
    off = LocalEngineSettings.from_toml(toml, environ={**none, CLAUDE_LOCAL_SWITCH: "0"})
    assert off.enabled_engines == ()

    # A malformed file reads as "every switch at its default" rather than crashing a
    # health check, and the environment still decides.
    toml.write_text("this is not toml {{{", encoding="utf-8")
    assert LocalEngineSettings.from_toml(toml, environ={}).enabled_engines == (EngineId.GPTOSSLOOP,)
    assert LocalEngineSettings.from_toml(
        toml, environ={**none, QWEN_SWITCH: "1"}
    ).enabled_engines == (EngineId.QWENLOOP,)


# ── claudeloop-local's configuration ──────────────────────────────────────────


def test_claudeloop_local_defaults_to_the_local_profile() -> None:
    config = _settings().claudeloop_local

    assert (config.profile, config.context_window, config.structured_verdict) == (
        "local",
        32_768,
        False,
    )


def test_claudeloop_local_reads_its_engines_table() -> None:
    settings = _settings(engines={"claudeloop_local": {"profile": "gpu", "context_window": 65_536}})

    assert settings.claudeloop_local.profile == "gpu"
    assert settings.claudeloop_local.context_window == 65_536


def test_the_profile_environment_override_wins_and_a_blank_one_does_not() -> None:
    table = {"engines": {"claudeloop_local": {"profile": "gpu"}}}

    overridden = LocalEngineSettings(
        environ={"VIBEY_CLAUDELOOP_LOCAL_PROFILE": " laptop "}, config=table
    )
    blank = LocalEngineSettings(environ={"VIBEY_CLAUDELOOP_LOCAL_PROFILE": "  "}, config=table)

    assert overridden.claudeloop_local.profile == "laptop"
    assert blank.claudeloop_local.profile == "gpu"


def test_an_allow_list_shaped_engines_key_configures_nothing() -> None:
    """The Kubernetes operator stores `engines` as the CR's allow-list, a list."""
    assert _settings(engines=["claudeloop", "claudeloop-local"]).claudeloop_local.profile == (
        "local"
    )


def test_a_claudeloop_local_key_that_is_not_a_table_is_refused() -> None:
    with pytest.raises(ConfigError, match="must be a table"):
        _ = _settings(engines={"claudeloop_local": "gpu"}).claudeloop_local


def test_an_invalid_claudeloop_local_table_is_refused_loudly() -> None:
    with pytest.raises(ConfigError, match="context_window"):
        _ = _settings(engines={"claudeloop_local": {"context_window": -1}}).claudeloop_local


# ── descriptors and adapters ─────────────────────────────────────────────────


def test_claudeloop_local_is_built_from_the_configured_profile_others_are_static() -> None:
    settings = _settings(engines={"claudeloop_local": {"profile": "gpu"}})

    assert settings.descriptor(EngineId.CLAUDELOOP_LOCAL).doctor_args == ("--profile", "gpu")
    assert settings.descriptor(EngineId.QWENLOOP) is QWENLOOP
    assert settings.descriptor(EngineId.GPTOSSLOOP) is GPTOSSLOOP
    assert settings.descriptor(EngineId.CLAUDELOOP) is CLAUDELOOP


def test_descriptors_are_only_the_enabled_local_engines() -> None:
    settings = _settings({CLAUDE_LOCAL_SWITCH: "1"})

    assert [d.engine_id for d in settings.descriptors()] == [
        EngineId.GPTOSSLOOP,
        EngineId.CLAUDELOOP_LOCAL,
    ]


class _Overlay:
    def overlay_for(self, engine_id: EngineId) -> dict[str, str]:
        return {"FOR": engine_id.value}


def test_every_enabled_engine_gets_an_adapter_carrying_its_overlay() -> None:
    settings = _settings(features={"qwenloop": True, "claudeloop_local": True})

    adapters = settings.adapters(_Overlay())

    assert set(adapters) == {EngineId.GPTOSSLOOP, EngineId.QWENLOOP, EngineId.CLAUDELOOP_LOCAL}
    qwen = adapters[EngineId.QWENLOOP]
    assert isinstance(qwen, LoopProcessAdapter)
    assert qwen.env_overlay == {"FOR": "qwenloop"}
    assert adapters[EngineId.CLAUDELOOP_LOCAL].descriptor.doctor_args == ("--profile", "local")


def test_a_paid_engine_adapter_is_the_plain_one() -> None:
    adapter = _settings().adapter(EngineId.CLAUDELOOP, LocalEndpointEnvironment({}))

    assert isinstance(adapter, LoopProcessAdapter)
    assert adapter.descriptor is CLAUDELOOP
    assert adapter.env_overlay == {}


def test_both_classes_satisfy_their_declared_seams() -> None:
    assert isinstance(_settings(), LocalEngineSettingsInterface)
    assert isinstance(LocalEndpointEnvironment({}), LocalEndpointEnvironmentInterface)


# ── the one local endpoint setting ────────────────────────────────────────────


@pytest.mark.parametrize("engine_id", [EngineId.GPTOSSLOOP, EngineId.QWENLOOP])
def test_without_vibey_ollama_url_a_runner_keeps_its_own_backend_selection(
    engine_id: EngineId,
) -> None:
    assert LocalEndpointEnvironment({}).overlay_for(engine_id) == {}
    assert LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": ""}).overlay_for(engine_id) == {}


def test_each_runner_reads_its_own_endpoint_variables() -> None:
    assert all(isinstance(v, LocalRunnerVariablesInterface) for v in RUNNER_VARIABLES.values())
    assert {e: (v.base_url, v.model) for e, v in RUNNER_VARIABLES.items()} == {
        EngineId.GPTOSSLOOP: ("GPTOSSLOOP_BASE_URL", "GPTOSSLOOP_MODEL"),
        EngineId.QWENLOOP: ("QWENLOOP_BASE_URL", "QWENLOOP_MODEL"),
    }


def test_vibey_ollama_url_becomes_each_runners_openai_compat_endpoint() -> None:
    """gptossloop gets the endpoint and this era's default model; qwenloop gets only the
    endpoint, and runs the Qwen model it names itself (ADR-0060)."""
    endpoint = LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": "http://10.0.0.5:11434/"})

    assert endpoint.overlay_for(EngineId.GPTOSSLOOP) == {
        "GPTOSSLOOP_BASE_URL": "http://10.0.0.5:11434/v1",
        "GPTOSSLOOP_MODEL": "gpt-oss:20b",
    }
    assert endpoint.overlay_for(EngineId.QWENLOOP) == {
        "QWENLOOP_BASE_URL": "http://10.0.0.5:11434/v1",
    }


def test_the_model_follows_vibey_ollama_model_then_the_cli_option() -> None:
    environ = {"VIBEY_OLLAMA_URL": "http://127.0.0.1:11434", "VIBEY_OLLAMA_MODEL": "qwen3:14b"}

    overlay = LocalEndpointEnvironment(environ).overlay_for(EngineId.GPTOSSLOOP)
    assert overlay["GPTOSSLOOP_MODEL"] == "qwen3:14b"
    chosen = LocalEndpointEnvironment(environ, model="gpt-oss:20b")
    assert chosen.overlay_for(EngineId.GPTOSSLOOP)["GPTOSSLOOP_MODEL"] == "gpt-oss:20b"
    assert "QWENLOOP_MODEL" not in chosen.overlay_for(EngineId.QWENLOOP)


def test_what_the_operator_set_for_a_runner_directly_is_kept() -> None:
    environ = {
        "VIBEY_OLLAMA_URL": "http://127.0.0.1:11434",
        "GPTOSSLOOP_BASE_URL": "http://gpu-box:8000/v1",
        "QWENLOOP_BASE_URL": "http://qwen-box:8000/v1",
    }

    assert LocalEndpointEnvironment(environ).overlay_for(EngineId.GPTOSSLOOP) == {
        "GPTOSSLOOP_MODEL": "gpt-oss:20b"
    }
    assert LocalEndpointEnvironment(environ).overlay_for(EngineId.QWENLOOP) == {}


def test_claudeloop_local_takes_its_endpoint_from_its_profile_not_from_here() -> None:
    endpoint = LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": "http://127.0.0.1:11434"})

    assert endpoint.overlay_for(EngineId.CLAUDELOOP_LOCAL) == {}
    assert endpoint.overlay_for(EngineId.CLAUDELOOP) == {}


def test_a_non_http_endpoint_is_refused_by_the_same_rule_design_uses() -> None:
    endpoint = LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": "file:///etc/passwd"})

    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_URL"):
        endpoint.overlay_for(EngineId.GPTOSSLOOP)


# -- the model `vibey loops` reports for a local runner --------------------------------------
#
# It mirrors `overlay_for`, because that is the only path by which vibey's model reaches a
# runner's session (contract amendment 4): the runner's own model variable when set, else
# vibey's model -- gptossloop only, and only while VIBEY_OLLAMA_URL is set -- else nothing,
# and the runner's own configuration chooses.

URL = {"VIBEY_OLLAMA_URL": "http://127.0.0.1:11434"}


def test_only_gptossloops_model_is_one_vibey_chooses() -> None:
    endpoint = LocalEndpointEnvironment({**URL, "VIBEY_OLLAMA_MODEL": "qwen3-coder"})
    for engine_id in EngineId:
        if engine_id is not EngineId.GPTOSSLOOP:
            assert endpoint.model_for(engine_id) is None, engine_id


def test_without_the_endpoint_setting_vibey_hands_gptossloop_no_model() -> None:
    """VIBEY_OLLAMA_MODEL alone never reaches gptossloop: nothing renders it into
    GPTOSSLOOP_MODEL unless VIBEY_OLLAMA_URL is set."""
    assert LocalEndpointEnvironment({}).model_for(EngineId.GPTOSSLOOP) is None
    lone = LocalEndpointEnvironment({"VIBEY_OLLAMA_MODEL": "qwen3-coder"}, model="gemma3:27b")
    assert lone.model_for(EngineId.GPTOSSLOOP) is None
    empty = LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": ""})
    assert empty.model_for(EngineId.GPTOSSLOOP) is None


def test_with_the_endpoint_setting_gptossloops_model_is_the_one_the_overlay_hands_it() -> None:
    assert LocalEndpointEnvironment(URL).model_for(EngineId.GPTOSSLOOP) == "gpt-oss:20b"
    environ = {**URL, "VIBEY_OLLAMA_MODEL": "qwen3-coder"}
    assert LocalEndpointEnvironment(environ).model_for(EngineId.GPTOSSLOOP) == "qwen3-coder"
    chosen = LocalEndpointEnvironment(environ, model="gemma3:27b")
    assert chosen.model_for(EngineId.GPTOSSLOOP) == "gemma3:27b"


@pytest.mark.parametrize(
    ("engine_id", "variable"),
    [(EngineId.GPTOSSLOOP, "GPTOSSLOOP_MODEL"), (EngineId.QWENLOOP, "QWENLOOP_MODEL")],
)
def test_a_model_the_operator_gave_a_runner_itself_wins(engine_id: EngineId, variable: str) -> None:
    """The runner's own model variable reaches it through its own passthrough, and the
    overlay never replaces it, so it is the model the runner runs -- with or without the
    endpoint setting."""
    named = {variable: "llama3.3", "VIBEY_OLLAMA_MODEL": "qwen3-coder"}
    assert LocalEndpointEnvironment(named).model_for(engine_id) == "llama3.3"
    assert LocalEndpointEnvironment({**URL, **named}).model_for(engine_id) == "llama3.3"


def test_a_blank_model_variable_is_ignored_and_never_replaced() -> None:
    """A runner ignores a blank model variable, and the overlay does not replace a variable
    that is set, so neither name reaches it: the runner's own configuration chooses."""
    blank = {"GPTOSSLOOP_MODEL": "  ", "VIBEY_OLLAMA_MODEL": "qwen3-coder"}
    assert LocalEndpointEnvironment(blank).model_for(EngineId.GPTOSSLOOP) is None
    assert LocalEndpointEnvironment({**URL, **blank}).model_for(EngineId.GPTOSSLOOP) is None


def test_a_malformed_endpoint_is_refused_even_when_a_runner_names_its_own_model() -> None:
    """The worker resolves the overlay before it starts a runner, so a malformed setting
    stops it whatever its model variable says; `vibey loops` refuses it the same way."""
    environ = {"VIBEY_OLLAMA_URL": "ftp://nowhere", "QWENLOOP_MODEL": "llama3.3"}

    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_URL"):
        LocalEndpointEnvironment(environ).model_for(EngineId.QWENLOOP)
