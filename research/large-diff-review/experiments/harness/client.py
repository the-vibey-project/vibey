"""Model access for the study: slot etiquette, a request that yields, an append-only store.

Research code (never imported by the package). Every request that reaches the model is
recorded in `results/requests.jsonl` with its telemetry; its reasoning text, which can run
to ~80k characters, is kept gzipped under `results/thinking/`. A request is identified by
the SHA-256 of its exact body plus a replicate index, so a run that is interrupted resumes
by skipping every request already recorded.
"""

from __future__ import annotations

import gzip
import hashlib
import http.client
import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EXP = Path(__file__).resolve().parents[1]
RESULTS = EXP / "results"
SERVER_LOG = Path.home() / ".ollama" / "logs" / "server.log"
# Another review client: a live pull-request review, or the canary lane. The harness never
# runs under these names (it is `python3 .../harness/run.py`).
OTHERS = re.compile(
    r"vibey-gh\s+(local-review|review-canary\s+run)|vibey_gh[./]local_review|"
    r"-m\s+vibey_gh\S*\s+(local-review|review-canary\s+run)"
)
SHELLS = {"zsh", "bash", "sh", "-zsh", "-bash", "sleep", "tail"}


def body_key(body: dict[str, Any], endpoint: str, replicate: int = 0) -> str:
    raw = json.dumps({"endpoint": endpoint, "body": body}, sort_keys=True)
    return hashlib.sha256(f"{raw}#rep{replicate}".encode()).hexdigest()


class Etiquette:
    """Waits until nobody else is using the model, and says when someone starts to."""

    def __init__(self, poll_s: float = 30.0, out=print) -> None:
        self.poll_s = poll_s
        self.out = out
        self.me = os.getpid()

    def others(self) -> list[str]:
        done = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True)
        found = []
        for line in done.stdout.splitlines():
            pid, _, command = line.strip().partition(" ")
            if not pid.isdigit() or int(pid) == self.me:
                continue
            # A shell that merely waits on a client (a `zsh -c 'until ...'` loop) is not one.
            first = command.split(" ", 1)[0].rsplit("/", 1)[-1]
            if first in SHELLS or "grep" in command or "pytest" in command:
                continue
            if OTHERS.search(command):
                found.append(command[:160])
        return found

    def connections(self) -> list[str]:
        """Clients other than this process holding a connection to Ollama's port. The
        self-hosted CI runner lives in a Docker container, invisible to `ps`; its requests
        reach Ollama through Docker's port forwarder, so they show here (`com.docke`)."""
        done = subprocess.run(
            ["lsof", "-nP", "-iTCP:11434", "-sTCP:ESTABLISHED"], capture_output=True, text=True
        )
        found = []
        for line in done.stdout.splitlines()[1:]:
            cols = line.split()
            if len(cols) < 2 or cols[0] == "ollama" or cols[1] == str(self.me):
                continue
            found.append(f"{cols[0]} pid {cols[1]} {cols[-2]}")
        return found

    def live_review(self) -> list[str]:
        """A live review in flight right now: a review process, or a connection from the
        Docker-hosted runner seen twice, 4 s apart (a GET /api/ps poll is gone by then)."""
        others = self.others()
        if others:
            return others
        first = [c for c in self.connections() if c.startswith("com.docke")]
        if not first:
            return []
        time.sleep(4)
        return [c for c in self.connections() if c.startswith("com.docke")]

    def log_busy(self) -> str:
        """'' when the server log shows no request in flight, else why it looks busy."""
        try:
            size = SERVER_LOG.stat().st_size
            with SERVER_LOG.open("rb") as handle:
                handle.seek(max(0, size - 400_000))
                tail = handle.read().decode("utf-8", errors="replace")
            age = time.time() - SERVER_LOG.stat().st_mtime
        except OSError as error:
            return f"server log unreadable: {error}"
        started = max(tail.rfind("processing task"), tail.rfind("new prompt"))
        finished = max(tail.rfind('POST     "/api/chat"'), tail.rfind('POST     "/api/generate"'))
        loading = tail.rfind("llama-server started")
        if started > finished and age < 120:
            return "a request is in flight (server log)"
        if loading > finished and loading > started and age < 30:
            return "a model is loading (server log)"
        return ""

    def busy(self) -> str:
        others = self.others()
        if others:
            return "another review client is running: " + others[0]
        connected = self.connections()
        if connected:
            return "another client is connected to the model: " + connected[0]
        return self.log_busy()

    def wait_clear(self) -> float:
        started = time.monotonic()
        said = ""
        while True:
            why = self.busy()
            if not why:
                # Twice, a few seconds apart: a client between two of its requests looks idle.
                time.sleep(8)
                why = self.busy()
                if not why:
                    return time.monotonic() - started
            if why != said:
                self.out(f"[etiquette] waiting: {why}")
                said = why
            time.sleep(self.poll_s)


