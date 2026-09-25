# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The local engines: which are switched on, how each is configured, and where they run.

Sub-doctrine 8.a makes the sovereign path the preference, and ADR-0038 makes the
selector act on it. That only works if every place that asks "which local engines
exist here?" gets one answer, so this module is the one resolver: the composition
root, `vibey worker`, `vibey work` and `vibey doctor` all read it rather than each
keeping a copy of the precedence rule (two copies of it is how `doctor` once could
not see the engine the worker was running).

- `LocalEngineSettings` answers from the environment first, then the project's
  config: `VIBEY_FEATURE_<KEY>` whenever it is set at all, else `[features] <key>`,
  else the engine's own default -- on for gptossloop, the sovereign default, and off
  for every other local engine (ADR-0060).
- `LocalEndpointEnvironment` turns the one operator setting, `VIBEY_OLLAMA_URL`, into
  the variables each local engine's own process reads.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from vibey.application.ports import EngineAdapter
from vibey.domain.config import (
    LOCAL_ENGINE_FEATURES,
    LOCAL_ENGINES_ON_BY_DEFAULT,
    ClaudeloopLocalConfig,
    ConfigError,
    parse_toml_string,
)
from vibey.domain.engine import EngineDescriptor, EngineId
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID, ClaudeloopLocalDescriptors
from vibey.infrastructure.engines.interfaces.descriptors_interface import (
    ClaudeloopLocalDescriptorsInterface,
)
from vibey.infrastructure.engines.interfaces.local_engines_interface import (
    LocalEndpointEnvironmentInterface,
)
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter
from vibey.infrastructure.engines.ollama_chat import OLLAMA_URL_ENV, OllamaChatClient

#: The values that switch a feature on. Any other value that is set switches it off.
TRUTHY = frozenset({"1", "true", "yes", "on"})
#: Overrides `[engines.claudeloop_local] profile` when set and non-empty.
CLAUDELOOP_LOCAL_PROFILE_ENV = "VIBEY_CLAUDELOOP_LOCAL_PROFILE"
#: What each local runner's openai-compat backend reads (its own settings, #243): the
#: one runner package reads `GPTOSSLOOP_*` as gptossloop and `QWENLOOP_*` as qwenloop.
GPTOSSLOOP_BASE_URL_ENV = "GPTOSSLOOP_BASE_URL"
GPTOSSLOOP_MODEL_ENV = "GPTOSSLOOP_MODEL"
QWENLOOP_BASE_URL_ENV = "QWENLOOP_BASE_URL"
QWENLOOP_MODEL_ENV = "QWENLOOP_MODEL"


@dataclass(frozen=True, slots=True)
class LocalRunnerVariables:
    """The two variables one local runner reads for its endpoint: its base URL and model."""

    base_url: str
    model: str


#: The local engines vibey hands an endpoint, and the variables each reads for it.
RUNNER_VARIABLES: dict[EngineId, LocalRunnerVariables] = {
    EngineId.GPTOSSLOOP: LocalRunnerVariables(GPTOSSLOOP_BASE_URL_ENV, GPTOSSLOOP_MODEL_ENV),
    EngineId.QWENLOOP: LocalRunnerVariables(QWENLOOP_BASE_URL_ENV, QWENLOOP_MODEL_ENV),
}
#: The local engines vibey also hands a model: the one that runs this era's default
#: model (`VIBEY_OLLAMA_MODEL`, 8.d). qwenloop runs the Qwen model it names itself, so
#: vibey hands it only the endpoint (ADR-0060).
HANDED_A_MODEL = frozenset({EngineId.GPTOSSLOOP})


@dataclass(frozen=True, slots=True)
class LocalEngineSwitch:
    """One local engine's feature switch: a `[features]` key, its environment name, and
    whether the engine is on when neither sets it (ADR-0060)."""

    engine_id: EngineId
    feature_key: str
    on_by_default: bool = False

    @property
    def env_var(self) -> str:
        return f"VIBEY_FEATURE_{self.feature_key.upper()}"


