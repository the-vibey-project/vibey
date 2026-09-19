# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Feasibility over the six-materials state vector (#134): unknown is a value, the whole
path is judged, and agency shortfalls are reported first."""

from __future__ import annotations

import math

import pytest

from vibey_gh.config import EstimateConfig, GhConfig, load_config
from vibey_gh.feasibility import (
    DEFAULT_STAGES,
    MATERIALS,
    MEASURED_BY,
    NO,
    PROPERTIES,
    STAGE_NAMES,
    UNKNOWN,
    YES,
    Coordinate,
    FeasibilityEvaluator,
    Gap,
    Pipeline,
    Requirement,
    Stage,
    StateVector,
)
from vibey_gh.interfaces.feasibility_evaluator_interface import FeasibilityEvaluatorInterface
from vibey_gh.interfaces.pipeline_interface import PipelineInterface


def _measured(material: str, prop: str, value: float) -> Coordinate:
    return Coordinate(material, prop, value, source=f"test: {material}.{prop}", measured_at=1.0)


def _state(**values: float) -> StateVector:
    """A state with `material_prop=value` measured and everything else unknown."""
    return StateVector.unknown().with_measurements(
        _measured(*name.split("_"), value) for name, value in values.items()
    )


# -- coordinates -------------------------------------------------------------------------


def test_the_state_has_eighteen_coordinates_in_the_papers_order():
    assert MATERIALS == ("network", "hardware", "software", "agent", "information", "agency")
    assert PROPERTIES == ("availability", "stability", "reliability")
    assert set(MEASURED_BY) == {(m, p) for m in MATERIALS for p in PROPERTIES}
    state = StateVector.unknown(measured_at=5.0)
    assert [c.name for c in state.coordinates][:4] == [
        "network.availability",
        "network.stability",
        "network.reliability",
        "hardware.availability",
    ]
    assert len(state.coordinates) == 18 and state.measured == 0 and state.confidence == 0.0
    assert all(c.value is None and c.measured_at == 5.0 for c in state.coordinates)


def test_an_unknown_coordinate_says_what_would_measure_it():
    agency = StateVector.unknown().get("agency", "availability")
    assert not agency.known and agency.distance is None
    # Paid credit is agency: permission to act by spending (a defaulted decision).
    assert "paid credit" in agency.source and agency.source.startswith("unmeasured")


@pytest.mark.parametrize(
    "material, prop, value, message",
    [
        ("money", "availability", None, "not a material"),
        ("agency", "freshness", None, "not a property"),
        ("agency", "availability", 1.5, "from 0 to 1"),
        ("agency", "availability", -0.1, "from 0 to 1"),
        ("agency", "availability", math.nan, "from 0 to 1"),
        ("agency", "availability", math.inf, "from 0 to 1"),
    ],
)
def test_a_coordinate_outside_the_space_is_refused(material, prop, value, message):
    with pytest.raises(ValueError, match=message):
        Coordinate(material, prop, value, source="x")


def test_a_measured_coordinate_knows_its_distance_from_peak():
    coordinate = _measured("hardware", "availability", 0.62)
    assert coordinate.known and coordinate.name == "hardware.availability"
    assert coordinate.distance == 0.38


def test_a_state_vector_holds_each_coordinate_exactly_once():
    full = StateVector.unknown().coordinates
    with pytest.raises(ValueError, match="exactly once"):
        StateVector(full[:-1])
    with pytest.raises(ValueError, match="exactly once"):
        StateVector((*full[:-1], full[0]))


def test_a_state_vector_is_kept_in_canonical_order_whatever_order_it_is_built_in():
    shuffled = tuple(reversed(StateVector.unknown().coordinates))
    assert StateVector(shuffled) == StateVector.unknown()


def test_measurements_replace_their_unknowns_and_raise_confidence():
    state = _state(hardware_availability=1.0, software_availability=0.5)
    assert state.measured == 2 and state.confidence == round(2 / 18, 4)
    assert state.get("software", "availability").value == 0.5
    with pytest.raises(KeyError):
        state.get("money", "availability")


# -- requirements, stages, the pipeline --------------------------------------------------


def test_a_requirement_names_a_real_coordinate_with_a_minimum_on_the_scale():
    assert Requirement.parse("agency.availability").minimum == 1.0
    assert Requirement.parse("agency.stability", 0.5).name == "agency.stability"
    with pytest.raises(ValueError, match="not a material"):
        Requirement.parse("money.availability")
    with pytest.raises(ValueError, match="from 0 to 1"):
        Requirement("agency", "availability", 2.0)


def test_the_default_pipeline_is_the_nine_stages_install_through_main_validation():
    assert STAGE_NAMES == (
        "install",
        "interview",
        "feature-branch",
        "develop",
        "develop-deployment",
        "develop-validation",
        "main",
        "main-deployment",
        "main-validation",
    )
    # Only availability is gated by default: without φ a stability or reliability
    # shortfall dilates time rather than making the work impossible.
    for stage in DEFAULT_STAGES:
        assert stage.summary and stage.requirements
        assert {r.prop for r in stage.requirements} == {"availability"}
    # Merging to main is an agency question before it is anything else.
    main = next(s for s in DEFAULT_STAGES if s.name == "main")
    assert "agency" in {r.material for r in main.requirements}


def test_a_stage_needing_materials_needs_their_availability_in_full():
    stage = Stage.needing("ship", "why", "network", "agency")
    assert stage.requirements == (
        Requirement("network", "availability", 1.0),
        Requirement("agency", "availability", 1.0),
    )


def test_the_pipeline_cuts_the_path_a_run_must_pass():
    pipeline = Pipeline()
    assert isinstance(pipeline, PipelineInterface)
    assert pipeline.names == STAGE_NAMES
    assert [s.name for s in pipeline.path("develop")] == list(STAGE_NAMES[:4])
    assert [s.name for s in pipeline.path("main", "develop-validation")] == [
        "develop-validation",
        "main",
    ]
    assert [s.name for s in pipeline.path("main", "main")] == ["main"]


@pytest.mark.parametrize(
    "operation, start, message",
    [
        ("promote", None, "'promote' is not a stage"),
        ("main", "nowhere", "'nowhere' is not a stage"),
        ("develop", "main", "comes after"),
    ],
)
def test_a_path_that_is_not_one_is_refused_by_name(operation, start, message):
    with pytest.raises(ValueError, match=message):
        Pipeline().path(operation, start)


@pytest.mark.parametrize(
    "stages, message",
    [
        ((), "at least one stage"),
        ((Stage(" "),), "at least one stage"),
        ((Stage("a"), Stage("a")), "unique"),
    ],
)
def test_a_pipeline_needs_named_unique_stages(stages, message):
    with pytest.raises(ValueError, match=message):
        Pipeline(stages)


def test_the_configured_pipeline_is_the_default_when_nothing_is_configured():
    assert Pipeline.from_config(EstimateConfig()).names == STAGE_NAMES


def test_a_configured_stage_vector_replaces_the_default_outright():
    config = EstimateConfig(
        requirements=(("main", (("agency.availability", 0.5), ("network.stability", 0.25))),)
    )
    main = Pipeline.from_config(config).path("main", "main")[0]
    assert main.requirements == (
        Requirement("agency", "availability", 0.5),
        Requirement("network", "stability", 0.25),
    )
    assert "[estimate.requirements.main]" in main.summary


def test_a_configured_pipeline_may_reorder_and_add_stages():
    config = EstimateConfig(
        stages=("develop", "canary", "main"),
        requirements=(("canary", (("hardware.availability", 1.0),)),),
    )
    pipeline = Pipeline.from_config(config)
    assert pipeline.names == ("develop", "canary", "main")


@pytest.mark.parametrize(
    "config, message",
    [
        (EstimateConfig(stages=("develop", "canary")), "'canary' has no requirement vector"),
        (
            EstimateConfig(stages=("develop",), requirements=(("main", ()),)),
            "never reaches: \\['main'\\]",
        ),
        (
            EstimateConfig(requirements=(("main", (("money.availability", 1.0),)),)),
            "not a material",
        ),
    ],
)
def test_a_configured_pipeline_that_cannot_be_judged_is_refused_loudly(config, message):
    with pytest.raises(ValueError, match=message):
        Pipeline.from_config(config)


# -- the configuration that carries it ---------------------------------------------------


def test_the_estimate_section_loads_from_the_configuration_file(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        "[estimate]\n"
        "offline = false\n"
        'model = "qwen3:14b"\n'
        'stages = ["develop", "main"]\n'
        'report_first = ["agency", "network"]\n'
        "[estimate.requirements.main]\n"
        '"agency.availability" = 1\n'
        '"network.availability" = 0.5\n'
    )
    estimate = load_config(tmp_path).estimate
    assert estimate == EstimateConfig(
        offline=False,
        model="qwen3:14b",
        stages=("develop", "main"),
        requirements=(("main", (("agency.availability", 1), ("network.availability", 0.5))),),
        report_first=("agency", "network"),
    )
    assert GhConfig(root=tmp_path).estimate == EstimateConfig()


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"stages": ("a", "a")}, "estimate.stages entries must be unique"),
        ({"report_first": ("",)}, "estimate.report_first entries must be non-empty"),
        ({"requirements": (("a", ()), ("a", ()))}, "estimate.requirements entries must be unique"),
        ({"requirements": (("a", (("agency", 1.0),)),)}, "is not 'material.property'"),
        ({"requirements": (("a", ((".availability", 1.0),)),)}, "is not 'material.property'"),
        ({"requirements": (("a", (("agency.", 1.0),)),)}, "is not 'material.property'"),
        ({"requirements": (("a", (("a.b.c", 1.0),)),)}, "is not 'material.property'"),
        ({"requirements": (("a", (("agency.availability", 1.5),)),)}, "from 0 to 1"),
        ({"requirements": (("a", (("agency.availability", True),)),)}, "from 0 to 1"),
        ({"requirements": (("a", (("agency.availability", "1"),)),)}, "from 0 to 1"),
    ],
)
def test_the_estimate_section_refuses_a_malformed_table(kwargs, message):
    with pytest.raises(ValueError, match=message):
        EstimateConfig(**kwargs)


@pytest.mark.parametrize("requirements", ['"main"', "{ main = 1 }"])
def test_requirements_must_be_a_table_of_stage_tables(tmp_path, requirements):
    (tmp_path / ".vibey-gh.toml").write_text(f"[estimate]\nrequirements = {requirements}\n")
    with pytest.raises(ValueError, match="table of stage tables"):
        load_config(tmp_path)


# -- the verdict -------------------------------------------------------------------------


def test_the_evaluator_declares_its_seam():
    assert isinstance(FeasibilityEvaluator(), FeasibilityEvaluatorInterface)


def test_yes_only_when_every_required_coordinate_is_measured_and_meets_its_minimum():
    stages = (Stage.needing("build", "", "hardware", "software"),)
    verdict = FeasibilityEvaluator().evaluate(
        _state(hardware_availability=1.0, software_availability=1.0), stages
    )
    assert verdict.verdict == YES and verdict.blocked_at is None
    assert not verdict.shortfalls and not verdict.unknowns
    assert verdict.confidence == 1.0 and verdict.stages[0].verdict == YES


def test_an_unmeasured_coordinate_withholds_yes_but_never_invents_no():
    stages = (Stage.needing("build", "", "hardware", "agency"),)
    verdict = FeasibilityEvaluator().evaluate(_state(hardware_availability=1.0), stages)
    assert verdict.verdict == UNKNOWN and verdict.blocked_at is None
    assert [g.name for g in verdict.unknowns] == ["agency.availability"]
    assert verdict.unknowns[0].verdict == UNKNOWN
    assert (verdict.required, verdict.required_measured, verdict.confidence) == (2, 1, 0.5)


def test_one_measured_shortfall_anywhere_on_the_path_makes_it_no():
    """Kleene's AND: an unknown early stage cannot rescue a known failure later -- the run
    cannot complete, whatever the early stage turns out to be."""
    stages = (
        Stage.needing("early", "", "agent"),
        Stage.needing("late", "", "hardware"),
    )
    verdict = FeasibilityEvaluator().evaluate(_state(hardware_availability=0.4), stages)
    assert verdict.verdict == NO and verdict.blocked_at == "late"
    assert [v.verdict for v in verdict.stages] == [UNKNOWN, NO]
    (gap,) = verdict.shortfalls
    assert gap == Gap("late", "hardware", "availability", 1.0, 0.4, "test: hardware.availability")
    assert gap.describe() == (
        "hardware.availability 0.4 < 1 at 'late' (test: hardware.availability)"
    )


def test_the_first_failing_stage_is_where_the_run_is_blocked():
    stages = (
        Stage.needing("one", "", "network"),
        Stage.needing("two", "", "hardware"),
    )
    verdict = FeasibilityEvaluator().evaluate(
        _state(network_availability=0.0, hardware_availability=0.0), stages
    )
    assert verdict.blocked_at == "one"


def test_agency_shortfalls_are_reported_first_however_late_they_bite():
    stages = (
        Stage.needing("install", "", "hardware"),
        Stage.needing("main", "", "network", "agency"),
    )
    verdict = FeasibilityEvaluator().evaluate(
        _state(hardware_availability=0.5, network_availability=0.5, agency_availability=0.0),
        stages,
    )
    assert verdict.blocked_at == "install"
    assert [(g.stage, g.name) for g in verdict.shortfalls] == [
        ("main", "agency.availability"),
        ("install", "hardware.availability"),
        ("main", "network.availability"),
    ]


def test_unknowns_follow_the_same_priority_order():
    verdict = FeasibilityEvaluator().evaluate(StateVector.unknown(), Pipeline().path("develop"))
    assert verdict.unknowns[0].name == "agency.availability"
    assert verdict.unknowns[0].stage == "install"


def test_which_materials_lead_the_report_is_configurable():
    stages = (Stage.needing("s", "", "network", "agency"),)
    state = _state(network_availability=0.0, agency_availability=0.0)
    ranked = FeasibilityEvaluator(report_first=("network",)).evaluate(state, stages).shortfalls
    assert [g.material for g in ranked] == ["network", "agency"]
    ranked = FeasibilityEvaluator(report_first=()).evaluate(state, stages).shortfalls
    assert [g.material for g in ranked] == ["network", "agency"]
    with pytest.raises(ValueError, match="no such material"):
        FeasibilityEvaluator(report_first=("money",))


def test_confidence_counts_coordinates_not_requirement_instances():
    """Agency needed at five stages is one thing to measure, not five."""
    verdict = FeasibilityEvaluator().evaluate(
        _state(hardware_availability=1.0, software_availability=1.0), Pipeline().path("develop")
    )
    assert verdict.required == 6 and verdict.required_measured == 2
    assert verdict.confidence == round(2 / 6, 4)


def test_a_path_that_requires_nothing_is_feasible_and_fully_confident():
    verdict = FeasibilityEvaluator().evaluate(StateVector.unknown(), (Stage("noop"),))
    assert verdict.verdict == YES and verdict.confidence == 1.0 and verdict.required == 0
