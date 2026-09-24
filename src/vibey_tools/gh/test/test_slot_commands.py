# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh slots` and `[local_models]`: the composition, with every machine faked."""

from __future__ import annotations

import io
import json
from argparse import Namespace
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import pytest

from vibey_gh import slot_commands
from vibey_gh.cli import main
from vibey_gh.config import LocalModelsConfig, load_config
from vibey_gh.doctor import _check_unknown_keys
from vibey_gh.interfaces.slot_commands_interface import SlotCommandsInterface
from vibey_gh.slot_commands import SlotCommands
from vibey_gh.slots import EVIDENCE_SCHEMA, POOL_SCHEMA, DeviceFingerprint, HostSample

GIB = 2**30
NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def fp(**changes: Any) -> DeviceFingerprint:
    base: dict[str, Any] = dict(
        hardware="Mac17,2",
        processor="Apple M5",
        memory_bytes=24 * GIB,
        accelerator="Apple M5 GPU, 10 cores",
        os="macOS 26.6.2",
        runtime="ollama 0.34.4",
        model="gpt-oss:20b",
        model_digest="dig",
        context_window=65536,
    )
    base.update(changes)
    return DeviceFingerprint(**base)


class Client:
    def __init__(self, url: str = "", loaded: list[Any] | None = None) -> None:
        self.base_url = url
        self.readings = list(loaded) if loaded is not None else [[]]

    def version(self) -> str:
        return "0.34.4"

    def loaded(self) -> Any:
        return self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]

    def digest(self, model: str) -> str:
        return "dig"

    def chat(self, body: Any, timeout_s: float) -> tuple[int, dict[str, Any]]:
        answer = {"message": {"content": "ok"}, "done_reason": "stop"}
        return 200, {**answer, "prompt_eval_count": 1, "eval_count": 1}


class Fingerprinter:
    def __init__(self, result: DeviceFingerprint) -> None:
        self.result = result

    def __call__(self, client: Any) -> Fingerprinter:
        return self

    def fingerprint(self, model: str, context_window: int) -> DeviceFingerprint:
        return self.result


class Server:
    starts: ClassVar[list[int]] = []

    def __init__(
        self,
        binary: str,
        log_dir: Path,
        *,
        port: int,
        settings: dict[str, str],
        runtime: str = "0.34.4",
    ) -> None:
        self.binary, self.log_dir, self.port, self.given = binary, log_dir, port, settings
        self.runtime = runtime

    def settings(self, parallel: int) -> dict[str, str]:
        return {"OLLAMA_NUM_PARALLEL": str(parallel)}

    def start(self, parallel: int) -> Any:
        Server.starts.append(parallel)
        client = Client()
        client.version = lambda: self.runtime  # type: ignore[method-assign]
        return client

    def stop(self) -> None:
        return None

    def log_facts(self) -> dict[str, Any]:
        return {"readable": True}


class Sampler:
    def sample(self) -> HostSample:
        return HostSample(0.0, 5 * GIB, 50.0, 0, 0, 16384, True)


def commands(
    tmp_path: Path,
    *,
    result: DeviceFingerprint | None = None,
    cfg: LocalModelsConfig | None = None,
    **kwargs: Any,
) -> tuple[SlotCommands, io.StringIO, io.StringIO]:
    out, err = io.StringIO(), io.StringIO()
    made = SlotCommands(
        cfg or LocalModelsConfig(evidence_dir=str(tmp_path / "slots")),
        fallback_model="gpt-oss:20b",
        environ={},
        client_factory=lambda url: Client(url),
        fingerprinter_factory=Fingerprinter(result or fp()),
        sampler_factory=Sampler,
        which=lambda name: None,
        platform_name="darwin",
        now=lambda: NOW,
        sleep=lambda seconds: None,
        out=out,
        err=err,
        **kwargs,
    )
    return made, out, err


def test_the_commands_honour_their_seam(tmp_path: Path) -> None:
    assert isinstance(commands(tmp_path)[0], SlotCommandsInterface)
    assert isinstance(SlotCommands(LocalModelsConfig()), SlotCommandsInterface)


