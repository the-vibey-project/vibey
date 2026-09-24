# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Local slot calibration (`vibey_gh.slots`): the logic, exactly, with every machine faked.

The measurement itself is evidence, not a test (ADR-0057). What is tested here is that the
evidence is read, judged and gated the way the ADR says: the bounds, the stop rule, the
ideal N, the fingerprint that keys it, the checkpoint that lets a sweep survive a reboot,
and the gate that turns a declaration into a number.
"""

from __future__ import annotations

import io
import json
import subprocess
import threading
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Self

import pytest

from vibey_gh import slots
from vibey_gh.interfaces.slots_interface import (
    CorpusSamplerInterface,
    DeviceFingerprinterInterface,
    HostMemorySamplerInterface,
    OllamaClientInterface,
    SlotEvidenceStoreInterface,
    SlotGateInterface,
    SlotServerInterface,
    SlotVerdictInterface,
    SweepCheckpointInterface,
    TurnReplayerInterface,
)
from vibey_gh.slots import (
    EVIDENCE_SCHEMA,
    MEASURED,
    POOL_SCHEMA,
    AnswerShape,
    CorpusSampler,
    DarwinHostSampler,
    DeviceFingerprint,
    DeviceFingerprinter,
    DirectoryLock,
    HostSample,
    LinuxHostSampler,
    MemoryWatch,
    OllamaClient,
    PlatformProbes,
    PoolRun,
    SlotBounds,
    SlotDecision,
    SlotEvidenceStore,
    SlotGate,
    SlotReport,
    SlotSweep,
    SlotVerdict,
    SpawnedOllamaServer,
    StepSummary,
    SweepCheckpoint,
    TurnOutcome,
    TurnPool,
    TurnReplayer,
)

GIB = 2**30

# ---------------------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------------------


class Response:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body, self.status = body, status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def opener_for(routes: dict[str, Any]) -> Any:
    calls: list[tuple[str, str, Any, float]] = []

    def opener(request: Any, timeout: float) -> Any:
        path = request.full_url.split("11434", 1)[-1]
        body = json.loads(request.data) if request.data else None
        calls.append((request.get_method(), path, body, timeout))
        answer = routes[path]
        if isinstance(answer, BaseException):
            raise answer
        if isinstance(answer, Response):
            return answer
        return Response(json.dumps(answer).encode())

    opener.calls = calls  # type: ignore[attr-defined]
    return opener


GOOD = {
    "message": {
        "content": "",
        "tool_calls": [{"function": {"name": "read_file", "arguments": {"path": "x"}}}],
    },
    "done_reason": "stop",
    "prompt_eval_count": 100,
    "eval_count": 10,
    "prompt_eval_duration": 2_000_000,
    "eval_duration": 1_000_000,
}


class FakeClient:
    def __init__(self, version: str = "0.34.4", loaded: Any = (), digest: str = "d1") -> None:
        self.base_url = "http://fake"
        self._version = version
        self._loaded = loaded
        self._digest = digest
        self.chats: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.answers: list[tuple[int, dict[str, Any]]] = []

    def version(self) -> str:
        return self._version

    def loaded(self) -> Any:
        value = self._loaded() if callable(self._loaded) else self._loaded
        return None if value is None else list(value)

    def digest(self, model: str) -> str:
        return self._digest

    def chat(self, body: Any, timeout_s: float) -> tuple[int, dict[str, Any]]:
        with self.lock:
            self.chats.append(dict(body))
            if self.answers:
                return self.answers.pop(0)
        return 200, GOOD


def fingerprint(**changes: Any) -> DeviceFingerprint:
    base: dict[str, Any] = dict(
        hardware="Mac17,2",
        processor="Apple M5",
        memory_bytes=24 * GIB,
        accelerator="Apple M5 GPU, 10 cores",
        os="macOS 26.6.2",
        runtime="ollama 0.34.4",
        model="gpt-oss:20b",
        model_digest="17052f91a42e",
        context_window=65536,
    )
    base.update(changes)
    return DeviceFingerprint(**base)


def outcome(turn_id: str = "r#1", **changes: Any) -> TurnOutcome:
    base: dict[str, Any] = dict(
        segment=0,
        turn_id=turn_id,
        worker=0,
        started_s=0.0,
        ended_s=10.0,
        status=200,
        error="",
        done_reason="stop",
        prompt_tokens=1000,
        output_tokens=100,
        prompt_ms=500.0,
        output_ms=100.0,
        recorded_input_tokens=1000,
        first_in_segment=True,
        signature="tools:read_file(path)",
        exact="abc",
    )
    base.update(changes)
    return TurnOutcome(**base)


def step(parallel: int, throughput: float, **changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "parallel": parallel,
        "num_ctx": 65536,
        "turns": 2,
        "ok": 2,
        "throughput_turns_per_hour": throughput,
        "output_tokens_per_s": 5.0,
        "latency_p50_s": 10.0,
        "latency_p95_s": 20.0,
        "done_reasons": {"stop": 2},
        "memory": {
            "readable": True,
            "wired_peak_bytes": 10 * GIB,
            "swapout_mb_per_minute": 1.0,
            "residency": {"calibration": {"changes": 0}, "production": {"models": []}},
        },
        "server": {"loads_during": 0, "truncations_during": 0, "shifts_during": 0},
        "outcomes": [outcome("r#1").as_dict(), outcome("r#2").as_dict()],
        "fidelity": {"structural": 1.0, "exact": 1.0},
    }
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


class Files:
    def __init__(self, files: dict[str, str]) -> None:
        self.files = files

    def read(self, path: str) -> str | None:
        return self.files.get(path)


# ---------------------------------------------------------------------------------------
# seams
# ---------------------------------------------------------------------------------------


def test_every_class_honours_its_declared_seam(tmp_path: Path) -> None:
    client = OllamaClient("http://127.0.0.1:11434")
    assert isinstance(client, OllamaClientInterface)
    assert isinstance(DeviceFingerprinter(client), DeviceFingerprinterInterface)
    assert isinstance(DarwinHostSampler(), HostMemorySamplerInterface)
    assert isinstance(LinuxHostSampler(), HostMemorySamplerInterface)
    assert isinstance(SpawnedOllamaServer("ollama", tmp_path), SlotServerInterface)
    assert isinstance(TurnReplayer(client, "m", num_ctx=8), TurnReplayerInterface)
    sampler = CorpusSampler(segments=1, segment_length=1, strata=[])
    assert isinstance(sampler, CorpusSamplerInterface)
    assert isinstance(SlotVerdict(SlotBounds()), SlotVerdictInterface)
    assert isinstance(SweepCheckpoint(tmp_path, {}), SweepCheckpointInterface)
    assert isinstance(SlotEvidenceStore(tmp_path), SlotEvidenceStoreInterface)
    assert isinstance(SlotGate(SlotVerdict(SlotBounds()), max_age_days=1), SlotGateInterface)


def test_run_returns_stdout_or_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    assert slots._run(["echo", "hello"]).strip() == "hello"
    assert slots._run(["false"]) == ""
    assert slots._run(["/nonexistent/binary-for-this-test"]) == ""

    def slow(*args: Any, **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired("x", 1)

    monkeypatch.setattr(slots.subprocess, "run", slow)
    assert slots._run(["anything"]) == ""


# ---------------------------------------------------------------------------------------
# the device
# ---------------------------------------------------------------------------------------


def test_a_fingerprint_is_keyed_stably_and_names_what_changed() -> None:
    one = fingerprint()
    assert one.key() == fingerprint().key()
    assert one.key() != fingerprint(model_digest="other").key()
    assert one.missing == []
    assert fingerprint(hardware="", memory_bytes=0).missing == ["hardware", "memory_bytes"]
    assert one.differences(one.as_dict()) == []
    changed = one.differences({**one.as_dict(), "runtime": "ollama 0.34.2"})
    assert changed == ["runtime was 'ollama 0.34.2', is 'ollama 0.34.4'"]


def test_the_ollama_client_speaks_the_api() -> None:
    error_body = io.BytesIO(b'{"error": "request exceeds the available context size"}')
    routes = {
        "/api/version": {"version": "0.34.4"},
        "/api/ps": {"models": [{"name": "gpt-oss:20b"}, "junk"]},
        "/api/tags": {
            "models": [
                {"name": "gpt-oss:20b", "digest": "dig"},
                "junk",
                {"model": "qwen:latest", "digest": "q"},
            ]
        },
        "/api/chat": urllib.error.HTTPError("u", 400, "bad", {}, error_body),  # type: ignore[arg-type]
    }
    opener = opener_for(routes)
    client = OllamaClient("http://127.0.0.1:11434/", opener=opener)
    assert client.base_url == "http://127.0.0.1:11434"
    assert client.version() == "0.34.4"
    assert client.loaded() == [{"name": "gpt-oss:20b"}]
    assert client.digest("gpt-oss:20b") == "dig"
    assert client.digest("qwen") == "q"
    assert client.digest("absent") == ""
    status, data = client.chat({"model": "m"}, 5.0)
    assert (status, data["error"]) == (400, "request exceeds the available context size")
    assert opener.calls[-1][0] == "POST" and opener.calls[-1][3] == 5.0


def test_the_ollama_client_reads_absence_as_absence() -> None:
    down = opener_for(
        {
            "/api/version": urllib.error.URLError("refused"),
            "/api/ps": {"no": "models"},
            "/api/tags": ValueError("bad url"),
            "/api/chat": Response(b"not json", 200),
        }
    )
    client = OllamaClient("http://127.0.0.1:11434", opener=down)
    assert client.version() == ""
    assert client.loaded() is None
    assert client.digest("m") == ""
    assert client.chat({}, 1.0) == (200, {"error": "an answer that was not JSON"})
    silent = OllamaClient("http://127.0.0.1:11434", opener=opener_for({"/api/chat": OSError("x")}))
    assert silent.chat({}, 1.0) == (0, {"error": "no answer"})
    listed = OllamaClient("http://127.0.0.1:11434", opener=opener_for({"/api/version": ["a"]}))
    assert listed.version() == ""


DARWIN = {
    ("sysctl", "-n", "hw.model"): "Mac17,2\n",
    ("sysctl", "-n", "machdep.cpu.brand_string"): "Apple M5\n",
    ("sysctl", "-n", "hw.memsize"): f"{24 * GIB}\n",
    (
        "system_profiler",
        "SPDisplaysDataType",
    ): "  Chipset Model: Apple M5\n  Total Number of Cores: 10\n",
    ("sw_vers", "-productName"): "macOS\n",
    ("sw_vers", "-productVersion"): "26.6.2\n",
}


def test_a_mac_states_itself() -> None:
    reader = DeviceFingerprinter(
        FakeClient(), platform_name="darwin", run=lambda argv: DARWIN.get(tuple(argv), "")
    )
    assert reader.fingerprint("gpt-oss:20b", 65536) == fingerprint(model_digest="d1")


def test_a_sandboxed_mac_is_read_from_system_profiler_instead() -> None:
    answers = {
        ("system_profiler", "SPHardwareDataType"): (
            "  Model Identifier: Mac17,2\n  Chip: Apple M5\n  Memory: 24 GB\n"
        ),
        ("system_profiler", "SPDisplaysDataType"): "  Chipset Model: Apple M5\n",
    }
    got = DeviceFingerprinter(
        FakeClient(version=""),
        platform_name="darwin",
        run=lambda argv: answers.get(tuple(argv), ""),
    ).fingerprint("m", 8)
    assert (got.hardware, got.processor, got.memory_bytes) == ("Mac17,2", "Apple M5", 24 * GIB)
    assert got.accelerator == "Apple M5" and got.runtime == "" and got.os == ""
    assert "runtime" in got.missing
    blank = DeviceFingerprinter(FakeClient(), platform_name="darwin", run=lambda argv: "")
    got = blank.fingerprint("m", 8)
    assert (got.memory_bytes, got.accelerator) == (0, "none")


def test_a_linux_host_states_itself_from_its_own_files() -> None:
    files = Files(
        {
            "/sys/devices/virtual/dmi/id/product_name": "ThinkStation\n",
            "/proc/cpuinfo": "processor: 0\nmodel name: AMD Ryzen 9\n",
            "/proc/meminfo": "MemTotal: 1000 kB\n",
            "/etc/os-release": 'NAME="Arch"\nPRETTY_NAME="Arch Linux"\n',
        }
    )
    two = "NVIDIA RTX 4090, 24564 MiB\nNVIDIA RTX 4090, 24564 MiB\n"
    got = DeviceFingerprinter(
        FakeClient(), platform_name="linux", run=lambda argv: two, reader=files
    ).fingerprint("m", 8)
    assert got.hardware == "ThinkStation" and got.processor == "AMD Ryzen 9"
    assert got.memory_bytes == 1000 * 1024 and got.os == "Arch Linux"
    assert got.accelerator == "NVIDIA RTX 4090, 24564 MiB; NVIDIA RTX 4090, 24564 MiB"
    arm = Files({"/proc/cpuinfo": "Model: Raspberry Pi 5\n"})
    bare = DeviceFingerprinter(
        FakeClient(), platform_name="linux", run=lambda argv: "", reader=arm
    ).fingerprint("m", 8)
    assert (bare.processor, bare.memory_bytes, bare.accelerator, bare.os, bare.hardware) == (
        "Raspberry Pi 5",
        0,
        "none",
        "",
        "",
    )


# ---------------------------------------------------------------------------------------
# what the hardware charges
# ---------------------------------------------------------------------------------------

VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                   167991.
Pages wired down:                             291757.
"Translation faults":                     7179055245.
Swapins:                                   100.
Swapouts:                                  200.
"""


def test_a_mac_reports_wired_pages_and_swap_counters() -> None:
    answers = {
        ("vm_stat",): VM_STAT,
        ("memory_pressure", "-Q"): "System-wide memory free percentage: 73%\n",
    }
    got = DarwinHostSampler(
        run=lambda argv: answers.get(tuple(argv), ""), clock=lambda: 5.0
    ).sample()
    assert got == HostSample(5.0, 291757 * 16384, 73.0, 100, 200, 16384, True)
    silent = DarwinHostSampler(run=lambda argv: "", clock=lambda: 1.0).sample()
    assert (silent.readable, silent.page_bytes, silent.free_percent, silent.wired_bytes) == (
        False,
        4096,
        None,
        0,
    )


def test_a_linux_host_reports_unevictable_memory_plus_the_accelerator() -> None:
    files = Files(
        {
            "/proc/meminfo": "MemTotal: 1000 kB\nMemAvailable: 250 kB\nUnevictable: 10 kB\nHugePages_Total:\n",
            "/proc/vmstat": "pswpin 7\npswpout 9\nbroken\nnr x\n",
        }
    )
    got = LinuxHostSampler(run=lambda argv: "3\n4\nN/A\n", reader=files, clock=lambda: 2.0).sample()
    assert got.wired_bytes == 10 * 1024 + 7 * 2**20
    assert (got.free_percent, got.swapins, got.swapouts, got.readable) == (25.0, 7, 9, True)
    nothing = LinuxHostSampler(run=lambda argv: "", reader=Files({}), clock=lambda: 0.0).sample()
    assert (nothing.readable, nothing.free_percent) == (False, None)


