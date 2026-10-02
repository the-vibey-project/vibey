"""+CONS: re-score verdicts with the consistency rule (findings decide): pass := pass AND no
blocking/major finding. Also counts INCONSISTENT verdicts. Zero model cost.

  cons.py canary   -- on the canary lane's A0 verdicts (results/b0-canary)
"""

from __future__ import annotations

import json
import sys

from cases import CaseBook
from client import RESULTS
from review import score
from stats import PROPORTIONS

SEVERE = ("blocking", "major")


class Consistency:
    def inconsistent(self, verdict: dict, keywords=()) -> bool:
        if verdict is None or verdict.get("pass") is not True:
            return False
        severe = any(
            str(f.get("severity", "")).lower() in SEVERE for f in verdict.get("findings") or []
        )
        summary = str(verdict.get("summary", "")).lower()
        named = any(k.lower() in summary for k in keywords)
        return severe or named

    def apply(self, verdict: dict | None) -> dict | None:
        if verdict is None:
            return None
        out = dict(verdict)
        severe = any(
            str(f.get("severity", "")).lower() in SEVERE for f in verdict.get("findings") or []
        )
        out["pass"] = verdict.get("pass") is True and not severe
        return out


def canary() -> None:
    book = CaseBook()
    cons = Consistency()
    rows = [
        json.loads(line)
        for line in (RESULTS / "b0-canary" / "review-canary-smoke.work.jsonl")
        .read_text()
        .splitlines()
    ]
    tally = {
        "raw": [0, 0, 0, 0],
        "cons": [0, 0, 0, 0],
    }  # caught, defects judged, fp, controls judged
    inconsistent = 0
    per = []
    for row in rows:
        case = book.canary_case(row["case"])
        review = row["review"]
        verdict, code = review.get("verdict"), review.get("code")
        if verdict is None:
            continue
        inconsistent += cons.inconsistent(verdict, case.keywords)
        for name, v in (("raw", verdict), ("cons", cons.apply(verdict))):
            s = score(case, v, code)
            t = tally[name]
            if case.is_defect:
                t[0] += s["outcome"] == "caught"
                t[1] += 1
            else:
                t[2] += s["outcome"] == "false_positive"
                t[3] += 1
            if name == "cons":
                per.append((case.case_id, s["outcome"]))
    for name, (c, n, f, m) in tally.items():
        print(
            f"A0{'+CONS' if name == 'cons' else ''}: recall {c}/{n} {PROPORTIONS.wilson(c, n)[0]:.3f} "
            f"[{PROPORTIONS.wilson(c, n)[1]:.3f}, {PROPORTIONS.wilson(c, n)[2]:.3f}]; FP {f}/{m}"
        )
    print(
        "inconsistent verdicts (pass=true with a blocking/major finding or a class keyword in the summary):",
        inconsistent,
    )


if __name__ == "__main__":
    {"canary": canary}[sys.argv[1]]()
