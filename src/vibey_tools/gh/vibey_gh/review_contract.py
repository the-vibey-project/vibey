# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which half of a pull-request review a diff alone can carry.

vibey-gh's pull-request review asks for nineteen answers in one JSON object: a verdict
(`pass`), a `summary`, a `findings` array, and sixteen booleans that certify the
repository's documentation contract — `complete`, `accurate`, `human_readable`,
`audience_order`, `links_valid` and the rest. Two different reviewers answer that same
schema from very different amounts of evidence. The paid exact-head reviewer reads the
whole proposed repository under `target/`; the local fallback in `local_review.py` is
handed one diff and nothing else.

That gap is not about model size. A reviewer cannot judge whether a README opens with the
problem before the vocabulary, whether the site's nav puts the beginner on-ramp first, or
whether every hyperlink resolves, when the only thing in front of it is a patch. Those
judgments need the documents themselves. `pass`, `summary` and `findings` are different:
each one is grounded in lines the diff actually contains.

That split used to live implicitly in three places — `local_review.REVIEW_SCHEMA` (what
the local model is asked), `local_review.UNEVALUATED_FIELDS` (what it is not asked), and
a hand-written `--json-schema` literal in `templates/workflows/pr-review.yml` (what the
paid path is asked). Three copies of one meaning drift, and one of them was already misread:
`audience_order` is in `UNEVALUATED_FIELDS` and yet the fallback writes `true` for it. Both
are true at once, and the reconciliation is the whole point of this module — the `true` is
a SHAPE placeholder that keeps `jq` and every downstream `.pass` reader working, not a
claim that the field was checked. This module says that once, in a form code can read, so
no caller has to infer it from a boolean that looks like an answer.

The paid path's copy is gone: the template now carries `__VIBEY_GH_REVIEW_SCHEMA__`, and
`install.render_workflow` fills it from `ReviewContract.json_schema()`. So the schema a
reviewer is held to and the halves this module draws are one table, not two that have to
be kept in step by hand.

