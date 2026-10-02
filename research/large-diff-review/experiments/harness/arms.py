"""The arm registry and the diff-level runner every stage uses.

A diff-level result is appended to results/diffs.jsonl as soon as it is known; a run
resumes by skipping (stage, arm, case) triples already there, and every request inside is
itself resumed from results/requests.jsonl.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cases import Case
from client import RESULTS, Model, host_fingerprint
from review import DecoupledArm, DecoupledConfig, ProductionArm, score

FORCE_FILE = RESULTS / "force_mode.txt"  # Stage 0's verdict on the mechanism (LOG.md)


def force_mode() -> str:
    return FORCE_FILE.read_text().strip() if FORCE_FILE.is_file() else "prefill"


def make_arm(name: str, model: Model, offline: bool = False):
    """Arms by name: A0, A1, A2, D<k>[-BF<R>][-low|-high][+TRI][+CTXnone|+CTXfile][@model]."""
    if name == "A0":
        return ProductionArm("A0", model, offline=offline)
    if name == "A1":
        return ProductionArm("A1", model, force=force_mode(), budget=4096, offline=offline)
    if name == "A2":
        return ProductionArm(
            "A2", model, options={"temperature": 1.0, "top_p": 1.0, "seed": 42}, offline=offline
        )
    if not name.startswith("D"):
        raise ValueError(name)
    spec, _, llm = name.partition("@")
    head, *flags = spec.split("+")
    bits = head.split("-")
    cfg = DecoupledConfig(name, k_tokens=int(bits[0][1:]) * 1024)
    for bit in bits[1:]:
        if bit.startswith("BF"):
            cfg.force, cfg.budget = force_mode(), int(bit[2:])
        elif bit in ("low", "medium", "high"):
            cfg.think = bit
        elif bit == "T1":
            cfg.options = {"temperature": 1.0, "top_p": 1.0, "seed": 42}
        else:
            raise ValueError(f"{name}: {bit}")
    for flag in flags:
        if flag == "TRI":
            cfg.triage = True
        elif flag.startswith("CTX"):
            cfg.context = flag[3:].lower()
        elif flag == "SA":
            cfg.static = True
        elif flag == "VER":
            cfg.verify = True
        elif flag == "FF":
            cfg.findings_first = True
        else:
            raise ValueError(f"{name}: {flag}")
    if llm:
        cfg.model = llm
    return DecoupledArm(cfg, model, offline=offline)


class DiffLedger:
    """results/diffs.jsonl: one line per (stage, arm, case) outcome."""

    def __init__(self, path: Path = RESULTS / "diffs.jsonl") -> None:
        self.path = path
        self.rows: list[dict[str, Any]] = []
        if path.is_file():
            self.rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def done(self, stage: str, arm: str, case_id: str) -> dict[str, Any] | None:
        for row in reversed(self.rows):
            if (row["stage"], row["arm"], row["case_id"]) == (stage, arm, case_id):
                return row
        return None

    def add(self, row: dict[str, Any]) -> None:
        with self.path.open("a") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        self.rows.append(row)


def run_case(
    stage: str,
    arm_name: str,
    case: Case,
    model: Model,
    ledger: DiffLedger,
    host_case: Case | None = None,
    offline: bool = False,
    fail_fast: bool = False,
) -> dict[str, Any] | None:
    found = ledger.done(stage, arm_name, case.case_id)
    if found is not None:
        return found
    arm = make_arm(arm_name, model, offline)
    started = time.time()
    if isinstance(arm, ProductionArm):
        res = arm.review(case)
        out = {
            "verdict": res.verdict,
            "code": res.code,
            "reason": res.reason,
            "keys": res.keys,
            "wall_s": res.wall_s,
            "forced": int(res.forced),
            "parts": len([k for k in res.keys]),
        }
        if res.missing:
            return None
    else:
        out = arm.review(case, host_case, fail_fast=fail_fast)
        if out["code"] == "missing":
            return None
    row = {
        "stage": stage,
        "arm": arm_name,
        "case_id": case.case_id,
        "kind": case.kind,
        "host": case.host,
        "needle": case.needle,
        "position": case.position,
        "chars": len(case.diff),
        "elapsed_s": round(time.time() - started, 1),
        "host_fp": host_fingerprint()["id"],
        **out,
    }
    row["score"] = score(case, out["verdict"], out["code"])
    ledger.add(row)
    return row
