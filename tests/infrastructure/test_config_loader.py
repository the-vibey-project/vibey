# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

import pytest

from vibey.infrastructure.config_loader import load_config_from_path


def test_load_config_from_path_reads_and_parses(tmp_path: Path) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "from-disk"\n')

    config = load_config_from_path(config_path)

    assert config.project.name == "from-disk"


def test_environment_enables_qwenloop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "from-disk"\n')
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "yes")
    assert load_config_from_path(config_path).features.qwenloop


def test_invalid_environment_override_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "from-disk"\n')
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "maybe")
    with pytest.raises(ValueError, match="boolean"):
        load_config_from_path(config_path)


def test_environment_rejects_non_table_features(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('features = "bad"\n[project]\nname = "from-disk"\n')
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "true")
    with pytest.raises(ValueError, match="table"):
        load_config_from_path(config_path)


def test_environment_switches_every_local_engine_the_same_way(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """One table of switches for the loader and the worker's resolver alike."""
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "from-disk"\n\n[features]\nqwenloop = true\n')
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "off")
    monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "on")

    config = load_config_from_path(config_path)

    assert config.features.qwenloop is False
    assert config.features.claudeloop_local is True
    assert config.engines.enabled[-1] == "claudeloop-local"


def test_a_non_boolean_claudeloop_local_switch_names_itself(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "from-disk"\n')
    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)
    monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "sometimes")
    with pytest.raises(ValueError, match="VIBEY_FEATURE_CLAUDELOOP_LOCAL must be a boolean"):
        load_config_from_path(config_path)
