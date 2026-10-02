"""Tables for LOG.md and REPORT.md, computed from the raw JSONL only.

analyze.py hm2 | s1 | s2 | s3 | requests
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

from client import RESULTS, RequestStore
from stats import LOOPS, PROPORTIONS


def fmt(p) -> str:
    est, lo, hi = p
    return "n/a" if est is None else f"{est:.2f} [{lo:.2f}, {hi:.2f}]"


def rows(stage: str) -> list[dict]:
    path = RESULTS / "diffs.jsonl"
    if not path.is_file():
        return []
    from arms import DiffLedger

    return [r for r in DiffLedger(path).rows if r["stage"] == stage]


def hm2() -> None:
    store = RequestStore()
    groups = defaultdict(list)
    for rec in store.records():
        tag = rec.get("tag") or {}
        if tag.get("stage") != "hm2":
            continue
        thinking = store.thinking(rec["key"])
        groups[(tag["host"], tag["part"], tag["variant"][:2])].append(
            {
                "variant": tag["variant"],
                "rep": tag.get("rep"),
                "outcome": rec["outcome"],
                "done": rec.get("done_reason"),
                "prompt": rec.get("prompt_tokens"),
                "eval": rec.get("eval_tokens"),
                "reasoning": rec.get("reasoning_chars"),
                "answer": rec.get("answer_chars"),
                "wall": rec.get("wall_s"),
                "loop200x3": LOOPS.substring_loop(thinking),
                "rep8": round(LOOPS.repeated_ngram_fraction(thinking) or 0, 3),
                "head": thinking[:0],
            }
        )
    for key, items in sorted(groups.items()):
        finished = sum(
            1 for i in items if i["outcome"] == "ok" and i["done"] == "stop" and i["answer"]
        )
        print(f"#{key[0]} part {key[1]} {key[2]}: finished {finished}/{len(items)}")
        for i in items:
            print("   ", json.dumps(i))


def s1() -> None:
    by_arm = defaultdict(list)
    for r in rows("s1"):
        by_arm[r["arm"]].append(r)
    print("| arm | verdicts | wall p50 (min) | wall max (min) | parts | forced | codes |")
    print("|---|---|---|---|---|---|---|")
    for arm, items in sorted(by_arm.items()):
        k = sum(1 for r in items if r["verdict"] is not None)
        walls = [r["wall_s"] / 60 for r in items]
        codes = sorted({r["code"] for r in items if r["verdict"] is None})
        p50 = PROPORTIONS.quantile(walls, 0.5)
        print(
            f"| {arm} | {k}/{len(items)} | {p50:.1f} | {max(walls):.1f} | "
            f"{sum(r['parts'] for r in items)} | {sum(r.get('forced', 0) for r in items)} | {', '.join(codes)} |"
        )


def s2() -> None:
    by_arm = defaultdict(list)
    for r in rows("s2"):
        by_arm[r["arm"]].append(r)
    print(
        "| arm | needle parts caught | recall (Wilson 95%) | clean parts blocked | FP/part | no verdict | mean min/req |"
    )
    print("|---|---|---|---|---|---|---|")
    for arm, items in sorted(by_arm.items()):
        needles = [r for r in items if r["kind"] == "needle-part"]
        clean = [r for r in items if r["kind"] == "clean-part"]
        nv = sum(1 for r in items if r["verdict"] is None)
        nd = [r for r in needles if r["verdict"] is not None]
        caught = sum(1 for r in nd if r["score"]["outcome"] == "caught")
        cl = [r for r in clean if r["verdict"] is not None]
        fp = sum(1 for r in cl if r["score"]["outcome"] == "false_positive")
        mean = sum(r["wall_s"] for r in items) / max(1, len(items)) / 60
        print(
            f"| {arm} | {caught}/{len(nd)} | {fmt(PROPORTIONS.wilson(caught, len(nd)))} | {fp}/{len(cl)} | "
            f"{fmt(PROPORTIONS.wilson(fp, len(cl)))} | {nv} | {mean:.1f} |"
        )


def requests() -> None:
    store = RequestStore()
    recs = store.records()
    print(len(recs), "requests;", round(sum(r["wall_s"] for r in recs) / 3600, 2), "model-hours")
    bands = defaultdict(lambda: [0, 0])
    for r in recs:
        if r.get("endpoint") != "/api/chat" or not r.get("prompt_tokens"):
            continue
        band = min(r["prompt_tokens"] // 8000, 7) * 8
        bands[band][1] += 1
        if r["outcome"] == "ok" and r.get("done_reason") == "stop" and r.get("answer_chars"):
            bands[band][0] += 1
    for band in sorted(bands):
        k, n = bands[band]
        print(
            f"prompt {band}k-{band + 8}k tokens: answered {k}/{n} {fmt(PROPORTIONS.wilson(k, n))}"
        )


if __name__ == "__main__":
    {"hm2": hm2, "s1": s1, "s2": s2, "requests": requests}[sys.argv[1]]()
