# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one local-engine resolver, and the one local endpoint setting (ADR-0038)."""

from pathlib import Path

import pytest

from vibey.domain.config import ConfigError
from vibey.domain.engine import EngineId
from vibey.infrastructure.engines.descriptors import CLAUDELOOP, QWENLOOP
from vibey.infrastructure.engines.interfaces import (
    LocalEndpointEnvironmentInterface,
    LocalEngineSettingsInterface,
)
from vibey.infrastructure.engines.local_engines import (
    LOCAL_ENGINE_SWITCHES,
    LocalEndpointEnvironment,
    LocalEngineSettings,
)
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter

QWEN_SWITCH = "VIBEY_FEATURE_QWENLOOP"
CLAUDE_LOCAL_SWITCH = "VIBEY_FEATURE_CLAUDELOOP_LOCAL"


def _settings(environ: dict[str, str] | None = None, **config: object) -> LocalEngineSettings:
    return LocalEngineSettings(environ=environ or {}, config=config)


# ── switches ────────────────────────────────────────────────────────────────


def test_there_is_one_switch_per_local_engine_named_after_its_feature_key() -> None:
    assert [(s.engine_id, s.feature_key, s.env_var) for s in LOCAL_ENGINE_SWITCHES] == [
        (EngineId.QWENLOOP, "qwenloop", QWEN_SWITCH),
        (EngineId.CLAUDELOOP_LOCAL, "claudeloop_local", CLAUDE_LOCAL_SWITCH),
    ]


def test_everything_is_off_by_default() -> None:
    settings = _settings()

    assert settings.enabled_engines == ()
    assert settings.any_enabled is False


def test_the_features_table_switches_each_engine_on() -> None:
    settings = _settings(features={"qwenloop": True, "claudeloop_local": True})

    assert settings.enabled_engines == (EngineId.QWENLOOP, EngineId.CLAUDELOOP_LOCAL)
    assert settings.any_enabled is True


def test_only_a_real_true_counts_in_the_config() -> None:
    assert _settings(features={"claudeloop_local": "true"}).enabled_engines == ()
    assert _settings(features="qwenloop").enabled_engines == ()


@pytest.mark.parametrize(
    "value, expected",
    [("1", True), ("true", True), (" YES ", True), ("on", True), ("0", False), ("nope", False)],
)
def test_the_environment_wins_whenever_it_is_set(value: str, expected: bool) -> None:
    on_in_config = _settings(
        {CLAUDE_LOCAL_SWITCH: value}, features={"claudeloop_local": not expected}
    )

    assert on_in_config.enabled(EngineId.CLAUDELOOP_LOCAL) is expected


def test_a_paid_engine_has_no_switch_and_is_never_a_local_one() -> None:
    assert _settings({QWEN_SWITCH: "1"}).enabled(EngineId.CLAUDELOOP) is False


def test_doctor_reads_vibey_toml_under_the_environment(tmp_path: Path) -> None:
    toml = tmp_path / "vibey.toml"
    assert LocalEngineSettings.from_toml(toml, environ={}).enabled_engines == ()  # no file

    toml.write_text("[features]\nclaudeloop_local = true\n", encoding="utf-8")
    assert LocalEngineSettings.from_toml(toml, environ={}).enabled_engines == (
        EngineId.CLAUDELOOP_LOCAL,
    )
    off = LocalEngineSettings.from_toml(toml, environ={CLAUDE_LOCAL_SWITCH: "0"})
    assert off.enabled_engines == ()

    # A malformed file reads as "every switch off" rather than crashing a health check,
    # and the environment still decides.
    toml.write_text("this is not toml {{{", encoding="utf-8")
    assert LocalEngineSettings.from_toml(toml, environ={}).enabled_engines == ()
    assert LocalEngineSettings.from_toml(toml, environ={QWEN_SWITCH: "1"}).enabled_engines == (
        EngineId.QWENLOOP,
    )


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
    assert settings.descriptor(EngineId.CLAUDELOOP) is CLAUDELOOP


def test_descriptors_are_only_the_enabled_local_engines() -> None:
    settings = _settings({CLAUDE_LOCAL_SWITCH: "1"})

    assert [d.engine_id for d in settings.descriptors()] == [EngineId.CLAUDELOOP_LOCAL]


class _Overlay:
    def overlay_for(self, engine_id: EngineId) -> dict[str, str]:
        return {"FOR": engine_id.value}


