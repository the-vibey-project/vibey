# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh estimate` (#134): two coordinates measured by the fit, sixteen honestly
unknown, the whole path judged, the duration from the shared estimator, cost unknown."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibey_gh import fit
from vibey_gh.cli import main
from vibey_gh.estimate_report import (
    COST_REASON,
    EXIT_CODES,
    REPAIR_REASON,
    STAGE_DURATION_REASON,
    OperationEstimate,
)
from vibey_gh.feasibility import NO, UNKNOWN, YES, Pipeline, Stage
from vibey_gh.fit import Machine, Model
from vibey_gh.fitloop import JOURNAL_ENV
from vibey_gh.interfaces.operation_estimator_interface import OperationEstimatorInterface
from vibey_gh.operation_estimate import OperationEstimator

MACHINE = Machine(total_gb=25.77, free_gb=2.97, swap_used_gb=6.5, swap_total_gb=7.0)
MODEL = Model(name="qwen2.5-coder:14b", size_gb=10.52, context_length=9390)
LOCAL = "http://127.0.0.1:11434"


class Machines:
    """A memory sampler that states a fixed machine."""

    def __init__(self, machine: Machine = MACHINE) -> None:
        self.machine = machine

    def sample(self) -> Machine:
        return self.machine


class Models:
    """A model sampler that states a fixed model -- or none -- and counts its reads."""

    def __init__(self, model: Model | None = MODEL) -> None:
        self.model = model
        self.asked: list[str] = []

    def sample(self, name: str) -> Model | None:
        self.asked.append(name)
        return self.model


def _estimator(
    *,
    machine: Machine = MACHINE,
    model: Model | None = MODEL,
    base_url: str = LOCAL,
    offline: bool = True,
    journal: Path | None = None,
    pipeline: Pipeline | None = None,
    models: Models | None = None,
) -> OperationEstimator:
    return OperationEstimator(
        "qwen2.5-coder:14b",
        base_url=base_url,
        offline=offline,
        journal=journal,
        pipeline=pipeline,
        machine_sampler=Machines(machine),
        model_sampler=models or Models(model),
        clock=lambda: 1_800_000_000.0,
    )


def _write_journal(path: Path, *entries: dict) -> Path:
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8")
    return path


# -- the two measured coordinates --------------------------------------------------------


def test_the_estimator_declares_its_seam():
    assert isinstance(_estimator(), OperationEstimatorInterface)


def test_the_fit_measures_hardware_and_software_availability_and_nothing_else():
    result = _estimator().estimate("develop")
    hardware = result.state.get("hardware", "availability")
    software = result.state.get("software", "availability")
    assert hardware.value == 1.0 and software.value == 1.0
    assert hardware.measured_at == software.measured_at == 1_800_000_000.0
    assert "32.77 GB ceiling (25.77 GB memory + 7.0 GB paging)" in hardware.source
    assert "3.47 GB available now" in hardware.source
    assert software.source == f"runner at {LOCAL} holds qwen2.5-coder:14b (loaded)"
    # The other sixteen are unknown -- none is defaulted to healthy.
    assert result.state.measured == 2
    assert result.verdict.verdict == UNKNOWN and result.exit_code == EXIT_CODES[UNKNOWN] == 3


def test_a_model_on_disk_is_held_but_its_size_is_a_lower_bound():
    cold = Model(name="qwen2.5-coder:14b", size_gb=8.99, context_length=32768, resident=False)
    result = _estimator(model=cold).estimate("develop")
    assert "(on disk, not loaded)" in result.state.get("software", "availability").source
    assert "(weights on disk: a lower bound)" in result.state.get("hardware", "availability").source


def test_a_model_the_machine_cannot_host_is_a_measured_no_at_the_first_stage_needing_it():
    huge = Model(name="llama:405b", size_gb=229.0, context_length=8192)
    result = _estimator(model=huge).estimate("develop")
    hardware = result.state.get("hardware", "availability")
    assert hardware.value == pytest.approx(32.77 / 229.0, abs=1e-4) and hardware.value < 1
    assert result.verdict.verdict == NO and result.verdict.blocked_at == "install"
    assert result.exit_code == 1


def test_a_model_a_hair_over_the_ceiling_never_reads_as_peak():
    """Rounded down when short, so the estimate can never call a machine able to host a
    model the fit calculus declares the floor for."""
    over = Model(name="m", size_gb=32.7701, context_length=1)
    value = _estimator(model=over).estimate("install").state.get("hardware", "availability").value
    assert value is not None and value < 1.0