@dataclass
class Reply:
    status: int = 0
    body: dict[str, Any] = field(default_factory=dict)
    wall_s: float = 0.0
    t_start: float = 0.0
    t_end: float = 0.0
    outcome: str = "ok"  # ok | timeout | yielded | http_error | transport_error
    error: str = ""


class YieldingClient:
    """One HTTP request to Ollama, aborted (only ever our own) when another review client
    appears or the deadline passes. Closing the socket cancels the generation server-side."""

    def __init__(
        self, host: str = "127.0.0.1", port: int = 11434, etiquette: Etiquette | None = None
    ):
        self.host, self.port = host, port
        self.etiquette = etiquette or Etiquette()

    def post(
        self, endpoint: str, body: dict[str, Any], deadline_s: float, *, watch: bool = True
    ) -> Reply:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=None)
        reply = Reply(t_start=time.time())
        box: dict[str, Any] = {}

        def work() -> None:
            try:
                conn.request(
                    "POST", endpoint, json.dumps(body), {"Content-Type": "application/json"}
                )
                response = conn.getresponse()
                box["status"] = response.status
                box["raw"] = response.read()
            except Exception as error:  # noqa: BLE001 - reported, never swallowed
                box["error"] = repr(error)

        thread = threading.Thread(target=work, daemon=True)
        started = time.monotonic()
        thread.start()
        why = ""
        while thread.is_alive():
            thread.join(5.0)
            if not thread.is_alive():
                break
            if time.monotonic() - started > deadline_s:
                why = "timeout"
            elif watch and self.etiquette.live_review():
                why = "yielded"
            if why:
                try:
                    if conn.sock is not None:
                        conn.sock.shutdown(2)
                    conn.close()
                except OSError:
                    pass
                thread.join(10.0)
                break
        reply.wall_s = time.monotonic() - started
        reply.t_end = time.time()
        if why:
            reply.outcome = why
            return reply
        if "error" in box:
            reply.outcome, reply.error = "transport_error", box["error"]
            return reply
        reply.status = int(box.get("status", 0))
        try:
            reply.body = json.loads(box.get("raw") or b"{}")
        except ValueError:
            reply.body = {"error": (box.get("raw") or b"")[:500].decode("utf-8", "replace")}
        if reply.status != 200:
            reply.outcome, reply.error = "http_error", str(reply.body.get("error", ""))[:500]
        return reply


def invalid_keys() -> set[str]:
    """Records the contention audit (`contention.py`) found queued behind another client's
    request: kept in the append-only log, never used as a result."""
    path = RESULTS / "invalidations.jsonl"
    if not path.is_file():
        return set()
    return {
        (row["key"], row.get("t_start"))
        for row in map(json.loads, filter(str.strip, path.read_text().splitlines()))
    }


class RequestStore:
    """Append-only record of every request answered; the resume and cache index."""

    def __init__(self, path: Path = RESULTS / "requests.jsonl") -> None:
        self.path = path
        self.thinking_dir = path.parent / "thinking"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.thinking_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, dict[str, Any]] = {}
        invalid = invalid_keys()
        if self.path.is_file():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    record = json.loads(line)
                    if (record["key"], record.get("t_start")) not in invalid:
                        self._index[record["key"]] = record

    def get(self, key: str) -> dict[str, Any] | None:
        return self._index.get(key)

    def records(self) -> list[dict[str, Any]]:
        return list(self._index.values())

    def thinking(self, key: str) -> str:
        path = self.thinking_dir / f"{key}.txt.gz"
        return gzip.decompress(path.read_bytes()).decode() if path.is_file() else ""

    def put(self, record: dict[str, Any], thinking: str = "") -> dict[str, Any]:
        if thinking:
            (self.thinking_dir / f"{record['key']}.txt.gz").write_bytes(
                gzip.compress(thinking.encode())
            )
        with self.path.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._index[record["key"]] = record
        return record


