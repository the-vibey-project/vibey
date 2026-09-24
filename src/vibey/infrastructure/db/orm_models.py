# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pydantic-backed SQLAlchemy ORM projections for vibey's PostgreSQL schema.

Migrations remain the authority for creating and evolving the schema. These
SQLModel classes are the typed Python representation of every relation that a
current migration leaves behind, including the provisioned projection tables
and the migration catalog. They intentionally do not call ``create_all``:
schema changes must stay forward-only, checksummed migrations.

The live repositories still use asyncpg where PostgreSQL semantics are part of
the contract (``FOR UPDATE SKIP LOCKED``, append-only rules, and transactional
``NOTIFY``). The ORM projection gives other adapters and tools a validated,
Pydantic-native object model without weakening those paths.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlmodel import Field, SQLModel

PHASE_ENUM = ENUM(
    "intake",
    "design",
    "visual_design",
    "build",
    "review",
    "deploy_design",
    "deploy_execute",
    "deploy_review",
    "deploy",
    "done",
    "abandoned",
    name="phase",
    create_type=False,
    validate_strings=False,
)
PROVENANCE_ENUM = ENUM(
    "trusted",
    "agent",
    "untrusted",
    name="provenance",
    create_type=False,
    validate_strings=False,
)
JOB_STATE_ENUM = ENUM(
    "ready",
    "leased",
    "succeeded",
    "failed",
    "awaiting_human",
    "awaiting_capacity",
    "cancelled",
    name="job_state",
    create_type=False,
    validate_strings=False,
)
WORK_ITEM_STATE_ENUM = ENUM(
    "pending",
    "implementing",
    "verifying",
    "ready",
    "integrated",
    "blocked",
    "waived",
    name="work_item_state",
    create_type=False,
    validate_strings=False,
)
OPEN_KIND_ENUM = ENUM(
    "question",
    "decision",
    "assumption",
    "finding",
    name="open_kind",
    create_type=False,
    validate_strings=False,
)
CIRCUIT_STATE_ENUM = ENUM(
    "closed",
    "half_open",
    "open",
    name="circuit_state",
    create_type=False,
    validate_strings=False,
)


def _utc_now() -> datetime:
    """Provide a local value for timestamp fields before a row is flushed."""
    return datetime.now(UTC)


class VibeyOrmModel(SQLModel):
    """Shared Pydantic base for every mapped database object."""


class ProjectOrm(VibeyOrmModel, table=True):
    __tablename__ = "project"
    __table_args__ = (
        CheckConstraint(
            "cycle >= 1 AND cycle <= max_cycles + 1",
            name="project_cycle_bounded",
        ),
        Index("project_repo_uniq", "repo_path", unique=True),
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    name: str = Field(sa_column=Column(Text, nullable=False))
    repo_path: str = Field(sa_column=Column(Text, nullable=False))
    phase: str = Field(
        default="intake",
        sa_column=Column(PHASE_ENUM, nullable=False, server_default=text("'intake'")),
    )
    cycle: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default=text("1")),
    )
    max_cycles: int = Field(
        default=10,
        sa_column=Column(Integer, nullable=False, server_default=text("10")),
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )


