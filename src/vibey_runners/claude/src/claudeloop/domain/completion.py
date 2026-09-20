# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Completion verdicts — was the whole task finished, or just this turn?

Primary source is the structured-output verdict the model returns per turn
(ClaudeAgentOptions.output_format). A legacy substring marker is retained as a
fallback for when structured output isn't available on a given model/config.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_DONE_MARKER = "CLAUDELOOP_TASK_FULLY_COMPLETE"


@dataclass(frozen=True, slots=True)
class Done:
    summary: str = ""


@dataclass(frozen=True, slots=True)
class Continue:
    remaining_work: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Blocked:
    reason: str


CompletionVerdict = Done | Continue | Blocked


@dataclass(frozen=True, slots=True)
class StructuredVerdict:
    """Mirrors the JSON schema handed to the model via output_format:
    {"complete": bool, "remaining_work": [str], "blocked_on": str|null, "summary": str}

    ``blocked_on`` is terminal (evaluate → Blocked). It is only for true
    external/human blockers; waitable self-started work belongs in
    ``remaining_work`` with ``blocked_on`` left null.
    """

    complete: bool
    remaining_work: tuple[str, ...] = ()
    blocked_on: str | None = None
    summary: str = ""


def evaluate(
    *,
    structured: StructuredVerdict | None,
    output_text: str,
    done_marker: str = DEFAULT_DONE_MARKER,
    cost_usd: float = 0.0,
    empty_turn_streak: int = 0,
    empty_turn_limit: int = 3,
    output_tokens: int = 0,
    marker_fallback: bool = True,
) -> CompletionVerdict:
    """Decide what a single turn's outcome means for the overall task.

    Precedence: a structured verdict is authoritative when present. Only when it is
    absent do we fall back to substring-matching the legacy marker in raw text.

    Empty turns with no structured verdict are soft-failed: treated as wait-only
    Continue, or Blocked after ``empty_turn_limit`` consecutive empties. A turn is
    empty when it produced no text, cost nothing, AND generated no output tokens —
    the token count is what keeps this meaningful on a local backend, where every
    turn is recorded at zero cost (domain/backend.py, cost_mode "zero").

    ``marker_fallback=False`` turns the substring fallback off, so only a
    structured verdict can complete a run. A local backend defaults to that:
    Claude Code delivers the structured verdict through a tool call, and a model
    that cannot make real tool calls was observed writing both its tool calls and
    the done marker as plain text — a "Done" for work that never happened.
    """
    if structured is not None:
        if structured.blocked_on:
            return Blocked(reason=structured.blocked_on)
        if structured.complete:
            return Done(summary=structured.summary)
        return Continue(remaining_work=structured.remaining_work)

    if marker_fallback and done_marker in output_text:
        return Done(summary="")

    if not output_text.strip() and cost_usd <= 0.0 and output_tokens <= 0:
        if empty_turn_streak + 1 >= empty_turn_limit:
            return Blocked(reason="repeated empty model responses")
        return Continue(
            remaining_work=("Waiting for a non-empty model response",),
        )

    return Continue(remaining_work=())
