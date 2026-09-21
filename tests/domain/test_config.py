# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from vibey.domain.config import ConfigError, load_config_from_string

ARCHITECTURE_DOC_EXAMPLE = """
[project]
name          = "my-app"
repo          = "."
max_cycles    = 10
strict_loopback = false          # true forces REVIEW -> DESIGN always

[isolation]
level         = "container"      # worktree | container | vm
allow_push    = false
egress        = [
    "api.anthropic.com", "api.openai.com", "api.cursor.sh", "generativelanguage.googleapis.com"
]

[budget]
max_dollars_per_cycle = 40.0
max_dollars_total     = 250.0
max_turns_per_item    = 60

[engines]
enabled = ["claudeloop", "codexloop", "cursorloop", "agyloop"]

[engines.weights]                # base rotation weights
claudeloop = 3
codexloop  = 2
cursorloop = 2
agyloop    = 1

[phases.design]
effort   = "high"
engines  = ["claudeloop", "codexloop"]     # optional per-phase allow-list

[phases.build]
effort      = "low"
parallelism = 4

[phases.review]
effort = "high"

[provision]
plugins = [
    "software-architecture", "quality-engineering", "security-first-dev", "engineering-process"
]

[deploy]
enabled = false
target  = "azure"
iac     = "bicep"
"""


def test_architecture_doc_example_parses_every_field() -> None:
    config = load_config_from_string(ARCHITECTURE_DOC_EXAMPLE)

    assert config.project.name == "my-app"
    assert config.project.repo == "."
    assert config.project.max_cycles == 10
    assert config.project.strict_loopback is False

    assert config.isolation.level == "container"
    assert config.isolation.allow_push is False
    assert config.isolation.egress == (
        "api.anthropic.com",
        "api.openai.com",
        "api.cursor.sh",
        "generativelanguage.googleapis.com",
    )

    assert config.budget.max_dollars_per_cycle == 40.0
    assert config.budget.max_dollars_total == 250.0
    assert config.budget.max_turns_per_item == 60

    assert config.engines.enabled == (
        "claudeloop",
        "codexloop",
        "cursorloop",
        "agyloop",
        "qwenloop",
        "opencode",
    )
    assert config.engines.weights == {
        "claudeloop": 3,
        "codexloop": 2,
        "cursorloop": 2,
        "agyloop": 1,
    }

    assert config.phases.design.effort == "high"
    assert config.phases.design.engines == ("claudeloop", "codexloop")
    assert config.phases.build.effort == "low"
    assert config.phases.build.parallelism == 4
    assert config.phases.review.effort == "high"

    assert config.provision.plugins == (
        "software-architecture",
        "quality-engineering",
        "security-first-dev",
        "engineering-process",
    )

    assert config.deploy.enabled is False
    assert config.deploy.target == "azure"
    assert config.deploy.iac == "bicep"


def test_minimal_config_applies_defaults() -> None:
    config = load_config_from_string('[project]\nname = "tiny"\n')

    assert config.project.name == "tiny"
    assert config.project.max_cycles == 10
    assert config.isolation.level == "worktree"
    assert config.engines.enabled == (
        "qwenloop",
        "opencode",
    )
    assert config.phases.design.effort == "high"
    assert config.phases.build.effort == "low"
    assert config.phases.review.effort == "high"
    assert config.deploy.enabled is False
    assert config.features.qwenloop is True
    assert config.qwenloop.backend == "auto"
    assert config.notifications.enabled is False
    assert config.notifications.desktop is True
    assert config.notifications.webhooks == ()
    assert config.telemetry.enabled is True
    assert config.telemetry.export_path is None