class EventOrm(VibeyOrmModel, table=True):
    __tablename__ = "event"
    __table_args__ = (
        UniqueConstraint("event_id", "seq", name="event_id_seq_uniq"),
        Index("event_project_seq", "project_id", "seq"),
        Index("event_kind", "project_id", "kind", "seq"),
        Index("event_correlation", "correlation_id", "seq"),
        Index(
            "event_payload_gin",
            "payload",
            postgresql_using="gin",
            postgresql_ops={"payload": "jsonb_path_ops"},
        ),
        Index("event_digest", "digest"),
        Index("event_project_produced_at", "project_id", "produced_at"),
        Index("event_project_engine", "project_id", "engine_id", "seq"),
        {"postgresql_partition_by": "RANGE (seq)"},
    )

    event_id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    seq: int = Field(sa_column=Column(BigInteger, primary_key=True, nullable=False))
    cycle: int = Field(sa_column=Column(Integer, nullable=False))
    phase: str = Field(sa_column=Column(PHASE_ENUM, nullable=False))
    kind: str = Field(sa_column=Column(Text, nullable=False))
    engine_id: str | None = Field(default=None, sa_column=Column(Text))
    job_id: UUID | None = Field(default=None, sa_column=Column(PostgresUUID(as_uuid=True)))
    causation_id: UUID | None = Field(default=None, sa_column=Column(PostgresUUID(as_uuid=True)))
    correlation_id: UUID = Field(sa_column=Column(PostgresUUID(as_uuid=True), nullable=False))
    provenance: str = Field(
        default="agent",
        sa_column=Column(PROVENANCE_ENUM, nullable=False, server_default=text("'agent'")),
    )
    produced_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    digest: str = Field(sa_column=Column(Text, nullable=False))


class EventSeqOrm(VibeyOrmModel, table=True):
    __tablename__ = "event_seq"

    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    next_seq: int = Field(
        default=1,
        sa_column=Column(BigInteger, nullable=False, server_default=text("1")),
    )


class JobOrm(VibeyOrmModel, table=True):
    __tablename__ = "job"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key", name="job_idem_uniq"),
        CheckConstraint(
            "(state = 'leased') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="job_lease_consistent",
        ),
        CheckConstraint("bump_seq IS NULL OR bump_seq > 0", name="job_bump_seq_positive"),
        CheckConstraint(
            "(bump_seq IS NULL) = (bump_origin IS NULL)", name="job_bump_origin_with_seq"
        ),
        Index(
            "job_claim",
            "project_id",
            "bump_seq",
            "priority",
            "run_after",
            "id",
            postgresql_where=text("state = 'ready'"),
        ),
        Index("job_expiring", "lease_expires_at", postgresql_where=text("state = 'leased'")),
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    cycle: int = Field(sa_column=Column(Integer, nullable=False))
    phase: str = Field(sa_column=Column(PHASE_ENUM, nullable=False))
    kind: str = Field(sa_column=Column(Text, nullable=False))
    state: str = Field(
        default="ready",
        sa_column=Column(JOB_STATE_ENUM, nullable=False, server_default=text("'ready'")),
    )
    priority: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    work_item_id: str | None = Field(default=None, sa_column=Column(Text))
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    requirement: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    idempotency_key: str = Field(sa_column=Column(Text, nullable=False))
    attempts: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    max_attempts: int = Field(
        default=7,
        sa_column=Column(Integer, nullable=False, server_default=text("7")),
    )
    run_after: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    lease_owner: str | None = Field(default=None, sa_column=Column(Text))
    lease_expires_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    assigned_engine: str | None = Field(default=None, sa_column=Column(Text))
    last_error: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    bump_seq: int | None = Field(default=None, sa_column=Column(BigInteger))
    bump_origin: UUID | None = Field(default=None, sa_column=Column(PostgresUUID(as_uuid=True)))


class JobDependencyOrm(VibeyOrmModel, table=True):
    __tablename__ = "job_dependency"
    __table_args__ = (CheckConstraint("job_id <> depends_on_job_id", name="no_self_dep"),)

    job_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("job.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    depends_on_job_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("job.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )


class WorkItemOrm(VibeyOrmModel, table=True):
    __tablename__ = "work_item"

    item_id: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    cycle: int = Field(sa_column=Column(Integer, primary_key=True, nullable=False))
    title: str = Field(sa_column=Column(Text, nullable=False))
    state: str = Field(
        default="pending",
        sa_column=Column(WORK_ITEM_STATE_ENUM, nullable=False, server_default=text("'pending'")),
    )
    acceptance_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
    )
    depends_on: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False, server_default=text("'{}'")),
    )
    branch: str | None = Field(default=None, sa_column=Column(Text))
    worktree_path: str | None = Field(default=None, sa_column=Column(Text))
    attempt: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    current_effort: int = Field(
        default=1,
        sa_column=Column(SmallInteger, nullable=False, server_default=text("1")),
    )
    last_engine: str | None = Field(default=None, sa_column=Column(Text))
    verification: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    blocked_reason: str | None = Field(default=None, sa_column=Column(Text))


