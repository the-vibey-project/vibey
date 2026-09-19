# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Append-only forecast and billing-ledger adapters.

The forecast ledger is intentionally separate from GitHub's mutable issue
objects.  Each record carries a source fingerprint and a digest-linked
predecessor, so a human can inspect how an estimate changed and a refresh can
be idempotent when nothing changed.  A conductor ledger export can be supplied
as the billing source; its spend fields are interpreted with the same names as
``LedgerSpendRule``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, cast

from vibey_gh.delivery_estimate import BillingUsage
from vibey_gh.interfaces.delivery_estimate_interface import (
    BillingLedgerReaderInterface,
    BillingLedgerSnapshotInterface,
    DeliveryEstimateLedgerInterface,
    DeliveryForecastInterface,
)

__all__ = [
    "DEFAULT_ESTIMATE_LEDGER",
    "DEFAULT_ESTIMATE_REPORT",
    "DELIVERY_ESTIMATE_LEDGER_FORMAT",
    "BillingLedgerReader",
    "BillingLedgerSnapshot",
    "DeliveryEstimateLedger",
]

DELIVERY_ESTIMATE_LEDGER_FORMAT: Final = "vibey-delivery-estimate-ledger/v1"
DEFAULT_ESTIMATE_LEDGER: Final = Path(".vibey/delivery-estimates.jsonl")
DEFAULT_ESTIMATE_REPORT: Final = Path("docs/estimate.md")
_GENESIS: Final = "0" * 64


@dataclass(frozen=True, slots=True)
class BillingLedgerSnapshot(BillingLedgerSnapshotInterface):
    usage: BillingUsage
    problems: tuple[str, ...] = ()


