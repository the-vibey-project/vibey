# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import importlib

import pytest
import typer

from vibey.domain.effort import Effort
from vibey.domain.engine import EngineControls, EngineId, EventEnvelope, EventLog, PluginSystem
from vibey.infrastructure.engines.descriptors import (
    AGYLOOP,
    ALL_DESCRIPTORS,
    BY_ENGINE_ID,
    CLAUDELOOP,
    CODEXLOOP,
    CURSORLOOP,
    OPENCODE,
    QWENLOOP,
)

ALL_EFFORTS = list(Effort)

# claudeloop/agyloop/cursorloop all have a real, verified per-effort CLI
# flag (confirmed against real --help output, see descriptors.py's own
# header comment) and so always produce non-empty argv. codexloop has no
# CLI-level effort control at all -- see test_codexloop_has_no_cli_level_
# effort_control below for its own, deliberately different invariant. OpenCode
# is also deliberately empty because its provider-specific model controls are
# not a portable effort contract.
DESCRIPTORS_WITH_REAL_EFFORT_FLAGS = [
    d for d in ALL_DESCRIPTORS if d.engine_id not in {EngineId.CODEXLOOP, EngineId.OPENCODE}
]


@pytest.mark.parametrize(
    "descriptor", DESCRIPTORS_WITH_REAL_EFFORT_FLAGS, ids=lambda d: d.engine_id.value
)
@pytest.mark.parametrize("effort", ALL_EFFORTS)
def test_invoke_covers_every_effort_level(descriptor, effort) -> None:  # type: ignore[no-untyped-def]
    invocation = descriptor.invoke(effort)
    assert invocation.argv
    assert invocation.achieved <= effort


def test_all_descriptors_have_unique_engine_ids() -> None:
    ids = [d.engine_id for d in ALL_DESCRIPTORS]
    assert len(ids) == len(set(ids))
    assert set(ids) == set(EngineId)


def test_by_engine_id_matches_all_descriptors() -> None:
    assert set(BY_ENGINE_ID) == {d.engine_id for d in ALL_DESCRIPTORS}
    for descriptor in ALL_DESCRIPTORS:
        assert BY_ENGINE_ID[descriptor.engine_id] is descriptor


def test_claudeloop_and_agyloop_achieve_full_five_level_range() -> None:
    for effort in ALL_EFFORTS:
        assert CLAUDELOOP.invoke(effort).achieved is effort
        assert AGYLOOP.invoke(effort).achieved is effort


def test_codexloop_has_no_cli_level_effort_control() -> None:
    """codexloop's `run` has no --effort flag at all (confirmed against real
    --help and cli/commands/run.py directly) and no other CLI-level way to
    set effort/reasoning depth at invocation -- per its own domain/
    model_profile.py it always starts at internal Effort.MEDIUM and can
    only change via a runtime SetEffort event, not a launch flag. Every
    level projects to empty argv and Effort.STANDARD (MEDIUM's vibey
    equivalent) -- vibey's own effort request has no effect on codexloop
    today, so requesting anything above STANDARD saturates."""
    for effort in ALL_EFFORTS:
        invocation = CODEXLOOP.invoke(effort)
        assert invocation.argv == ()
        assert invocation.achieved is Effort.STANDARD
    assert CODEXLOOP.saturates_at(Effort.TRIVIAL) is False
    assert CODEXLOOP.saturates_at(Effort.LOW) is False
    assert CODEXLOOP.saturates_at(Effort.STANDARD) is False
    assert CODEXLOOP.saturates_at(Effort.HIGH) is True
    assert CODEXLOOP.saturates_at(Effort.MAX) is True


def test_opencode_has_no_portable_cli_effort_control() -> None:
    from vibey.infrastructure.engines.descriptors import OPENCODE

    assert [OPENCODE.invoke(e).argv for e in ALL_EFFORTS] == [()] * len(ALL_EFFORTS)
    assert all(OPENCODE.invoke(e).achieved is Effort.STANDARD for e in ALL_EFFORTS)
    assert OPENCODE.saturates_at(Effort.HIGH)


