# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Parsing and validation of the vibey.toml schema.

Pure: this module accepts already-loaded TOML text or a dict and returns
either a validated ``VibeyConfig`` or a list of ``ConfigError``s. It never
touches the filesystem — reading the file is an infrastructure concern.
"""

import tomllib
from dataclasses import dataclass, field
from typing import Any, ClassVar

from vibey.domain.errors import VibeyError
from vibey.domain.queue_priority import OPERATOR_SOURCE
from vibey.domain.queue_reap import (
    DEFAULT_DEAD_LETTER_MIN_DEPTH,
    DEFAULT_LEASE_GRACE_SECONDS,
    DEFAULT_STALE_READY_SECONDS,
    BrokerPolicy,
    ReapThresholds,
)

VALID_ISOLATION_LEVELS = ("worktree", "container", "vm")
VALID_EFFORTS = ("trivial", "low", "standard", "high", "max")
# The engine id is `opencode` (the provider multiplexer); `opencodeloop` is the
# wrapper binary and package that adapts it. The canonical id is what config,
# the CLI and the ledger all speak.
# The sovereign default pair (on without declaration; ADR-0060 made gptossloop, the
# local runner on GPT-OSS, the local half of it)
DEFAULT_ENGINES = ("gptossloop", "opencode")
# Local engines, each behind its own `[features]` switch (ADR-0015, ADR-0038). The
# feature key is the engine id with the hyphen a TOML bare key cannot carry.
LOCAL_ENGINE_FEATURES = {
    "gptossloop": "gptossloop",
    "qwenloop": "qwenloop",
    "claudeloop-local": "claudeloop_local",
}
# The local engines whose switch is on when nothing sets it (ADR-0060): the sovereign
# default, which a project switches off only by saying so -- `[features] gptossloop =
# false` or `VIBEY_FEATURE_GPTOSSLOOP=0`. Every other local engine is opt-in.
LOCAL_ENGINES_ON_BY_DEFAULT = frozenset({"gptossloop"})
KNOWN_ENGINES = (
    "claudeloop",
    "codexloop",
    "cursorloop",
    "agyloop",
    "opencode",
    "gptossloop",
    "qwenloop",
    "claudeloop-local",
)
# Said beside a refused request for an engine whose meaning changed, so the operator who
# configured the old one learns what it became (ADR-0060).
_SWITCH_HINTS = {
    "qwenloop": (
        " -- qwenloop runs a Qwen model since ADR-0060; the gpt-oss engine it used to be is "
        "gptossloop, on by default"
    ),
}
DEFAULT_CLAUDELOOP_LOCAL_PROFILE = "local"
DEFAULT_LOCAL_CONTEXT_WINDOW = 32_768


class ConfigError(VibeyError):
    """Raised when vibey.toml fails validation."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    name: str
    repo: str = "."
    max_cycles: int = 10
    strict_loopback: bool = False


@dataclass(frozen=True, slots=True)
class IsolationConfig:
    level: str = "worktree"
    allow_push: bool = False
    egress: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BudgetConfig:
    max_dollars_per_cycle: float | None = None
    max_dollars_total: float | None = None
    max_turns_per_item: int | None = None


@dataclass(frozen=True, slots=True)
class ClaudeloopLocalConfig:
    """`[engines.claudeloop_local]`: which claudeloop backend profile the
    claudeloop-local engine runs, and what vibey may claim about it (ADR-0038).

    - ``profile`` names a `[profiles.NAME]` table in claudeloop's own config; the
      profile, not vibey, carries the local server's ``base_url`` and the model tiers.
    - ``context_window`` is the descriptor's context window; keep it equal to the
      profile's own ``context_window`` and the server's ``OLLAMA_CONTEXT_LENGTH``.
    - ``structured_verdict`` claims the capability. Off by default: a local model
      earns it only when ``vibey doctor --conformance`` proves it for the model the
      profile configures, and a claim conformance cannot prove makes the engine
      ineligible rather than trusted.
    """

    profile: str = DEFAULT_CLAUDELOOP_LOCAL_PROFILE
    context_window: int = DEFAULT_LOCAL_CONTEXT_WINDOW
    structured_verdict: bool = False

    @classmethod
    def from_table(cls, table: dict[str, Any], path: str) -> "ClaudeloopLocalConfig":
        """Validate one already-parsed table; `path` names it in any error."""
        profile = _optional(
            table, "profile", f"{path}.profile", str, DEFAULT_CLAUDELOOP_LOCAL_PROFILE
        )
        if not profile.strip():
            raise ConfigError(f"{path}.profile", "must name a claudeloop backend profile")
        context_window = _optional(
            table, "context_window", f"{path}.context_window", int, DEFAULT_LOCAL_CONTEXT_WINDOW
        )
        if isinstance(context_window, bool) or context_window <= 0:
            raise ConfigError(f"{path}.context_window", "must be a positive integer")
        return cls(
            profile=profile.strip(),
            context_window=context_window,
            structured_verdict=_optional(
                table, "structured_verdict", f"{path}.structured_verdict", bool, False
            ),
        )


