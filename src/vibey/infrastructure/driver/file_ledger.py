# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The driver's append-only ledger (ADR-0070): one JSON line per record under
`<worktree>/.vibey/driver/ledger.jsonl`.

The driver is a Claude Code session, not a vibey project, so its failover is recorded
beside the worktree it steers rather than in the Postgres ledger. The rules are the
ledger's own: a line is only ever appended (opened `a`, never rewritten), each line
carries its sequence number and the SHA-256 of the line before it, and an append is
flushed and fsynced before the caller starts the process it describes. Two writers --
the hook and the timer -- take an exclusive `flock` around the read of the last line
and the append, so a sequence number is never issued twice.
"""

import fcntl
import hashlib
import json
import os
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from vibey.domain.failover import FAILOVER_POLICY, FailoverKind, FailoverRecord
from vibey.domain.interfaces.failover_interface import FailoverPolicyInterface

GENESIS = "0" * 64


class JsonlDriverLedger:
    """Declared by `interfaces/file_ledger_interface.py`; satisfies `DriverLedgerPort`."""

    def __init__(self, path: Path, *, policy: FailoverPolicyInterface = FAILOVER_POLICY) -> None:
        self._path = path
        self._policy = policy

    def records(self) -> tuple[FailoverRecord, ...]:
        return self._policy.read_rows(self._rows())

    def append(self, kind: FailoverKind, *, at: datetime, payload: Mapping[str, object]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            lines = [line for line in handle.read().splitlines() if line.strip()]
            prev = hashlib.sha256(lines[-1].encode()).hexdigest() if lines else GENESIS
            line = json.dumps(
                {
                    "seq": len(lines) + 1,
                    "prev": prev,
                    "kind": kind.value,
                    "at": at.isoformat(),
                    "trusted": True,
                    "payload": dict(payload),
                },
                sort_keys=True,
            )
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def verify_chain(self) -> bool:
        """Every line names the digest of the line before it, from the genesis."""
        prev = GENESIS
        for number, raw in enumerate(self._lines(), start=1):
            row = json.loads(raw)
            if row.get("seq") != number or row.get("prev") != prev:
                return False
            prev = hashlib.sha256(raw.encode()).hexdigest()
        return True

    def _lines(self) -> list[str]:
        if not self._path.exists():
            return []
        return [
            line for line in self._path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]

    def _rows(self) -> list[Mapping[str, object]]:
        rows: list[Mapping[str, object]] = []
        for raw in self._lines():
            try:
                row = json.loads(raw)
            except ValueError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows
