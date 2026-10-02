"""Parse the Ollama server logs (snapshot in evidence/raw/ollama) into one row per request.

Source: ~/.ollama/logs/server*.log of the operator's workstation (Apple M5, 24 GB), snapshot
copied gzipped into evidence/raw/ollama/ (MANIFEST holds sha256 prefix and line count; the
snapshot instant is SNAPSHOT_AT_UTC). Ollama 0.35.0 runs llama.cpp's llama-server per load,
so the log carries llama-server's slot records (no timestamps) interleaved with Ollama's GIN
access lines (local wall time, America/New_York, -04:00 for the whole span) and `time=` lines.

One row per llama-server *task* (a request that reached the slot), joined to the GIN access
line that closed it, plus one row per local-inference GIN line that never became a task (load
timeouts, client aborts during load). The whole snapshot is consumed; lines the parser does
not recognise are counted, by family, in the summary rather than dropped silently.

Derived fields and how they are defined:
  prompt_tokens      task.n_tokens at 'new prompt' (the whole prompt, cached or not)
  cached_tokens      the first 'cached n_tokens' after 'new prompt' (prefix reused from cache)
  eval_tokens        'eval time = ... / N tokens' (completed tasks only)
  generated_tokens   eval_tokens when present; else n_tokens at 'stop processing' minus
                     prompt_tokens (+1), floored at 0 -- the method used by
                     docs/architecture/evidence/review-lane-2026-10-01.json
  end_kind           'abandoned' the task never released: its runner was replaced or the
                                 server restarted while it ran (eviction / kill)
                     'stop'      completed with timing lines, not at a known cap
                     'length'    completed and generated_tokens == an inferred num_predict cap
                                 (2048, 4096, 8192 or 16384); 'length_ctx' when prompt +
                                 generated filled n_ctx (context full)
                     'cancelled' a 'cancel task' line for the task (client went away)
                     'no_task'   a GIN line for an inference endpoint that never reached a slot
  gin_*              the access line: end time, duration, status, endpoint, client
  wait_s             gin_duration - (llama-server load seconds if this request loaded it)
                     - task processing seconds: time queued in Ollama before the slot took it
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import pathlib
import re
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parent
RAW = EVIDENCE / "raw" / "ollama"
ORDER = [
    "server-5.log",
    "server-4.log",
    "server-3.log",
    "server-2.log",
    "server-1.log",
    "server.log",
]
TZ = dt.timezone(dt.timedelta(hours=-4))  # EDT; the span 2026-09-27..10-01 has no DST change
INFER = {
    '"/api/chat"',
    '"/api/generate"',
    '"/v1/chat/completions"',
    '"/v1/completions"',
    '"/v1/messages"',
    '"/v1/responses"',
    '"/api/codex/v1/responses"',
}
CAPS = (
    16384,
    8192,
    4096,
    2048,
)  # exactly a power of two >= 2048 is taken as a num_predict cap; 256 is not (think=low reviews stop there naturally)

GIN = re.compile(
    r"^\[GIN\] (\d{4}/\d\d/\d\d - \d\d:\d\d:\d\d) \| (\d{3}) \|\s+(\S+) \|\s+(\S+) \| (\w+)\s+(\S+)"
)
TIME = re.compile(r"^time=(\S+) level=(\w+) source=(\S+) msg=\"([^\"]*)\"(.*)$")
NEWPROMPT = re.compile(r"new prompt, n_ctx_slot = (\d+), n_keep = (\d+), task.n_tokens = (\d+)")
CACHED = re.compile(r"\| task (\d+) \| cached n_tokens = (\d+), memory_seq_rm")
PP = re.compile(
    r"prompt processing, n_tokens =\s+(\d+), progress = ([\d.]+), t =\s+([\d.]+) s / ([\d.]+) tokens per second"
)
NGEN = re.compile(r"n_gen =\s+(\d+), tg =\s+([\d.]+) t/s")
PEVAL = re.compile(r"prompt eval time =\s+([\d.]+) ms /\s+(\d+) tokens")
EVAL = re.compile(r"^slot print_timing: .*\|\s+eval time =\s+([\d.]+) ms /\s+(\d+) tokens")
TOTAL = re.compile(r"total time =\s+([\d.]+) ms /\s+(\d+) tokens")
RELEASE = re.compile(r"\| task (\d+) \| stop processing: n_tokens = (\d+), truncated = (\d+)")
CANCEL = re.compile(r"srv\s+stop: cancel task, id_task = (\d+)")
NEWSLOT = re.compile(r"new slot, n_ctx = (\d+)")
LAUNCH = re.compile(r"\| task (\d+) \| processing task")


def duration(text: str) -> float:
    """Go's time.Duration.String(): 1h2m3.5s, 2m4s, 7.04s, 723.291µs, 14.04ms."""
    total = 0.0
    for value, unit in re.findall(r"([\d.]+)(h|ms|µs|us|ns|m|s)", text):
        total += (
            float(value)
            * {"h": 3600, "m": 60, "s": 1, "ms": 1e-3, "µs": 1e-6, "us": 1e-6, "ns": 1e-9}[unit]
        )
    return total