def test_a_model_of_no_size_fits_anywhere():
    empty = Model(name="m", size_gb=0.0, context_length=1)
    result = _estimator(model=empty).estimate("install")
    assert result.state.get("hardware", "availability").value == 1.0


def test_an_unreadable_machine_leaves_hardware_unknown_not_empty():
    unreadable = Machine(
        total_gb=0.0, free_gb=0.0, swap_used_gb=0.0, swap_total_gb=0.0, readable=False
    )
    hardware = (
        _estimator(machine=unreadable).estimate("install").state.get("hardware", "availability")
    )
    assert hardware.value is None and "not an empty machine" in hardware.source


def test_a_model_the_runner_did_not_report_is_unknown_on_both_sides():
    result = _estimator(model=None).estimate("install")
    software = result.state.get("software", "availability")
    hardware = result.state.get("hardware", "availability")
    assert software.value is None and hardware.value is None
    assert "does not say which" in software.source and "unknown, not zero" in software.source
    assert "size is unknown" in hardware.source
    assert result.verdict.verdict == UNKNOWN


# -- offline by default ------------------------------------------------------------------


@pytest.mark.parametrize(
    "url, local",
    [
        ("http://127.0.0.1:11434", True),
        ("http://localhost:11434", True),
        ("http://ollama.localhost", True),
        ("http://[::1]:11434", True),
        ("http://127.8.8.8", True),
        ("http://10.0.0.5:11434", False),
        ("http://gpu-box.lan:11434", False),
        ("not a url", False),
    ],
)
def test_only_this_machine_counts_as_local(url, local):
    assert OperationEstimator.is_local(url) is local


def test_offline_never_reads_a_runner_on_another_machine():
    models = Models()
    result = _estimator(base_url="http://10.0.0.5:11434", models=models).estimate("install")
    assert models.asked == [] and not result.runner_read and result.offline
    software = result.state.get("software", "availability")
    assert software.value is None and "estimate is offline" in software.source
    assert "--online" in software.source


def test_online_reads_it():
    models = Models()
    result = _estimator(base_url="http://10.0.0.5:11434", offline=False, models=models).estimate(
        "install"
    )
    assert models.asked == ["qwen2.5-coder:14b"] and result.runner_read and not result.offline


def test_a_path_that_is_not_one_is_refused_before_anything_is_measured():
    models = Models()
    with pytest.raises(ValueError, match="not a stage"):
        _estimator(models=models).estimate("promote")
    assert models.asked == []


# -- duration: the one estimator, over the fit journal -----------------------------------


def test_duration_is_projected_from_the_fit_journals_observations(tmp_path):
    journal = _write_journal(
        tmp_path / "fit.jsonl",
        {
            "kind": "observation",
            "payload_bytes": 1024,
            "elapsed_s": 60.0,
            "concurrent": 1,
            "model": "qwen2.5-coder:14b",
        },
        {
            "kind": "observation",
            "payload_bytes": 11264,
            "elapsed_s": 160.0,
            "concurrent": 1,
            "model": "qwen2.5-coder:14b",
        },
        # Another model's timing, and a projection, must not move this one's estimate.
        {
            "kind": "observation",
            "payload_bytes": 1024,
            "elapsed_s": 9999.0,
            "concurrent": 1,
            "model": "llama:70b",
        },
        {"kind": "decision", "projected_service_s": 1.0, "model": "qwen2.5-coder:14b"},
    )
    result = _estimator(journal=journal).estimate("develop", payload_bytes=8192)
    assert result.duration.value == pytest.approx(130.0) and result.duration.n == 2
    assert result.duration.basis == "linear"
    assert "130.0s for 8192 bytes on qwen2.5-coder:14b (linear, n=2" in "\n".join(result.lines())
    # Read, never written: an estimate is not an admission.
    assert journal.read_text(encoding="utf-8").count("\n") == 4


def test_without_observations_the_duration_is_unknown_and_says_where_it_looked(tmp_path):
    result = _estimator(journal=tmp_path / "empty.jsonl").estimate("develop")
    assert result.duration.value is None
    assert f"(journal {tmp_path / 'empty.jsonl'})" in "\n".join(result.lines())
    no_journal = _estimator(journal=None).estimate("develop")
    assert "(no journal)" in "\n".join(no_journal.lines())


# -- the report --------------------------------------------------------------------------


