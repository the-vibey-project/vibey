# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The review contract.

What is worth pinning here is not that the module holds two tuples. It is that the two
tuples are the SAME meaning the review schema and the local fallback already carry, so a
change to any one of the three has to move the other two.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

import pytest

from vibey_gh import install, local_review
from vibey_gh.config import GhConfig
from vibey_gh.install import WORKFLOWS, render_workflow
from vibey_gh.interfaces import ReviewContractPort
from vibey_gh.review_contract import (
    DEFAULT_FIELD_SCHEMAS,
    DIFF_GROUNDABLE,
    REQUIRES_WIDER_CONTEXT,
    REVIEW_CONTRACT,
    ReviewContract,
)

# The `--json-schema` the paid exact-head reviewer was held to while it was a hand-written
# literal in `templates/workflows/pr-review.yml` (as of 4e9adf18), verbatim. The template
# now carries a placeholder that `install.render_workflow` fills from the contract, and
# rendering must not change a byte of what the reviewer is asked. When the schema is MEANT
# to change, change this in the same commit, so the difference is in front of a reviewer.
LEGACY_REVIEW_SCHEMA = (
    '{"type":"object","properties":{"pass":{"type":"boolean"},"complete":{"type":"boolean"},'
    '"accurate":{"type":"boolean"},"human_readable":{"type":"boolean"},'
    '"opening_accessible":{"type":"boolean"},"opening_bluf":{"type":"boolean"},'
    '"audience_order":{"type":"boolean"},"architecture_diagram_complete":{"type":"boolean"},'
    '"all_capabilities_documented":{"type":"boolean"},'
    '"all_commands_documented":{"type":"boolean"},'
    '"all_configuration_documented":{"type":"boolean"},'
    '"examples_sufficient":{"type":"boolean"},"onboarding_sufficient":{"type":"boolean"},'
    '"operations_sufficient":{"type":"boolean"},"security_sufficient":{"type":"boolean"},'
    '"release_process_sufficient":{"type":"boolean"},"links_valid":{"type":"boolean"},'
    '"summary":{"type":"string"},"findings":{"type":"array","items":{"type":"object",'
    '"properties":{"severity":{"type":"string"},"path":{"type":"string"},'
    '"line":{"type":"integer"},"explanation":{"type":"string"},'
    '"recommended_fix":{"type":"string"}},'
    '"required":["severity","path","explanation","recommended_fix"]}}},'
    '"required":["pass","complete","accurate","human_readable","opening_accessible",'
    '"opening_bluf","audience_order","architecture_diagram_complete",'
    '"all_capabilities_documented","all_commands_documented","all_configuration_documented",'
    '"examples_sufficient","onboarding_sufficient","operations_sufficient",'
    '"security_sufficient","release_process_sufficient","links_valid","summary","findings"]}'
)


# The exact-head review picks its schema at run time (#133): the wider half alone when the
# sovereign lane carried the diff half, the whole review otherwise. Both are literals inside
# one GitHub expression, so neither is visible to a plain shell tokenizer until that
# expression is resolved -- which is what this does, once per branch.
_SCHEMA_CHOICE = re.compile(
    r"--json-schema '\$\{\{ (?P<condition>.+?) && '(?P<wider>[^']*)' "
    r"\|\| '(?P<full>[^']*)' \}\}'"
)


def _schema_arguments(text: str, marker: str = "links_valid") -> dict[str, str]:
    """Both `--json-schema` arguments of the review job, as the action will tokenize them.

    Each branch of the expression is substituted back into the line and tokenized
    shell-style, exactly as the action would see it once GitHub has resolved the choice.
    Found by a field only the review schema carries; the workflow holds other schemas."""
    for line in text.splitlines():
        choice = _SCHEMA_CHOICE.search(line)
        if not choice:
            continue
        arguments = {}
        for branch in ("wider", "full"):
            resolved = line[: choice.start()] + f"--json-schema '{choice[branch]}'"
            tokens = shlex.split(resolved.strip())
            arguments[branch] = tokens[tokens.index("--json-schema") + 1]
        if marker in arguments["full"]:
            assert choice["condition"] == "steps.half.outputs.half == 'requires-wider-context'"
            return arguments
    raise AssertionError("pr-review.yml no longer declares the review schema")


