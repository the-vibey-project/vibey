# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from vibey.domain.interfaces.sovereign_model_interface import SovereignModelsInterface
from vibey.domain.sovereign_model import (
    DEFAULT_SOVEREIGN_TAG,
    SOVEREIGN_CATALOG,
    SOVEREIGN_FAMILY,
    SOVEREIGN_MODEL_ENV,
    SOVEREIGN_MODELS,
    SovereignModels,
)

HERETIC = "hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE"


def test_the_default_is_the_heretic_build() -> None:
    assert SOVEREIGN_CATALOG.default().key == "heretic"
    assert DEFAULT_SOVEREIGN_TAG == HERETIC
    assert SOVEREIGN_CATALOG.all()[0] is SOVEREIGN_CATALOG.default()


def test_the_catalogue_satisfies_its_interface() -> None:
    assert isinstance(SOVEREIGN_CATALOG, SovereignModelsInterface)


def test_both_builds_share_one_architecture_so_a_fit_carries_over() -> None:
    assert {m.family for m in SOVEREIGN_MODELS} == {SOVEREIGN_FAMILY}


def test_the_stock_build_is_the_library_tag() -> None:
    stock = SOVEREIGN_CATALOG.by_key("stock")
    assert stock is not None and stock.tag == "gpt-oss:20b"


def test_a_key_is_found_whatever_its_case_and_padding() -> None:
    found = SOVEREIGN_CATALOG.by_key("  HERETIC ")
    assert found is not None and found.tag == HERETIC
    assert SOVEREIGN_CATALOG.by_key("llama") is None


def test_a_tag_names_its_build_exactly() -> None:
    assert SOVEREIGN_CATALOG.variant_of(HERETIC) is SOVEREIGN_CATALOG.by_key("heretic")
    assert SOVEREIGN_CATALOG.variant_of(" gpt-oss:20b ") is SOVEREIGN_CATALOG.by_key("stock")
    assert SOVEREIGN_CATALOG.variant_of("gpt-oss:120b") is None
    assert SOVEREIGN_CATALOG.same_family("gpt-oss:20b") is True
    assert SOVEREIGN_CATALOG.same_family("qwen3:14b") is False


def test_a_key_resolves_to_its_tag_and_a_tag_is_left_alone() -> None:
    assert SOVEREIGN_CATALOG.resolve("stock") == "gpt-oss:20b"
    assert SOVEREIGN_CATALOG.resolve("qwen3:14b") == "qwen3:14b"


@pytest.mark.parametrize(
    ("environ", "explicit", "expected"),
    [
        ({}, None, HERETIC),
        ({}, "", HERETIC),
        ({"VIBEY_OLLAMA_MODEL": "   "}, None, HERETIC),
        ({SOVEREIGN_MODEL_ENV: "stock"}, None, "gpt-oss:20b"),
        ({SOVEREIGN_MODEL_ENV: "heretic"}, None, HERETIC),
        ({"VIBEY_OLLAMA_MODEL": "qwen3:14b", SOVEREIGN_MODEL_ENV: "stock"}, None, "qwen3:14b"),
        ({"VIBEY_OLLAMA_MODEL": "qwen3:14b"}, "stock", "gpt-oss:20b"),
        ({"VIBEY_OLLAMA_MODEL": "stock"}, None, "gpt-oss:20b"),
    ],
)
def test_the_tag_follows_the_documented_precedence(
    environ: dict[str, str], explicit: str | None, expected: str
) -> None:
    assert SOVEREIGN_CATALOG.from_environment(environ, explicit=explicit) == expected


def test_a_default_key_that_names_nothing_is_an_error_not_a_guess() -> None:
    with pytest.raises(LookupError, match="no sovereign model is keyed 'missing'"):
        SovereignModels(default_key="missing").default()
