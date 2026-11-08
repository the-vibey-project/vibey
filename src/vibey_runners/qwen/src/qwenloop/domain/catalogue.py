# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The model catalogue as data: pinned models, parameter counts, and licences."""

from dataclasses import dataclass

from qwenloop.domain.model import Backend, ModelProfile


@dataclass(frozen=True, slots=True)
class OllamaArtifact:
    tag: str


@dataclass(frozen=True, slots=True)
class ModelEntry:
    name: str
    family: str
    total_params_b: float
    active_params_b: float
    license_spdx: str
    license_osi: bool
    min_ram_gib: int
    context_window: int
    ollama: OllamaArtifact | None
    gguf: ModelProfile | None
    evidence: str
    recorded: str
    unverified: tuple[str, ...] = ()


QWEN25_CODER_14B_Q5_K_M = ModelProfile(
    name="qwen2.5-coder-14b-q5-k-m",
    backend=Backend.LLAMA_CPP,
    repository="Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
    revision="d0a692ef765eefbf2fabb130b3cb2e8917e3d225",
    filename="qwen2.5-coder-14b-instruct-q5_k_m.gguf",
    sha256="98ab25e0132e3f1e6d3554e1b64de2b5021908819b740d9c208430117e49a775",
    size=10_508_873_152,
    quantization="Q5_K_M",
)


CATALOGUE: tuple[ModelEntry, ...] = (
    ModelEntry(
        name="qwen2.5-coder-14b",
        family="qwen2.5-coder",
        total_params_b=14.7,
        active_params_b=14.7,
        license_spdx="Apache-2.0",
        license_osi=True,
        min_ram_gib=16,
        context_window=32_768,
        ollama=OllamaArtifact("qwen2.5-coder:14b"),
        gguf=QWEN25_CODER_14B_Q5_K_M,
        evidence=(
            "previous default; 215 s for a ten-turn session at 32,768 tokens on an M5 24 GB"
            " (llama.cpp); loaded on Ollama as qwen2.5-coder:14b at 9.7 GB resident on a 24 GB machine"
            " (vibey_gh/fit.py:15)"
        ),
        recorded="2026-09-22",
        unverified=(),
    ),
    ModelEntry(
        name="gpt-oss-20b",
        family="gpt-oss",
        total_params_b=20.9,
        active_params_b=3.6,
        license_spdx="Apache-2.0",
        license_osi=True,
        min_ram_gib=16,
        context_window=131_072,
        ollama=OllamaArtifact("gpt-oss:20b"),
        gguf=None,
        evidence=(
            "the 8.d designated default: 86 s for a ten-turn session at 131,072 tokens in 13.1 GB"
            " resident on an M5 24 GB (Ollama); its llama.cpp GGUF is pinned from"
            " ggml-org/gpt-oss-20b-GGUF but never load-tested"
        ),
        recorded="2026-09-22",
        unverified=("llama.cpp",),
    ),
)


class ModelCatalogue:
    """The pinned model catalogue as data."""

    def __init__(self, entries: tuple[ModelEntry, ...] = CATALOGUE) -> None:
        seen_names: set[str] = set()
        seen_tags: set[str] = set()
        for entry in entries:
            if entry.name in seen_names:
                raise ValueError(f"duplicate catalogue entry name: {entry.name}")
            seen_names.add(entry.name)

            if entry.ollama is not None:
                tag = entry.ollama.tag
                if tag in seen_tags:
                    raise ValueError(f"duplicate Ollama tag in the catalogue: {tag}")
                seen_tags.add(tag)

            if entry.ollama is None and entry.gguf is None:
                raise ValueError(
                    f"catalogue entry {entry.name} pins neither an Ollama tag nor a GGUF"
                )

        self._entries = entries
        self._by_name = {entry.name: entry for entry in entries}
        self._by_tag = {entry.ollama.tag: entry for entry in entries if entry.ollama is not None}

    def entries(self) -> tuple[ModelEntry, ...]:
        """Every model entry in the catalogue, in declared order."""
        return self._entries

    def get(self, name: str) -> ModelEntry:
        """Lookup an entry by name or raise KeyError listing known entries."""
        if name in self._by_name:
            return self._by_name[name]
        known = ", ".join(sorted(self._by_name))
        raise KeyError(f"unknown catalogue entry {name!r}; known: {known}")

    def by_ollama_tag(self, tag: str) -> ModelEntry | None:
        """Lookup an entry by its Ollama tag, or None if unknown."""
        return self._by_tag.get(tag)