@dataclass(frozen=True, slots=True)
class EnginesConfig:
    enabled: tuple[str, ...] = DEFAULT_ENGINES
    weights: dict[str, int] = field(default_factory=dict)
    claudeloop_local: ClaudeloopLocalConfig = field(default_factory=ClaudeloopLocalConfig)


@dataclass(frozen=True, slots=True)
class PhaseConfig:
    effort: str = "standard"
    engines: tuple[str, ...] | None = None
    parallelism: int | None = None


@dataclass(frozen=True, slots=True)
class PhasesConfig:
    design: PhaseConfig = field(default_factory=lambda: PhaseConfig(effort="high"))
    build: PhaseConfig = field(default_factory=lambda: PhaseConfig(effort="low"))
    review: PhaseConfig = field(default_factory=lambda: PhaseConfig(effort="high"))


@dataclass(frozen=True, slots=True)
class ProvisionConfig:
    plugins: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DeployConfig:
    enabled: bool = False
    target: str = "openstack"
    iac: str = "bicep"


@dataclass(frozen=True, slots=True)
class NotificationWebhookConfig:
    """One signed outbound notification destination."""

    url: str
    secret: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationsConfig:
    """Operator notifications for a project.

    Notifications stay opt-in because desktop alerts and outbound webhooks are
    side effects.  Once enabled, desktop delivery defaults on and webhook
    destinations are explicit.
    """

    enabled: bool = False
    desktop: bool = True
    webhooks: tuple[NotificationWebhookConfig, ...] = ()


@dataclass(frozen=True, slots=True)
class TelemetryConfig:
    """Whether in-process spans and production rotation metrics are recorded."""

    enabled: bool = True
    export_path: str | None = None


@dataclass(frozen=True, slots=True)
class FeaturesConfig:
    # On unless switched off: the sovereign default engine (ADR-0060).
    gptossloop: bool = True
    # The same runner on a Qwen model; opt-in.
    qwenloop: bool = False
    claudeloop_local: bool = False

    def enables(self, engine: str) -> bool:
        """Whether the switch for a local engine id is on; paid engines need none."""
        key = LOCAL_ENGINE_FEATURES.get(engine)
        return key is None or bool(getattr(self, key))


@dataclass(frozen=True, slots=True)
class QwenloopConfig:
    backend: str = "auto"
    portable_profile: str = "qwen2.5-coder-14b-q5-k-m"
    nvidia_profile: str = "qwen2.5-coder-14b-bf16"
    idle_timeout_seconds: int = 900
    startup_timeout_seconds: int = 180
    context_window: int = 32_768


# The operational surfaces of ADR-0042. Each table is optional: an omitted
# table (or an omitted key) leaves the surface on its in-memory default, so a
# project runs with no external service configured at all. A real endpoint is
# how an operator declares a self-hosted sovereign service (or a paid relay).


@dataclass(frozen=True, slots=True)
class TrackerConfig:
    """`[tracker]`: the Issue Tracker surface (sovereign default: Plane).

    Plane's work-item routes are workspace-scoped
    (`/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/`),
    so both identifiers are required to address a project.
    """

    url: str | None = None
    token: str | None = None
    workspace_slug: str | None = None
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class DocsConfig:
    """`[docs]`: the Documentation surface (sovereign default: BookStack)."""

    url: str | None = None
    token_id: str | None = None
    token_secret: str | None = None
    book_id: int | None = None


@dataclass(frozen=True, slots=True)
class SecretsConfig:
    """`[secrets]`: the Secrets surface (sovereign default: OpenBao)."""

    url: str | None = None
    token: str | None = None