class OpenItemOrm(VibeyOrmModel, table=True):
    __tablename__ = "open_item"
    __table_args__ = (
        Index(
            "open_item_open",
            "project_id",
            "kind",
            postgresql_where=text("closed_seq IS NULL AND superseded_by IS NULL"),
        ),
        Index("open_item_norm", "project_id", "kind", "normalized"),
    )

    item_id: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    kind: str = Field(sa_column=Column(OPEN_KIND_ENUM, nullable=False))
    opened_seq: int = Field(sa_column=Column(BigInteger, nullable=False))
    closed_seq: int | None = Field(default=None, sa_column=Column(BigInteger))
    superseded_by: str | None = Field(
        default=None,
        sa_column=Column(Text, ForeignKey("open_item.item_id")),
    )
    blocking: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    severity: str | None = Field(default=None, sa_column=Column(Text))
    ambiguity: str | None = Field(default=None, sa_column=Column(Text))
    body: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    normalized: str = Field(sa_column=Column(Text, nullable=False))


class HandoffOrm(VibeyOrmModel, table=True):
    __tablename__ = "handoff"
    __table_args__ = (CheckConstraint("to_seq >= from_seq", name="handoff_range_sane"),)

    handoff_id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    cycle: int = Field(sa_column=Column(Integer, nullable=False))
    phase: str = Field(sa_column=Column(PHASE_ENUM, nullable=False))
    job_id: UUID | None = Field(
        default=None,
        sa_column=Column(PostgresUUID(as_uuid=True), ForeignKey("job.id", ondelete="SET NULL")),
    )
    from_engine: str | None = Field(default=None, sa_column=Column(Text))
    to_engine: str = Field(sa_column=Column(Text, nullable=False))
    reason: str = Field(sa_column=Column(Text, nullable=False))
    from_seq: int = Field(sa_column=Column(BigInteger, nullable=False))
    to_seq: int = Field(sa_column=Column(BigInteger, nullable=False))
    range_digest: str = Field(sa_column=Column(Text, nullable=False))
    envelope: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    gate_mode: str = Field(sa_column=Column(Text, nullable=False))
    gate_attempts: int = Field(
        default=1,
        sa_column=Column(Integer, nullable=False, server_default=text("1")),
    )
    gate_violations: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    accepted: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )


class EngineHealthOrm(VibeyOrmModel, table=True):
    __tablename__ = "engine_health"
    __table_args__ = (
        CheckConstraint(
            "capacity_state IS DISTINCT FROM 'CreditsExhausted' OR resets_at IS NULL",
            name="credits_never_have_a_deadline",
        ),
    )

    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    engine_id: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    installed: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    version: str | None = Field(default=None, sa_column=Column(Text))
    conformance_ok: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("false")),
    )
    conformance_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    auth_ok_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    circuit: str = Field(
        default="closed",
        sa_column=Column(CIRCUIT_STATE_ENUM, nullable=False, server_default=text("'closed'")),
    )
    capacity_state: str | None = Field(default=None, sa_column=Column(Text))
    resets_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    probe_next_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    probe_attempt: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    consecutive_fail: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    ewma_failure: float = Field(
        default=0.0,
        sa_column=Column(Float, nullable=False, server_default=text("0.0")),
    )
    cost_usd_cycle: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(12, 4), nullable=False, server_default=text("0")),
    )
    selected_count: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, server_default=text("0")),
    )


class RotationCursorOrm(VibeyOrmModel, table=True):
    __tablename__ = "rotation_cursor"

    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    engine_id: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    current: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    order: int = Field(sa_column=Column("order", Integer, nullable=False))


