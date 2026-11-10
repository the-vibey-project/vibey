# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which open-weights model should drive the sovereign BUILD loop: measured, not assumed.

    python scripts/model_quality_study.py screen  [--models a,b]
    python scripts/model_quality_study.py run     [--models a,b] [--set screening|confirmation|all]
    python scripts/model_quality_study.py summary [--set confirmation]
    python scripts/model_quality_study.py check

The protocol is `research/model-quality/PREREGISTRATION.md`; every value it fixes is in
`scripts/model_quality_study.toml`. One trial drives the real `qwenloop run` in a fresh git
repository, then scores the result with hidden tests the model never saw, plus lint and type
checks, the way `build_verify_handler` scores a work item. The model's own tests passing counts
for nothing. Results go to a digest-chained ledger (`CanaryLedger`, 10.e); a run resumes by
skipping every (model, task, trial) already in it, so a crash re-runs one trial and no more.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vibey_gh.review_canary import CanaryLedger, WilsonInterval

# The storm's tools sit under docs/plans; the durability gate that refuses volatile storage
# (10.h, exit 78) lives there, and is reused rather than reimplemented (10.e).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/plans/qwenstorm-3.0.0/tools"))
import storm_durability  # noqa: E402 - after the path it is found on

try:
    from scripts.interfaces.model_quality_study_interface import (
        ClockInterface,
        CommandRunnerInterface,
        ModelPreparerInterface,
        StudyLedgerInterface,
        StudySummarizerInterface,
        TaskLoaderInterface,
        TrialRunnerInterface,
        TrialScorerInterface,
        WorkspaceInterface,
    )
    from scripts.minimum_specs import IdleGate, LlamaServerLog, SubprocessRunner
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.model_quality_study_interface import (  # type: ignore[import-not-found,no-redef]
        ClockInterface,
        CommandRunnerInterface,
        ModelPreparerInterface,
        StudyLedgerInterface,
        StudySummarizerInterface,
        TaskLoaderInterface,
        TrialRunnerInterface,
        TrialScorerInterface,
        WorkspaceInterface,
    )
    from minimum_specs import (  # type: ignore[import-not-found,no-redef]
        IdleGate,
        LlamaServerLog,
        SubprocessRunner,
    )

SCRIPT = "scripts/model_quality_study.py"
DEFAULT_CONFIG = "scripts/model_quality_study.toml"
RECORD_FORMAT = "vibey/model-quality/1"
RECORD_KIND = "TrialMeasured"
TIERS = ("t1", "t2", "t3", "t4")
LANGUAGES = ("python", "typescript")
#: Where a failed check lands in the failure vocabulary the preregistration records.
FAILURE_OF_CHECK = {"hidden": "wrong_behaviour", "lint": "lint", "types": "types"}
GIB = 1024**3


@dataclass(frozen=True)
class Settings:
    raw: Mapping[str, Any]
    models: tuple[Mapping[str, Any], ...]

    @classmethod
    def load(cls, path: Path) -> Settings:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls(data["study"], tuple(data["model"]))

    def __getattr__(self, name: str) -> Any:
        try:
            return self.raw[name]
        except KeyError:
            raise AttributeError(name) from None


# ------------------------------------------------------------------------ tasks


@dataclass(frozen=True)
class Check:
    name: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class Task:
    id: str
    tier: str
    language: str
    expected_files: tuple[str, ...]
    checks: tuple[Check, ...]
    directory: Path

    @property
    def plan(self) -> str:
        return (self.directory / "plan.md").read_text(encoding="utf-8")


