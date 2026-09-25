# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

import pytest

from qwenloop.domain.config import QwenConfig
from qwenloop.domain.model import Backend
from qwenloop.infrastructure.interfaces import SettingsLoaderInterface
from qwenloop.infrastructure.settings import SettingsLoader


def test_missing_default_file_is_an_empty_layer(tmp_path: Path) -> None:
    loader = SettingsLoader({}, default_path=tmp_path / "absent.toml")
    assert isinstance(loader, SettingsLoaderInterface)
    assert loader.path == tmp_path / "absent.toml"
    assert loader.load() == QwenConfig(model="qwen3:14b")
    assert loader.api_key == ""


def test_default_path_is_the_user_config_dir() -> None:
    assert SettingsLoader({}).path.name == "config.toml"
    assert SettingsLoader({}).path.parent.name == "qwenloop"


def test_file_then_environment_then_flags(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'base_url = "http://file:1/v1"\nmodel = "file-model"\nmax_turns = 12\n', encoding="utf-8"
    )
    environ = {"QWENLOOP_CONFIG": str(config)}
    from_file = SettingsLoader(environ).load()
    assert (from_file.base_url, from_file.model, from_file.max_turns) == (
        "http://file:1/v1",
        "file-model",
        12,
    )

    environ |= {"QWENLOOP_BASE_URL": "http://env:2/v1", "QWENLOOP_MODEL": "env-model"}
    from_env = SettingsLoader(environ).load({"base_url": None, "model": None})
    assert (from_env.base_url, from_env.model) == ("http://env:2/v1", "env-model")

    from_flags = SettingsLoader(environ).load(
        {"base_url": "http://flag:3/v1", "model": "flag-model", "backend": Backend.OPENAI_COMPAT}
    )
    assert (from_flags.base_url, from_flags.model, from_flags.backend) == (
        "http://flag:3/v1",
        "flag-model",
        Backend.OPENAI_COMPAT,
    )


def test_blank_environment_values_do_not_override(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('model = "file-model"\n', encoding="utf-8")
    loaded = SettingsLoader(
        {"QWENLOOP_CONFIG": str(config), "QWENLOOP_MODEL": "  ", "QWENLOOP_BASE_URL": ""}
    ).load()
    assert loaded.model == "file-model"
    assert not loaded.endpoint_configured


def test_api_key_comes_from_the_environment_only() -> None:
    assert SettingsLoader({"QWENLOOP_API_KEY": " sk-local \n"}).api_key == "sk-local"


def test_a_named_config_file_that_is_missing_is_an_error(tmp_path: Path) -> None:
    missing = tmp_path / "nope.toml"
    with pytest.raises(ValueError, match="QWENLOOP_CONFIG names .*nope.toml, which does not exist"):
        SettingsLoader({"QWENLOOP_CONFIG": str(missing)}).load()


def test_malformed_toml_is_an_error_naming_the_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("base_url = \n", encoding="utf-8")
    with pytest.raises(ValueError, match="bad.toml is not valid TOML"):
        SettingsLoader({"QWENLOOP_CONFIG": str(bad)}).load()


def test_config_path_expands_the_home_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "qwen.toml").write_text('model = "home-model"\n', encoding="utf-8")
    loader = SettingsLoader({"QWENLOOP_CONFIG": "~/qwen.toml"})
    assert loader.path == tmp_path / "qwen.toml"
    assert loader.load().model == "home-model"


def test_each_engine_reads_only_its_own_settings(tmp_path: Path) -> None:
    """ADR-0060: gptossloop reads GPTOSSLOOP_* and asks for gpt-oss:20b; qwenloop reads
    QWENLOOP_* and asks for qwen3:14b. A model named for one never reaches the other."""
    from qwenloop.domain.config import GPTOSSLOOP, QWENLOOP

    environ = {
        "GPTOSSLOOP_BASE_URL": "http://gpt:1/v1",
        "GPTOSSLOOP_API_KEY": "gpt-key",
        "QWENLOOP_MODEL": "qwen3:32b",
        "QWENLOOP_API_KEY": "qwen-key",
    }
    absent = tmp_path / "absent.toml"
    gptoss = SettingsLoader(environ, identity=GPTOSSLOOP, default_path=absent)
    qwen = SettingsLoader(environ, identity=QWENLOOP, default_path=absent)
    assert (gptoss.load().model, gptoss.load().base_url, gptoss.api_key) == (
        "gpt-oss:20b",
        "http://gpt:1/v1",
        "gpt-key",
    )
    assert (qwen.load().model, qwen.load().base_url, qwen.api_key) == ("qwen3:32b", "", "qwen-key")
    assert SettingsLoader({}, identity=GPTOSSLOOP).path.parent.name == "gptossloop"
    with pytest.raises(ValueError, match="GPTOSSLOOP_CONFIG names"):
        SettingsLoader({"GPTOSSLOOP_CONFIG": str(absent)}, identity=GPTOSSLOOP).load()
