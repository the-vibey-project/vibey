# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-cluster preflight: the wiring checks a deployed worker cannot make
for itself, but which decide whether it will work at all.

Every check here corresponds to a way a chart install has actually failed
or could silently half-work. A worker that starts, logs "worker started",
and reports Ready can still be unable to create a worktree, unable to
authenticate any engine, or wired to a DSN that its own autoscaler cannot
resolve. None of those surface as a crash; they surface as work that
never gets done.
"""

import ipaddress
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

import asyncpg

from vibey.domain.engine import EngineDescriptor, EngineId
from vibey.infrastructure.db.interfaces import (
    LedgerGuardInspectorInterface,
    LocalAuthProbeInterface,
)
from vibey.infrastructure.db.ledger_guard import LedgerGuardInspector
from vibey.infrastructure.db.local_auth import AuthVerdict, LocalAuthProbe
from vibey.infrastructure.db.migrator import discover_migrations
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID, DEFAULT_DESCRIPTORS
from vibey.infrastructure.interfaces.cluster_preflight_interface import (
    DatabaseSecurityChecksInterface,
    EngineAuthCheckInterface,
)
from vibey.infrastructure.postgres import POSTGRES_MIN_MAJOR, parse_postgres_server_version


@dataclass(frozen=True, slots=True)
class ClusterCheck:
    name: str
    ok: bool
    detail: str = ""
    # Could not be determined either way. Not a failure, and never printed as a pass.
    unknown: bool = False

    @property
    def mark(self) -> str:
        if not self.ok:
            return "FAIL"
        return "UNKNOWN" if self.unknown else "PASS"


# Subscription login is a TTY flow and does not exist in a cluster, so an
# engine in a container authenticates by API key or not at all. These are
# the variables each runner's own doctor_env looks for.
ENGINE_API_KEY_ENVS: Mapping[EngineId, tuple[str, ...]] = {
    EngineId.CLAUDELOOP: ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"),
    EngineId.CODEXLOOP: ("OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "CODEX_API_KEY"),
    EngineId.CURSORLOOP: ("CURSOR_API_KEY",),
    EngineId.AGYLOOP: ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"),
}

# Which engine each `vibey worker --provider` drives for DESIGN/decompose. Only
# claudeloop is an engine subprocess there: `scripted` runs no engine at all, and
# the qwenloop provider talks to a local Ollama over HTTP rather than running the
# `qwenloop` binary (infrastructure/engines/qwenloop_design.py), so neither puts an
# engine under this check. The keys are the worker's accepted --provider values.
PROVIDER_ENGINES: Mapping[str, EngineId | None] = {
    "scripted": None,
    "claudeloop": EngineId.CLAUDELOOP,
    "qwenloop": None,
    "opencode": EngineId.OPENCODE,
}

_ALWAYS_RESOLVABLE = frozenset({"localhost"})


def _resolves_beyond_namespace(host: str) -> bool:
    if host in _ALWAYS_RESOLVABLE:
        return True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return "." in host
    return True


def check_dsn_resolves_cluster_wide(dsn: str) -> ClusterCheck:
    """A bare Service name resolves only from inside its own namespace.

    The worker is in that namespace, so it never notices. KEDA's operator
    is not: it dials Postgres itself to evaluate the scaler query, and an
    unqualified DSN fails there and nowhere else. That is exactly how one
    shipped once.
    """
    host = urlsplit(dsn).hostname
    if host is None:
        return ClusterCheck("dsn-host", False, "DSN has no host component")
    if _resolves_beyond_namespace(host):
        return ClusterCheck("dsn-host", True, host)
    return ClusterCheck(
        "dsn-host",
        False,
        f"{host!r} is a bare name -- it resolves only inside this namespace. "
        "Readers outside it (KEDA's operator, notably) cannot. "
        "Use <service>.<namespace>.svc.<clusterDomain>.",
    )


def check_not_root(uid: int) -> ClusterCheck:
    """The chart runs the pod as uid 10001 with allowPrivilegeEscalation
    false. Running as root means that security context was lost."""
    if uid == 0:
        return ClusterCheck("non-root", False, "running as root (uid 0)")
    return ClusterCheck("non-root", True, f"uid {uid}")


def check_workspace_writable(workspace: Path) -> ClusterCheck:
    """BUILD phase work happens in real git worktrees the worker creates
    itself. A read-only or wrongly-owned volume fails at the first one,
    long after the pod reports Ready."""
    probe = workspace / ".vibey-preflight"
    try:
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        return ClusterCheck("workspace-writable", False, f"{workspace}: {exc}")
    return ClusterCheck("workspace-writable", True, str(workspace))


class EngineAuthCheck:
    """Judges engine credentials against the engines the worker will actually use.

    Since ADR-0037 every runner ships in the image, so ``which`` finds all five
    paid engines in every pod, including a default chart install that runs
    ``--provider scripted`` with no keys at all. Presence on ``PATH`` therefore
    says nothing about intent, and judging every binary it finds made that
    default install -- the one CI deploys -- fail this check. Intent is what the
    worker was told: its ``--engines`` allow-list (chart value ``worker.engines``)
    and its ``--provider`` (``worker.provider``). Those engines must be on
    ``PATH`` and hold an API key, because subscription login is a TTY flow that
    does not exist in a cluster. With neither set, nothing is required and the
    verdict says what the worker's default pool can and cannot authenticate.
    """

    def __init__(
        self,
        *,
        which: Callable[[str], str | None],
        allow_list: frozenset[EngineId] | None = None,
        provider: str = "scripted",
        api_key_envs: Mapping[EngineId, tuple[str, ...]] = ENGINE_API_KEY_ENVS,
        provider_engines: Mapping[str, EngineId | None] = PROVIDER_ENGINES,
        descriptors: Mapping[EngineId, EngineDescriptor] = BY_ENGINE_ID,
        default_pool: Sequence[EngineDescriptor] = DEFAULT_DESCRIPTORS,
    ) -> None:
        if provider not in provider_engines:
            accepted = ", ".join(repr(p) for p in provider_engines)
            raise ValueError(f"provider must be one of {accepted}, not {provider!r}")
        self._which = which
        self._allow_list = allow_list
        self._provider = provider
        self._api_key_envs = api_key_envs
        self._provider_engine = provider_engines[provider]
        self._descriptors = descriptors
        self._default_pool = tuple(default_pool)

    @classmethod
    def for_worker(
        cls,
        *,
        engines: str | None,
        provider: str | None,
        which: Callable[[str], str | None],
    ) -> Self:
        """Built from the worker's own flag values, spelled the way the worker takes them.

        ``engines`` is the comma-separated ``--engines`` value; empty or ``None``
        means no allow-list, exactly as the worker and the chart treat it.
        ``provider`` ``None`` is the worker's default, ``scripted``. Raises
        ``ValueError`` naming the offending value.
        """
        allow_list: frozenset[EngineId] | None = None
        if engines:
            allow_list = frozenset(EngineId(e.strip()) for e in engines.split(","))
        return cls(which=which, allow_list=allow_list, provider=provider or "scripted")

    @staticmethod
    def _names(engines: Sequence[EngineId]) -> str:
        return ", ".join(sorted(e.value for e in engines))

    def _has_key(self, environ: Mapping[str, str], engine: EngineId) -> bool:
        return any(environ.get(var) for var in self._api_key_envs.get(engine, ()))

    def _on_path(self, descriptor: EngineDescriptor) -> bool:
        return self._which(descriptor.binary) is not None

    def check(self, environ: Mapping[str, str]) -> ClusterCheck:
        required = set(self._allow_list or ())
        if self._provider_engine is not None:
            required.add(self._provider_engine)
        if not required:
            return self._nothing_required(environ)

        judged = sorted(required)
        missing = [e for e in judged if not self._on_path(self._descriptors[e])]
        keyless = [e for e in judged if not self._api_key_envs.get(e)]
        unauthenticated = [
            e
            for e in judged
            if e not in missing and e not in keyless and not self._has_key(environ, e)
        ]
        problems: list[str] = []
        if missing:
            problems.append(f"required but not on PATH: {self._names(missing)}")
        if unauthenticated:
            problems.append(
                f"installed but unauthenticated: {self._names(unauthenticated)} "
                "-- subscription login does not exist in a cluster; mount API keys "
                "as a Secret (engineAuth.keys)"
            )
        if problems:
            return ClusterCheck("engine-auth", False, "; ".join(problems))
        detail = f"{len(judged)} engine(s) this worker uses: {self._names(judged)}"
        if keyless:
            detail += f" ({self._names(keyless)} takes no API key)"
        return ClusterCheck("engine-auth", True, f"{detail}; every API key present")

    def _nothing_required(self, environ: Mapping[str, str]) -> ClusterCheck:
        """No allow-list and a provider that drives no engine subprocess.

        The worker's pool is then every engine it ships, and one without a key
        simply never passes conformance, so it is never selected. That is not a
        fault -- it is the scripted install -- but a pass that said nothing would
        hide the one fact an operator needs: whether BUILD can run at all.
        """
        shipped = [d.engine_id for d in self._default_pool if self._on_path(d)]
        keyed = [e for e in shipped if self._has_key(environ, e)]
        unkeyed = [e for e in shipped if e not in keyed]
        scope = f"no --engines allow-list and --provider {self._provider}: nothing required"
        if not keyed:
            return ClusterCheck(
                "engine-auth",
                True,
                f"{scope}. {len(shipped)} engine binaries on PATH, none with an API key, "
                "so no engine-driven (BUILD) job can run -- set worker.engines and "
                "engineAuth.keys to use one",
            )
        detail = f"{scope}. API key present: {self._names(keyed)}"
        if unkeyed:
            detail += f"; in the worker's default pool without one: {self._names(unkeyed)}"
        return ClusterCheck(
            "engine-auth",
            True,
            f"{detail}. Set worker.engines, and pass it here as --engines, to require them",
        )


async def check_database(dsn: str) -> tuple[ClusterCheck, asyncpg.Connection | None]:
    try:
        conn: asyncpg.Connection = await asyncpg.connect(dsn)
    except (OSError, asyncpg.PostgresError) as exc:
        return ClusterCheck("database", False, f"cannot connect: {exc}"), None
    try:
        server_version_num = await conn.fetchval("SHOW server_version_num")
    except asyncpg.PostgresError as exc:
        await conn.close()
        return ClusterCheck("database", False, f"version check failed: {exc}"), None
    version = parse_postgres_server_version(server_version_num)
    if version is None:
        return ClusterCheck(
            "database", False, "server returned an unreadable PostgreSQL version"
        ), conn
    if not version.supported:
        return (
            ClusterCheck(
                "database",
                False,
                f"PostgreSQL {version} is below vibey's {POSTGRES_MIN_MAJOR}+ support floor",
            ),
            conn,
        )
    return ClusterCheck("database", True, f"PostgreSQL {version}; connected"), conn


async def check_migrations(conn: asyncpg.Connection, migrations_dir: Path) -> ClusterCheck:
    """The worker applies migrations at startup, so a pending migration
    here means startup did not finish or the image is older than the
    database expects."""
    expected = {m.version for m in discover_migrations(migrations_dir)}
    if not expected:
        return ClusterCheck("migrations", False, f"no migrations found at {migrations_dir}")
    try:
        rows = await conn.fetch("SELECT version FROM schema_migration")
    except asyncpg.PostgresError as exc:
        return ClusterCheck("migrations", False, f"schema_migration unreadable: {exc}")
    applied = {str(r["version"]) for r in rows}
    pending = sorted(expected - applied)
    if pending:
        return ClusterCheck("migrations", False, f"pending: {', '.join(pending)}")
    return ClusterCheck("migrations", True, f"{len(applied)} applied")


class DatabaseSecurityChecks:
    """The two database checks of ADR-0055, shared by `vibey doctor` and its --cluster
    sweep: can the application's role rewrite the ledger, and can anyone connect as a
    role that could without a password."""

    def __init__(
        self,
        *,
        inspector: LedgerGuardInspectorInterface | None = None,
        probe: LocalAuthProbeInterface | None = None,
    ) -> None:
        self._inspector = inspector if inspector is not None else LedgerGuardInspector()
        self._probe = probe if probe is not None else LocalAuthProbe()

    async def run(self, conn: asyncpg.Connection, dsn: str) -> tuple[ClusterCheck, ...]:
        guard = await self._inspector.inspect(conn)
        finding = await self._probe.probe(conn, dsn)
        return (
            ClusterCheck("ledger-guard", guard.in_force, guard.describe()),
            ClusterCheck(
                "local-auth",
                finding.verdict is not AuthVerdict.FAIL,
                finding.detail,
                unknown=finding.verdict is AuthVerdict.UNKNOWN,
            ),
        )


class ClusterPreflight:
    """Every in-cluster wiring check, in the order ``vibey doctor --cluster`` prints them.

    The engine judgement is injected rather than built here: it is the one check
    that depends on how the worker was invoked, and the pod's environment does
    not carry that -- only the worker's command line does.
    """

    def __init__(
        self,
        *,
        engine_auth: EngineAuthCheckInterface,
        database_security: DatabaseSecurityChecksInterface | None = None,
    ) -> None:
        self._engine_auth = engine_auth
        self._database_security = (
            database_security if database_security is not None else DatabaseSecurityChecks()
        )

    async def run(
        self,
        *,
        dsn: str,
        workspace: Path,
        migrations_dir: Path,
        environ: Mapping[str, str],
        uid: int,
    ) -> tuple[ClusterCheck, ...]:
        checks: list[ClusterCheck] = [
            check_dsn_resolves_cluster_wide(dsn),
            check_not_root(uid),
            check_workspace_writable(workspace),
            self._engine_auth.check(environ),
        ]
        db_check, conn = await check_database(dsn)
        checks.append(db_check)
        if conn is not None:
            try:
                checks.append(await check_migrations(conn, migrations_dir))
                checks.extend(await self._database_security.run(conn, dsn))
            finally:
                await conn.close()
        return tuple(checks)


def all_ok(checks: Sequence[ClusterCheck]) -> bool:
    return all(c.ok for c in checks)