def test_the_report_leads_with_the_verdict_and_states_every_unknown():
    text = "\n".join(_estimator().estimate("develop").lines())
    assert (
        "operation 'develop' from 'install' — install → interview → feature-branch → develop"
        in text
    )
    assert (
        "feasible: UNKNOWN — 4 of 6 required coordinate(s) unmeasured; none measured short" in text
    )
    assert f"cost: unknown — {COST_REASON}" in text
    assert f"duration: unknown for the stages — {STAGE_DURATION_REASON}" in text
    assert "confidence: 0.3333 — 2 of 6 required coordinate(s) measured; 2 of 18 in all" in text
    assert "shortfalls: none measured" in text
    lines = text.splitlines()
    unknown = [line for line in lines if " unknown — " in line and "needed at" in line]
    # Agency first.
    assert unknown[0].endswith(
        "unknown — agency.availability, needed at install, feature-branch, develop"
    )
    assert f"repair ranking: {REPAIR_REASON}" in text
    assert any(line.startswith("  hardware     availability  1  d=0") for line in lines)
    assert "at 2027-01-15T08:00:00Z" in text
    assert any(line.startswith("  install              UNKNOWN") for line in lines)


def test_a_measured_no_names_the_stage_and_the_first_shortfall():
    huge = Model(name="llama:405b", size_gb=229.0, context_length=8192)
    text = "\n".join(_estimator(model=huge).estimate("install").lines())
    assert "feasible: NO — blocked at stage 'install'; first: hardware.availability 0.143" in text
    assert "shortfall — hardware.availability 0.143" in text


def test_yes_when_every_required_coordinate_is_measured():
    pipeline = Pipeline(
        (Stage.needing("local-review", "the sovereign lane", "hardware", "software"),)
    )
    result = _estimator(pipeline=pipeline).estimate("local-review")
    assert result.verdict.verdict == YES and result.exit_code == 0
    text = "\n".join(result.lines())
    assert "feasible: YES" in text and "every requirement met" in text


def test_the_json_carries_every_basis_and_every_unknown_as_null():
    data = _estimator().estimate("main", start="develop-validation").as_dict()
    assert json.loads(json.dumps(data)) == data
    assert data["operation"] == "main" and data["from"] == "develop-validation"
    assert data["stages"] == ["develop-validation", "main"]
    assert data["feasible"] == UNKNOWN and data["blocked_at"] is None
    assert data["cost"] == {"value": None, "reason": COST_REASON}
    assert data["repair"] == {"ranking": None, "reason": REPAIR_REASON}
    assert data["duration"]["stages_s"] is None and data["duration"]["local_service_s"] is None
    assert data["duration"]["journal"] is None
    assert data["measured"] == {"required": 4, "required_measured": 0, "coordinates": 2, "of": 18}
    assert data["unknowns"][0]["coordinate"] == "agency.availability"
    assert len(data["state"]) == 18
    hardware = next(c for c in data["state"] if c["coordinate"] == "hardware.availability")
    assert hardware["value"] == 1.0 and hardware["distance"] == 0.0
    assert data["stage_verdicts"][1] == {
        "stage": "main",
        "verdict": UNKNOWN,
        "gaps": ["network.availability", "agency.availability"],
    }
    assert data["runner"] == LOCAL and data["runner_read"] is True and data["offline"] is True


def test_the_json_names_the_journal_it_read_and_every_shortfall(tmp_path):
    huge = Model(name="llama:405b", size_gb=229.0, context_length=8192)
    data = _estimator(model=huge, journal=tmp_path / "j.jsonl").estimate("install").as_dict()
    assert data["duration"]["journal"] == str(tmp_path / "j.jsonl")
    assert data["shortfalls"][0]["coordinate"] == "hardware.availability"
    assert data["shortfalls"][0]["minimum"] == 1.0


def test_a_time_that_was_never_recorded_is_said_to_be_so():
    assert OperationEstimate._utc(None) == "an unrecorded time"


# -- the command -------------------------------------------------------------------------


@pytest.fixture
def repo(monkeypatch, tmp_path):
    """A repository of its own, the fit's samplers stubbed, and the default journal kept
    inside the test."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text("")
    monkeypatch.setenv(JOURNAL_ENV, str(tmp_path / "default-journal.jsonl"))
    monkeypatch.delenv("VIBEY_OLLAMA_URL", raising=False)
    models = Models()
    monkeypatch.setattr(fit, "machine_sampler", lambda: Machines())
    monkeypatch.setattr(fit, "OllamaModelSampler", _StubRunner(models))
    return tmp_path, models


class _StubRunner:
    """Stands in for `fit.OllamaModelSampler`: keeps its `resolve_base_url`, and hands out
    the test's model sampler instead of a socket."""

    def __init__(self, models: Models) -> None:
        self.models = models
        self.urls: list[str] = []
        self.resolve_base_url = fit.OllamaModelSampler.resolve_base_url

    def __call__(self, base_url: str) -> Models:
        self.urls.append(base_url)
        return self.models


