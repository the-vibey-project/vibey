# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import importlib
import math
from collections.abc import Sequence

import pytest
import typer

from vibey.domain.effort import Effort
from vibey.domain.engine import (
    Capability,
    EngineAffordances,
    EngineControls,
    EngineId,
    EngineTier,
    EventEnvelope,
    EventLog,
    IsolationLevel,
    PluginSystem,
)
from vibey.infrastructure.engines.argv import EFFORT_ARGV, PLAN_FLAG, RUN_ARGV_TEMPLATE
from vibey.infrastructure.engines.descriptors import (
    ALL_DESCRIPTORS,
    BY_ENGINE_ID,
    CLAUDELOOP,
    CODEXLOOP,
    GPTOSSLOOP,
    QWENLOOP,
)

ALL_EFFORTS = list(Effort)

# Every engine but codexloop has a real, verified per-effort CLI
# flag (confirmed against real --help output, see descriptors.py's own
# header comment) and so always produce non-empty argv. codexloop has no
# CLI-level effort control at all -- see test_codexloop_has_no_cli_level_
# effort_control below for its own, deliberately different invariant.
DESCRIPTORS_WITH_REAL_EFFORT_FLAGS = [
    d for d in ALL_DESCRIPTORS if d.engine_id is not EngineId.CODEXLOOP
]


@pytest.mark.parametrize(
    "descriptor", DESCRIPTORS_WITH_REAL_EFFORT_FLAGS, ids=lambda d: d.engine_id.value
)
@pytest.mark.parametrize("effort", ALL_EFFORTS)
def test_invoke_covers_every_effort_level(descriptor, effort) -> None:  # type: ignore[no-untyped-def]
    invocation = descriptor.invoke(effort)
    # ULTRA passes no turn limit to a runner whose effort is only a turn limit (ADR-0063).
    assert invocation.argv or (
        effort is Effort.ULTRA and "--max-turns" in str(descriptor.invoke(Effort.MAX).argv)
    )
    assert invocation.achieved <= effort


def test_all_descriptors_have_unique_engine_ids() -> None:
    ids = [d.engine_id for d in ALL_DESCRIPTORS]
    assert len(ids) == len(set(ids))
    assert set(ids) == set(EngineId)


def test_by_engine_id_matches_all_descriptors() -> None:
    assert set(BY_ENGINE_ID) == {d.engine_id for d in ALL_DESCRIPTORS}
    for descriptor in ALL_DESCRIPTORS:
        assert BY_ENGINE_ID[descriptor.engine_id] is descriptor


def test_claudeloop_achieves_the_full_five_level_range() -> None:
    for effort in ALL_EFFORTS:
        assert CLAUDELOOP.invoke(effort).achieved is effort


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
    assert {d.tier for d in DEFAULT_DESCRIPTORS} == {EngineTier.PAID}


# -- what `vibey loops` reports about each engine ---------------------------------------------
#
# Every value below was read from the runner's own code in this tree. The tests hold the
# descriptors to it: a declared control must be a verb the runner's CLI defines, with the
# options and positionals the template uses, and a capability that is set must name its proof.

AFFORDANCE_FIELDS = (
    "images",
    "files",
    "paste_text",
    "paste_images",
    "plugins",
    "mcp",
    "skills",
    "web_search",
)
RUNNER_CLI = {
    EngineId.CLAUDELOOP: "claudeloop.cli.app",
    EngineId.CLAUDELOOP_LOCAL: "claudeloop.cli.app",
    EngineId.CODEXLOOP: "codexloop.cli.app",
    EngineId.GPTOSSLOOP: "qwenloop.cli.app",
    EngineId.QWENLOOP: "qwenloop.cli.app",
}
VERBS = {"stop": "stop", "wind_down": "wind-down", "prompt": "prompt"}


def _runner_commands(engine_id: EngineId) -> dict[str, object]:
    """The runner's own verbs, read from its Typer app. Typer carries its own click, so
    the parameters are told apart by `param_type_name`, not by class."""
    app = importlib.import_module(RUNNER_CLI[engine_id]).app
    return dict(typer.main.get_command(app).commands)  # type: ignore[attr-defined]