class TaskLoader(TaskLoaderInterface):
    """Reads `<root>/<id>/{task.toml,plan.md,seed/,hidden/}`; a bad task is refused by name."""

    def load_all(self, root: Path) -> tuple[Task, ...]:
        tasks = [self._load(path.parent) for path in sorted(root.glob("*/task.toml"))]
        return tuple(tasks)

    def _load(self, directory: Path) -> Task:
        name = directory.name
        try:
            data = tomllib.loads((directory / "task.toml").read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise ValueError(f"task {name}: task.toml is not TOML: {exc}") from exc
        problems: list[str] = []
        if data.get("id") != name:
            problems.append(f"id must equal the directory name {name!r}")
        if data.get("tier") not in TIERS:
            problems.append(f"tier must be one of {TIERS}")
        if data.get("language") not in LANGUAGES:
            problems.append(f"language must be one of {LANGUAGES}")
        checks = tuple(
            Check(str(item["name"]), tuple(map(str, item["argv"])))
            for item in data.get("check", [])
            if "name" in item and "argv" in item
        )
        if not checks:
            problems.append("at least one [[check]] with a name and argv is required")
        if not (directory / "plan.md").is_file():
            problems.append("plan.md is missing")
        if not (directory / "seed").is_dir():
            problems.append("seed/ is missing")
        hidden = directory / "hidden"
        if not hidden.is_dir() or not any(p.is_file() for p in hidden.rglob("*")):
            problems.append("hidden/ must hold at least one test the model never sees")
        if problems:
            raise ValueError(f"task {name}: " + "; ".join(problems))
        return Task(
            name,
            data["tier"],
            data["language"],
            tuple(map(str, data.get("expected_files", []))),
            checks,
            directory,
        )

    def split(
        self, tasks: Sequence[Task], *, screening: int, seed: int
    ) -> tuple[tuple[Task, ...], tuple[Task, ...]]:
        """A seeded shuffle, dealt round-robin across tiers so screening mirrors the corpus."""
        rng = random.Random(seed)  # noqa: S311 - a reproducible split, not a secret
        by_tier: dict[str, list[Task]] = defaultdict(list)
        for task in tasks:
            by_tier[task.tier].append(task)
        for tier in by_tier:
            rng.shuffle(by_tier[tier])
        chosen: list[Task] = []
        while len(chosen) < min(screening, len(tasks)):
            for tier in sorted(by_tier):
                if by_tier[tier] and len(chosen) < screening:
                    chosen.append(by_tier[tier].pop())
        taken = {task.id for task in chosen}
        rest = [task for task in tasks if task.id not in taken]
        return (
            tuple(sorted(chosen, key=lambda task: task.id)),
            tuple(sorted(rest, key=lambda task: task.id)),
        )


# ------------------------------------------------------------------------ one trial


class Workspace(WorkspaceInterface):
    """A fresh git repository per trial: the seed and the plan, never the hidden tests."""

    def create(self, task: Task, parent: Path) -> Path:
        parent.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=f"{task.id}-", dir=parent))
        shutil.copytree(task.directory / "seed", work, dirs_exist_ok=True)
        shutil.copy2(task.directory / "plan.md", work / "plan.md")
        git = ["git", "-c", "user.email=study@vibey.invalid", "-c", "user.name=study"]
        for argv in (["git", "init", "-q"], [*git, "add", "."], [*git, "commit", "-qm", "seed"]):
            subprocess.run(argv, cwd=work, check=True, capture_output=True)  # noqa: S603
        return work


@dataclass(frozen=True)
class EventTally:
    turns: int = 0
    tool_calls: int = 0
    parse_retries: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    finished: bool = False
    tools: Mapping[str, int] = field(default_factory=dict)

    @property
    def parse_rate(self) -> float | None:
        """The share of attempted tool calls that parsed: calls / (calls + retries)."""
        attempts = self.tool_calls + self.parse_retries
        return self.tool_calls / attempts if attempts else None

    @classmethod
    def parse(cls, text: str) -> EventTally:
        turns = calls = retries = tokens_in = tokens_out = 0
        finished = False
        tools: Counter[str] = Counter()
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("type") if isinstance(event, dict) else None
            if kind == "turn.completed":
                turns += 1
                tokens_in += int(event.get("input_tokens") or 0)
                tokens_out += int(event.get("output_tokens") or 0)
            elif kind == "tool.call":
                calls += 1
                tools[str(event.get("name"))] += 1
            elif kind == "turn.retried":
                retries += 1
            elif kind == "completed":
                finished = True
        return cls(turns, calls, retries, tokens_in, tokens_out, finished, dict(tools))

    def to_dict(self) -> dict[str, Any]:
        return {
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "parse_retries": self.parse_retries,
            "parse_rate": self.parse_rate,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "finished": self.finished,
            "tools": dict(self.tools),
        }


