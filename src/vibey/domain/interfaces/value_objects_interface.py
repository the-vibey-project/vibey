# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for domain values added or changed during the sovereign-first work.

Most domain values are immutable records or closed vocabularies.  They still
have a useful interface: consumers depend on the fields and pure operations,
not on the dataclass or enum implementation.  The broad ``object`` members in
this module intentionally avoid importing sibling implementation modules and
therefore preserve domain purity; the member names and mutability guarantees
are the contract at this layer.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class StringValueInterface(Protocol):
    @property
    def value(self) -> str: ...


@runtime_checkable
class UnrecognizedCircuitStateInterface(StringValueInterface, Protocol):
    @property
    def members(self) -> frozenset[str]: ...


@runtime_checkable
class ClaudeloopLocalConfigInterface(Protocol):
    @property
    def profile(self) -> str: ...

    @property
    def context_window(self) -> int: ...

    @property
    def structured_verdict(self) -> bool: ...

    @classmethod
    def from_table(cls, table: dict[str, object], path: str) -> ClaudeloopLocalConfigInterface: ...


@runtime_checkable
class EnginesConfigInterface(Protocol):
    @property
    def enabled(self) -> tuple[str, ...]: ...

    @property
    def weights(self) -> Mapping[str, int]: ...

    @property
    def claudeloop_local(self) -> ClaudeloopLocalConfigInterface: ...


@runtime_checkable
class FeaturesConfigInterface(Protocol):
    @property
    def qwenloop(self) -> bool: ...

    @property
    def claudeloop_local(self) -> bool: ...

    def enables(self, engine: str) -> bool: ...


@runtime_checkable
class EngineIdInterface(StringValueInterface, Protocol): ...


@runtime_checkable
class EngineTierInterface(StringValueInterface, Protocol): ...


@runtime_checkable
class UnrecognizedEngineIdInterface(StringValueInterface, Protocol):
    @property
    def members(self) -> frozenset[str]: ...


@runtime_checkable
class EngineDescriptorInterface(Protocol):
    @property
    def engine_id(self) -> object: ...

    @property
    def binary(self) -> str: ...

    @property
    def min_version(self) -> str: ...

    @property
    def state_dir(self) -> str: ...

    @property
    def done_marker(self) -> str: ...

    @property
    def auth_env(self) -> tuple[str, ...]: ...

    @property
    def capabilities(self) -> frozenset[object]: ...

    @property
    def effort_projection(self) -> Mapping[object, object]: ...

    @property
    def session_verb(self) -> str: ...

    @property
    def isolation_flags(self) -> Mapping[object, tuple[str, ...]]: ...

    @property
    def cost_per_mtok_in(self) -> float: ...

    @property
    def cost_per_mtok_out(self) -> float: ...

    @property
    def context_window(self) -> int: ...

    @property
    def base_weight(self) -> int: ...

    @property
    def supports_cwd_flag(self) -> bool: ...

    @property
    def plan_flag(self) -> str | None: ...

    @property
    def tier(self) -> object: ...

    @property
    def doctor_args(self) -> tuple[str, ...]: ...

    def invoke(self, effort: object) -> object: ...

    def saturates_at(self, effort: object) -> bool: ...


@runtime_checkable
class SovereignResearchUnavailableInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class UnrecognizedJobStateInterface(StringValueInterface, Protocol):
    @property
    def members(self) -> frozenset[str]: ...


@runtime_checkable
class EventKindInterface(StringValueInterface, Protocol): ...


@runtime_checkable
class UnrecognizedProvenanceInterface(StringValueInterface, Protocol):
    @property
    def members(self) -> frozenset[str]: ...


@runtime_checkable
class LedgerEventInterface(Protocol):
    @property
    def event_id(self) -> UUID: ...

    @property
    def project_id(self) -> UUID: ...

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> object: ...

    @property
    def seq(self) -> int: ...

    @property
    def kind(self) -> object: ...

    @property
    def engine_id(self) -> object: ...

    @property
    def job_id(self) -> UUID | None: ...

    @property
    def causation_id(self) -> UUID | None: ...

    @property
    def correlation_id(self) -> UUID | None: ...

    @property
    def provenance(self) -> object: ...

    @property
    def produced_at(self) -> datetime: ...

    @property
    def payload(self) -> Mapping[str, object]: ...

    @property
    def digest(self) -> str: ...

    @property
    def interpretable(self) -> bool: ...


@runtime_checkable
class ChainFindingKindInterface(StringValueInterface, Protocol): ...


@runtime_checkable
class InvalidLedgerQueryInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class ActorScopeInterface(StringValueInterface, Protocol): ...


@runtime_checkable
class InvalidLedgerRecordInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class UnrecognizedPhaseInterface(StringValueInterface, Protocol):
    @property
    def members(self) -> frozenset[str]: ...


@runtime_checkable
class PhaseStateInterface(Protocol):
    @property
    def phase(self) -> object: ...

    @property
    def cycle(self) -> int: ...

    @property
    def max_cycles(self) -> int: ...

    @property
    def entered_at(self) -> datetime: ...


@runtime_checkable
class CostReportEntryInterface(Protocol):
    @property
    def phase(self) -> object: ...

    @property
    def engine_id(self) -> object: ...

    @property
    def turns(self) -> int: ...

    @property
    def dollars(self) -> float: ...


@runtime_checkable
class WorkLedgerEntryInterface(Protocol):
    @property
    def causation_id(self) -> UUID | None: ...

    @property
    def complete(self) -> bool: ...

    @property
    def remaining_work(self) -> tuple[str, ...]: ...

    @property
    def last_seq(self) -> int: ...


@runtime_checkable
class WithheldReasonInterface(StringValueInterface, Protocol): ...


@runtime_checkable
class InvalidPublicationRulesInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class CandidateInterface(Protocol):
    @property
    def engine_id(self) -> object: ...

    @property
    def base_weight(self) -> int: ...

    @property
    def current(self) -> int: ...

    @property
    def order(self) -> int: ...

    @property
    def health_factor(self) -> float: ...

    @property
    def fidelity_factor(self) -> float: ...

    @property
    def cost_factor(self) -> float: ...

    @property
    def affinity_factor(self) -> float: ...

    @property
    def tier(self) -> object: ...

    def effective_weight(self) -> float: ...