class HumanGateOrm(VibeyOrmModel, table=True):
    __tablename__ = "human_gate"
    __table_args__ = (
        Index(
            "human_gate_open",
            "project_id",
            "raised_at",
            postgresql_where=text("answered_at IS NULL"),
        ),
    )

    gate_id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    job_id: UUID | None = Field(
        default=None,
        sa_column=Column(PostgresUUID(as_uuid=True), ForeignKey("job.id", ondelete="CASCADE")),
    )
    kind: str = Field(sa_column=Column(Text, nullable=False))
    prompt: str = Field(sa_column=Column(Text, nullable=False))
    options: list[Any] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    )
    default_answer: str | None = Field(default=None, sa_column=Column(Text))
    answer: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    raised_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    timeout_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    answered_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    answered_by: str | None = Field(default=None, sa_column=Column(Text))


class ArtifactOrm(VibeyOrmModel, table=True):
    __tablename__ = "artifact"

    artifact_id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=text("gen_random_uuid()"),
        ),
    )
    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    cycle: int = Field(sa_column=Column(Integer, nullable=False))
    kind: str = Field(sa_column=Column(Text, nullable=False))
    path: str = Field(sa_column=Column(Text, nullable=False))
    digest: str = Field(sa_column=Column(Text, nullable=False))
    produced_by: str | None = Field(default=None, sa_column=Column(Text))
    seq: int = Field(sa_column=Column(BigInteger, nullable=False))
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )


class BudgetLedgerOrm(VibeyOrmModel, table=True):
    __tablename__ = "budget_ledger"

    project_id: UUID = Field(
        sa_column=Column(
            PostgresUUID(as_uuid=True),
            ForeignKey("project.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    cycle: int = Field(sa_column=Column(Integer, primary_key=True, nullable=False))
    phase: str = Field(sa_column=Column(PHASE_ENUM, primary_key=True, nullable=False))
    engine_id: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    turns: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, server_default=text("0")),
    )
    tokens_in: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, server_default=text("0")),
    )
    tokens_out: int = Field(
        default=0,
        sa_column=Column(BigInteger, nullable=False, server_default=text("0")),
    )
    dollars: Decimal = Field(
        default=Decimal("0"),
        sa_column=Column(Numeric(12, 4), nullable=False, server_default=text("0")),
    )


class SchemaMigrationOrm(VibeyOrmModel, table=True):
    __tablename__ = "schema_migration"

    version: str = Field(sa_column=Column(Text, primary_key=True, nullable=False))
    applied_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    checksum: str = Field(sa_column=Column(Text, nullable=False))


# The migrations currently leave these fourteen relations in the live schema.
# Keeping the registry explicit makes a newly added migration fail the ORM
# coverage test until its Pydantic/SQLAlchemy projection is added beside it.
ORM_TABLE_MODELS: tuple[type[SQLModel], ...] = (
    ProjectOrm,
    EventOrm,
    EventSeqOrm,
    JobOrm,
    JobDependencyOrm,
    WorkItemOrm,
    OpenItemOrm,
    HandoffOrm,
    EngineHealthOrm,
    RotationCursorOrm,
    HumanGateOrm,
    ArtifactOrm,
    BudgetLedgerOrm,
    SchemaMigrationOrm,
)
ORM_TABLE_NAMES = frozenset(model.__tablename__ for model in ORM_TABLE_MODELS)


__all__ = [
    "ArtifactOrm",
    "BudgetLedgerOrm",
    "EngineHealthOrm",
    "EventOrm",
    "EventSeqOrm",
    "HandoffOrm",
    "HumanGateOrm",
    "JobDependencyOrm",
    "JobOrm",
    "OpenItemOrm",
    "ORM_TABLE_MODELS",
    "ORM_TABLE_NAMES",
    "ProjectOrm",
    "RotationCursorOrm",
    "SchemaMigrationOrm",
    "VibeyOrmModel",
    "WorkItemOrm",
]
