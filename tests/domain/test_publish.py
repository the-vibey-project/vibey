# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Publishing a finished project: its settings, the proposal, and what an answer can change."""

from pathlib import Path

import pytest

from vibey.domain.config import ConfigError, PublishConfig, load_config_from_string
from vibey.domain.publish import (
    BODY_LIMIT,
    CHOICES,
    DESCRIPTION_LIMIT,
    TITLE_LIMIT,
    PublishAnswerError,
    PublishKind,
    PublishPlan,
    PublishTarget,
    decide,
    default_plan,
    slug,
)

REPO = Path("/work/project")


def _target(*, remote: str | None = "git@github.com:me/x.git", default: str | None = "develop"):
    return PublishTarget(
        branch="vibey/abc/1/integration",
        remote="origin",
        remote_url=remote,
        default_branch=default,
        repo_path=str(REPO),
    )


def _plan(*, remote: str | None = "git@github.com:me/x.git", **settings: object) -> PublishPlan:
    return default_plan(
        project_name="Ministry Section 2",
        objective="Fold Humbleberger Ministries into the site.\nWith a Hebrew twin.",
        criteria=("C1", "C2"),
        cycle=1,
        target=_target(remote=remote),
        config=PublishConfig(**settings),  # type: ignore[arg-type]
    )


# -- settings ----------------------------------------------------------------------------


def test_nothing_is_published_unless_the_project_says_so_and_the_safe_choices_are_the_defaults() -> (
    None
):
    config = PublishConfig.from_data({})

    assert (config.mode, config.visibility, config.draft) == ("off", "private", True)
    assert (config.base, config.remote, config.owner) == (None, "origin", None)


def test_every_setting_is_read_from_the_table() -> None:
    config = PublishConfig.from_data(
        {
            "publish": {
                "mode": "interview",
                "visibility": "public",
                "draft": False,
                "base": "develop",
                "remote": "upstream",
                "owner": "the-vibey-project",
            }
        }
    )

    assert config == PublishConfig(
        "interview", "public", False, "develop", "upstream", "the-vibey-project"
    )


def test_the_table_is_also_read_from_a_whole_toml_document() -> None:
    config = load_config_from_string('[project]\nname = "x"\n[publish]\nmode = "auto"\n')

    assert config.publish.mode == "auto"


@pytest.mark.parametrize(
    ("table", "setting"),
    [
        ("yes", "publish"),
        ({"mode": "sometimes"}, "publish.mode"),
        ({"visibility": "internal"}, "publish.visibility"),
        ({"draft": "yes"}, "publish.draft"),
        ({"base": "-d"}, "publish.base"),
        ({"base": "a b"}, "publish.base"),
        ({"base": 3}, "publish.base"),
        ({"remote": "--upload-pack=x"}, "publish.remote"),
        ({"owner": "o;rm"}, "publish.owner"),
        ({"visibilty": "public"}, "publish.visibilty"),
    ],
)
def test_a_setting_that_is_wrong_or_misspelled_is_refused_naming_it(
    table: object, setting: str
) -> None:
    with pytest.raises(ConfigError) as caught:
        PublishConfig.from_data({"publish": table})

    assert setting in str(caught.value)


# -- the proposal ------------------------------------------------------------------------


def test_a_checkout_with_a_remote_proposes_a_draft_pull_request_into_its_default_branch() -> None:
    plan = _plan()

    assert plan.kind is PublishKind.PULL_REQUEST
    assert (plan.branch, plan.remote, plan.base, plan.draft) == (
        "vibey/abc/1/integration",
        "origin",
        "develop",
        True,
    )
    assert plan.title == "feat: Fold Humbleberger Ministries into the site. With a Hebrew twin."
    assert "## Acceptance criteria\n\nC1, C2" in plan.body
    assert "project `Ministry Section 2`, cycle 1" in plan.body


def test_a_checkout_with_no_remote_proposes_a_new_private_repository() -> None:
    plan = _plan(remote=None)

    assert plan.kind is PublishKind.NEW_REPOSITORY
    assert (plan.repo_name, plan.visibility, plan.owner) == ("ministry-section-2", "private", None)
    assert plan.base == "develop"


def test_the_settings_beat_the_checkout_and_the_fallbacks_hold_when_nothing_is_known() -> None:
    chosen = _plan(base="main", draft=False, visibility="public", owner="org")
    blind = default_plan(
        project_name="p",
        objective="",
        criteria=(),
        cycle=2,
        target=_target(default=None),
        config=PublishConfig(),
    )

    assert (chosen.base, chosen.draft, chosen.visibility, chosen.owner) == (
        "main",
        False,
        "public",
        "org",
    )
    assert blind.base == "main"
    assert blind.title == "feat: p" and "none recorded" in blind.body


def test_a_long_objective_is_cut_to_a_title_and_a_description_that_fit() -> None:
    plan = default_plan(
        project_name="p",
        objective="word " * 400,
        criteria=(),
        cycle=1,
        target=_target(),
        config=PublishConfig(),
    )

    assert len(plan.title) <= TITLE_LIMIT and plan.title.endswith("\u2026")
    assert len(plan.description) <= DESCRIPTION_LIMIT