def test_agyloop_uses_real_five_level_effort_flag() -> None:
    assert AGYLOOP.invoke(Effort.MAX).argv == ("--preset", "high", "--effort", "max")
    assert AGYLOOP.saturates_at(Effort.MAX) is False


def test_cursorloop_has_no_effort_flag_only_model_ids() -> None:
    for effort in ALL_EFFORTS:
        invocation = CURSORLOOP.invoke(effort)
        assert invocation.argv[0] == "--model"
        assert invocation.achieved is effort


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_saturates_at_truth_table(descriptor) -> None:  # type: ignore[no-untyped-def]
    for effort in ALL_EFFORTS:
        achieved = descriptor.invoke(effort).achieved
        assert descriptor.saturates_at(effort) == (achieved < effort)


# ── claudeloop-local (ADR-0038) ───────────────────────────────────────────────


def test_claudeloop_local_is_the_claudeloop_binary_on_a_profile_at_no_cost() -> None:
    from vibey.domain.engine import EngineTier
    from vibey.infrastructure.engines.descriptors import CLAUDELOOP_LOCAL

    assert CLAUDELOOP_LOCAL.engine_id is EngineId.CLAUDELOOP_LOCAL
    assert CLAUDELOOP_LOCAL.binary == CLAUDELOOP.binary
    assert CLAUDELOOP_LOCAL.state_dir == CLAUDELOOP.state_dir
    assert CLAUDELOOP_LOCAL.done_marker == CLAUDELOOP.done_marker
    assert CLAUDELOOP_LOCAL.auth_env == ()
    assert (CLAUDELOOP_LOCAL.cost_per_mtok_in, CLAUDELOOP_LOCAL.cost_per_mtok_out) == (0.0, 0.0)
    assert CLAUDELOOP_LOCAL.tier is EngineTier.LOCAL
    assert CLAUDELOOP_LOCAL.doctor_args == ("--profile", "local")


def test_claudeloop_local_honest_ceiling_is_standard_even_at_max() -> None:
    from vibey.infrastructure.engines.descriptors import CLAUDELOOP_LOCAL

    assert [CLAUDELOOP_LOCAL.invoke(e).achieved for e in ALL_EFFORTS] == [
        Effort.TRIVIAL,
        Effort.LOW,
        Effort.STANDARD,
        Effort.STANDARD,
        Effort.STANDARD,
    ]
    assert CLAUDELOOP_LOCAL.saturates_at(Effort.HIGH)
    assert CLAUDELOOP_LOCAL.saturates_at(Effort.MAX)
    assert "ceiling" in CLAUDELOOP_LOCAL.invoke(Effort.MAX).notes
    assert CLAUDELOOP_LOCAL.invoke(Effort.STANDARD).notes == ""


def test_claudeloop_local_is_built_from_its_configured_profile() -> None:
    from vibey.domain.config import ClaudeloopLocalConfig
    from vibey.infrastructure.engines.descriptors import ClaudeloopLocalDescriptors
    from vibey.infrastructure.engines.interfaces import ClaudeloopLocalDescriptorsInterface

    factory = ClaudeloopLocalDescriptors()
    built = factory.build(ClaudeloopLocalConfig(profile="gpu-box", context_window=65_536))

    assert isinstance(factory, ClaudeloopLocalDescriptorsInterface)
    assert built.invoke(Effort.HIGH).argv == ("--profile", "gpu-box", "--preset", "high")
    assert built.doctor_args == ("--profile", "gpu-box")
    assert built.context_window == 65_536