def test_settings_resolve_argument_then_declaration_then_default(tmp_path: Path) -> None:
    cfg = LocalModelsConfig(
        model="qwen3:14b", ollama_binary="/opt/ollama", evidence_dir=str(tmp_path)
    )
    made, _, _ = commands(tmp_path, cfg=cfg)
    assert made.model(Namespace(model="x")) == "x" and made.model(Namespace()) == "qwen3:14b"
    assert commands(tmp_path)[0].model(Namespace(model="")) == "gpt-oss:20b"
    assert made.binary(Namespace(binary="/b")) == "/b"
    assert made.binary(Namespace()) == "/opt/ollama"
    assert commands(tmp_path)[0].binary(Namespace()).startswith("/Applications/Ollama.app/")
    linux = SlotCommands(LocalModelsConfig(), which=lambda name: None, platform_name="linux")
    assert linux.binary(Namespace()) == "/usr/local/bin/ollama"
    on_path = SlotCommands(LocalModelsConfig(), which=lambda name: "/usr/bin/ollama")
    assert on_path.binary(Namespace()) == "/usr/bin/ollama"
    env = SlotCommands(LocalModelsConfig(), environ={"VIBEY_OLLAMA_URL": "http://box:11434/"})
    assert env.production_url(Namespace()) == "http://box:11434"
    assert env.production_url(Namespace(base_url="http://a/")) == "http://a"
    assert made.store().directory == tmp_path
    assert made.bounds().min_throughput_gain == 0.10


def test_arguments_for_extras_and_settings_are_parsed_or_refused() -> None:
    assert SlotCommands.extras(None) == []
    assert SlotCommands.extras(["2@32768"]) == [(2, 32768)]
    with pytest.raises(ValueError, match="N@CONTEXT"):
        SlotCommands.extras(["two"])
    assert SlotCommands.settings(["OLLAMA_FLASH_ATTENTION=1"]) == {"OLLAMA_FLASH_ATTENTION": "1"}
    for bad in (["PATH=/x"], ["OLLAMA_X"]):
        with pytest.raises(ValueError, match="OLLAMA_NAME=VALUE"):
            SlotCommands.settings(bad)
    assert SlotCommands.settings(None) == {}


def test_corpus_draws_and_writes_a_corpus(tmp_path: Path) -> None:
    pool = tmp_path / "pool.jsonl"
    turns = [{"recorded_input_tokens": 10}, {"recorded_input_tokens": 40000}]
    line = {"schema": POOL_SCHEMA, "run": "r", "preamble": [], "tools": [], "turns": turns}
    pool.write_text(json.dumps(line) + "\n", encoding="utf-8")
    made, _, err = commands(tmp_path)
    args = Namespace(
        pool=str(pool),
        out=str(tmp_path / "c.json"),
        segments=2,
        segment_length=1,
        strata="32768,",
        min_per_stratum=1,
        seed=0,
    )
    assert made.corpus(args) == 0
    corpus = json.loads((tmp_path / "c.json").read_text())
    assert corpus["source"]["pool"] == str(pool) and len(corpus["segments"]) == 2
    assert "2 segments, 2 turns" in err.getvalue()


def good_evidence(result: DeviceFingerprint) -> dict[str, Any]:
    def step(n: int, t: float) -> dict[str, Any]:
        memory = {
            "readable": True,
            "wired_peak_bytes": 10 * GIB,
            "swapout_mb_per_minute": 1.0,
            "residency": {},
        }
        return {
            "parallel": n,
            "throughput_turns_per_hour": t,
            "done_reasons": {"stop": 1},
            "memory": memory,
            "server": {},
            "outcomes": [],
            "fidelity": {"structural": 1.0},
        }

    return {
        "schema": EVIDENCE_SCHEMA,
        "fingerprint": result.as_dict(),
        "fingerprint_key": result.key(),
        "cutoff": {"ended": NOW.isoformat()},
        "steps": [step(1, 100.0), step(2, 200.0)],
    }


