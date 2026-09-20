# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import os
from pathlib import Path

from vibey.domain.config import VibeyConfig, parse_config, parse_toml_string
from vibey.infrastructure.engines.local_engines import LOCAL_ENGINE_SWITCHES

RUNTIME_CONFIG_KEYS = ("notifications", "telemetry")


def load_config_from_path(path: Path) -> VibeyConfig:
    data = parse_toml_string(path.read_text())
    # Every local engine's environment switch overrides its `[features]` key -- the
    # same switches, from the same table, `LocalEngineSettings` reads for the worker.
    # Unlike that resolver, validation refuses a value that is not a boolean at all.
    for switch in LOCAL_ENGINE_SWITCHES:
        override = os.environ.get(switch.env_var)
        if override is None:
            continue
        normalized = override.strip().lower()
        if normalized not in {"0", "1", "false", "true", "no", "yes", "off", "on"}:
            raise ValueError(f"{switch.env_var} must be a boolean value")
        features = data.setdefault("features", {})
        if not isinstance(features, dict):
            raise ValueError("features must be a table")
        features[switch.feature_key] = normalized in {"1", "true", "yes", "on"}
    return parse_config(data)


def load_runtime_config_from_path(path: Path) -> dict[str, object]:
    """Load the opt-in runtime tables copied into a project's stored config.

    ``vibey new`` historically stores a small JSON config rather than the
    whole TOML document.  Keep that compatibility shape, but make the
    notification and telemetry tables in ``vibey.toml`` effective at runtime.
    A missing file is normal for projects created with CLI-only settings.
    Other TOML errors remain visible to the caller so an operator cannot
    believe a malformed configuration was accepted.
    """
    if not path.is_file():
        return {}
    data = parse_toml_string(path.read_text())
    return {key: value for key in RUNTIME_CONFIG_KEYS if isinstance((value := data.get(key)), dict)}