def test_claudeloop_local_claims_a_structured_verdict_only_when_configured_to() -> None:
    """A local model has to prove it can make the tool call a verdict is. Unclaimed by
    default; claimed, conformance must prove it or the engine is ineligible."""
    from vibey.domain.config import ClaudeloopLocalConfig
    from vibey.domain.engine import Capability
    from vibey.infrastructure.engines.descriptors import (
        CLAUDELOOP_LOCAL,
        ClaudeloopLocalDescriptors,
    )

    assert Capability.STRUCTURED_VERDICT not in CLAUDELOOP_LOCAL.capabilities
    claimed = ClaudeloopLocalDescriptors().build(ClaudeloopLocalConfig(structured_verdict=True))
    assert Capability.STRUCTURED_VERDICT in claimed.capabilities
    # A local profile does not forward --effort, so effort cannot change mid-run either.
    assert Capability.MID_RUN_EFFORT not in claimed.capabilities


def test_the_local_descriptors_are_exactly_the_local_tier() -> None:
    from vibey.domain.engine import EngineTier
    from vibey.infrastructure.engines.descriptors import DEFAULT_DESCRIPTORS, LOCAL_DESCRIPTORS

    assert {d.tier for d in LOCAL_DESCRIPTORS} == {EngineTier.LOCAL}
    assert {d.tier for d in DEFAULT_DESCRIPTORS} == {EngineTier.PAID, EngineTier.LOCAL}


# -- what `vibey loops` reports about each engine ---------------------------------------------
#
# Every value below was read from the runner's own code in this tree. The tests hold the
# descriptors to it: a declared control must be a verb the runner's CLI defines, with the
# options and positionals the template uses, and a capability that is set must name its proof.

AFFORDANCE_FIELDS = ("images", "files", "paste_text", "paste_images", "plugins", "mcp")
RUNNER_CLI = {
    EngineId.CLAUDELOOP: "claudeloop.cli.app",
    EngineId.CLAUDELOOP_LOCAL: "claudeloop.cli.app",
    EngineId.CODEXLOOP: "codexloop.cli.app",
    EngineId.CURSORLOOP: "cursorloop.cli.app",
    EngineId.AGYLOOP: "agyloop.cli.app",
    EngineId.OPENCODE: "opencodeloop.cli.app",
    EngineId.QWENLOOP: "qwenloop.cli.app",
}
VERBS = {"stop": "stop", "wind_down": "wind-down", "prompt": "prompt"}


def _runner_commands(engine_id: EngineId) -> dict[str, object]:
    """The runner's own verbs, read from its Typer app. Typer carries its own click, so
    the parameters are told apart by `param_type_name`, not by class."""
    app = importlib.import_module(RUNNER_CLI[engine_id]).app
    return dict(typer.main.get_command(app).commands)  # type: ignore[attr-defined]


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_every_capability_that_is_set_names_its_proof(descriptor) -> None:  # type: ignore[no-untyped-def]
    affordances = descriptor.affordances
    for name in AFFORDANCE_FIELDS:
        if getattr(affordances, name) is None:
            assert name not in affordances.evidence, f"{descriptor.engine_id}: {name}"
        else:
            assert affordances.evidence.get(name, "").strip(), f"{descriptor.engine_id}: {name}"
    assert set(affordances.evidence) <= set(AFFORDANCE_FIELDS)


def test_the_capabilities_each_runner_shows() -> None:
    shown = {
        d.engine_id.value: tuple(getattr(d.affordances, name) for name in AFFORDANCE_FIELDS)
        for d in ALL_DESCRIPTORS
    }
    claude = (None, True, True, None, PluginSystem.CLAUDE_PLUGINS, True)
    skills = PluginSystem.SKILLS_CONTEXT
    assert shown == {
        "claudeloop": claude,
        "codexloop": (None, True, True, None, skills, None),
        "cursorloop": (None, True, True, None, skills, None),
        "agyloop": (None, True, True, None, skills, False),
        "opencode": (None, True, True, None, skills, None),
        "qwenloop": (False, True, True, False, skills, False),
        "claudeloop-local": claude,
    }


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_every_declared_control_is_a_verb_the_runner_defines_as_the_template_uses_it(
    descriptor,  # type: ignore[no-untyped-def]
) -> None:
    commands = _runner_commands(descriptor.engine_id)
    for field, verb in VERBS.items():
        template = getattr(descriptor.controls, field)
        if template is None:
            continue
        assert template[0] == verb
        command = commands[verb]
        params = command.params  # type: ignore[attr-defined]
        options = {opt for p in params if p.param_type_name == "option" for opt in p.opts}
        arguments = [p for p in params if p.param_type_name == "argument"]
        words = template[1:]
        values = {i + 1 for i, word in enumerate(words) if word.startswith("--")}
        flags = [word for word in words if word.startswith("--")]
        positionals = [w for i, w in enumerate(words) if not w.startswith("--") and i not in values]
        assert set(flags) <= options, f"{descriptor.engine_id} {verb}: {flags} vs {options}"
        assert len(positionals) == len(arguments), f"{descriptor.engine_id} {verb}"