class QwenloopRunner(TrialRunnerInterface):
    """Drives the real `qwenloop run`, as the October benchmark did, and reads its events."""

    def __init__(self, settings: Settings, commands: CommandRunnerInterface) -> None:
        self._settings = settings
        self._commands = commands

    def run(self, *, workspace: Path, tag: str, plan: str) -> Mapping[str, Any]:
        argv = [
            *self._settings.runner_argv,
            "run",
            str(workspace / plan),
            "--cwd",
            str(workspace),
            "--backend",
            "openai-compat",
            "--base-url",
            self._settings.base_url,
            "--max-turns",
            str(self._settings.max_turns),
        ]
        started = time.monotonic()
        result = self._commands.run(
            argv, timeout=self._settings.wall_s, env={"QWENLOOP_MODEL": tag}
        )
        seconds = round(time.monotonic() - started, 1)
        events = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(workspace.glob(".qwenloop/runs/*/events.jsonl"))
        )
        return {
            "exit": result.returncode,
            "timed_out": result.returncode == 124,
            "seconds": seconds,
            **EventTally.parse(events).to_dict(),
        }


class TrialScorer(TrialScorerInterface):
    """The hidden tests, copied in only now, then every declared check, in order."""

    def __init__(self, commands: CommandRunnerInterface, *, timeout: float) -> None:
        self._commands = commands
        self._timeout = timeout

    def score(self, task: Task, workspace: Path) -> Mapping[str, Any]:
        missing = [name for name in task.expected_files if not (workspace / name).is_file()]
        if missing:
            return {"solved": False, "failure": "no_files", "checks": {}, "missing": missing}
        shutil.copytree(task.directory / "hidden", workspace / "hidden", dirs_exist_ok=True)
        outcomes: dict[str, bool] = {}
        failure: str | None = None
        for check in task.checks:
            result = self._commands.run(check.argv, cwd=str(workspace), timeout=self._timeout)
            passed = result.returncode == 0
            outcomes[check.name] = passed
            if not passed and failure is None:
                failure = (
                    "check_timeout"
                    if result.returncode == 124
                    else FAILURE_OF_CHECK.get(check.name, check.name)
                )
        return {"solved": failure is None, "failure": failure, "checks": outcomes}


# ------------------------------------------------------------------------ models