def test_the_probes_follow_the_platform() -> None:
    assert isinstance(PlatformProbes.host_sampler("linux"), LinuxHostSampler)
    assert isinstance(PlatformProbes.host_sampler("darwin"), DarwinHostSampler)


class Samples:
    def __init__(self, samples: list[HostSample]) -> None:
        self.samples = samples

    def sample(self) -> HostSample:
        return self.samples.pop(0) if len(self.samples) > 1 else self.samples[0]


def test_a_watch_summarises_peak_wired_swap_rates_and_residency() -> None:
    samples = Samples(
        [
            HostSample(0.0, 10 * GIB, 50.0, 0, 0, 16384, True),
            HostSample(30.0, 12 * GIB, None, 10, 100, 16384, True),
            HostSample(60.0, 11 * GIB, 40.0, 20, 200, 16384, True),
        ]
    )
    readings = iter(
        [[{"name": "m", "size": 1, "context_length": 8}], None, [{"name": "m", "size": 2}]]
    )
    watch = MemoryWatch(
        samples,
        {"calibration": FakeClient(loaded=lambda: next(readings)), "production": FakeClient()},
    )
    for _ in range(3):
        watch.sample_once()
    summary = watch.summary()
    assert summary["wired_peak_bytes"] == 12 * GIB and summary["free_percent_min"] == 40.0
    assert (summary["swapins"], summary["swapouts"]) == (20, 200)
    assert summary["swapout_mb_per_minute"] == round(200 * 16384 / 1e6, 2)
    assert summary["timeline"][1] == [30.0, round(12 * GIB / 1e9, 3), None, 10, 100]
    residency = summary["residency"]
    assert residency["calibration"] == {
        "models": ["m"],
        "unreadable": 1,
        "changes": 1,
        "last": [["m", 2, 0]],
    }
    assert residency["production"] == {"models": [], "unreadable": 0, "changes": 0, "last": []}


def test_a_watch_that_could_read_nothing_says_so() -> None:
    watch = MemoryWatch(
        Samples([HostSample(0.0, 0, None, 0, 0, 4096, False)]),
        {"production": FakeClient(loaded=None)},
    )
    watch.sample_once()
    assert watch.summary() == {
        "samples": 1,
        "readable": False,
        "residency": {"production": {"models": [], "unreadable": 1, "changes": 0, "last": None}},
    }
    one = MemoryWatch(Samples([HostSample(0.0, 5, None, 0, 0, 4096, True)]), {})
    one.sample_once()
    assert one.summary()["free_percent_min"] is None


def test_a_watch_samples_in_the_background_until_it_is_left() -> None:
    samples = Samples([HostSample(0.0, 1, 1.0, 0, 0, 4096, True)])
    with MemoryWatch(samples, {}, interval_s=0.001) as watch:
        threading.Event().wait(0.05)
    assert len(watch.samples) >= 3
    MemoryWatch(samples, {}).__exit__(None, None, None)


# ---------------------------------------------------------------------------------------
# the runner being swept
# ---------------------------------------------------------------------------------------


class Process:
    def __init__(self, exits: int | None = None, hangs: bool = False) -> None:
        self.exits, self.hangs = exits, hangs
        self.terminated = self.killed = False
        self.waits = 0

    def poll(self) -> int | None:
        return self.exits

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float) -> int:
        self.waits += 1
        if self.hangs and self.waits == 1:
            raise subprocess.TimeoutExpired("ollama", timeout)
        return 0


class Clock:
    def __init__(self, step: float = 1.0) -> None:
        self.now, self.step = 0.0, step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


def server(
    tmp_path: Path, versions: list[str], process: Process, **kwargs: Any
) -> tuple[SpawnedOllamaServer, list[Any]]:
    launched: list[Any] = []

    class Client(FakeClient):
        def version(self) -> str:
            return versions.pop(0) if len(versions) > 1 else versions[0]

    def popen(argv: Any, **options: Any) -> Process:
        launched.append((argv, options))
        return process

    made = SpawnedOllamaServer(
        "/Applications/Ollama.app/Contents/Resources/ollama",
        tmp_path / "logs",
        environ={
            "HOME": "/Users/x",
            "PATH": "/bin",
            "SECRET_TOKEN": "never",
            "OLLAMA_MODELS": "/m",
        },
        settings={"OLLAMA_FLASH_ATTENTION": "false"},
        popen=popen,
        client_factory=lambda url: Client(),
        sleep=lambda s: None,
        **kwargs,
    )
    return made, launched


def test_a_calibration_runner_starts_on_its_own_port_with_only_what_it_needs(
    tmp_path: Path,
) -> None:
    made, launched = server(tmp_path, ["", "", "0.34.4"], Process(), clock=Clock())
    client = made.start(2)
    assert client.version() == "0.34.4"
    argv, options = launched[0]
    assert argv == ["/Applications/Ollama.app/Contents/Resources/ollama", "serve"]
    env = options["env"]
    assert "SECRET_TOKEN" not in env and env["HOME"] == "/Users/x" and env["OLLAMA_MODELS"] == "/m"
    assert env["OLLAMA_HOST"] == "127.0.0.1:11435" and env["OLLAMA_NUM_PARALLEL"] == "2"
    assert env["OLLAMA_NOPRUNE"] == "true" and env["OLLAMA_FLASH_ATTENTION"] == "false"
    assert made.settings(3)["OLLAMA_NUM_PARALLEL"] == "3"
    assert len(list((tmp_path / "logs").glob("serve-*-p2.log"))) == 1