def gin_time(text: str) -> dt.datetime:
    return dt.datetime.strptime(text, "%Y/%m/%d - %H:%M:%S").replace(tzinfo=TZ)


def lines():
    for name in ORDER:
        with gzip.open(RAW / f"{name}.gz", "rt", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, 1):
                yield name, number, line.rstrip("\n")


def parse():
    tasks: list[dict] = []
    gins: list[dict] = []
    families: Counter = Counter()
    load = {
        "model": None,
        "blob": None,
        "n_ctx": None,
        "started_s": None,
        "start_time": None,
        "used": False,
    }
    task = None
    seq = 0
    files_span: dict[str, list[str]] = {}

    current_file = None
    for name, number, line in lines():
        seq += 1
        if name != current_file:
            if task is not None:  # the server restarted with the task open
                task["seq_end"], task["abandoned"] = seq, True
                tasks.append(task)
                task = None
            current_file = name
        m = TIME.match(line)
        if m:
            families["time="] += 1
            stamp, level, source, msg, rest = m.groups()
            span = files_span.setdefault(name, [stamp, stamp])
            span[1] = stamp
            if msg == "using llama-server for model":
                if task is not None:  # the runner was replaced before the task released
                    task["seq_end"], task["abandoned"] = seq, True
                    tasks.append(task)
                    task = None
                load = {
                    "model": None,
                    "blob": re.search(r"model=(\S+)", rest).group(1).rsplit("/", 1)[-1][:19],
                    "n_ctx": None,
                    "started_s": None,
                    "start_time": stamp,
                    "used": False,
                }
            elif msg == "template selection":
                mm = re.search(r"model=registry.ollama.ai/library/(\S+)", rest)
                if mm:
                    load["model"] = mm.group(1)
            elif msg.startswith("llama-server started in"):
                load["started_s"] = float(re.search(r"([\d.]+) seconds", msg).group(1))
            continue
        m = GIN.match(line)
        if m:
            families["GIN"] += 1
            when, status, dur, client, method, path = m.groups()
            iso = gin_time(when).isoformat()
            span = files_span.setdefault(name, [iso, iso])
            span[0] = span[0] or iso
            span[1] = iso
            gins.append(
                {
                    "seq": seq,
                    "file": name,
                    "line": number,
                    "end": gin_time(when),
                    "status": int(status),
                    "duration_s": duration(dur),
                    "client": client,
                    "method": method,
                    "path": path.strip('"'),
                }
            )
            continue
        if line.startswith("slot") or line.startswith("srv"):
            families["slot/srv"] += 1
            if mm := NEWSLOT.search(line):
                load["n_ctx"] = int(mm.group(1))
            elif LAUNCH.search(line):
                if task is not None:
                    task["seq_end"], task["abandoned"] = seq, True
                    tasks.append(task)
                task = {
                    "seq_start": seq,
                    "file": name,
                    "line": number,
                    "model": load["model"],
                    "blob": load["blob"],
                    "load_n_ctx": load["n_ctx"],
                    "load_started_s": load["started_s"],
                    "first_after_load": not load["used"],
                    "load_time_line": load["start_time"],
                    "prompt_tokens": None,
                    "n_ctx_slot": None,
                    "cached_tokens": None,
                    "pp_last_tokens": None,
                    "pp_last_t": None,
                    "pp_last_rate": None,
                    "ngen_last": None,
                    "tg_last": None,
                    "prompt_eval_ms": None,
                    "prompt_eval_tokens": None,
                    "eval_ms": None,
                    "eval_tokens": None,
                    "total_ms": None,
                    "cancelled": False,
                    "stop_n_tokens": None,
                    "truncated": None,
                    "seq_end": None,
                    "abandoned": False,
                }
                load["used"] = True
            elif task is not None:
                if mm := NEWPROMPT.search(line):
                    task["n_ctx_slot"], _, task["prompt_tokens"] = map(int, mm.groups())
                elif (mm := CACHED.search(line)) and task["cached_tokens"] is None:
                    task["cached_tokens"] = int(mm.group(2))
                elif mm := PP.search(line):
                    task["pp_last_tokens"], task["pp_last_t"], task["pp_last_rate"] = (
                        int(mm.group(1)),
                        float(mm.group(3)),
                        float(mm.group(4)),
                    )
                elif mm := NGEN.search(line):
                    task["ngen_last"], task["tg_last"] = int(mm.group(1)), float(mm.group(2))
                elif mm := PEVAL.search(line):
                    task["prompt_eval_ms"], task["prompt_eval_tokens"] = (
                        float(mm.group(1)),
                        int(mm.group(2)),
                    )
                elif mm := EVAL.search(line):
                    task["eval_ms"], task["eval_tokens"] = float(mm.group(1)), int(mm.group(2))
                elif mm := TOTAL.search(line):
                    task["total_ms"] = float(mm.group(1))
                elif CANCEL.search(line):
                    task["cancelled"] = True
                elif mm := RELEASE.search(line):
                    task["stop_n_tokens"], task["truncated"] = int(mm.group(2)), int(mm.group(3))
                    task["seq_end"] = seq
                    tasks.append(task)
                    task = None
            continue
        families["other"] += 1
    if task is not None:
        task["seq_end"] = None  # still running at the snapshot (the last file is the live log)
        tasks.append(task)
    return tasks, gins, families, files_span


