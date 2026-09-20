# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Data transfer objects passed between application/ and infrastructure/ adapters.
Not domain value objects — these carry the raw shape of one SDK interaction
before domain.classify.classify() and domain.completion.evaluate() reduce them
to CapacityState / CompletionVerdict."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from claudeloop.domain.classify import TurnSignals
from claudeloop.domain.completion import StructuredVerdict


@dataclass(frozen=True, slots=True)
class TurnOutcome:
    """What one real or probe turn produced, translated from raw SDK messages
    by infrastructure/agent/translate.py."""

    signals: TurnSignals
    verdict: StructuredVerdict | None
    output_text: str
    session_id: str | None
    cost_usd: float = 0.0
    raw_events: tuple[dict[str, object], ...] = ()
    # Token counts from ResultMessage.usage. Kept even when cost is recorded as
    # zero (a local backend), because they are the only evidence a turn did work.
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ProbeResult:
    signals: TurnSignals
    at: datetime


@dataclass(frozen=True, slots=True)
class RunResult:
    success: bool
    reason: str
    session_id: str | None
    turns_spent: int
    dollars_spent: float


@dataclass(frozen=True, slots=True)
class BackendStatus:
    """What `doctor` learned by asking a profile's ``base_url`` directly.

    ``models`` is None when the server answered but offers no model listing the
    probe understands — reachable, but the tiers could not be verified.
    """

    reachable: bool
    detail: str
    models: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class ToolCallStatus:
    """Whether a model, asked through the backend's Anthropic endpoint to call a
    tool, answered with a real ``tool_use`` block. ``supported`` is None when the
    question could not be put (an HTTP error, a timeout)."""

    supported: bool | None
    detail: str
