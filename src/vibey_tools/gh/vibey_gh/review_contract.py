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

Until now that split lived implicitly in three places — `local_review.REVIEW_SCHEMA` (what
the local model is asked), `local_review.UNEVALUATED_FIELDS` (what it is not asked), and
the review job's `--json-schema` in `templates/workflows/pr-automation.yml` (what the paid
path is asked). Three copies of one meaning drift, and one of them was already misread:
`audience_order` is in `UNEVALUATED_FIELDS` and yet the fallback writes `true` for it. Both
are true at once, and the reconciliation is the whole point of this module — the `true` is
a SHAPE placeholder that keeps `jq` and every downstream `.pass` reader working, not a
claim that the field was checked. This module says that once, in a form code can read, so
no caller has to infer it from a boolean that looks like an answer.

Deliberately data, not behaviour. It decides nothing and calls nothing; it states what
each half means so the reviewers, the workflow templates and the tests can all agree.
"""

from __future__ import annotations

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

    def __post_init__(self) -> None:
        overlap = sorted(set(self.diff_groundable) & set(self.requires_wider_context))
        if overlap:
            # A field in both halves is the exact lie this module exists to prevent:
            # something a caller would treat as evaluated and unevaluated at once.
            raise ValueError(f"a review field cannot be in both halves: {', '.join(overlap)}")

    @classmethod
    def default(cls) -> ReviewContract:
        """The split as vibey-gh's own review schema draws it."""
        return cls(
            diff_groundable=DEFAULT_DIFF_GROUNDABLE_FIELDS,
            requires_wider_context=DEFAULT_WIDER_CONTEXT_FIELDS,
        )

    @property
    def fields(self) -> tuple[str, ...]:
        """Every field the review schema carries: the diff-groundable half, then the other.

        This is the contract's own order, NOT the key order of any schema document. The
        primary schema in `templates/workflows/pr-automation.yml` puts `summary` and
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


# The contract this repository's reviewers actually read.
REVIEW_CONTRACT = ReviewContract.default()
