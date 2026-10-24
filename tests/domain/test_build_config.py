# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from vibey.domain.config import BuildConfig, BuildSlicingConfig, ConfigError
from vibey.domain.interfaces import BuildConfigInterface, BuildSlicingConfigInterface
from vibey.domain.slicing import DEFAULT_MAX_CHILDREN


def test_an_absent_table_is_the_default() -> None:
    config = BuildConfig.from_data({})
    assert config.slicing.max_children == DEFAULT_MAX_CHILDREN
    assert isinstance(config, BuildConfigInterface)
    assert isinstance(config.slicing, BuildSlicingConfigInterface)


def test_max_children_is_read() -> None:
    assert (
        BuildConfig.from_data({"build": {"slicing": {"max_children": 5}}}).slicing.max_children == 5
    )


@pytest.mark.parametrize("bad", [1, 0, -3, True, "8", 2.5])
def test_a_cap_that_could_never_group_is_refused(bad: object) -> None:
    with pytest.raises(ConfigError, match="max_children"):
        BuildConfig.from_data({"build": {"slicing": {"max_children": bad}}})


def test_an_unknown_key_is_named() -> None:
    with pytest.raises(ConfigError, match=r"build.slicing.wide"):
        BuildConfig.from_data({"build": {"slicing": {"wide": 1}}})
    with pytest.raises(ConfigError, match=r"build.extra"):
        BuildConfig.from_data({"build": {"extra": {}}})


def test_the_table_reader_alone_applies_the_default() -> None:
    assert BuildSlicingConfig.from_table({}, "build.slicing").max_children == DEFAULT_MAX_CHILDREN
