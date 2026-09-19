# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where qwenloop's settings come from: a TOML file, the environment, and flags."""

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

from platformdirs import user_config_path

from qwenloop.domain.config import QwenConfig, QwenConfigParser
from qwenloop.domain.interfaces import QwenConfigParserInterface

#: Points qwenloop at a config file. Unset: `<user config dir>/qwenloop/config.toml`.
ENV_CONFIG = "QWENLOOP_CONFIG"
#: The OpenAI-compatible base URL to attach to (`base_url`), `/v1` included.
ENV_BASE_URL = "QWENLOOP_BASE_URL"
#: The model name the endpoint serves (`model`).
ENV_MODEL = "QWENLOOP_MODEL"
#: The endpoint's API key. Environment only: a secret belongs neither in a config file
#: nor on a command line, where `ps` would show it to every user on the machine.
ENV_API_KEY = "QWENLOOP_API_KEY"


class SettingsLoader:
    """Layers settings in precedence order: config file, then environment, then flags.

    A missing default config file is an empty layer, so qwenloop runs with no file at all.
    A file named by `QWENLOOP_CONFIG` that does not exist, or any file that does not parse,
    is an error: an operator who pointed at a file meant it to be read.
    """

    ENVIRONMENT_KEYS: ClassVar[Mapping[str, str]] = {ENV_BASE_URL: "base_url", ENV_MODEL: "model"}

    def __init__(
        self,
        environ: Mapping[str, str],
        *,
        parser: QwenConfigParserInterface | None = None,
        default_path: Path | None = None,
    ) -> None:
        self._environ = environ
        self._parser = parser or QwenConfigParser()
        self._default_path = default_path or user_config_path("qwenloop") / "config.toml"

    @property
    def path(self) -> Path:
        configured = self._environ.get(ENV_CONFIG, "").strip()
        return Path(configured).expanduser() if configured else self._default_path

    @property
    def api_key(self) -> str:
        return self._environ.get(ENV_API_KEY, "").strip()

    def load(self, overrides: Mapping[str, object | None] | None = None) -> QwenConfig:
        layered: dict[str, Any] = self._file_layer()
        for variable, key in self.ENVIRONMENT_KEYS.items():
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
            if self._environ.get(ENV_CONFIG, "").strip():
                raise ValueError(f"{ENV_CONFIG} names {path}, which does not exist")
            return {}
        try:
            with path.open("rb") as stream:
                return tomllib.load(stream)
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"{path} is not valid TOML: {exc}") from exc