def test_notifications_and_telemetry_parse_from_toml() -> None:
    config = load_config_from_string(
        '[project]\nname = "observable"\n\n'
        "[notifications]\nenabled = true\ndesktop = false\n\n"
        '[[notifications.webhooks]]\nurl = " https://example.test/hook "\nsecret = "s3cret"\n\n'
        '[telemetry]\nenabled = false\nexport_path = ".vibey/telemetry.json"\n'
    )

    assert config.notifications.enabled is True
    assert config.notifications.desktop is False
    assert config.notifications.webhooks[0].url == "https://example.test/hook"
    assert config.notifications.webhooks[0].secret == "s3cret"
    assert config.telemetry.enabled is False
    assert config.telemetry.export_path == ".vibey/telemetry.json"


@pytest.mark.parametrize(
    "fragment, match",
    [
        ('[notifications]\nwebhooks = "bad"', "notifications.webhooks"),
        ("[notifications]\nwebhooks = [1]", "must be a table"),
        ('[[notifications.webhooks]]\nurl = " "', "must not be empty"),
        ('[[notifications.webhooks]]\nurl = "https://x"\nsecret = 7', "must be a str"),
        ('[notifications]\nenabled = "yes"', "notifications.enabled"),
        ('[telemetry]\nenabled = "yes"', "telemetry.enabled"),
        ("[telemetry]\nexport_path = 7", "telemetry.export_path"),
    ],
)
def test_invalid_notification_or_telemetry_config_is_rejected(fragment: str, match: str) -> None:
    with pytest.raises(ConfigError, match=match):
        load_config_from_string(f'[project]\nname = "x"\n\n{fragment}\n')


def test_qwenloop_feature_auto_includes_standby() -> None:
    config = load_config_from_string(
        '[project]\nname = "x"\n\n[features]\nqwenloop = true\n\n'
        '[qwenloop]\nbackend = "llama.cpp"\n'
    )
    assert "qwenloop" in config.engines.enabled
    assert config.qwenloop.backend == "llama.cpp"


def test_qwenloop_request_is_always_allowed() -> None:
    config = load_config_from_string('[project]\nname = "x"\n\n[engines]\nenabled = ["qwenloop"]\n')
    assert "qwenloop" in config.engines.enabled


def test_invalid_qwenloop_config_is_rejected() -> None:
    with pytest.raises(ConfigError):
        load_config_from_string(
            '[project]\nname = "x"\n\n[features]\nqwenloop = true\n\n'
            '[qwenloop]\nbackend = "ollama"\n'
        )
    with pytest.raises(ConfigError, match="non-negative"):
        load_config_from_string(
            '[project]\nname = "x"\n\n[features]\nqwenloop = true\n\n'
            "[qwenloop]\nidle_timeout_seconds = -1\n"
        )
    with pytest.raises(ConfigError, match="must be positive"):
        load_config_from_string(
            '[project]\nname = "x"\n\n[features]\nqwenloop = true\n\n'
            "[qwenloop]\ncontext_window = 0\n"
        )


def test_missing_project_table_is_rejected() -> None:
    with pytest.raises(ConfigError):
        load_config_from_string("")


def test_missing_project_name_is_rejected() -> None:
    with pytest.raises(ConfigError):
        load_config_from_string('[project]\nrepo = "."\n')


def test_wrong_type_for_project_name_is_rejected() -> None:
    with pytest.raises(ConfigError):
        load_config_from_string("[project]\nname = 42\n")


def test_invalid_isolation_level_is_rejected() -> None:
    text = '[project]\nname = "x"\n\n[isolation]\nlevel = "chroot"\n'
    with pytest.raises(ConfigError):
        load_config_from_string(text)


def test_invalid_phase_effort_is_rejected() -> None:
    text = '[project]\nname = "x"\n\n[phases.build]\neffort = "extreme"\n'
    with pytest.raises(ConfigError):
        load_config_from_string(text)


def test_unknown_engine_in_enabled_list_is_rejected() -> None:
    text = '[project]\nname = "x"\n\n[engines]\nenabled = ["claudeloop", "chatgpt"]\n'
    with pytest.raises(ConfigError):
        load_config_from_string(text)