def _schema_argument(text: str, marker: str = "links_valid") -> str:
    """The FULL-review `--json-schema` argument: what the paid reviewer answers whenever no
    sovereign lane carried the diff half -- and what it answered before the lanes split."""
    return _schema_arguments(text, marker)["full"]


def _rendered_pr_review() -> str:
    """`pr-review.yml` as `vibey-gh install` writes it. The template alone holds only a
    placeholder where the schema goes; what the reviewer is held to exists only rendered."""
    return render_workflow(WORKFLOWS / "pr-review.yml", GhConfig(root=Path(".")))


def _primary_review_schema() -> dict:
    """The `--json-schema` the paid exact-head reviewer is held to."""
    return json.loads(_schema_argument(_rendered_pr_review()))


def test_the_contract_covers_the_primary_review_schema_exactly():
    """The split is a split OF something. If the paid reviewer's schema grows a judgment
    and the contract does not classify it, nobody has decided whether a diff can carry it
    — and the local fallback would silently neither ask for it nor placeholder it."""
    schema = _primary_review_schema()

    assert set(REVIEW_CONTRACT.fields) == set(schema["required"])
    assert set(REVIEW_CONTRACT.fields) == set(schema["properties"])


def test_the_local_fallback_asks_for_exactly_the_diff_groundable_half():
    assert REVIEW_CONTRACT.diff_groundable == ("pass", "summary", "findings")
    assert set(local_review.REVIEW_SCHEMA["properties"]) == set(REVIEW_CONTRACT.diff_groundable)
    assert local_review.REVIEW_SCHEMA["required"] == list(REVIEW_CONTRACT.diff_groundable)
    assert local_review.UNEVALUATED_FIELDS == REVIEW_CONTRACT.requires_wider_context


def test_the_documentation_contract_is_the_half_a_diff_cannot_carry():
    """Named individually rather than by count: each one is a statement about documents
    the diff does not contain, and a reader should be able to check that claim field by
    field."""
    assert REVIEW_CONTRACT.requires_wider_context == (
        "complete",
        "accurate",
        "human_readable",
        "opening_accessible",
        "opening_bluf",
        "audience_order",
        "architecture_diagram_complete",
        "all_capabilities_documented",
        "all_commands_documented",
        "all_configuration_documented",
        "examples_sufficient",
        "onboarding_sufficient",
        "operations_sufficient",
        "security_sufficient",
        "release_process_sufficient",
        "links_valid",
    )


def test_fields_is_the_two_halves_in_order_and_not_the_yaml_key_order():
    """`fields` orders the diff-groundable half first, then the documentation contract.

    That is deliberately NOT the primary schema's own key order -- `pr-review.yml`
    puts `summary` and `findings` LAST -- so a caller who zips `fields` against a schema's
    values positionally binds them to the wrong names. The docstring says so; this checks
    it, and checks it against the local fallback's own ordering rather than against
    `fields` itself, which would only restate the claim.
    """
    schema = _primary_review_schema()

    assert REVIEW_CONTRACT.fields == (
        tuple(local_review.REVIEW_SCHEMA["required"]) + local_review.UNEVALUATED_FIELDS
    )
    assert REVIEW_CONTRACT.fields[:3] == ("pass", "summary", "findings")
    # The concrete fact the "not schema order" claim rests on. Reorder the YAML to match
    # and this fails, which is the moment to change the docstring rather than ignore it.
    assert list(schema["properties"])[1] == "complete"
    assert list(schema["properties"])[-2:] == ["summary", "findings"]


@pytest.mark.parametrize(
    ("field", "half"),
    [
        ("pass", DIFF_GROUNDABLE),
        ("findings", DIFF_GROUNDABLE),
        ("audience_order", REQUIRES_WIDER_CONTEXT),
        ("links_valid", REQUIRES_WIDER_CONTEXT),
    ],
)
def test_classify_names_the_half(field, half):
    assert REVIEW_CONTRACT.classify(field) == half
    assert REVIEW_CONTRACT.is_diff_groundable(field) is (half == DIFF_GROUNDABLE)