def _is_placeholder(word: str) -> bool:
    return word.startswith("{") and word.endswith("}")


def _read_as_click_would(command: object, words: Sequence[str], what: str) -> None:
    """Reads `words` against `command`'s parameters the way click parses them, and fails on
    what the runner would refuse: an option it does not define, a value its type rejects, or
    a count of positionals its arguments cannot take.

    A boolean or counting option takes no value; every other option takes the next word. A
    `{placeholder}` is a value the caller fills in, so only its position is checked.
    """
    params = command.params  # type: ignore[attr-defined]
    options = {
        opt: param
        for param in params
        if param.param_type_name == "option"
        for opt in (*param.opts, *param.secondary_opts)
    }
    positionals: list[str] = []
    rest = list(words)
    while rest:
        word = rest.pop(0)
        if not word.startswith("-"):
            positionals.append(word)
            continue
        assert word in options, f"{what}: {word} is not one of {sorted(options)}"
        param = options[word]
        if param.is_flag or param.count:
            continue
        assert rest, f"{what}: {word} takes a value, and nothing follows it"
        value = rest.pop(0)
        if not _is_placeholder(value):
            param.type.convert(value, param, None)  # the runner's own check of the value
    arguments = [param for param in params if param.param_type_name == "argument"]
    required = sum(1 for argument in arguments if argument.required)
    most = (
        math.inf
        if any(argument.nargs == -1 for argument in arguments)
        else sum(argument.nargs for argument in arguments)
    )
    assert required <= len(positionals) <= most, (
        f"{what}: positionals {positionals} for arguments {[a.name for a in arguments]}"
    )


def test_a_boolean_flag_takes_no_value_so_the_word_after_it_is_a_positional() -> None:
    probe = typer.Typer()

    @probe.command()
    def prompt(
        text: str,
        now: bool = typer.Option(False, "--now"),
        run_id: str = typer.Option("", "--run-id"),
    ) -> None:
        """A verb shaped like the runners' own `prompt`."""

    @probe.command()
    def stop() -> None:
        """A second verb, so the app is a group, as every runner's is."""

    command = typer.main.get_command(probe).commands["prompt"]  # type: ignore[attr-defined]

    _read_as_click_would(command, ["--now", "{text}", "--run-id", "{run_id}"], "probe")
    with pytest.raises(AssertionError, match="positionals"):
        _read_as_click_would(command, ["--now", "--run-id", "{run_id}"], "probe")
    with pytest.raises(AssertionError, match="--later"):
        _read_as_click_would(command, ["{text}", "--later"], "probe")


def _evidence_problems(affordances: EngineAffordances) -> list[str]:
    """The fields whose evidence breaks the rule: a set value needs evidence that is not the
    `unknown: ` form; an unknown value needs none, or evidence in that form."""
    problems: list[str] = []
    for name in AFFORDANCE_FIELDS:
        reason = affordances.evidence.get(name)
        if getattr(affordances, name) is None:
            ok = reason is None or reason.startswith("unknown: ")
        else:
            ok = bool(reason and reason.strip()) and not reason.startswith("unknown: ")
        if not ok:
            problems.append(name)
    return problems


