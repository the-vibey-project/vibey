"""Supplementary deterministic arm SA-only: what static analysis alone says about the canary
corpus, no model. A diagnostic counts when the change INTRODUCES it (present after, not
before, by rule code and message) on a line the change touches (± 2). Reported two ways:
any non-style diagnostic, and a class-specific rule set fixed below before looking."""

from __future__ import annotations

import json
import sys
from collections import Counter

from cases import CaseBook
from client import RESULTS
from review import STATIC
from vibey_gh import local_review as lr

# Style/documentation families that say nothing about correctness.
STYLE = (
    "D",
    "E",
    "W",
    "I",
    "N",
    "Q",
    "COM",
    "ANN",
    "ERA",
    "T20",
    "FBT",
    "EM",
    "TRY003",
    "PLR",
    "C90",
    "ARG",
    "UP",
    "RUF100",
    "CPY",
    "FA",
    "TD",
    "FIX",
    "INP",
    "PTH",
    "G",
    "SLF",
    "PIE790",
    "RET50",
    "SIM108",
    "PLC",
    "DTZ",
    "S101",
    "TC",
    "ISC",
    "BLE",
    "FURB",
)
CLASS_RULES = {
    "sql_injection": ("S608", "B608"),
    "swallowed_exception": (
        "S110",
        "S112",
        "B110",
        "B112",
        "SIM105",
        "BLE001",
        "TRY300",
        "PERF203",
        "S113",
    ),
    "resource_leak": ("SIM115",),
    "missing_await": ("RUF006", "ASYNC", "PLE1142"),
}


def code(said: str) -> str:
    return said.split(":", 1)[0].split(" ", 1)[1]


def style(c: str) -> bool:
    return any(c == s or (c.startswith(s) and c[len(s) :].isdigit()) for s in STYLE)


def main() -> int:
    book = CaseBook()
    rows = []
    for case in book.canary.cases:
        c = book.canary_case(case.id)
        path = case.path
        before = c.built.before
        after = c.built.after
        ranges = lr.SOURCE_CONTEXT.changed(c.diff).get(path, [])
        pre = Counter(said for _, said in STATIC.diagnostics(path, before))
        new = []
        for line, said in STATIC.diagnostics(path, after):
            if pre[said] > 0:
                pre[said] -= 1
                continue
            if any(a - 2 <= line <= b + 2 for a, b in ranges):
                new.append((line, said))
        codes = [code(s) for _, s in new]
        substantive = [x for x in codes if not style(x)]
        rules = CLASS_RULES.get(case.defect_class, ())
        classed = [x for x in codes if any(x == r or x.startswith(r) for r in rules)]
        rows.append(
            {
                "case": case.id,
                "kind": case.kind,
                "class": case.defect_class,
                "introduced": codes,
                "substantive": substantive,
                "class_hit": bool(classed),
            }
        )
    (RESULTS / "static_only.json").write_text(json.dumps(rows, indent=1))
    d = [r for r in rows if r["kind"] == "defect"]
    k = [r for r in rows if r["kind"] == "control"]
    print(
        "defects with a substantive new diagnostic:",
        sum(bool(r["substantive"]) for r in d),
        "/",
        len(d),
    )
    print("defects with a class-rule hit:", sum(r["class_hit"] for r in d), "/", len(d))
    print(
        "controls with a substantive new diagnostic:",
        sum(bool(r["substantive"]) for r in k),
        "/",
        len(k),
    )
    for r in rows:
        print(
            r["kind"][:4], r["class"][:14].ljust(14), r["case"][:40].ljust(40), r["substantive"][:6]
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