def test_allowed_prints_the_number_and_why(tmp_path: Path) -> None:
    cfg = LocalModelsConfig(concurrent_runs="measured", evidence_dir=str(tmp_path / "slots"))
    made, out, err = commands(tmp_path, cfg=cfg)
    made.store().write(good_evidence(fp()))
    assert made.allowed(Namespace()) == 0
    assert out.getvalue().strip() == "2" and "measured on this device" in err.getvalue()


def test_allowed_with_no_evidence_prints_one_and_requests_a_calibration(tmp_path: Path) -> None:
    cfg = LocalModelsConfig(concurrent_runs="measured", evidence_dir=str(tmp_path / "slots"))
    made, out, err = commands(tmp_path, cfg=cfg)
    assert made.allowed(Namespace(json=True)) == 0
    decision = json.loads(out.getvalue())
    assert decision["runs"] == 1 and decision["recalibrate"] and decision["model"] == "gpt-oss:20b"
    assert decision["notes"][0].startswith("calibration requested: ")
    assert made.store().requested(fp().key())
    assert "note: calibration requested" in err.getvalue()


def test_allowed_strict_exits_two_when_a_declared_number_is_refused(tmp_path: Path) -> None:
    cfg = LocalModelsConfig(concurrent_runs=3, evidence_dir=str(tmp_path / "slots"))
    made, out, _ = commands(tmp_path, cfg=cfg, result=fp(runtime=""))
    assert made.allowed(Namespace(strict=True)) == 2
    assert out.getvalue().strip() == "1"
    assert not made.store().requested(fp(runtime="").key())


def test_allowed_one_probes_nothing_and_requests_nothing(tmp_path: Path) -> None:
    made, out, err = commands(tmp_path)
    made._fingerprinter_factory = None  # type: ignore[assignment]  # never reached
    assert made.allowed(Namespace(json=True)) == 0
    decision = json.loads(out.getvalue())
    assert (decision["runs"], decision["fingerprint_key"], decision["recalibrate"]) == (
        1,
        "",
        False,
    )
    assert "one run at a time (8.c)" in err.getvalue()
    assert not (tmp_path / "slots").exists()


def test_wait_idle_waits_for_production_and_gives_up_when_told(tmp_path: Path) -> None:
    made, _, err = commands(tmp_path)
    assert made.wait_idle(Client(loaded=[[{"name": "m"}], []]), 60) is True
    assert "waiting for it to idle" in err.getvalue()
    assert made.wait_idle(Client(loaded=[[{"name": "m"}]]), 0) is False
    assert made.wait_idle(Client(loaded=[None]), 0) is True


def calibrate_args(corpus: Path, **changes: Any) -> Namespace:
    base: dict[str, Any] = dict(
        corpus=str(corpus),
        model="",
        context_window=0,
        base_url="",
        binary="/bin/ollama",
        port=0,
        max_runs=2,
        num_predict=16,
        seed=1,
        no_repeat_baseline=True,
        extra=None,
        server_setting=None,
        interval=0.001,
        lock="",
        wait_idle=0.0,
        if_requested=False,
        log_dir="",
        out="",
    )
    base.update(changes)
    return Namespace(**base)


def a_corpus(tmp_path: Path) -> Path:
    path = tmp_path / "corpus.json"
    corpus = {
        "sha256": "c0ffee",
        "segment_length": 1,
        "population": {"runs": 1, "turns": 1},
        "tools": {},
        "notes": ["storm-shaped"],
        "segments": [
            {"tools_ref": "", "turns": [{"id": "r#1", "messages": [], "recorded_input_tokens": 1}]}
        ],
    }
    path.write_text(json.dumps(corpus), encoding="utf-8")
    return path


def test_calibrate_refuses_a_device_it_cannot_fingerprint(tmp_path: Path) -> None:
    made, _, err = commands(tmp_path, result=fp(hardware=""))
    assert made.calibrate(calibrate_args(a_corpus(tmp_path))) == 1
    assert "could not be fingerprinted (hardware unread)" in err.getvalue()


