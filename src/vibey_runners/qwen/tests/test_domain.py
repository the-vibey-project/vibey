# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from qwenloop.application.backend_selection import BackendChoice, BackendSelector, Hardware
from qwenloop.application.interfaces import BackendSelectorInterface
from qwenloop.domain.config import (
    DEFAULT_ENDPOINT_BASE_URL,
    DEFAULT_ENDPOINT_MODEL,
    DEFAULT_SKIP_DIRS,
    QwenConfig,
    QwenConfigParser,
    ToolLimits,
)
from qwenloop.domain.interfaces import QwenConfigInterface, QwenConfigParserInterface
from qwenloop.domain.model import (
    Backend,
    CapacityKind,
    RunStatus,
    ServerInfo,
    terminal_status,
)

parser = QwenConfigParser()
selector = BackendSelector()


def test_default_config() -> None:
    assert parser.parse({}) == QwenConfig()
    assert isinstance(parser, QwenConfigParserInterface)


def test_config_validation() -> None:
    with pytest.raises(ValueError):
        parser.parse({"max_turns": 0})
    with pytest.raises(ValueError):
        parser.parse({"idle_timeout_seconds": -1})
    with pytest.raises(ValueError):
        parser.parse({"backend": "unknown"})
    with pytest.raises(ValueError, match="positive"):
        parser.parse({"endpoint_timeout_seconds": 0})


def test_tool_limits_default_and_come_from_the_tools_table() -> None:
    default = parser.parse({})
    assert isinstance(default, QwenConfigInterface)
    assert default.tools == ToolLimits()
    assert default.tools.skip_dirs == DEFAULT_SKIP_DIRS
    assert ".git" in DEFAULT_SKIP_DIRS
    configured = parser.parse(
        {"tools": {"max_search_matches": 7, "max_read_chars": "50", "skip_dirs": ["vendor"]}}
    )
    assert configured.tools == ToolLimits(
        max_search_matches=7, max_read_chars=50, skip_dirs=("vendor",)
    )
    assert default.tools.search_timeout_seconds == 10.0
    timed = parser.parse({"tools": {"search_timeout_seconds": 2, "max_skipped_examples": 3}})
    assert (timed.tools.search_timeout_seconds, timed.tools.max_skipped_examples) == (2.0, 3)


@pytest.mark.parametrize(
    ("tools", "message"),
    [
        ("100", "tools must be a table"),
        ({"max_matches": 5}, "unknown qwenloop tools key\\(s\\): max_matches"),
        ({"max_find_results": 0}, "tools.max_find_results must be positive"),
        ({"max_line_chars": -1}, "tools.max_line_chars must be positive"),
        ({"skip_dirs": ".git"}, "tools.skip_dirs must be a list"),
        ({"skip_dirs": [".git", 3]}, "tools.skip_dirs must be a list"),
        ({"skip_dirs": [""]}, "tools.skip_dirs must be a list"),
        ({"max_skipped_examples": 0}, "tools.max_skipped_examples must be positive"),
        ({"search_timeout_seconds": 0}, "tools.search_timeout_seconds must be a positive"),
        ({"search_timeout_seconds": float("inf")}, "tools.search_timeout_seconds must be a"),
        ({"search_timeout_seconds": float("nan")}, "tools.search_timeout_seconds must be a"),
        ({"search_timeout_seconds": "soon"}, "tools.search_timeout_seconds must be a"),
    ],
)
def test_tool_limits_refuse_what_they_cannot_honour(tools: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parser.parse({"tools": tools})


def test_config_refuses_unknown_keys_instead_of_ignoring_them() -> None:
    with pytest.raises(ValueError, match="unknown qwenloop config key\\(s\\): api_key, base-url"):
        parser.parse({"base-url": "http://x/v1", "api_key": "secret"})


def test_endpoint_is_unconfigured_by_default_and_falls_back_to_ollama() -> None:
    config = parser.parse({})
    assert not config.endpoint_configured
    assert config.endpoint_url == DEFAULT_ENDPOINT_BASE_URL == "http://127.0.0.1:11434/v1"
    assert config.model == DEFAULT_ENDPOINT_MODEL == "gpt-oss:20b"


def test_endpoint_settings_are_parsed_and_normalised() -> None:
    config = parser.parse(
        {
            "backend": "openai-compat",
            "base_url": "  http://gpu-box:8000/v1/  ",
            "model": " qwen2.5-coder:1.5b ",
            "endpoint_timeout_seconds": 9,
        }
    )
    assert config.backend is Backend.OPENAI_COMPAT
    assert config.endpoint_configured
    assert config.base_url == config.endpoint_url == "http://gpu-box:8000/v1"
    assert config.model == "qwen2.5-coder:1.5b"
    assert config.endpoint_timeout_seconds == 9


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://host/v1", "127.0.0.1:11434/v1", "http://"]
)
def test_base_url_must_be_http_with_a_host(url: str) -> None:
    with pytest.raises(ValueError, match="base_url must be an http:// or https:// URL"):
        parser.parse({"base_url": url})


