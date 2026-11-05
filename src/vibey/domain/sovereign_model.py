# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign model: which weights the local loop runs, and how to name them (ADR-0099).

The sovereign default (sub-doctrine 8.a) is GPT-OSS 20B. It comes in two builds that share one
architecture and one memory footprint, so every measured capacity figure for the one holds for
the other:

- ``heretic`` -- the default. ``p-e-w/gpt-oss-20b-heretic-v2``, GPT-OSS 20B with its refusal
  direction removed by Heretic. The loop is a coding agent that must run commands, edit files and
  open pull requests; a model that declines the work it was given is a stalled loop, and vibey's
  own bounds (gates, caps, the ledger) are the safety layer, not the model's reflexes. The v2
  build is the one chosen: its KL divergence from the original is 0.1248 on its model card
  (v1: 0.96), so what it does outside refusals stays close to the model vibey was measured on.
- ``stock`` -- OpenAI's ``gpt-oss:20b`` from the Ollama library, unchanged.

The weights are Apache-2.0. The tool that made them (Heretic) is AGPL-3.0 and is NOT a runtime
dependency of vibey: only its published output is used, pulled through Ollama's Hugging Face
support.

Pure data and string rules; no I/O, no environment of its own. The caller hands in the mapping.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from vibey.domain.interfaces.sovereign_model_interface import SovereignModelsInterface

#: Selects a variant by key (``heretic`` | ``stock``). Beaten by ``VIBEY_OLLAMA_MODEL``.
SOVEREIGN_MODEL_ENV: Final = "VIBEY_SOVEREIGN_MODEL"
#: The long-standing variable naming any Ollama tag. When set it wins over the variant.
OLLAMA_MODEL_ENV: Final = "VIBEY_OLLAMA_MODEL"
DEFAULT_VARIANT_KEY: Final = "heretic"
#: The architecture both builds share; capacity, fit and benchmark records are keyed to it.
SOVEREIGN_FAMILY: Final = "gpt-oss:20b"


@dataclass(frozen=True, slots=True)
class SovereignModel:
    key: str
    label: str
    #: What Ollama is asked for: a library tag, or ``hf.co/<user>/<repo>:<quant>``.
    tag: str
    #: The shape both builds share, so a fit measured on one is valid for the other.
    family: str
    source: str
    license: str
    download: str
    note: str


SOVEREIGN_MODELS: Final = (
    SovereignModel(
        key="heretic",
        label="GPT-OSS 20B, Heretic v2",
        tag="hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE",
        family=SOVEREIGN_FAMILY,
        source="https://huggingface.co/p-e-w/gpt-oss-20b-heretic-v2",
        license="Apache-2.0 (weights); Heretic itself is AGPL-3.0 and is not used at runtime",
        download="12.1 GB",
        note=(
            "Refusal direction removed (49/100 test prompts refused against 98/100 for the "
            "original; KL divergence 0.1248). Native MXFP4, so the same footprint as stock."
        ),
    ),
    SovereignModel(
        key="stock",
        label="GPT-OSS 20B, as released",
        tag="gpt-oss:20b",
        family=SOVEREIGN_FAMILY,
        source="https://ollama.com/library/gpt-oss",
        license="Apache-2.0",
        download="14 GB",
        note="OpenAI's release, unmodified. Pick it when a refusing model is the point.",
    ),
)


class SovereignModels:
    """Names the sovereign model and resolves what an operator asked for."""

    def __init__(
        self,
        models: tuple[SovereignModel, ...] = SOVEREIGN_MODELS,
        default_key: str = DEFAULT_VARIANT_KEY,
    ) -> None:
        self._models = models
        self._default_key = default_key

    def all(self) -> tuple[SovereignModel, ...]:
        return self._models

    def default(self) -> SovereignModel:
        return self._by_key(self._default_key)

    def by_key(self, key: str) -> SovereignModel | None:
        wanted = key.strip().lower()
        for model in self._models:
            if model.key == wanted:
                return model
        return None

    def variant_of(self, tag: str) -> SovereignModel | None:
        """The build a tag names exactly, or None for a tag vibey does not know by name."""
        wanted = tag.strip()
        for model in self._models:
            if model.tag == wanted:
                return model
        return None

    def same_family(self, tag: str) -> bool:
        """Whether a tag is one of the builds that share the sovereign architecture."""
        return self.variant_of(tag) is not None

    def resolve(self, name: str) -> str:
        """A variant key becomes its tag; any other name is an Ollama tag and is left alone."""
        found = self.by_key(name)
        return found.tag if found is not None else name

    def from_environment(self, environ: Mapping[str, str], *, explicit: str | None = None) -> str:
        """The tag the local loop runs.

        Precedence: an explicit ``--ollama-model``, then ``VIBEY_OLLAMA_MODEL``, then the variant
        ``VIBEY_SOVEREIGN_MODEL`` names, then the default build. An empty variable counts as
        unset. A name in either of the first two that is a variant key (``stock``) is resolved to
        its tag, so ``--ollama-model stock`` works.
        """
        for raw in (explicit, environ.get(OLLAMA_MODEL_ENV), environ.get(SOVEREIGN_MODEL_ENV)):
            if raw is not None and raw.strip():
                return self.resolve(raw.strip())
        return self.default().tag

    def _by_key(self, key: str) -> SovereignModel:
        found = self.by_key(key)
        if found is None:
            raise LookupError(f"no sovereign model is keyed {key!r}")
        return found


SOVEREIGN_CATALOG: Final[SovereignModelsInterface] = SovereignModels()
DEFAULT_SOVEREIGN_TAG: Final = SOVEREIGN_CATALOG.default().tag
