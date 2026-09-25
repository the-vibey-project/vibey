# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where a runner's settings come from: a TOML file, the environment, and flags.

Each engine this package carries reads its own (ADR-0060): `gptossloop` reads
`GPTOSSLOOP_*` and `<user config dir>/gptossloop/config.toml`, `qwenloop` reads
`QWENLOOP_*` and `<user config dir>/qwenloop/config.toml`. Naming a model for one never
changes the model the other runs.
"""

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

from qwenloop.domain.config import QWENLOOP, QwenConfig, QwenConfigParser, RunnerIdentity
from qwenloop.domain.interfaces import QwenConfigParserInterface

#: qwenloop's own names, kept for the callers that import them. `RunnerIdentity` derives
#: the same names for any engine: `QWENLOOP.env_config` is `ENV_CONFIG`, and so on.
#: Points qwenloop at a config file. Unset: `<user config dir>/qwenloop/config.toml`.
ENV_CONFIG = QWENLOOP.env_config
#: The OpenAI-compatible base URL to attach to (`base_url`), `/v1` included.
ENV_BASE_URL = QWENLOOP.env_base_url
#: The model name the endpoint serves (`model`).
ENV_MODEL = QWENLOOP.env_model
#: The endpoint's API key. Environment only: a secret belongs neither in a config file
#: nor on a command line, where `ps` would show it to every user on the machine.
ENV_API_KEY = QWENLOOP.env_api_key


class SettingsLoader:
    """Layers settings in precedence order: config file, then environment, then flags.

    A missing default config file is an empty layer, so the runner runs with no file at
    all. A file named by `<PREFIX>_CONFIG` that does not exist, or any file that does not
    parse, is an error: an operator who pointed at a file meant it to be read.
    """

    def __init__(
        self,
        environ: Mapping[str, str],
        *,
        identity: RunnerIdentity = QWENLOOP,
        parser: QwenConfigParserInterface | None = None,
        default_path: Path | None = None,
    ) -> None:
        self._environ = environ
        self._identity = identity
        self._parser = parser or QwenConfigParser(default_model=identity.default_model)
        self._default_path = default_path or user_config_path(identity.name) / "config.toml"

    @property
    def environment_keys(self) -> Mapping[str, str]:
        """Each environment variable this engine reads, and the setting it fills."""
        return {self._identity.env_base_url: "base_url", self._identity.env_model: "model"}

    @property
    def path(self) -> Path:
        configured = self._environ.get(self._identity.env_config, "").strip()
        return Path(configured).expanduser() if configured else self._default_path

    @property
    def api_key(self) -> str:
        return self._environ.get(self._identity.env_api_key, "").strip()

    def load(self, overrides: Mapping[str, object | None] | None = None) -> QwenConfig:
        layered: dict[str, Any] = self._file_layer()
        for variable, key in self.environment_keys.items():
            value = self._environ.get(variable, "").strip()
            if value:
                layered[key] = value
        for key, override in (overrides or {}).items():
            if override is not None:
                layered[key] = override
        return self._parser.parse(layered)

    def _file_layer(self) -> dict[str, Any]:
        path = self.path
        if not path.exists():
            if self._environ.get(self._identity.env_config, "").strip():
                raise ValueError(f"{self._identity.env_config} names {path}, which does not exist")
            return {}
        try:
            with path.open("rb") as stream:
                return tomllib.load(stream)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"{path} is not valid TOML: {exc}") from exc