@pytest.mark.parametrize("url", ["http://u@host/v1"])
def test_base_url_must_not_embed_credentials(url: str) -> None:
    with pytest.raises(ValueError, match="must not include credentials"):
        parser.parse({"base_url": url})


def test_model_must_not_be_blank() -> None:
    with pytest.raises(ValueError, match="model must name"):
        parser.parse({"model": "   "})


def test_backend_auto_requires_linux_large_gpu_and_vllm() -> None:
    assert isinstance(selector, BackendSelectorInterface)
    assert (
        selector.select(
            Backend.AUTO, Hardware("Darwin"), vllm_installed=True, endpoint_configured=False
        ).backend
        is Backend.LLAMA_CPP
    )
    selected = selector.select(
        Backend.AUTO,
        Hardware("Linux", 40 * 1024**3),
        vllm_installed=True,
        endpoint_configured=False,
    )
    assert selected.backend is Backend.VLLM
    assert "40 GiB" in selected.reason
    assert (
        selector.select(
            Backend.VLLM, Hardware("Darwin"), vllm_installed=False, endpoint_configured=False
        ).backend
        is Backend.VLLM
    )


def test_vllm_threshold_is_configurable() -> None:
    small = BackendSelector(vllm_min_vram_bytes=24 * 1024**3)
    selected = small.select(
        Backend.AUTO,
        Hardware("Linux", 24 * 1024**3),
        vllm_installed=True,
        endpoint_configured=False,
    )
    assert selected.backend is Backend.VLLM
    assert "24 GiB" in selected.reason


def test_configured_endpoint_outranks_hardware_but_not_an_explicit_request() -> None:
    attached = selector.select(
        Backend.AUTO, Hardware("Linux", 80 * 1024**3), vllm_installed=True, endpoint_configured=True
    )
    assert attached.backend is Backend.OPENAI_COMPAT
    assert "endpoint is configured" in attached.reason
    explicit = selector.select(
        Backend.LLAMA_CPP, Hardware("Darwin"), vllm_installed=False, endpoint_configured=True
    )
    assert explicit.backend is Backend.LLAMA_CPP
    requested = selector.select(
        Backend.OPENAI_COMPAT, Hardware("Darwin"), vllm_installed=False, endpoint_configured=False
    )
    assert requested.backend is Backend.OPENAI_COMPAT


def test_server_info_keeps_the_token_out_of_its_repr() -> None:
    info = ServerInfo(Backend.OPENAI_COMPAT, "m", "http://x/v1", False, True, token="sk-secret")
    assert "sk-secret" not in repr(info)
    assert info.model == ""


def test_capacity_outranks_completion() -> None:
    assert terminal_status(CapacityKind.LOCAL_BUSY, True) is RunStatus.FAILED
    assert terminal_status(CapacityKind.AVAILABLE, True) is RunStatus.COMPLETED
    assert terminal_status(CapacityKind.AVAILABLE, False) is RunStatus.RUNNING


def test_a_running_local_ollama_is_the_default_backend_when_nothing_is_configured() -> None:
    linux_gpu = Hardware("Linux", nvidia_vram_bytes=80 * 1024**3)
    chosen = selector.select(
        Backend.AUTO,
        linux_gpu,
        vllm_installed=True,
        endpoint_configured=False,
        ollama_available=True,
    )
    assert chosen == BackendChoice(
        Backend.OPENAI_COMPAT, "a local Ollama is running: the default backend"
    )
    # an explicit backend and a configured endpoint still decide first
    assert (
        selector.select(
            Backend.LLAMA_CPP,
            linux_gpu,
            vllm_installed=True,
            endpoint_configured=False,
            ollama_available=True,
        ).reason
        == "explicit configuration"
    )
    assert (
        selector.select(
            Backend.AUTO,
            linux_gpu,
            vllm_installed=True,
            endpoint_configured=True,
            ollama_available=True,
        ).reason
        == "an OpenAI-compatible endpoint is configured"
    )
    # without a running Ollama nothing changes
    assert (
        selector.select(
            Backend.AUTO, linux_gpu, vllm_installed=True, endpoint_configured=False
        ).backend
        is Backend.VLLM
    )
