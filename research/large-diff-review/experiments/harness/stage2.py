"""Stage 2 -- successive halving on recall and false positives, development data only.

Part-level, as registered: recall on the part of each dev needle case that carries the
needle (18 cases: 9 dev needles x 2 on the six S2 hosts, early/middle/late), and the
false-positive rate on a seeded sample of the S2 hosts' clean parts. Round 1 runs every
arm on half of each (hosts 1-3 of S2); round 2 the better half on all.

  stage2.py round1 ARM [ARM ...]     stage2.py round2 ARM [ARM ...]
"""

from __future__ import annotations

import json
import random
import sys

from arms import DiffLedger, make_arm
from cases import CaseBook
from client import Model, host_fingerprint
from review import needle_part, review_part, score

CLEAN_PER_HOST = 3
SEED = 20261005


def cases(book: CaseBook, round_: str):
    hosts = book.selection["halving_hosts_s2"]
    hosts = hosts[:3] if round_ == "round1" else hosts
    plan = book.needle_plan(hosts, book.selection["dev_needles"])
    return hosts, [book.needle_case(h, n, p) for h, n, p in plan]


def main(argv: list[str]) -> int:
    round_, arms = argv[1], argv[2:]
    book = CaseBook()
    model = Model()
    ledger = DiffLedger()
    hosts, needles = cases(book, round_)
    for name in arms:
        arm = make_arm(name, model)
        if not hasattr(arm, "part_requests"):
            from review import ProductionParts

            arm = ProductionParts(arm)
        for case in needles:
            cid = f"{case.case_id}#part"
            if ledger.done("s2", name, cid):
                continue
            label, payload, paths = needle_part(arm, case)
            res = review_part(arm, case, label, payload, paths)
            if res.missing:
                continue
            row = {
                "stage": "s2",
                "arm": name,
                "case_id": cid,
                "kind": "needle-part",
                "host": case.host,
                "needle": case.needle,
                "position": case.position,
                "class": case.meta["class"],
                "verdict": res.verdict,
                "code": res.code,
                "keys": res.keys,
                "wall_s": res.wall_s,
                "forced": int(res.forced),
                "host_fp": host_fingerprint()["id"],
            }
            row["score"] = score(case, res.verdict, res.code)
            ledger.add(row)
            print(
                json.dumps(
                    {k: row[k] for k in ("arm", "case_id", "code", "wall_s")}
                    | {"outcome": row["score"]["outcome"]}
                ),
                flush=True,
            )
        rng = random.Random(SEED)
        for number in hosts:
            host = book.host(number)
            parts = arm.part_requests(host)
            for label, payload, paths in rng.sample(parts, min(CLEAN_PER_HOST, len(parts))):
                cid = f"{host.case_id}#{label}"
                if ledger.done("s2", name, cid):
                    continue
                res = review_part(arm, host, label, payload, paths)
                if res.missing:
                    continue
                row = {
                    "stage": "s2",
                    "arm": name,
                    "case_id": cid,
                    "kind": "clean-part",
                    "host": number,
                    "verdict": res.verdict,
                    "code": res.code,
                    "keys": res.keys,
                    "wall_s": res.wall_s,
                    "forced": int(res.forced),
                    "host_fp": host_fingerprint()["id"],
                }
                row["score"] = score(host, res.verdict, res.code)
                ledger.add(row)
                print(
                    json.dumps(
                        {k: row[k] for k in ("arm", "case_id", "code", "wall_s")}
                        | {"outcome": row["score"]["outcome"]}
                    ),
                    flush=True,
                )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