@dataclass(frozen=True, slots=True)
class FilesConfig:
    """`[files]`: the File storage surface (sovereign default: Nextcloud)."""

    url: str | None = None
    user: str | None = None
    password: str | None = None


@dataclass(frozen=True, slots=True)
class EmailConfig:
    """`[email]`: the Email surface (sovereign default: Forward Email)."""

    smtp_host: str | None = None
    smtp_port: int | None = None
    username: str | None = None
    password: str | None = None
    from_email: str | None = None


@dataclass(frozen=True, slots=True)
class SmsConfig:
    """`[sms]`: the SMS surface (gateway: Kannel; handsets: Fossify Messages)."""

    url: str | None = None
    username: str | None = None
    password: str | None = None
    sender: str | None = None


@dataclass(frozen=True, slots=True)
class MessagingConfig:
    """`[messaging]`: the Messaging surface (sovereign default: Matrix)."""

    url: str | None = None
    token: str | None = None
    room_id: str | None = None


@dataclass(frozen=True, slots=True)
class ConfigStoreConfig:
    """`[config_store]`: application configuration storage (default: Infisical)."""

    url: str | None = None
    token: str | None = None
    project_id: str | None = None
    environment: str = "dev"


@dataclass(frozen=True, slots=True)
class CacheConfig:
    """`[cache]`: the Cache surface (sovereign default: Redis)."""

    url: str | None = None


@dataclass(frozen=True, slots=True)
class BusConfig:
    """`[bus]`: the service-bus surface (sovereign default: RabbitMQ)."""

    url: str | None = None
    username: str | None = None
    password: str | None = None
    vhost: str = "/"
    """The vhost vibey's queues, and the reaper's reads, are scoped to (ADR-0056)."""


@dataclass(frozen=True, slots=True)
class BlobConfig:
    """`[blob]`: the Blob storage surface (sovereign default: Garage, S3 API)."""

    url: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    region: str = "us-east-1"


@dataclass(frozen=True, slots=True)
class SiemConfig:
    """`[siem]`: the SIEM surface (sovereign default: Wazuh indexer)."""

    url: str | None = None
    username: str | None = None
    password: str | None = None
    index: str = "vibey-audit"


@dataclass(frozen=True, slots=True)
class QueuePriorityConfig:
    """`[queue.priority]`: who besides the operator may move a job ahead (ADR-0054).

    ``sources`` names the automations the operator admits, each exactly as it will
    identify itself. Empty -- the default -- admits nobody but the operator: the
    absence of a grant is refusal (12.f, 12.j), and a source that relays another
    person's words (a label anyone may set, an issue comment) is a stranger however
    it is named. ``operator`` is reserved and never declared.
    """

    sources: tuple[str, ...] = ()

    @classmethod
    def from_table(cls, table: dict[str, Any], path: str) -> "QueuePriorityConfig":
        """Validate one already-parsed table; `path` names it in any error."""
        raw = _optional(table, "sources", f"{path}.sources", list, [])
        sources: list[str] = []
        for index, value in enumerate(raw):
            where = f"{path}.sources[{index}]"
            if not isinstance(value, str):
                raise ConfigError(where, "must be a string naming a declared source")
            name = value.strip()
            if not name:
                raise ConfigError(where, "must name a source, not be blank")
            if name == OPERATOR_SOURCE:
                raise ConfigError(
                    where,
                    f"{OPERATOR_SOURCE!r} is reserved: the operator is always admitted "
                    "and is never declared",
                )
            if name in sources:
                raise ConfigError(where, f"{name!r} is declared twice")
            sources.append(name)
        return cls(sources=tuple(sources))


