"""Contention audit: which of the study's requests overlapped another client's request?

Ollama logs one access line per request at its END, with its duration and client address.
A request of ours is CONTENDED when another client's request overlapped it by more than a
few seconds (one slot: one of the two queued behind the other, so our timing -- and, for a
deadline, our outcome -- is not the model's own). Contended records are listed in
results/invalidations.jsonl; the store then ignores them (the records stay in the
append-only log) and the request is asked again.

  contention.py audit [--write]
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from client import RESULTS, RequestStore

LOGS = sorted((Path.home() / ".ollama" / "logs").glob("server*.log"))
GIN = re.compile(
    r"\[GIN\] (\d{4}/\d{2}/\d{2} - \d{2}:\d{2}:\d{2}) \| (\d{3}) \|\s+(\S+) \|\s+(\S+) \| POST\s+\"(/api/\w+)\""
)
UNITS = {"h": 3600.0, "m": 60.0, "s": 1.0, "ms": 1e-3, "µs": 1e-6, "us": 1e-6, "ns": 1e-9}


def seconds(text: str) -> float:
    total = 0.0
    for value, unit in re.findall(r"([\d.]+)(h|ms|µs|us|ns|m|s)", text):
        total += float(value) * UNITS[unit]
    return total


class Audit:
    def requests(self) -> list[dict]:
        found = []
        for log in LOGS:
            for line in log.read_text(errors="replace").splitlines():
                m = GIN.search(line)
                if not m:
                    continue
                end = datetime.strptime(m.group(1), "%Y/%m/%d - %H:%M:%S").timestamp()
                dur = seconds(m.group(3))
                found.append(
                    {
                        "end": end,
                        "start": end - dur,
                        "dur": dur,
                        "status": m.group(2),
                        "client": m.group(4),
                        "path": m.group(5),
                    }
                )
        return found

    def run(self, write: bool) -> list[dict]:
        store = RequestStore()
        mine = [r for r in store.records() if r.get("t_start")]
        server = self.requests()
        # Each of our records is matched to the server line that ended within 2 s of it.
        claimed = set()
        for r in mine:
            for i, s in enumerate(server):
                if i not in claimed and abs(s["end"] - r["t_end"]) <= 2.5 and s["dur"] > 0.5:
                    claimed.add(i)
                    break
        foreign = [s for i, s in enumerate(server) if i not in claimed and s["dur"] > 1.0]
        contended = []
        for r in mine:
            overlap = 0.0
            who = set()
            for s in foreign:
                # One slot, first come first served: a foreign request that began BEFORE ours
                # and was still running when ours began kept ours waiting. One that began
                # after ours waited behind ours, and our timing is our own.
                if s["start"] < r["t_start"] - 1.0 and s["end"] > r["t_start"] + 3.0:
                    overlap += min(r["t_end"], s["end"]) - r["t_start"]
                    who.add(s["client"])
            if overlap > 0:
                contended.append(
                    {
                        "key": r["key"],
                        "tag": r["tag"],
                        "overlap_s": round(overlap, 1),
                        "clients": sorted(who),
                        "outcome": r["outcome"],
                        "wall_s": r["wall_s"],
                    }
                )
        if write:
            path = RESULTS / "invalidations.jsonl"
            known = set()
            if path.is_file():
                known = {
                    (row["key"], row.get("t_start"))
                    for row in map(json.loads, filter(str.strip, path.read_text().splitlines()))
                }
            with path.open("a") as handle:
                for c in contended:
                    if (c["key"], c["t_start"]) not in known:
                        handle.write(
                            json.dumps({**c, "reason": "overlapped another client's request"})
                            + "\n"
                        )
            self.tombstone({c["key"] for c in contended})
        return contended

    def tombstone(self, keys: set[str]) -> None:
        """Void every diff row already written that used a voided request."""
        diffs, void = RESULTS / "diffs.jsonl", RESULTS / "void_rows.jsonl"
        if not diffs.is_file():
            return
        done = set()
        if void.is_file():
            done = {json.loads(x)["line"] for x in void.read_text().splitlines() if x.strip()}
        lines = [x for x in diffs.read_text().splitlines() if x.strip()]
        with void.open("a") as handle:
            for i, line in enumerate(lines):
                row = json.loads(line)
                if i not in done and keys.intersection(row.get("keys") or []):
                    handle.write(
                        json.dumps(
                            {
                                "line": i,
                                "stage": row["stage"],
                                "arm": row["arm"],
                                "case_id": row["case_id"],
                                "reason": "used a request the contention audit voided",
                            }
                        )
                        + "\n"
                    )


if __name__ == "__main__":
    out = Audit().run("--write" in sys.argv)
    for c in out:
        print(json.dumps(c))
    print(len(out), "contended")
