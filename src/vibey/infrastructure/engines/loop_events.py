# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Event type translation: loop event_type vocabulary → vibey EventKind.

Real loop events.jsonl files use dotted event_type strings ("chatter.assistant",
"sdk.message", "RateLimitEvent") rather than vibey's EventKind vocabulary.
This module maps the observed real event types to EventKind, engine by engine.

CLAUDELOOP's mapping is built from real events.jsonl captured by real,
authenticated, live runs (see docs/plans/fleet/e1-loop-event-map-vibey.md
and the conformance investigation it closed out) -- an earlier version of
this file claimed the same for every engine while actually containing
fabricated event_type strings for all of them (session.user_turn,
function.call, thread.message.user, agent.savepoint, ...: none of these
are real).

CODEXLOOP previously carried that same unverified guesswork. It was
replaced (2026-08-18) with vocabulary read directly from the engine's own
source -- real string literals its own code already recognizes or emits,
not fabrications. At the time, codexloop wrote nothing into events.jsonl in
this environment at all (its sink was fully implemented but not wired into
the real run path -- see docs/plans/fleet/c4-wire-events-sink-codexloop.md);
the gap was fixed and landed the same day (codexloop#30). Current
verification status:

- CODEXLOOP: `infrastructure/events.py::JsonlRunEventSink` is now
  constructed in `bootstrap.py` and wired into `CodexExecGateway`, which
  emits the vocabulary below (sourced from
  `infrastructure/agent/events.py::JsonlParser`, the exact type strings it
  parses from the wrapped `codex exec --json` subprocess's own stdout) to
  the sink after every turn. Verified end to end with a real subprocess
  smoke test -- a fake `codex` binary on PATH (codexloop's own
  `tests/shim/fake_codex.py` harness) driving the real, unmodified
  `CodexExecGateway.send_turn` code path -- confirming events.jsonl is
  genuinely populated with this vocabulary. Not yet observed against a
  live, authenticated `codex` CLI session, since `codex` isn't installed
  in this environment.

Two more paid engines had mappings here until ADR-0078 retired them.

One turn, one TURN_COMPLETED. The budget brake (LedgerBudgetSource) counts
every TURN_COMPLETED in a cycle as a turn against ``max_cycle_turns``, so
each engine maps only the runner's own turn boundary to it -- one event per
real turn -- and nothing else. Text that rides alongside a turn
(claudeloop's ``chatter.*`` echoes, qwenloop's streamed
``text_delta`` fragments) maps to TRANSCRIPT_RECORDED: kept in the ledger
for replay, never counted. Before #266 ``chatter.assistant`` also mapped to
TURN_COMPLETED, so under claudeloop's default ``log_chatter=summary`` a
cycle hit its turn cap after half the configured turns, and every qwenloop
token delta counted as a turn. TURN_REQUESTED follows the same rule
(``turn.starting`` only, not ``chatter.prompt``).
"""

from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind

# Mapping from real loop event_type strings to vibey's EventKind vocabulary.
# Unmapped types are logged and skipped gracefully rather than crashing.

LOOP_EVENT_MAP: dict[EngineId, dict[str, EventKind]] = {
    EngineId.CLAUDELOOP: {
        # Claudeloop events (captured from a real events.jsonl in the
        # conformance run docs/plans/fleet/e1-loop-event-map-vibey.md records).
        "run.started": EventKind.SESSION_SEEDED,
        "preflight": EventKind.SESSION_SEEDED,
        # turn.starting and turn.completed are the runner's own turn
        # boundaries, emitted exactly once per turn whatever log_chatter is
        # set to. chatter.prompt and chatter.assistant echo the same turn's
        # text -- under the default log_chatter=summary, both fire every
        # turn -- so they are transcript, never a second turn.
        "turn.starting": EventKind.TURN_REQUESTED,
        "chatter.prompt": EventKind.TRANSCRIPT_RECORDED,
        "chatter.assistant": EventKind.TRANSCRIPT_RECORDED,
        "turn.completed": EventKind.TURN_COMPLETED,
        # chatter.delta (streamed fragments, log_chatter=full only) stays
        # unmapped: chatter.assistant already carries the assembled text,
        # and mapping every delta would append one ledger row per fragment.
        "chatter.tool": EventKind.TOOL_INVOKED,
        "savepoint": EventKind.SAVEPOINT_CREATED,
        # capacity.forecast is emitted only while capacity IS available (see
        # runner.py::_project_capacity's own docstring: "only while the
        # vendor says we are not already blocked" -- it's proactive headroom
        # telemetry, never a rejection). Mapping it to CAPACITY_REJECTED
        # would make every normal, successful run look capacity-constrained.
        # BUDGET_SPENT matches its actual payload (headroom,
        # turns_until_exhaustion, seconds_until_reset).
        "capacity.forecast": EventKind.BUDGET_SPENT,
        "finished": EventKind.VERDICT_RENDERED,
    },
    EngineId.CODEXLOOP: {
        # Real `codex exec --json` vocabulary, sourced directly from
        # codexloop's own infrastructure/agent/events.py::JsonlParser --
        # the exact type strings it parses from the wrapped codex CLI's
        # own event stream. See the module docstring: now wired end to end
        # and verified with a real subprocess smoke test (fake codex
        # binary, real CodexExecGateway code path), though not yet against
        # a live, authenticated codex CLI session.
        "thread.started": EventKind.SESSION_SEEDED,
        "turn.started": EventKind.TURN_REQUESTED,
        "turn.completed": EventKind.TURN_COMPLETED,
        # turn.failed is still a turn boundary -- success/failure lives in
        # the payload (its ``error`` object), mirroring how VERDICT_RENDERED
        # enrichment elsewhere checks payload fields rather than encoding it
        # into the kind. It is not a double count: codex ends every turn
        # with exactly one of turn.completed or turn.failed, never both. It
        # counts toward the turn cap on purpose -- a failed turn is still a
        # turn attempt the vendor served, and a run failing turn after turn
        # is exactly the runaway the cap exists to stop.
        "turn.failed": EventKind.TURN_COMPLETED,
        # "item" is codex's generic envelope for a discrete unit of agent
        # work -- command execution, patch application, MCP tool calls,
        # reasoning, AND plain agent messages all arrive as item.started/
        # item.completed with the real distinction only in a payload
        # ``type`` field this string-keyed map can't see. Approximated as
        # TOOL_INVOKED, the closest existing EventKind, same coarseness
        # claudeloop already accepts for its own tool events.
        "item.started": EventKind.TOOL_INVOKED,
        "item.completed": EventKind.TOOL_INVOKED,
        # rate_limits.updated is proactive plan/window telemetry folded
        # into TurnSignals for classification -- it is not itself a
        # rejection (see domain/classify.py: rejection comes from
        # error_code/error_type/http_status, never straight from this
        # event), so it gets the same BUDGET_SPENT treatment as
        # claudeloop's capacity.forecast.
        "rate_limits.updated": EventKind.BUDGET_SPENT,
        # codexloop's own wrapper-level terminal verdict (codexloop#35),
        # the one event in its stream that is not raw codex vocabulary. It
        # carries success/complete/reason and, on success only, the done
        # marker -- previously nothing published the marker at all, so a
        # finished codexloop run was indistinguishable from an abandoned
        # one to any reader of events.jsonl.
        "run.verdict": EventKind.VERDICT_RENDERED,
        # "error" and "event_msg" deliberately left unmapped: both are
        # generic wrapper types whose real meaning depends on payload
        # contents this string-keyed map can't see (event_msg mostly
        # carries unrelated telemetry and only rarely means rate-limit
        # data; "error" spans everything from a transient tool hiccup to
        # a fatal auth failure). translate_event_type() already treats an
        # unmapped type as "log and skip" -- the honest choice here.
    },
    EngineId.QWENLOOP: {
        "run.started": EventKind.SESSION_SEEDED,
        # text_delta is one streamed fragment of the model's answer -- many
        # per turn -- so it is transcript. turn.completed is qwenloop's own
        # per-turn boundary (application/runner.py appends one after each
        # model call's stream ends), the only qwenloop event that counts.
        "text_delta": EventKind.TRANSCRIPT_RECORDED,
        "turn.completed": EventKind.TURN_COMPLETED,
        "tool_result": EventKind.TOOL_INVOKED,
        "completed": EventKind.VERDICT_RENDERED,
        "failed": EventKind.VERDICT_RENDERED,
    },
}
# claudeloop-local is the claudeloop binary on a local backend profile: the same
# runner writes the same events.jsonl, so it reads through the same map -- one
# entry, not a copy that could drift from it (ADR-0038).
LOOP_EVENT_MAP[EngineId.CLAUDELOOP_LOCAL] = LOOP_EVENT_MAP[EngineId.CLAUDELOOP]
# gptossloop is the qwenloop runner on GPT-OSS: the same runner writes the same events,
# so it too reads through qwenloop's one entry (ADR-0064).
LOOP_EVENT_MAP[EngineId.GPTOSSLOOP] = LOOP_EVENT_MAP[EngineId.QWENLOOP]


def translate_event_type(engine_id: EngineId, event_type: str) -> EventKind | None:
    """Map a loop's event_type to vibey's EventKind, or None if unrecognized.

    Unrecognized types should be logged and skipped, not raise - a new loop
    version emitting a new event type must not crash vibey.
    """
    engine_map = LOOP_EVENT_MAP.get(engine_id, {})
    return engine_map.get(event_type)


__all__ = ["LOOP_EVENT_MAP", "translate_event_type"]
