# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pinned model profiles. Digests are operator-verifiable manifest fields."""

from qwenloop.domain.catalogue import CATALOGUE, QWEN25_CODER_14B_Q5_K_M
from qwenloop.domain.model import Backend, ModelProfile

QWEN_REVISION = "65784b8b67c59e1ae00b0f85206ac78775a2a2f4"
QWEN_GGUF_REVISION = QWEN25_CODER_14B_Q5_K_M.revision

PORTABLE = QWEN25_CODER_14B_Q5_K_M

NVIDIA_BF16 = ModelProfile(
    name="qwen2.5-coder-14b-bf16",
    backend=Backend.VLLM,
    repository="Qwen/Qwen2.5-Coder-14B-Instruct",
    revision=QWEN_REVISION,
    filename=None,
    sha256=None,
    size=29_600_000_000,
    quantization="BF16",
)

PROFILES = {profile.name: profile for profile in (PORTABLE, NVIDIA_BF16)}

#: Every catalogue entry's llama.cpp pin, by profile name, so a GGUF can be chosen by name.
CATALOGUE_PROFILES: dict[str, ModelProfile] = {
    entry.gguf.name: entry.gguf for entry in CATALOGUE if entry.gguf is not None
}