def test_an_unknown_field_raises_rather_than_defaulting_to_either_answer():
    """Defaulting to "diff-groundable" would licence a local model to certify something
    nobody decided it could; defaulting the other way would silently drop a judgment."""
    with pytest.raises(KeyError, match="not a review field"):
        REVIEW_CONTRACT.classify("verdict")
    with pytest.raises(KeyError):
        REVIEW_CONTRACT.is_diff_groundable("verdict")


def test_a_field_cannot_sit_in_both_halves():
    """The exact lie this module exists to prevent: something a caller would read as
    evaluated and unevaluated at once."""
    with pytest.raises(ValueError, match="both halves: accurate, summary"):
        ReviewContract(
            diff_groundable=("pass", "summary", "accurate"),
            requires_wider_context=("accurate", "summary"),
        )


@pytest.mark.parametrize(
    "half, other",
    [
        ("diff_groundable", "requires_wider_context"),
        ("requires_wider_context", "diff_groundable"),
    ],
)
def test_a_half_cannot_name_the_same_field_twice(half: str, other: str):
    """A duplicate inside ONE half, which the cross-half check above cannot see.

    `ReviewContract` is constructible by embedding repositories, so the halves are a
    caller's input rather than this module's own constant. A repeated name produces a
    duplicated entry in `fields` and in a JSON Schema's `required` list while
    `placeholders()` silently collapses it back to one -- so the count a reader takes
    from the schema and the count a verdict carries would disagree.

    Both halves are exercised because the guard is a loop over the two, and a loop only
    ever entered once would leave the other half unguarded.
    """
    label = DIFF_GROUNDABLE if half == "diff_groundable" else REQUIRES_WIDER_CONTEXT
    kwargs = {half: ("pass", "summary", "summary"), other: ()}
    with pytest.raises(ValueError, match=f"{label} review fields must be unique"):
        ReviewContract(**kwargs)  # type: ignore[arg-type]


def test_the_placeholders_are_shape_compatibility_and_say_so():
    """`audience_order` is unevaluated AND emitted as `true`. Both are true at once, and
    the reconciliation has to be readable from the code rather than inferred from a
    boolean that looks like an answer."""
    placeholders = REVIEW_CONTRACT.placeholders()

    assert set(placeholders) == set(REVIEW_CONTRACT.requires_wider_context)
    assert placeholders["audience_order"] is True
    assert all(value is True for value in placeholders.values())
    # The value alone is a lie; the notice is what makes the pair honest, so it travels
    # in the same verdict.
    assert "NOT evaluated" in REVIEW_CONTRACT.unevaluated_notice


def test_a_repository_can_declare_its_own_split():
    """Everything is a constructor argument, not a literal in a method: a repository whose
    review schema is shaped differently configures this rather than forking it."""
    contract = ReviewContract(
        diff_groundable=("pass",),
        requires_wider_context=("house_style",),
        unevaluated_placeholder=False,
        unevaluated_notice="not checked here",
    )

    assert contract.fields == ("pass", "house_style")
    assert contract.placeholders() == {"house_style": False}
    assert contract.unevaluated_notice == "not checked here"


def test_the_contract_satisfies_the_declared_seam():
    assert isinstance(REVIEW_CONTRACT, ReviewContractPort)
    assert REVIEW_CONTRACT == ReviewContract.default()

    # Including the placeholder value itself: it decides what `placeholders()` writes into
    # every verdict, so a caller holding only the seam has to be able to read it, and a
    # substitute implementation must not be able to satisfy the Protocol without it.
    port: ReviewContractPort = REVIEW_CONTRACT
    assert port.unevaluated_placeholder is True
    assert set(port.placeholders().values()) == {port.unevaluated_placeholder}
    # The schema is read through the same seam, so a substitute contract has to render one.
    # The table also types the wider half's report fields, which the full schema never asks.
    judged = [name for name in port.field_schemas if name not in port.wider_report_fields]
    assert judged == port.json_schema()["required"]
    assert port.wider_report_fields == (port.wider_summary_field, port.wider_findings_field)


def test_the_rendered_schema_is_the_hand_written_one_it_replaced():
    """Moving the schema into the contract is groundwork, not a change to the review: the
    paid reviewer must be asked exactly what it was asked before, down to key order —
    a model answers in the order the schema lists the fields."""
    rendered = _schema_argument(_rendered_pr_review())

    assert json.loads(rendered) == json.loads(LEGACY_REVIEW_SCHEMA)
    assert rendered == LEGACY_REVIEW_SCHEMA
    assert json.dumps(REVIEW_CONTRACT.json_schema(), separators=(",", ":")) == rendered


