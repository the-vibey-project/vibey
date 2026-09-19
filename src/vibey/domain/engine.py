# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Final

from vibey.domain.effort import Effort
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.domain.stored_value import StoredValueParser, UnrecognizedValue

# The *loop runners' shared "graceful wind-down" exit code: the engine ran
# out of window capacity mid-item and stopped cleanly after writing its
# state, so the item hands off to another engine instead of failing
# (handoff-protocol.md §3). A domain constant because the meaning belongs
# to the protocol, not to any one subprocess adapter.
EXIT_CODE_WIND_DOWN = 75

# EX_CONFIG from sysexits.h: the runner stopped because its own backend is
# misconfigured -- an unreachable local server, a model that is not pulled or
# fails to load, a context window too small for one request. claudeloop exits
# with it for `BackendMisconfigured`. No retry fixes a configuration, so the
# job parks for a human instead of burning its attempts on the same fault.
EXIT_CODE_BACKEND_MISCONFIGURED = 78


class EngineId(StrEnum):
    CLAUDELOOP = "claudeloop"
    CODEXLOOP = "codexloop"
    CURSORLOOP = "cursorloop"
    AGYLOOP = "agyloop"
    QWENLOOP = "qwenloop"
    # The same claudeloop binary, driven through a named backend profile that
    # points Claude Code at a local model (Ollama) instead of Anthropic. A
    # separate engine, not a flag on claudeloop: it has its own health row,
    # its own circuit, its own cost (zero) and its own tier (ADR-0038).
    CLAUDELOOP_LOCAL = "claudeloop-local"


class EngineTier(StrEnum):
    """Who the engine answers to. LOCAL runs on hardware the operator owns and
    costs nothing per token; PAID runs on a vendor's account."""

    LOCAL = "local"
    PAID = "paid"


# Selection order across tiers. Sub-doctrine 8.a: the sovereign path is the
# preference, not the fallback -- a paid engine is chosen only when no local
# engine is eligible (ADR-0038, amending ADR-0015's standby rule).
TIER_PREFERENCE: tuple[EngineTier, ...] = (EngineTier.LOCAL, EngineTier.PAID)


@dataclass(frozen=True, slots=True)
class UnrecognizedEngineId(UnrecognizedValue):
    """A stored engine id this vibey has no `EngineId` member for (vibey#287).

    The `engine_id` columns are plain text, so a newer vibey adds an engine without
    a migration -- #281's `claudeloop-local` is the first -- and its health rows,
    rotation cursors, ledger events and job requirements reach the older workers of a
    rolling upgrade at once. An older worker can never run such an engine, so it
    never selects one; what it must not do is crash on the row.
    """

    members: ClassVar[frozenset[str]] = frozenset(engine.value for engine in EngineId)


type StoredEngineId = EngineId | UnrecognizedEngineId
"""What a stored engine id reads as: a member this vibey knows, or the text of one
it does not. Narrow with `isinstance(engine_id, EngineId)` before using it as a key
of a `Mapping[EngineId, ...]` or handing it to anything that runs an engine."""

ENGINE_ID_PARSER: Final[StoredValueParserInterface[EngineId, UnrecognizedEngineId]] = (
    StoredValueParser(EngineId, UnrecognizedEngineId)
)
"""The parser every reader of an `engine_id` column shares. Stateless."""


class Capability(StrEnum):
    SAVEPOINTS = "savepoints"
    UNWIND = "unwind"
    STRUCTURED_VERDICT = "structured_verdict"
    MID_RUN_PROMPT = "mid_run_prompt"
    MID_RUN_MODEL = "mid_run_model"
    MID_RUN_EFFORT = "mid_run_effort"
    ATTACHMENTS = "attachments"
    SLASH_COMMANDS = "slash_commands"
    WEB_SEARCH = "web_search"
    SNAPSHOT = "snapshot"
    SANDBOX = "sandbox"


class IsolationLevel(StrEnum):
    WORKTREE = "worktree"
    CONTAINER = "container"
    VM = "vm"


@dataclass(frozen=True, slots=True)
class EngineInvocation:
    argv: tuple[str, ...]
    achieved: Effort
    notes: str = ""


@dataclass(frozen=True, slots=True)
class EngineDescriptor:
    engine_id: EngineId
    binary: str
    min_version: str
    state_dir: str
    done_marker: str
    auth_env: tuple[str, ...]
    capabilities: frozenset[Capability]
    effort_projection: Mapping[Effort, EngineInvocation]
    session_verb: str
    isolation_flags: Mapping[IsolationLevel, tuple[str, ...]]
    cost_per_mtok_in: float
    cost_per_mtok_out: float
    context_window: int
    base_weight: int = 1
    # Whether the engine's own `run`/`resume` CLI accepts a `--cwd` flag.
    # False for an engine that doesn't have it yet (verified against the
    # real installed binary, not assumed) -- build_argv() must not append a
    # flag the binary would reject at argument parsing, before it ever gets
    # a chance to run.
    supports_cwd_flag: bool = True
    # How the engine's `run` verb takes the plan file. None means a bare
    # positional path (claudeloop, codexloop, agyloop); a string is the flag
    # the binary requires instead (cursorloop: `--plan`). Verified against
    # each installed binary's own --help, never assumed -- passing a
    # positional to a binary that wants a flag fails at argument parsing,
    # before the session ever starts.
    plan_flag: str | None = None
    # Which side of TIER_PREFERENCE the engine sits on. PAID unless the
    # engine runs on the operator's own hardware.
    tier: EngineTier = EngineTier.PAID
    # Extra arguments for `<binary> doctor` in preflight. claudeloop-local
    # passes its profile, so the health check probes the local backend the
    # run will use rather than the Anthropic login a profile never touches.
    doctor_args: tuple[str, ...] = ()

    def invoke(self, effort: Effort) -> EngineInvocation:
        try:
            return self.effort_projection[effort]
        except KeyError:
            # Fall back to the highest projection at or below the requested
            # effort -- the descriptor's own saturation point.
            candidates = sorted((e for e in self.effort_projection if e <= effort), reverse=True)
            if not candidates:
                raise
            return self.effort_projection[candidates[0]]

    def saturates_at(self, effort: Effort) -> bool:
        return self.invoke(effort).achieved < effort


@dataclass(frozen=True, slots=True)
class JobRequirement:
    effort: Effort
    capabilities: frozenset[Capability] = frozenset()
    excluded: frozenset[EngineId] = frozenset()  # the "must differ" constraint