@dataclass(frozen=True, slots=True)
class QueueReapConfig:
    """`[queue.reap]`: when queued or held work counts as stuck, and what bounds it
    (ADR-0056). Every threshold is a key (12.c); the defaults are measured choices, each
    explained in docs/reference/configuration.md.

    The same thresholds judge the PostgreSQL job queue and every queue on the broker, so
    both reap identically. The broker keys (`owned_queue_pattern`, `consumer_timeout_seconds`,
    `delivery_limit`, ...) become the policy vibey reconciles onto the queues it owns.
    """

    enabled: bool = True
    interval_seconds: int = 60
    lease_grace_seconds: int = DEFAULT_LEASE_GRACE_SECONDS
    stale_ready_seconds: int = DEFAULT_STALE_READY_SECONDS
    dead_letter_min_depth: int = DEFAULT_DEAD_LETTER_MIN_DEPTH
    dead_letter_peek_limit: int = 100
    owned_queue_pattern: str = r"^vibey\."
    dead_letter_queue_pattern: str = r"(\.dlq|\.dead)$"
    policy_name: str = "vibey-reap"
    policy_priority: int = 0
    consumer_timeout_seconds: int = 21600
    """Six hours: at least the longest job lease (two hours for BUILD) with room, the
    ADR-0044 default. Applies to vibey's own queues only; the broker-wide default is the
    chart's `surfaces.rabbitmq.consumerTimeoutMs`."""
    delivery_limit: int = 20

    _POSITIVE: ClassVar[tuple[str, ...]] = (
        "interval_seconds",
        "stale_ready_seconds",
        "dead_letter_min_depth",
        "dead_letter_peek_limit",
        "consumer_timeout_seconds",
        "delivery_limit",
    )

    def __post_init__(self) -> None:
        for name in self._POSITIVE:
            if getattr(self, name) < 1:
                raise ConfigError(f"queue.reap.{name}", "must be at least 1")
        if self.lease_grace_seconds < 0:
            raise ConfigError("queue.reap.lease_grace_seconds", "must not be negative")
        try:
            self.broker_policy()
        except ValueError as exc:
            raise ConfigError("queue.reap", str(exc)) from exc

    @classmethod
    def from_table(cls, table: dict[str, Any], path: str) -> "QueueReapConfig":
        """Validate one already-parsed table; `path` names it in any error."""
        values: dict[str, Any] = {}
        for key in cls.__dataclass_fields__:
            if key not in table:
                continue
            default = getattr(cls(), key)
            value = table[key]
            # bool is an int to isinstance; a threshold written `true` is a mistake.
            if type(value) is not type(default):
                raise ConfigError(
                    f"{path}.{key}",
                    f"must be a {type(default).__name__}, got {type(value).__name__}",
                )
            values[key] = value
        unknown = sorted(set(table) - set(cls.__dataclass_fields__))
        if unknown:
            raise ConfigError(f"{path}.{unknown[0]}", "is not a [queue.reap] key")
        return cls(**values)

    def thresholds(self) -> ReapThresholds:
        return ReapThresholds(
            lease_grace_seconds=self.lease_grace_seconds,
            stale_ready_seconds=self.stale_ready_seconds,
            dead_letter_min_depth=self.dead_letter_min_depth,
        )

    def broker_policy(self) -> BrokerPolicy:
        return BrokerPolicy(
            name=self.policy_name,
            pattern=self.owned_queue_pattern,
            consumer_timeout_ms=self.consumer_timeout_seconds * 1000,
            delivery_limit=self.delivery_limit,
            priority=self.policy_priority,
            dead_letter_pattern=self.dead_letter_queue_pattern,
        )


@dataclass(frozen=True, slots=True)
class QueueConfig:
    """`[queue]`: the job queue's declared policy."""

    priority: QueuePriorityConfig = field(default_factory=QueuePriorityConfig)
    reap: QueueReapConfig = field(default_factory=QueueReapConfig)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> "QueueConfig":
        """Read `[queue]` from a whole parsed document. Needs nothing else in it, so a
        reader that wants only the queue policy does not demand `[project]`."""
        table = _optional(data, "queue", "queue", dict, {})
        priority = _optional(table, "priority", "queue.priority", dict, {})
        reap = _optional(table, "reap", "queue.reap", dict, {})
        return cls(
            priority=QueuePriorityConfig.from_table(priority, "queue.priority"),
            reap=QueueReapConfig.from_table(reap, "queue.reap"),
        )


