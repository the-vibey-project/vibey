# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The local model families vibey knows by name (ADR-0093, #1662).

A family is a name a person can say -- `codestral`, `gemma` -- and the Ollama tag that is a
sensible place to start with it. It is NOT a claim about what the model can do. Whether a
model calls tools is decided by Ollama from more than its template (a built-in renderer
counts), and a template check measured wrong on the models that matter, so the answer comes
only from the Ollama that will run it (`/api/show` capabilities). This module turns that
answer into the jobs the model can be tried for; it never invents one.
"""

from dataclasses import dataclass
from typing import Final

from vibey.domain.interfaces.model_families_interface import ModelFamiliesInterface

TOOLS: Final = "tools"
COMPLETION: Final = "completion"
INSERT: Final = "insert"


@dataclass(frozen=True, slots=True)
class ModelFamily:
    key: str
    label: str
    # The names (the part of a tag before `:`) this family covers. A name belongs when it is
    # one of these, or one of these followed by a digit or a hyphen (`llama3.1`, `starcoder2`,
    # `deepseek-coder-v2`): `codellama` is not `llama` and `codegemma` is not `gemma`.
    stems: tuple[str, ...]
    suggested_tag: str


MODEL_FAMILIES: Final = (
    ModelFamily("qwen-coder", "Qwen Coder", ("qwen2.5-coder", "qwen3-coder"), "qwen2.5-coder:14b"),
    ModelFamily("deepseek-coder", "DeepSeek Coder", ("deepseek-coder",), "deepseek-coder:6.7b"),
    ModelFamily("codestral", "Codestral", ("codestral",), "codestral:22b"),
    ModelFamily("starcoder", "StarCoder", ("starcoder",), "starcoder2:7b"),
    ModelFamily("gemma", "Gemma", ("gemma",), "gemma3:12b"),
    ModelFamily("llama", "Llama", ("llama",), "llama3.1:8b"),
    ModelFamily("codellama", "CodeLlama", ("codellama",), "codellama:13b"),
    ModelFamily("codegemma", "CodeGemma", ("codegemma",), "codegemma:7b"),
)


class ModelFamilies:
    """Finds a model's family and says what it can be tried for."""

    def __init__(self, families: tuple[ModelFamily, ...] = MODEL_FAMILIES) -> None:
        self._families = families

    def all(self) -> tuple[ModelFamily, ...]:
        return self._families

    def family_of(self, tag: str) -> ModelFamily | None:
        """The family a tag (`codestral:22b`, `llama3.1`) belongs to, or None."""
        name = tag.partition(":")[0].rpartition("/")[2].lower()
        best: tuple[int, ModelFamily] | None = None
        for family in self._families:
            for stem in family.stems:
                rest = name[len(stem) :]
                matches = name.startswith(stem) and (
                    not rest or rest[0].isdigit() or rest[0] == "-"
                )
                if matches and (best is None or len(stem) > best[0]):
                    best = (len(stem), family)
        return best[1] if best else None

    def resolve(self, name: str) -> str:
        """A family key becomes its suggested tag; anything else is already a tag."""
        for family in self._families:
            if name.lower() == family.key:
                return family.suggested_tag
        return name

    def jobs(self, capabilities: frozenset[str]) -> tuple[str, ...]:
        """What a model reporting `capabilities` can be tried for. Tool-calling is necessary
        for native BUILD, not sufficient: a model can report it and still write its calls out
        as text (Qwen2.5-Coder 14B on Ollama does), which only a run shows. A model without it
        can still be driven through the text tool-call protocol, which is slower and, where it
        was measured, no better (ADR-0093)."""
        jobs: list[str] = []
        if TOOLS in capabilities:
            jobs.append("BUILD (it reports tool-calling; a run shows whether it uses it well)")
        if COMPLETION in capabilities:
            jobs.append("DESIGN and DECOMPOSE (JSON mode needs no tool-calling)")
        if INSERT in capabilities:
            jobs.append("fill-in-the-middle completion")
        if COMPLETION in capabilities and TOOLS not in capabilities:
            jobs.append("BUILD through the text tool-call protocol (slower; measured unreliable)")
        return tuple(jobs)


MODEL_FAMILY_CATALOG: Final[ModelFamiliesInterface] = ModelFamilies()
