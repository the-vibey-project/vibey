# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh slots`: the calibration of concurrent local runs, as three commands.

- `corpus` draws a stratified corpus of turn segments from a turn pool.
- `calibrate` sweeps N = 1, 2, 3, ... on this device under a shared lock, beside an idle
  production runner, and records the evidence keyed to this device's fingerprint. Each
  completed step is kept at once, so a sweep a reboot interrupts resumes where it stopped.
- `allowed` prints how many runs of the model may run at once here -- the number a queue
  reads -- and says why on standard error. No evidence, or stale evidence, prints 1 and
  requests a calibration, so the gap is closed by the next idle window rather than by
  somebody remembering it.

Every factory that touches the machine is a constructor parameter (ADR-0016); `cli.py`
builds the real ones.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from vibey_gh.interfaces.slot_commands_interface import SlotCommandsInterface
from vibey_gh.slots import (
    EVIDENCE_SCHEMA,
    GB,
    CorpusSampler,
    DeviceFingerprinter,
    DirectoryLock,
    OllamaClient,
    PlatformProbes,
    SlotBounds,
    SlotEvidenceStore,
    SlotGate,
    SlotReport,
    SlotSweep,
    SlotVerdict,
    SpawnedOllamaServer,
    SweepCheckpoint,
    TurnPool,
    TurnReplayer,
)

OLLAMA_URL_ENV = "VIBEY_OLLAMA_URL"


