# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One review verdict from two lanes, saying which lane carried what.

Doctrine 8.a makes the sovereign path the preferred way to run, and #133 applies it to
pull-request review by splitting the work along the line `vibey_gh.review_contract` draws.
When the operator's own runner is up, a local model reviews the diff and carries the
diff-groundable half -- `pass`, `summary`, `findings`. The paid reviewer then answers only
the requires-wider-context half: the sixteen documentation-contract judgments, which need
the whole repository rather than a patch, plus `wider_summary` and `wider_findings` to say
what it found. It is no longer asked for the verdict on the diff at all.

Two answers are not a verdict. This module is where they become one, and it is the only
place that decides what "passed" means -- the workflow used to spell that out as a `jq`
expression listing the sixteen booleans by name, a second copy of the contract that would
have had to learn the split by hand.

The rules, per half:

- **diff-groundable, sovereign lane**: the local reviewer's own `pass`. A local verdict
  that declines with no finding is a decline, not a pass.
- **requires-wider-context, paid lane**: every judgment is exactly `true` and there are no
  findings. That is the rule the paid review has always been held to, and when the paid
  reviewer answers BOTH halves (`FULL`, the only shape when no sovereign lane carried
  anything) it is applied exactly as the old `jq` applied it, so that path is unchanged.

The combined `pass` is both halves passing. Whether automated repair may act on a failure
is a separate answer: repair is a paid agent editing the branch, and it acts on the paid
lane's findings only. A local model's finding is a lead for a human to verify -- the gate
already said so when that model was only a fallback -- so a failure carried by the
sovereign lane alone is never `repairable`.

With no paid review declared (sub-doctrine 8.b, `[pr_automation] paid_review = false`)
there is no paid answer at all: `NO_PAID`. The sovereign lane then answers the whole schema,
and its verdict is composed alone under the strictest reading of both halves -- its own
`pass`, every judgment exactly `true`, and no findings -- and only when the verdict says it
answered both halves. A diff-only verdict's documentation judgments are placeholders, and
reading them as answers is the one thing this module must never do.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from vibey_gh.interfaces.review_contract_interface import ReviewContractPort
from vibey_gh.review_contract import DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT, REVIEW_CONTRACT

# The two lanes, by the names the gate and the persisted verdict use for them.
SOVEREIGN_LANE = "sovereign"
PAID_LANE = "paid"

# The paid reviewer answered the whole schema itself: the review as it always was, and the
# only shape there is when no sovereign lane carried the diff half.
FULL = "full"

# No paid reviewer was asked anything, because no paid review is declared (8.b): the
# sovereign lane's verdict is the whole review.
NO_PAID = "none"

# What the paid reviewer can have been asked. Never the diff half alone: under Option A the
# sovereign lane goes first, so a paid reviewer answering only the diff half has no job.
PAID_HALVES = (FULL, REQUIRES_WIDER_CONTEXT, NO_PAID)


def _count(value: object) -> int:
    """How many findings a field holds, for the job output and the gate's wording.

    Module-level, not a method: it reads no composer state, and both the full and the split
    paths call it on answers of either lane. A list is counted; anything else, including a
    missing field, is zero -- the schema makes every findings field an array, so the other
    shapes exist only in a malformed answer, whose pass/fail `_holds` decides separately.
    """
    return len(value) if isinstance(value, list) else 0


