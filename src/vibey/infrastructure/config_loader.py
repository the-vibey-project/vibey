# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from vibey.domain.config import VibeyConfig, parse_config, parse_toml_string
from vibey.infrastructure.build.gate_runner import SubprocessGateRunner
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.engines.local_engines import LOCAL_ENGINE_SWITCHES

# The tables `vibey new` copies from vibey.toml into the project record. `gates` and
# `engine_environment` decide what a gate command and an engine session may see of the
# worker's environment; they are declared here, never hand-edited into the record.
RUNTIME_CONFIG_KEYS = ("notifications", "telemetry", "gates", "engine_environment")

# Every operational surface's environment overlay: (table, key, variable,
# cast). An empty variable counts as unset, the way the Ollama client treats
# one. Set values beat the file -- in a cluster the chart renders endpoint
# URLs from its own values and injects tokens from Secrets, so no vibey.toml
# has to exist at all.
_SURFACE_ENV_VARS: tuple[tuple[str, str, str, type], ...] = (
    ("tracker", "url", "VIBEY_TRACKER_URL", str),
    ("tracker", "token", "VIBEY_TRACKER_TOKEN", str),
    ("tracker", "workspace_slug", "VIBEY_TRACKER_WORKSPACE_SLUG", str),
    ("tracker", "project_id", "VIBEY_TRACKER_PROJECT_ID", str),
    ("docs", "url", "VIBEY_DOCS_URL", str),
    ("docs", "token_id", "VIBEY_DOCS_TOKEN_ID", str),
    ("docs", "token_secret", "VIBEY_DOCS_TOKEN_SECRET", str),
    ("docs", "book_id", "VIBEY_DOCS_BOOK_ID", int),
    ("secrets", "url", "VIBEY_SECRETS_URL", str),
    ("secrets", "token", "VIBEY_SECRETS_TOKEN", str),
    ("files", "url", "VIBEY_FILES_URL", str),
    ("files", "user", "VIBEY_FILES_USER", str),
    ("files", "password", "VIBEY_FILES_PASSWORD", str),
    ("email", "smtp_host", "VIBEY_EMAIL_SMTP_HOST", str),
    ("email", "smtp_port", "VIBEY_EMAIL_SMTP_PORT", int),
    ("email", "username", "VIBEY_EMAIL_USERNAME", str),
    ("email", "password", "VIBEY_EMAIL_PASSWORD", str),
    ("email", "from_email", "VIBEY_EMAIL_FROM", str),
    ("sms", "url", "VIBEY_SMS_URL", str),
    ("sms", "username", "VIBEY_SMS_USERNAME", str),
    ("sms", "password", "VIBEY_SMS_PASSWORD", str),
    ("sms", "sender", "VIBEY_SMS_SENDER", str),
    ("messaging", "url", "VIBEY_MESSAGING_URL", str),
    ("messaging", "token", "VIBEY_MESSAGING_TOKEN", str),
    ("messaging", "room_id", "VIBEY_MESSAGING_ROOM_ID", str),
    ("config_store", "url", "VIBEY_CONFIG_STORE_URL", str),
    ("config_store", "token", "VIBEY_CONFIG_STORE_TOKEN", str),
    ("config_store", "project_id", "VIBEY_CONFIG_STORE_PROJECT_ID", str),
    ("config_store", "environment", "VIBEY_CONFIG_STORE_ENVIRONMENT", str),
    ("cache", "url", "VIBEY_CACHE_URL", str),
    ("bus", "url", "VIBEY_BUS_URL", str),
    ("bus", "username", "VIBEY_BUS_USERNAME", str),
    ("bus", "password", "VIBEY_BUS_PASSWORD", str),
    ("blob", "url", "VIBEY_BLOB_URL", str),
    ("blob", "access_key", "VIBEY_BLOB_ACCESS_KEY", str),
    ("blob", "secret_key", "VIBEY_BLOB_SECRET_KEY", str),
    ("blob", "region", "VIBEY_BLOB_REGION", str),
    ("siem", "url", "VIBEY_SIEM_URL", str),
    ("siem", "username", "VIBEY_SIEM_USERNAME", str),
    ("siem", "password", "VIBEY_SIEM_PASSWORD", str),
    ("siem", "index", "VIBEY_SIEM_INDEX", str),
)


def apply_env_overrides(
    data: dict[str, Any], environ: Mapping[str, str] = os.environ
) -> dict[str, Any]:
    """Overlay surface environment variables onto parsed TOML data, in place."""
    for table, key, variable, cast in _SURFACE_ENV_VARS:
        raw = environ.get(variable)
        if raw is None or not raw.strip():
            continue
        section = data.setdefault(table, {})
        if not isinstance(section, dict):
            raise ValueError(f"{table} must be a table")
        if cast is int:
            try:
                section[key] = int(raw.strip())
            except ValueError:
                raise ValueError(f"{variable} must be an integer") from None
        else:
            section[key] = raw.strip()
    return data


def load_config_from_path(path: Path) -> VibeyConfig:
    data = parse_toml_string(path.read_text())
    # Every local engine's environment switch overrides its `[features]` key -- the
    # same switches, from the same table, `LocalEngineSettings` reads for the worker.
    # Unlike that resolver, validation refuses a value that is not a boolean at all.
    for switch in LOCAL_ENGINE_SWITCHES:
        override = os.environ.get(switch.env_var)
        if override is None:
            continue
        normalized = override.strip().lower()
        if normalized not in {"0", "1", "false", "true", "no", "yes", "off", "on"}:
            raise ValueError(f"{switch.env_var} must be a boolean value")
        features = data.setdefault("features", {})
        if not isinstance(features, dict):
            raise ValueError("features must be a table")
        features[switch.feature_key] = normalized in {"1", "true", "yes", "on"}
    apply_env_overrides(data)
    return parse_config(data)


def load_runtime_config_from_path(path: Path) -> dict[str, object]:
    """Load the opt-in runtime tables copied into a project's stored config.

    ``vibey new`` historically stores a small JSON config rather than the
    whole TOML document.  Keep that compatibility shape, but make the
    notification and telemetry tables in ``vibey.toml`` effective at runtime.
    A missing file is normal for projects created with CLI-only settings.
    Other TOML errors remain visible to the caller so an operator cannot
    believe a malformed configuration was accepted.
    """
    if not path.is_file():
        return {}
    data = parse_toml_string(path.read_text())
    runtime = {key: data[key] for key in RUNTIME_CONFIG_KEYS if key in data}
    if runtime:
        # Validate the same tables with the domain parser before copying them
        # into the project's stored JSON.  A synthetic project name lets this
        # narrow loader validate only the runtime tables; the CLI supplies the
        # real project record separately.
        parse_config({"project": {"name": "runtime-config"}, **runtime})
        # The child-environment tables are the worker's own objects, validated by the
        # parsers the worker builds them with -- so a forbidden declaration (a VIBEY_*
        # name, libpq's PG*, a DSN) is refused here, before anything is stored.
        SubprocessGateRunner.from_config(runtime)
        EngineEnvironmentPolicy.from_config(runtime)
    return runtime