def test_the_unknown_prefix_is_reserved_for_an_unknown_value() -> None:
    """`unknown: ` evidence beside a value that is set contradicts it: a claim cannot cite its
    own absence. Only a `None` field may carry it, and a set field must still carry evidence."""
    claimed = EngineAffordances(mcp=True, evidence={"mcp": "unknown: no code"})
    withdrawn = EngineAffordances(mcp=None, evidence={"mcp": "unknown: no code"})
    unexplained = EngineAffordances(mcp=None, evidence={"mcp": "no code"})
    bare = EngineAffordances(mcp=True)

    assert _evidence_problems(claimed) == ["mcp"]
    assert _evidence_problems(withdrawn) == []
    assert _evidence_problems(unexplained) == ["mcp"]
    assert _evidence_problems(bare) == ["mcp"]


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_every_capability_that_is_set_names_its_proof(descriptor) -> None:  # type: ignore[no-untyped-def]
    """A value that is set names where it is shown. An unknown value may say why it is unknown
    -- a withdrawn claim keeps the reason it was withdrawn -- and then says so first."""
    affordances = descriptor.affordances
    assert _evidence_problems(affordances) == [], descriptor.engine_id
    assert set(affordances.evidence) <= set(AFFORDANCE_FIELDS)


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_each_capability_claimed_agrees_with_the_facts_that_prove_it(descriptor) -> None:  # type: ignore[no-untyped-def]
    """The coarse capabilities and the facts `vibey loops` shows cannot disagree: a mid-run
    prompt exactly where a prompt control is declared, attachments only where the engine is
    proven to take an image, and web search only where its `run` takes `--web-search`."""
    claims = descriptor.capabilities
    engine = descriptor.engine_id.value

    assert (Capability.MID_RUN_PROMPT in claims) == (descriptor.controls.prompt is not None), engine
    if Capability.ATTACHMENTS in claims:
        affordances = descriptor.affordances
        assert affordances.images is True or affordances.paste_images is True, engine
    if Capability.WEB_SEARCH in claims:
        run = _runner_commands(descriptor.engine_id)["run"]
        assert "--web-search" in {opt for p in run.params for opt in p.opts}, engine  # type: ignore[attr-defined]


def test_no_runner_claims_what_its_own_code_does_not_back() -> None:
    """The claims the #1131 review found unbacked, withdrawn: qwenloop's `attach` and
    `web-search` only echo. codexloop and qwenloop act on a prompt (qwenloop since #1133),
    and say so."""
    assert not {Capability.ATTACHMENTS, Capability.WEB_SEARCH} & QWENLOOP.capabilities
    acting = CODEXLOOP.capabilities & QWENLOOP.capabilities
    assert Capability.MID_RUN_PROMPT in acting


def test_the_capabilities_each_runner_shows() -> None:
    shown = {
        d.engine_id.value: tuple(getattr(d.affordances, name) for name in AFFORDANCE_FIELDS)
        for d in ALL_DESCRIPTORS
    }
    claude = (None, True, True, None, PluginSystem.CLAUDE_PLUGINS, True, True)
    context = PluginSystem.SKILLS_CONTEXT
    bundle = PluginSystem.VIBEY_BUNDLE
    assert shown == {
        # Web search off until Phase 6 gives every loop `vibey_search` (SP-LOOPS Phase 4, R4).
        "claudeloop": (*claude, False),
        # No MCP code in codexloop: unknown, not yes (SP-LOOPS Task 1).
        "codexloop": (None, True, True, None, context, None, None, None),
        # The local runner takes the snapshot as the vibey bundle (SP-LOOPS Phase 5, Task 9).
        "gptossloop": (False, True, True, False, bundle, True, True, True),
        "qwenloop": (False, True, True, False, bundle, True, True, True),
        # The same binary, but a local backend cannot serve web search.
        "claudeloop-local": (*claude, False),
    }


def test_the_gaps_between_each_lane_and_full_access_are_pinned() -> None:
    """Every lane is meant to have all skills, Claude's plugins, every MCP server and web
    search with the research tools (#1666). What each engine is not shown to have is pinned,
    so a gap can only close because a runner's code was read and can never widen unseen. Each
    entry here is a capability gap to close in the runner, not a fact to accept."""
    gaps = {d.engine_id.value: d.affordances.full_access_gaps() for d in ALL_DESCRIPTORS}
    assert gaps == {
        "claudeloop": ("web_search",),
        "codexloop": ("skills", "plugins", "mcp", "web_search"),
        "gptossloop": (),
        "qwenloop": (),
        "claudeloop-local": ("web_search",),
    }