def test_the_template_carries_placeholders_and_never_a_hand_written_schema():
    """A literal beside the placeholders is how a second copy creeps back in."""
    raw = (WORKFLOWS / "pr-review.yml").read_text(encoding="utf-8")

    assert (
        "--json-schema '${{ steps.half.outputs.half == 'requires-wider-context' && "
        "'__VIBEY_GH_REVIEW_WIDER_SCHEMA__' || '__VIBEY_GH_REVIEW_SCHEMA__' }}'"
    ) in raw
    assert raw.count("__VIBEY_GH_REVIEW_SCHEMA__") == 1
    assert raw.count("__VIBEY_GH_REVIEW_WIDER_SCHEMA__") == 1
    assert '"links_valid"' not in raw
    rendered = _rendered_pr_review()
    assert "__VIBEY_GH_REVIEW_SCHEMA__" not in rendered
    assert "__VIBEY_GH_REVIEW_WIDER_SCHEMA__" not in rendered


def _deployed_copies() -> list:
    """Every rendered `pr-review.yml` this checkout carries: the tenant's own and, inside
    the monorepo, the workspace root's -- rendered with a different configuration, which is
    exactly why both are read rather than assumed to agree. A standalone sdist has only the
    first."""
    tenant = Path(__file__).resolve().parent.parent
    copies = [pytest.param(tenant / ".github/workflows/pr-review.yml", id="tenant")]
    for parent in tenant.parents:
        candidate = parent / ".github/workflows/pr-review.yml"
        if candidate.is_file():
            copies.append(pytest.param(candidate, id="workspace"))
            break
    return copies


@pytest.mark.parametrize("path", _deployed_copies())
def test_every_deployed_copy_asks_what_the_contract_says(path: Path):
    deployed = _schema_arguments(path.read_text(encoding="utf-8"))

    assert json.loads(deployed["full"]) == REVIEW_CONTRACT.json_schema()
    assert json.loads(deployed["wider"]) == REVIEW_CONTRACT.json_schema([REQUIRES_WIDER_CONTEXT])


def test_the_full_schema_requires_every_field_in_schema_order():
    schema = REVIEW_CONTRACT.json_schema()
    judged = [
        name for name in DEFAULT_FIELD_SCHEMAS if name not in ("wider_summary", "wider_findings")
    ]

    assert schema["type"] == "object"
    assert list(schema["properties"]) == judged
    assert schema["required"] == judged
    assert set(schema["required"]) == set(REVIEW_CONTRACT.fields)
    assert schema == REVIEW_CONTRACT.json_schema((DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT))


def test_one_half_is_exactly_that_half():
    """The seam the sovereign-first ordering stands on: each half's schema asks for its own
    fields, all of them, and nothing from the other half. The wider half asked ALONE also
    asks where to write its own prose and findings -- `summary` and `findings` are the
    other lane's -- and asks them after its judgments, verdict before words."""
    diff = REVIEW_CONTRACT.json_schema([DIFF_GROUNDABLE])
    wider = REVIEW_CONTRACT.json_schema([REQUIRES_WIDER_CONTEXT])
    judgments = list(REVIEW_CONTRACT.requires_wider_context)

    assert diff["required"] == ["pass", "summary", "findings"]
    assert list(diff["properties"]) == diff["required"]
    assert wider["required"] == [*judgments, "wider_summary", "wider_findings"]
    assert list(wider["properties"]) == wider["required"]
    assert all(wider["properties"][name] == {"type": "boolean"} for name in judgments)
    assert wider["properties"]["wider_summary"] == {"type": "string"}
    assert wider["properties"]["wider_findings"] == diff["properties"]["findings"]
    assert not {"pass", "summary", "findings"} & set(wider["properties"])
    assert diff["properties"]["findings"]["items"]["required"] == [
        "severity",
        "path",
        "explanation",
        "recommended_fix",
    ]


