# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deterministic backend selection."""

from qwenloop.domain.model import Backend, BackendChoice, Hardware

__all__ = ["BackendChoice", "BackendSelector", "Hardware"]

#: The usable VRAM below which `auto` never picks BF16 vLLM (ADR 0001).
DEFAULT_VLLM_MIN_VRAM_BYTES = 40 * 1024**3


class BackendSelector:
    """Picks a backend: an explicit request, then a configured endpoint, then the hardware.

    A configured endpoint outranks the hardware because the operator named it; qwenloop
    starting a llama-server of its own beside the one it was pointed at would be the
    silent backend change the README promises never happens.
    """

    def __init__(self, *, vllm_min_vram_bytes: int = DEFAULT_VLLM_MIN_VRAM_BYTES) -> None:
        self._vllm_min_vram_bytes = vllm_min_vram_bytes

    def select(
        self,
        requested: Backend,
        hardware: Hardware,
        *,
        vllm_installed: bool,
        endpoint_configured: bool,
        ollama_available: bool = False,
    ) -> BackendChoice:
        if requested is not Backend.AUTO:
            return BackendChoice(requested, "explicit configuration")
        if endpoint_configured:
            return BackendChoice(
                Backend.OPENAI_COMPAT, "an OpenAI-compatible endpoint is configured"
            )
        if ollama_available:
            # Nothing configured, and a local Ollama is running: it is the default (#388).
            return BackendChoice(
                Backend.OPENAI_COMPAT, "a local Ollama is running: the default backend"
            )
        if (
            hardware.system == "Linux"
            and hardware.nvidia_vram_bytes >= self._vllm_min_vram_bytes
            and vllm_installed
        ):
            gib = self._vllm_min_vram_bytes // 1024**3
            return BackendChoice(
                Backend.VLLM, f"Linux NVIDIA GPU has at least {gib} GiB usable VRAM"
            )
        return BackendChoice(Backend.LLAMA_CPP, "portable backend for this hardware")
