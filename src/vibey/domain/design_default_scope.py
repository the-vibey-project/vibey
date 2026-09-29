# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The narrowest-scope default for a DESIGN interview question.

A DESIGN question carries a default the model wrote itself, and "accept the
defaults" is the designed zero-touch path through the interview. When the same
model writes both the question and its default, accepting defaults means accepting
the model's appetite. Measured live on 2026-09-29 (project 9692abab, issue #998, a
pure insertion into README.md): 22 questions, most of the form "Should we also add
X?" defaulting to "Yes", grew a table of contents into a generator script, unit
tests and a CI check -- and the CI change touches `.github/**`, which the delegated
approver may never approve, so an issue deliverable unattended became one that
must end at a person.

The prompt now asks for the narrowest default, but a model can ignore prose. This
module is the deterministic half: it recognises a yes/no question that proposes a
new artefact beyond the intake and, when the declared default is not already
negative, rewrites it to the minimal answer. The rule is deliberately small enough
to state in one sentence, so every rewrite can be explained from the record alone:

    a yes/no question that proposes to add, include, extend, enforce or automate
    something, naming an artefact the intake does not name, defaults to "No".

It is conservative by construction. A question about *how* to do what the intake
asks ("Should the anchor generation follow GitHub's algorithm exactly?") names no
artefact and is left alone, and so is one about the granularity of the requested
deliverable ("Do we need to include sub-headings?"): a sub-heading is part of a
table of contents, not a new thing beside it. A false negative leaves the model's
default standing, which is where things were before; a false positive only makes a
proposed default narrower, and a person answering explicitly is never overridden.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from vibey.domain.interfaces.design_default_scope_interface import (
    DesignDefaultScopeGuardInterface,
)


class DefaultScope(StrEnum):
    """`[design.interview] default_scope`: whose appetite a declared default follows."""

    #: A scope-widening question's affirmative default is rewritten to "No".
    NARROWEST = "narrowest"
    #: The model's default is recorded as the model wrote it.
    MODEL = "model"


DEFAULT_SCOPE: Final[DefaultScope] = DefaultScope.NARROWEST
"""The default when nothing is declared. Narrowest is safe as a default: it only
ever proposes less work, preserves the model's original, and never overrides an
answer a person gives."""

NARROWEST_DEFAULT: Final[str] = "No (the intake does not ask for this; out of scope)"
"""The default a scope-widening question is given. Worded for the synthesiser that
reads the ledger next, so the refusal lands as a non-goal rather than a bare "No"."""

# A yes/no question opens with an auxiliary. "Which ...", "What ...", "How ..." ask
# for a choice or a value, and a choice has no single minimal answer to rewrite to.
_YES_NO = re.compile(
    r"^\W*(?:should|shall|do|does|did|will|would|can|could|is|are|must|may|need)\b",
    re.IGNORECASE,
)

# The verbs and phrases that propose doing more than the thing asked.
_EXTENSION = re.compile(
    r"\b(?:add(?:s|ed|ing)?|also|additional(?:ly)?|as\s+well|as\s+part\s+of"
    r"|includ(?:e|es|ed|ing)|extend(?:s|ed|ing)?|enforc(?:e|es|ed|ing)"
    r"|automat(?:e|es|ed|ing|ically)|introduc(?:e|es|ed|ing)|creat(?:e|es|ed|ing)"
    r"|commit(?:s|ted|ting)?|integrat(?:e|es|ed|ing)|provid(?:e|es|ed|ing))\b",
    re.IGNORECASE,
)

