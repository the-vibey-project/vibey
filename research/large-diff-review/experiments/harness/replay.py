"""Hm2 -- the mechanism replay: production's own request for #1312 part 1 (dev host) and
#1317 part 3 (holdout host; mechanism only -- completion and loop metrics are read, the
verdict content is not), at temperature 0 (twice: determinism) and at temperature 1.0 /
top_p 1.0 with seeds 1-5. Production deadline, production num_ctx and num_predict."""

from __future__ import annotations

import json
import sys

from cases import CaseBook
from client import Model
from review import ProductionPart

TARGETS = ((1312, 1), (1317, 3))
VARIANTS = [("T0", {}, 0), ("T0", {}, 1)] + [
    (f"T1s{s}", {"temperature": 1.0, "top_p": 1.0, "seed": s}, 0) for s in range(1, 6)
]


def main(argv: list[str]) -> int:
    book = CaseBook()
    model = Model()
    only = set(argv[1:])
    for name, options, rep in VARIANTS:
        for host, index in TARGETS:
            if only and f"{host}" not in only:
                continue
            part = ProductionPart(model, options).bodies(book.host(host))[index - 1]
            tag = {"stage": "hm2", "host": host, "part": index, "variant": name, "rep": rep}
            rec = model.ask("/api/chat", part["body"], part["deadline"], tag=tag, replicate=rep)
            keep = (
                "outcome",
                "done_reason",
                "prompt_tokens",
                "eval_tokens",
                "reasoning_chars",
                "answer_chars",
                "wall_s",
                "prompt_eval_s",
                "eval_s",
            )
            print(json.dumps({**tag, **{k: rec.get(k) for k in keep}}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