def test_the_summary_says_exactly_what_will_happen_in_each_case() -> None:
    pr = _plan().summary()
    ready = _plan(draft=False).summary()
    new = _plan(remote=None, owner="org").summary()
    anonymous = _plan(remote=None).summary()

    assert "open a draft pull request into develop" in pr and "Title: feat:" in pr
    assert "open a pull request ready for review" in ready
    assert "Create the private GitHub repository org/ministry-section-2" in new
    assert "and push branch vibey/abc/1/integration to it as develop" in new
    assert "repository ministry-section-2 " in anonymous


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Ministry Section 2", "ministry-section-2"), ("  --A/b!! ", "a-b"), ("???", "project")],
)
def test_a_project_name_becomes_a_repository_name(name: str, expected: str) -> None:
    assert slug(name) == expected


# -- answers -----------------------------------------------------------------------------


def test_accepting_the_defaults_publishes_the_proposal_and_so_does_no_choice_at_all() -> None:
    plan = _plan()

    assert decide(plan, {"choice": "accept_defaults"}).plan == plan
    assert decide(plan, {}).plan == plan
    assert decide(plan, None).plan == plan
    assert not decide(plan, None).skipped


def test_skipping_publishes_nothing_and_says_why() -> None:
    decision = decide(_plan(), {"choice": "SKIP"})

    assert decision.skipped and decision.plan is None
    assert decision.reason == "the operator chose not to publish"


def test_a_custom_answer_changes_only_the_fields_it_names() -> None:
    plan = _plan(remote=None)

    decision = decide(
        plan,
        {
            "choice": "custom",
            "title": "  A better title ",
            "body": "Words.",
            "description": "Short.",
            "base": "main",
            "owner": "org",
            "repo": "my.repo_1",
            "draft": False,
            "visibility": "public",
        },
    )

    assert decision.plan is not None
    assert (decision.plan.title, decision.plan.body, decision.plan.description) == (
        "A better title",
        "Words.",
        "Short.",
    )
    assert (decision.plan.base, decision.plan.owner, decision.plan.repo_name) == (
        "main",
        "org",
        "my.repo_1",
    )
    assert (decision.plan.draft, decision.plan.visibility) == (False, "public")
    assert decision.plan.branch == plan.branch and decision.plan.kind is plan.kind


def test_a_custom_answer_naming_nothing_changes_nothing() -> None:
    plan = _plan()

    assert decide(plan, {"choice": "custom"}).plan == plan


@pytest.mark.parametrize(
    ("answer", "complaint"),
    [
        ({"choice": "maybe"}, "choice must be one of"),
        ({"choice": "custom", "colour": "red"}, "'colour' is not a field"),
        ({"choice": "custom", "title": ""}, "title must be some text"),
        ({"choice": "custom", "title": 3}, "title must be some text"),
        ({"choice": "custom", "title": "x" * (TITLE_LIMIT + 1)}, "title is"),
        ({"choice": "custom", "title": "a\nb"}, "title must be one line"),
        ({"choice": "custom", "body": "x" * (BODY_LIMIT + 1)}, "body is"),
        ({"choice": "custom", "base": "--force"}, "base must be a plain name"),
        ({"choice": "custom", "owner": "a b"}, "owner must be a plain name"),
        ({"choice": "custom", "repo": ".."}, "repo must be a plain repository name"),
        ({"choice": "custom", "repo": "a/b"}, "repo must be a plain repository name"),
        ({"choice": "custom", "repo": 4}, "repo must be a plain repository name"),
        ({"choice": "custom", "draft": "no"}, "draft must be true or false"),
        ({"choice": "custom", "visibility": "internal"}, "visibility must be one of"),
    ],
)
def test_an_answer_that_cannot_be_used_is_refused_naming_what_to_fix(
    answer: dict[str, object], complaint: str
) -> None:
    with pytest.raises(PublishAnswerError, match=complaint):
        decide(_plan(), answer)


def test_the_gate_offers_exactly_these_choices() -> None:
    assert CHOICES == ("accept_defaults", "custom", "skip")


def test_an_empty_remote_from_an_earlier_attempt_is_pushed_to_and_the_summary_says_so() -> None:
    plan = default_plan(
        project_name="Demo",
        objective="Ship it",
        criteria=("C1",),
        cycle=1,
        target=PublishTarget(
            branch="vibey/abc/1/integration",
            remote="origin",
            remote_url="git@github.com:me/demo.git",
            default_branch=None,
            repo_path=str(REPO),
            remote_empty=True,
        ),
        config=PublishConfig(),
    )

    assert plan.kind is PublishKind.NEW_REPOSITORY
    assert plan.existing_remote == "git@github.com:me/demo.git" and plan.base == "main"
    assert plan.summary() == (
        "Push branch vibey/abc/1/integration to the empty repository at "
        "git@github.com:me/demo.git as main."
    )