# The artefacts a widening question proposes, each under one canonical name so the
# recorded reason reads the same however the model phrased it. Order is the order a
# reason lists them in.
_ARTEFACTS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("test", re.compile(r"\b(?:unit[\s-]?)?tests?\b|\btesting\b", re.IGNORECASE)),
    ("ci", re.compile(r"\bci\b|\bcontinuous\s+integration\b", re.IGNORECASE)),
    ("pipeline", re.compile(r"\bpipelines?\b", re.IGNORECASE)),
    ("workflow", re.compile(r"\bworkflows?\b|\bgithub\s+actions?\b", re.IGNORECASE)),
    ("script", re.compile(r"\bscripts?\b", re.IGNORECASE)),
    ("hook", re.compile(r"\bhooks?\b|\bpre-commit\b", re.IGNORECASE)),
    ("lint", re.compile(r"\blint(?:s|er|ers|ing)?\b", re.IGNORECASE)),
    ("check", re.compile(r"\bchecks?\b", re.IGNORECASE)),
    ("comment", re.compile(r"\bcomments?\b", re.IGNORECASE)),
    ("badge", re.compile(r"\bbadges?\b", re.IGNORECASE)),
    ("changelog", re.compile(r"\bchangelog\b", re.IGNORECASE)),
    ("generator", re.compile(r"\bgenerators?\b", re.IGNORECASE)),
    ("tool", re.compile(r"\btool(?:s|ing)?\b", re.IGNORECASE)),
    ("automation", re.compile(r"\bautomation\b", re.IGNORECASE)),
    ("configuration", re.compile(r"\bconfig(?:uration)?s?\b", re.IGNORECASE)),
    ("dependency", re.compile(r"\bdependenc(?:y|ies)\b|\bpackages?\b", re.IGNORECASE)),
    ("makefile", re.compile(r"\bmakefile\b|\bmake\s+targets?\b", re.IGNORECASE)),
)

# A default that already declines is already the minimal answer.
_NEGATIVE = re.compile(
    r"^\W*(?:no|none|not|never|nothing|neither|false|n/?a|skip|omit|leave|without"
    r"|don'?t|do\s+not|out\s+of\s+scope)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ScopeClassification:
    """Why a question is, or is not, scope-widening -- the evidence, not a verdict."""

    yes_no: bool
    extends: bool
    #: Every artefact the question names, canonical names in declaration order.
    artefacts: tuple[str, ...]
    #: The subset of `artefacts` the intake does not name.
    beyond_intake: tuple[str, ...]

    @property
    def widening(self) -> bool:
        return self.yes_no and self.extends and bool(self.beyond_intake)


@dataclass(frozen=True, slots=True)
class ScopedDefault:
    """The default to declare, and -- when it was rewritten -- what and why."""

    default: str
    #: The model's own default when it was rewritten; None when it stands.
    model_default: str | None = None
    #: One sentence a reader can check against the question and the intake.
    reason: str | None = None

    @property
    def rewritten(self) -> bool:
        return self.model_default is not None


class DesignDefaultScopeGuard:
    """Rewrites a scope-widening question's affirmative default to the minimal one.

    Pure and stateless: the question, the model's default, the intake text and the
    declared policy in; the default to record out.
    """

    def classify(self, question: str, *, intake: str) -> ScopeClassification:
        named = tuple(name for name, pattern in _ARTEFACTS if pattern.search(question))
        return ScopeClassification(
            yes_no=_YES_NO.search(question) is not None,
            extends=_EXTENSION.search(question) is not None,
            artefacts=named,
            beyond_intake=tuple(
                name for name, pattern in _ARTEFACTS if name in named and not pattern.search(intake)
            ),
        )

    def declines(self, default: str) -> bool:
        return _NEGATIVE.search(default) is not None

    def scope(
        self, question: str, default: str, *, intake: str, policy: DefaultScope
    ) -> ScopedDefault:
        if policy is DefaultScope.MODEL or self.declines(default):
            return ScopedDefault(default=default)
        found = self.classify(question, intake=intake)
        if not found.widening:
            return ScopedDefault(default=default)
        return ScopedDefault(
            default=NARROWEST_DEFAULT,
            model_default=default,
            reason=(
                "narrowest-scope default: the question proposes "
                f"{', '.join(found.beyond_intake)}, which the intake does not ask for, "
                f"so the model's default {default!r} was narrowed"
            ),
        )


DESIGN_DEFAULT_SCOPE: Final[DesignDefaultScopeGuardInterface] = DesignDefaultScopeGuard()
"""The guard every DESIGN interview declares its defaults through. Stateless."""