@pytest.mark.parametrize(
    "paid",
    [d for d in ALL_DESCRIPTORS if d.tier is EngineTier.PAID],
    ids=lambda d: d.engine_id.value,
)
def test_the_sovereign_default_has_every_capability_a_paid_loop_has(paid) -> None:  # type: ignore[no-untyped-def]
    """The acceptance in data (SP-LOOPS Phase 5): whatever full access a paid loop is shown to
    have, the sovereign default is shown to have too -- its gaps are a subset of every paid
    loop's."""
    sovereign = set(GPTOSSLOOP.affordances.full_access_gaps())
    assert sovereign <= set(paid.affordances.full_access_gaps()), paid.engine_id.value


LOCAL_RUNNER_SNAPSHOT_CITES = {
    "plugins": ("--capabilities", "skills_list", "skill_read", "SkillShelf", "skills_context"),
    "skills": (
        "--capabilities",
        "skills_list",
        "skill_read",
        "SkillShelf",
        "capability_prompt_tokens",
        "capability_answer_tokens",
    ),
    "mcp": (
        "--capabilities",
        "mcp_list",
        "mcp_call",
        "McpSessionPool",
        "StdioTransport",
        "scrubbed launcher",
        "HttpTransport",
        "capability_answer_tokens",
    ),
}


@pytest.mark.parametrize("affordance", ["plugins", "skills", "mcp"])
def test_local_runner_snapshot_evidence_says_the_real_run_probe_is_pending(
    affordance: str,
) -> None:
    """SP-LOOPS Phase 5: no real `gptossloop` or MCP server has run a snapshot yet, so what it
    gives a local run is unit-proven only, and each claim ends saying so. Each also names the
    code it rests on. Remove the phrase when the operator records the probe."""
    for descriptor in (GPTOSSLOOP, QWENLOOP):
        evidence = descriptor.affordances.evidence[affordance]
        assert evidence.endswith("unit-proven; real-run probe pending"), (
            descriptor.engine_id,
            evidence,
        )
        for cite in LOCAL_RUNNER_SNAPSHOT_CITES[affordance]:
            assert cite in evidence, (descriptor.engine_id, affordance, cite)


def test_claudeloop_claims_no_web_search_while_builtin_web_is_off_by_default() -> None:
    """`[loops] builtin_web` is off unless a person sets it, and then claudeloop disallows
    Claude Code's own web tools (SP-LOOPS Phase 4, R4). A claim of web search would be a claim
    the default run does not have; `claudeloop-local` never has them, whatever the key (R11)."""
    from vibey_runners.common.capabilities.bundle import BundleSpec

    from vibey.infrastructure.engines.descriptors import CLAUDELOOP_LOCAL

    assert BundleSpec.default().builtin_web is False
    assert BundleSpec.from_mapping({}).builtin_web is False
    for descriptor in (CLAUDELOOP, CLAUDELOOP_LOCAL):
        evidence = descriptor.affordances.evidence["web_search"]
        assert descriptor.affordances.web_search is False, descriptor.engine_id
        assert "builtin_web" in evidence and "CLAUDE_BUILTIN_WEB_TOOLS" in evidence, evidence
    assert "R11" in CLAUDELOOP_LOCAL.affordances.evidence["web_search"]
    assert "--web-search" not in CLAUDELOOP.launch_flags


@pytest.mark.parametrize("affordance", ["files", "plugins", "mcp", "skills"])
def test_claudeloops_snapshot_evidence_says_the_real_run_probe_is_pending(
    affordance: str,
) -> None:
    """The plan's Verification step 5 (SP-LOOPS Phase 4): until the operator's real-run probe
    has run against a real `claude`, what the snapshot gives a run is unit-proven only, and
    the evidence says so. Remove the phrase when the probe's outcome is recorded."""
    from vibey.infrastructure.engines.descriptors import CLAUDELOOP_LOCAL

    for descriptor in (CLAUDELOOP, CLAUDELOOP_LOCAL):
        evidence = descriptor.affordances.evidence[affordance]
        assert "unit-proven; real-run probe pending" in evidence, (descriptor.engine_id, evidence)


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_every_launch_flag_is_one_the_runners_run_defines(descriptor) -> None:  # type: ignore[no-untyped-def]
    run = _runner_commands(descriptor.engine_id)["run"]
    defined = {opt for p in run.params for opt in p.opts}  # type: ignore[attr-defined]
    assert set(descriptor.launch_flags) <= defined, descriptor.engine_id.value