class OllamaApi:
    """The three Ollama calls the study makes; a seam so tests never need a server."""

    def __init__(self, url: str, probe: Any = None) -> None:
        self._url = url.rstrip("/")
        self._probe = probe

    def _post(self, path: str, body: Mapping[str, Any], timeout: float = 600) -> Any:
        request = urllib.request.Request(  # noqa: S310 - the local Ollama the run uses anyway
            f"{self._url}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read() or b"{}")

    def probe(self, tag: str) -> frozenset[str] | None:
        if self._probe is None:
            from qwenloop.infrastructure.ollama_probe import OllamaModelProbe

            self._probe = OllamaModelProbe()
        return self._probe.capabilities(self._url + "/v1", tag)  # type: ignore[no-any-return]

    def create(self, name: str, modelfile: str) -> None:
        self._post("/api/create", {"model": name, "modelfile": modelfile, "stream": False})

    def resident_bytes(self, name: str) -> int:
        """Load the model at its derived context, read what Ollama holds, then unload it."""
        self._post(
            "/api/generate",
            {"model": name, "prompt": "ok", "stream": False, "options": {"num_predict": 1}},
        )
        with urllib.request.urlopen(f"{self._url}/api/ps", timeout=30) as response:  # noqa: S310
            loaded = json.loads(response.read()).get("models", [])
        size = next(
            (int(m.get("size", 0)) for m in loaded if m.get("name", "").startswith(name)), 0
        )
        self._post("/api/generate", {"model": name, "keep_alive": 0, "stream": False})
        return size


class ModelPreparer(ModelPreparerInterface):
    """Screens a candidate by the entry rules of the preregistration and builds its 32k tag."""

    def __init__(self, ollama: Any, settings: Settings) -> None:
        self._ollama = ollama
        self._settings = settings

    @staticmethod
    def derived_name(entry: Mapping[str, Any], num_ctx: int) -> str:
        return f"mq-{entry['key']}-{num_ctx}"

    def derive(self, entry: Mapping[str, Any], num_ctx: int) -> str:
        name = self.derived_name(entry, num_ctx)
        self._ollama.create(name, f"FROM {entry['tag']}\nPARAMETER num_ctx {num_ctx}\n")
        return name

    def screen(self, entry: Mapping[str, Any]) -> Mapping[str, Any]:
        reasons: list[str] = []
        capabilities = self._ollama.probe(entry["tag"])
        tools = capabilities is not None and "tools" in capabilities
        if not tools:
            reasons.append("no tool-calling reported by Ollama")
        resident_gib: float | None = None
        derived: str | None = None
        fits = False
        if tools:
            derived = self.derive(entry, self._settings.num_ctx)
            resident_gib = round(self._ollama.resident_bytes(derived) / GIB, 2)
            fits = resident_gib <= float(self._settings.max_resident_gib)
            if not fits:
                reasons.append(
                    f"resident {resident_gib} GiB at {self._settings.num_ctx} tokens exceeds "
                    f"{self._settings.max_resident_gib} GiB"
                )
        runnable = tools and fits
        licence_ok = bool(entry.get("license_spdx")) and bool(entry.get("license_osi"))
        if not entry.get("license_spdx"):
            reasons.append("licence not recorded, so treated as non-OSI")
        elif not entry.get("license_osi"):
            reasons.append("licence is not OSI-approved: measured for reference, never the default")
        return {
            "key": entry["key"],
            "eligible": runnable and licence_ok and not entry.get("reference_only", False),
            "runnable": runnable,
            "reasons": reasons,
            "capabilities": sorted(capabilities or ()),
            "resident_gib": resident_gib,
            "derived_tag": derived,
        }


# ------------------------------------------------------------------------ ledger, summary


class StudyLedger(StudyLedgerInterface):
    """One digest-chained line per trial, in the family's own ledger (`CanaryLedger`)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._ledger = CanaryLedger(record_format=RECORD_FORMAT, kind=RECORD_KIND)

    def append(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self._ledger.read(self._path)  # a broken chain stops the run before it adds to it
        return self._ledger.append(self._path, payload)

    def read(self) -> tuple[Mapping[str, Any], ...]:
        return self._ledger.read(self._path)

    def done(self) -> set[tuple[str, str, int]]:
        return {(str(r["model"]), str(r["task"]), int(r["trial"])) for r in self.read()}


class StudySummarizer(StudySummarizerInterface):
    def __init__(self) -> None:
        self._wilson = WilsonInterval()

    def _cell(self, solved: int, n: int, z: float) -> dict[str, Any]:
        bounds = self._wilson.bounds(solved, n, z)
        return {
            "solved": solved,
            "n": n,
            "rate": solved / n if n else None,
            "wilson": None if bounds is None else (round(bounds[0], 4), round(bounds[1], 4)),
        }

    def summarize(self, trials: Sequence[Mapping[str, Any]], z: float) -> Mapping[str, Any]:
        by_model: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in trials:
            by_model[str(row["model"])].append(row)
        models: dict[str, Any] = {}
        for key, rows in sorted(by_model.items()):
            cell = self._cell(sum(1 for r in rows if r["solved"]), len(rows), z)
            tiers: dict[str, Any] = {}
            for tier in sorted({str(r["tier"]) for r in rows}):
                inner = [r for r in rows if r["tier"] == tier]
                tiers[tier] = self._cell(sum(1 for r in inner if r["solved"]), len(inner), z)
            cell["tiers"] = tiers
            cell["seconds_mean"] = round(sum(float(r["seconds"]) for r in rows) / len(rows), 1)
            cell["failures"] = dict(Counter(r["failure"] for r in rows if r.get("failure")))
            models[key] = cell
        return {"z": z, "models": models}

    def decide(
        self, summary: Mapping[str, Any], models: Sequence[Mapping[str, Any]]
    ) -> Mapping[str, Any]:
        """Preregistration section 6: rank by solve rate; speed breaks a tie only inside an
        overlap of Wilson intervals; the default must be OSI-licensed and not a reference."""
        measured = summary["models"]
        info = {str(m["key"]): m for m in models}
        keys = [key for key in measured if key in info]
        ranking = sorted(keys, key=lambda k: (-measured[k]["rate"], measured[k]["seconds_mean"]))
        reasons: dict[str, str] = {}
        eligible = [
            k for k in ranking if info[k].get("license_osi") and not info[k].get("reference_only")
        ]
        for key in ranking:
            if key not in eligible:
                reasons[key] = "licence is not OSI-approved or the model is a reference point"
        if not eligible:
            reasons["_"] = "no OSI-licensed model was measured, so there is no default to pick"
            return {"default": None, "ranking": ranking, "reasons": reasons}
        leader = eligible[0]
        low, high = measured[leader]["wilson"]
        tied = [
            k
            for k in eligible
            if measured[k]["wilson"][0] <= high and measured[k]["wilson"][1] >= low
        ]
        winner = min(tied, key=lambda k: (measured[k]["seconds_mean"], -measured[k]["rate"]))
        if len(tied) > 1:
            reasons[winner] = (
                f"intervals overlap the leader's ({', '.join(tied)}); the fastest wins the tie"
            )
        else:
            reasons[winner] = "highest solve rate among OSI-licensed models, intervals clear"
        return {"default": winner, "ranking": ranking, "reasons": reasons}


# ------------------------------------------------------------------------ orchestration


class SystemClock(ClockInterface):
    def now(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class StudyRunner:
    """Walks model x task x trial, skipping what the ledger already holds."""

    def __init__(
        self,
        settings: Settings,
        ledger: StudyLedger,
        runner: TrialRunnerInterface,
        scorer: TrialScorerInterface,
        workspace: WorkspaceInterface,
        preparer: ModelPreparerInterface,
        idle: Any,
        clock: ClockInterface,
        trials_root: Path,
    ) -> None:
        self._s = settings
        self._ledger = ledger
        self._runner = runner
        self._scorer = scorer
        self._workspace = workspace
        self._preparer = preparer
        self._idle = idle
        self._clock = clock
        self._root = trials_root

    def run(
        self,
        models: Sequence[Mapping[str, Any]],
        sets: Mapping[str, Sequence[Task]],
        host: Mapping[str, Any],
    ) -> int:
        done = self._ledger.done()
        ran = 0
        for entry in models:
            tag: str | None = None
            for set_name, tasks in sets.items():
                for task in tasks:
                    for number in range(1, int(self._s.trials) + 1):
                        if (str(entry["key"]), task.id, number) in done:
                            continue
                        quiet, why, conditions = self._idle.wait()
                        if not quiet:
                            print(f"stopping: {why}", file=sys.stderr)
                            return ran
                        tag = tag or self._preparer.derive(entry, int(self._s.num_ctx))
                        work = self._workspace.create(task, self._root)
                        outcome = self._runner.run(workspace=work, tag=tag, plan="plan.md")
                        score = self._scorer.score(task, work)
                        self._ledger.append(
                            {
                                "model": entry["key"],
                                "tag": entry["tag"],
                                "derived_tag": tag,
                                "task": task.id,
                                "tier": task.tier,
                                "set": set_name,
                                "trial": number,
                                "recorded": self._clock.now(),
                                "host": dict(host),
                                "conditions": conditions,
                                "workspace": str(work),
                                "solved": score["solved"],
                                "failure": score["failure"],
                                "checks": score["checks"],
                                **{k: outcome[k] for k in outcome},
                            }
                        )
                        ran += 1
        return ran


class TrialHome:
    """Where trial repositories live: under the storm home, refused when that is volatile."""

    @staticmethod
    def resolve(settings: Settings) -> Path:
        home, _ = storm_durability.StormHome(os.environ).resolve()
        root = home / settings.trials_subdir
        storm_durability.DurabilityGate(storm_durability.VolatileLocations(os.environ)).enforce(
            {"trial repositories": root}, "VIBEY_STORM_HOME"
        )
        return root


# ------------------------------------------------------------------------ command line


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _pick(settings: Settings, keys: str | None) -> list[Mapping[str, Any]]:
    wanted = set(keys.split(",")) if keys else None
    chosen = [m for m in settings.models if wanted is None or m["key"] in wanted]
    unknown = (wanted or set()) - {m["key"] for m in settings.models}
    if unknown:
        raise SystemExit(f"unknown model key(s): {', '.join(sorted(unknown))}")
    return chosen


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=SCRIPT, description=__doc__)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("screen", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("--models")
    commands.choices["run"].add_argument(
        "--set", default="all", choices=("screening", "confirmation", "all")
    )
    summary = commands.add_parser("summary")
    summary.add_argument(
        "--set", default="confirmation", choices=("screening", "confirmation", "all")
    )
    commands.add_parser("check")
    args = parser.parse_args(argv)

    repo = _repo()
    settings = Settings.load(repo / args.config)
    ledger = StudyLedger(repo / settings.ledger)

    if args.command == "check":
        rows = ledger.read()  # raises on a broken chain
        print(f"ledger ok: {len(rows)} trial(s), chain intact")
        return 0
    if args.command == "summary":
        rows = [r for r in ledger.read() if args.set == "all" or r["set"] == args.set]
        summarizer = StudySummarizer()
        summed = summarizer.summarize(rows, float(settings.z))
        verdict = summarizer.decide(summed, settings.models)
        print(json.dumps({"summary": summed, "decision": verdict}, indent=2, default=list))
        return 0

    ollama = OllamaApi(settings.ollama_url)
    preparer = ModelPreparer(ollama, settings)
    models = _pick(settings, args.models)
    if args.command == "screen":
        print(json.dumps([preparer.screen(m) for m in models], indent=2))
        return 0

    tasks = TaskLoader().load_all(repo / settings.tasks)
    screening, confirmation = TaskLoader().split(
        tasks, screening=int(settings.screening), seed=int(settings.split_seed)
    )
    sets = {"screening": screening, "confirmation": confirmation}
    if args.set != "all":
        sets = {args.set: sets[args.set]}
    commands_runner = SubprocessRunner()
    idle_settings = dict(settings.idle)
    idle_settings["server_log"] = str(Path(idle_settings["server_log"]).expanduser())
    idle = IdleGate(
        idle_settings, LlamaServerLog(Path(idle_settings["server_log"])), commands_runner
    )
    host = {
        "system": platform.system(),
        "machine": platform.machine(),
        "node": platform.node(),
        # Scores depend on the checkers, so their versions are part of the record.
        **{tool: importlib.metadata.version(tool) for tool in ("ruff", "mypy", "pytest")},
    }
    ran = StudyRunner(
        settings,
        ledger,
        QwenloopRunner(settings, commands_runner),
        TrialScorer(commands_runner, timeout=float(settings.check_timeout_s)),
        Workspace(),
        preparer,
        idle,
        SystemClock(),
        TrialHome.resolve(settings),
    ).run(models, sets, host)
    print(f"ran {ran} trial(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