def test_a_calibration_never_shares_a_port(tmp_path: Path) -> None:
    made, launched = server(tmp_path, ["0.34.4"], Process())
    with pytest.raises(RuntimeError, match="already answers"):
        made.start(1)
    assert launched == []


def test_a_runner_that_dies_or_never_answers_is_reported_with_its_log(tmp_path: Path) -> None:
    made, _ = server(tmp_path, [""], Process(exits=1), clock=Clock())
    with pytest.raises(RuntimeError, match="did not answer"):
        made.start(1)
    silent = Process()
    made, _ = server(tmp_path, [""], silent, clock=Clock(step=100.0), ready_timeout_s=150.0)
    with pytest.raises(RuntimeError, match="did not answer"):
        made.start(1)
    assert silent.terminated


def test_stopping_is_safe_twice_and_kills_a_runner_that_will_not_stop(tmp_path: Path) -> None:
    stubborn = Process(hangs=True)
    made, _ = server(tmp_path, ["", "0.34.4"], stubborn, clock=Clock())
    made.start(1)
    made.stop()
    assert stubborn.terminated and stubborn.killed
    made.stop()
    exited = Process()
    made, _ = server(tmp_path, ["", "0.34.4"], exited, clock=Clock())
    made.start(1)
    exited.exits = 0
    made.stop()
    assert not exited.terminated


LOG = """msg="loading model via llama-server"
llama_kv_cache_iswa: creating non-SWA KV cache, size = 65536 cells
llama_kv_cache:       MTL0 KV buffer size =  1536.00 MiB
llama_kv_cache_iswa: creating     SWA KV cache, size = 768 cells
srv    load_model: initializing, n_slots = 2, n_ctx_slot = 65536, kv_unified = 'false'
slot release: id 0 | stop processing: n_tokens = 70, truncated = 0
slot release: id 1 | stop processing: n_tokens = 70, truncated = 3
common_init: KV cache shifting is not supported for this context
send_error: request (36798 tokens) exceeds the available context size (32768 tokens)
context shift happened
ggml_metal_synchronize: error: command buffer 0 failed with status 5
"""


def test_the_runner_log_is_read_for_slots_cache_loads_and_losses(tmp_path: Path) -> None:
    made, _ = server(tmp_path, ["", "0.34.4"], Process(), clock=Clock())
    assert made.log_facts() == {"readable": False}
    made.start(2)
    log = made._log_path
    assert log is not None
    log.write_text(LOG, encoding="utf-8")
    facts = made.log_facts()
    assert (facts["n_slots"], facts["n_ctx_slot"]) == (2, 65536)
    assert facts["kv_cells"] == {"non-SWA": 65536, "SWA": 768}
    assert facts["buffers"] == ["llama_kv_cache:       MTL0 KV buffer size =  1536.00 MiB"]
    counts = (facts["loads"], facts["truncations"], facts["shifts"], facts["overflows"])
    assert counts == (1, 1, 1, 1) and facts["device_failures"] == 1
    log.write_text("nothing here", encoding="utf-8")
    assert made.log_facts()["n_slots"] is None
    log.unlink()
    assert made.log_facts() == {"readable": False}


# ---------------------------------------------------------------------------------------
# the replay
# ---------------------------------------------------------------------------------------


def test_an_answer_is_compared_by_its_structure_and_by_its_whole() -> None:
    structure, exact = AnswerShape.of(
        {
            "content": "",
            "tool_calls": [
                {"function": {"name": "edit_file", "arguments": {"path": "a", "old": "b"}}},
                "junk",
                {"function": {"name": "shell", "arguments": "x"}},
            ],
        }
    )
    assert structure == "tools:edit_file(old,path);();shell()"
    assert len(exact) == 16
    assert AnswerShape.of({"content": "done ```qwenloop-verdict```"})[0] == "text:fenced"
    assert AnswerShape.of({"content": None})[0] == "text"
    assert AnswerShape.of({"content": "a"})[1] != AnswerShape.of({"content": "b"})[1]


def test_a_turn_is_sent_so_that_it_can_never_be_silently_truncated() -> None:
    replayer = TurnReplayer(FakeClient(), "gpt-oss:20b", num_ctx=65536, num_predict=64, seed=7)
    body = replayer.body([{"role": "user", "content": "x"}], [{"type": "function"}], 64)
    assert body["truncate"] is False and body["shift"] is False and body["stream"] is False
    assert body["options"] == {"temperature": 0.0, "seed": 7, "num_ctx": 65536, "num_predict": 64}
    assert body["tools"] == [{"type": "function"}]
    assert "tools" not in replayer.body([], [], 1)


def test_the_warm_up_loads_the_model_and_is_not_timed() -> None:
    client = FakeClient()
    warm = TurnReplayer(client, "m", num_ctx=8).warm()
    assert warm.ok and warm.turn_id == "warm" and client.chats[0]["options"]["num_predict"] == 8


def test_workers_replay_segments_in_order_and_record_failures() -> None:
    client = FakeClient()
    client.answers = [
        (400, {"error": "exceeds the available context size"}),
        (0, {}),
        (200, {"message": {"content": ""}, "done_reason": ""}),
    ]
    ticks = iter(range(1000))
    replayer = TurnReplayer(client, "m", num_ctx=8, clock=lambda: float(next(ticks)))
    segments = [
        {
            "turns": [
                {"id": "a#1", "messages": [], "recorded_input_tokens": 5},
                {"id": "a#2", "messages": []},
            ],
            "tools": [],
        },
        {"turns": [{"id": "b#1", "messages": []}]},
        {"turns": [{"id": "c#1", "messages": []}]},
        {"turns": [{"id": "d#1", "messages": []}]},
    ]
    outcomes = replayer.run(segments, 2)
    assert len(outcomes) == 5
    assert [o.started_s for o in outcomes] == sorted(o.started_s for o in outcomes)
    failed = sorted(o.error for o in outcomes if not o.ok)
    assert failed[0] == "exceeds the available context size" and failed[1] == "status 0"
    assert "silent failure" in failed[2]
    assert all(o.signature == "" for o in outcomes if not o.ok)
    good = next(o for o in outcomes if o.ok)
    assert (
        good.signature == "tools:read_file(path)" and good.prompt_ms == 2.0 and good.wall_s == 1.0
    )
    assert {o.turn_id for o in outcomes if not o.first_in_segment} <= {"a#2"}
    assert outcome().as_dict()["wall_s"] == 10.0


# ---------------------------------------------------------------------------------------
# the corpus
# ---------------------------------------------------------------------------------------


def pool_run(name: str, depths: list[int], notes: tuple[str, ...] = ()) -> PoolRun:
    return PoolRun(
        run=name,
        source=f"/lanes/{name}",
        tools=[{"type": "function", "function": {"name": "read_file"}}],
        preamble=[{"role": "system", "content": "s"}],
        turns=[
            {
                "turn": i + 1,
                "recorded_input_tokens": d,
                "recorded_output_tokens": 1,
                "after": [{"role": "assistant", "content": f"{name}{i}"}],
            }
            for i, d in enumerate(depths)
        ],
        notes=notes,
    )