@pytest.mark.parametrize("halves", [[], ["everything"], [DIFF_GROUNDABLE, "diff-only"]])
def test_a_half_that_does_not_exist_is_refused(halves):
    """An empty or misspelt selection would otherwise render a schema that asks nothing."""
    with pytest.raises(ValueError, match="halves must name"):
        REVIEW_CONTRACT.json_schema(halves)


def test_a_field_with_no_declared_type_raises_rather_than_being_guessed():
    """The same rule `classify` keeps: a guessed type is a reviewer asked a different
    question than the one the gate reads."""
    contract = ReviewContract(diff_groundable=("pass",), requires_wider_context=("house_style",))

    assert contract.json_schema([DIFF_GROUNDABLE])["required"] == ["pass"]
    with pytest.raises(KeyError, match="no JSON type declared for review field.s.: house_style"):
        contract.json_schema()


def test_a_repository_can_declare_its_own_types():
    contract = ReviewContract(
        diff_groundable=("pass", "notes"),
        requires_wider_context=("house_style",),
        field_schemas={
            "notes": {"type": "string"},
            "house_style": {"type": "boolean"},
            "pass": {"type": "boolean"},
            "unused": {"type": "null"},
        },
    )

    schema = contract.json_schema()

    # The table's order, not the contract's; and an entry no field names is simply unused.
    assert schema["required"] == ["notes", "house_style", "pass"]
    assert schema["properties"]["notes"] == {"type": "string"}


def test_the_rendered_schema_cannot_reach_back_into_the_contract():
    schema = REVIEW_CONTRACT.json_schema()
    schema["properties"]["findings"]["items"]["required"].append("mutated")
    schema["properties"]["pass"]["type"] = "string"

    fresh = REVIEW_CONTRACT.json_schema()
    assert "mutated" not in fresh["properties"]["findings"]["items"]["required"]
    assert fresh["properties"]["pass"] == {"type": "boolean"}


def test_an_apostrophe_in_a_schema_cannot_break_the_single_quoted_argument(monkeypatch):
    """`claude_args` is tokenized shell-style and the schema sits inside single quotes.
    JSON's own syntax has no apostrophe, but a string in a configured fragment can: the
    render writes it as the JSON escape, which parses back to the same text."""
    contract = ReviewContract(
        diff_groundable=("pass",),
        requires_wider_context=("house_style",),
        field_schemas={
            "pass": {"type": "boolean", "description": "the reviewer's verdict"},
            "house_style": {"type": "boolean", "description": "the house's own style"},
            "wider_summary": {"type": "string"},
            "wider_findings": {"type": "array"},
        },
    )
    monkeypatch.setattr(install, "REVIEW_CONTRACT", contract)

    arguments = _schema_arguments(_rendered_pr_review(), marker="house_style")

    # Both branches, because both are expression literals as well as shell arguments, and
    # an apostrophe would end either one early.
    assert "'" not in arguments["full"] and "'" not in arguments["wider"]
    full = json.loads(arguments["full"])
    assert full["properties"]["pass"]["description"] == "the reviewer's verdict"
    wider = json.loads(arguments["wider"])
    assert wider["properties"]["house_style"]["description"] == "the house's own style"


def test_the_full_schema_never_asks_for_the_wider_report_fields():
    """The report fields exist for a reviewer answering the wider half ALONE. One reviewer
    answering both halves writes `summary` and `findings`; handing it two more names to
    write the same things into would change the review it has always been asked for."""
    full = REVIEW_CONTRACT.json_schema()
    both = REVIEW_CONTRACT.json_schema([DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT])
    diff = REVIEW_CONTRACT.json_schema([DIFF_GROUNDABLE])

    for schema in (full, both, diff):
        assert not set(REVIEW_CONTRACT.wider_report_fields) & set(schema["properties"])
    assert REVIEW_CONTRACT.wider_report_fields == ("wider_summary", "wider_findings")


def test_the_report_fields_are_neither_half():
    """They are where one lane says what it found, not judgments: nothing classifies them,
    and nothing placeholders them."""
    for name in REVIEW_CONTRACT.wider_report_fields:
        assert name not in REVIEW_CONTRACT.fields
        assert name not in REVIEW_CONTRACT.placeholders()
        with pytest.raises(KeyError, match="not a review field"):
            REVIEW_CONTRACT.classify(name)


