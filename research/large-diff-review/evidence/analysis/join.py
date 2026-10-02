"""Join Ollama requests to the review that sent them; label every request with its workload.

Inputs: dataset-ollama.jsonl (parse_ollama.py), dataset-reviews.jsonl (parse_reviews.py).
Outputs: both datasets rewritten in place with join fields, and analysis/join.summary.json.

A request belongs to a CI review when it ran inside that job's `Review with the local model`
step (access-line start >= step start - 10 s, end <= step end + 10 s), is a gpt-oss:20b
/api/chat request, and came from client ::1. The address rule is evidence-derived, not assumed:
without it, every request in a job window that came from ::1 matched a job (134/134), while the
127.0.0.1 requests that fell inside job windows were the host's own concurrent runs (the local
studies 2026-09-30/10-01 and an unidentified host process from 2026-10-01 16:38 local onward,
which sends its own one-token probes). `ci_unmatched_v6` in the summary counts ::1 requests
that no job window covers.

Local studies (docs/architecture/evidence/review-lane-2026-10-01.json) ran on the host itself:
  think_study  "2026-09-30T22:08 to 2026-10-01T00:01 America/New_York", --think low then medium
  source_study "2026-10-01, finished 02:18 America/New_York", default effort, with sources
Their requests are labelled by client 127.0.0.1 and these windows (boundaries read off the
request sequence: the 8 low-effort requests end 22:41:41, the medium pass starts 22:41:42).
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parent
UTC = dt.UTC
TZ = dt.timezone(dt.timedelta(hours=-4))
PR_1316_MERGED = dt.datetime(
    2026, 10, 1, 18, 16, 1, tzinfo=UTC
)  # 7f056017f, 2026-10-01T14:16:01-04:00
STUDY = [
    (
        "study_think_low",
        dt.datetime(2026, 9, 30, 22, 5, tzinfo=TZ),
        dt.datetime(2026, 9, 30, 22, 41, 42, tzinfo=TZ),
    ),
    (
        "study_think_medium",
        dt.datetime(2026, 9, 30, 22, 41, 42, tzinfo=TZ),
        dt.datetime(2026, 10, 1, 0, 2, tzinfo=TZ),
    ),
    (
        "study_source",
        dt.datetime(2026, 10, 1, 0, 2, tzinfo=TZ),
        dt.datetime(2026, 10, 1, 2, 20, tzinfo=TZ),
    ),
]
SMALL_CTX = {4096, 8192, 131072}


def ts(text):
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def load(name):
    return [json.loads(ln) for ln in (EVIDENCE / name).read_text(encoding="utf-8").splitlines()]


def main() -> int:
    ollama = load("dataset-ollama.jsonl")
    reviews = load("dataset-reviews.jsonl")
    for r in ollama:
        for k in (
            "workload",
            "ci_job_id",
            "ci_run_id",
            "ci_pr",
            "ci_settings_reserve",
            "ci_settings_timeout",
            "ci_settings_think",
            "ci_after_1316",
            "is_probe",
        ):
            r[k] = None
    tasks = [r for r in ollama if r["end_kind"] != "no_task" and r["gin_start_utc"]]
    for r in ollama:
        if r["end_kind"] != "no_task" and not r["gin_start_utc"]:
            r["workload"] = "unjoined"
    for r in ollama:
        r["is_probe"] = bool(
            r["end_kind"] != "no_task"
            and (r["generated_tokens"] or 0) <= 1
            and (r["prompt_tokens"] or 0) < 500
        )
    # The log's coverage: per file, first to last access line (server restarts leave gaps).
    parsed = json.loads((HERE / "parse_ollama.summary.json").read_text())
    spans = {f: [ts(a), ts(b)] for f, (a, b) in parsed["file_time_spans_local"].items()}
    claimed = set()
    for rev in reviews:
        rev["ollama_sources"] = []
        a, b = ts(rev["review_step_started_at"]), ts(rev["review_step_completed_at"])
        if not a or not b:
            continue
        lo, hi = a - dt.timedelta(seconds=10), b + dt.timedelta(seconds=10)
        for r in tasks:
            if (
                r["model"] != "gpt-oss:20b"
                or r["gin_path"] != "/api/chat"
                or id(r) in claimed
                or r["gin_client"] != "::1"
            ):
                continue
            if ts(r["gin_start_utc"]) >= lo and ts(r["gin_end_utc"]) <= hi:
                claimed.add(id(r))
                s = rev["settings"] or {}
                r.update(
                    {
                        "workload": "ci_probe" if r["is_probe"] else "ci_review",
                        "ci_job_id": rev["job_id"],
                        "ci_run_id": rev["run_id"],
                        "ci_pr": rev["pr"],
                        "ci_settings_reserve": s.get("reasoning_reserve"),
                        "ci_settings_timeout": s.get("timeout"),
                        "ci_settings_think": s.get("think"),
                        "ci_after_1316": ts(r["gin_start_utc"]) >= PR_1316_MERGED,
                    }
                )
                rev["ollama_sources"].append(r["source"])
        # Also count no-task access lines (load failures, aborts) in the window.
        rev["ollama_no_task_in_window"] = sum(
            1
            for r in ollama
            if r["end_kind"] == "no_task"
            and r["gin_path"] == "/api/chat"
            and lo <= ts(r["gin_start_utc"])
            and ts(r["gin_end_utc"]) <= hi
        )
        mine = [r for r in tasks if r["source"] in set(rev["ollama_sources"]) and not r["is_probe"]]
        rev["ollama_join"] = (
            {
                "requests": len(mine),
                "probes": sum(
                    1 for r in tasks if r["source"] in set(rev["ollama_sources"]) and r["is_probe"]
                ),
                "prompt_tokens": [r["prompt_tokens"] for r in mine],
                "generated_tokens": [r["generated_tokens"] for r in mine],
                "end_kinds": [r["end_kind"] for r in mine],
                "n_ctx_slot": [r["n_ctx_slot"] for r in mine],
                "wait_s": [r["wait_s"] for r in mine],
                "gin_duration_s": [r["gin_duration_s"] for r in mine],
            }
            if rev["ollama_sources"]
            else None
        )
        rev["ollama_log_covers"] = any(f_lo <= a and b <= f_hi for f_lo, f_hi in spans.values())
    for r in tasks:
        if r["workload"]:
            continue
        start = ts(r["gin_start_utc"])
        label = None
        if start is None:
            r["workload"] = "unjoined"
            continue
        if r["gin_client"] == "127.0.0.1" and r["gin_path"] == "/api/chat":
            for name, lo, hi in STUDY:
                if lo <= start < hi:
                    label = name
        if label is None:
            if (
                r["gin_path"] == "/api/chat"
                and r["model"] == "gpt-oss:20b"
                and r["n_ctx_slot"] not in SMALL_CTX
                and (r["prompt_tokens"] or 0) >= 1000
            ):
                label = "other_review_shaped"
            elif r["is_probe"]:
                label = "other_probe"
            else:
                label = "other"
        r["workload"] = label
    for r in ollama:
        if r["end_kind"] == "no_task":
            r["workload"] = "no_task"
    with open(EVIDENCE / "dataset-ollama.jsonl", "w", encoding="utf-8") as h:
        for r in ollama:
            h.write(json.dumps(r, sort_keys=True) + "\n")
    with open(EVIDENCE / "dataset-reviews.jsonl", "w", encoding="utf-8") as h:
        for r in reviews:
            h.write(json.dumps(r, sort_keys=True) + "\n")
    ci = [r for r in tasks if r["workload"] in ("ci_review", "ci_probe")]
    summary = {
        "log_coverage_utc": {k: [v[0].isoformat(), v[1].isoformat()] for k, v in spans.items()},
        "workloads": Counter(r["workload"] for r in ollama).most_common(),
        "ci_request_clients": Counter(r["gin_client"] for r in ci).most_common(),
        "ci_unmatched_v6": Counter(
            r["workload"]
            for r in tasks
            if r["gin_client"] == "::1" and r["workload"] not in ("ci_review", "ci_probe")
        ).most_common(),
        "review_shaped_unmatched_clients": Counter(
            r["gin_client"] for r in tasks if r["workload"] == "other_review_shaped"
        ).most_common(),
        "reviews_in_log_span": sum(1 for r in reviews if r.get("ollama_log_covers")),
        "reviews_in_log_span_with_requests": sum(
            1 for r in reviews if r.get("ollama_log_covers") and r["ollama_sources"]
        ),
        "reviews_in_log_span_by_code_and_joined": Counter(
            (r["code"], bool(r["ollama_sources"])) for r in reviews if r.get("ollama_log_covers")
        ).most_common(),
    }
    (HERE / "join.summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