def join(tasks, gins):
    """Close each task with its access line; keep the inference access lines left over."""
    used = set()
    infer = [g for g in gins if g["method"] == "POST" and f'"{g["path"]}"' in INFER]
    by_seq = sorted(infer, key=lambda g: g["seq"])
    for t in tasks:
        if t["seq_end"] is None:
            t["gin"] = None
            continue
        processing = (t["total_ms"] or 0) / 1000.0
        if t["cancelled"] or t["abandoned"]:
            processing = (t["pp_last_t"] or 0) + (
                (t["ngen_last"] or 0) / t["tg_last"] if t["tg_last"] else 0
            )
        best = None
        for g in by_seq:
            if g["seq"] < t["seq_start"] - 5 or id(g) in used:
                continue
            if g["seq"] > t["seq_end"] + 400:
                break
            if g["seq"] < t["seq_end"] - 12 and not t["cancelled"]:
                continue
            if g["duration_s"] + 2.0 < processing:
                continue
            if (
                (t["cancelled"] or t["abandoned"])
                and g["status"] == 200
                and g["seq"] < t["seq_end"]
            ):
                continue
            best = g
            break
        if best is not None:
            used.add(id(best))
        t["gin"] = best
    orphans = [g for g in infer if id(g) not in used]
    return orphans