The halves are also what the lanes are ordered by (doctrine 8.a, #133). When the sovereign
lane is up it carries the diff-groundable half, and the paid reviewer is handed only
`json_schema([REQUIRES_WIDER_CONTEXT])` -- the sixteen judgments plus the two report fields
it writes its own prose and findings into. `vibey_gh.review_composition` puts the two
answers back together into one verdict that says which lane carried which field.

With no paid review declared (sub-doctrine 8.b) there is no second lane at all: the
sovereign reviewer answers the whole schema itself. That is when two more facts in this
table earn their keep. `field_questions` is what each documentation judgment ASKS, so the
prompt a local model is handed is built from the same rows as the schema it answers; and
`scope_field` is where every local verdict names the halves it actually answered, so a
diff-only verdict -- whose documentation judgments are placeholders -- can never be read
as a whole review.

Deliberately data, not behaviour. It decides nothing and calls nothing; it states what
each half means — and what JSON type each field is answered in — so the reviewers, the
workflow templates and the tests can all agree.
"""

from __future__ import annotations

import copy
import dataclasses
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

# The two halves, named rather than spelled out at each call site.
DIFF_GROUNDABLE = "diff-groundable"
REQUIRES_WIDER_CONTEXT = "requires-wider-context"

# What a reviewer can answer from the diff in front of it: a verdict, a description of the
# change, and findings that each point at an added or modified line.
DEFAULT_DIFF_GROUNDABLE_FIELDS = ("pass", "summary", "findings")

# The documentation contract. Every one of these is a statement about documents the diff
# does not contain — a README's opening, the published site's nav order, whether each
# platform surface has a working example, whether every link resolves. Cross-file reasoning
# over the repository as it would stand, which is exactly what a diff withholds.
DEFAULT_WIDER_CONTEXT_FIELDS = (
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

# Where a reviewer answering the wider-context half ON ITS OWN writes its prose and its
# findings. `summary` and `findings` belong to the diff-groundable half, so once the
# sovereign lane carries that half they hold the sovereign lane's words; a second reviewer
# writing into the same two names would overwrite them, and the published verdict could no
# longer say which lane said what. So the wider half, answered alone, reports under names
# of its own. They are never asked for when one reviewer answers both halves: the full
# schema stays exactly the one the paid reviewer has always been handed.
DEFAULT_WIDER_SUMMARY_FIELD = "wider_summary"
DEFAULT_WIDER_FINDINGS_FIELD = "wider_findings"

# The shape of one finding. Every reviewer that reports findings reports them in this form,
# and `line` is optional because not every finding is about a single line.
DEFAULT_FINDING_SCHEMA: Mapping[str, object] = {
    "type": "object",
    "properties": {
        "severity": {"type": "string"},
        "path": {"type": "string"},
        "line": {"type": "integer"},
        "explanation": {"type": "string"},
        "recommended_fix": {"type": "string"},
    },
    "required": ["severity", "path", "explanation", "recommended_fix"],
}

# The JSON type each field is answered in. The verdict and every documentation judgment
# are booleans, because the gate combines them with `and`; the summary is prose; the
# findings are a list of the objects above.
#
# The ORDER of this table is the order of the schema's keys, and it is deliberately not
# the contract's own order (`ReviewContract.fields`): the verdict first, then the sixteen
# judgments, then the prose. That is the order the paid reviewer has always been handed,
# and a model writes its answer in the order the schema lists the fields — so reordering
# this table changes what the model has already committed to by the time it writes its
# summary. Keep it unless that change is the point.
#
# The wider half's own report fields come last. The full schema never selects them, so
# they cannot move a key of it; the wider half answered alone lists its sixteen judgments
# first and its prose after, the same "verdict before words" order as the full schema.
DEFAULT_FIELD_SCHEMAS: Mapping[str, Mapping[str, object]] = {
    "pass": {"type": "boolean"},
    **{name: {"type": "boolean"} for name in DEFAULT_WIDER_CONTEXT_FIELDS},
    "summary": {"type": "string"},
    "findings": {"type": "array", "items": DEFAULT_FINDING_SCHEMA},
    DEFAULT_WIDER_SUMMARY_FIELD: {"type": "string"},
    DEFAULT_WIDER_FINDINGS_FIELD: {"type": "array", "items": DEFAULT_FINDING_SCHEMA},
}

# What each documentation judgment asks, in one line a reviewer can answer from a change.
# The paid reviewer's prompt states the whole contract in prose; a local model answering the
# whole review with no paid lane declared (8.b) is handed these instead, so its prompt is
# built from the same rows as its schema and cannot list a judgment the schema lacks.
DEFAULT_FIELD_QUESTIONS: Mapping[str, str] = {
    "complete": "nothing user-facing that the change adds, alters or removes is left undocumented",
    "accurate": "no documentation says something the changed code no longer does",
    "human_readable": (
        "prose the change adds orients a first-time reader and defines every load-bearing term"
        " where it is first used"
    ),
    "opening_accessible": (
        "the first two text blocks of README.md (and of the documentation landing page, when"
        " supplied) survive zero project context"
    ),
    "opening_bluf": (
        "those same opening blocks state a problem the reader recognises before any project"
        " vocabulary or description of what the software is"
    ),
    "audience_order": (
        "documentation the change adds sits where the beginner-first arc puts it: the beginner"
        " on-ramp before engineering reference, theory after"
    ),
    "architecture_diagram_complete": (
        "a change to a module, public interface, workflow, data flow, security boundary or"
        " release channel updates docs/project.mmd to match"
    ),
    "all_capabilities_documented": (
        "every CLI, SDK, API, MCP or webhook capability the change adds or alters is documented"
    ),
    "all_commands_documented": "every command, subcommand or flag the change adds or alters is documented",
    "all_configuration_documented": (
        "every configuration key the change adds or alters is documented, with its default"
    ),
    "examples_sufficient": (
        "each surface the change adds has a working example naming only things that exist"
    ),
    "onboarding_sufficient": "installation, prerequisites and the quick start remain correct",
    "operations_sufficient": (
        "anything operational the change adds says how to run it, recover it and troubleshoot it"
    ),
    "security_sufficient": (
        "every trust boundary, secret or permission the change adds or alters is documented"
    ),
    "release_process_sufficient": (
        "every effect the change has on release, provenance or upgrade is documented"
    ),
    "links_valid": (
        "every link the change adds is well formed, and a link to a repository path names one"
        " that exists"
    ),
}

# Where a local verdict names the halves it actually answered -- `[DIFF_GROUNDABLE]` for a
# diff-only review, both halves for a whole one. Neither a judgment nor a report field: the
# reviewer does not answer it, the code that ran the reviewer states it.
DEFAULT_SCOPE_FIELD = "scope"

# Said in the verdict's own summary, because the verdict travels further than this module
# does: it lands in a job log, a PR comment and an artifact, read by people who will never
# open this file.
DEFAULT_UNEVALUATED_NOTICE = (
    "The documentation-contract fields were NOT evaluated by this reviewer; "
    "only the diff itself was reviewed."
)


@dataclass(frozen=True)
class ReviewContract:
    """One source of truth for what a diff-only reviewer may and may not certify.

    Every part is a constructor argument rather than a literal in a method, so a repository
    that shapes its review schema differently — more documentation judgments, fewer, a
    different placeholder — constructs its own instance instead of editing the tuples in
    this module. That is as far as it goes today: the reviewers import the module-level
    `REVIEW_CONTRACT` below directly, so nothing yet reads a contract out of `vibey.toml` or
    takes one as an argument. Carrying a configured instance to the reviewers is a
    follow-up; until it lands, "configurable" means constructible, not wired.
    """

    diff_groundable: tuple[str, ...]
    requires_wider_context: tuple[str, ...]
    # What a reviewer that did not evaluate a field writes for it anyway. The primary
    # schema types these as booleans and the gate aggregates them with `and`, so omitting
    # them would read as a malformed verdict and `false` would read as a failed judgment.
    # `true` keeps the payload shape-compatible; `unevaluated_notice` is what stops it
    # being read as an answer.
    unevaluated_placeholder: bool = True
    unevaluated_notice: str = DEFAULT_UNEVALUATED_NOTICE
    # Field name -> the JSON Schema fragment it is answered in, in schema key order. A
    # repository with its own fields supplies its own table; a field with no entry makes
    # `json_schema` raise rather than guess a type for it. Left out of the hash because a
    # mapping has none; it still takes part in equality.
    field_schemas: Mapping[str, Mapping[str, object]] = dataclasses.field(
        default_factory=lambda: DEFAULT_FIELD_SCHEMAS, hash=False
    )
    # Where the wider half, answered by a reviewer that is NOT also answering the diff
    # half, writes its prose and its findings (see `DEFAULT_WIDER_SUMMARY_FIELD`). Report
    # fields, not judgments: they belong to neither half, so `fields`, `classify` and
    # `placeholders` never see them, and only a wider-half-alone schema asks for them.
    # Named by role rather than listed, so nothing downstream has to guess which of the
    # two holds the findings.
    wider_summary_field: str = DEFAULT_WIDER_SUMMARY_FIELD
    wider_findings_field: str = DEFAULT_WIDER_FINDINGS_FIELD
    # Judgment name -> what it asks (see `DEFAULT_FIELD_QUESTIONS`). Out of the hash for the
    # same reason as `field_schemas`; a judgment with no entry makes `questions` raise.
    field_questions: Mapping[str, str] = dataclasses.field(
        default_factory=lambda: DEFAULT_FIELD_QUESTIONS, hash=False
    )
    # Where a local verdict names the halves it answered (see `DEFAULT_SCOPE_FIELD`).
    scope_field: str = DEFAULT_SCOPE_FIELD

    def __post_init__(self) -> None:
        for label, fields in (
            (DIFF_GROUNDABLE, self.diff_groundable),
            (REQUIRES_WIDER_CONTEXT, self.requires_wider_context),
            ("wider report", self.wider_report_fields),
        ):
            if len(set(fields)) != len(fields):
                raise ValueError(f"{label} review fields must be unique")
        overlap = sorted(set(self.diff_groundable) & set(self.requires_wider_context))
        if overlap:
            # A field in both halves is the exact lie this module exists to prevent:
            # something a caller would treat as evaluated and unevaluated at once.
            raise ValueError(f"a review field cannot be in both halves: {', '.join(overlap)}")
        clash = sorted(set(self.wider_report_fields) & set(self.fields))
        if clash:
            # A report field that is also a judgment would be written by two lanes at once
            # -- the collision the report fields exist to avoid.
            raise ValueError(f"a wider report field cannot be a review field: {', '.join(clash)}")
        if self.scope_field in self.fields + self.wider_report_fields:
            # A lane writing the scope would be claiming its own remit; the scope is what
            # the code that ran it says it asked.
            raise ValueError(f"the scope field cannot be a review field: {self.scope_field}")

    @classmethod
    def default(cls) -> ReviewContract:
        """The split as vibey-gh's own review schema draws it."""
        return cls(
            diff_groundable=DEFAULT_DIFF_GROUNDABLE_FIELDS,
            requires_wider_context=DEFAULT_WIDER_CONTEXT_FIELDS,
        )

    @property
    def wider_report_fields(self) -> tuple[str, ...]:
        """The wider half's own summary and findings fields, in that order."""
        return (self.wider_summary_field, self.wider_findings_field)

    @property
    def fields(self) -> tuple[str, ...]:
        """Every field the review schema carries: the diff-groundable half, then the other.

        This is the contract's own order, NOT the key order of any schema document. The
        schema `json_schema()` renders follows `field_schemas`, which puts `summary` and
        `findings` last; here they sit second and third, beside `pass`, because the halves
        are what this module is about. So zip this against a schema's values positionally
        and the values land on the wrong names — look fields up by name.
        """
        return self.diff_groundable + self.requires_wider_context

    def classify(self, field: str) -> str:
        """Which half `field` belongs to, as `DIFF_GROUNDABLE` or `REQUIRES_WIDER_CONTEXT`.

        Unknown fields raise rather than defaulting to either answer: guessing
        "diff-groundable" would licence a local model to certify something nobody decided
        it could, and guessing the other way would silently drop a judgment.
        """
        if field in self.diff_groundable:
            return DIFF_GROUNDABLE
        if field in self.requires_wider_context:
            return REQUIRES_WIDER_CONTEXT
        raise KeyError(f"not a review field: {field!r}")

    def is_diff_groundable(self, field: str) -> bool:
        """Whether a reviewer holding only the diff may answer `field` on its own evidence."""
        return self.classify(field) == DIFF_GROUNDABLE

    def placeholders(self) -> dict[str, bool]:
        """What a diff-only reviewer writes for the fields it did not evaluate.

        These are NOT assertions. Every value here is `unevaluated_placeholder`, present so
        the verdict keeps the shape the gate parses; the truth about them is
        `unevaluated_notice`, which belongs in the same payload.
        """
        return {field: self.unevaluated_placeholder for field in self.requires_wider_context}

    def questions(self) -> list[tuple[str, str]]:
        """Each documentation judgment with the question it asks, in the contract's order.

        Raises `KeyError` for a judgment with no declared question, for the reason
        `json_schema` refuses an untyped field: a reviewer asked something nobody wrote down
        is answering a different question than the one the gate reads.
        """
        missing = [name for name in self.requires_wider_context if name not in self.field_questions]
        if missing:
            raise KeyError(f"no question declared for review field(s): {', '.join(missing)}")
        return [(name, self.field_questions[name]) for name in self.requires_wider_context]

    def json_schema(self, halves: Iterable[str] | None = None) -> dict[str, object]:
        """The JSON Schema a reviewer answering `halves` is held to.

        `halves` names `DIFF_GROUNDABLE`, `REQUIRES_WIDER_CONTEXT`, or both; `None` means
        both, which is the full schema the paid exact-head reviewer answers whenever no
        other lane carries the diff half. Every selected field is a property AND required
        — a reviewer that may skip a field is one whose silence reads as an answer.

        The wider half selected WITHOUT the diff half also asks for `wider_report_fields`:
        that reviewer is not the one writing `summary` and `findings`, and still has to be
        able to say what it found. With both halves selected they are left out, so the full
        schema is byte-for-byte the one it has always been.

        Keys follow `field_schemas`, not `fields`; see `DEFAULT_FIELD_SCHEMAS` for why that
        order is kept. Each fragment is copied, so a caller editing the result cannot
        reach back into the contract.

        Raises `ValueError` for a half that does not exist (or none at all) and `KeyError`
        for a selected field with no declared type: a schema that silently omitted a field,
        or typed it by guesswork, is a reviewer asked a different question than the one
        the gate reads.
        """
        chosen = (DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT) if halves is None else tuple(halves)
        known = {DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT}
        if not chosen or not set(chosen) <= known:
            raise ValueError(
                f"halves must name {DIFF_GROUNDABLE!r} and/or {REQUIRES_WIDER_CONTEXT!r}, "
                f"not {chosen!r}"
            )
        wanted = {name for name in self.fields if self.classify(name) in chosen}
        if DIFF_GROUNDABLE not in chosen:
            wanted |= set(self.wider_report_fields)
        undeclared = wanted - set(self.field_schemas)
        missing = [name for name in self.fields + self.wider_report_fields if name in undeclared]
        if missing:
            raise KeyError(f"no JSON type declared for review field(s): {', '.join(missing)}")
        order = [name for name in self.field_schemas if name in wanted]
        return {
            "type": "object",
            "properties": {name: copy.deepcopy(dict(self.field_schemas[name])) for name in order},
            "required": order,
        }


# The contract this repository's reviewers actually read.
REVIEW_CONTRACT = ReviewContract.default()