@dataclass(frozen=True, slots=True)
class VibeyConfig:
    project: ProjectConfig
    isolation: IsolationConfig = field(default_factory=IsolationConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    engines: EnginesConfig = field(default_factory=EnginesConfig)
    phases: PhasesConfig = field(default_factory=PhasesConfig)
    provision: ProvisionConfig = field(default_factory=ProvisionConfig)
    deploy: DeployConfig = field(default_factory=DeployConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    qwenloop: QwenloopConfig = field(default_factory=QwenloopConfig)
    tracker: TrackerConfig = field(default_factory=TrackerConfig)
    docs: DocsConfig = field(default_factory=DocsConfig)
    secrets: SecretsConfig = field(default_factory=SecretsConfig)
    files: FilesConfig = field(default_factory=FilesConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    sms: SmsConfig = field(default_factory=SmsConfig)
    messaging: MessagingConfig = field(default_factory=MessagingConfig)
    config_store: ConfigStoreConfig = field(default_factory=ConfigStoreConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    bus: BusConfig = field(default_factory=BusConfig)
    blob: BlobConfig = field(default_factory=BlobConfig)
    siem: SiemConfig = field(default_factory=SiemConfig)
    queue: QueueConfig = field(default_factory=QueueConfig)


def parse_toml_string(text: str) -> dict[str, Any]:
    return tomllib.loads(text)


def _require(table: dict[str, Any], key: str, path: str, type_: type) -> Any:
    if key not in table:
        raise ConfigError(path, f"missing required field {key!r}")
    value = table[key]
    if not isinstance(value, type_):
        raise ConfigError(path, f"{key!r} must be a {type_.__name__}, got {type(value).__name__}")
    return value


def _optional(table: dict[str, Any], key: str, path: str, type_: type, default: Any) -> Any:
    if key not in table:
        return default
    value = table[key]
    if not isinstance(value, type_):
        raise ConfigError(path, f"{key!r} must be a {type_.__name__}, got {type(value).__name__}")
    return value


def _parse_project(data: dict[str, Any]) -> ProjectConfig:
    table = _optional(data, "project", "project", dict, {})
    if "name" not in table:
        raise ConfigError("project.name", "missing required field 'name'")
    return ProjectConfig(
        name=_require(table, "name", "project.name", str),
        repo=_optional(table, "repo", "project.repo", str, "."),
        max_cycles=_optional(table, "max_cycles", "project.max_cycles", int, 10),
        strict_loopback=_optional(table, "strict_loopback", "project.strict_loopback", bool, False),
    )


def _parse_isolation(data: dict[str, Any]) -> IsolationConfig:
    table = _optional(data, "isolation", "isolation", dict, {})
    level = _optional(table, "level", "isolation.level", str, "worktree")
    if level not in VALID_ISOLATION_LEVELS:
        raise ConfigError(
            "isolation.level", f"must be one of {VALID_ISOLATION_LEVELS}, got {level!r}"
        )
    egress = _optional(table, "egress", "isolation.egress", list, [])
    return IsolationConfig(
        level=level,
        allow_push=_optional(table, "allow_push", "isolation.allow_push", bool, False),
        egress=tuple(egress),
    )


def _parse_budget(data: dict[str, Any]) -> BudgetConfig:
    table = _optional(data, "budget", "budget", dict, {})
    return BudgetConfig(
        max_dollars_per_cycle=table.get("max_dollars_per_cycle"),
        max_dollars_total=table.get("max_dollars_total"),
        max_turns_per_item=table.get("max_turns_per_item"),
    )


def _parse_engines(data: dict[str, Any], features: FeaturesConfig) -> EnginesConfig:
    table = _optional(data, "engines", "engines", dict, {})
    # The sovereign pair are on without declaration. The one way one leaves the pool is
    # the declaration its own switch is for (gptossloop's `[features] gptossloop =
    # false`); nothing else -- an `enabled` list that omits it included -- removes it.
    sovereign = tuple(engine for engine in DEFAULT_ENGINES if features.enables(engine))
    enabled = tuple(_optional(table, "enabled", "engines.enabled", list, list(sovereign)))
    for default in sovereign:
        if default not in enabled:
            enabled = (*enabled, default)
    for engine in enabled:
        if engine not in KNOWN_ENGINES:
            raise ConfigError("engines.enabled", f"unknown engine {engine!r}")
    weights = _optional(table, "weights", "engines.weights", dict, {})
    for engine in weights:
        if engine not in KNOWN_ENGINES:
            raise ConfigError("engines.weights", f"unknown engine {engine!r}")
    local = _optional(table, "claudeloop_local", "engines.claudeloop_local", dict, {})
    return EnginesConfig(
        enabled=enabled,
        weights=dict(weights),
        claudeloop_local=ClaudeloopLocalConfig.from_table(local, "engines.claudeloop_local"),
    )


def _parse_phase(table: dict[str, Any], path: str, default_effort: str) -> PhaseConfig:
    effort = _optional(table, "effort", f"{path}.effort", str, default_effort)
    if effort not in VALID_EFFORTS:
        raise ConfigError(f"{path}.effort", f"must be one of {VALID_EFFORTS}, got {effort!r}")
    engines_raw = table.get("engines")
    engines = tuple(engines_raw) if engines_raw is not None else None
    parallelism = table.get("parallelism")
    return PhaseConfig(effort=effort, engines=engines, parallelism=parallelism)


def _parse_phases(data: dict[str, Any]) -> PhasesConfig:
    table = _optional(data, "phases", "phases", dict, {})
    design = _optional(table, "design", "phases.design", dict, {})
    build = _optional(table, "build", "phases.build", dict, {})
    review = _optional(table, "review", "phases.review", dict, {})
    return PhasesConfig(
        design=_parse_phase(design, "phases.design", "high"),
        build=_parse_phase(build, "phases.build", "low"),
        review=_parse_phase(review, "phases.review", "high"),
    )


def _parse_provision(data: dict[str, Any]) -> ProvisionConfig:
    table = _optional(data, "provision", "provision", dict, {})
    plugins = tuple(_optional(table, "plugins", "provision.plugins", list, []))
    return ProvisionConfig(plugins=plugins)


def _parse_deploy(data: dict[str, Any]) -> DeployConfig:
    table = _optional(data, "deploy", "deploy", dict, {})
    return DeployConfig(
        enabled=_optional(table, "enabled", "deploy.enabled", bool, False),
        target=_optional(table, "target", "deploy.target", str, "openstack"),
        iac=_optional(table, "iac", "deploy.iac", str, "bicep"),
    )


def _parse_notifications(data: dict[str, Any]) -> NotificationsConfig:
    table = _optional(data, "notifications", "notifications", dict, {})
    raw_webhooks = _optional(table, "webhooks", "notifications.webhooks", list, [])
    webhooks: list[NotificationWebhookConfig] = []
    for index, raw_webhook in enumerate(raw_webhooks):
        path = f"notifications.webhooks[{index}]"
        if not isinstance(raw_webhook, dict):
            raise ConfigError(path, "must be a table")
        url = _require(raw_webhook, "url", f"{path}.url", str).strip()
        if not url:
            raise ConfigError(f"{path}.url", "must not be empty")
        secret = raw_webhook.get("secret")
        if secret is not None and not isinstance(secret, str):
            raise ConfigError(f"{path}.secret", "must be a str or omitted")
        webhooks.append(NotificationWebhookConfig(url=url, secret=secret))
    return NotificationsConfig(
        enabled=_optional(table, "enabled", "notifications.enabled", bool, False),
        desktop=_optional(table, "desktop", "notifications.desktop", bool, True),
        webhooks=tuple(webhooks),
    )


def _parse_telemetry(data: dict[str, Any]) -> TelemetryConfig:
    table = _optional(data, "telemetry", "telemetry", dict, {})
    export_path = table.get("export_path")
    if export_path is not None and not isinstance(export_path, str):
        raise ConfigError("telemetry.export_path", "must be a str or omitted")
    return TelemetryConfig(
        enabled=_optional(table, "enabled", "telemetry.enabled", bool, True),
        export_path=export_path,
    )


def _parse_features(data: dict[str, Any]) -> FeaturesConfig:
    table = _optional(data, "features", "features", dict, {})
    return FeaturesConfig(
        gptossloop=_optional(table, "gptossloop", "features.gptossloop", bool, True),
        qwenloop=_optional(table, "qwenloop", "features.qwenloop", bool, False),
        claudeloop_local=_optional(
            table, "claudeloop_local", "features.claudeloop_local", bool, False
        ),
    )


def _parse_qwenloop(data: dict[str, Any]) -> QwenloopConfig:
    table = _optional(data, "qwenloop", "qwenloop", dict, {})
    backend = _optional(table, "backend", "qwenloop.backend", str, "auto")
    if backend not in {"auto", "llama.cpp", "vllm"}:
        raise ConfigError("qwenloop.backend", "must be one of ('auto', 'llama.cpp', 'vllm')")
    result = QwenloopConfig(
        backend=backend,
        portable_profile=_optional(
            table, "portable_profile", "qwenloop.portable_profile", str, "qwen2.5-coder-14b-q5-k-m"
        ),
        nvidia_profile=_optional(
            table, "nvidia_profile", "qwenloop.nvidia_profile", str, "qwen2.5-coder-14b-bf16"
        ),
        idle_timeout_seconds=_optional(
            table, "idle_timeout_seconds", "qwenloop.idle_timeout_seconds", int, 900
        ),
        startup_timeout_seconds=_optional(
            table, "startup_timeout_seconds", "qwenloop.startup_timeout_seconds", int, 180
        ),
        context_window=_optional(table, "context_window", "qwenloop.context_window", int, 32_768),
    )
    if result.idle_timeout_seconds < 0:
        raise ConfigError("qwenloop.idle_timeout_seconds", "must be non-negative")
    if result.startup_timeout_seconds <= 0 or result.context_window <= 0:
        raise ConfigError("qwenloop", "startup_timeout_seconds and context_window must be positive")
    return result


def _parse_tracker(data: dict[str, Any]) -> TrackerConfig:
    table = _optional(data, "tracker", "tracker", dict, {})
    return TrackerConfig(
        url=_optional(table, "url", "tracker.url", str, None),
        token=_optional(table, "token", "tracker.token", str, None),
        workspace_slug=_optional(table, "workspace_slug", "tracker.workspace_slug", str, None),
        project_id=_optional(table, "project_id", "tracker.project_id", str, None),
    )


def _parse_docs(data: dict[str, Any]) -> DocsConfig:
    table = _optional(data, "docs", "docs", dict, {})
    book_id = table.get("book_id")
    if book_id is not None and (isinstance(book_id, bool) or not isinstance(book_id, int)):
        raise ConfigError("docs.book_id", "must be an integer or omitted")
    return DocsConfig(
        url=_optional(table, "url", "docs.url", str, None),
        token_id=_optional(table, "token_id", "docs.token_id", str, None),
        token_secret=_optional(table, "token_secret", "docs.token_secret", str, None),
        book_id=book_id,
    )


def _parse_secrets(data: dict[str, Any]) -> SecretsConfig:
    table = _optional(data, "secrets", "secrets", dict, {})
    return SecretsConfig(
        url=_optional(table, "url", "secrets.url", str, None),
        token=_optional(table, "token", "secrets.token", str, None),
    )


def _parse_files(data: dict[str, Any]) -> FilesConfig:
    table = _optional(data, "files", "files", dict, {})
    return FilesConfig(
        url=_optional(table, "url", "files.url", str, None),
        user=_optional(table, "user", "files.user", str, None),
        password=_optional(table, "password", "files.password", str, None),
    )


def _parse_email(data: dict[str, Any]) -> EmailConfig:
    table = _optional(data, "email", "email", dict, {})
    smtp_port = table.get("smtp_port")
    if smtp_port is not None and (isinstance(smtp_port, bool) or not isinstance(smtp_port, int)):
        raise ConfigError("email.smtp_port", "must be an integer or omitted")
    return EmailConfig(
        smtp_host=_optional(table, "smtp_host", "email.smtp_host", str, None),
        smtp_port=smtp_port,
        username=_optional(table, "username", "email.username", str, None),
        password=_optional(table, "password", "email.password", str, None),
        from_email=_optional(table, "from_email", "email.from_email", str, None),
    )


def _parse_sms(data: dict[str, Any]) -> SmsConfig:
    table = _optional(data, "sms", "sms", dict, {})
    return SmsConfig(
        url=_optional(table, "url", "sms.url", str, None),
        username=_optional(table, "username", "sms.username", str, None),
        password=_optional(table, "password", "sms.password", str, None),
        sender=_optional(table, "sender", "sms.sender", str, None),
    )


def _parse_messaging(data: dict[str, Any]) -> MessagingConfig:
    table = _optional(data, "messaging", "messaging", dict, {})
    return MessagingConfig(
        url=_optional(table, "url", "messaging.url", str, None),
        token=_optional(table, "token", "messaging.token", str, None),
        room_id=_optional(table, "room_id", "messaging.room_id", str, None),
    )


def _parse_config_store(data: dict[str, Any]) -> ConfigStoreConfig:
    table = _optional(data, "config_store", "config_store", dict, {})
    return ConfigStoreConfig(
        url=_optional(table, "url", "config_store.url", str, None),
        token=_optional(table, "token", "config_store.token", str, None),
        project_id=_optional(table, "project_id", "config_store.project_id", str, None),
        environment=_optional(table, "environment", "config_store.environment", str, "dev"),
    )


def _parse_cache(data: dict[str, Any]) -> CacheConfig:
    table = _optional(data, "cache", "cache", dict, {})
    return CacheConfig(
        url=_optional(table, "url", "cache.url", str, None),
    )


def _parse_bus(data: dict[str, Any]) -> BusConfig:
    table = _optional(data, "bus", "bus", dict, {})
    return BusConfig(
        url=_optional(table, "url", "bus.url", str, None),
        username=_optional(table, "username", "bus.username", str, None),
        password=_optional(table, "password", "bus.password", str, None),
        vhost=_optional(table, "vhost", "bus.vhost", str, "/"),
    )


def _parse_blob(data: dict[str, Any]) -> BlobConfig:
    table = _optional(data, "blob", "blob", dict, {})
    return BlobConfig(
        url=_optional(table, "url", "blob.url", str, None),
        access_key=_optional(table, "access_key", "blob.access_key", str, None),
        secret_key=_optional(table, "secret_key", "blob.secret_key", str, None),
        region=_optional(table, "region", "blob.region", str, "us-east-1"),
    )


def _parse_siem(data: dict[str, Any]) -> SiemConfig:
    table = _optional(data, "siem", "siem", dict, {})
    return SiemConfig(
        url=_optional(table, "url", "siem.url", str, None),
        username=_optional(table, "username", "siem.username", str, None),
        password=_optional(table, "password", "siem.password", str, None),
        index=_optional(table, "index", "siem.index", str, "vibey-audit"),
    )


def parse_config(data: dict[str, Any]) -> VibeyConfig:
    """Validate an already-parsed TOML dict and build a VibeyConfig.

    Raises ConfigError on the first violation found.
    """
    features = _parse_features(data)
    engines = _parse_engines(data, features)
    phase_engines = (
        *(
            _optional(
                _optional(data, "phases", "phases", dict, {}), "design", "phases.design", dict, {}
            ).get("engines")
            or []
        ),
        *(
            _optional(
                _optional(data, "phases", "phases", dict, {}), "build", "phases.build", dict, {}
            ).get("engines")
            or []
        ),
        *(
            _optional(
                _optional(data, "phases", "phases", dict, {}), "review", "phases.review", dict, {}
            ).get("engines")
            or []
        ),
    )
    for engine, key in LOCAL_ENGINE_FEATURES.items():
        if not features.enables(engine) and (engine in engines.enabled or engine in phase_engines):
            hint = _SWITCH_HINTS.get(engine, "")
            raise ConfigError(
                f"features.{key}", f"must be true before {engine} can be requested{hint}"
            )
    if "enabled" not in _optional(data, "engines", "engines", dict, {}):
        # An omitted pool is the default pool plus every local engine switched on.
        switched_on = tuple(e for e in LOCAL_ENGINE_FEATURES if features.enables(e))
        unique_enabled: list[str] = []
        for e in (*engines.enabled, *switched_on):
            if e not in unique_enabled:
                unique_enabled.append(e)
        engines = EnginesConfig(
            enabled=tuple(unique_enabled),
            weights=engines.weights,
            claudeloop_local=engines.claudeloop_local,
        )
    return VibeyConfig(
        project=_parse_project(data),
        isolation=_parse_isolation(data),
        budget=_parse_budget(data),
        engines=engines,
        phases=_parse_phases(data),
        provision=_parse_provision(data),
        deploy=_parse_deploy(data),
        notifications=_parse_notifications(data),
        telemetry=_parse_telemetry(data),
        features=features,
        qwenloop=_parse_qwenloop(data),
        tracker=_parse_tracker(data),
        docs=_parse_docs(data),
        secrets=_parse_secrets(data),
        files=_parse_files(data),
        email=_parse_email(data),
        sms=_parse_sms(data),
        messaging=_parse_messaging(data),
        config_store=_parse_config_store(data),
        cache=_parse_cache(data),
        bus=_parse_bus(data),
        blob=_parse_blob(data),
        siem=_parse_siem(data),
        queue=QueueConfig.from_data(data),
    )


def load_config_from_string(text: str) -> VibeyConfig:
    return parse_config(parse_toml_string(text))
