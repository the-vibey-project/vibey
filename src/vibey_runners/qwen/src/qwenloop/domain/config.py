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
#: This era's default free model (sub-doctrine 8.d): GPT-OSS 20B, under the name Ollama
#: gives it. The pinned llama.cpp profiles are a separate choice and keep their own model.
DEFAULT_ENDPOINT_MODEL = "gpt-oss:20b"


#: Directories no search or find descends into unless the operator says otherwise:
#: version-control internals, virtual environments, dependency trees, tool caches, and
#: qwenloop's own run records.
DEFAULT_SKIP_DIRS: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".qwenloop",
)


@dataclass(frozen=True, slots=True)
class ToolLimits:
    """How much any one tool call may read or return. Declared here with defaults and
    overridable from the config file's `[tools]` table (sub-doctrine 12.h). A limit the
    model passes in a call may narrow these, never widen them."""

    # read_file / open_file: characters of file content one call returns.
    max_read_chars: int = 200_000
    # search: matching lines one call returns.
    max_search_matches: int = 100
    # find: file paths one call returns.
    max_find_results: int = 200
    # search: characters kept of any one matching line.
    max_line_chars: int = 240
    # search: a file larger than this is skipped rather than read.
    max_file_bytes: int = 2_000_000
    # search / find: directory names never descended into.
    skip_dirs: tuple[str, ...] = DEFAULT_SKIP_DIRS


_TOOL_LIMIT_KEYS = frozenset(item.name for item in fields(ToolLimits))


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
    # What one tool call may read or return: the config file's `[tools]` table.
    tools: ToolLimits = ToolLimits()

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
            tools=self._tool_limits(data.get("tools", {})),
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
    def _tool_limits(data: object) -> ToolLimits:
        """The `[tools]` table: every bound a positive integer, `skip_dirs` a list of names.
        An unknown key is refused for the same reason as at the top level."""
        if not isinstance(data, Mapping):
            raise ValueError("tools must be a table of tool limits")
        unknown = sorted(set(data) - _TOOL_LIMIT_KEYS)
        if unknown:
            raise ValueError(f"unknown qwenloop tools key(s): {', '.join(unknown)}")
        defaults = ToolLimits()
        bounds = {
            item.name: int(data.get(item.name, getattr(defaults, item.name)))
            for item in fields(ToolLimits)
            if item.name != "skip_dirs"
        }
        for name, value in bounds.items():
            if value <= 0:
                raise ValueError(f"tools.{name} must be positive")
        skip_dirs = data.get("skip_dirs", defaults.skip_dirs)
        if not isinstance(skip_dirs, list | tuple) or not all(
            isinstance(item, str) and item for item in skip_dirs
        ):
            raise ValueError("tools.skip_dirs must be a list of directory names")
        return ToolLimits(**bounds, skip_dirs=tuple(skip_dirs))

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