def test_calibrate_if_requested_does_nothing_unrequested(tmp_path: Path) -> None:
    made, _, err = commands(tmp_path)
    assert made.calibrate(calibrate_args(a_corpus(tmp_path), if_requested=True)) == 0
    assert "nothing to do" in err.getvalue()


def test_calibrate_never_measures_beside_a_busy_production_runner(tmp_path: Path) -> None:
    made, _, err = commands(tmp_path)
    made._client_factory = lambda url: Client(url, loaded=[[{"name": "qwen3:14b"}]])  # type: ignore[assignment]
    assert made.calibrate(calibrate_args(a_corpus(tmp_path))) == 1
    assert "never went idle" in err.getvalue()


def test_calibrate_sweeps_records_evidence_and_publishes_after_every_step(tmp_path: Path) -> None:
    locks: list[Path] = []

    @contextmanager
    def lock(path: Path, log: Any) -> Any:
        locks.append(path)
        yield

    made, out, err = commands(tmp_path, server_factory=Server, lock_factory=lock)
    made.store().request(fp().key(), "asked")
    out_file = tmp_path / "run" / "evidence.json"
    args = calibrate_args(
        a_corpus(tmp_path),
        if_requested=True,
        lock=str(tmp_path / ".ollama-lock"),
        out=str(out_file),
        log_dir=str(tmp_path / "logs"),
        no_repeat_baseline=False,
        extra=["2@32768"],
        server_setting=["OLLAMA_FLASH_ATTENTION=false"],
    )
    assert made.calibrate(args) == 0
    evidence = json.loads(out_file.read_text())
    assert evidence["fingerprint_key"] == fp().key() and evidence["schema"] == EVIDENCE_SCHEMA
    assert evidence["source"]["corpus_sha256"] == "c0ffee" and "partial" not in evidence
    assert "storm-shaped" in evidence["not_measured"]
    assert "differed in throughput by " in evidence["confidence"]
    assert evidence["extras"][0]["num_ctx"] == 32768 and evidence["declared"] == 1
    assert evidence["method"]["server_settings"] == {"OLLAMA_FLASH_ATTENTION": "false"}
    assert out_file.with_suffix(".md").read_text().startswith("# Slot calibration")
    assert made.store().read(fp().key())["sweep_key"] == evidence["sweep_key"]
    assert not made.store().requested(fp().key())
    assert locks == [tmp_path / ".ollama-lock"]
    assert "evidence recorded" in err.getvalue() and "# Slot calibration" in out.getvalue()
    progress = tmp_path / "slots" / "progress" / evidence["sweep_key"]
    assert sorted(p.name for p in progress.iterdir()) == [
        "step-1-repeat.json",
        "step-1.json",
        "step-2.json",
        "step-extra-2@32768.json",
    ]


def test_a_calibration_resumes_from_its_checkpoint(tmp_path: Path) -> None:
    Server.starts = []
    made, _, err = commands(tmp_path, server_factory=Server)
    assert made.calibrate(calibrate_args(a_corpus(tmp_path), max_runs=1)) == 0
    assert Server.starts == [1]
    assert made.calibrate(calibrate_args(a_corpus(tmp_path), max_runs=2)) == 0
    assert Server.starts == [1, 2]
    assert "1: taken from the checkpoint" in err.getvalue()


def test_the_machine_declared_lock_is_taken_when_no_flag_names_one(tmp_path: Path) -> None:
    taken: list[Path] = []

    @contextmanager
    def lock(path: Path, log: Any) -> Any:
        taken.append(path)
        yield

    made, _, _ = commands(tmp_path, server_factory=Server, lock_factory=lock)
    made._environ = {"VIBEY_OLLAMA_LOCK": str(tmp_path / "shared.lock")}
    assert made.calibrate(calibrate_args(a_corpus(tmp_path), max_runs=1)) == 0
    assert taken == [tmp_path / "shared.lock"]


