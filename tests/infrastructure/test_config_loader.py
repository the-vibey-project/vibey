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


# -- QueueConfigLoader (ADR-0054) ----------------------------------------------------


def test_queue_config_reads_declared_sources_without_a_project_table(tmp_path: Path) -> None:
    from vibey.infrastructure.config_loader import QUEUE_CONFIG
    from vibey.infrastructure.interfaces import QueueConfigLoaderInterface

    path = tmp_path / "vibey.toml"
    path.write_text('[queue.priority]\nsources = ["storm"]\n')

    assert isinstance(QUEUE_CONFIG, QueueConfigLoaderInterface)
    assert QUEUE_CONFIG.load(path).priority.sources == ("storm",)


def test_a_missing_file_declares_no_source(tmp_path: Path) -> None:
    from vibey.infrastructure.config_loader import QueueConfigLoader

    assert QueueConfigLoader().load(tmp_path / "absent.toml").priority.sources == ()


def test_a_malformed_file_is_an_error_never_an_empty_declaration(tmp_path: Path) -> None:
    from vibey.domain.config import ConfigError
    from vibey.infrastructure.config_loader import QueueConfigLoader

    path = tmp_path / "vibey.toml"
    path.write_text("[queue.priority\nsources = [")

    with pytest.raises(ConfigError, match="is not valid TOML"):
        QueueConfigLoader().load(path)


# -- [queue.reap] and the environment alone (ADR-0056) --------------------------------


def test_the_queue_reap_overlay_reaches_a_nested_table_with_its_types() -> None:
    from vibey.infrastructure.config_loader import apply_env_overrides

    data: dict[str, object] = {"queue": {"priority": {"sources": ["storm"]}}}
    apply_env_overrides(
        data,
        {
            "VIBEY_QUEUE_REAP_ENABLED": " Off ",
            "VIBEY_QUEUE_REAP_STALE_READY_SECONDS": "120",
            "VIBEY_QUEUE_REAP_OWNED_QUEUE_PATTERN": r"^mine\.",
            "VIBEY_BUS_VHOST": "vibey",
        },
    )
    assert data == {
        "queue": {
            "priority": {"sources": ["storm"]},
            "reap": {
                "enabled": False,
                "stale_ready_seconds": 120,
                "owned_queue_pattern": r"^mine\.",
            },
        },
        "bus": {"vhost": "vibey"},
    }


@pytest.mark.parametrize(
    ("environ", "match"),
    [
        ({"VIBEY_QUEUE_REAP_ENABLED": "maybe"}, "VIBEY_QUEUE_REAP_ENABLED must be a boolean"),
        (
            {"VIBEY_QUEUE_REAP_DELIVERY_LIMIT": "x"},
            "VIBEY_QUEUE_REAP_DELIVERY_LIMIT must be an int",
        ),
    ],
)
def test_a_malformed_queue_reap_variable_names_itself(environ: dict[str, str], match: str) -> None:
    from vibey.infrastructure.config_loader import apply_env_overrides

    with pytest.raises(ValueError, match=match):
        apply_env_overrides({}, environ)


def test_a_nested_overlay_refuses_a_non_table_parent() -> None:
    from vibey.infrastructure.config_loader import apply_env_overrides

    with pytest.raises(ValueError, match="queue.reap must be a table"):
        apply_env_overrides({"queue": 3}, {"VIBEY_QUEUE_REAP_ENABLED": "1"})


def test_the_environment_alone_declares_the_bus_and_the_reaper() -> None:
    """A cluster pod has no vibey.toml; the chart puts everything in its environment."""
    from vibey.infrastructure.config_loader import ENVIRONMENT_CONFIG, EnvironmentConfigLoader
    from vibey.infrastructure.interfaces.class_contracts import EnvironmentConfigLoaderInterface

    assert isinstance(ENVIRONMENT_CONFIG, EnvironmentConfigLoaderInterface)
    config = ENVIRONMENT_CONFIG.load(
        {
            "VIBEY_BUS_URL": "http://bus:15672",
            "VIBEY_BUS_USERNAME": "u",
            "VIBEY_BUS_PASSWORD": "p",
            "VIBEY_QUEUE_REAP_INTERVAL_SECONDS": "30",
        }
    )
    assert config.project.name == EnvironmentConfigLoader.PLACEHOLDER_PROJECT
    assert (config.bus.url, config.bus.username, config.bus.password, config.bus.vhost) == (
        "http://bus:15672",
        "u",
        "p",
        "/",
    )
    assert config.queue.reap.interval_seconds == 30
    assert ENVIRONMENT_CONFIG.load({}).bus.url is None


def test_the_environment_alone_refuses_a_threshold_out_of_range() -> None:
    from vibey.infrastructure.config_loader import ENVIRONMENT_CONFIG

    with pytest.raises(ConfigError, match="queue.reap.interval_seconds"):
        ENVIRONMENT_CONFIG.load({"VIBEY_QUEUE_REAP_INTERVAL_SECONDS": "0"})
