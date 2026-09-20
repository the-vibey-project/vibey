# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import re
from pathlib import Path

import pytest

from vibey.domain.config import ConfigError
from vibey.infrastructure.config_loader import (
    load_config_from_path,
    load_runtime_config_from_path,
)


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


def test_runtime_tables_are_loaded_for_project_creation(tmp_path: Path) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text(
        "[notifications]\nenabled = true\n\n"
        '[[notifications.webhooks]]\nurl = "https://example.test/hook"\n\n'
        "[telemetry]\nenabled = false\n"
    )

    assert load_runtime_config_from_path(config_path) == {
        "notifications": {
            "enabled": True,
            "webhooks": [{"url": "https://example.test/hook"}],
        },
        "telemetry": {"enabled": False},
    }


def test_runtime_tables_ignore_missing_files_and_unrelated_config(tmp_path: Path) -> None:
    assert load_runtime_config_from_path(tmp_path / "missing.toml") == {}

    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "x"\n\n[features]\nqwenloop = true\n')
    assert load_runtime_config_from_path(config_path) == {}


@pytest.mark.parametrize(
    "toml, path",
    [
        ('[notifications]\nenabled = "yes"\n', "notifications.enabled"),
        ("[notifications]\nwebhooks = [1]\n", "notifications.webhooks[0]"),
        ('[telemetry]\nenabled = "yes"\n', "telemetry.enabled"),
    ],
)
def test_runtime_tables_are_validated_before_persistence(
    tmp_path: Path, toml: str, path: str
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text(toml)

    with pytest.raises(ConfigError, match=re.escape(path)):
        load_runtime_config_from_path(config_path)