def test_a_control_left_undeclared_is_one_the_runner_cannot_take() -> None:
    """agyloop has no wind-down verb; opencodeloop has no control verb at all. qwenloop's
    prompt is the one verb that exists and is still not declared: its runner never reads the
    control that verb writes (qwenloop application/runner.py)."""
    assert "wind-down" not in _runner_commands(EngineId.AGYLOOP)
    assert not {"stop", "wind-down", "prompt"} & set(_runner_commands(EngineId.OPENCODE))
    assert QWENLOOP.controls.prompt is None
    assert AGYLOOP.controls.wind_down is None
    assert OPENCODE.controls == EngineControls()


def test_the_controls_each_runner_defines() -> None:
    assert CLAUDELOOP.controls == EngineControls(
        stop=("stop", "--run-id", "{run_id}", "--cwd", "{cwd}"),
        wind_down=("wind-down", "--run-id", "{run_id}", "--cwd", "{cwd}"),
        prompt=("prompt", "{text}", "--now", "--run-id", "{run_id}", "--cwd", "{cwd}"),
    )
    assert CODEXLOOP.controls == EngineControls(
        stop=("stop", "--run-id", "{run_id}"),
        wind_down=("wind-down", "--run-id", "{run_id}"),
        prompt=("prompt", "{text}", "--now", "--run-id", "{run_id}"),
    )
    assert CURSORLOOP.controls == EngineControls(
        stop=("stop", "--run-id", "{run_id}", "--cwd", "{cwd}"),
        wind_down=("wind-down", "--run-id", "{run_id}", "--cwd", "{cwd}"),
        prompt=("prompt", "{text}", "--run-id", "{run_id}", "--cwd", "{cwd}"),
    )
    assert AGYLOOP.controls == EngineControls(
        stop=("stop", "--run-id", "{run_id}", "--cwd", "{cwd}"),
        prompt=("prompt", "{text}", "--now", "--run-id", "{run_id}", "--cwd", "{cwd}"),
    )
    assert QWENLOOP.controls == EngineControls(
        stop=("stop", "{run_id}", "--cwd", "{cwd}"),
        wind_down=("wind-down", "{run_id}", "--cwd", "{cwd}"),
    )
    assert BY_ENGINE_ID[EngineId.CLAUDELOOP_LOCAL].controls == CLAUDELOOP.controls


def test_every_runner_writes_its_events_in_its_own_run_directory() -> None:
    path = "{cwd}/{state_dir}/runs/{run_id}/events.jsonl"
    envelopes = {d.engine_id.value: d.events for d in ALL_DESCRIPTORS}
    assert envelopes == {
        "claudeloop": EventLog(path, EventEnvelope.EVENT_TYPE_PAYLOAD),
        "codexloop": EventLog(path, EventEnvelope.TYPE),
        "cursorloop": EventLog(path, EventEnvelope.EVENT_TYPE_PAYLOAD),
        "agyloop": EventLog(path, EventEnvelope.EVENT_TYPE_PAYLOAD),
        "opencode": EventLog(path, EventEnvelope.EVENT_TYPE),
        "qwenloop": EventLog(path, EventEnvelope.TYPE),
        "claudeloop-local": EventLog(path, EventEnvelope.EVENT_TYPE_PAYLOAD),
    }