def test_every_enabled_engine_gets_an_adapter_carrying_its_overlay() -> None:
    settings = _settings(features={"qwenloop": True, "claudeloop_local": True})

    adapters = settings.adapters(_Overlay())

    assert set(adapters) == {EngineId.QWENLOOP, EngineId.CLAUDELOOP_LOCAL}
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


def test_without_vibey_ollama_url_qwenloop_keeps_its_own_backend_selection() -> None:
    assert LocalEndpointEnvironment({}).overlay_for(EngineId.QWENLOOP) == {}
    assert LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": ""}).overlay_for(EngineId.QWENLOOP) == {}


def test_vibey_ollama_url_becomes_qwenloops_openai_compat_endpoint() -> None:
    endpoint = LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": "http://10.0.0.5:11434/"})

    assert endpoint.overlay_for(EngineId.QWENLOOP) == {
        "QWENLOOP_BASE_URL": "http://10.0.0.5:11434/v1",
        "QWENLOOP_MODEL": "gpt-oss:20b",
    }


def test_the_model_follows_vibey_ollama_model_then_the_cli_option() -> None:
    environ = {"VIBEY_OLLAMA_URL": "http://127.0.0.1:11434", "VIBEY_OLLAMA_MODEL": "qwen3:14b"}

    assert LocalEndpointEnvironment(environ).overlay_for(EngineId.QWENLOOP)["QWENLOOP_MODEL"] == (
        "qwen3:14b"
    )
    chosen = LocalEndpointEnvironment(environ, model="gpt-oss:20b")
    assert chosen.overlay_for(EngineId.QWENLOOP)["QWENLOOP_MODEL"] == "gpt-oss:20b"


def test_what_the_operator_set_for_qwenloop_directly_is_kept() -> None:
    environ = {
        "VIBEY_OLLAMA_URL": "http://127.0.0.1:11434",
        "QWENLOOP_BASE_URL": "http://gpu-box:8000/v1",
    }

    assert LocalEndpointEnvironment(environ).overlay_for(EngineId.QWENLOOP) == {
        "QWENLOOP_MODEL": "gpt-oss:20b"
    }


def test_claudeloop_local_takes_its_endpoint_from_its_profile_not_from_here() -> None:
    endpoint = LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": "http://127.0.0.1:11434"})

    assert endpoint.overlay_for(EngineId.CLAUDELOOP_LOCAL) == {}
    assert endpoint.overlay_for(EngineId.CLAUDELOOP) == {}


def test_a_non_http_endpoint_is_refused_by_the_same_rule_design_uses() -> None:
    endpoint = LocalEndpointEnvironment({"VIBEY_OLLAMA_URL": "file:///etc/passwd"})

    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_URL"):
        endpoint.overlay_for(EngineId.QWENLOOP)


# -- the model `vibey loops` reports for qwenloop --------------------------------------------


def test_only_qwenloops_model_is_one_vibey_chooses() -> None:
    endpoint = LocalEndpointEnvironment({"VIBEY_OLLAMA_MODEL": "qwen3-coder"})
    for engine_id in EngineId:
        if engine_id is not EngineId.QWENLOOP:
            assert endpoint.model_for(engine_id) is None, engine_id


def test_qwenloops_model_defaults_to_the_one_the_sovereign_providers_use() -> None:
    assert LocalEndpointEnvironment({}).model_for(EngineId.QWENLOOP) == "gpt-oss:20b"


def test_qwenloops_model_follows_vibey_ollama_model_and_ollama_model() -> None:
    environ = {"VIBEY_OLLAMA_MODEL": "qwen3-coder"}
    assert LocalEndpointEnvironment(environ).model_for(EngineId.QWENLOOP) == "qwen3-coder"
    chosen = LocalEndpointEnvironment(environ, model="gemma3:27b")
    assert chosen.model_for(EngineId.QWENLOOP) == "gemma3:27b"


def test_a_model_the_operator_gave_qwenloop_itself_wins() -> None:
    """QWENLOOP_MODEL reaches qwenloop through its own passthrough, and the overlay never
    replaces it, so it is the model qwenloop runs."""
    environ = {"QWENLOOP_MODEL": "llama3.3", "VIBEY_OLLAMA_MODEL": "qwen3-coder"}
    assert LocalEndpointEnvironment(environ).model_for(EngineId.QWENLOOP) == "llama3.3"
    blank = {"QWENLOOP_MODEL": "  ", "VIBEY_OLLAMA_MODEL": "qwen3-coder"}
    assert LocalEndpointEnvironment(blank).model_for(EngineId.QWENLOOP) == "qwen3-coder"