def test_a_report_field_cannot_also_be_a_judgment():
    """A report field that is also a review field would be written by two lanes at once --
    the collision the report fields exist to prevent."""
    with pytest.raises(ValueError, match="wider report field cannot be a review field: summary"):
        ReviewContract(
            diff_groundable=("pass", "summary"),
            requires_wider_context=("house_style",),
            wider_summary_field="summary",
        )


def test_the_two_report_fields_cannot_be_one_field():
    with pytest.raises(ValueError, match="wider report review fields must be unique"):
        ReviewContract(
            diff_groundable=("pass",),
            requires_wider_context=("house_style",),
            wider_summary_field="notes",
            wider_findings_field="notes",
        )


def test_a_repository_can_name_its_own_report_fields():
    contract = ReviewContract(
        diff_groundable=("pass",),
        requires_wider_context=("house_style",),
        field_schemas={
            "pass": {"type": "boolean"},
            "house_style": {"type": "boolean"},
            "house_notes": {"type": "string"},
            "house_issues": {"type": "array"},
        },
        wider_summary_field="house_notes",
        wider_findings_field="house_issues",
    )

    wider = contract.json_schema([REQUIRES_WIDER_CONTEXT])

    assert wider["required"] == ["house_style", "house_notes", "house_issues"]


def test_an_untyped_report_field_raises_like_any_other():
    """The same rule as every field: a guessed type is a different question."""
    contract = ReviewContract(
        diff_groundable=("pass",),
        requires_wider_context=("house_style",),
        field_schemas={"pass": {"type": "boolean"}, "house_style": {"type": "boolean"}},
    )

    assert contract.json_schema()["required"] == ["pass", "house_style"]
    with pytest.raises(KeyError, match="wider_summary, wider_findings"):
        contract.json_schema([REQUIRES_WIDER_CONTEXT])


# --------------------------------------------------------------------------------------
# The whole review, answered by one sovereign reviewer (sub-doctrine 8.b)
# --------------------------------------------------------------------------------------


def test_every_documentation_judgment_carries_the_question_a_reviewer_is_asked():
    """With no paid review declared, the sovereign lane answers the documentation contract
    too, and a local model asked for sixteen bare field names guesses at what each means.
    Each judgment's question lives beside its type, in the one table, so the prompt a
    reviewer is handed cannot list a judgment the schema lacks or skip one it has."""
    asked = REVIEW_CONTRACT.questions()

    assert [name for name, _ in asked] == list(REVIEW_CONTRACT.requires_wider_context)
    for name, question in asked:
        assert question.strip() and question == REVIEW_CONTRACT.field_questions[name]
    # A seam reader gets the same table.
    port: ReviewContractPort = REVIEW_CONTRACT
    assert port.questions() == asked


def test_a_judgment_with_no_question_raises_rather_than_being_asked_blind():
    """The same rule as a field with no type: a reviewer asked a question nobody wrote down
    is asked a different question than the one the gate reads."""
    contract = ReviewContract(
        diff_groundable=("pass",),
        requires_wider_context=("house_style", "tone"),
        field_questions={"tone": "the prose is kind"},
    )

    with pytest.raises(KeyError, match="no question declared for review field.*house_style"):
        contract.questions()


def test_a_verdict_names_the_halves_it_actually_answered():
    """A diff-only verdict writes `true` into every judgment it did NOT evaluate, to keep
    its shape. Read as a whole review, those placeholders would pass sixteen judgments
    nobody made -- so every local verdict says which halves it answered, under a key that
    is neither a judgment nor a report field."""
    assert REVIEW_CONTRACT.scope_field == "scope"
    assert REVIEW_CONTRACT.scope_field not in REVIEW_CONTRACT.fields
    assert REVIEW_CONTRACT.scope_field not in REVIEW_CONTRACT.wider_report_fields
    port: ReviewContractPort = REVIEW_CONTRACT
    assert port.scope_field == "scope"


@pytest.mark.parametrize("name", ["pass", "house_style", "wider_summary"])
def test_the_scope_field_cannot_be_a_field_a_lane_writes(name: str):
    with pytest.raises(ValueError, match=f"scope field cannot be a review field: {name}"):
        ReviewContract(
            diff_groundable=("pass",),
            requires_wider_context=("house_style",),
            scope_field=name,
        )