def test_calibrate_on_another_runtime_records_nothing_for_this_device(tmp_path: Path) -> None:
    def elsewhere(*a: Any, **k: Any) -> Server:
        return Server(*a, runtime="0.32.15", **k)

    made, _, err = commands(tmp_path, server_factory=elsewhere)
    assert made.calibrate(calibrate_args(a_corpus(tmp_path))) == 1
    assert "was NOT recorded" in err.getvalue() and "ollama 0.32.15" in err.getvalue()
    assert made.store().read(fp().key()) is None


def test_calibrate_records_nothing_when_no_clean_reading_could_be_taken(tmp_path: Path) -> None:
    made, _, err = commands(tmp_path, server_factory=Server)
    busy = [[], [{"name": "gpt-oss:20b"}]]
    made._client_factory = lambda url: Client(url, loaded=busy)  # type: ignore[assignment]
    out_file = tmp_path / "evidence.json"
    assert made.calibrate(calibrate_args(a_corpus(tmp_path), out=str(out_file))) == 1
    assert "no clean reading could be taken" in err.getvalue()
    assert json.loads(out_file.read_text())["contaminated"] is True
    assert made.store().read(fp().key()) is None


def test_the_evidence_without_a_repeat_says_the_noise_is_unmeasured(tmp_path: Path) -> None:
    made, _, _ = commands(tmp_path)
    args = Namespace(seed=1, num_predict=2, interval=1.0)
    evidence = made.evidence(
        {"steps": []}, {}, Path("c.json"), fp(), made.bounds(), args, NOW, NOW, "m", 8, {}, "k"
    )
    assert "an unmeasured share" in evidence["confidence"] and evidence["corpus"]["turns"] == 0
    assert evidence["judgement"]["ideal"] == 1
    first = {"parallel": 1, "turns": 60, "throughput_turns_per_hour": 150.0}
    measured = made.evidence(
        {"steps": [first], "baseline_repeat": {"throughput_turns_per_hour": 165.0}},
        {},
        Path("c.json"),
        fp(),
        made.bounds(),
        args,
        NOW,
        NOW,
        "m",
        8,
        {},
        "k",
    )
    assert "differed in throughput by 0.1 --" in measured["confidence"]


# ---------------------------------------------------------------------------------------
# the command line and the configuration
# ---------------------------------------------------------------------------------------


def test_the_cli_dispatches_to_the_slot_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    seen: list[Any] = []

    class Recorder:
        def __init__(self, local_models: Any, **kwargs: Any) -> None:
            seen.append((local_models, kwargs))

        def allowed(self, args: Any) -> int:
            seen.append(args.slots_action)
            return 0

    monkeypatch.setattr(slot_commands, "SlotCommands", Recorder)
    assert main(["slots", "allowed", "--json"]) == 0
    assert seen[0][1]["fallback_model"] == "gpt-oss:20b" and seen[1] == "allowed"


def test_local_models_is_declared_validated_and_known_to_the_doctor(tmp_path: Path) -> None:
    (tmp_path / ".vibey-gh.toml").write_text(
        '[local_models]\nconcurrent_runs = "measured"\nmodel = "gpt-oss:20b"\n'
        "wired_ceiling_fraction = 0.75\n",
        encoding="utf-8",
    )
    cfg = load_config(tmp_path).local_models
    assert (cfg.concurrent_runs, cfg.model, cfg.wired_ceiling_fraction) == (
        "measured",
        "gpt-oss:20b",
        0.75,
    )
    assert _check_unknown_keys(tmp_path) == []
    assert LocalModelsConfig.from_table({"concurrent_runs": 2, "stray": 1}).concurrent_runs == 2
    for bad, words in (
        ({"concurrent_runs": 0}, "whole number"),
        ({"concurrent_runs": "two"}, "whole number"),
        ({"concurrent_runs": True}, "whole number"),
        ({"context_window": 0}, "at least 1"),
        ({"wired_ceiling_fraction": 1.5}, "at most 1"),
        ({"fidelity_tolerance": -0.1}, "must not be negative"),
    ):
        with pytest.raises(ValueError, match=words):
            LocalModelsConfig(**bad)
