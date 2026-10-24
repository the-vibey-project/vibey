# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from vibey.domain.model_families import MODEL_FAMILIES, MODEL_FAMILY_CATALOG, ModelFamilies

ISSUE_1662 = (
    "qwen-coder",
    "deepseek-coder",
    "codestral",
    "starcoder",
    "gemma",
    "llama",
    "codellama",
    "codegemma",
)


def test_every_family_the_issue_names_is_known() -> None:
    assert tuple(f.key for f in MODEL_FAMILIES) == ISSUE_1662
    assert MODEL_FAMILY_CATALOG.all() == MODEL_FAMILIES


@pytest.mark.parametrize("family", MODEL_FAMILIES, ids=lambda f: f.key)
def test_each_suggested_tag_belongs_to_its_own_family(family) -> None:  # type: ignore[no-untyped-def]
    assert MODEL_FAMILY_CATALOG.family_of(family.suggested_tag) == family


@pytest.mark.parametrize(
    ("tag", "key"),
    [
        ("qwen2.5-coder:14b", "qwen-coder"),
        ("qwen3-coder:30b", "qwen-coder"),
        ("deepseek-coder:6.7b", "deepseek-coder"),
        ("deepseek-coder-v2:16b", "deepseek-coder"),
        ("codestral:22b", "codestral"),
        ("starcoder:7b", "starcoder"),
        ("starcoder2:3b", "starcoder"),
        ("gemma:2b", "gemma"),
        ("gemma3:12b", "gemma"),
        ("gemma4:26b", "gemma"),
        ("llama2", "llama"),
        ("llama3.1:8b", "llama"),
        ("llama3.3:70b", "llama"),
        ("codellama:13b", "codellama"),
        ("codegemma:7b", "codegemma"),
        ("library/Codestral:22b", "codestral"),
    ],
)
def test_a_tag_finds_its_family(tag: str, key: str) -> None:
    family = MODEL_FAMILY_CATALOG.family_of(tag)
    assert family is not None and family.key == key


@pytest.mark.parametrize("tag", ["gpt-oss:20b", "qwen3:14b", "llamafile:1b", "mistral:7b", ""])
def test_a_tag_outside_every_family_has_none(tag: str) -> None:
    assert MODEL_FAMILY_CATALOG.family_of(tag) is None


def test_a_longer_stem_wins_over_a_shorter_one() -> None:
    """`codellama` is not `llama`, and `codegemma` is not `gemma`."""
    assert MODEL_FAMILY_CATALOG.family_of("codellama:7b").key == "codellama"  # type: ignore[union-attr]
    assert MODEL_FAMILY_CATALOG.family_of("codegemma:2b").key == "codegemma"  # type: ignore[union-attr]
    narrow = ModelFamilies(MODEL_FAMILIES[:5])
    assert narrow.family_of("codellama:7b") is None


def test_a_family_key_resolves_to_its_suggested_tag_and_a_tag_is_left_alone() -> None:
    assert MODEL_FAMILY_CATALOG.resolve("Codestral") == "codestral:22b"
    assert MODEL_FAMILY_CATALOG.resolve("gemma3:1b") == "gemma3:1b"
    assert MODEL_FAMILY_CATALOG.resolve("gpt-oss:20b") == "gpt-oss:20b"


def test_jobs_follow_only_what_the_model_reports() -> None:
    jobs = MODEL_FAMILY_CATALOG.jobs
    assert jobs(frozenset()) == ()
    assert [j.split(" ")[0] for j in jobs(frozenset({"completion", "tools", "insert"}))] == [
        "BUILD",
        "DESIGN",
        "fill-in-the-middle",
    ]
    assert [j.split(" ")[0] for j in jobs(frozenset({"completion"}))] == ["DESIGN", "BUILD"]
    assert "text tool-call protocol" in jobs(frozenset({"completion"}))[1]
    assert "a run shows" in jobs(frozenset({"tools"}))[0]
    # With tools the model builds natively; the text protocol is only for one without them.
    assert not any("text tool-call" in j for j in jobs(frozenset({"completion", "tools"})))


def test_the_catalogue_satisfies_its_interface() -> None:
    from vibey.domain.interfaces import ModelFamiliesInterface

    assert isinstance(MODEL_FAMILY_CATALOG, ModelFamiliesInterface)
