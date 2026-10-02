"""One row per run of the `Sovereign diff review` job of .github/workflows/pr-review.yml.

Sources (all copied under evidence/raw/gh/, fetched 2026-10-01 ~21:40Z):
  runs.json            gh run list --workflow pr-review.yml -L 1000 (559 runs, 2026-09-21..10-01)
  jobs/<run>.json      GET /actions/runs/<run>/jobs (step timestamps and conclusions)
  joblogs/<job>.log    GET /actions/jobs/<job>/logs (404 -> <job>.err: never started or expired)
  artifacts/pr-review-sovereign-<pr>-<run>/{verdict,outcome}.json   the job's own records
  diffs/<pr>-<sha>.diff.gz   GitHub compare develop...<head_sha> (see fetch_diffs.py)

Every completed, non-skipped Sovereign job is a row; a job whose log could not be fetched is
kept with log_available=false rather than dropped. Settings are read from the command the log
echoes (the workflow at that run's ref), not assumed from today's file.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parent
GH = EVIDENCE / "raw" / "gh"
STAMP = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z) ?(.*)$")
FLAGS = {
    "model": r"--model '?([^' \\]+)",
    "max_chars": r"--max-chars (\d+)",
    "max_document_chars": r"--max-document-chars (\d+)",
    "timeout": r"--timeout (\d+)",
    "context_window": r"--context-window (\d+)",
    "reasoning_reserve": r"--reasoning-reserve (\d+)",
    "chars_per_token": r"--chars-per-token (\d+)",
    "think": r"--think '([^']*)'",
    "max_chunks": r"--max-chunks (\d+)",
    "retries": r"--retries (\d+)",
    "retry_backoff_seconds": r"--retry-backoff-seconds (\d+)",
    "prompt_tokens_per_second": r"--prompt-tokens-per-second (\d+)",
    "output_tokens_per_second": r"--output-tokens-per-second (\d+)",
    "slot_wait_seconds": r"--slot-wait-seconds (\d+)",
}


def classify(
    reason: str, has_verdict: bool, step_conclusion: str | None, job_conclusion: str
) -> str:
    r = reason or ""
    if has_verdict:
        return "reviewed"
    if "done_reason=length" in r or "ran out of room" in r:
        return "answer_incomplete_length"
    if "stopped without finishing" in r or "reasoning (" in r and "but no answer" in r:
        return "answer_incomplete"
    if "busy" in r:
        return "model_busy"
    if "timed out" in r:
        return "model_timeout"
    if "unreachable" in r:
        return "model_unreachable"
    if "unusable response" in r:
        return "answer_unusable"
    if "exceeds the sovereign model's window" in r:
        return "diff_exceeds_window"
    if "max_chunks allows" in r:
        return "chunk_budget_exceeded"
    if "is larger than one part may carry" in r:
        return "diff_exceeds_window_hunk"
    if "prompt_eval_count" in r:
        return "prompt_truncated"
    if "empty diff" in r:
        return "empty_diff"
    if job_conclusion == "cancelled":
        return "cancelled"
    if step_conclusion in (None, "skipped"):
        return "job_failed_before_review"
    return "job_failed"


def review_segment(lines: list[str]):
    start = next((i for i, ln in enumerate(lines) if "vibey-gh local-review" in ln), None)
    if start is None:
        return None, [], ""
    command = []
    i = start
    while i < len(lines) and "##[endgroup]" not in lines[i]:
        command.append(lines[i])
        i += 1
    out = []
    for ln in lines[i + 1 :]:
        if "##[group]" in ln:
            break
        out.append(ln)
    return start, out, "\n".join(command)


def main() -> int:
    runs = {r["databaseId"]: r for r in json.loads((GH / "runs.json").read_text())}
    rows = []
    for path in sorted((GH / "jobs").glob("*.json")):
        for job in json.loads(path.read_text())["jobs"]:
            if (
                job["name"] != "Sovereign diff review"
                or job["conclusion"] == "skipped"
                or job["status"] != "completed"
            ):
                continue
            run = runs[job["run_id"]]
            steps = {s["name"]: s for s in job.get("steps") or []}
            step = steps.get("Review with the local model") or {}
            row = {
                "source": f"gh:run/{job['run_id']}/job/{job['id']}",
                "run_id": job["run_id"],
                "job_id": job["id"],
                "run_attempt": run["attempt"],
                "run_created_at": run["createdAt"],
                "run_head_sha": run["headSha"],
                "job_started_at": job["started_at"],
                "job_completed_at": job["completed_at"],
                "job_conclusion": job["conclusion"],
                "runner": job.get("runner_name"),
                "review_step_started_at": step.get("started_at"),
                "review_step_completed_at": step.get("completed_at"),
                "review_step_conclusion": step.get("conclusion"),
            }
            log = GH / "joblogs" / f"{job['id']}.log"
            lines = (
                log.read_text(encoding="utf-8", errors="replace").splitlines()
                if log.exists() and log.stat().st_size
                else []
            )
            if not any(STAMP.match(ln) for ln in lines[:5]):
                lines = []  # the API answered 404 (job never started, or its log expired)
            row["log_available"] = bool(lines)
            text = [STAMP.match(ln).group(2) if STAMP.match(ln) else ln for ln in lines]
            env = {}
            for t in text:
                m = re.match(
                    r"^\s+(PR|HEAD_SHA|ROLE|SCOPE|SOURCE_CONTEXT|MAX_SOURCE_CHARS|PATHS): (.*)$", t
                )
                if m and m.group(1) not in env:
                    env[m.group(1)] = m.group(2).strip()
            row["pr"] = int(env["PR"]) if env.get("PR", "").isdigit() else None
            row["head_sha"] = env.get("HEAD_SHA")
            row["role"], row["scope"] = env.get("ROLE"), env.get("SCOPE") or None
            row["source_context"] = env.get("SOURCE_CONTEXT")
            start, out, command = review_segment(text)
            settings = {}
            for key, pattern in FLAGS.items():
                m = re.search(pattern, command)
                settings[key] = (
                    (m.group(1) if key in ("model", "think") else int(m.group(1))) if m else None
                )
            settings["split_added_hunks"] = "--split-added-hunks" in command if command else None
            settings["source_dir"] = "--source-dir" in command if command else None
            row["settings"] = settings
            row["fetched_sources"] = sum(
                1 for t in text if t.startswith("fetched ") and " at " in t
            )
            reason = ""
            for t in out:
                m = re.match(r"^##\[warning\]the sovereign lane produced no verdict: (.*)$", t)
                if m:
                    reason = m.group(1)
            # The warning is cut at 300 characters (the workflow's `cut -c1-300`); the full
            # line is the stderr the step echoes just before it, so prefer that.
            plain = [
                t
                for t in out
                if t.strip()
                and not t.startswith("##[")
                and not t.lstrip().startswith(("{", "}", '"'))
            ]
            for t in plain:
                if reason and t.startswith(reason[:120]) and len(t) > len(reason):
                    reason = t
            if not reason and plain:
                reason = plain[-1]
            row["reason"] = reason or None
            # The job's own records, when its artifact survived.
            art = GH / "artifacts" / f"pr-review-sovereign-{row['pr']}-{job['run_id']}"
            verdict = outcome = None
            if (art / "verdict.json").exists() and (art / "verdict.json").stat().st_size:
                try:
                    verdict = json.loads((art / "verdict.json").read_text())
                except json.JSONDecodeError:
                    verdict = None
            if (art / "outcome.json").exists():
                outcome = json.loads((art / "outcome.json").read_text())
            if verdict is None and out:
                blob = "\n".join(t for t in out if not t.startswith("##["))
                i = blob.find("{")
                if i >= 0:
                    try:
                        verdict = json.JSONDecoder().raw_decode(blob[i:])[0]
                    except json.JSONDecodeError:
                        verdict = None
            has_verdict = isinstance(verdict, dict) and "pass" in verdict
            row["outcome_record"] = outcome
            row["code_derived"] = classify(
                reason, has_verdict, step.get("conclusion"), job["conclusion"]
            )
            row["code"] = (outcome or {}).get("code") or row["code_derived"]
            row["parts"] = (outcome or {}).get("parts") or (verdict or {}).get("parts")
            row["attempts"] = (outcome or {}).get("attempts")
            m = re.search(r"part (\d+) of (\d+)", reason)
            row["failed_part"], row["parts_from_reason"] = (
                (int(m.group(1)), int(m.group(2))) if m else (None, None)
            )
            m = re.search(r"\((\d+) attempts?\)", reason)
            if m and row["attempts"] is None:
                row["attempts"] = int(m.group(1))
            m = re.search(r"(\d+) reasoning chars, (\d+) answer chars", reason)
            row["reasoning_chars"], row["answer_chars"] = (
                (int(m.group(1)), int(m.group(2))) if m else (None, None)
            )
            m = re.search(
                r"the diff \(~(\d+) tokens\) exceeds the sovereign model's window \((\d+) tokens\) once its ~(\d+) tokens",
                reason,
            )
            row["window_refusal"] = (
                {
                    "diff_tokens_est": int(m.group(1)),
                    "window": int(m.group(2)),
                    "instruction_tokens_est": int(m.group(3)),
                }
                if m
                else None
            )
            m = re.search(
                r"the diff \((\d+) characters\) needs (\d+) parts of at most (\d+) characters",
                reason,
            )
            row["chunk_refusal"] = (
                {
                    "diff_chars": int(m.group(1)),
                    "parts_needed": int(m.group(2)),
                    "part_chars": int(m.group(3)),
                }
                if m
                else None
            )
            row["verdict_pass"] = verdict.get("pass") if has_verdict else None
            row["findings"] = len(verdict.get("findings") or []) if has_verdict else None
            row["verdict_flags"] = (
                {
                    k: verdict.get(k)
                    for k in ("accurate", "complete", "human_readable", "opening_accessible")
                }
                if has_verdict
                else None
            )
            row["verdict_truncation"] = (
                {k: verdict[k] for k in verdict if "trunc" in k or "omit" in k or "cut" in k}
                if has_verdict
                else None
            )
            if row["review_step_started_at"] and row["review_step_completed_at"]:
                from datetime import datetime

                a = datetime.fromisoformat(row["review_step_started_at"].replace("Z", "+00:00"))
                b = datetime.fromisoformat(row["review_step_completed_at"].replace("Z", "+00:00"))
                row["review_step_seconds"] = (b - a).total_seconds()
            else:
                row["review_step_seconds"] = None
            # Diff statistics, when the diff at the reviewed head was fetched.
            dstats = EVIDENCE / "raw" / "gh" / "diffs" / f"{row['pr']}-{row['head_sha']}.stats.json"
            row["diff"] = json.loads(dstats.read_text()) if dstats.exists() else None
            row["diff_chars_logged"] = (row["chunk_refusal"] or {}).get("diff_chars")
            rows.append(row)
    rows.sort(key=lambda r: r["job_started_at"] or "")
    with open(EVIDENCE / "dataset-reviews.jsonl", "w", encoding="utf-8") as handle:
        for r in rows:
            handle.write(json.dumps(r, sort_keys=True) + "\n")
    summary = {
        "rows": len(rows),
        "with_log": sum(r["log_available"] for r in rows),
        "span": [rows[0]["job_started_at"], rows[-1]["job_started_at"]],
        "codes": Counter(r["code"] for r in rows).most_common(),
        "codes_derived_vs_record": Counter(
            (r["code_derived"], (r["outcome_record"] or {}).get("code")) for r in rows
        ).most_common(),
        "with_diff_stats": sum(1 for r in rows if r["diff"]),
        "diff_size_validation": [
            {
                "pr": r["pr"],
                "logged_chars": r["diff_chars_logged"],
                "fetched_chars": (r["diff"] or {}).get("chars"),
            }
            for r in rows
            if r["diff_chars_logged"]
        ],
    }
    (HERE / "parse_reviews.summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
