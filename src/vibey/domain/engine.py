# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
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
    # The sovereign default engine (8.b, 8.d): the local runner on GPT-OSS, on unless a
    # project switches it off. What was called qwenloop until ADR-0062, when qwenloop
    # became the same runner on the Qwen model its name promises -- opt-in, below.
    GPTOSSLOOP = "gptossloop"
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


class Loop(StrEnum):
    """The family's two loops, exactly two (sub-doctrine 8.c)."""

    SOVEREIGN = "sovereignloop"
    PAID = "paidloop"


LOOP_BY_TIER: Final[Mapping[EngineTier, Loop]] = MappingProxyType(
    {EngineTier.LOCAL: Loop.SOVEREIGN, EngineTier.PAID: Loop.PAID}
)
"""The loop that drives an engine of each tier (8.c): the sovereign loop what runs on the
operator's own hardware, the paid loop every paid engine."""

DEFAULT_LOOP: Final = Loop.SOVEREIGN
"""The canon's default loop (8.a, 8.b); every other loop is reached only by declaration. This
states the rule. The selector does not read a paid declaration yet: it prefers the local tier
(`TIER_PREFERENCE`) and falls back to a paid engine whenever no local engine is eligible."""

PAID_DEFAULT_ENGINE: Final = EngineId.CLAUDELOOP
"""The canon's paid default (8.b): Claude, through claudeloop, the paid engine a paid
declaration reaches unless it names another. It never makes paid a default over sovereign.
The selector does not act on it yet: within the paid tier it rotates by weight."""

REPEALED_FROM_LOOPS: Final[frozenset[EngineId]] = frozenset()
"""Engines 8.b repeals from both loops while their code is still in the tree. Their
descriptors are not changed by being named here: anything that reports one reports it as
the code says, and says the canon differs. Empty since the repealed OpenCode engine and its
runner were deleted: a repeal ends in deletion, and this set holds only the interval between
the two."""

RENAMED_ENGINES: Final[Mapping[EngineId, str]] = MappingProxyType(
    {
        EngineId.QWENLOOP: (
            "since ADR-0062 qwenloop runs a Qwen model (qwen3:14b unless QWENLOOP_MODEL "
            "names another); the gpt-oss engine it used to be is gptossloop"
        ),
    }
)
"""Engines whose name now means something it did not, and what a reader who knew the old
meaning needs to hear. Reported beside the engine; nothing selects by it."""


class PluginSystem(StrEnum):
    """How a loop takes extensions beyond its plan."""

    SKILLS_CONTEXT = "skills-context"
    """vibey-skills context packets: text vibey writes into the plan, so any loop takes them."""
    CLAUDE_PLUGINS = "claude-plugins"
    """Claude Code's own plugin system, where a loop runs it."""


@dataclass(frozen=True, slots=True)
class EngineAffordances:
    """What a person can hand a loop besides its plan -- the menus an editor may offer.

    `None` is unknown: nothing in the tree shows it either way, and no menu is offered for
    it. A value is set on a descriptor only where the runner's own code or `--help` shows it,
    and `evidence` names where, by the field it proves. Never from memory or a vendor's
    marketing.
    """

    images: bool | None = None
    files: bool | None = None
    paste_text: bool | None = None
    paste_images: bool | None = None
    plugins: PluginSystem | None = None
    mcp: bool | None = None
    evidence: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EngineControls:
    """A runner's own verbs for a run in flight, as the argv after its binary. `{run_id}`,
    `{cwd}` and, for `prompt`, `{text}` are filled in by the caller. `None` is unverified:
    the runner's CLI definition in this tree does not show that verb."""

    stop: tuple[str, ...] | None = None
    wind_down: tuple[str, ...] | None = None
    prompt: tuple[str, ...] | None = None


class EventEnvelope(StrEnum):
    """How a runner shapes one line of its events.jsonl."""

    TYPE = "type"
    """A top-level `"type"` key, the fields beside it."""
    EVENT_TYPE_PAYLOAD = "event_type+payload"
    """`{"event_type": ..., "payload": {...}}`."""
    EVENT_TYPE = "event_type"
    """A top-level `"event_type"` key, the fields beside it, and no payload wrapper."""


@dataclass(frozen=True, slots=True)
class EventLog:
    """Where a runner writes a run's events, as a template over `{cwd}`, `{state_dir}` and
    `{run_id}`, and how each line is shaped. `None` is unverified."""

    path: str | None = None
    envelope: EventEnvelope | None = None


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
    # Optional flag that lets an adapter keep the orchestration run id when
    # resuming a provider session. Most runners derive their state path from
    # the session id; a runner that keeps the provider's session id and vibey's
    # run id apart accepts this explicit value instead.
    resume_run_id_flag: str | None = None
    # Which side of TIER_PREFERENCE the engine sits on. PAID unless the
    # engine runs on the operator's own hardware.
    tier: EngineTier = EngineTier.PAID
    # Extra arguments for `<binary> doctor` in preflight. claudeloop-local
    # passes its profile, so the health check probes the local backend the
    # run will use rather than the Anthropic login a profile never touches.
    doctor_args: tuple[str, ...] = ()
    # The environment variables the engine's own process reads -- its runner's
    # configuration and its vendor CLI's -- passed through to its sessions on top of
    # the system basics. A trailing `*` names a prefix (`CLAUDELOOP_*`); `auth_env`
    # always passes too. Nothing else in the worker's environment reaches a session
    # unless the project declares it, and vibey's own variables never can
    # (infrastructure/engines/engine_environment.py).
    env_passthrough: tuple[str, ...] = ()
    # What a person can hand this loop besides its plan (images, files, pasted text or
    # images, plugins, MCP), each proven from the runner's own code or `--help` and the
    # proof named in `evidence`; unknown until then. `vibey loops` reports them.
    affordances: EngineAffordances = EngineAffordances()
    # The runner's own CLI verbs for a run in flight, from its CLI definition; unverified
    # until then. vibey's adapter itself steers a run through files in its run directory.
    controls: EngineControls = EngineControls()
    # Where the runner writes a run's events and how each line is shaped, from its writer.
    events: EventLog = EventLog()

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