@dataclass(frozen=True)
class ReviewComposer:
    """Composes the review verdict from the paid lane and, when it ran, the sovereign lane.

    The field names that play each role are constructor arguments, defaulting to the ones
    `REVIEW_CONTRACT` draws, so a repository with its own contract constructs its own
    composer rather than editing this one.
    """

    contract: ReviewContractPort = field(default_factory=lambda: REVIEW_CONTRACT)
    verdict_field: str = "pass"
    summary_field: str = "summary"
    findings_field: str = "findings"

    def __post_init__(self) -> None:
        for role, name in (
            ("verdict", self.verdict_field),
            ("summary", self.summary_field),
            ("findings", self.findings_field),
        ):
            if name not in self.contract.diff_groundable:
                # Each of these is read from whichever lane carried the diff half. Naming a
                # field outside that half would read it from the wrong lane.
                raise ValueError(
                    f"the {role} field {name!r} must be in the diff-groundable half of the"
                    " review contract"
                )

    def compose(
        self,
        paid: Mapping[str, Any] | None,
        *,
        half: str,
        sovereign: Mapping[str, Any] | None = None,
        head_sha: str = "",
    ) -> dict[str, Any]:
        """The envelope the review job turns into its outputs.

        - `verdict`: what `record-review` persists for this head.
        - `structured`: what the repair agent is handed as the review result.
        - `carried`: every field of the verdict, mapped to the lane that answered it.
        - `halves`: each unit that was answered as a whole, with its lane, whether it
          passed, and how many findings it reported.
        - `findings`: the findings across every lane.
        - `repairable`: whether automated repair may act on this outcome.
        """
        if half == NO_PAID:
            if paid:
                raise ValueError(
                    "no paid review is declared, so there is no paid answer to compose; the"
                    " sovereign lane's verdict is the whole review"
                )
            if sovereign is None:
                raise ValueError(
                    "no paid review is declared, so the sovereign lane's whole-review verdict"
                    " is needed"
                )
            if not isinstance(sovereign, Mapping):
                raise TypeError(
                    f"the sovereign verdict must be a JSON object, not {type(sovereign).__name__}"
                )
            return self._sovereign_whole(sovereign, head_sha)
        if paid is None and half in (FULL, REQUIRES_WIDER_CONTEXT):
            raise ValueError(f"the paid lane returned no answer to compose for the {half} review")
        if not isinstance(paid, Mapping):
            raise TypeError(f"the paid answer must be a JSON object, not {type(paid).__name__}")
        if half == FULL:
            return self._full(paid, head_sha)
        if half == REQUIRES_WIDER_CONTEXT:
            if sovereign is None:
                raise ValueError(
                    "the paid lane answered only the requires-wider-context half, so the"
                    " sovereign lane's verdict is needed for the diff-groundable half"
                )
            if not isinstance(sovereign, Mapping):
                raise TypeError(
                    f"the sovereign verdict must be a JSON object, not {type(sovereign).__name__}"
                )
            return self._split(paid, sovereign, head_sha)
        raise ValueError(f"the paid half must be one of {', '.join(PAID_HALVES)}, not {half!r}")

    def _holds(self, answer: Mapping[str, Any], findings_field: str) -> bool:
        """Every documentation judgment is exactly `true` and nothing was found.

        Exactly the `jq` this replaced: `.x == true` for each judgment, so a string
        `"true"` or a missing field fails, and `(.findings // []) | length == 0`, so an
        absent or null findings field passes.
        """
        judged = all(answer.get(name) is True for name in self.contract.requires_wider_context)
        return judged and not (answer.get(findings_field) or [])

    def _full(self, paid: Mapping[str, Any], head_sha: str) -> dict[str, Any]:
        # The review exactly as it was before the lanes split. `verdict` is what the old
        # `jq` produced: the answer, the head appended, and `pass` RECOMPUTED from the
        # judgments and the findings rather than taken from the model -- a reviewer's own
        # `pass` has never been trusted over its booleans. `structured` stays the raw
        # answer, as repair was always handed it.
        passed = self._holds(paid, self.findings_field)
        verdict = dict(paid)
        verdict["head_sha"] = head_sha
        verdict[self.verdict_field] = passed
        findings = _count(paid.get(self.findings_field))
        return {
            "half": FULL,
            "verdict": verdict,
            "structured": dict(paid),
            "carried": {name: PAID_LANE for name in self.contract.fields},
            "halves": {FULL: {"lane": PAID_LANE, "passed": passed, "findings": findings}},
            "findings": findings,
            "repairable": not passed,
        }

    def _split(
        self, paid: Mapping[str, Any], sovereign: Mapping[str, Any], head_sha: str
    ) -> dict[str, Any]:
        diff_passed = sovereign.get(self.verdict_field) is True
        wider_passed = self._holds(paid, self.contract.wider_findings_field)
        diff_findings = _count(sovereign.get(self.findings_field))
        wider_findings = _count(paid.get(self.contract.wider_findings_field))

        # Every field in the schema's own key order, each taken from the lane that carried
        # it. A field the lane left out stays out rather than being invented as `null`.
        rank = {name: index for index, name in enumerate(self.contract.field_schemas)}
        names = sorted(
            self.contract.fields + self.contract.wider_report_fields,
            key=lambda name: rank.get(name, len(rank)),
        )
        carried: dict[str, str] = {}
        verdict: dict[str, Any] = {}
        for name in names:
            lane = SOVEREIGN_LANE if name in self.contract.diff_groundable else PAID_LANE
            carried[name] = lane
            source = sovereign if lane == SOVEREIGN_LANE else paid
            if name in source:
                verdict[name] = source[name]
        verdict[self.verdict_field] = diff_passed and wider_passed
        verdict["head_sha"] = head_sha
        # Persisted with the verdict, so a later evaluation of this head can tell a local
        # finding (re-review) from a paid one (repair) without re-deriving the split.
        verdict["carried"] = carried
        verdict["repairable"] = not wider_passed
        return {
            "half": REQUIRES_WIDER_CONTEXT,
            "verdict": verdict,
            "structured": verdict,
            "carried": carried,
            "halves": {
                DIFF_GROUNDABLE: {
                    "lane": SOVEREIGN_LANE,
                    "passed": diff_passed,
                    "findings": diff_findings,
                },
                REQUIRES_WIDER_CONTEXT: {
                    "lane": PAID_LANE,
                    "passed": wider_passed,
                    "findings": wider_findings,
                },
            },
            "findings": diff_findings + wider_findings,
            "repairable": not wider_passed,
        }

    def _sovereign_whole(self, sovereign: Mapping[str, Any], head_sha: str) -> dict[str, Any]:
        answered = sovereign.get(self.contract.scope_field)
        both = {DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT}
        if not isinstance(answered, list) or set(answered) != both:
            # The one refusal this path exists for: a diff-only verdict carries `true` for
            # every documentation judgment as a SHAPE placeholder, and read as a whole review
            # it would pass sixteen judgments nobody made.
            raise ValueError(
                "the sovereign verdict did not answer both halves (its"
                f" {self.contract.scope_field!r} is {answered!r}), so it cannot stand for the"
                " whole review: a diff-only verdict's documentation judgments are placeholders,"
                " not answers"
            )
        passed = sovereign.get(self.verdict_field) is True and self._holds(
            sovereign, self.findings_field
        )
        findings = _count(sovereign.get(self.findings_field))
        # Every field in the schema's own key order; one the reviewer left out stays out.
        verdict = {
            name: sovereign[name]
            for name in self.contract.field_schemas
            if name in self.contract.fields and name in sovereign
        }
        verdict[self.verdict_field] = passed
        verdict["head_sha"] = head_sha
        carried = {name: SOVEREIGN_LANE for name in self.contract.fields}
        verdict["carried"] = carried
        # Repair is a paid agent, and none is declared; a local finding is a lead for a
        # human besides. So a sovereign-only failure is never handed to repair.
        verdict["repairable"] = False
        return {
            "half": NO_PAID,
            "verdict": verdict,
            "structured": verdict,
            "carried": carried,
            "halves": {FULL: {"lane": SOVEREIGN_LANE, "passed": passed, "findings": findings}},
            "findings": findings,
            "repairable": False,
        }


# The composer this repository's workflow calls.
REVIEW_COMPOSER = ReviewComposer()