def telemetry(reply: Reply, body: dict[str, Any]) -> dict[str, Any]:
    """What every request records, whatever answered it."""
    message = reply.body.get("message") or {}
    thinking = str(message.get("thinking") or reply.body.get("thinking") or "")
    content = str(message.get("content") or reply.body.get("response") or "")
    options = dict(body.get("options") or {})
    return {
        "model": body.get("model"),
        "think": body.get("think", ""),
        "options": options,
        "raw": bool(body.get("raw", False)),
        "status": reply.status,
        "outcome": reply.outcome,
        "error": reply.error,
        "done_reason": reply.body.get("done_reason"),
        "prompt_tokens": reply.body.get("prompt_eval_count"),
        "eval_tokens": reply.body.get("eval_count"),
        "prompt_eval_s": (reply.body.get("prompt_eval_duration") or 0) / 1e9,
        "eval_s": (reply.body.get("eval_duration") or 0) / 1e9,
        "load_s": (reply.body.get("load_duration") or 0) / 1e9,
        "reasoning_chars": len(thinking),
        "answer_chars": len(content),
        "content": content,
        "wall_s": round(reply.wall_s, 2),
        "t_start": reply.t_start,
        "t_end": reply.t_end,
    }, thinking


_HOST: dict[str, Any] = {}


def host_fingerprint() -> dict[str, Any]:
    """CPU, memory, OS, Ollama version and model digests: on every record, so a measurement
    is only ever read as one of THIS host (the monthly calibration's rule)."""
    if not _HOST:

        def sh(*cmd: str) -> str:
            done = subprocess.run(cmd, capture_output=True, text=True)
            return done.stdout.strip()

        try:
            tags = json.loads(sh("curl", "-s", "http://127.0.0.1:11434/api/tags") or "{}")
            version = json.loads(sh("curl", "-s", "http://127.0.0.1:11434/api/version") or "{}")
        except ValueError:
            tags, version = {}, {}
        _HOST.update(
            cpu=sh("sysctl", "-n", "machdep.cpu.brand_string"),
            cores=sh("sysctl", "-n", "hw.ncpu"),
            mem_bytes=sh("sysctl", "-n", "hw.memsize"),
            os=sh("sw_vers", "-productVersion"),
            ollama=version.get("version", ""),
            digests={m["name"]: m.get("digest", "")[:12] for m in tags.get("models", [])},
        )
        _HOST["id"] = hashlib.sha256(json.dumps(_HOST, sort_keys=True).encode()).hexdigest()[:16]
    return _HOST


class Model:
    """The study's one door to the model: etiquette, then the request, then the record."""

    def __init__(self, store: RequestStore | None = None, out=print) -> None:
        self.store = store or RequestStore()
        self.etiquette = Etiquette(out=out)
        self.client = YieldingClient(etiquette=self.etiquette)
        self.out = out
        self.sent = 0

    def ask(
        self,
        endpoint: str,
        body: dict[str, Any],
        deadline_s: float,
        *,
        tag: dict[str, Any],
        replicate: int = 0,
        offline: bool = False,
    ) -> dict[str, Any] | None:
        """The record for this exact request: from the store, or asked now. None when the
        harness is offline (composition only) and the request was never answered."""
        key = body_key(body, endpoint, replicate)
        cached = self.store.get(key)
        if cached is not None:
            return cached
        if offline:
            return None
        import fcntl

        # One harness process at a time talks to the model: two of ours that both saw the
        # slot free would otherwise queue one request behind the other inside Ollama, where
        # its deadline runs while it waits.
        lock = (RESULTS / ".model.lock").open("w")
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return self._ask_locked(endpoint, body, deadline_s, tag, replicate, key)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()

    def _ask_locked(self, endpoint, body, deadline_s, tag, replicate, key):
        while True:
            waited = self.etiquette.wait_clear()
            reply = self.client.post(endpoint, body, deadline_s)
            if reply.outcome == "yielded":
                self.out(f"[etiquette] yielded {tag} after {reply.wall_s:.0f}s; re-queued")
                with (RESULTS / "yields.jsonl").open("a") as handle:
                    handle.write(
                        json.dumps(
                            {"key": key, "tag": tag, "wall_s": reply.wall_s, "t": time.time()}
                        )
                        + "\n"
                    )
                continue
            break
        self.sent += 1
        record, thinking = telemetry(reply, body)
        record.update(
            key=key,
            endpoint=endpoint,
            replicate=replicate,
            tag=tag,
            deadline_s=round(deadline_s, 1),
            slot_wait_s=round(waited, 1),
            host=host_fingerprint()["id"],
            model_digest=host_fingerprint()["digests"].get(str(body.get("model")), ""),
        )
        return self.store.put(record, thinking)