def test_no_engine_is_launched_narrower_than_its_runner_allows() -> None:
    """Lanes are never restricted at launch: no flag vibey passes narrows the tools, MCP
    servers, plugins or settings a session loads."""
    narrowing = {
        "--allowed-tools",
        "--allowedTools",
        "--disallowed-tools",
        "--disallowedTools",
        "--strict-mcp-config",
        "--bare",
        "--disable-slash-commands",
        "--tools",
    }
    for descriptor in ALL_DESCRIPTORS:
        flags = {
            *descriptor.launch_flags,
            *(f for flags in descriptor.isolation_flags.values() for f in flags),
            *(t for inv in descriptor.effort_projection.values() for t in inv.argv),
        }
        assert not narrowing & flags, descriptor.engine_id.value


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
        _read_as_click_would(commands[verb], template[1:], f"{descriptor.engine_id} {verb}")


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
@pytest.mark.parametrize("effort", ALL_EFFORTS, ids=lambda e: e.name)
def test_the_run_template_and_every_effort_flag_are_ones_the_runner_takes(  # type: ignore[no-untyped-def]
    descriptor, effort
) -> None:
    """The `run` template `vibey loops` publishes, filled as its caller fills it, at every
    effort and every isolation level, is a command line the runner's own `run` accepts."""
    template = RUN_ARGV_TEMPLATE.template(descriptor)
    assert template[:2] == ("{binary}", "run")
    run = _runner_commands(descriptor.engine_id)["run"]
    for isolation in IsolationLevel:
        words: list[str] = []
        for word in template[2:]:
            if word == PLAN_FLAG:
                assert descriptor.plan_flag is not None
                words.append(descriptor.plan_flag)
            elif word == EFFORT_ARGV:
                words += descriptor.invoke(effort).argv
                words += descriptor.isolation_flags.get(isolation, ())
            else:
                words.append(word)
        _read_as_click_would(run, words, f"{descriptor.engine_id} run at {effort.name}")


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
    assert QWENLOOP.controls == EngineControls(
        stop=("stop", "{run_id}", "--cwd", "{cwd}"),
        wind_down=("wind-down", "{run_id}", "--cwd", "{cwd}"),
        prompt=("prompt", "{run_id}", "{text}", "--cwd", "{cwd}"),
    )
    assert BY_ENGINE_ID[EngineId.CLAUDELOOP_LOCAL].controls == CLAUDELOOP.controls


def test_gptossloop_is_the_qwenloop_runner_under_its_own_name_and_settings() -> None:
    """ADR-0064: gptossloop differs from qwenloop in its id, its binary, the runner version
    that first shipped it and the settings it reads -- never in how a run is laid out."""
    gptoss = BY_ENGINE_ID[EngineId.GPTOSSLOOP]
    assert (gptoss.binary, gptoss.min_version, gptoss.env_passthrough) == (
        "gptossloop",
        "0.3.0",
        ("GPTOSSLOOP_*",),
    )
    assert (gptoss.state_dir, gptoss.done_marker, gptoss.controls, gptoss.events) == (
        QWENLOOP.state_dir,
        QWENLOOP.done_marker,
        QWENLOOP.controls,
        QWENLOOP.events,
    )
    assert gptoss.tier is QWENLOOP.tier is EngineTier.LOCAL


def test_every_runner_writes_its_events_in_its_own_run_directory() -> None:
    path = "{cwd}/{state_dir}/runs/{run_id}/events.jsonl"
    envelopes = {d.engine_id.value: d.events for d in ALL_DESCRIPTORS}
    assert envelopes == {
        "claudeloop": EventLog(path, EventEnvelope.EVENT_TYPE_PAYLOAD),
        "codexloop": EventLog(path, EventEnvelope.TYPE),
        "gptossloop": EventLog(path, EventEnvelope.TYPE),
        "qwenloop": EventLog(path, EventEnvelope.TYPE),
        "claudeloop-local": EventLog(path, EventEnvelope.EVENT_TYPE_PAYLOAD),
    }
