# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from vibey.domain.effort import Effort
from vibey.domain.engine import (
    Capability,
    EngineDescriptor,
    EngineId,
    EngineInvocation,
    IsolationLevel,
    JobRequirement,
)


def _descriptor(effort_projection: dict[Effort, EngineInvocation]) -> EngineDescriptor:
    return EngineDescriptor(
        engine_id=EngineId.CODEXLOOP,
        binary="codexloop",
        min_version="1.0.0",
        state_dir=".codexloop",
        done_marker="CODEXLOOP_TASK_FULLY_COMPLETE",
        auth_env=("OPENAI_API_KEY",),
        capabilities=frozenset({Capability.STRUCTURED_VERDICT}),
        effort_projection=effort_projection,
        session_verb="resume",
        isolation_flags={IsolationLevel.WORKTREE: ()},
        cost_per_mtok_in=1.0,
        cost_per_mtok_out=2.0,
        context_window=128_000,
    )


def test_invoke_returns_exact_projection_when_present() -> None:
    descriptor = _descriptor(
        {
            Effort.LOW: EngineInvocation(("--effort", "low"), achieved=Effort.LOW),
            Effort.HIGH: EngineInvocation(("--effort", "high"), achieved=Effort.HIGH),
        }
    )

    assert descriptor.invoke(Effort.LOW).achieved is Effort.LOW
    assert descriptor.invoke(Effort.HIGH).achieved is Effort.HIGH


def test_invoke_falls_back_to_highest_projection_at_or_below_requested() -> None:
    descriptor = _descriptor(
        {
            Effort.TRIVIAL: EngineInvocation((), achieved=Effort.TRIVIAL),
            Effort.HIGH: EngineInvocation(("--effort", "high"), achieved=Effort.HIGH),
        }
    )

    invocation = descriptor.invoke(Effort.MAX)

    assert invocation.achieved is Effort.HIGH


def test_invoke_raises_when_no_projection_at_or_below_requested() -> None:
    descriptor = _descriptor(
        {Effort.HIGH: EngineInvocation(("--effort", "high"), achieved=Effort.HIGH)}
    )

    with pytest.raises(KeyError):
        descriptor.invoke(Effort.LOW)


@pytest.mark.parametrize(
    ("requested", "achieved", "expected_saturated"),
    [
        (Effort.HIGH, Effort.HIGH, False),
        (Effort.MAX, Effort.HIGH, True),
        (Effort.LOW, Effort.LOW, False),
        (Effort.STANDARD, Effort.HIGH, False),
    ],
)
def test_saturates_at_truth_table(
    requested: Effort, achieved: Effort, expected_saturated: bool
) -> None:
    descriptor = _descriptor({requested: EngineInvocation((), achieved=achieved)})

    assert descriptor.saturates_at(requested) is expected_saturated


def test_job_requirement_defaults() -> None:
    requirement = JobRequirement(effort=Effort.STANDARD)

    assert requirement.capabilities == frozenset()
    assert requirement.excluded == frozenset()


def test_job_requirement_excluded_carries_the_must_differ_constraint() -> None:
    requirement = JobRequirement(effort=Effort.HIGH, excluded=frozenset({EngineId.CLAUDELOOP}))

    assert EngineId.CLAUDELOOP in requirement.excluded


def test_local_engines_are_preferred_before_paid_ones() -> None:
    """Sub-doctrine 8.a, as data: the sovereign tier is tried first (ADR-0038)."""
    from vibey.domain.engine import TIER_PREFERENCE, EngineTier

    assert TIER_PREFERENCE == (EngineTier.LOCAL, EngineTier.PAID)


def test_claudeloop_local_is_its_own_engine_id_not_a_flag() -> None:
    from vibey.domain.engine import EngineId

    assert EngineId("claudeloop-local") is EngineId.CLAUDELOOP_LOCAL


def test_a_misconfigured_backend_exits_ex_config() -> None:
    from vibey.domain.engine import EXIT_CODE_BACKEND_MISCONFIGURED, EXIT_CODE_WIND_DOWN

    assert EXIT_CODE_BACKEND_MISCONFIGURED == 78
    assert EXIT_CODE_BACKEND_MISCONFIGURED != EXIT_CODE_WIND_DOWN


# -- the two loops and what a descriptor declares about running one ----------------------------


def test_the_family_runs_exactly_two_loops_one_per_tier() -> None:
    from vibey.domain.engine import LOOP_BY_TIER, EngineTier, Loop

    assert [loop.value for loop in Loop] == ["sovereignloop", "paidloop"]
    assert dict(LOOP_BY_TIER) == {EngineTier.LOCAL: Loop.SOVEREIGN, EngineTier.PAID: Loop.PAID}


def test_sovereign_is_the_default_and_claude_the_paid_default() -> None:
    from vibey.domain.engine import DEFAULT_LOOP, PAID_DEFAULT_ENGINE, EngineId, Loop

    assert DEFAULT_LOOP is Loop.SOVEREIGN
    assert PAID_DEFAULT_ENGINE is EngineId.CLAUDELOOP


def test_the_repealed_opencode_engine_is_deleted_and_nothing_is_left_repealed() -> None:
    """Canon 8.b repealed OpenCode; its engine and runner are now deleted, so no engine
    waits between repeal and deletion."""
    from vibey.domain.engine import REPEALED_FROM_LOOPS, EngineId

    assert "opencode" not in {engine.value for engine in EngineId}
    assert frozenset() == REPEALED_FROM_LOOPS


def test_a_stored_opencode_engine_id_still_reads_verbatim() -> None:
    """Rows written while opencode was an engine stay in the append-only ledger and the
    shared tables; a reader keeps the text instead of raising on it."""
    from vibey.domain.engine import ENGINE_ID_PARSER, UnrecognizedEngineId

    assert ENGINE_ID_PARSER.parse("opencode") == UnrecognizedEngineId("opencode")


def test_a_descriptor_declares_nothing_it_has_not_shown() -> None:
    """Every new fact defaults to unknown, so an engine nobody has checked shows no menu,
    no control and no event log."""
    from vibey.domain.engine import EngineAffordances, EngineControls, EventLog

    unknown = _descriptor({})
    assert unknown.affordances == EngineAffordances()
    assert unknown.controls == EngineControls()
    assert unknown.events == EventLog()
    affordances = EngineAffordances()
    assert (
        affordances.images,
        affordances.files,
        affordances.paste_text,
        affordances.paste_images,
        affordances.plugins,
        affordances.mcp,
    ) == (None, None, None, None, None, None)
    assert affordances.evidence == {}
    assert (EventLog().path, EventLog().envelope) == (None, None)
    controls = EngineControls()
    assert (controls.stop, controls.wind_down, controls.prompt) == (None, None, None)


def test_the_plugin_systems_and_event_envelopes_are_named_as_the_contract_names_them() -> None:
    from vibey.domain.engine import EventEnvelope, PluginSystem

    assert [system.value for system in PluginSystem] == ["skills-context", "claude-plugins"]
    assert [envelope.value for envelope in EventEnvelope] == [
        "type",
        "event_type+payload",
        "event_type",
    ]
