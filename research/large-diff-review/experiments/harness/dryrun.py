"""Offline dry run: sizes every arm's requests for a case without asking the model."""

import sys
from pathlib import Path

from cases import CaseBook
from client import Model, RequestStore
from review import DecoupledArm, DecoupledConfig, ProductionArm

book = CaseBook()
store = RequestStore(Path(__file__).resolve().parents[1] / "results" / "scratch" / "dry.jsonl")
model = Model(store)
for n in [int(x) for x in sys.argv[1:]] or book.selection["screen_hosts_s1"]:
    case = book.host(n)
    print(f"host {n}: {len(case.diff)} chars, {len(case.sources)} sources")
    for k in (4096, 8192, 16384, 32768):
        for tri in (False, True):
            arm = DecoupledArm(
                DecoupledConfig(f"D{k // 1024}", k_tokens=k, triage=tri), model, offline=True
            )
            reqs = arm.part_requests(case)
            sizes = [sum(len(m["content"]) for m in p["messages"]) // 3 for _, p, _ in reqs]
            print(
                f"  D{k // 1024}{'+TRI' if tri else ''}: {len(reqs)} parts, prompt tok est sum={sum(sizes)} max={max(sizes) if sizes else 0}"
            )
    cp = arm.contract_payload(case)
    print("  contract prompt tok est", sum(len(m["content"]) for m in cp["messages"]) // 3)
    res = ProductionArm("A0", model, offline=True).review(case)
    print("  A0 offline:", res.code, len(res.keys))