#: Every local engine, in the order the rest of the tree lists them. The feature keys
#: and defaults come from the domain's own tables, so the config schema and this
#: resolver cannot name a switch, or its default, differently.
LOCAL_ENGINE_SWITCHES: tuple[LocalEngineSwitch, ...] = tuple(
    LocalEngineSwitch(EngineId(engine), key, engine in LOCAL_ENGINES_ON_BY_DEFAULT)
    for engine, key in LOCAL_ENGINE_FEATURES.items()
)
#: What an operator who switched qwenloop on before ADR-0060 needs to hear: the switch
#: they set now means something else.
QWENLOOP_SWITCH_NOTICE = (
    "qwenloop is switched on, and since ADR-0060 it runs a Qwen model (qwen3:14b unless "
    "QWENLOOP_MODEL names another). The gpt-oss engine qwenloop used to be is gptossloop, "
    "on by default: drop VIBEY_FEATURE_QWENLOOP / [features] qwenloop unless you want "
    "Qwen as well."
)


class LocalEngineSettings:
    """Which local engines are switched on for one project, and how each is configured.

    Declared by `interfaces/local_engines_interface.py`. `config` is the project's
    configuration as a plain mapping: the stored project record for the worker and
    `vibey work`, the parsed `./vibey.toml` for `vibey doctor`.
    """

    def __init__(
        self,
        *,
        environ: Mapping[str, str],
        config: Mapping[str, object],
        descriptors: ClaudeloopLocalDescriptorsInterface | None = None,
    ) -> None:
        self._environ = environ
        self._config = config
        self._descriptors = descriptors if descriptors is not None else ClaudeloopLocalDescriptors()
        self._switches = {switch.engine_id: switch for switch in LOCAL_ENGINE_SWITCHES}

    @classmethod
    def from_toml(cls, path: Path, *, environ: Mapping[str, str]) -> "LocalEngineSettings":
        """The settings `vibey doctor` reads: a missing or malformed file is an empty
        config, so a broken `vibey.toml` reports every switch off rather than crashing a
        health check -- and the environment still decides, as everywhere else."""
        try:
            data: Mapping[str, object] = parse_toml_string(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        return cls(environ=environ, config=data)

    def switch_for(self, engine_id: EngineId) -> str | None:
        """The variable that switches `engine_id` on, or None for an engine with no switch."""
        switch = self._switches.get(engine_id)
        return None if switch is None else switch.env_var

    def on_by_default(self, engine_id: EngineId) -> bool:
        """Whether `engine_id` is on when neither its variable nor `[features]` sets it."""
        switch = self._switches.get(engine_id)
        return switch is not None and switch.on_by_default

    def enabled(self, engine_id: EngineId) -> bool:
        switch = self._switches.get(engine_id)
        if switch is None:
            return False
        override = self._environ.get(switch.env_var)
        if override is not None:
            return override.strip().lower() in TRUTHY
        features = self._config.get("features")
        value = features.get(switch.feature_key) if isinstance(features, Mapping) else None
        # Only a boolean decides; anything else leaves the engine at its default, as an
        # absent key does. An on-by-default engine is switched off only by saying so.
        return value if isinstance(value, bool) else switch.on_by_default

    @property
    def notices(self) -> tuple[str, ...]:
        """What the operator should hear about how their switches now read (ADR-0060)."""
        return (QWENLOOP_SWITCH_NOTICE,) if self.enabled(EngineId.QWENLOOP) else ()

    @property
    def enabled_engines(self) -> tuple[EngineId, ...]:
        return tuple(s.engine_id for s in LOCAL_ENGINE_SWITCHES if self.enabled(s.engine_id))

    @property
    def any_enabled(self) -> bool:
        return bool(self.enabled_engines)

    @property
    def claudeloop_local(self) -> ClaudeloopLocalConfig:
        """`[engines.claudeloop_local]`, validated, with the profile's environment override.

        The worker's project record may carry `engines` as the operator's allow-list (a
        list, from the Kubernetes CR); only a table can configure an engine, so any other
        shape is read as "not configured" rather than refused.
        """
        engines = self._config.get("engines")
        raw = engines.get("claudeloop_local") if isinstance(engines, Mapping) else None
        if raw is not None and not isinstance(raw, Mapping):
            raise ConfigError("engines.claudeloop_local", "must be a table")
        table = dict(raw) if raw is not None else {}
        parsed = ClaudeloopLocalConfig.from_table(table, "engines.claudeloop_local")
        profile = (self._environ.get(CLAUDELOOP_LOCAL_PROFILE_ENV) or "").strip()
        return replace(parsed, profile=profile) if profile else parsed

    def descriptor(self, engine_id: EngineId) -> EngineDescriptor:
        """The descriptor this project runs `engine_id` with: claudeloop-local is built
        from its configured profile, every other engine is its static descriptor."""
        if engine_id is EngineId.CLAUDELOOP_LOCAL:
            return self._descriptors.build(self.claudeloop_local)
        return BY_ENGINE_ID[engine_id]

    def descriptors(self) -> tuple[EngineDescriptor, ...]:
        return tuple(self.descriptor(engine_id) for engine_id in self.enabled_engines)

    def adapter(
        self, engine_id: EngineId, endpoint: LocalEndpointEnvironmentInterface
    ) -> EngineAdapter:
        return LoopProcessAdapter(
            descriptor=self.descriptor(engine_id), env_overlay=endpoint.overlay_for(engine_id)
        )

    def adapters(
        self, endpoint: LocalEndpointEnvironmentInterface
    ) -> dict[EngineId, EngineAdapter]:
        """An adapter for every local engine switched on, each with its endpoint overlay."""
        return {engine_id: self.adapter(engine_id, endpoint) for engine_id in self.enabled_engines}


class LocalEndpointEnvironment:
    """`VIBEY_OLLAMA_URL`, the one operator setting, in each local engine's own terms.

    Declared by `interfaces/local_engines_interface.py`. The DESIGN and DECOMPOSE
    providers already read `VIBEY_OLLAMA_URL` / `VIBEY_OLLAMA_MODEL` through
    `OllamaChatClient`; this reads the same two through the same client -- so the URL is
    validated by the same rule and defaults the same way -- and hands each local runner
    its own names for them (ADR-0060):

    - gptossloop: `GPTOSSLOOP_BASE_URL` = `<VIBEY_OLLAMA_URL>/v1`, and `GPTOSSLOOP_MODEL`
      = `--ollama-model`, else `VIBEY_OLLAMA_MODEL`, else the default -- the providers'
      model, so BUILD and DESIGN run the same one;
    - qwenloop: `QWENLOOP_BASE_URL` only. It runs the Qwen model it names itself, and
      this era's default model is not one.

    Each is derived only when `VIBEY_OLLAMA_URL` is set and the target is not already
    set: an operator who configured a runner directly keeps what they configured, and
    one who configured nothing keeps the runner's own backend selection.
    claudeloop-local gets nothing here -- its endpoint is its claudeloop profile's
    `base_url`.
    """

    def __init__(self, environ: Mapping[str, str], *, model: str | None = None) -> None:
        self._environ = environ
        self._model = model

    def model_for(self, engine_id: EngineId) -> str | None:
        """The model `engine_id` runs, when it reaches the engine by a path vibey knows.

        For a local runner, exactly as the model reaches it: its own model variable
        (`GPTOSSLOOP_MODEL`, `QWENLOOP_MODEL`) as the operator set it (the runner reads it
        and ignores a blank one, and the overlay never replaces it); else the model
        `overlay_for` hands it, which it does only for gptossloop and only when
        `VIBEY_OLLAMA_URL` is set; else None, and the runner's own configuration chooses.
        None for every other engine: a model named in its argv, or chosen by its own
        configuration, is not one vibey hands it.

        The overlay is resolved first, always: a malformed endpoint setting is refused here
        exactly as the worker refuses it, even when the model variable would name the model.
        """
        variables = RUNNER_VARIABLES.get(engine_id)
        if variables is None:
            return None
        handed = self.overlay_for(engine_id)
        named = (self._environ.get(variables.model) or "").strip()
        return named or handed.get(variables.model)

    def overlay_for(self, engine_id: EngineId) -> dict[str, str]:
        variables = RUNNER_VARIABLES.get(engine_id)
        if variables is None or not self._environ.get(OLLAMA_URL_ENV):
            return {}
        client = OllamaChatClient.from_environment(self._environ, model=self._model)
        derived = {variables.base_url: f"{client.base_url}/v1"}
        if engine_id in HANDED_A_MODEL:
            derived[variables.model] = client.model
        return {key: value for key, value in derived.items() if not self._environ.get(key)}


__all__ = [
    "CLAUDELOOP_LOCAL_PROFILE_ENV",
    "GPTOSSLOOP_BASE_URL_ENV",
    "GPTOSSLOOP_MODEL_ENV",
    "HANDED_A_MODEL",
    "LOCAL_ENGINE_SWITCHES",
    "QWENLOOP_BASE_URL_ENV",
    "QWENLOOP_MODEL_ENV",
    "QWENLOOP_SWITCH_NOTICE",
    "RUNNER_VARIABLES",
    "TRUTHY",
    "LocalEndpointEnvironment",
    "LocalEngineSettings",
    "LocalEngineSwitch",
    "LocalRunnerVariables",
]
