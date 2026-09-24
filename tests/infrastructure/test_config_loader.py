# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import re
from pathlib import Path

import pytest

from vibey.domain.config import ConfigError
from vibey.infrastructure.config_loader import (
    RUNTIME_CONFIG_KEYS,
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


def test_surface_env_overlay_wires_a_cluster_without_a_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """In a cluster the chart renders endpoint URLs from its values and
    injects tokens from Secrets: no vibey.toml has to exist at all."""
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "from-disk"\n')
    monkeypatch.setenv("VIBEY_TRACKER_URL", "http://plane:3000")
    monkeypatch.setenv("VIBEY_TRACKER_TOKEN", "tok")
    monkeypatch.setenv("VIBEY_TRACKER_WORKSPACE_SLUG", "ws")
    monkeypatch.setenv("VIBEY_TRACKER_PROJECT_ID", "pid")
    monkeypatch.setenv("VIBEY_CACHE_URL", "redis://cache:6379")
    monkeypatch.setenv("VIBEY_BUS_URL", "http://bus:15672")
    monkeypatch.setenv("VIBEY_BUS_USERNAME", "u")
    monkeypatch.setenv("VIBEY_BUS_PASSWORD", "p")
    monkeypatch.setenv("VIBEY_BLOB_URL", "http://blob:3900")
    monkeypatch.setenv("VIBEY_BLOB_ACCESS_KEY", "ak")
    monkeypatch.setenv("VIBEY_BLOB_SECRET_KEY", "sk")
    monkeypatch.setenv("VIBEY_SIEM_URL", "http://siem:9200")
    monkeypatch.setenv("VIBEY_DOCS_BOOK_ID", "7")
    monkeypatch.setenv("VIBEY_EMAIL_SMTP_PORT", "587")
    monkeypatch.setenv("VIBEY_SMS_SENDER", "alerts")

    config = load_config_from_path(config_path)

    assert config.tracker.url == "http://plane:3000"
    assert config.tracker.workspace_slug == "ws"
    assert config.cache.url == "redis://cache:6379"
    assert config.bus.password == "p"
    assert config.blob.secret_key == "sk"
    assert config.blob.region == "us-east-1"
    assert config.siem.index == "vibey-audit"
    assert config.docs.book_id == 7
    assert config.email.smtp_port == 587
    assert config.sms.sender == "alerts"


def test_surface_env_overlay_beats_the_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "x"\n\n[tracker]\nurl = "http://file"\n')
    monkeypatch.setenv("VIBEY_TRACKER_URL", "http://env")

    assert load_config_from_path(config_path).tracker.url == "http://env"


def test_surface_env_overlay_ignores_empty_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "x"\n')
    monkeypatch.setenv("VIBEY_TRACKER_URL", "   ")

    assert load_config_from_path(config_path).tracker.url is None


def test_surface_env_overlay_rejects_bad_integers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('[project]\nname = "x"\n')
    monkeypatch.setenv("VIBEY_DOCS_BOOK_ID", "many")

    with pytest.raises(ValueError, match="VIBEY_DOCS_BOOK_ID must be an integer"):
        load_config_from_path(config_path)


def test_surface_env_overlay_rejects_non_table_sections(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text('tracker = "nope"\n[project]\nname = "x"\n')
    monkeypatch.setenv("VIBEY_TRACKER_URL", "http://env")

    with pytest.raises(ValueError, match="tracker must be a table"):
        load_config_from_path(config_path)


# ── [gates] and [engine_environment]: declared in vibey.toml, never hand-edited ──


def test_the_child_environment_tables_are_runtime_tables(tmp_path: Path) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text(
        '[gates]\nisolate_python_env = false\nenv_allow = ["TEST_DATABASE_URL"]\n\n'
        "[engine_environment.engines]\n"
        'claudeloop = ["GH_TOKEN"]\n'
        '"claudeloop-local" = ["GH_TOKEN"]\n'
    )

    assert "gates" in RUNTIME_CONFIG_KEYS
    assert "engine_environment" in RUNTIME_CONFIG_KEYS
    assert load_runtime_config_from_path(config_path) == {
        "gates": {"isolate_python_env": False, "env_allow": ["TEST_DATABASE_URL"]},
        "engine_environment": {
            "engines": {"claudeloop": ["GH_TOKEN"], "claudeloop-local": ["GH_TOKEN"]}
        },
    }


@pytest.mark.parametrize(
    "toml, message",
    [
        ('[gates]\nenv_allow = ["VIBEY_PG_URL"]\n', "gates.env_allow: VIBEY_PG_URL"),
        ('[gates]\nenv_allow = ["GIT_DIR"]\n', "gates.env_allow: GIT_DIR"),
        ("[gates]\ntimeout_seconds = -1\n", "gates.timeout_seconds"),
        ('[engine_environment]\nallow = ["PGPASSWORD"]\n', "engine_environment.allow: PG"),
        (
            '[engine_environment.engines]\nopencode = ["APP_DATABASE_URL"]\n',
            "engine_environment.engines.opencode: APP_DATABASE_URL",
        ),
        (
            '[engine_environment.engines]\nnot-an-engine = ["X"]\n',
            "unknown engine 'not-an-engine'",
        ),
        ('[engine_environment]\nsurprise = ["X"]\n', "unknown key 'surprise'"),
    ],
)
def test_a_malformed_or_forbidden_declaration_is_refused_before_persistence(
    tmp_path: Path, toml: str, message: str
) -> None:
    config_path = tmp_path / "vibey.toml"
    config_path.write_text(toml)

    with pytest.raises(ValueError, match=re.escape(message)):
        load_runtime_config_from_path(config_path)
