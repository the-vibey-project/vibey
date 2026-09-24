# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vibey.domain.config import (
    ConfigError,
    QueueConfig,
    VibeyConfig,
    parse_config,
    parse_toml_string,
)
from vibey.infrastructure.engines.local_engines import LOCAL_ENGINE_SWITCHES
from vibey.infrastructure.interfaces.class_contracts import (
    EnvironmentConfigLoaderInterface,
    QueueConfigLoaderInterface,
)

RUNTIME_CONFIG_KEYS = ("notifications", "telemetry")

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
    ("bus", "vhost", "VIBEY_BUS_VHOST", str),
)

# `[queue.reap]` (ADR-0056): the reaper's thresholds and the broker policy they declare.
# A dotted table is a nested one. In a cluster the chart renders these from
# `worker.queueReap`, so the thresholds are code there too (12.c).
_QUEUE_REAP_ENV_VARS: tuple[tuple[str, str, str, type], ...] = (
    ("queue.reap", "enabled", "VIBEY_QUEUE_REAP_ENABLED", bool),
    ("queue.reap", "interval_seconds", "VIBEY_QUEUE_REAP_INTERVAL_SECONDS", int),
    ("queue.reap", "lease_grace_seconds", "VIBEY_QUEUE_REAP_LEASE_GRACE_SECONDS", int),
    ("queue.reap", "stale_ready_seconds", "VIBEY_QUEUE_REAP_STALE_READY_SECONDS", int),
    ("queue.reap", "dead_letter_min_depth", "VIBEY_QUEUE_REAP_DEAD_LETTER_MIN_DEPTH", int),
    ("queue.reap", "dead_letter_peek_limit", "VIBEY_QUEUE_REAP_DEAD_LETTER_PEEK_LIMIT", int),
    ("queue.reap", "owned_queue_pattern", "VIBEY_QUEUE_REAP_OWNED_QUEUE_PATTERN", str),
    ("queue.reap", "dead_letter_queue_pattern", "VIBEY_QUEUE_REAP_DEAD_LETTER_QUEUE_PATTERN", str),
    ("queue.reap", "policy_name", "VIBEY_QUEUE_REAP_POLICY_NAME", str),
    ("queue.reap", "policy_priority", "VIBEY_QUEUE_REAP_POLICY_PRIORITY", int),
    ("queue.reap", "consumer_timeout_seconds", "VIBEY_QUEUE_REAP_CONSUMER_TIMEOUT_SECONDS", int),
    ("queue.reap", "delivery_limit", "VIBEY_QUEUE_REAP_DELIVERY_LIMIT", int),
)

_TRUE: Final = frozenset({"1", "true", "yes", "on"})
_FALSE: Final = frozenset({"0", "false", "no", "off"})


def apply_env_overrides(
    data: dict[str, Any], environ: Mapping[str, str] = os.environ
) -> dict[str, Any]:
    """Overlay surface and `[queue.reap]` environment variables onto parsed TOML data,
    in place. A dotted table name is a nested table."""
    for table, key, variable, cast in (*_SURFACE_ENV_VARS, *_QUEUE_REAP_ENV_VARS):
        raw = environ.get(variable)
        if raw is None or not raw.strip():
            continue
        section: Any = data
        for part in table.split("."):
            section = section.setdefault(part, {})
            if not isinstance(section, dict):
                raise ValueError(f"{table} must be a table")
        value = raw.strip()
        if cast is int:
            try:
                section[key] = int(value)
            except ValueError:
                raise ValueError(f"{variable} must be an integer") from None
        elif cast is bool:
            lowered = value.lower()
            if lowered not in _TRUE | _FALSE:
                raise ValueError(f"{variable} must be a boolean value")
            section[key] = lowered in _TRUE
        else:
            section[key] = value
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
    return runtime


class QueueConfigLoader:
    """Reads `[queue]` from a vibey.toml, and only `[queue]` (ADR-0054).

    The queue-priority grant reader needs the queue policy and nothing else, so it does
    not demand the `[project]` table a whole-document parse requires. A missing file declares no
    source: the operator alone may reorder the queue, which is the default the
    absence of a grant means (12.f, 12.j). A malformed file raises -- a declaration
    that cannot be read is not the same fact as no declaration (10.f).
    """

    def load(self, path: Path) -> QueueConfig:
        try:
            text = path.read_text()
        except FileNotFoundError:
            return QueueConfig()
        except (OSError, UnicodeDecodeError) as exc:
            # A file that is there and cannot be read -- no permission, a directory, not
            # text -- is not the same fact as no file, and must never read as one.
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc
        try:
            data = parse_toml_string(text)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc
        return QueueConfig.from_data(data)


QUEUE_CONFIG: Final[QueueConfigLoaderInterface] = QueueConfigLoader()
"""The loader the queue-priority grant is read through. Stateless, so one instance serves."""


class EnvironmentConfigLoader:
    """What the environment alone declares, for a process with no vibey.toml.

    In a cluster the chart renders every operational endpoint into the worker's
    environment and puts no vibey.toml in its working directory (`/work`, the worktrees
    volume). `build_app` reads the environment overlay only through a vibey.toml, so the
    bus and the reaper's thresholds were never composed there (ADR-0056). This reads the
    same overlay on its own, under a placeholder project name nothing else sees.
    """

    PLACEHOLDER_PROJECT: Final = "environment"

    def load(self, environ: Mapping[str, str] = os.environ) -> VibeyConfig:
        data = apply_env_overrides({"project": {"name": self.PLACEHOLDER_PROJECT}}, environ)
        return parse_config(data)


ENVIRONMENT_CONFIG: Final[EnvironmentConfigLoaderInterface] = EnvironmentConfigLoader()