def test_unknown_engine_in_weights_is_rejected() -> None:
    text = '[project]\nname = "x"\n\n[engines.weights]\nchatgpt = 1\n'
    with pytest.raises(ConfigError):
        load_config_from_string(text)


def test_wrong_type_for_optional_field_is_rejected() -> None:
    text = '[project]\nname = "x"\n\n[isolation]\negress = "not-a-list"\n'
    with pytest.raises(ConfigError):
        load_config_from_string(text)


def test_require_reports_missing_field_by_path() -> None:
    from vibey.domain.config import _require

    with pytest.raises(ConfigError) as exc_info:
        _require({}, "name", "project.name", str)

    assert exc_info.value.path == "project.name"


def test_malformed_toml_raises() -> None:
    with pytest.raises(Exception):  # noqa: B017 - tomllib.TOMLDecodeError, not our concern
        load_config_from_string("[project\nname = 'x'")


def test_claudeloop_local_defaults_to_the_local_profile_and_claims_no_verdict() -> None:
    config = load_config_from_string('[project]\nname = "tiny"\n')

    assert config.features.claudeloop_local is False
    assert config.engines.claudeloop_local.profile == "local"
    assert config.engines.claudeloop_local.context_window == 32_768
    assert config.engines.claudeloop_local.structured_verdict is False
    assert "claudeloop-local" not in config.engines.enabled


def test_claudeloop_local_feature_joins_the_default_pool_with_its_profile() -> None:
    config = load_config_from_string(
        '[project]\nname = "x"\n\n[features]\nclaudeloop_local = true\n\n'
        '[engines.claudeloop_local]\nprofile = " ollama "\ncontext_window = 65536\n'
        "structured_verdict = true\n"
    )

    assert config.engines.enabled[-1] == "claudeloop-local"
    assert config.engines.claudeloop_local.profile == "ollama"
    assert config.engines.claudeloop_local.context_window == 65_536
    assert config.engines.claudeloop_local.structured_verdict is True
    assert config.features.enables("claudeloop-local")
    assert config.features.enables("claudeloop")  # a paid engine needs no switch
    assert config.features.enables("qwenloop")


def test_both_local_features_join_the_pool_in_order() -> None:
    config = load_config_from_string(
        '[project]\nname = "x"\n\n[features]\nqwenloop = true\nclaudeloop_local = true\n'
    )

    assert config.engines.enabled[-2:] == ("opencode", "claudeloop-local")


def test_claudeloop_local_request_requires_its_feature() -> None:
    with pytest.raises(ConfigError, match="features.claudeloop_local"):
        load_config_from_string(
            '[project]\nname = "x"\n\n[engines]\nenabled = ["claudeloop-local"]\n'
        )
    with pytest.raises(ConfigError, match="features.claudeloop_local"):
        load_config_from_string(
            '[project]\nname = "x"\n\n[phases.build]\nengines = ["claudeloop-local"]\n'
        )


def test_an_explicit_pool_is_kept_as_written() -> None:
    config = load_config_from_string(
        '[project]\nname = "x"\n\n[features]\nclaudeloop_local = true\n\n'
        '[engines]\nenabled = ["claudeloop-local"]\n'
    )

    assert config.engines.enabled == ("claudeloop-local", "qwenloop", "opencode")


@pytest.mark.parametrize(
    "table, match",
    [
        ('profile = "  "', "must name a claudeloop backend profile"),
        ("profile = 7", "must be a str"),
        ("context_window = 0", "must be a positive integer"),
        ("context_window = true", "must be a positive integer"),
        ('structured_verdict = "yes"', "must be a bool"),
    ],
)
def test_an_invalid_claudeloop_local_table_is_refused(table: str, match: str) -> None:
    with pytest.raises(ConfigError, match=match):
        load_config_from_string(f'[project]\nname = "x"\n\n[engines.claudeloop_local]\n{table}\n')
