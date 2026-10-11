# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a BUILD job tells the engine about the work, besides its title."""

from vibey.application.build_brief import MAX_BRIEF_CHARS, render_work_item_brief
from vibey.domain.spec import AcceptanceCriterion, Constraint, ConstraintKind, DesignSpec

SPEC = DesignSpec(
    objective="Fold the ministry into the site as a /ministry section.",
    constraints=(
        Constraint("Reuse src/lib/collectionUtils.ts; do not rebuild it.", ConstraintKind.HARD),
        Constraint("Prefer small server components.", ConstraintKind.SOFT),
    ),
    non_goals=("Redirects from the old domain.",),
    criteria=(
        AcceptanceCriterion("C1", "a post", "the import runs", "a page exists", "a test passes"),
        AcceptanceCriterion("C2", "an article", "it builds", "it renders", "the page is 200"),
        AcceptanceCriterion("C3", "the donate page", "it renders", "the embed shows", "CSP ok"),
    ),
    nfrs=(),
    walking_skeleton="one post and one article, each with a Hebrew twin",
)

PAYLOAD = {
    "title": "Walking skeleton",
    "acceptance_ids": ["C1", "C2"],
    "files_touched_hint": ["src/app/ministry/page.tsx", "src/app/ministry/[slug]/page.tsx"],
    "depends_on_items": [],
}


def test_the_brief_says_what_is_being_built_and_the_rules_that_bind_it() -> None:
    brief = render_work_item_brief(SPEC, PAYLOAD)

    assert brief.startswith("# Your task\n")
    assert "Fold the ministry into the site as a /ministry section." in brief
    assert "one post and one article, each with a Hebrew twin" in brief
    assert "- [must] Reuse src/lib/collectionUtils.ts; do not rebuild it." in brief
    assert "- [prefer] Prefer small server components." in brief
    assert "Redirects from the old domain." in brief


def test_the_brief_gives_this_items_criteria_in_full_and_no_one_elses() -> None:
    brief = render_work_item_brief(SPEC, PAYLOAD)

    assert (
        "- C1: given a post, when the import runs, then a page exists. Measured by: a test passes"
        in brief
    )
    assert "- C2: given an article" in brief
    assert "C3" not in brief  # another item's: it would only be a second thing to build


def test_the_brief_names_the_files_to_write_and_says_not_to_search_for_them() -> None:
    brief = render_work_item_brief(SPEC, PAYLOAD)

    assert "- src/app/ministry/page.tsx" in brief and "- src/app/ministry/[slug]/page.tsx" in brief
    assert "create any that do not exist yet rather than searching the repository" in brief


def test_the_brief_says_which_earlier_items_are_already_in_the_branch() -> None:
    brief = render_work_item_brief(SPEC, {**PAYLOAD, "depends_on_items": ["ws", "ministry-pages"]})

    assert "already merged into your branch, so their code is here: ws, ministry-pages." in brief
    assert "already merged" not in render_work_item_brief(SPEC, PAYLOAD)


def test_the_brief_points_at_agents_md_and_warns_off_stale_context() -> None:
    brief = render_work_item_brief(SPEC, PAYLOAD)

    assert "Read AGENTS.md first" in brief
    assert ".vibey/context/" in brief and "earlier, unrelated work" in brief
    assert "do not weaken them" in brief


def test_a_criterion_the_spec_does_not_define_is_named_not_invented() -> None:
    brief = render_work_item_brief(SPEC, {**PAYLOAD, "acceptance_ids": ["C1", "C9"]})

    assert "- C9 (not found in the accepted spec)" in brief


def test_without_a_spec_it_still_tells_the_item_what_it_has() -> None:
    brief = render_work_item_brief(None, PAYLOAD)

    assert "## Your work item: Walking skeleton" in brief
    assert "- C1 (not found in the accepted spec)" in brief  # the ids, with no text to quote
    assert "src/app/ministry/page.tsx" in brief
    assert "What is being built" not in brief and "Rules for all" not in brief


def test_without_a_spec_or_anything_in_the_payload_there_is_no_brief() -> None:
    assert render_work_item_brief(None, {}) == ""
    assert render_work_item_brief(None, {"title": "only a title"}) == ""


def test_a_spec_with_a_payload_that_names_no_criteria_gives_the_rules_but_no_item_section() -> None:
    brief = render_work_item_brief(SPEC, {"title": "legacy item"})

    assert "Rules for all of this work" in brief
    assert "## Your work item" not in brief and "Make these acceptance criteria" not in brief
    assert "How to work" in brief


def test_a_title_is_optional() -> None:
    brief = render_work_item_brief(SPEC, {k: v for k, v in PAYLOAD.items() if k != "title"})

    assert "## Your work item\n" in brief


def test_blank_and_non_list_values_are_ignored() -> None:
    brief = render_work_item_brief(
        SPEC,
        {
            "title": "t",
            "acceptance_ids": "C1",
            "files_touched_hint": ["  ", ""],
            "depends_on_items": 7,
        },
    )

    assert "## Your work item" not in brief


def test_a_spec_with_no_walking_skeleton_text_or_rules_says_less() -> None:
    bare = DesignSpec("Do the thing.", (), (), (), (), "  ")

    brief = render_work_item_brief(bare, PAYLOAD)

    assert "Do the thing." in brief
    assert "first slice" not in brief
    assert "Rules for all" not in brief and "Out of scope" not in brief


def test_a_very_long_brief_is_cut_at_a_line_with_a_note() -> None:
    huge = DesignSpec(
        "Build it.",
        tuple(Constraint(f"rule {n}: " + "x" * 200, ConstraintKind.HARD) for n in range(200)),
        (),
        SPEC.criteria,
        (),
        "skeleton",
    )

    brief = render_work_item_brief(huge, PAYLOAD)

    assert len(brief) <= MAX_BRIEF_CHARS + 200
    assert "the rest of this brief was cut for length" in brief
    assert brief.index("Build it.") < brief.index("rule 0:")  # the objective always survives
