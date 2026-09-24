# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for the forge, feasibility, estimation and configuration values.

The forge tool has deliberately small shared ports, but its immutable nouns and
configuration records are still public class surfaces.  These protocols keep
those surfaces importable without making an interface module consume the
implementation module that supplies the value.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from vibey_gh.interfaces.feasibility_evaluator_interface import FeasibilityEvaluatorInterface
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_snapshot_interface import (
    ForgeReaderInterface,
    SnapshotStoreInterface,
)
from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface
from vibey_gh.interfaces.graded_estimator_interface import GradedEstimatorInterface
from vibey_gh.interfaces.memory_sampler_interface import MemorySamplerInterface
from vibey_gh.interfaces.model_sampler_interface import ModelSamplerInterface
from vibey_gh.interfaces.protected_paths_interface import ProtectedPathsInterface
from vibey_gh.interfaces.review_composition_interface import ReviewComposerPort
from vibey_gh.interfaces.review_contract_interface import ReviewContractPort


@runtime_checkable
class ForgeValueInterface(Protocol):
    @property
    def value(self) -> str: ...


@runtime_checkable
class ForgeKindInterface(ForgeValueInterface, Protocol): ...


@runtime_checkable
class ForgeRepositoryInterface(Protocol):
    @property
    def kind(self) -> ForgeKindInterface: ...

    @property
    def host(self) -> str: ...

    @property
    def owner(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def full_name(self) -> str: ...


@runtime_checkable
class ChangeRequestInterface(Protocol):
    @property
    def number(self) -> int: ...

    @property
    def head_ref(self) -> str: ...

    @property
    def head_sha(self) -> str: ...

    @property
    def base_ref(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def state(self) -> str: ...


@runtime_checkable
class ForgeIssueInterface(Protocol):
    @property
    def number(self) -> int: ...

    @property
    def title(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def state(self) -> str: ...


@runtime_checkable
class ForgeCommentInterface(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def author(self) -> str: ...

    @property
    def body(self) -> str: ...


@runtime_checkable
class ForgeReviewInterface(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def author(self) -> str: ...

    @property
    def verdict(self) -> str: ...

    @property
    def body(self) -> str: ...


@runtime_checkable
class ForgeUserInterface(Protocol):
    @property
    def login(self) -> str: ...

    @property
    def name(self) -> str: ...


@runtime_checkable
class CheckResultInterface(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def head_sha(self) -> str: ...

    @property
    def conclusion(self) -> str: ...


@runtime_checkable
class ForgeReleaseInterface(Protocol):
    @property
    def tag(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def draft(self) -> bool: ...

    @property
    def label(self) -> str: ...


@runtime_checkable
class ForgeLabelInterface(Protocol):
    @property
    def name(self) -> str: ...


@runtime_checkable
class ProtectedRefInterface(Protocol):
    @property
    def ref(self) -> str: ...


@runtime_checkable
class NotSupportedInterface(Protocol):
    @property
    def kind(self) -> ForgeKindInterface: ...

    @property
    def verb(self) -> str: ...

    @property
    def reason(self) -> str: ...

    @property
    def problem(self) -> str: ...


@runtime_checkable
class GitHubForgeInterface(ForgeAdapterInterface, Protocol):
    """The GitHub implementation of the forge-neutral adapter."""


@runtime_checkable
class GitLabForgeInterface(ForgeAdapterInterface, Protocol):
    """The GitLab implementation of the forge-neutral adapter."""


@runtime_checkable
class ForgejoForgeInterface(ForgeAdapterInterface, Protocol):
    """The Forgejo implementation of the forge-neutral adapter."""


@runtime_checkable
class ForgeAdapterReaderInterface(ForgeReaderInterface, Protocol):
    """Reads snapshot artifacts through a forge-neutral adapter."""


@runtime_checkable
class ForgejoTransportInterface(ForgeTransportInterface, Protocol):
    """The Forgejo transport implementation.

    `timeout` is declared here rather than on `ForgeTransportInterface` because only the two
    HTTP transports have one: the `gh` transport shells out to a client that owns its own.
    Left undeclared, the seam this change exists to add would be invisible to any caller
    typed against this interface -- a public attribute that works and cannot be seen is not
    a seam (ADR-0016: interfaces declare).
    """

    @property
    def timeout(self) -> float:
        """Seconds a single call may take before it is abandoned."""
        ...


@runtime_checkable
class GitLabTransportInterface(ForgeTransportInterface, Protocol):
    """The GitLab transport implementation."""

    @property
    def timeout(self) -> float:
        """Seconds a single call may take before it is abandoned."""
        ...


@runtime_checkable
class ForgeClassInterface(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def native_class(self) -> str: ...

    @property
    def endpoint(self) -> str: ...

    @property
    def id_field(self) -> str: ...

    @property
    def since(self) -> bool: ...

    @property
    def cursor(self) -> bool: ...

    @classmethod
    def named(cls, name: str) -> ForgeClassInterface: ...


@runtime_checkable
class SnapshotStoreErrorInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class _ChainInterface(Protocol):
    """The private append-only chain cursor held by the snapshot store."""

    @property
    def records(self) -> int: ...

    @property
    def head(self) -> str | None: ...

    @property
    def latest(self) -> Mapping[tuple[str, str], str]: ...


@runtime_checkable
class JsonlSnapshotStoreInterface(SnapshotStoreInterface, Protocol):
    def path(self, forge_class: str) -> Path: ...

    def _load(self, forge_class: str) -> _ChainInterface: ...


@runtime_checkable
class MarketplaceErrorInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class PlatformConfigInterface(Protocol):
    @property
    def kind(self) -> ForgeKindInterface: ...

    @property
    def host(self) -> str: ...

    @property
    def repository(self) -> str: ...

    @property
    def token_env(self) -> str: ...

    def not_adapted(self) -> str | None: ...


class _ConfigRecordInterface(Protocol):
    """Shared marker with an explicit introspection surface for TOML records."""

    @property
    def __dataclass_fields__(self) -> Mapping[str, object]: ...


@runtime_checkable
class TidyConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def keep_branches(self) -> tuple[str, ...]: ...

    @property
    def fail_check(self) -> bool: ...

    @property
    def trust_forge_deletions(self) -> bool: ...


@runtime_checkable
class PrAutomationFallbackConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def runner_label(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def base_url(self) -> str | None: ...

    @property
    def trusted_only(self) -> bool: ...

    @property
    def max_diff_chars(self) -> int: ...

    @property
    def timeout_seconds(self) -> int: ...

    @property
    def heartbeat_ref(self) -> str: ...

    @property
    def heartbeat_max_age_minutes(self) -> int: ...

    @property
    def context_paths(self) -> tuple[str, ...]: ...


@runtime_checkable
class PrAutomationConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def scan_workflows(self) -> bool: ...

    @property
    def ignored_checks(self) -> tuple[str, ...]: ...

    @property
    def max_repair_attempts(self) -> int: ...

    @property
    def model(self) -> str: ...

    @property
    def review_untrusted_authors(self) -> bool: ...

    @property
    def repair_untrusted_authors(self) -> bool: ...

    @property
    def replace_fork_prs(self) -> bool: ...

    @property
    def retain_schedule_backstop(self) -> bool: ...

    @property
    def paid_review(self) -> bool: ...

    @property
    def fallback(self) -> PrAutomationFallbackConfigInterface: ...


@runtime_checkable
class MergeQueueConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def merge_method(self) -> str: ...

    @property
    def grouping_strategy(self) -> str: ...

    @property
    def check_response_timeout_minutes(self) -> int: ...

    @property
    def max_entries_to_build(self) -> int: ...

    @property
    def max_entries_to_merge(self) -> int: ...

    @property
    def min_entries_to_merge(self) -> int: ...

    @property
    def min_entries_to_merge_wait_minutes(self) -> int: ...


@runtime_checkable
class RulesetConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def required_checks(self) -> tuple[str, ...]: ...

    @property
    def required_approvals(self) -> int: ...

    @property
    def merge_queue(self) -> MergeQueueConfigInterface: ...


@runtime_checkable
class RulesetsConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def integration(self) -> RulesetConfigInterface: ...

    @property
    def release(self) -> RulesetConfigInterface: ...


@runtime_checkable
class DocumentationConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def model(self) -> str: ...

    @property
    def required_files(self) -> tuple[str, ...]: ...

    @property
    def require_roadmap(self) -> bool: ...

    @property
    def production_label(self) -> str: ...

    @property
    def preview_label(self) -> str: ...

    @property
    def generate_book(self) -> bool: ...

    @property
    def generate_paper(self) -> bool: ...

    @property
    def require_provenance(self) -> bool: ...


@runtime_checkable
class MarketplaceConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def name(self) -> str: ...

    @property
    def members(self) -> tuple[str, ...]: ...

    @property
    def description(self) -> str: ...


@runtime_checkable
class EstimateConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def offline(self) -> bool: ...

    @property
    def model(self) -> str: ...

    @property
    def stages(self) -> tuple[str, ...]: ...

    @property
    def requirements(self) -> Mapping[str, Mapping[str, float]]: ...

    @property
    def report_first(self) -> bool: ...

    @classmethod
    def from_table(cls, table: Mapping[str, object]) -> EstimateConfigInterface: ...


@runtime_checkable
class GhConfigInterface(_ConfigRecordInterface, Protocol):
    @property
    def root(self) -> Path: ...

    @property
    def text(self) -> str: ...

    @property
    def integration_branch(self) -> str: ...

    @property
    def release_branch(self) -> str: ...

    @property
    def owner(self) -> str: ...

    @property
    def platform(self) -> PlatformConfigInterface: ...

    @property
    def rulesets(self) -> RulesetsConfigInterface: ...

    @property
    def documentation(self) -> DocumentationConfigInterface: ...

    @property
    def marketplace(self) -> MarketplaceConfigInterface: ...

    @property
    def estimate(self) -> EstimateConfigInterface: ...

    def header(self) -> str: ...

    def trailer_key(self) -> str: ...


@runtime_checkable
class OperationEstimateInterface(Protocol):
    @property
    def operation(self) -> str: ...

    @property
    def start(self) -> str: ...

    @property
    def stages(self) -> tuple[object, ...]: ...

    @property
    def verdict(self) -> str: ...

    @property
    def state(self) -> object: ...

    @property
    def duration(self) -> object: ...

    @property
    def payload_bytes(self) -> int: ...

    @property
    def model(self) -> str | None: ...

    @property
    def runner(self) -> str | None: ...

    @property
    def runner_read(self) -> bool: ...

    @property
    def offline(self) -> bool: ...

    @property
    def journal(self) -> Path | None: ...

    def exit_code(self) -> int: ...

    def as_dict(self) -> dict[str, object]: ...

    def lines(self) -> tuple[str, ...]: ...


@runtime_checkable
class SampleInterface(Protocol):
    @property
    def x(self) -> float: ...

    @property
    def y(self) -> float: ...


@runtime_checkable
class MachineInterface(Protocol):
    """The measured host-memory record used by the local fit."""

    @property
    def total_gb(self) -> float: ...

    @property
    def free_gb(self) -> float: ...

    @property
    def swap_used_gb(self) -> float: ...

    @property
    def swap_total_gb(self) -> float: ...

    @property
    def readable(self) -> bool: ...

    @property
    def available_gb(self) -> float: ...


@runtime_checkable
class ModelInterface(Protocol):
    """The measured model record returned by the local runner."""

    @property
    def name(self) -> str: ...

    @property
    def size_gb(self) -> float: ...

    @property
    def context_length(self) -> int: ...

    @property
    def resident(self) -> bool: ...


@runtime_checkable
class ObservationInterface(Protocol):
    """One measured operation contributing evidence to the fit."""

    @property
    def payload_bytes(self) -> int: ...

    @property
    def elapsed_s(self) -> float: ...

    @property
    def concurrent(self) -> int: ...

    @property
    def sample(self) -> SampleInterface: ...


@runtime_checkable
class DarwinMemorySamplerInterface(MemorySamplerInterface, Protocol):
    """The macOS memory sampler."""


@runtime_checkable
class LinuxMemorySamplerInterface(MemorySamplerInterface, Protocol):
    """The Linux memory sampler."""


@runtime_checkable
class OllamaModelSamplerInterface(ModelSamplerInterface, Protocol):
    """The Ollama model sampler."""

    @staticmethod
    def resolve_base_url(
        explicit: str | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        fallback: str = "http://127.0.0.1:11434",
    ) -> str: ...


@runtime_checkable
class LinearFitInterface(Protocol):
    @property
    def intercept(self) -> float: ...

    @property
    def slope(self) -> float: ...

    @property
    def n(self) -> int: ...

    @property
    def basis(self) -> str: ...

    @property
    def reason(self) -> str: ...

    def at(self, x: float) -> float: ...


@runtime_checkable
class PredictionInterface(Protocol):
    @property
    def value(self) -> float | None: ...

    @property
    def x(self) -> float: ...

    @property
    def basis(self) -> str: ...

    @property
    def n(self) -> int: ...

    @property
    def reason(self) -> str: ...

    @property
    def known(self) -> bool: ...


@runtime_checkable
class GradeInterface(Protocol):
    @property
    def predicted(self) -> float | None: ...

    @property
    def actual(self) -> float: ...

    @property
    def basis(self) -> str: ...

    @property
    def n(self) -> int: ...

    @property
    def error(self) -> float | None: ...

    @property
    def abs_error(self) -> float | None: ...

    @property
    def relative_error(self) -> float | None: ...


@runtime_checkable
class TrackRecordInterface(Protocol):
    @property
    def graded(self) -> int: ...

    @property
    def ungraded(self) -> int: ...

    @property
    def mean_error(self) -> float | None: ...

    @property
    def mean_abs_error(self) -> float | None: ...


@runtime_checkable
class GradedEstimatorClassInterface(GradedEstimatorInterface, Protocol):
    """The concrete estimator with the shared fit/grading port."""


@runtime_checkable
class CoordinateInterface(Protocol):
    @property
    def material(self) -> str: ...

    @property
    def prop(self) -> str: ...

    @property
    def value(self) -> float | None: ...

    @property
    def source(self) -> str: ...

    @property
    def measured_at(self) -> float | None: ...

    @property
    def name(self) -> str: ...

    @property
    def known(self) -> bool: ...

    @property
    def distance(self) -> float | None: ...


@runtime_checkable
class StateVectorInterface(Protocol):
    @property
    def coordinates(self) -> tuple[CoordinateInterface, ...]: ...

    @classmethod
    def unknown(cls, measured_at: float | None = None) -> StateVectorInterface: ...

    def get(self, material: str, prop: str) -> CoordinateInterface: ...

    def with_measurements(
        self, measurements: Sequence[CoordinateInterface]
    ) -> StateVectorInterface: ...

    @property
    def measured(self) -> int: ...

    @property
    def confidence(self) -> float: ...


@runtime_checkable
class RequirementInterface(Protocol):
    @property
    def material(self) -> str: ...

    @property
    def prop(self) -> str: ...

    @property
    def minimum(self) -> float: ...

    @property
    def name(self) -> str: ...

    @classmethod
    def parse(cls, coordinate: str, minimum: float = 0.8) -> RequirementInterface: ...


@runtime_checkable
class StageInterface(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def requirements(self) -> tuple[RequirementInterface, ...]: ...

    @property
    def summary(self) -> str: ...

    @classmethod
    def needing(cls, name: str, summary: str, *materials: str) -> StageInterface: ...


@runtime_checkable
class GapInterface(Protocol):
    @property
    def stage(self) -> str: ...

    @property
    def material(self) -> str: ...

    @property
    def prop(self) -> str: ...

    @property
    def minimum(self) -> float: ...

    @property
    def value(self) -> float | None: ...

    @property
    def source(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def verdict(self) -> str: ...

    def describe(self) -> str: ...


@runtime_checkable
class StageVerdictInterface(Protocol):
    @property
    def stage(self) -> str: ...

    @property
    def verdict(self) -> str: ...

    @property
    def gaps(self) -> tuple[GapInterface, ...]: ...


@runtime_checkable
class PipelineVerdictInterface(Protocol):
    @property
    def verdict(self) -> str: ...

    @property
    def stages(self) -> tuple[StageVerdictInterface, ...]: ...

    @property
    def blocked_at(self) -> str | None: ...

    @property
    def shortfalls(self) -> tuple[GapInterface, ...]: ...

    @property
    def unknowns(self) -> tuple[GapInterface, ...]: ...

    @property
    def required(self) -> int: ...

    @property
    def required_measured(self) -> int: ...

    @property
    def confidence(self) -> float: ...


@runtime_checkable
class FeasibilityEvaluatorClassInterface(FeasibilityEvaluatorInterface, Protocol):
    """The three-valued feasibility evaluator."""


@runtime_checkable
class FitLoopInterface(Protocol):
    def default_journal(self) -> Path: ...

    def replay(self) -> Sequence[object]: ...

    def observe(self, *args: object, **kwargs: object) -> object: ...

    def estimate(self, *args: object, **kwargs: object) -> object: ...

    def decisions(self) -> Sequence[object]: ...

    def admit(self) -> object: ...

    def recommendation(self) -> object: ...


@runtime_checkable
class FlattenErrorInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class RangeCommitInterface(Protocol):
    @property
    def sha(self) -> str: ...

    @property
    def author(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def merge(self) -> bool: ...


@runtime_checkable
class ReviewThreadInterface(Protocol):
    @property
    def author(self) -> str: ...

    @property
    def path(self) -> str: ...

    @property
    def line(self) -> int | None: ...

    @property
    def excerpt(self) -> str: ...


@runtime_checkable
class FlattenPlanInterface(Protocol):
    @property
    def branch(self) -> str: ...

    @property
    def base(self) -> str: ...

    @property
    def base_sha(self) -> str: ...

    @property
    def old_sha(self) -> str: ...

    @property
    def tree(self) -> str: ...

    @property
    def range_size(self) -> int: ...

    @property
    def commits(self) -> tuple[RangeCommitInterface, ...]: ...

    @property
    def threads(self) -> tuple[ReviewThreadInterface, ...]: ...

    @property
    def threads_problem(self) -> str | None: ...

    def subject(self) -> str: ...


@runtime_checkable
class VerdictInterface(Protocol):
    @property
    def number(self) -> int: ...

    @property
    def title(self) -> str: ...

    @property
    def author(self) -> str: ...

    @property
    def reason(self) -> str: ...

    @property
    def held_for_review(self) -> bool: ...

    @property
    def restackable(self) -> bool: ...

    def ready(self) -> bool: ...


@runtime_checkable
class AutomationStateInterface(Protocol):
    @property
    def lineage_sha(self) -> str: ...

    @property
    def current_sha(self) -> str: ...

    @property
    def attempts(self) -> int: ...

    @property
    def review_sha(self) -> str | None: ...

    @property
    def review_passed(self) -> bool: ...

    @property
    def review_repairable(self) -> bool: ...

    @property
    def replacement_pr(self) -> int | None: ...

    @property
    def heals(self) -> int: ...

    @property
    def history(self) -> tuple[object, ...]: ...


@runtime_checkable
class ProtectedPathsGuardInterface(ProtectedPathsInterface, Protocol):
    def touched(self, patterns: Sequence[str], paths: Iterable[str]) -> tuple[str, ...]: ...

    def parse_listing(self, text: str) -> tuple[tuple[str, ...], int]: ...

    def refusal(self, pr: Mapping[str, Any], patterns: Sequence[str]) -> str | None: ...


@runtime_checkable
class ReviewComposerClassInterface(ReviewComposerPort, Protocol):
    """The composed sovereign-plus-paid review implementation."""


@runtime_checkable
class ReviewContractClassInterface(ReviewContractPort, Protocol):
    """The review field split used by both lanes."""