def rows(tasks, orphans):
    out = []
    for t in tasks:
        g = t.get("gin")
        prompt = t["prompt_tokens"] or 0
        if t["eval_tokens"] is not None:
            generated = t["eval_tokens"]
        elif t["stop_n_tokens"] is not None:
            generated = (
                max(0, t["stop_n_tokens"] - prompt + 1) if t["stop_n_tokens"] >= prompt else 0
            )
        else:
            generated = t["ngen_last"] or 0
        if t["seq_end"] is None:
            kind = "running_at_snapshot"
        elif t["cancelled"]:
            kind = "cancelled"
        elif t["abandoned"]:
            kind = "abandoned"
        elif t["eval_tokens"] is None:
            kind = "unknown"
        elif t["eval_tokens"] in CAPS:
            kind = "length"
        elif t["n_ctx_slot"] and prompt + t["eval_tokens"] >= t["n_ctx_slot"] - 1:
            kind = "length_ctx"
        else:
            kind = "stop"
        processing_s = (t["total_ms"] / 1000.0) if t["total_ms"] else None
        row = {
            "source": f"ollama:{t['file']}:{t['line']}",
            "model": t["model"],
            "blob": t["blob"],
            "n_ctx_slot": t["n_ctx_slot"],
            "prompt_tokens": t["prompt_tokens"],
            "cached_tokens": t["cached_tokens"],
            "prompt_eval_tokens": t["prompt_eval_tokens"],
            "prompt_eval_s": round(t["prompt_eval_ms"] / 1000, 3) if t["prompt_eval_ms"] else None,
            "prompt_eval_tps": round(t["prompt_eval_tokens"] / (t["prompt_eval_ms"] / 1000), 2)
            if t["prompt_eval_ms"]
            else None,
            "generated_tokens": generated,
            "eval_s": round(t["eval_ms"] / 1000, 3) if t["eval_ms"] else None,
            "eval_tps": round(t["eval_tokens"] / (t["eval_ms"] / 1000), 2)
            if t["eval_ms"] and t["eval_tokens"]
            else None,
            "processing_s": processing_s,
            "cancel_progress": None,
            "end_kind": kind,
            "stop_n_tokens": t["stop_n_tokens"],
            "loaded_runner": t["first_after_load"],
            "load_s": t["load_started_s"] if t["first_after_load"] else 0.0,
        }
        if t["cancelled"] or t["abandoned"]:
            row["cancel_progress"] = {
                "pp_tokens": t["pp_last_tokens"],
                "pp_t_s": t["pp_last_t"],
                "pp_rate": t["pp_last_rate"],
                "n_gen": t["ngen_last"],
                "tg": t["tg_last"],
            }
            row["processing_s"] = round(
                (t["pp_last_t"] or 0)
                + ((t["ngen_last"] or 0) / t["tg_last"] if t["tg_last"] else 0),
                2,
            )
        if g:
            end = g["end"]
            row.update(
                {
                    "gin_end_local": end.isoformat(),
                    "gin_end_utc": end.astimezone(dt.UTC).isoformat(),
                    "gin_start_utc": (end - dt.timedelta(seconds=g["duration_s"]))
                    .astimezone(dt.UTC)
                    .isoformat(),
                    "gin_status": g["status"],
                    "gin_duration_s": round(g["duration_s"], 3),
                    "gin_path": g["path"],
                    "gin_client": g["client"],
                }
            )
            spent = (row["processing_s"] or 0) + (row["load_s"] or 0)
            row["wait_s"] = round(max(0.0, g["duration_s"] - spent), 2)
        else:
            row.update(
                {
                    "gin_end_local": None,
                    "gin_end_utc": None,
                    "gin_start_utc": None,
                    "gin_status": None,
                    "gin_duration_s": None,
                    "gin_path": None,
                    "gin_client": None,
                    "wait_s": None,
                }
            )
        out.append(row)
    for g in orphans:
        end = g["end"]
        out.append(
            {
                "source": f"ollama:{g['file']}:{g['line']}",
                "model": None,
                "blob": None,
                "n_ctx_slot": None,
                "prompt_tokens": None,
                "cached_tokens": None,
                "prompt_eval_tokens": None,
                "prompt_eval_s": None,
                "prompt_eval_tps": None,
                "generated_tokens": None,
                "eval_s": None,
                "eval_tps": None,
                "processing_s": None,
                "cancel_progress": None,
                "end_kind": "no_task",
                "stop_n_tokens": None,
                "loaded_runner": None,
                "load_s": None,
                "gin_end_local": end.isoformat(),
                "gin_end_utc": end.astimezone(dt.UTC).isoformat(),
                "gin_start_utc": (end - dt.timedelta(seconds=g["duration_s"]))
                .astimezone(dt.UTC)
                .isoformat(),
                "gin_status": g["status"],
                "gin_duration_s": round(g["duration_s"], 3),
                "gin_path": g["path"],
                "gin_client": g["client"],
                "wait_s": None,
            }
        )
    out.sort(key=lambda r: r["gin_end_utc"] or "9999")
    return out


def main() -> int:
    tasks, gins, families, files_span = parse()
    orphans = join(tasks, gins)
    data = rows(tasks, orphans)
    with open(EVIDENCE / "dataset-ollama.jsonl", "w", encoding="utf-8") as handle:
        for r in data:
            handle.write(json.dumps(r, sort_keys=True) + "\n")
    summary = {
        "snapshot_at_utc": (RAW / "SNAPSHOT_AT_UTC").read_text().strip(),
        "files": ORDER,
        "line_families": dict(families),
        "file_time_spans_local": files_span,
        "tasks": len(tasks),
        "tasks_with_access_line": sum(1 for t in tasks if t.get("gin")),
        "inference_access_lines_without_task": len(orphans),
        "orphan_status_paths": Counter(f"{g['status']} {g['path']}" for g in orphans).most_common(),
        "end_kinds": Counter(r["end_kind"] for r in data).most_common(),
        "models": Counter(r["model"] for r in data).most_common(),
    }
    (EVIDENCE / "analysis" / "parse_ollama.summary.json").write_text(
        json.dumps(summary, indent=1, default=str) + "\n"
    )
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