def test_the_command_reports_and_exits_unknown(repo, capsys):
    assert main(["estimate", "--operation", "develop"]) == 3
    out = capsys.readouterr().out
    assert "feasible: UNKNOWN" in out and "hardware     availability  1" in out
    assert "default-journal.jsonl" in out


def test_the_command_speaks_json(repo, capsys):
    assert main(["estimate", "--operation", "main", "--from", "main", "--json"]) == 3
    data = json.loads(capsys.readouterr().out)
    assert data["stages"] == ["main"] and data["feasible"] == UNKNOWN


def test_the_command_exits_one_on_a_measured_no(repo, capsys):
    _, models = repo
    models.model = Model(name="llama:405b", size_gb=229.0, context_length=8192)
    assert main(["estimate", "--operation", "install"]) == 1
    assert "feasible: NO" in capsys.readouterr().out


def test_the_command_exits_zero_only_on_yes(repo, capsys):
    root, _ = repo
    (root / ".vibey-gh.toml").write_text(
        '[estimate]\nstages = ["local-review"]\n'
        '[estimate.requirements.local-review]\n"hardware.availability" = 1\n'
    )
    assert main(["estimate", "--operation", "local-review"]) == 0
    assert "feasible: YES" in capsys.readouterr().out


def test_an_unknown_stage_is_a_usage_error_naming_the_real_ones(repo, capsys):
    assert main(["estimate", "--operation", "promote"]) == 2
    err = capsys.readouterr().err
    assert "'promote' is not a stage" in err and "main-validation" in err


def test_a_configuration_that_cannot_be_judged_is_a_usage_error(repo, capsys):
    root, _ = repo
    (root / ".vibey-gh.toml").write_text('[estimate]\nstages = ["canary"]\n')
    assert main(["estimate", "--operation", "canary"]) == 2
    assert "'canary' has no requirement vector" in capsys.readouterr().err


def test_the_model_and_runner_follow_the_local_lane_unless_told_otherwise(repo, monkeypatch):
    root, models = repo
    runner = fit.OllamaModelSampler
    (root / ".vibey-gh.toml").write_text(
        '[pr_automation.fallback]\nmodel = "qwen3:14b"\nbase_url = "http://localhost:9999"\n'
    )
    main(["estimate", "--operation", "install"])
    assert models.asked[-1] == "qwen3:14b" and runner.urls[-1] == "http://localhost:9999"

    (root / ".vibey-gh.toml").write_text('[estimate]\nmodel = "gpt-oss:20b"\n')
    main(["estimate", "--operation", "install"])
    assert models.asked[-1] == "gpt-oss:20b"

    main(["estimate", "--operation", "install", "--model", "m", "--base-url", "http://[::1]:1"])
    assert models.asked[-1] == "m" and runner.urls[-1] == "http://[::1]:1"


def test_a_remote_runner_is_read_only_when_the_command_is_online(repo, capsys):
    root, models = repo
    remote = ["--base-url", "http://10.0.0.5:11434"]
    main(["estimate", "--operation", "install", *remote])
    assert models.asked == []
    assert "estimate is offline" in capsys.readouterr().out

    main(["estimate", "--operation", "install", *remote, "--online"])
    assert len(models.asked) == 1

    (root / ".vibey-gh.toml").write_text("[estimate]\noffline = false\n")
    main(["estimate", "--operation", "install", *remote])
    assert len(models.asked) == 2


def test_the_journal_is_chosen_like_the_fits(repo, capsys):
    root, _ = repo
    journal = _write_journal(
        root / "mine.jsonl",
        {
            "kind": "observation",
            "payload_bytes": 8192,
            "elapsed_s": 42.0,
            "concurrent": 1,
            "model": "qwen2.5-coder:14b",
        },
    )
    main(["estimate", "--operation", "install", "--journal", str(journal), "--json"])
    assert json.loads(capsys.readouterr().out)["duration"]["local_service_s"] == 42.0

    main(["estimate", "--operation", "install", "--no-journal", "--json"])
    duration = json.loads(capsys.readouterr().out)["duration"]
    assert duration["journal"] is None and duration["local_service_s"] is None


def test_estimate_is_a_capability_on_every_surface():
    from vibey_gh import surfaces

    assert "estimate" in surfaces.CAPABILITIES
    assert surfaces.parity()["estimate"] == surfaces.SURFACES
