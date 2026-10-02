"""Stage 1 -- screening on verdict and time (PREREGISTRATION §6.1).

Arms on the four S1 hosts, host-major so every arm is seen early; an arm is dropped as
soon as it fails one host (the registered rule: ≥ 1 failure of 4 gives a Wilson upper
bound < 0.95), and its remaining hosts are not run.
"""

from __future__ import annotations

import json
import sys

from arms import DiffLedger, run_case
from cases import CaseBook
from client import Model

ARMS = [
    "D8-T1",
    "D16-T1",
    "D16-BF4096",
    "D8",
    "D16",
    "A2",
    "A0",
    "A1",
    "D16-T1-BF8192",
    "D4-T1",
    "D32-T1",
    "D4",
    "D32",
]


def main(argv: list[str]) -> int:
    arms = argv[1:] or ARMS
    book = CaseBook()
    model = Model()
    ledger = DiffLedger()
    dropped: set[str] = set()
    for host in book.selection["screen_hosts_s1"]:
        case = book.host(host)
        for arm in arms:
            if arm in dropped:
                continue
            row = run_case("s1", arm, case, model, ledger, fail_fast=True)
            if row is None:
                continue
            print(
                json.dumps(
                    {
                        k: row.get(k)
                        for k in (
                            "arm",
                            "case_id",
                            "code",
                            "wall_s",
                            "parts",
                            "forced",
                            "elapsed_s",
                        )
                    }
                ),
                flush=True,
            )
            if row["verdict"] is None:
                dropped.add(arm)
                print(
                    f"[stage1] {arm} dropped: no verdict on host {host} ({row['code']})", flush=True
                )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