class SlotCommands(SlotCommandsInterface):
    """Composes `vibey_gh.slots` for the command line."""

    def __init__(
        self,
        local_models: Any,
        *,
        fallback_model: str = "",
        fallback_url: str = "http://127.0.0.1:11434",
        environ: Mapping[str, str] | None = None,
        client_factory: Callable[[str], Any] = OllamaClient,
        fingerprinter_factory: Callable[[Any], Any] = DeviceFingerprinter,
        server_factory: Callable[..., Any] = SpawnedOllamaServer,
        sampler_factory: Callable[[], Any] = PlatformProbes.host_sampler,
        lock_factory: Callable[..., AbstractContextManager[Any]] = DirectoryLock,
        which: Callable[[str], str | None] = shutil.which,
        platform_name: str = "",
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        sleep: Callable[[float], None] = time.sleep,
        out: TextIO | None = None,
        err: TextIO | None = None,
    ) -> None:
        self._cfg = local_models
        self._environ = os.environ if environ is None else environ
        self._fallback_model = fallback_model
        self._fallback_url = fallback_url
        self._client_factory = client_factory
        self._fingerprinter_factory = fingerprinter_factory
        self._server_factory = server_factory
        self._sampler_factory = sampler_factory
        self._lock_factory = lock_factory
        self._which = which
        self._platform = platform_name
        self._now = now
        self._sleep = sleep
        self._out = out or sys.stdout
        self._err = err or sys.stderr

    # -- shared -----------------------------------------------------------------------

    def bounds(self) -> SlotBounds:
        cfg = self._cfg
        return SlotBounds(
            wired_ceiling_fraction=cfg.wired_ceiling_fraction,
            swap_growth_factor=cfg.swap_growth_factor,
            swap_floor_mb_per_minute=cfg.swap_floor_mb_per_minute,
            fidelity_tolerance=cfg.fidelity_tolerance,
            min_throughput_gain=cfg.min_throughput_gain,
            max_evidence_age_days=cfg.max_evidence_age_days,
        )

    def model(self, args: Any) -> str:
        return getattr(args, "model", "") or self._cfg.model or self._fallback_model

    def production_url(self, args: Any) -> str:
        explicit = getattr(args, "base_url", "")
        return (explicit or self._environ.get(OLLAMA_URL_ENV) or self._fallback_url).rstrip("/")

    def store(self) -> SlotEvidenceStore:
        return SlotEvidenceStore(SlotEvidenceStore.resolve(self._cfg.evidence_dir, self._environ))

    def binary(self, args: Any) -> str:
        return (
            getattr(args, "binary", "")
            or self._cfg.ollama_binary
            or self._which("ollama")
            or PlatformProbes.default_binary(self._platform)
        )

    def _say(self, line: str) -> None:
        print(f"vibey-gh slots: {line}", file=self._err, flush=True)

    # -- corpus -----------------------------------------------------------------------

    def corpus(self, args: Any) -> int:
        runs, pool_sha = TurnPool.load(Path(args.pool))
        sampler = CorpusSampler(
            segments=args.segments,
            segment_length=args.segment_length,
            strata=[int(edge) for edge in str(args.strata).split(",") if edge.strip()],
            min_per_stratum=args.min_per_stratum,
            seed=args.seed,
        )
        document = sampler.sample(runs)
        document["source"] = {"pool": str(args.pool), "pool_sha256": pool_sha}
        Path(args.out).write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
        turns = sum(len(segment["turns"]) for segment in document["segments"])
        self._say(
            f"{len(document['segments'])} segments, {turns} turns, allocation"
            f" {document['allocation']} from {document['population']['turns']} turns in"
            f" {document['population']['runs']} runs -> {args.out}"
        )
        return 0

    # -- allowed ----------------------------------------------------------------------

    def allowed(self, args: Any) -> int:
        model = self.model(args)
        declared = self._cfg.concurrent_runs
        store = self.store()
        fingerprint = evidence = None
        # One needs no evidence (8.c's floor), so it probes nothing: no command runs, no
        # runner is asked, and no calibration is requested on a device that declared one.
        if declared != 1:
            client = self._client_factory(self.production_url(args))
            fingerprint = self._fingerprinter_factory(client).fingerprint(
                model, self._cfg.context_window
            )
            if not fingerprint.missing:
                evidence = store.read(fingerprint.key())
        gate = SlotGate(
            SlotVerdict(self.bounds()), max_age_days=self._cfg.max_evidence_age_days, now=self._now
        )
        decision = gate.decide(declared, fingerprint, evidence)
        key = fingerprint.key() if fingerprint is not None else ""
        if decision.recalibrate:
            request = store.request(key, decision.reason)
            decision = type(decision)(
                decision.runs,
                decision.reason,
                decision.recalibrate,
                decision.refused,
                (*decision.notes, f"calibration requested: {request}"),
            )
        if getattr(args, "json", False):
            payload = {**decision.as_dict(), "fingerprint_key": key, "model": model}
            print(json.dumps(payload, sort_keys=True), file=self._out)
        else:
            print(decision.runs, file=self._out)
        self._say(f"{decision.runs} concurrent run(s) of {model}: {decision.reason}")
        for note in decision.notes:
            self._say(f"note: {note}")
        return 2 if getattr(args, "strict", False) and decision.refused else 0

    # -- calibrate --------------------------------------------------------------------

    @staticmethod
    def extras(values: list[str] | None) -> list[tuple[int, int]]:
        parsed = []
        for value in values or []:
            parallel, _, num_ctx = value.partition("@")
            if not (parallel.isdigit() and num_ctx.isdigit()):
                raise ValueError(f"--extra takes N@CONTEXT, e.g. 2@32768 (got {value!r})")
            parsed.append((int(parallel), int(num_ctx)))
        return parsed

    @staticmethod
    def settings(values: list[str] | None) -> dict[str, str]:
        parsed = {}
        for value in values or []:
            key, sep, setting = value.partition("=")
            if not sep or not key.startswith("OLLAMA_"):
                raise ValueError(f"--server-setting takes OLLAMA_NAME=VALUE (got {value!r})")
            parsed[key] = setting
        return parsed

    def wait_idle(self, production: Any, wait_s: float) -> bool:
        """Wait, up to `wait_s`, until the production runner has nothing resident."""
        waited = 0.0
        while True:
            loaded = production.loaded()
            if not loaded:
                return True
            if waited >= wait_s:
                return False
            names = [entry.get("name") for entry in loaded]
            self._say(f"production runner holds {names}; waiting for it to idle")
            self._sleep(30)
            waited += 30

    def calibrate(self, args: Any) -> int:
        model = self.model(args)
        context = args.context_window or self._cfg.context_window
        production = self._client_factory(self.production_url(args))
        fingerprint = self._fingerprinter_factory(production).fingerprint(model, context)
        if fingerprint.missing:
            self._say(
                f"this device could not be fingerprinted ({', '.join(fingerprint.missing)} unread);"
                " evidence cannot be keyed to it, so nothing is calibrated"
            )
            return 1
        store = self.store()
        if args.if_requested and not store.requested(fingerprint.key()):
            self._say(f"no calibration requested for {fingerprint.key()}; nothing to do")
            return 0
        corpus_path = Path(args.corpus)
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        segments = CorpusSampler.resolve(corpus)
        lock_path = args.lock or self._cfg.lock
        lock = self._lock_factory(Path(lock_path), log=self._say) if lock_path else nullcontext()
        bounds = self.bounds()
        method = self.method(args, context)
        checkpoint = SweepCheckpoint(
            store.directory / "progress",
            {
                "fingerprint": fingerprint.key(),
                "corpus": corpus.get("sha256", ""),
                "method": method,
            },
        )
        started = self._now()

        def publish(record: Mapping[str, Any], ended: datetime | None = None) -> dict[str, Any]:
            evidence = self.evidence(
                record,
                corpus,
                corpus_path,
                fingerprint,
                bounds,
                args,
                started,
                ended or self._now(),
                model,
                context,
                method,
                checkpoint.key,
            )
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", "utf-8")
                out.with_suffix(".md").write_text(SlotReport.markdown(evidence), "utf-8")
            return evidence

        def partial_evidence(record: Mapping[str, Any]) -> None:
            # After every step, so a sweep a reboot interrupts has published what it measured.
            publish({**record, "partial": True})

        with lock:
            if not self.wait_idle(production, args.wait_idle):
                self._say(
                    "the production runner never went idle; a calibration beside it would"
                    " measure contention"
                )
                return 1
            server = self._server_factory(
                self.binary(args),
                (
                    Path(args.log_dir)
                    if args.log_dir
                    else store.directory / "logs" / fingerprint.key()
                ),
                port=args.port or self._cfg.calibration_port,
                settings=self.settings(args.server_setting),
            )
            sweep = SlotSweep(
                server,
                self._sampler_factory(),
                SlotVerdict(bounds),
                lambda client, num_ctx: TurnReplayer(
                    client, model, num_ctx=num_ctx, num_predict=args.num_predict, seed=args.seed
                ),
                production=production,
                max_runs=args.max_runs or self._cfg.max_runs,
                repeat_baseline=not args.no_repeat_baseline,
                extras=self.extras(args.extra),
                interval_s=args.interval,
                log=self._say,
                settings=server.settings,
                idle=lambda: self.wait_idle(production, args.wait_idle),
                checkpoint=checkpoint,
                on_step=partial_evidence,
            )
            record = sweep.run(segments, context, fingerprint.as_dict())
        evidence = publish(record, self._now())
        print(SlotReport.markdown(evidence), file=self._out)
        if record.get("contaminated"):
            self._say(
                "another runner held a model resident and no clean reading could be taken;"
                " the evidence was NOT recorded for this device"
            )
            return 1
        mismatched = sorted(
            {step.get("runtime", "") for step in record["steps"]} - {fingerprint.runtime}
        )
        if mismatched:
            self._say(
                f"the calibration ran on {mismatched}, not the production {fingerprint.runtime};"
                " the evidence was NOT recorded for this device. Pass --binary for the runner"
                " production uses"
            )
            return 1
        self._say(f"evidence recorded: {store.write(evidence)}")
        return 0

    @staticmethod
    def method(args: Any, context: int) -> dict[str, Any]:
        """What makes two sweeps the same measurement, beside the device and the corpus."""
        return {
            "api": "/api/chat, truncate=false, shift=false, stream=false",
            "temperature": 0.0,
            "seed": args.seed,
            "num_predict": args.num_predict,
            "num_ctx_per_slot": context,
            "workers": "N closed-loop workers for N slots, one segment at a time each",
            "runner": "a separate `ollama serve` per step on its own port, beside an idle"
            " production runner",
            "sampling_interval_s": args.interval,
            "repeat_baseline": not args.no_repeat_baseline,
            "extras": list(args.extra or []),
            "server_settings": dict(SlotCommands.settings(args.server_setting)),
        }

    def evidence(
        self,
        record: Mapping[str, Any],
        corpus: Mapping[str, Any],
        corpus_path: Path,
        fingerprint: Any,
        bounds: SlotBounds,
        args: Any,
        started: datetime,
        ended: datetime,
        model: str,
        context: int,
        method: Mapping[str, Any],
        sweep_key: str,
    ) -> dict[str, Any]:
        steps = record["steps"]
        turns = steps[0]["turns"] if steps else 0
        repeat = record.get("baseline_repeat")
        noise = None
        if repeat and steps and steps[0]["throughput_turns_per_hour"]:
            first = steps[0]["throughput_turns_per_hour"]
            noise = round(abs(repeat["throughput_turns_per_hour"] - first) / first, 4)
        population = corpus.get("population", {})
        memory_gib = round(fingerprint.memory_bytes / 2**30)
        judgement = record.get("judgement") or SlotVerdict(bounds).judge(record)
        return {
            "schema": EVIDENCE_SCHEMA,
            "object": (
                f"how many runs of {model} fit at once on one {fingerprint.hardware}"
                f" ({fingerprint.processor}, {memory_gib} GiB) under {fingerprint.runtime},"
                f" at a {context}-token context per run"
            ),
            "source": {
                "corpus": str(corpus_path),
                "corpus_sha256": corpus.get("sha256", ""),
                "pool": corpus.get("source", {}),
                "population": population,
                "share_at_or_over": corpus.get("share_at_or_over", {}),
                "notes": corpus.get("notes", []),
            },
            "cutoff": {"started": started.isoformat(), "ended": ended.isoformat()},
            "fingerprint": fingerprint.as_dict(),
            "fingerprint_key": fingerprint.key(),
            "sweep_key": sweep_key,
            "method": dict(method),
            "corpus": {
                "segments": len(corpus.get("segments", [])),
                "turns": turns,
                "segment_length": corpus.get("segment_length"),
                "allocation": corpus.get("allocation", {}),
            },
            "bounds": bounds.as_dict(),
            **{key: value for key, value in record.items() if key != "fingerprint"},
            "judgement": judgement,
            "not_measured": [
                (
                    "Other models, other context windows, and other devices: this evidence"
                    " describes one fingerprint."
                ),
                (
                    "Tool execution: only the model's time was replayed. A real lane also runs"
                    " tools between turns, leaving the runner idle, which favours more slots than"
                    " this measures."
                ),
                (
                    f"Whole runs: each segment is {corpus.get('segment_length')} consecutive turns,"
                    " so prefix reuse across a whole lane of dozens of turns was not replayed."
                ),
                (
                    "Thermals and power: no temperature or power draw was read; a throttled or"
                    " battery-powered machine may differ."
                ),
                "Long-horizon stability: each step lasted minutes, not a night.",
                *corpus.get("notes", []),
            ],
            "confidence": (
                f"{turns} turns per step in {len(corpus.get('segments', []))} segments, drawn from"
                f" {population.get('turns')} turns in {population.get('runs')} runs. One slot run"
                " twice differed in throughput by"
                f" {noise if noise is not None else 'an unmeasured share'}"
                " -- a difference between steps smaller than that is noise, not a finding. Peak"
                f" wired memory is a whole-machine reading sampled every {args.interval}s."
                f" Ceiling: {round(bounds.wired_ceiling_fraction * fingerprint.memory_bytes / GB, 2)} GB."
            ),
            "declared": self._cfg.concurrent_runs,
        }