class BillingLedgerReader(BillingLedgerReaderInterface):
    """Reads a core ledger export without treating absent data as zero spend."""

    def read(self, path: Path) -> BillingLedgerSnapshot:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return BillingLedgerSnapshot(
                usage=BillingUsage(),
                problems=(f"billing ledger unavailable at {path}: {exc}",),
            )
        events: list[Mapping[str, object]] = []
        problems: list[str] = []
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"billing ledger line {number}: invalid JSON ({exc.msg})")
                continue
            if isinstance(value, Mapping) and "shard" in value:
                continue
            if not isinstance(value, Mapping):
                problems.append(f"billing ledger line {number}: expected an object")
                continue
            events.append(value)
        if not events:
            if lines and not problems:
                problems.append("billing ledger contains no event records")
            return BillingLedgerSnapshot(usage=BillingUsage(), problems=tuple(problems))
        usage = self._usage(events)
        return BillingLedgerSnapshot(usage=usage, problems=tuple(problems))

    @classmethod
    def _usage(cls, events: list[Mapping[str, object]]) -> BillingUsage:
        dollars = 0.0
        spend_events = 0
        turn_completed_events = 0
        budget_turns = 0
        phase_transitions = 0
        capacity_rejections = 0
        handoffs = 0
        tools = 0
        files = 0
        artifacts = 0
        moments: list[datetime] = []
        for event in events:
            kind = str(event.get("kind", ""))
            payload = event.get("payload")
            body = payload if isinstance(payload, Mapping) else {}
            if kind == "TurnCompleted":
                spend_events += 1
                turn_completed_events += 1
                dollars += cls._number(body.get("cost_usd"))
            elif kind == "BudgetSpent":
                spend_events += 1
                dollars += cls._number(body.get("dollars"))
                turns = body.get("turns")
                if isinstance(turns, int) and not isinstance(turns, bool):
                    budget_turns += turns
            elif kind == "PhaseTransitioned":
                phase_transitions += 1
            elif kind == "CapacityRejected":
                capacity_rejections += 1
            elif kind == "HandoffInitiated":
                handoffs += 1
            elif kind == "ToolInvoked":
                tools += 1
            elif kind == "FileEdited":
                files += 1
            elif kind == "ArtifactProduced":
                artifacts += 1
            moment = cls._moment(event.get("produced_at"))
            if moment is not None:
                moments.append(moment)
        elapsed = (max(moments) - min(moments)).total_seconds() if moments else None
        return BillingUsage(
            elapsed_seconds=elapsed,
            dollars=dollars if spend_events else None,
            turn_completed_events=turn_completed_events,
            budget_turns=budget_turns,
            ledger_events=len(events),
            phase_transition_events=phase_transitions,
            capacity_rejections=capacity_rejections,
            handoffs=handoffs,
            tool_invocations=tools,
            file_edits=files,
            artifacts_produced=artifacts,
        )

    @staticmethod
    def _number(value: object) -> float:
        return (
            float(value) if isinstance(value, int | float) and not isinstance(value, bool) else 0.0
        )

    @staticmethod
    def _moment(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            moment = datetime.fromisoformat(value)
        except ValueError:
            return None
        return moment if moment.tzinfo is not None and moment.utcoffset() is not None else None


class DeliveryEstimateLedger(DeliveryEstimateLedgerInterface):
    """Reads, appends and renders the repository's forecast ledger."""

    def read(self, path: Path) -> tuple[Mapping[str, object], ...]:
        return tuple(
            cast(Mapping[str, object], record["payload"]) for record in self._records(path)
        )

    def record(self, forecast: DeliveryForecastInterface, path: Path) -> bool:
        records = self._records(path)
        payload = dict(forecast.event_payload())
        input_digest = _digest(
            {key: value for key, value in payload.items() if key != "recorded_at"}
        )
        if any(self._input_digest(record) == input_digest for record in records):
            return False
        previous = records[-1] if records else None
        seq = 1 if previous is None else self._integer(previous.get("seq"), "seq") + 1
        previous_digest = _text(previous.get("digest"), "digest") if previous else _GENESIS
        envelope: dict[str, object] = {
            "format": DELIVERY_ESTIMATE_LEDGER_FORMAT,
            "seq": seq,
            "kind": "DeliveryEstimateRecorded",
            "produced_at": forecast.recorded_at,
            "source_fingerprint": forecast.source_fingerprint,
            "input_digest": input_digest,
            "previous_digest": previous_digest,
            "payload": payload,
        }
        envelope["digest"] = _digest(envelope)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n")
        return True

    def write_report(self, forecast: DeliveryForecastInterface, path: Path) -> None:
        document = [
            "# Continuous delivery estimate",
            "",
            (
                "This page is a generated, append-only-ledger-backed forecast. Re-run "
                "`vibey-gh forecast` after changes to refresh it."
            ),
            "",
            f"- Recorded at: `{forecast.recorded_at}`",
            f"- Source fingerprint: `{forecast.source_fingerprint}`",
            "",
            "## Current estimate",
            "",
            *[f"- {line.removeprefix('vibey-gh forecast: ')}" for line in forecast.lines()],
            "",
            "## Full machine-readable record",
            "",
            "```json",
            json.dumps(forecast.as_dict(), indent=2, sort_keys=True),
            "```",
            "",
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(document), encoding="utf-8")

    def _records(self, path: Path) -> tuple[Mapping[str, object], ...]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise ValueError(f"cannot read estimate ledger {path}: {exc}") from exc
        records: list[Mapping[str, object]] = []
        expected_previous = _GENESIS
        expected_seq = 1
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"estimate ledger line {number} is not JSON: {exc.msg}") from exc
            if not isinstance(value, Mapping):
                raise TypeError(f"estimate ledger line {number} is not an object")
            seq = self._integer(value.get("seq"), "seq")
            if seq != expected_seq:
                raise ValueError(
                    f"estimate ledger line {number} has seq {seq}, expected {expected_seq}"
                )
            previous = _text(value.get("previous_digest"), "previous_digest")
            if previous != expected_previous:
                raise ValueError(f"estimate ledger line {number} breaks the digest chain")
            payload = value.get("payload")
            if not isinstance(payload, Mapping):
                raise TypeError(f"estimate ledger line {number} has no object payload")
            digest = _text(value.get("digest"), "digest")
            if digest != _digest({key: item for key, item in value.items() if key != "digest"}):
                raise ValueError(f"estimate ledger line {number} has an invalid digest")
            records.append(value)
            expected_previous, expected_seq = digest, seq + 1
        return tuple(records)

    @staticmethod
    def _integer(value: object, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"estimate ledger {field} must be an integer")
        return value

    @staticmethod
    def _input_digest(record: Mapping[str, object]) -> str | None:
        stored = record.get("input_digest")
        if isinstance(stored, str):
            return stored
        payload = record.get("payload")
        if not isinstance(payload, Mapping):
            return None
        return _digest({key: value for key, value in payload.items() if key != "recorded_at"})


def _text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"estimate ledger {field} must be text")
    return value


def _digest(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