def test_a_payload_is_the_preamble_plus_every_earlier_appendix() -> None:
    run = PoolRun(
        run="r",
        source="s",
        tools=[],
        preamble=[{"role": "system", "content": "p"}],
        turns=[
            {
                "before": [{"role": "user", "content": "retry"}],
                "after": [{"role": "assistant", "content": "a1"}],
            },
            {"after": [{"role": "assistant", "content": "a2"}]},
            {"messages": [{"role": "system", "content": "trimmed"}]},
        ],
    )
    assert [m["content"] for m in run.payload(0)] == ["p", "retry"]
    assert [m["content"] for m in run.payload(1)] == ["p", "retry", "a1"]
    assert run.payload(2) == [{"role": "system", "content": "trimmed"}]


def test_a_turn_pool_is_read_line_by_line_and_refuses_another_schema(tmp_path: Path) -> None:
    good = {"schema": POOL_SCHEMA, "run": "r", "preamble": [], "turns": [], "notes": ["n"]}
    path = tmp_path / "pool.jsonl"
    path.write_text(json.dumps(good) + "\n\n", encoding="utf-8")
    runs, sha = TurnPool.load(path)
    assert runs[0].run == "r" and runs[0].notes == ("n",) and len(sha) == 64
    path.write_text(json.dumps({**good, "schema": "other"}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pool.jsonl:1"):
        TurnPool.load(path)


def test_the_sampler_names_its_strata_and_refuses_an_empty_corpus() -> None:
    sampler = CorpusSampler(segments=4, segment_length=1, strata=[32768, 16384])
    assert sampler.labels() == ["0-16383", "16384-32767", ">=32768"]
    assert [sampler.label(t) for t in (0, 16384, 40000)] == ["0-16383", "16384-32767", ">=32768"]
    with pytest.raises(ValueError):
        CorpusSampler(segments=0, segment_length=1, strata=[])


def test_allocation_is_proportional_keeps_the_tail_and_never_exceeds_the_total() -> None:
    sampler = CorpusSampler(segments=10, segment_length=1, strata=[10, 20], min_per_stratum=2)
    assert sampler.allocate({}, {}) == {}
    got = sampler.allocate({"0-9": 90, "10-19": 9, ">=20": 1}, {"0-9": 50, "10-19": 5, ">=20": 1})
    assert got == {"0-9": 7, "10-19": 2, ">=20": 1}
    tight = CorpusSampler(segments=1, segment_length=1, strata=[10, 20], min_per_stratum=1)
    each = {"0-9": 1, "10-19": 1, ">=20": 1}
    assert tight.allocate(each, each) == each


def test_a_corpus_is_stratified_seeded_contiguous_and_says_where_it_came_from() -> None:
    runs = [
        pool_run("a", [100, 200, 30000, 31000]),
        pool_run("b", [150, 250, 400], notes=("args unrecorded",)),
        pool_run("c", [40000, 41000]),
    ]
    sampler = CorpusSampler(
        segments=3, segment_length=2, strata=[1000, 32768], min_per_stratum=1, seed=3
    )
    corpus = sampler.sample(runs)
    assert corpus == sampler.sample(runs)
    assert corpus["population"] == {
        "runs": 3,
        "turns": 9,
        "by_stratum": {"0-999": 5, "1000-32767": 2, ">=32768": 2},
    }
    assert corpus["share_at_or_over"] == {"1000": round(4 / 9, 4), "32768": round(2 / 9, 4)}
    assert corpus["notes"] == ["args unrecorded"]
    assert sum(corpus["allocation"].values()) == len(corpus["segments"]) == 3
    deep = next(s for s in corpus["segments"] if s["stratum"] == ">=32768")
    assert [t["id"] for t in deep["turns"]] == ["c#1", "c#2"]
    assert deep["turns"][1]["messages"][-1] == {"role": "assistant", "content": "c0"}
    assert CorpusSampler.resolve(corpus)[0]["tools"] == runs[0].tools
    empty = CorpusSampler(segments=1, segment_length=1, strata=[10]).sample([])
    assert empty["share_at_or_over"] == {"10": 0.0} and empty["segments"] == []


def test_distinct_runs_are_drawn_before_a_run_is_drawn_twice() -> None:
    assert CorpusSampler._distinct_first([(0, 1), (0, 2), (1, 1), (2, 5), (1, 3)]) == [
        (0, 1),
        (1, 1),
        (2, 5),
        (0, 2),
        (1, 3),
    ]


# ---------------------------------------------------------------------------------------
# the step, the verdict
# ---------------------------------------------------------------------------------------


def test_percentiles_interpolate_and_say_none_for_nothing() -> None:
    assert StepSummary.percentile([], 0.5) is None
    assert StepSummary.percentile([4.0], 0.95) == 4.0
    assert StepSummary.percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5


def test_a_step_is_summarised_with_throughput_latency_errors_and_the_runners_account() -> None:
    outcomes = [
        outcome("a#1", worker=0, started_s=0.0, ended_s=10.0, prompt_tokens=990),
        outcome("a#2", worker=0, started_s=10.0, ended_s=20.0, first_in_segment=False),
        outcome("b#1", worker=1, started_s=0.0, ended_s=15.0, status=400, error="refused"),
        outcome("b#2", worker=1, started_s=15.0, ended_s=16.0, status=0, error="no answer"),
        outcome("b#3", worker=1, started_s=16.0, ended_s=17.0, status=500, error="boom"),
    ]
    summary = StepSummary.build(
        2,
        65536,
        outcomes,
        {"readable": True},
        {"loads": 1, "truncations": 0, "device_failures": 0},
        {"loads": 1, "truncations": 2, "device_failures": 3, "n_slots": 2, "readable": True},
        {"OLLAMA_NUM_PARALLEL": "2"},
    )
    assert summary["errors"] == {"refused (400)": 1, "no answer": 1, "status 500": 1}
    assert summary["ok"] == 2 and summary["wall_s"] == 20.0
    assert summary["throughput_turns_per_hour"] == 360.0
    assert summary["busy_window_s"] == 17.0
    assert summary["busy_throughput_turns_per_hour"] == round(1 / 17 * 3600, 2)
    assert summary["prompt_vs_recorded_p50"] == 0.99  # 0.995, to two places
    server_account = summary["server"]
    assert server_account["truncations_during"] == 2 and server_account["loads_during"] == 0
    assert server_account["device_failures_during"] == 3
    idle = StepSummary.build(3, 8, outcomes[:1], {}, {}, {}, {})
    assert idle["busy_window_s"] == 10.0
    nothing = StepSummary.build(1, 8, [], {}, {}, {}, {})
    assert nothing["throughput_turns_per_hour"] == 0.0
    assert nothing["busy_throughput_turns_per_hour"] == 0.0


def test_agreement_compares_the_same_turns_and_nothing_else() -> None:
    base = {
        "outcomes": [
            outcome("a").as_dict(),
            outcome("b", signature="text").as_dict(),
            outcome("c", error="x").as_dict(),
        ]
    }
    same = {
        "outcomes": [
            outcome("a").as_dict(),
            outcome("b", exact="zzz", signature="text").as_dict(),
            outcome("d").as_dict(),
        ]
    }
    assert StepSummary.agreement(same, base) == {"compared": 2, "structural": 1.0, "exact": 0.5}
    assert StepSummary.agreement({"outcomes": []}, base) == {
        "compared": 0,
        "structural": None,
        "exact": None,
    }


def test_the_verdict_names_every_breach_in_plain_words() -> None:
    verdict = SlotVerdict(SlotBounds())
    first = step(1, 100.0, memory={"swapout_mb_per_minute": 100.0})
    bad = step(
        2,
        150.0,
        memory={
            "readable": False,
            "wired_peak_bytes": 30 * GIB,
            "swapout_mb_per_minute": 500.0,
            "residency": {
                "calibration": {"changes": 2},
                "production": {"models": ["qwen3:14b"]},
            },
        },
        server={
            "loads_during": 1,
            "truncations_during": 1,
            "shifts_during": 2,
            "device_failures_during": 4,
        },
        outcomes=[outcome("r#1", error="refused", status=400).as_dict()],
        fidelity={"structural": 0.5},
        done_reasons={"stop": 1, "load": 1},
    )
    text = " | ".join(verdict.breaches(bad, first, 24 * GIB, 1.0))
    for words in (
        "could not be read",
        "over the",
        "swap-outs ran at 500.0",
        "1 turn(s) that ran at one slot failed here: r#1",
        "structural fidelity 0.5",
        "other than stop or length",
        "1 truncation",
        "2 context shift",
        "4 device failure",
        "loaded or evicted",
        "contaminated",
    ):
        assert words in text
    unjudged = step(2, 1.0)
    del unjudged["fidelity"]
    assert verdict.breaches(unjudged, step(1, 1.0), 24 * GIB, 1.0) == [
        "structural fidelity None is below 0.95"
    ]
    assert verdict.pressure(step(1, 1.0, memory={"wired_peak_bytes": 30 * GIB}), first, 0) == []


def test_the_first_step_is_the_floor_its_pressure_is_reported_never_refusing() -> None:
    first = step(1, 100.0, memory={"wired_peak_bytes": 21 * GIB, "swapout_mb_per_minute": 6000.0})
    judged = SlotVerdict(SlotBounds()).judge(
        {"fingerprint": {"memory_bytes": 24 * GIB}, "steps": [first]}
    )
    assert judged["steps"][0]["within_bounds"] is True
    assert len(judged["steps"][0]["floor_warnings"]) == 2
    assert judged["ideal"] == 1 and judged["stop"] == ""


def test_the_sweep_stops_at_a_broken_bound_and_the_ideal_is_the_last_good_step() -> None:
    evidence = {
        "fingerprint": {"memory_bytes": 24 * GIB},
        "steps": [
            step(1, 100.0),
            step(2, 180.0),
            step(3, 250.0, memory={"wired_peak_bytes": 23 * GIB}),
            step(4, 400.0),
        ],
    }
    judged = SlotVerdict(SlotBounds()).judge(evidence)
    assert judged["stop"].startswith("a bound broke at 3: wired memory peaked")
    assert [j["parallel"] for j in judged["steps"]] == [1, 2, 3]
    assert judged["ideal"] == 2


def test_the_sweep_stops_on_a_plateau_and_the_ideal_is_the_smallest_near_the_best() -> None:
    evidence = {
        "fingerprint": {"memory_bytes": 24 * GIB},
        "self_consistency": {"structural": 0.9},
        "steps": [
            step(1, 100.0),
            step(2, 150.0),
            step(3, 160.0, fidelity={"structural": 0.86}),
            step(4, 158.0),
            step(5, 999.0),
        ],
    }
    judged = SlotVerdict(SlotBounds()).judge(evidence)
    assert judged["stop"].startswith("throughput stopped improving: 2 steps")
    assert judged["ideal"] == 2
    assert SlotVerdict(SlotBounds()).judge({})["ideal"] == 1


# ---------------------------------------------------------------------------------------
# the checkpoint and the sweep
# ---------------------------------------------------------------------------------------


def test_a_checkpoint_keeps_steps_for_exactly_this_sweep(tmp_path: Path) -> None:
    identity = {"fingerprint": "abc", "corpus": "c0ffee", "method": {"seed": 42}}
    kept = SweepCheckpoint(tmp_path, identity)
    assert kept.load("1") is None
    kept.save("1", {"parallel": 1})
    kept.save("extra-2@32768", {"parallel": 2})
    again = SweepCheckpoint(tmp_path, dict(identity))
    assert again.key == kept.key and again.load("1") == {"parallel": 1}
    assert again.load("extra-2@32768") == {"parallel": 2}
    other = SweepCheckpoint(tmp_path, {**identity, "corpus": "different"})
    assert other.key != kept.key and other.load("1") is None
    # A file for this key whose identity does not match is not this sweep's.
    (other.directory).mkdir(parents=True)
    (other.directory / "step-1.json").write_text(json.dumps({"identity": identity, "step": {}}))
    assert other.load("1") is None
    (kept.directory / "step-2.json").write_text("{not json")
    assert kept.load("2") is None


class FakeServer:
    def __init__(self) -> None:
        self.started: list[int] = []
        self.stops = 0

    def start(self, parallel: int) -> FakeClient:
        self.started.append(parallel)
        return FakeClient()

    def stop(self) -> None:
        self.stops += 1

    def log_facts(self) -> dict[str, Any]:
        return {"readable": True, "loads": 1, "n_slots": self.started[-1]}


class FakeReplayer:
    def __init__(
        self, client: Any, num_ctx: int, throughput: dict[int, float], warm_ok: bool = True
    ) -> None:
        self.num_ctx, self.throughput, self.warm_ok = num_ctx, throughput, warm_ok

    def warm(self) -> TurnOutcome:
        if self.warm_ok:
            return outcome("warm")
        return outcome("warm", status=500, error="out of memory")

    def run(self, segments: Any, workers: int) -> list[TurnOutcome]:
        wall = 3600.0 / self.throughput.get(workers, 1.0)
        # The same turn at every concurrency, as a real corpus replays it.
        return [outcome("s#1", ended_s=wall)]


class InstantWatch(MemoryWatch):
    def __enter__(self) -> MemoryWatch:  # type: ignore[override]
        self.sample_once()
        return self

    def __exit__(self, *exc: object) -> None:
        self.sample_once()


REST = HostSample(0.0, 5 * GIB, 50.0, 0, 0, 16384, True)
CURVE = {1: 100.0, 2: 180.0, 3: 185.0, 4: 186.0}


def sweep_with(
    production: FakeClient | None = None, **kwargs: Any
) -> tuple[SlotSweep, FakeServer, list[str]]:
    fake, lines = FakeServer(), []
    made = SlotSweep(
        fake,
        Samples([REST]),
        SlotVerdict(SlotBounds()),
        lambda client, num_ctx: FakeReplayer(client, num_ctx, CURVE),
        production=production,
        log=lines.append,
        watch=InstantWatch,
        **kwargs,
    )
    return made, fake, lines


def test_a_sweep_measures_the_floor_twice_steps_up_and_restores_the_runner() -> None:
    published: list[int] = []
    made, fake, lines = sweep_with(
        FakeClient(),
        max_runs=6,
        extras=[(2, 32768)],
        settings=lambda n: {"OLLAMA_NUM_PARALLEL": str(n)},
        on_step=lambda record: published.append(len(record["steps"])),
    )
    record = made.run([{"turns": []}], 65536, {"memory_bytes": 24 * GIB})
    assert fake.started == [1, 1, 2, 3, 4, 2]
    assert [s["parallel"] for s in record["steps"]] == [1, 2, 3, 4]
    assert record["self_consistency"]["structural"] == 1.0
    assert record["steps"][1]["fidelity"] == {"compared": 1, "structural": 1.0, "exact": 1.0}
    assert record["extras"][0]["num_ctx"] == 32768 and record["contaminated"] is False
    assert record["judgement"]["ideal"] == 2
    first = record["steps"][0]
    assert first["runtime"] == "ollama 0.34.4" and first["discarded_attempts"] == 0
    assert first["memory_at_rest"] == {"wired_bytes": 5 * GIB, "free_percent": 50.0}
    assert fake.stops == len(fake.started) + 1
    assert published == [1, 2, 3, 4, 4]
    assert any(line.startswith("stopping: throughput stopped improving") for line in lines)


def test_a_resumed_sweep_takes_its_kept_steps_and_measures_only_the_rest(tmp_path: Path) -> None:
    identity = {"fingerprint": "abc", "corpus": "c", "method": {}}
    first, fake, _ = sweep_with(max_runs=2, checkpoint=SweepCheckpoint(tmp_path, identity))
    first.run([], 8, {})
    assert fake.started == [1, 1, 2]
    resumed, fake, lines = sweep_with(max_runs=4, checkpoint=SweepCheckpoint(tmp_path, identity))
    record = resumed.run([], 8, {})
    assert fake.started == [3, 4]
    assert [s["parallel"] for s in record["steps"]] == [1, 2, 3, 4]
    assert sum("taken from the checkpoint" in line for line in lines) == 3


def test_a_sweep_that_cannot_load_the_model_says_so_and_still_stops_the_runner() -> None:
    fake = FakeServer()
    sweep = SlotSweep(
        fake,
        Samples([REST]),
        SlotVerdict(SlotBounds()),
        lambda client, num_ctx: FakeReplayer(client, num_ctx, {}, warm_ok=False),
        repeat_baseline=False,
        watch=InstantWatch,
    )
    with pytest.raises(RuntimeError, match="did not load at 1 slot"):
        sweep.run([], 8, {})
    assert fake.stops == 2


def test_a_sweep_without_a_runtime_records_none() -> None:
    class Silent(FakeServer):
        def start(self, parallel: int) -> FakeClient:
            super().start(parallel)
            return FakeClient(version="")

    record = SlotSweep(
        Silent(),
        Samples([REST]),
        SlotVerdict(SlotBounds()),
        lambda client, num_ctx: FakeReplayer(client, num_ctx, {1: 10.0}),
        max_runs=1,
        repeat_baseline=False,
        watch=InstantWatch,
    ).run([], 8, {})
    assert record["steps"][0]["runtime"] == ""
    assert "baseline_repeat" not in record


def production_that_is_busy_for(readings: int) -> FakeClient:
    """A production runner that reports a resident model for its first `readings` readings."""
    seen = {"n": 0}

    def loaded() -> list[dict[str, Any]]:
        seen["n"] += 1
        return [{"name": "gpt-oss:20b", "size": 1}] if seen["n"] <= readings else []

    return FakeClient(loaded=loaded)


def test_a_step_taken_beside_a_busy_production_runner_is_discarded_and_measured_again(
    tmp_path: Path,
) -> None:
    idles: list[int] = []
    checkpoint = SweepCheckpoint(tmp_path, {"k": 1})
    made, fake, lines = sweep_with(
        production_that_is_busy_for(2),
        repeat_baseline=False,
        max_runs=1,
        idle=lambda: bool(idles.append(1)) or True,
        checkpoint=checkpoint,
    )
    record = made.run([], 8, {})
    assert record["contaminated"] is False and fake.started == [1, 1]
    assert record["steps"][0]["discarded_attempts"] == 1 and idles == [1]
    assert any("reading discarded" in line for line in lines)
    assert checkpoint.load("1") is not None


def test_a_sweep_that_never_gets_a_clean_reading_keeps_nothing_and_stops(tmp_path: Path) -> None:
    checkpoint = SweepCheckpoint(tmp_path, {"k": 2})
    made, fake, lines = sweep_with(
        production_that_is_busy_for(999),
        retries=1,
        extras=[(2, 32768)],
        idle=lambda: True,
        checkpoint=checkpoint,
    )
    record = made.run([], 8, {})
    assert record["contaminated"] is True and record["steps"][0]["contaminated"] is True
    assert record["steps"][0]["discarded_attempts"] == 2 and record["extras"] == []
    assert "baseline_repeat" not in record and fake.started == [1, 1]
    assert lines[-1].startswith("stopping: no clean reading")
    assert checkpoint.load("1") is None
    unwatched, _, _ = sweep_with(production_that_is_busy_for(999))
    assert unwatched.run([], 8, {})["steps"][0]["discarded_attempts"] == 1


def test_a_contaminated_repeat_or_extra_taints_the_whole_record() -> None:
    # Two readings per step: the first step is clean, the repeat is not.
    readings = iter([[], [], [{"name": "m"}], [{"name": "m"}]] + [[]] * 99)
    repeat, _, _ = sweep_with(FakeClient(loaded=lambda: next(readings)), max_runs=2)
    record = repeat.run([], 8, {})
    assert record["contaminated"] is True and len(record["steps"]) == 1
    busy_after = {"n": 0}

    def later() -> list[dict[str, Any]]:
        busy_after["n"] += 1
        return [{"name": "m"}] if busy_after["n"] > 6 else []

    extra, _, _ = sweep_with(
        FakeClient(loaded=later), repeat_baseline=False, max_runs=3, extras=[(2, 32768), (3, 8)]
    )
    tainted = extra.run([], 8, {})
    assert tainted["contaminated"] is True and len(tainted["extras"]) == 2
    assert all(e.get("contaminated") for e in tainted["extras"])


# ---------------------------------------------------------------------------------------
# the evidence and the gate
# ---------------------------------------------------------------------------------------


def test_the_store_resolves_writes_reads_and_requests(tmp_path: Path) -> None:
    assert SlotEvidenceStore.resolve("/x", {}) == Path("/x")
    assert SlotEvidenceStore.resolve("", {"VIBEY_GH_SLOTS_DIR": "/y"}) == Path("/y")
    assert SlotEvidenceStore.resolve("", {}) == Path("~/.local/state/vibey-gh/slots").expanduser()
    assert isinstance(SlotEvidenceStore.resolve(), Path)
    store = SlotEvidenceStore(tmp_path / "slots")
    assert store.read("k") is None and not store.requested("k")
    request = store.request("k", "no evidence")
    assert store.requested("k") and json.loads(request.read_text())["reason"] == "no evidence"
    store.request("k", "again")
    assert json.loads(request.read_text())["reason"] == "no evidence"
    written = store.write({"fingerprint_key": "k", "steps": [1]})
    assert written == tmp_path / "slots" / "k.json" and not store.requested("k")
    assert store.read("k") == {"fingerprint_key": "k", "steps": [1]}
    written.write_text("[1, 2]", encoding="utf-8")
    assert store.read("k") is None
    written.write_text("{not json", encoding="utf-8")
    assert store.read("k") is None


NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def evidence_for(
    fp: DeviceFingerprint, *steps_: dict[str, Any], ended: datetime = NOW
) -> dict[str, Any]:
    return {
        "schema": EVIDENCE_SCHEMA,
        "fingerprint": fp.as_dict(),
        "fingerprint_key": fp.key(),
        "cutoff": {"started": ended.isoformat(), "ended": ended.isoformat()},
        "steps": list(steps_) or [step(1, 100.0)],
    }


def gate(days: float = 30.0) -> SlotGate:
    return SlotGate(SlotVerdict(SlotBounds()), max_age_days=days, now=lambda: NOW)


def test_one_is_always_allowed_and_needs_no_evidence() -> None:
    decision = gate().decide(1, None, None)
    assert decision == SlotDecision(
        1, "[local_models] concurrent_runs = 1: one run at a time (8.c)"
    )
    assert decision.as_dict()["notes"] == []


def test_an_unfingerprinted_device_runs_one_and_refuses_a_number() -> None:
    assert gate().decide(MEASURED, None, None).runs == 1
    half = fingerprint(runtime="")
    measured = gate().decide(MEASURED, half, None)
    assert measured.runs == 1 and not measured.refused and "runtime unread" in measured.reason
    assert gate().decide(2, half, None).refused


def test_missing_stale_or_unclean_evidence_means_one_and_asks_for_a_calibration() -> None:
    fp = fingerprint()
    problems = [
        (None, "no calibration evidence"),
        ({**evidence_for(fp), "schema": "other"}, "not a complete, clean calibration"),
        ({**evidence_for(fp), "steps": []}, "not a complete, clean calibration"),
        ({**evidence_for(fp), "contaminated": True}, "not a complete, clean calibration"),
        (evidence_for(fingerprint(model_digest="old")), "stale: model_digest was 'old'"),
        ({**evidence_for(fp), "cutoff": {}}, "does not say when"),
        (evidence_for(fp, ended=NOW - timedelta(days=45)), "measured 45 days ago, beyond 30"),
    ]
    for evidence, words in problems:
        measured = gate().decide(MEASURED, fp, evidence)
        assert (measured.runs, measured.recalibrate, measured.refused) == (1, True, False)
        assert words in measured.reason and "unmeasured or stale means one" in measured.reason
        declared = gate().decide(3, fp, evidence)
        assert declared.refused and declared.runs == 1
        assert "concurrent_runs = 3 refused" in declared.reason


def test_measured_takes_the_ideal_the_evidence_supports_today() -> None:
    fp = fingerprint()
    decision = gate().decide(MEASURED, fp, evidence_for(fp, step(1, 100.0), step(2, 200.0)))
    assert decision.runs == 2 and "measured on this device on 2026-09-24" in decision.reason


def test_a_declared_number_is_allowed_only_where_it_was_measured_inside_every_bound() -> None:
    fp = fingerprint()
    evidence = evidence_for(
        fp,
        step(1, 100.0),
        step(2, 200.0),
        step(3, 205.0),
        step(4, 206.0, memory={"wired_peak_bytes": 23 * GIB}),
    )
    assert gate().decide(2, fp, evidence) == SlotDecision(
        2, "2: measured inside every bound on 2026-09-24"
    )
    assert "was never measured" in gate().decide(5, fp, evidence).reason
    flat = evidence_for(fp, step(1, 100.0), step(2, 105.0), step(3, 106.0))
    assert "no significant gain" in gate().decide(2, fp, flat).reason
    broken = evidence_for(fp, step(1, 100.0), step(2, 200.0, memory={"wired_peak_bytes": 23 * GIB}))
    refused = gate().decide(2, fp, broken)
    assert refused.refused and "broke a bound on this device: wired memory" in refused.reason


def test_the_report_tells_the_whole_curve() -> None:
    fp = fingerprint()
    evidence: dict[str, Any] = {
        **evidence_for(
            fp,
            step(1, 100.0, memory={"swapout_mb_per_minute": 999.0}),
            step(2, 300.0, memory={"wired_peak_bytes": 23 * GIB}),
        ),
        "object": "how many runs",
        "source": {"corpus_sha256": "abcdef0123456789ffff"},
        "corpus": {"segments": 2, "turns": 4},
        "baseline_repeat": step(1, 98.0),
        "extras": [step(2, 50.0, num_ctx=32768, fidelity={})],
        "self_consistency": {"structural": 1.0, "exact": 0.9, "compared": 4},
        "not_measured": ["thermals"],
        "confidence": "four turns",
    }
    evidence["judgement"] = SlotVerdict(SlotBounds()).judge(evidence)
    text = SlotReport.markdown(evidence)
    assert "Ideal concurrent runs: **1**" in text and "a bound broke at 2" in text
    assert "yes (floor: swap-outs ran at 999.0" in text
    assert "no: wired memory peaked" in text and "not judged" in text
    assert "| 2 | 32768 | 2/2 | 50.0 |" in text
    assert "agreed with itself: structural 1.0, exact 0.9 over 4 turns" in text
    assert "## Not measured\n\n- thermals" in text and "## Confidence\n\nfour turns" in text
    assert "**Contaminated:**" not in text
    assert "**Contaminated:**" in SlotReport.markdown({"contaminated": True})
    assert "sweep reached its limit" in SlotReport.markdown({})
    assert SlotReport.bounds_cell({"within_bounds": True}) == "yes"


def test_a_directory_lock_waits_for_its_holder_and_says_so_once(tmp_path: Path) -> None:
    path = tmp_path / "storm" / ".ollama-lock"
    path.parent.mkdir()
    path.mkdir()
    said: list[str] = []
    naps: list[float] = []

    def nap(seconds: float) -> None:
        naps.append(seconds)
        if len(naps) == 2:
            path.rmdir()

    with DirectoryLock(path, poll_s=5.0, sleep=nap, log=said.append):
        assert path.is_dir()
    assert not path.exists() and naps == [5.0, 5.0] and len(said) == 1
    fresh = tmp_path / "wiped" / ".ollama-lock"
    with DirectoryLock(fresh):
        fresh.rmdir()
    assert not fresh.exists() and fresh.parent.is_dir()
