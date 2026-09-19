# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure qwenloop configuration parsing."""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any
from urllib.parse import urlsplit

from qwenloop.domain.model import Backend

#: Where `--backend openai-compat` attaches when no `base_url` is configured: Ollama's
#: own default listen address, with the `/v1` prefix its OpenAI-compatible API lives under.
DEFAULT_ENDPOINT_BASE_URL = "http://127.0.0.1:11434/v1"
#: The same Qwen 2.5 Coder 14B the pinned profiles run, under the name Ollama gives it.
DEFAULT_ENDPOINT_MODEL = "qwen2.5-coder:14b"


@dataclass(frozen=True, slots=True)
class QwenConfig:
    backend: Backend = Backend.AUTO
    portable_profile: str = "qwen2.5-coder-14b-q5-k-m"
    nvidia_profile: str = "qwen2.5-coder-14b-bf16"
    idle_timeout_seconds: int = 900
    startup_timeout_seconds: int = 180
    context_window: int = 32_768
    max_turns: int = 40
    # The OpenAI-compatible base URL to attach to, `/v1` included. Empty means none is
    # configured, and `auto` selection then never picks the openai-compat backend.
    base_url: str = ""
    # The model name sent to an openai-compat endpoint. Managed servers ignore it.
    model: str = DEFAULT_ENDPOINT_MODEL
    # How long doctor, health, and start wait for an endpoint's model list.
    endpoint_timeout_seconds: int = 5

    @property
    def endpoint_configured(self) -> bool:
        """Whether an operator named an endpoint, rather than qwenloop assuming one."""
        return bool(self.base_url)

    @property
    def endpoint_url(self) -> str:
        """The base URL openai-compat attaches to: the configured one, else Ollama's default."""
        return self.base_url or DEFAULT_ENDPOINT_BASE_URL


_KEYS = frozenset(item.name for item in fields(QwenConfig))


class QwenConfigParser:
    """Validates one flat mapping of settings into a `QwenConfig`.

    The mapping is whatever the caller layered together (a config file, then environment,
    then flags); precedence is the caller's business, validity is this class's. An unknown
    key is refused rather than ignored, so a typo like `base-url` fails loudly instead of
    silently leaving the endpoint unconfigured.
    """

    def parse(self, data: Mapping[str, Any]) -> QwenConfig:
        unknown = sorted(set(data) - _KEYS)
        if unknown:
            raise ValueError(f"unknown qwenloop config key(s): {', '.join(unknown)}")
        defaults = QwenConfig()
        config = QwenConfig(
            backend=Backend(str(data.get("backend", defaults.backend.value))),
            portable_profile=str(data.get("portable_profile", defaults.portable_profile)),
            nvidia_profile=str(data.get("nvidia_profile", defaults.nvidia_profile)),
            idle_timeout_seconds=int(
                data.get("idle_timeout_seconds", defaults.idle_timeout_seconds)
            ),
            startup_timeout_seconds=int(
                data.get("startup_timeout_seconds", defaults.startup_timeout_seconds)
            ),
            context_window=int(data.get("context_window", defaults.context_window)),
            max_turns=int(data.get("max_turns", defaults.max_turns)),
            base_url=self._base_url(str(data.get("base_url", defaults.base_url))),
            model=str(data.get("model", defaults.model)).strip(),
            endpoint_timeout_seconds=int(
                data.get("endpoint_timeout_seconds", defaults.endpoint_timeout_seconds)
            ),
        )
        if config.idle_timeout_seconds < 0:
            raise ValueError("idle_timeout_seconds must be non-negative")
        if (
            config.startup_timeout_seconds <= 0
            or config.context_window <= 0
            or config.max_turns <= 0
            or config.endpoint_timeout_seconds <= 0
        ):
            raise ValueError("timeouts, context_window, and max_turns must be positive")
        if not config.model:
            raise ValueError("model must name the model the endpoint serves")
        return config

    @staticmethod
    def _base_url(value: str) -> str:
        """Normalise a base URL, refusing anything urllib could open that is not HTTP(S)."""
        text = value.strip().rstrip("/")
        if not text:
            return ""
        parts = urlsplit(text)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError(f"base_url must be an http:// or https:// URL, got {text!r}")
        if parts.username is not None or parts.password is not None:
            raise ValueError("base_url must not include credentials; use QWENLOOP_API_KEY")
        return text
