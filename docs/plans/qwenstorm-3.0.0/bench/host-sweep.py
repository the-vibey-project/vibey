"""Measure what a local-engine configuration costs this host, and what it still gets right.

    python3 host-sweep.py                 # the whole matrix
    python3 host-sweep.py --only C        # one configuration

Sub-doctrine 8.g: always measured. Every number this prints is read from the running machine,
never estimated. The method is the part that transfers to another host; the numbers are not.

Three things are measured per configuration, because optimising on one alone is how a machine
ends up fast and wrong:

  cost     wired memory, llama-server RSS and swap. On Apple Silicon the GPU shares system
           memory, so a model served "100% GPU" has its weights AND its KV cache wired through
           Metal -- unswappable, and understated by RSS. Wired is the number that matters.
  speed    tokens per second on a fixed prompt.
  fidelity a deterministic task with a checkable answer, run REPEATS times. Quantising the KV
           cache is the cheapest memory there is right up until the model starts getting
           things wrong, and nothing else in the sweep would notice that happening.

The sweep deliberately overshoots -- it includes settings expected to be too aggressive -- so
that the safe point is found from the far side rather than assumed. A configuration that
scores badly here has done its job.
"""

import argparse
import contextlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request

OLLAMA = "http://127.0.0.1:11434"
MODEL = "gpt-oss:20b"
REPEATS = 8

# context, kv cache type, and whether this row is expected to be a step too far.
MATRIX = {
    "A": (131072, "f16", "baseline: what the storm ran all evening"),
    "B": (65536, "f16", "context halved to the measured need (max turn was 49,118 tokens)"),
    "C": (65536, "q8_0", "and the KV cache quantised: a quarter of A's reservation"),
    "D": (65536, "q4_0", "OVERSHOOT: KV at 4 bits, expected to cost fidelity"),
    "E": (16384, "q4_0", "OVERSHOOT: below the measured p50, expected to truncate"),
}

# A task with one right answer, phrased so a correct model cannot reasonably miss it and a
# degraded one plausibly can: arithmetic it must actually carry out, returned as strict JSON.
PROBE = (
    'Return ONLY a JSON object, no prose and no code fence, of the form {"answer": <integer>}. '
    "Compute: 37 * 24 + 1156 - 89"
)
EXPECTED = 37 * 24 + 1156 - 89


def sh(argv: list[str]) -> str:
    return subprocess.run(argv, capture_output=True, text=True).stdout.strip()


def page_size() -> int:
    """hw.pagesize, never a remembered 4096: Apple Silicon pages are 16 KB and a sweep that
    assumes otherwise reports a quarter of the free memory it has, in the reassuring direction."""
    try:
        return int(sh(["sysctl", "-n", "hw.pagesize"]) or 16384)
    except ValueError:
        return 16384


def memory() -> dict[str, float]:
    ps = page_size()
    stat = sh(["vm_stat"])
    pages = {
        key.strip().lower(): int(value)
        for key, value in re.findall(r"^(.*?):\s+(\d+)\.$", stat, re.M)
    }

    def gb(name: str) -> float:
        return pages.get(name, 0) * ps / 1024**3

    swap = sh(["sysctl", "-n", "vm.swapusage"])
    used = re.search(r"used = ([\d.]+)M", swap)
    rss = 0.0
    for line in sh(["ps", "-Ao", "rss=,comm="]).splitlines():
        if "llama-server" in line:
            rss = max(rss, int(line.split()[0]) / 1024**2)
    return {
        "wired_gb": round(gb("pages wired down"), 2),
        "free_mb": round(gb("pages free") * 1024),
        "swap_used_gb": round(float(used.group(1)) / 1024, 2) if used else 0.0,
        "llama_rss_gb": round(rss, 2),
    }


def unload() -> None:
    # keep_alive 0 asks the server to drop the model now, so the next request reloads it at
    # the configuration under test rather than reusing whatever is already resident.
    with contextlib.suppress(urllib.error.URLError):
        urllib.request.urlopen(
            urllib.request.Request(
                f"{OLLAMA}/api/generate",
                data=json.dumps({"model": MODEL, "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"},
            ),
            timeout=60,
        ).read()
    for _ in range(30):
        if MODEL not in sh(["ollama", "ps"]):
            return
        time.sleep(1)


def ask(prompt: str, context: int) -> tuple[str, float, int]:
    body = json.dumps(
        {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": context, "temperature": 0},
        }
    ).encode()
    started = time.time()
    with urllib.request.urlopen(
        urllib.request.Request(
            f"{OLLAMA}/api/generate", data=body, headers={"Content-Type": "application/json"}
        ),
        timeout=600,
    ) as answer:
        payload = json.load(answer)
    elapsed = time.time() - started
    return payload.get("response", ""), elapsed, payload.get("eval_count", 0)


def correct(answer: str) -> bool:
    match = re.search(r'"answer"\s*:\s*(-?\d+)', answer)
    return bool(match) and int(match.group(1)) == EXPECTED


def measure(name: str) -> dict[str, object]:
    context, cache, note = MATRIX[name]
    unload()
    idle = memory()
    # Warm the model at this configuration, then measure a steady-state request.
    ask("hello", context)
    loaded = memory()
    hits, tokens, seconds = 0, 0, 0.0
    for _ in range(REPEATS):
        answer, elapsed, count = ask(PROBE, context)
        hits += correct(answer)
        tokens += count
        seconds += elapsed
    return {
        "config": name,
        "context": context,
        "kv_cache": cache,
        "note": note,
        "wired_gb": loaded["wired_gb"],
        "wired_delta_gb": round(loaded["wired_gb"] - idle["wired_gb"], 2),
        "llama_rss_gb": loaded["llama_rss_gb"],
        "swap_used_gb": loaded["swap_used_gb"],
        "free_mb": loaded["free_mb"],
        "tokens_per_second": round(tokens / seconds, 1) if seconds else 0.0,
        "fidelity": f"{hits}/{REPEATS}",
        "fidelity_rate": round(hits / REPEATS, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", choices=sorted(MATRIX))
    args = parser.parse_args()
    wanted = args.only or sorted(MATRIX)
    cache = os.environ.get("OLLAMA_KV_CACHE_TYPE", "f16")
    print(f"server KV cache type: {cache}   (restart ollama to change it)")
    print(
        f"{'cfg':4}{'ctx':>8}{'kv':>7}{'wired':>8}{'rss':>7}{'swap':>7}{'free':>8}{'tok/s':>8}  fidelity"
    )
    rows = []
    for name in wanted:
        if MATRIX[name][1] != cache:
            print(
                f"{name:4}{MATRIX[name][0]:>8}{MATRIX[name][1]:>7}   -- needs OLLAMA_KV_CACHE_TYPE={MATRIX[name][1]}"
            )
            continue
        row = measure(name)
        rows.append(row)
        print(
            f"{row['config']:4}{row['context']:>8}{row['kv_cache']:>7}"
            f"{row['wired_gb']:>8}{row['llama_rss_gb']:>7}{row['swap_used_gb']:>7}"
            f"{row['free_mb']:>8}{row['tokens_per_second']:>8}  {row['fidelity']}"
        )
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
