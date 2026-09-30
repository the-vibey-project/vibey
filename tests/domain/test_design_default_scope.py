# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The narrowest-scope default guard, measured against the #998 ledger.

Project 9692abab, issue #998 "docs(readme): add a table of contents to README.md": the
questions below are the model's own, verbatim from the ledger, with the defaults it
declared. Accepting them grew a pure README insertion into a generator script, tests and
a CI step.
"""

import pytest

from vibey.domain.config import ConfigError, DesignConfig, DesignInterviewConfig, parse_config
from vibey.domain.design_default_scope import (
    DEFAULT_SCOPE,
    DESIGN_DEFAULT_SCOPE,
    NARROWEST_DEFAULT,
    DefaultScope,
    DesignDefaultScopeGuard,
    ScopedDefault,
)
from vibey.domain.interfaces import (
    DesignConfigInterface,
    DesignDefaultScopeGuardInterface,
    DesignInterviewConfigInterface,
)

INTAKE_998 = "docs(readme): add a table of contents to README.md"

GUARD = DesignDefaultScopeGuard()

# (question, the model's default) -- rewritten under narrowest.
WIDENING_998 = [
    (
        "Should we add a comment in README.md indicating that the TOC is auto-generated?",
        "Yes",
    ),
    ("Should we add a unit test to verify the TOC is up-to-date", "Yes"),
    ("Should we commit the TOC generation script", "Yes"),
    (
        "Should the TOC generation script be included in the repository's CI configuration "
        "to enforce that the TOC stays current?",
        "Yes",
    ),
    (
        "Should the script be executed as part of the existing CI pipeline",
        "Existing CI pipeline",
    ),
]


@pytest.mark.parametrize(("question", "model_default"), WIDENING_998)
def test_each_widening_question_from_998_defaults_to_no(question: str, model_default: str) -> None:
    scoped = GUARD.scope(question, model_default, intake=INTAKE_998, policy=DefaultScope.NARROWEST)

    assert scoped.rewritten
    assert scoped.default == NARROWEST_DEFAULT
    assert scoped.model_default == model_default
    assert scoped.reason is not None
    assert repr(model_default) in scoped.reason


def test_the_reason_names_the_artefacts_beyond_the_intake() -> None:
    question, default = WIDENING_998[3]
    scoped = GUARD.scope(question, default, intake=INTAKE_998, policy=DefaultScope.NARROWEST)

    assert scoped.reason is not None
    assert "proposes ci, script, configuration, which the intake does not ask for" in (
        scoped.reason
    )
    found = GUARD.classify(question, intake=INTAKE_998)
    assert found.beyond_intake == ("ci", "script", "configuration")


# Counterexamples that must NOT be rewritten, each with why.
KEPT = [
    # A how-question about the thing asked for: no artefact beyond it, no extension verb.
    ("Should the anchor generation follow GitHub's algorithm exactly", "Yes"),
    # Borderline, decided KEEP: "include" is an extension verb, but a sub-heading is part
    # of the table of contents the intake asks for -- its granularity, not a new thing
    # beside it -- so the question names no artefact and its default stands.
    ("Do we need to include sub-headings", "Yes"),
    # Not yes/no: a choice has no single minimal answer to rewrite to.
    ("Which heading levels should the TOC include in its CI check?", "h2 and h3"),
    # Names an artefact but proposes nothing: passing the existing CI is not extra scope.
    ("Should the change pass the existing CI?", "Yes"),
]


@pytest.mark.parametrize(("question", "model_default"), KEPT)
def test_questions_that_propose_no_new_artefact_keep_the_models_default(
    question: str, model_default: str
) -> None:
    scoped = GUARD.scope(question, model_default, intake=INTAKE_998, policy=DefaultScope.NARROWEST)

    assert scoped == ScopedDefault(default=model_default)
    assert not scoped.rewritten


def test_an_artefact_the_intake_names_is_not_scope_beyond_it() -> None:
    intake = "Add a table of contents to README.md and a CI check that keeps it current"
    question = "Should we add a CI check that fails when the TOC is stale?"

    assert not GUARD.scope(question, "Yes", intake=intake, policy=DefaultScope.NARROWEST).rewritten
    found = GUARD.classify(question, intake=intake)
    assert found.artefacts == ("ci", "check")
    assert found.beyond_intake == ()
    assert not found.widening


def test_one_artefact_beyond_the_intake_is_enough_to_narrow() -> None:
    intake = "Add a table of contents to README.md and a CI check that keeps it current"
    question = "Should we also add a pre-commit hook for the TOC?"

    scoped = GUARD.scope(question, "Yes", intake=intake, policy=DefaultScope.NARROWEST)

    assert scoped.rewritten
    assert GUARD.classify(question, intake=intake).beyond_intake == ("hook",)


@pytest.mark.parametrize(
    "default", ["No", "no, keep it manual", "None", "Not needed", "Skip it", "Out of scope"]
)
def test_a_default_that_already_declines_is_left_alone(default: str) -> None:
    question = "Should we add a unit test to verify the TOC is up-to-date"

    assert GUARD.declines(default)
    assert GUARD.scope(
        question, default, intake=INTAKE_998, policy=DefaultScope.NARROWEST
    ) == ScopedDefault(default=default)


@pytest.mark.parametrize("default", ["Yes", "Existing CI pipeline", "Nonetheless yes", "Notably"])
def test_an_affirmative_or_restating_default_does_not_decline(default: str) -> None:
    assert not GUARD.declines(default)


def test_the_model_policy_records_the_models_default_unchanged() -> None:
    question, default = WIDENING_998[1]

    assert GUARD.scope(
        question, default, intake=INTAKE_998, policy=DefaultScope.MODEL
    ) == ScopedDefault(default=default)


def test_the_classification_is_evidence_not_just_a_verdict() -> None:
    found = GUARD.classify("Should we add a unit test to verify the TOC", intake=INTAKE_998)

    assert found.yes_no and found.extends
    assert found.artefacts == ("test",)
    assert found.widening
    assert not GUARD.classify("What should the TOC be called?", intake=INTAKE_998).yes_no


# -- the deliverable is never narrowed (#963) -------------------------------------------

#: Issue #963's intake, abridged verbatim from the ledger: the same README insertion, this
#: time supplying the generator script itself.
INTAKE_963 = (
    "GitHub issue #963: docs(readme): add a table of contents to README.md\n"
    "Generate the anchor list mechanically rather than by hand, with this script run from\n"
    "the repository root:\n```python\nimport re\nfrom pathlib import Path\n```\n"
    "Commit as `docs(readme): add a table of contents`. Do not push."
)

#: The two #963 questions whose declared "No" meant no deliverable, verbatim.
DELIVERABLE_963 = [
    "Should the lane commit the change to README.md?",
    "Should the lane generate the table of contents using the provided Python script or "
    "hardcode the list?",
]


@pytest.mark.parametrize("question", DELIVERABLE_963)
def test_the_963_deliverable_questions_are_never_narrowed(question: str) -> None:
    found = GUARD.classify(question, intake=INTAKE_963)

    assert found.delivers
    assert not found.widening
    assert GUARD.scope(
        question, "Yes", intake=INTAKE_963, policy=DefaultScope.NARROWEST
    ) == ScopedDefault(default="Yes")


def test_the_guard_never_rewrites_a_declining_default_to_yes() -> None:
    """#963's "No" was the model's own (no `model_default` in the ledger): the guard only
    ever narrows, so the prompt contract is what asks for the deliverable."""
    question = DELIVERABLE_963[0]
    assert GUARD.scope(question, "No", intake=INTAKE_963, policy=DefaultScope.NARROWEST) == (
        ScopedDefault(default="No")
    )


def test_committing_the_change_is_exempt_even_beside_an_artefact_beyond_the_intake() -> None:
    question = "Should the lane commit the change together with its updated test expectations?"
    found = GUARD.classify(question, intake=INTAKE_998)

    # Without the exemption this would narrow: "commit" extends and "test" is beyond 998.
    assert found.yes_no and found.extends and found.beyond_intake == ("test",)
    assert found.delivers and not found.widening


def test_the_provided_thing_must_be_named_in_the_intake() -> None:
    question = "Should the lane use the provided generator script?"
    named = "Generate the anchors with the generator in this issue."

    assert GUARD.classify(question, intake=named).delivers
    assert GUARD.classify(question, intake=named).beyond_intake == ("script",)
    assert not GUARD.scope(question, "Yes", intake=named, policy=DefaultScope.NARROWEST).rewritten
    # The same question against an intake that provides nothing still narrows.
    assert not GUARD.classify(question, intake=INTAKE_998).delivers
    assert GUARD.scope(question, "Yes", intake=INTAKE_998, policy=DefaultScope.NARROWEST).rewritten


@pytest.mark.parametrize(("question", "model_default"), WIDENING_998)
def test_no_998_widening_question_is_mistaken_for_the_deliverable(
    question: str, model_default: str
) -> None:
    # "Should we commit the TOC generation script" commits a new thing, not the change.
    assert not GUARD.classify(question, intake=INTAKE_998).delivers


def test_the_shared_guard_is_the_interface() -> None:
    assert isinstance(DESIGN_DEFAULT_SCOPE, DesignDefaultScopeGuardInterface)
    assert DEFAULT_SCOPE is DefaultScope.NARROWEST


# -- [design.interview] default_scope ---------------------------------------------------


def test_nothing_declared_means_narrowest() -> None:
    config = DesignConfig.from_data({})

    assert config.interview.default_scope is DefaultScope.NARROWEST
    assert isinstance(config, DesignConfigInterface)
    assert isinstance(config.interview, DesignInterviewConfigInterface)


def test_the_model_scope_is_declared_in_the_design_interview_table() -> None:
    config = parse_config(
        {"project": {"name": "p"}, "design": {"interview": {"default_scope": "model"}}}
    )

    assert config.design.interview.default_scope is DefaultScope.MODEL


def test_one_design_table_carries_both_the_interview_and_research_policies() -> None:
    config = DesignConfig.from_data(
        {
            "design": {
                "interview": {"default_scope": "model"},
                "research": {"on_unavailable": "record_gap"},
            }
        }
    )

    assert config.interview.default_scope is DefaultScope.MODEL
    assert config.research.on_unavailable.value == "record_gap"


def test_an_unknown_design_interview_key_is_refused() -> None:
    with pytest.raises(ConfigError) as caught:
        DesignConfig.from_data({"design": {"interview": {"default_scop": "model"}}})

    assert "design.interview.default_scop" in str(caught.value)


def test_an_unknown_scope_is_refused_naming_the_key_and_the_choices() -> None:
    with pytest.raises(ConfigError) as caught:
        DesignInterviewConfig.from_table({"default_scope": "widest"}, "design.interview")

    assert "design.interview.default_scope" in str(caught.value)
    assert "narrowest, model" in str(caught.value)


@pytest.mark.parametrize(
    ("data", "path"),
    [
        ({"design": "narrowest"}, "design"),
        ({"design": {"interview": []}}, "design.interview"),
        ({"design": {"interview": {"default_scope": 1}}}, "design.interview"),
    ],
)
def test_a_malformed_design_table_is_refused(data: dict[str, object], path: str) -> None:
    with pytest.raises(ConfigError) as caught:
        DesignConfig.from_data(data)

    assert path in str(caught.value)
