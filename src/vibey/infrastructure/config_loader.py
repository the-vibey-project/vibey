# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import os
from pathlib import Path

from vibey.domain.config import VibeyConfig, parse_config, parse_toml_string
from vibey.infrastructure.engines.local_engines import LOCAL_ENGINE_SWITCHES


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
