# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/minimum_specs.py`: the record, the derivations, staleness, rendering and check.

The measurement probes that need a live host (uv installs, PostgreSQL, Ollama) are driven
here through a fake command runner and fake clients, so every decision they make about a
failure -- skip it, say why, never invent a value -- is exercised without the host.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from scripts import minimum_specs as ms
from scripts.interfaces import minimum_specs_interface as contracts

REPO = Path(__file__).resolve().parents[2]
SETTINGS = ms.SpecsSettings.load(REPO / ms.DEFAULT_CONFIG)
M = SETTINGS.sovereign_model
HOST = "test host"


class FixedClock:
    def __init__(self, stamp: str = "2026-10-05T07:30:00.000Z") -> None:
        self.stamp = stamp

    def now(self) -> str:
        return self.stamp


class FakeRunner:
    """Answers commands by their first matching prefix; records every call."""

    def __init__(self, answers: Mapping[tuple[str, ...], ms.CommandResult] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[list[str]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> ms.CommandResult:
        self.calls.append(list(argv))
        for prefix, result in self.answers.items():
            if tuple(argv[: len(prefix)]) == prefix:
                return result
        return ms.CommandResult(127, "", f"no answer for {argv[:3]}", 0.0)


def ok(stdout: str = "", seconds: float = 1.0) -> ms.CommandResult:
    return ms.CommandResult(0, stdout, "", seconds)


def measured(
    fid: str, value: Any, unit: str = "MiB", at: str = "2026-09-29T23:00:00Z"
) -> ms.Figure:
    return ms.Figure(fid, fid, value, unit, "measured", "test", measured_at=at, host=HOST)


def committed() -> ms.SpecsRecord:
    return ms.SpecsRecord.load(REPO / SETTINGS.record)


# ------------------------------------------------------------------ the record


def test_every_seam_implements_its_declared_interface() -> None:
    # The protocols are not runtime-checkable, so the declaration is read from the MRO.
    assert contracts.CommandRunnerInterface in ms.SubprocessRunner.__mro__
    assert contracts.ClockInterface in ms.SystemClock.__mro__
    assert contracts.IdleGateInterface in ms.IdleGate.__mro__
    assert contracts.DerivationsInterface in ms.Derivations.__mro__
    for source in (ms.ModelFits, ms.LinuxDerivations):
        assert contracts.DerivationSourceInterface in source.__mro__
    assert contracts.PackageManagerInterface in ms.PackageManager.__mro__
    assert contracts.CellRunnerInterface in ms.CellRunner.__mro__
    assert contracts.StalenessPolicyInterface in ms.StalenessPolicy.__mro__
    for renderer in (ms.DocsRenderer, ms.PaperRenderer):
        assert contracts.RequirementsRendererInterface in renderer.__mro__
    for probe in (
        ms.DeclaredFloorsProbe,
        ms.PythonFloorProbe,
        ms.InstallFootprintProbe,
        ms.PostgresProbe,
        ms.OllamaSizesProbe,
        ms.ModelBench,
        ms.ProcessFootprintProbe,
        ms.DiskProbe,
        ms.LinuxCellProbe,
    ):
        assert contracts.ProbeInterface in probe.__mro__


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"status": "guessed"}, "unknown status"),
        ({"cadence": "daily"}, "unknown cadence"),
        ({"status": "derived"}, "formula and inputs"),
        ({"status": "stale", "reason": "down"}, "since when"),
        ({"status": "stale", "stale_since": "2026-09-29T00:00:00Z"}, "says why"),
        ({"status": "skipped", "reason": "down"}, "carries no value"),
        ({"measured_at": "last week"}, "not an ISO-8601"),
        ({"measured_at": "disk usage, 2026-09-29T23:52:35Z"}, "not an ISO-8601"),
    ],
)
def test_a_figure_refuses_to_exist_without_its_evidence(
    changes: dict[str, Any], message: str
) -> None:
    base = measured("x", 1)
    with pytest.raises(ValueError, match=message):
        replace(base, **changes)


def test_the_record_round_trips_through_json_byte_for_byte() -> None:
    record = committed()
    again = ms.SpecsRecord.from_json(record.to_json())
    assert again.to_json() == record.to_json()
    with pytest.raises(ValueError, match="schema"):
        ms.SpecsRecord.from_json(json.dumps({"schema": "other/1"}))


def test_the_committed_record_keeps_measured_derived_and_declared_apart() -> None:
    record = committed()
    kinds = {f.status for f in record.figures}
    assert {"measured", "derived", "declared"} <= kinds
    for figure in record.figures:
        if figure.status == "derived":
            assert figure.formula and figure.inputs is not None
        if figure.status == "measured":
            assert figure.host in record.hosts, figure.id
            assert figure.measured_at, figure.id
    assert record.sources and record.not_verified


# ------------------------------------------------------------------ derivations


def inputs() -> dict[str, ms.Figure]:
    """The seed's inputs, each written out, so the arithmetic below can be checked by hand."""
    figs = [
        measured("host.ram_bytes", 24 * ms.GIB, "bytes"),
        measured("gpu.working_set_limit_mib", 18185),
        measured("process.cli.worker_once.max_rss_mib", 275.8),
        measured("process.serve.idle_rss_mib", 101.9),
        measured("postgres.rss_peak_mib", 57.5),
        measured("design_call.prompt_tokens", 518, "tokens"),
        measured("design_call.output_tokens_max", 1260, "tokens"),
        ms.Figure(
            "declared.ollama_timeout_s",
            "t",
            900,
            "s",
            "declared",
            "read",
            measured_at="2026-09-30T00:00:00Z",
        ),
        ms.Figure("declared.conductor_context_max", "c", 8192, "tokens", "declared", "read"),
        ms.Figure("declared.conductor_output_tokens", "o", 2048, "tokens", "declared", "read"),
        ms.Figure("declared.runner_context_window", "r", 32768, "tokens", "declared", "read"),
        measured(f"model.{M}.download_bytes", 13_793_441_244, "bytes"),
        measured("model.qwen3:14b.download_bytes", 9_276_198_565, "bytes"),
        measured("disk.ollama_app_bytes", 628_854_784, "bytes"),
        measured("install.vibey-engine.venv_bytes", 629 * ms.MIB, "bytes"),
        measured("install.vibey-engine.uv_cache_bytes", 662_288 * 1024, "bytes"),
        measured("disk.postgres_install_bytes", 86_781_952, "bytes"),
        measured("disk.git_pack_mib", 92.32),
        measured("disk.worktree_bytes", 86_958_080, "bytes"),
        measured("disk.dev_venv_bytes", 834_072_576, "bytes"),
        measured("install.krypton-app.download_bytes", 211_022_167, "bytes"),
    ]
    for ctx, device, kv, compute in (
        (4096, 12239, 114, 16.02),
        (8192, 12339, 210, 20.02),
        (32768, 12974, 786, 44.02),
        (131072, 15566, 3090, 140.02),
    ):
        figs += [
            measured(f"bench.{M}.ctx{ctx}.device_mib", device),
            measured(f"bench.{M}.ctx{ctx}.kv_mib", kv),
            measured(f"bench.{M}.ctx{ctx}.host_model_mib", 1104.61),
            measured(f"bench.{M}.ctx{ctx}.host_compute_mib", compute),
        ]
    for kind, ctx, prompt, gen in (
        ("gpu", 4096, 826.6, 32.5),
        ("depth", 32768, 504.9, 26.6),
        ("cpu", 8192, 55.8, 4.2),
    ):
        figs += [
            measured(f"bench.{M}.{kind}.ctx{ctx}.prompt_tok_s", prompt, "tokens/s"),
            measured(f"bench.{M}.{kind}.ctx{ctx}.gen_tok_s", gen, "tokens/s"),
        ]
    for version, verdict in (
        ("3.11", "refused"),
        ("3.12", "works"),
        ("3.13", "works"),
        ("3.14", "works"),
    ):
        figs.append(measured(f"python.{version}.install", verdict, "verdict"))
    return {f.id: f for f in figs}


def derived(figures: Mapping[str, ms.Figure] | None = None) -> dict[str, ms.Figure]:
    return {f.id: f for f in ms.Derivations(SETTINGS).derive(figures or inputs())}


def test_memory_is_derived_from_measured_model_memory_against_context() -> None:
    d = derived()
    # (12339 + 1104.61 + 20.02) / 1024 = 13.148 -> 13.15; (12974 + 1104.61 + 44.02) / 1024 = 13.79
    assert d["ram.model_process.ctx8192"].value == 13.15
    assert d["ram.model_process.ctx32768"].value == 13.79
    assert d["ram.model_process.ctx131072"].value == 16.42
    assert d["ram.kv_per_token_kib"].value == 24.0  # (3090 - 114) * 1024 / (131072 - 4096)
    assert d["ram.vibey_side_gib"].value == 0.5  # 435.2 MiB rounds up to the 0.5 GiB step
    assert d["ram.minimum_need_gib"].value == 17.79  # 13.79 + 0.5 + 3.5
    assert d["ram.minimum_gb"].value == 24
    assert d["ram.recommended_need_gib"].value == 24.42  # 16.42 + 0.5 + 3.5 + 4
    assert d["ram.recommended_gb"].value == 32
    assert d["ram.design_only_need_gib"].value == 17.15
    assert d["ram.16gb_verdict"].value == "insufficient"
    assert d["gpu.metal_limit_16gb_mib"].value == 12123  # 16384 x 18185 / 24576
    assert d["gpu.over_16gb.ctx8192_mib"].value == 216
    assert d["gpu.over_16gb.ctx32768_mib"].value == 851
    assert d["gpu.discrete_vram_gb"].value == 16
    record = d["ram.minimum_need_gib"]
    assert record.status == "derived"
    assert record.inputs == {
        "ram.model_process.ctx32768": 13.79,
        "ram.vibey_side_gib": 0.5,
        "assumption.os_headroom_gib": 3.5,
    }
    assert (
        record.measured_at == "2026-09-29T23:00:00Z"
    )  # the newest dated input: the evidence cutoff


def test_throughput_thresholds_are_held_against_vibeys_own_timeout() -> None:
    d = derived()
    assert d["time.runner_turn_worst.gpu_s"].value == pytest.approx(
        137.8
    )  # 30720/504.9 + 2048/26.6
    assert d["throughput.minimum.turn_s"].value == 512.0  # 30720/100 + 2048/10
    assert d["throughput.minimum.fits"].value is True
    assert d["throughput.recommended.turn_s"].value == pytest.approx(143.4)
    assert d["throughput.host_meets_recommended"].value is True
    assert d["time.design_call.cpu_s"].value == pytest.approx(309.3)  # 518/55.8 + 1260/4.2
    assert d["cpu_only.design_fits"].value is True
    assert d["time.runner_turn_worst.cpu_s"].value == pytest.approx(1038.2)
    assert d["time.conductor_worst.cpu_s"].value == pytest.approx(1085.3)  # 6144/55.8 + 4096/4.2
    assert d["cpu_only.build_fits"].value is False


def test_a_lower_timeout_in_the_code_turns_the_minimum_rates_red() -> None:
    figures = inputs()
    figures["declared.ollama_timeout_s"] = replace(figures["declared.ollama_timeout_s"], value=300)
    d = derived(figures)
    assert d["throughput.minimum.fits"].value is False
    assert d["cpu_only.design_fits"].value is False


def test_disk_python_and_download_are_derived() -> None:
    d = derived()
    assert d["disk.minimum_need_gb"].value == 17.8
    assert d["disk.minimum_gb"].value == 20
    assert d["disk.recommended_need_gb"].value == 45.2
    assert d["disk.recommended_gb"].value == 50
    assert d["download.first_install_bytes"].value == 211_022_167 + 13_793_441_244
    assert d["python.floor"].value == "3.12"


def test_the_python_floor_says_none_when_no_candidate_works() -> None:
    figures = inputs()
    for version in ("3.12", "3.13", "3.14"):
        figures[f"python.{version}.install"] = replace(
            figures[f"python.{version}.install"], value="fails to install"
        )
    assert derived(figures)["python.floor"].value == "none"


def test_a_derived_figure_with_a_stale_input_is_stale_since_that_input() -> None:
    figures = inputs()
    old = figures[f"bench.{M}.ctx32768.device_mib"]
    figures[old.id] = replace(
        old, status="stale", was="measured", stale_since="2026-09-29T23:00:00Z", reason="host busy"
    )
    d = derived(figures)
    need = d["ram.minimum_need_gib"]
    assert need.status == "stale" and need.was == "derived"
    assert need.value == 17.79  # still computed, from the carried value
    assert need.stale_since == "2026-09-29T23:00:00Z"
    assert "ram.model_process.ctx32768" in (need.reason or "")
    assert d["ram.model_process.ctx8192"].status == "derived"  # untouched by that input


def test_a_derived_figure_with_a_missing_input_keeps_its_last_value_marked_stale() -> None:
    figures = inputs()
    first = derived(figures)
    figures.pop("gpu.working_set_limit_mib")
    figures["gpu.metal_limit_16gb_mib"] = first["gpu.metal_limit_16gb_mib"]
    d = derived(figures)
    carried = d["gpu.metal_limit_16gb_mib"]
    assert carried.status == "stale" and carried.value == 12123
    assert carried.stale_since == first["gpu.metal_limit_16gb_mib"].measured_at
    assert "gpu.working_set_limit_mib" in (carried.reason or "")
    # ...and one that never had a value is skipped, with no number invented.
    figures.pop("gpu.metal_limit_16gb_mib")
    never = derived(figures)["gpu.metal_limit_16gb_mib"]
    assert never.status == "skipped" and never.value is None


def test_rederiving_the_committed_record_changes_nothing() -> None:
    record = committed()
    again = ms.RecordBuilder(SETTINGS, FixedClock()).rederive(record)
    assert again.to_json() == record.to_json()


# ------------------------------------------------------------------ staleness


def test_a_measurement_that_could_not_run_is_kept_and_marked_stale() -> None:
    old = measured("bench.x", 12974)
    fresh = ms.Figure(
        "bench.x",
        "bench.x",
        None,
        "MiB",
        "skipped",
        "bench",
        measured_at="2026-10-05T07:30:00Z",
        reason="host not idle",
    )
    [merged] = ms.StalenessPolicy(set()).merge([old], [fresh])
    assert merged.status == "stale" and merged.value == 12974
    assert merged.was == "measured"
    assert merged.stale_since == old.measured_at
    assert merged.reason == "host not idle"


def test_a_figure_stale_twice_keeps_the_date_it_was_last_good() -> None:
    policy = ms.StalenessPolicy(set())
    old = measured("x", 5)
    once = policy.merge([old], [])[0]
    twice = policy.merge([once], [old.skipped("still down")])[0]
    assert twice.status == "stale" and twice.stale_since == old.measured_at
    assert twice.was == "measured" and twice.reason == "still down"
    back = policy.merge([twice], [measured("x", 6, at="2026-10-12T07:30:00Z")])[0]
    assert back.status == "measured" and back.value == 6 and back.stale_since is None


def test_a_once_figure_keeps_its_own_date_and_a_new_figure_is_added() -> None:
    once = replace(measured("network.runtime_internet", "none", "verdict"), cadence="once")
    new = measured("ollama.version", "0.35.0", "version")
    merged = {f.id: f for f in ms.StalenessPolicy(set()).merge([once], [new])}
    assert merged["network.runtime_internet"] == once
    assert merged["ollama.version"] == new


def test_a_skip_with_nothing_to_fall_back_on_stays_skipped() -> None:
    old = measured("x", 1).skipped("never ran")
    fresh = measured("x", 1).skipped("still cannot run")
    assert ms.StalenessPolicy(set()).merge([old], [fresh])[0].reason == "still cannot run"
    assert (
        ms.StalenessPolicy(set()).merge([old], [])[0].reason == "not reported by this run's probes"
    )


def test_derived_figures_are_recomputed_not_merged() -> None:
    derived_id = "ram.minimum_gb"
    old = ms.Figure(derived_id, "m", 24, "GB", "derived", "derived", formula="f", inputs={})
    assert ms.StalenessPolicy({derived_id}).merge([old], [old]) == []


def test_the_record_builder_merges_then_derives() -> None:
    previous = ms.RecordBuilder(SETTINGS, FixedClock("2026-09-30T00:00:00.000Z")).build(
        None, list(inputs().values()), {HOST: {}}
    )
    # This week every probe ran except the model bench, which found the host busy.
    week = [
        f.skipped("host not idle")
        if f.id.startswith("bench.")
        else replace(f, measured_at="2026-10-05T07:30:00Z")
        for f in inputs().values()
    ]
    record = ms.RecordBuilder(SETTINGS, FixedClock()).build(previous, week, {HOST: {"chip": "x"}})
    by = record.by_id()
    assert by[f"bench.{M}.ctx32768.device_mib"].status == "stale"
    assert by["ram.minimum_gb"].status == "stale" and by["ram.minimum_gb"].value == 24
    assert by["disk.minimum_gb"].status == "derived"  # its inputs were re-measured
    assert by["disk.minimum_gb"].measured_at == "2026-10-05T07:30:00Z"
    # A probe that reported nothing at all leaves its figures stale, never silently current.
    quiet = ms.RecordBuilder(SETTINGS, FixedClock()).build(previous, [], {})
    assert quiet.by_id()["disk.minimum_gb"].status == "stale"
    assert quiet.by_id()["disk.ollama_app_bytes"].reason == "not reported by this run's probes"
    assert record.generated_at == "2026-10-05T07:30:00.000Z"
    assert record.hosts[HOST] == {"chip": "x"}


# ------------------------------------------------------------------ rendering


def test_the_formatter_spells_out_status() -> None:
    fig = measured("x", 13_793_441_244, "bytes")
    assert ms.Formatter.cell(fig) == "13.79 GB"
    assert ms.Formatter.cell(replace(fig, value=209_577_992)) == "209.6 MB"
    stale = replace(
        fig, status="stale", was="measured", stale_since="2026-09-29T23:00:00Z", reason="host busy"
    )
    assert ms.Formatter.cell(stale) == "13.79 GB (stale since 2026-09-29: host busy)"
    assert ms.Formatter.cell(fig.skipped("no Ollama")) == "not measured (no Ollama)"
    assert ms.Formatter.cell(None) == "not measured"
    for value, unit, text in (
        (True, "verdict", "yes"),
        (13.79, "GiB", "13.79 GiB"),
        (24.0, "GB", "24 GB"),
        (12974, "MiB", "12,974 MiB"),
        (57.5, "MiB", "57.5 MiB"),
        (504.9, "tokens/s", "505 tok/s"),
        (4.2, "tokens/s", "4.2 tok/s"),
        (1038.2, "s", "1,038 s"),
        (20, "count", "20"),
        ("3.12", "version", "3.12"),
    ):
        assert ms.Formatter.value(replace(fig, value=value, unit=unit)) == text


def test_units_convert_through_bytes() -> None:
    assert ms.Units.convert(1, "GiB", "MiB") == 1024
    assert ms.Units.convert(1e9, "bytes", "GB") == 1
    with pytest.raises(ValueError):
        ms.Units.convert(1, "parsecs", "GB")


def test_a_stale_figure_shows_in_the_tables_and_the_status_list() -> None:
    record = committed()
    by = record.by_id()
    fid = f"bench.{M}.ctx32768.device_mib"
    stale = replace(
        by[fid],
        status="stale",
        was="measured",
        stale_since="2026-09-30T00:08:27.859Z",
        reason="host not idle",
    )
    record = replace(record, figures=tuple(stale if f.id == fid else f for f in record.figures))
    docs = ms.DocsRenderer(SETTINGS).blocks(record)
    assert "(stale since 2026-09-30: host not idle)" in docs["hardware"]
    assert "measured, stale" in docs["hardware"]  # the Basis column says so too
    assert f"| `{fid}` | stale | 2026-09-30 | host not idle |" in docs["status"]
    paper = ms.PaperRenderer(SETTINGS).blocks(record)["minimum-requirements"]
    assert "stale since 2026-09-30: host not idle" in paper


def test_every_generated_table_names_its_host_and_dates() -> None:
    record = committed()
    docs = ms.DocsRenderer(SETTINGS).blocks(record)
    host = next(h for h in record.hosts if "macOS" in h)  # the Linux cells are hosts too
    for name in ("hardware", "software", "network", "clients"):
        assert f"*Measured on {host}; figures dated 2026-09-29" in docs[name], name
    paper = ms.PaperRenderer(SETTINGS).blocks(record)["minimum-requirements"]
    assert "figures dated 2026-09-29 to 2026-09-30 (UTC)" in paper
    assert r"\label{tab:minimum-requirements}" in paper
    assert r"\begin{figure" not in paper  # the paper counts its figures; a table is not one


def test_tex_escaping_keeps_every_special_character_literal() -> None:
    assert ms.PaperRenderer.tex("50% & #1 _x_ $y {z} ~ ^ [hub] · `c`") == (
        r"50\% \& \#1 \_x\_ \$y \{z\} \textasciitilde{} \textasciicircum{} {[}hub{]} $\cdot$ c"
    )
    assert ms.PaperRenderer.tex(r">=3.12 <=900 a\b") == r"$\geq$3.12 $\leq$900 a\textbackslash{}b"


def test_generated_blocks_are_replaced_only_between_their_markers() -> None:
    doc = (
        "before\n"
        + ms.GeneratedBlocks.wrap("a", "old")
        + "\nmiddle\n"
        + ms.GeneratedBlocks.wrap("other", "keep")
        + "\n"
    )
    out = ms.GeneratedBlocks.replace_all(doc, {"a": "new"})
    assert out.startswith("before\n") and "new" in out and "old" not in out and "keep" in out
    assert ms.GeneratedBlocks.names(out) == ["a", "other"]
    assert ms.GeneratedBlocks.drift(out, {"a": "new"}) == []
    assert ms.GeneratedBlocks.drift(doc, {"a": "new", "missing": "x"}) == ["a", "missing"]


def test_check_fails_on_a_hand_edited_table_and_on_a_hand_edited_derivation(tmp_path: Path) -> None:
    for relative in (ms.DEFAULT_CONFIG, SETTINGS.record, SETTINGS.docs_page, SETTINGS.paper):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((REPO / relative).read_text(encoding="utf-8"), encoding="utf-8")
    cli = ms.MinimumSpecsCli(tmp_path, FixedClock())
    assert cli.run(["check"]) == 0

    page = tmp_path / SETTINGS.docs_page
    page.write_text(
        page.read_text(encoding="utf-8").replace("24 GB (needs", "16 GB (needs"), encoding="utf-8"
    )
    assert cli.run(["check"]) == 1
    assert cli.run(["render"]) == 0
    assert cli.run(["check"]) == 0

    record_path = tmp_path / SETTINGS.record
    raw = json.loads(record_path.read_text(encoding="utf-8"))
    for figure in raw["figures"]:
        if figure["id"] == "ram.minimum_gb":
            figure["value"] = 16
    record_path.write_text(json.dumps(raw), encoding="utf-8")
    assert cli.run(["check"]) == 1
    assert cli.run(["derive"]) == 0
    assert ms.SpecsRecord.load(record_path).by_id()["ram.minimum_gb"].value == 24
    assert cli.run(["check"]) == 0


# ------------------------------------------------------------------ probes (faked host)


def factory() -> ms.FigureFactory:
    return ms.FigureFactory(FixedClock(), HOST)


def test_declared_floors_are_read_from_where_the_repository_declares_them() -> None:
    by = {f.id: f for f in ms.DeclaredFloorsProbe(REPO, SETTINGS, factory()).run()}
    assert by["declared.postgres_min_major"].value == 14
    assert by["declared.python_requires"].value == ">=3.12"
    assert by["declared.ollama_timeout_s"].value == 900
    assert by["declared.runner_context_window"].value == 32768
    assert all(f.status == "declared" and f.source for f in by.values())


def test_a_declared_floor_that_moved_is_skipped_not_guessed(tmp_path: Path) -> None:
    by = {f.id: f for f in ms.DeclaredFloorsProbe(tmp_path, SETTINGS, factory()).run()}
    assert all(f.status == "skipped" and f.value is None for f in by.values())
    assert "not found in" in (by["declared.postgres_min_major"].reason or "")


def test_python_probe_records_refusals_and_skips_a_missing_interpreter(tmp_path: Path) -> None:
    ws = ms.Workspace(tmp_path)
    ws.wheel_paths = {"vibey-engine": tmp_path / "e.whl", "krypton-app": tmp_path / "k.whl"}
    refused = ms.CommandResult(
        1, "", "because the current Python version (3.11.15) does not satisfy Python>=3.12", 1
    )
    runner = FakeRunner(
        {
            ("uv", "venv", "-q", "-p", "3.11"): ok(),
            ("uv", "venv", "-q", "-p", "3.12"): ok(),
            ("uv", "venv", "-q", "-p", "3.13"): ms.CommandResult(
                2, "", "No interpreter found for Python 3.13", 1
            ),
            ("uv", "venv", "-q", "-p", "3.14"): ok(),
            (str(tmp_path / "venv-py3.11" / "bin" / "python"),): ok("Python 3.11.15"),
            (
                "uv",
                "pip",
                "install",
                "-q",
                "-p",
                str(tmp_path / "venv-py3.11" / "bin" / "python"),
            ): refused,
            ("uv", "pip", "install"): ok(),
            (str(tmp_path / "venv-py3.12" / "bin" / "vibey"),): ok("vibey 3.0.0"),
            (str(tmp_path / "venv-py3.14" / "bin" / "vibey"),): ms.CommandResult(
                1, "", "ImportError", 1
            ),
        }
    )
    builder = ms.PackageBuilder(tmp_path, SETTINGS, runner, ws)
    by = {f.id: f for f in ms.PythonFloorProbe(SETTINGS, runner, builder, ws, factory()).run()}
    assert by["python.3.11.install"].value == "refused"
    assert by["python.3.12.install"].value == "works"
    assert by["python.3.13.install"].status == "skipped" and "no Python 3.13" in (
        by["python.3.13.install"].reason or ""
    )
    assert by["python.3.14.install"].value == "installs, fails to run"


def test_a_failed_build_skips_every_install_figure_with_the_reason(tmp_path: Path) -> None:
    ws = ms.Workspace(tmp_path)
    runner = FakeRunner({("uv", "build"): ms.CommandResult(1, "", "no pyproject", 1)})
    builder = ms.PackageBuilder(tmp_path, SETTINGS, runner, ws)
    figures = ms.InstallFootprintProbe(
        SETTINGS, runner, builder, ws, ms.DirectorySize(runner), factory()
    ).run()
    assert figures and all(f.status == "skipped" for f in figures)
    assert all("`uv build` of vibey-engine failed" in (f.reason or "") for f in figures)
    python = ms.PythonFloorProbe(SETTINGS, runner, builder, ws, factory()).run()
    assert all(f.status == "skipped" for f in python)


def test_install_targets_name_this_checkouts_wheels() -> None:
    probe = ms.InstallFootprintProbe(SETTINGS, FakeRunner(), None, None, None, factory())  # type: ignore[arg-type]
    targets = probe.targets({"vibey-engine": Path("e.whl"), "krypton-app": Path("k.whl")})
    assert targets == {
        "vibey-engine": ["e.whl"],
        "vibey-engine[hub]": ["e.whl[hub]"],
        "krypton-app": ["k.whl", "e.whl[hub]"],
    }


def test_postgres_probe_skips_without_a_dsn_and_never_drops_what_it_did_not_create(
    tmp_path: Path,
) -> None:
    ws = ms.Workspace(tmp_path)
    unset = ms.PostgresProbe(SETTINGS, FakeRunner(), ws, factory(), environ={}).run()
    assert all(f.status == "skipped" and "is not set" in (f.reason or "") for f in unset)

    exists = FakeRunner(
        {
            (
                "psql",
                "postgresql://u@h/postgres",
                "-X",
                "-At",
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                "SHOW server_version",
            ): ok("18.4 (Homebrew)\n"),
            ("psql",): ms.CommandResult(1, "", 'database "vibey_specs_scratch" already exists', 1),
        }
    )
    probe = ms.PostgresProbe(
        SETTINGS,
        exists,
        ws,
        factory(),
        environ={"VIBEY_SPECS_PG_ADMIN_URL": "postgresql://u@h/postgres"},
    )
    by = {f.id: f for f in probe.run()}
    assert by["postgres.server_version"].value == "18.4"
    assert by["postgres.migrations_applied"].status == "skipped"
    assert probe.database is None  # nothing created, so nothing will be dropped
    assert not any("DROP" in " ".join(call) for call in exists.calls)


def test_the_scratch_url_replaces_only_the_database() -> None:
    runner = FakeRunner()
    for admin, expected in (
        (
            "postgresql://u:p@localhost:5432/postgres",
            "postgresql://u:p@localhost:5432/vibey_specs_scratch",
        ),
        ("postgresql:///postgres?host=/sock", "postgresql:///vibey_specs_scratch?host=/sock"),
        ("postgresql://localhost", "postgresql://localhost/vibey_specs_scratch"),
    ):
        assert ms.ScratchDatabase(admin, "vibey_specs_scratch", runner).url() == expected
    assert "unsafe" in ms.ScratchDatabase("postgresql://h/p", "x; DROP", runner).create()


def test_llama_server_accounting_is_read_from_the_log() -> None:
    log = "\n".join(
        [
            "common_memory_breakdown_print: |   - MTL0 (Apple M5)    | 18186 = 18185 + (12974 = 12036 +     786 +     151) +      -12974 |",
            "load_tensors:   CPU_Mapped model buffer size =  1104.61 MiB",
            "llama_context: n_ctx                 = 32768",
            "sched_reserve:        CPU compute buffer size =    44.02 MiB",
            '[GIN] 2026/09/29 - 20:02:25 | 200 |  1.2s | 127.0.0.1 | POST     "/api/chat"',
            '[GIN] 2026/09/29 - 20:02:26 | 200 |  1.2s | 127.0.0.1 | POST     "/api/show"',
        ]
    )
    assert ms.LlamaServerLog.accounting(log) == {
        "device_mib": 12974.0,
        "weights_mib": 12036.0,
        "kv_mib": 786.0,
        "compute_mib": 151.0,
        "working_set_limit_mib": 18185.0,
        "host_model_mib": 1104.61,
        "host_compute_mib": 44.02,
        "n_ctx": 32768.0,
    }
    assert ms.LlamaServerLog.inference_posts(log) == 1  # /api/show is not inference
    assert ms.LlamaServerLog.last_post_epoch(log) is not None
    assert ms.LlamaServerLog.last_post_epoch("nothing") is None


def gate(
    tmp_path: Path, load1: float, busy: str = "", log: str = "", clock: list[float] | None = None
) -> ms.IdleGate:
    path = tmp_path / "server.log"
    path.write_text(log, encoding="utf-8")
    ticks = clock if clock is not None else [0.0]
    settings = {
        **SETTINGS.idle,
        "busy_command": "check" if busy else "",
        "max_wait_s": 60,
        "poll_s": 30,
    }
    runner = FakeRunner({("/bin/sh",): ok(busy)})

    def monotonic() -> float:
        return ticks[0]

    def sleep(seconds: float) -> None:
        ticks[0] += seconds

    return ms.IdleGate(
        settings,
        ms.LlamaServerLog(path),
        runner,
        loadavg=lambda: (load1, load1, load1),
        sleep=sleep,
        monotonic=monotonic,
    )


def test_the_idle_gate_lets_a_quiet_host_through(tmp_path: Path) -> None:
    idle, reason, conditions = gate(tmp_path, 1.0).wait()
    assert idle and not reason
    assert conditions["load1"] == 1.0 and conditions["busy_command_output"] == ""


@pytest.mark.parametrize(
    ("load1", "busy", "log", "expected"),
    [
        (5.0, "", "", "load1 5.00 above"),
        (1.0, "runner: Runner.Worker", "", "busy command reported"),
        (
            1.0,
            "",
            '[GIN] 2999/01/01 - 00:00:00 | 200 | 1s | 127.0.0.1 | POST     "/api/chat"\n',
            "another Ollama client",
        ),
    ],
)
def test_the_idle_gate_waits_a_bounded_time_then_says_why(
    tmp_path: Path, load1: float, busy: str, log: str, expected: str
) -> None:
    idle, reason, conditions = gate(tmp_path, load1, busy, log).wait()
    assert not idle
    assert reason.startswith("host not idle after 60 s") and expected in reason
    assert conditions["waited_s"] == 60


def test_the_model_bench_touches_nothing_on_a_busy_host(tmp_path: Path) -> None:
    class Unusable:
        def __getattr__(self, name: str) -> Any:
            raise AssertionError(f"the bench touched Ollama ({name}) on a busy host")

    busy = gate(tmp_path, 9.0)
    log = ms.LlamaServerLog(tmp_path / "server.log")
    figures = ms.ModelBench(SETTINGS, Unusable(), busy, log, factory()).run()  # type: ignore[arg-type]
    assert figures and all(f.status == "skipped" for f in figures)
    assert {f.id for f in figures} == {
        fid for fid, _, _ in ms.ModelBench(SETTINGS, None, busy, log, factory()).expected()
    }  # type: ignore[arg-type]
    assert all("host not idle" in (f.reason or "") for f in figures)


def test_the_bench_prompt_is_deterministic_and_tagged() -> None:
    one = ms.ModelBench.prompt(500, 42, 4.83, "a")
    assert one == ms.ModelBench.prompt(500, 42, 4.83, "a")
    assert one != ms.ModelBench.prompt(500, 42, 4.83, "b")  # the tag defeats the prompt cache
    assert len(one) >= 500 * 4.83


def test_time_output_is_parsed_on_macos_and_gnu() -> None:
    mac = "        0.31 real         0.22 user         0.05 sys\n            78856192  maximum resident set size\n"
    gnu = "\tMaximum resident set size (kbytes): 77004\n\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:01.59\n"
    assert ms.ProcessFootprintProbe.parse_time(mac) == {"wall_s": 0.31, "max_rss_mib": 75.2}
    assert ms.ProcessFootprintProbe.parse_time(gnu) == {"wall_s": 61.59, "max_rss_mib": 75.2}


def test_ollama_sizes_skip_an_unreachable_server_with_the_reason() -> None:
    class Down:
        def version(self) -> str:
            raise OSError("connection refused")

        def manifest_bytes(self, model: str) -> int:
            if model == M:
                return 13_793_441_244
            raise OSError("registry unreachable")

    by = {f.id: f for f in ms.OllamaSizesProbe(SETTINGS, Down(), factory()).run()}  # type: ignore[arg-type]
    assert by["ollama.version"].status == "skipped" and "connection refused" in (
        by["ollama.version"].reason or ""
    )
    assert by[f"model.{M}.download_bytes"].value == 13_793_441_244
    assert by["model.qwen3:14b.download_bytes"].status == "skipped"


def test_the_host_id_names_model_chip_memory_and_os() -> None:
    info = {
        "model": "Mac17,2",
        "chip": "Apple M5",
        "ram_bytes": 24 * ms.GIB,
        "os": "macOS 26.6.2 (25G83)",
    }
    assert ms.HostDescriber.host_id(info) == "Mac17,2 · Apple M5 · 24 GiB · macOS 26.6.2 (25G83)"
    assert ms.HostDescriber.host_id({}) == "unknown · unknown chip · unknown memory · unknown OS"


def test_the_subprocess_runner_reports_a_missing_tool_and_a_timeout() -> None:
    runner = ms.SubprocessRunner()
    missing = runner.run(["definitely-not-a-command-vibey"], timeout=5)
    assert missing.returncode == 127 and not missing.ok
    slow = runner.run(["sleep", "5"], timeout=0.2)
    assert slow.returncode == 124 and "timed out" in slow.stderr
    fine = runner.run(["echo", "hi"], timeout=5, env={"X": "1"})
    assert fine.ok and fine.stdout.strip() == "hi" and fine.tail() == "hi"


# ------------------------------------------------------------------ probes: the happy paths


def test_install_probe_measures_each_target_from_a_cold_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The host path; on Linux the probe also reads the wheels' glibc floor, tested apart.
    monkeypatch.setattr(ms.platform, "system", lambda: "Darwin")
    ws = ms.Workspace(tmp_path)
    ws.wheel_paths = {"vibey-engine": tmp_path / "e.whl", "krypton-app": tmp_path / "k.whl"}
    runner = FakeRunner(
        {
            ("uv", "venv"): ok(),
            ("uv", "pip", "list"): ok(json.dumps([{"name": "a"}, {"name": "b"}])),
            ("uv", "pip", "install"): ok(seconds=21.79),
            ("du", "-sk"): ok("644392\t/somewhere\n"),
        }
    )

    class Downloads(FakeRunner):
        def run(self, argv: Sequence[str], **kwargs: Any) -> ms.CommandResult:
            if list(argv[1:4]) == ["-m", "pip", "download"]:
                dest = Path(argv[argv.index("-d") + 1])
                dest.mkdir(parents=True, exist_ok=True)
                (dest / "a.whl").write_bytes(b"x" * 1000)
                (dest / "b.whl").write_bytes(b"x" * 234)
                return ok()
            return runner.run(argv, **kwargs)

    fake = Downloads()
    for venv in ("venv-vibey-engine", "venv-vibey-engine-hub-", "venv-krypton-app"):
        (tmp_path / venv).mkdir()
        (tmp_path / f"cache-{venv}").mkdir()
    builder = ms.PackageBuilder(tmp_path, SETTINGS, fake, ws)
    probe = ms.InstallFootprintProbe(SETTINGS, fake, builder, ws, ms.DirectorySize(fake), factory())
    by = {f.id: f for f in probe.run()}
    assert by["install.vibey-engine.cold_s"].value == 21.8
    assert by["install.vibey-engine.packages"].value == 2
    assert by["install.vibey-engine.venv_bytes"].value == 644392 * 1024
    assert by["install.krypton-app.download_bytes"].value == 1234
    assert by["install.vibey-engine[hub].download_bytes"].conditions == {"files": 2}
    assert set(ws.venvs) == {"vibey-engine", "vibey-engine[hub]", "krypton-app"}
    assert all(f.status == "measured" for f in by.values())


def test_postgres_probe_migrates_a_scratch_database_it_then_drops(tmp_path: Path) -> None:
    ws = ms.Workspace(tmp_path)
    ws.venvs["vibey-engine"] = tmp_path / "venv"
    admin = "postgresql://u@h/postgres"
    psql = ("psql", admin, "-X", "-At", "-v", "ON_ERROR_STOP=1", "-c")
    size = "SELECT pg_database_size('vibey_specs_scratch')"
    migrate = (str(tmp_path / "venv" / "bin" / "vibey"), "migrate")
    runner = FakeRunner(
        {
            (*psql, "SHOW server_version"): ok("17.6\n"),
            (*psql, size): ok("9025215\n"),
            ("psql",): ok(),
            migrate: ms.CommandResult(1, "applied 20 migration(s): 0001_project", "guard", 1),
        }
    )
    environ = {"VIBEY_SPECS_PG_ADMIN_URL": admin}
    probe = ms.PostgresProbe(SETTINGS, runner, ws, factory(), environ=environ)
    by = {f.id: f for f in probe.run()}
    assert by["postgres.server_version"].value == "17.6"
    assert by["postgres.migrations_applied"].value == 20
    assert by["postgres.migrations_applied"].conditions == {"exit": 1}
    assert by["postgres.empty_db_bytes"].value == 9025215
    assert probe.database is not None and probe.database.created
    probe.database.drop()
    assert runner.calls[-1][-1] == 'DROP DATABASE IF EXISTS "vibey_specs_scratch"'
    assert not probe.database.created


class FakeOllama:
    """Answers the bench's loads and chats; writes llama-server lines into the log on load."""

    def __init__(self, log: Path) -> None:
        self.log = log
        self.calls: list[tuple[str, Mapping[str, Any] | None]] = []

    def unload(self, model: str) -> None:
        self.calls.append(("unload", {"model": model}))

    def call(self, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append((path, payload))
        options = dict((payload or {}).get("options", {}))
        if path == "/api/generate":
            ctx = options["num_ctx"]
            kv = ctx // 100
            with self.log.open("a", encoding="utf-8") as handle:
                handle.write(
                    "common_memory_breakdown_print: |   - MTL0 (Apple M5)    | "
                    f"18186 = 18185 + ({12036 + kv + 90} = 12036 +  {kv} +  90) + 0 |\n"
                    "load_tensors:   CPU_Mapped model buffer size =  1104.61 MiB\n"
                    "sched_reserve:        CPU compute buffer size =    20.02 MiB\n"
                )
            return {}
        with self.log.open("a", encoding="utf-8") as handle:
            handle.write(
                '[GIN] 2026/10/05 - 03:30:00 | 200 | 1s | 127.0.0.1 | POST     "/api/chat"\n'
            )
        slow = options.get("num_gpu") == 0
        return {
            "prompt_eval_count": 2000,
            "prompt_eval_duration": int(2000 / (50 if slow else 800) * 1e9),
            "eval_count": 256,
            "eval_duration": int(256 / (4 if slow else 32) * 1e9),
        }


class QuietGate:
    def __init__(self, log: ms.LlamaServerLog, foreign: int = 0) -> None:
        self._log = log
        self.foreign = foreign

    def wait(self) -> tuple[bool, str, dict[str, Any]]:
        return True, "", {"load1": 1.0}

    def log_offset(self) -> int:
        return self._log.offset()

    def foreign_requests_since(self, offset: int) -> int:
        return ms.LlamaServerLog.inference_posts(self._log.since(offset)) + self.foreign


#: A sweep every test host can run (the declared one goes to ten threads).
SMALL_SWEEP = {
    "threads": [1, 2],
    "context": 8192,
    "prompt_tokens": 256,
    "num_predict": 64,
    "runs": 2,
}


def bench_settings(**bench: Any) -> ms.SpecsSettings:
    return replace(
        SETTINGS, bench={**SETTINGS.bench, "runs": 2, "cpu_scaling": SMALL_SWEEP, **bench}
    )


def empty_log(tmp_path: Path) -> tuple[Path, ms.LlamaServerLog]:
    path = tmp_path / "server.log"
    path.write_text("", encoding="utf-8")
    return path, ms.LlamaServerLog(path)


def test_the_model_bench_reads_memory_and_rates_on_a_quiet_host(tmp_path: Path) -> None:
    path, log = empty_log(tmp_path)
    client = FakeOllama(path)
    settings = bench_settings(contexts=[8192, 32768], depth_contexts=[32768], cpu_contexts=[8192])
    bench = ms.ModelBench(settings, client, QuietGate(log), log, factory())  # type: ignore[arg-type]
    by = {f.id: f for f in bench.run()}
    assert by[f"bench.{M}.ctx32768.device_mib"].value == 12036 + 327 + 90
    assert by[f"bench.{M}.ctx32768.kv_mib"].value == 327.0
    assert by[f"bench.{M}.ctx8192.host_model_mib"].value == 1104.61
    assert by["gpu.working_set_limit_mib"].value == 18185.0
    assert by[f"bench.{M}.gpu.ctx8192.prompt_tok_s"].value == 800.0
    assert by[f"bench.{M}.cpu.ctx8192.gen_tok_s"].value == 4.0
    assert by[f"bench.{M}.depth.ctx32768.gen_tok_s"].conditions["runs_clean"] == 2
    assert all(f.status == "measured" for f in by.values())
    chats = [p for name, p in client.calls if name == "/api/chat" and p]
    cpu = [p for p in chats if p["options"].get("num_gpu") == 0]
    assert cpu and all(p["options"]["temperature"] == 0 for p in chats)
    assert client.calls[-1] == ("unload", {"model": M})  # it unloads what it loaded


def test_a_run_that_overlapped_another_client_is_discarded(tmp_path: Path) -> None:
    path, log = empty_log(tmp_path)
    settings = bench_settings(contexts=[8192], depth_contexts=[], cpu_contexts=[])
    gate = QuietGate(log, foreign=1)
    figures = ms.ModelBench(settings, FakeOllama(path), gate, log, factory()).run()  # type: ignore[arg-type]
    rates = [f for f in figures if f.id.endswith("tok_s")]
    assert rates
    assert all(
        f.status == "skipped" and "overlapped another client (2)" in (f.reason or "") for f in rates
    )


def test_the_model_bench_skips_the_rest_when_ollama_fails_mid_run(tmp_path: Path) -> None:
    path, log = empty_log(tmp_path)

    class Failing(FakeOllama):
        def call(self, path_: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
            raise OSError("connection reset")

    bench = ms.ModelBench(bench_settings(), Failing(path), QuietGate(log), log, factory())  # type: ignore[arg-type]
    figures = bench.run()
    assert figures and all(f.status == "skipped" for f in figures)
    assert "connection reset" in (figures[0].reason or "")


def test_disk_probe_sizes_the_ollama_app_and_the_shared_objects(tmp_path: Path) -> None:
    app = tmp_path / "Ollama.app"
    app.mkdir()
    settings = replace(SETTINGS, ollama={**SETTINGS.ollama, "app_path": str(app)})
    counted = ok("count: 1\nsize-pack: 94536\n")
    runner = FakeRunner({("du", "-sk"): ok("614116\tOllama.app\n"), ("git",): counted})
    sizes = ms.DirectorySize(runner)
    by = {f.id: f for f in ms.DiskProbe(tmp_path, settings, runner, sizes, factory()).run()}
    assert by["disk.ollama_app_bytes"].value == 614116 * 1024
    assert by["disk.git_pack_mib"].value == 92.32
    absent = replace(SETTINGS, ollama={**SETTINGS.ollama, "app_path": str(tmp_path / "none")})
    nothing = FakeRunner()
    probe = ms.DiskProbe(tmp_path, absent, nothing, ms.DirectorySize(nothing), factory())
    missing = {f.id: f for f in probe.run()}
    assert missing["disk.ollama_app_bytes"].status == "skipped"
    assert missing["disk.git_pack_mib"].status == "skipped"


def test_a_session_runs_the_chosen_probes_and_cleans_up() -> None:
    session = ms.MeasurementSession(
        REPO, SETTINGS, runner=FakeRunner(), clock=FixedClock(), environ={}, only=("declared",)
    )
    record = session.run(committed())
    by = record.by_id()
    assert by["declared.postgres_min_major"].measured_at == "2026-10-05T07:30:00.000Z"
    assert by["ollama.version"].status == "stale"  # not run this time: kept, and said so
    assert by["network.runtime_internet"].status == "measured"  # a once figure keeps its date
    assert record.generated_at == "2026-10-05T07:30:00.000Z"


# ------------------------------------------------------------------ found by the smoke run


def test_a_tool_that_exists_but_may_not_run_is_a_result_not_a_crash(tmp_path: Path) -> None:
    script = tmp_path / "not-executable"
    script.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    script.chmod(0o600)
    denied = ms.SubprocessRunner().run([str(script)], timeout=5)
    assert denied.returncode == 126 and not denied.ok


def test_an_unreadable_process_table_is_never_a_zero_rss() -> None:
    probe = ms.ProcessFootprintProbe(SETTINGS, FakeRunner(), None, factory(), None)  # type: ignore[arg-type]
    assert probe.tree_rss_mib(1) is None  # ps refused: no reading at all
    table = ok("  PID  PPID   RSS\n  10     1  2048\n  11    10  1024\n  12     1  4096\n")
    listed = ms.ProcessFootprintProbe(SETTINGS, FakeRunner({("ps",): table}), None, factory(), None)  # type: ignore[arg-type]
    assert listed.tree_rss_mib(10) == 3.0  # 10 and its child 11, not the unrelated 12
    assert listed.tree_rss_mib(99) is None  # gone before it was sampled


def test_a_crashed_probe_leaves_its_figures_stale_with_the_crash_named() -> None:
    class Crashing(ms.MeasurementSession):
        def _probes(self, figures: Any, ws: Any, holder: Any) -> Any:
            class Boom:
                name = "disk"

                def run(self) -> list[ms.Figure]:
                    raise PermissionError("Operation not permitted: 'ps'")

            yield Boom()

    session = Crashing(REPO, SETTINGS, runner=FakeRunner(), clock=FixedClock(), environ={})
    record = session.run(committed())
    ollama_app = record.by_id()["disk.ollama_app_bytes"]
    assert ollama_app.status == "stale"
    assert "crashed: disk: PermissionError" in (ollama_app.reason or "")


def test_a_derivation_that_cannot_be_computed_is_skipped_not_a_crash() -> None:
    one_context = replace(SETTINGS, bench={**SETTINGS.bench, "contexts": [4096]})
    by = {f.id: f for f in ms.Derivations(one_context).derive(inputs())}
    slope = by["ram.kv_per_token_kib"]
    assert slope.status == "skipped" and "ZeroDivisionError" in (slope.reason or "")
    assert by["ram.minimum_gb"].value == 24  # the rest still derive


def test_the_host_model_buffer_is_read_whether_or_not_the_weights_are_mapped() -> None:
    # Ollama 0.34 wrote the plain `CPU` form on the 2026-09-30 smoke run under memory pressure.
    read_in = "load_tensors:          CPU model buffer size =  1104.61 MiB\n"
    assert ms.LlamaServerLog.accounting(read_in) == {"host_model_mib": 1104.61}


def test_volatile_temp_paths_never_reach_the_committed_record() -> None:
    """The record is committed, so a probe's scratch path must not be (tests/meta guard)."""
    mac = "/usr/bin/time -l vibey new x --repo /var/folders/_8/abc123/T/hw/proj/repo"
    assert ms.VolatilePaths.scrub(mac) == "/usr/bin/time -l vibey new x --repo $TMPDIR/hw/proj/repo"
    assert ms.VolatilePaths.scrub("cd /private/tmp/claude-501/x") == "cd $TMPDIR/claude-501/x"
    assert (
        ms.VolatilePaths.scrub("/usr/bin/time -l vibey --version")
        == "/usr/bin/time -l vibey --version"
    )
    assert ms.VolatilePaths.scrub(None) is None
    figure = ms.Figure(
        id="cli.new.rss",
        label="vibey new peak RSS",
        value=74.0,
        unit="MiB",
        status="measured",
        method=mac,
        measured_at="2026-09-29T00:00:00Z",
        note="scratch under /tmp/x",
    )
    assert "/var/folders" not in figure.method and "$TMPDIR" in figure.method
    assert figure.note == "scratch under $TMPDIR/x"


# ------------------------------------------------------------------ the fitted models

MATH = ms.RequirementsMath()


def test_the_memory_line_is_fitted_to_the_measured_sweep() -> None:
    d = derived()
    contexts = [4096, 8192, 32768, 131072]
    totals = [12239 + 1104.61 + 16.02, 12339 + 1104.61 + 20.02, 12974 + 1104.61 + 44.02]
    totals.append(15566 + 1104.61 + 140.02)
    line = MATH.least_squares([float(c) for c in contexts], totals)
    assert d["fit.memory.m0_mib"].value == round(line.intercept, 1)
    assert d["fit.memory.k_kib_per_token"].value == round(line.slope * 1024, 3)
    assert d["fit.memory.r2"].value == round(line.r2, 6)
    assert d["fit.memory.r2"].value > 0.999  # the mechanism (weights + linear KV) holds
    assert d["fit.memory.max_residual_mib"].value == round(line.max_abs_residual, 1)
    assert d["fit.memory.m0_mib"].inputs is not None
    assert len(d["fit.memory.m0_mib"].inputs) == 12  # three buffers at each of four contexts


def test_linux_memory_is_the_fitted_model_with_headroom_plus_vibey_and_the_os() -> None:
    d = derived()
    m0, k = d["fit.memory.m0_mib"].value, d["fit.memory.k_kib_per_token"].value
    h = SETTINGS.linux["memory_headroom_factor"]
    need = round(h * (m0 + k / 1024 * 32768) / 1024 + 0.5 + 3.5, 2)
    assert d["linux.ram.minimum_need_gib"].value == need
    assert d["linux.ram.minimum_gb"].value == next(
        s for s in SETTINGS.assumptions["memory_sizes_gb"] if s >= need
    )
    rec = round(h * (m0 + k / 1024 * 131072) / 1024 + 0.5 + 3.5 + 4.0, 2)
    assert d["linux.ram.recommended_need_gib"].value == rec
    # The largest context 16 GB holds: solve h*(M0 + k*c)/1024 + 4 = 16e9 / 2^30 for c.
    c_max = ((16e9 / ms.MIB - 4.0 * 1024) / h - m0) / (k / 1024)
    assert d["linux.ram.max_context_at_probe"].value == max(0, math.floor(c_max))
    assert d["linux.ram.probe_fits_runner"].value is False
    assert d["linux.ram.minimum_need_gib"].inputs["config.linux.memory_headroom_factor"] == h


def sweep(arch: str, t1: float, p: float, threads: Sequence[int]) -> dict[str, ms.Figure]:
    return {
        f"bench.{M}.cpu.{arch}.threads{n}.gen_tok_s": measured(
            f"bench.{M}.cpu.{arch}.threads{n}.gen_tok_s", t1 / ((1 - p) + p / n), "tokens/s"
        )
        for n in threads
    }


def test_cores_come_from_amdahls_law_fitted_to_the_thread_sweep() -> None:
    figures = {**inputs(), **sweep("aarch64", 0.9, 0.95, [1, 2, 4, 6, 8, 10])}
    d = derived(figures)
    assert d["fit.cpu.aarch64.t1_tok_s"].value == pytest.approx(0.9)
    assert d["fit.cpu.aarch64.p"].value == pytest.approx(0.95)
    assert d["fit.cpu.aarch64.r2"].value == pytest.approx(1.0)
    assert d["fit.cpu.aarch64.asymptote_tok_s"].value == pytest.approx(18.0)
    theta = SETTINGS.linux["cpu_knee_tok_s_per_core"]
    knee = (math.sqrt(0.9 * 0.95 / theta) - 0.95) / 0.05
    assert d["fit.cpu.aarch64.knee_cores"].value == math.ceil(knee)
    floor = SETTINGS.assumptions["minimum_gen_tok_s"]  # 10 tok/s
    assert d["fit.cpu.aarch64.minimum_cores"].value == math.ceil(0.95 / (0.9 / floor - 0.05))
    # No x86_64 sweep was measured: nothing is invented for it.
    assert d["fit.cpu.x86_64.knee_cores"].status == "skipped"
    reason = d["fit.cpu.x86_64.knee_cores"].reason or ""
    assert "a fit needing 3 of its 6 measured points has 0" in reason
    assert "threads1.gen_tok_s and 5 more" in reason


def test_a_floor_above_the_asymptote_is_unreachable_and_a_partial_sweep_still_fits() -> None:
    slow = {**inputs(), **sweep("aarch64", 0.4, 0.9, [1, 2, 4])}  # asymptote 4 < 10 tok/s
    d = derived(slow)
    assert d["fit.cpu.aarch64.minimum_cores"].value == "unreachable"
    assert d["fit.cpu.aarch64.p"].value == pytest.approx(0.9)  # three of six counts suffice
    two = {**inputs(), **sweep("aarch64", 0.4, 0.9, [1, 2])}
    assert derived(two)["fit.cpu.aarch64.p"].status == "skipped"


def test_ledger_growth_is_the_integral_of_the_job_rate_over_the_horizon() -> None:
    figures = {
        **inputs(),
        "postgres.empty_db_bytes": measured("postgres.empty_db_bytes", 9_025_215, "bytes"),
        "postgres.after_one_job_bytes": measured(
            "postgres.after_one_job_bytes", 9_197_247, "bytes"
        ),
    }
    d = derived(figures)
    assert d["postgres.bytes_per_job"].value == 172_032
    g = SETTINGS.growth
    expected = 172_032 * (
        g["jobs_per_day"] * g["horizon_days"]
        + g["jobs_per_day_growth"] * g["horizon_days"] ** 2 / 2
    )
    assert d["disk.ledger_growth_gb"].value == round(expected / 1e9, 2)
    assert derived()["disk.ledger_growth_gb"].status == "skipped"  # never measured: no number


# ------------------------------------------------------------------ the Linux matrix

UBUNTU = "linux.ubuntu-24.04.aarch64"
BUNDLE = "linux.ollama.aarch64"


def cell_inputs() -> dict[str, ms.Figure]:
    figs = [
        measured(f"{UBUNTU}.pkg.base.bytes", 115_960_832, "bytes"),
        measured(f"{UBUNTU}.pkg.postgres.bytes", 233_686_016, "bytes"),
        measured(f"{UBUNTU}.pkg.desktop.bytes", 134_172_672, "bytes"),
        measured(f"{UBUNTU}.install.vibey-engine.venv_bytes", 701_739_008, "bytes"),
        measured(f"{UBUNTU}.install.vibey-engine.uv_cache_bytes", 723_202_048, "bytes"),
        measured(f"{UBUNTU}.install.krypton-app.venv_bytes", 709_271_552, "bytes"),
        measured(f"{BUNDLE}.unpacked_bytes", 2_238_464_000, "bytes"),
        measured(f"{UBUNTU}.glibc", "2.39", "version"),
        measured(f"{UBUNTU}.install.glibc_floor", "2.34", "version"),
        measured(f"{UBUNTU}.packaged.postgres", "16+257build1.1", "version"),
        measured(f"{UBUNTU}.packaged.python", "3.12.3-0ubuntu2.1", "version"),
        measured(f"{UBUNTU}.packaged.glib", "2.80.0-6ubuntu3.9", "version"),
        measured(f"{UBUNTU}.packaged.json_glib", "1.8.0-2build2", "version"),
        measured(f"{UBUNTU}.packaged.gtk4", "4.14.5+ds-0ubuntu0.10", "version"),
        measured(f"{UBUNTU}.packaged.libadwaita", "1.5.0-1ubuntu2", "version"),
    ]
    floors = [
        ms.Figure(f"declared.{k}", k, v, "semver", "declared", "read")
        for k, v in (
            ("postgres_min_major", 14),
            ("desktop_glib", ">= 2.74"),
            ("desktop_json_glib", ">= 1.6"),
            ("desktop_gtk4", ">= 4.12"),
            ("desktop_libadwaita", ">= 1.4"),
        )
    ]
    return {**inputs(), **{f.id: f for f in [*figs, *floors]}}


def test_a_cells_disk_is_the_sum_of_its_own_closures_and_installs() -> None:
    d = derived(cell_inputs())
    need = (
        115_960_832
        + 233_686_016
        + 701_739_008
        + 723_202_048
        + 2_238_464_000
        + 13_793_441_244
        + 92.32 * ms.MIB
        + 10 * 86_958_080
    ) / 1e9 + 1.0
    assert d[f"{UBUNTU}.disk.minimum_need_gb"].value == round(need, 1)
    assert d[f"{UBUNTU}.disk.minimum_gb"].value == math.ceil(round(need, 1) / 10) * 10
    rec = (
        round(need, 1)
        + (
            134_172_672
            + 709_271_552
            + 9_276_198_565
            + 834_072_576
            + 40 * 86_958_080
            + 13_793_441_244
        )
        / 1e9
    )
    assert d[f"{UBUNTU}.disk.recommended_need_gb"].value == round(rec, 1)
    # The ledger term waits for its per-job measurement; the rest of the disk does not.
    assert d[f"{UBUNTU}.disk.with_ledger_gb"].status == "skipped"


def test_a_cells_floors_compare_its_packaged_versions_with_vibeys() -> None:
    d = derived(cell_inputs())
    for floor in ("postgres", "python", "glibc", "desktop"):
        assert d[f"{UBUNTU}.floor.{floor}"].value is True, floor
    old = cell_inputs()
    old[f"{UBUNTU}.packaged.postgres"] = measured(
        f"{UBUNTU}.packaged.postgres", "13.9-1", "version"
    )
    old[f"{UBUNTU}.install.glibc_floor"] = measured(
        f"{UBUNTU}.install.glibc_floor", "2.40", "version"
    )
    old[f"{UBUNTU}.packaged.gtk4"] = measured(f"{UBUNTU}.packaged.gtk4", "1:4.10.1-1", "version")
    d = derived(old)
    assert d[f"{UBUNTU}.floor.postgres"].value is False
    assert d[f"{UBUNTU}.floor.glibc"].value is False
    assert d[f"{UBUNTU}.floor.desktop"].value is False


@pytest.mark.parametrize(
    ("have", "floor", "ok_"),
    [
        ("1:4.22.5-1", ">= 4.12", True),
        ("16+257build1.1", "14", True),
        ("6.8.0-146.146", "6.8", True),
        ("2.39", "2.40", False),
        ("3.12.3-0ubuntu2.1", "3.12", True),
        ("3.11.9", "3.12", False),
    ],
)
def test_versions_compare_by_their_leading_number(have: str, floor: str, ok_: bool) -> None:
    assert ms.Versions.at_least(have, floor) is ok_


def test_a_version_with_no_number_is_refused() -> None:
    with pytest.raises(ValueError, match="no version number"):
        ms.Versions.key("unknown")
    assert ms.Versions.major("18+290ubuntu1") == 18


def test_the_matrix_is_every_declared_distribution_on_every_architecture() -> None:
    matrix = ms.LinuxMatrix(SETTINGS)
    cells = matrix.cells()
    assert {(c.distro, c.arch) for c in cells} == {
        (d, a) for d in SETTINGS.linux["distros"] for a in SETTINGS.linux["arches"]
    }
    arm_arch = matrix.cell("arch", "aarch64")
    assert arm_arch.image == "" and "amd64 only" in arm_arch.reason
    assert matrix.cell("fedora", "aarch64").platform == "linux/arm64"
    ids = [fid for fid, _, _ in matrix.expected(matrix.cell("ubuntu-24.04", "aarch64"))]
    assert f"{BUNDLE}.unpacked_bytes" in ids  # the declared distribution measures the bundle
    assert f"{UBUNTU}.install.krypton-app.venv_bytes" in ids
    assert not any(i.startswith("linux.ollama.") for i, _, _ in matrix.expected(arm_arch))
    with pytest.raises(KeyError, match="no cell"):
        matrix.cell("gentoo", "aarch64")


def test_package_sizes_are_read_in_each_managers_own_format() -> None:
    parse = ms.PackageManager.parse_sizes
    assert parse("git\t20480\nlibc6\t13000\n", "name-tab-kib") == {
        "git": 20480 * 1024,
        "libc6": 13000 * 1024,
    }
    assert parse("git-core\t1234\n", "name-tab-bytes") == {"git-core": 1234}
    qi = "Name            : bash\nInstalled Size  : 9.59 MiB\n\nName            : zlib\nInstalled Size  : 172.00 KiB\n"
    assert parse(qi, "pacman-qi") == {"bash": round(9.59 * ms.MIB), "zlib": 172 * 1024}
    with pytest.raises(ValueError, match="unknown size_format"):
        parse("", "dnf-magic")


def test_the_package_manager_asks_the_repositories_and_takes_the_newest() -> None:
    config = SETTINGS.linux["package_managers"]["dnf"]
    info = "Installed packages\nVersion        : 2.88.0\n\nAvailable packages\nVersion        : 2.88.3\n"
    runner = FakeRunner({("dnf", "-q", "info"): ok(info), ("/bin/sh",): ok()})
    pm = ms.PackageManager(config, runner, 60)
    assert pm.version("glib2") == "2.88.3"
    pm.install(["gtk4", "evil; rm -rf /"])
    command = runner.calls[-1][2]
    assert "gtk4 evilrm-rf" in command and ";" not in command  # names, never shell
    nothing = ms.PackageManager(config, FakeRunner({("dnf",): ok("")}), 60)
    assert nothing.version("absent") is None
    with pytest.raises(OSError, match="listing installed packages failed"):
        nothing.installed()


class FakeManager:
    """A package manager over an in-memory system: install adds each package's closure."""

    def __init__(
        self, installed: set[str], closures: Mapping[str, set[str]], fail: str = ""
    ) -> None:
        self.current = set(installed)
        self._closures = closures
        self._fail = fail

    def installed(self) -> set[str]:
        return set(self.current)

    def sizes(self) -> dict[str, int]:
        return {name: 1000 * len(name) for name in self.current}

    def install(self, packages: Sequence[str]) -> ms.CommandResult:
        if self._fail and self._fail in packages:
            return ms.CommandResult(100, "", "E: Unable to locate package", 1)
        for package in packages:
            self.current |= self._closures.get(package, {package})
        return ok()

    def version(self, package: str) -> str | None:
        return None if package == "linux-image-generic" else "16+257build1.1"


class FakeInstall:
    name = "install"

    def run(self) -> list[ms.Figure]:
        return [measured(f"{UBUNTU}.install.vibey-engine.venv_bytes", 1, "bytes")]


def cell_probe(tmp_path: Path, manager: FakeManager, before: set[str] | None) -> ms.LinuxCellProbe:
    release = tmp_path / "os-release"
    release.write_text('PRETTY_NAME="Ubuntu 24.04.5 LTS"\n', encoding="utf-8")
    cell = ms.LinuxMatrix(SETTINGS).cell("ubuntu-24.04", "aarch64")
    return ms.LinuxCellProbe(
        SETTINGS,
        cell,
        manager,
        FakeInstall(),
        factory(),
        before,
        os_release=release,  # type: ignore[arg-type]
    )


def test_a_cell_measures_each_package_sets_closure_from_the_package_managers_sizes(
    tmp_path: Path,
) -> None:
    base = {"libc6", "bash"}
    after_bootstrap = base | {"python3", "git", "libpython3.12", "curl"}
    manager = FakeManager(
        after_bootstrap,
        {
            "postgresql": {"postgresql", "postgresql-16", "libpq5"},
            "libgtk-4-1": {"libgtk-4-1", "libcairo2"},
        },
    )
    by = {f.id: f for f in cell_probe(tmp_path, manager, base).run()}
    assert by[f"{UBUNTU}.os_release"].value == "Ubuntu 24.04.5 LTS"
    assert by[f"{UBUNTU}.pkg.base.count"].value == 4
    assert by[f"{UBUNTU}.pkg.base.bytes"].value == 1000 * sum(map(len, after_bootstrap - base))
    assert by[f"{UBUNTU}.pkg.postgres.count"].value == 3
    assert by[f"{UBUNTU}.pkg.postgres.bytes"].conditions["packages"] == [
        "libpq5",
        "postgresql",
        "postgresql-16",
    ]
    assert by[f"{UBUNTU}.packaged.postgres"].value == "16+257build1.1"
    kernel = by[f"{UBUNTU}.packaged.kernel"]
    assert kernel.status == "skipped" and "linux-image-generic" in (kernel.reason or "")
    assert by[f"{UBUNTU}.install.vibey-engine.venv_bytes"].value == 1  # the install probe's own


def test_a_cell_without_its_snapshot_or_with_a_failed_install_says_why(tmp_path: Path) -> None:
    manager = FakeManager({"bash"}, {}, fail="postgresql")
    by = {f.id: f for f in cell_probe(tmp_path, manager, None).run()}
    assert by[f"{UBUNTU}.pkg.base.bytes"].status == "skipped"
    assert "before the bootstrap" in (by[f"{UBUNTU}.pkg.base.bytes"].reason or "")
    failed = by[f"{UBUNTU}.pkg.postgres.bytes"]
    assert failed.status == "skipped" and "Unable to locate" in (failed.reason or "")
    assert by[f"{UBUNTU}.pkg.desktop.count"].status == "measured"


def test_the_installed_wheels_glibc_floor_is_their_newest_manylinux_tag(tmp_path: Path) -> None:
    site = tmp_path / "venv" / "lib" / "python3.12" / "site-packages"
    for name, tags in (
        (
            "pydantic_core-2.41",
            ["cp312-cp312-manylinux_2_17_aarch64", "cp312-cp312-manylinux2014_aarch64"],
        ),
        ("zstandard-0.25", ["cp312-cp312-manylinux_2_34_aarch64"]),
        ("httpx-0.28", ["py3-none-any"]),
        ("legacy-1.0", ["cp312-cp312-manylinux1_x86_64"]),
    ):
        info = site / f"{name}.dist-info"
        info.mkdir(parents=True)
        (info / "WHEEL").write_text("".join(f"Tag: {t}\n" for t in tags), encoding="utf-8")
    assert ms.InstallFootprintProbe.glibc_floor(tmp_path / "venv") == ("2.34", 3)
    assert ms.InstallFootprintProbe.glibc_floor(tmp_path / "nothing") is None


def test_an_emulated_cell_keeps_its_sizes_and_refuses_its_timings(tmp_path: Path) -> None:
    ws = ms.Workspace(tmp_path)
    ws.wheel_paths = {"vibey-engine": tmp_path / "e.whl", "krypton-app": tmp_path / "k.whl"}
    runner = FakeRunner(
        {
            ("uv", "venv"): ok(),
            ("uv", "pip", "list"): ok("[]"),
            ("uv", "pip", "install"): ok(seconds=300.0),
            ("du", "-sk"): ok("1000\t/x\n"),
        }
    )
    builder = ms.PackageBuilder(tmp_path, SETTINGS, runner, ws)
    probe = ms.InstallFootprintProbe(
        SETTINGS,
        runner,
        builder,
        ws,
        ms.DirectorySize(runner),
        factory(),
        prefix=f"{UBUNTU}.install",
        only=["vibey-engine"],
        emulated="linux/amd64 on aarch64",
    )
    (tmp_path / "venv-vibey-engine").mkdir()
    (tmp_path / "cache-venv-vibey-engine").mkdir()
    by = {f.id: f for f in probe.run()}
    assert set(probe.targets(ws.wheel_paths)) == {"vibey-engine"}
    cold = by[f"{UBUNTU}.install.vibey-engine.cold_s"]
    assert cold.status == "skipped" and "emulated" in (cold.reason or "")
    assert by[f"{UBUNTU}.install.vibey-engine.venv_bytes"].value == 1000 * 1024


def test_prebuilt_wheels_are_taken_from_the_hosts_directory(tmp_path: Path) -> None:
    (tmp_path / "vibey_engine-3.2.0-py3-none-any.whl").write_bytes(b"")
    environ = {ms.PackageBuilder.WHEELS_ENV: str(tmp_path)}
    builder = ms.PackageBuilder(
        tmp_path, SETTINGS, FakeRunner(), ms.Workspace(tmp_path / "ws"), environ
    )
    wheels, why = builder.build()
    assert wheels == {} and "krypton-app" in why
    (tmp_path / "krypton_app-3.2.0-py3-none-any.whl").write_bytes(b"")
    builder = ms.PackageBuilder(
        tmp_path, SETTINGS, FakeRunner(), ms.Workspace(tmp_path / "ws2"), environ
    )
    wheels, why = builder.build()
    assert not why and set(wheels) == {"vibey-engine", "krypton-app"}


class DockerFake(FakeRunner):
    """Builds no wheels (the host hands them over), runs the container by writing the record
    the cell's `measure` would, and streams the bundle."""

    def __init__(self, partial: ms.SpecsRecord | None, exit_code: int = 0) -> None:
        super().__init__({("/bin/sh",): ok("2238464000\n")})
        self._partial = partial
        self._exit = exit_code
        self.docker: list[str] = []

    def run(self, argv: Sequence[str], **kwargs: Any) -> ms.CommandResult:
        if argv and argv[0] == SETTINGS.linux["docker"]:
            self.docker = list(argv)
            out = next(v.split(":")[0] for v in argv if v.endswith(":/out"))
            if self._partial is not None:
                self._partial.save(Path(out) / "partial.json")
            return ms.CommandResult(self._exit, "", "docker: image pull failed", 1)
        return super().run(argv, **kwargs)


def wheel_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    for name in ("vibey_engine-3.2.0-py3-none-any.whl", "krypton_app-3.2.0-py3-none-any.whl"):
        (wheels / name).write_bytes(b"")
    monkeypatch.setenv(ms.PackageBuilder.WHEELS_ENV, str(wheels))


def test_a_cell_runs_its_image_bootstraps_it_and_keeps_only_its_own_figures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel_dir(tmp_path, monkeypatch)
    label = "ubuntu:24.04 (linux/arm64, native) on a test host"
    inside = ms.SpecsRecord(
        "2026-10-05T07:30:00.000Z",
        {label: {"system": "Linux"}},
        (
            replace(measured(f"{UBUNTU}.glibc", "2.39", "version"), host=label),
            measured("host.ram_bytes", 1, "bytes"),
        ),
    )
    fake = DockerFake(inside)
    runner = ms.CellRunner(
        REPO, SETTINGS, fake, FixedClock(), "a test host", "arm64", head=lambda url: 1_550_231_393
    )
    partial = runner.run("ubuntu-24.04", "aarch64")
    by = partial.by_id()
    assert set(by) == {f"{UBUNTU}.glibc", f"{BUNDLE}.download_bytes", f"{BUNDLE}.unpacked_bytes"}
    assert by[f"{BUNDLE}.unpacked_bytes"].value == 2_238_464_000
    assert partial.hosts[label]["emulated"] is False
    assert fake.docker[fake.docker.index("--platform") + 1] == "linux/arm64"
    script = fake.docker[-1]
    snapshot, refresh = script.index("packages-before.txt"), script.index("apt-get update")
    assert snapshot < refresh  # the base closure is measured from the pristine image
    assert "measure --out /out/partial.json" in script
    assert any(v.endswith(":/src:ro") for v in fake.docker)


def test_a_cell_on_the_other_architecture_is_emulated_and_a_failed_one_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel_dir(tmp_path, monkeypatch)
    fake = DockerFake(None, exit_code=125)
    runner = ms.CellRunner(REPO, SETTINGS, fake, FixedClock(), "a test host", "arm64")
    partial = runner.run("fedora", "x86_64")
    assert "emulated" in next(iter(partial.hosts))
    assert f"{ms.LinuxMatrix.EMULATED_ENV}=linux/amd64 on aarch64" in fake.docker
    figures = partial.figures
    assert figures and all(f.status == "skipped" for f in figures)
    assert "image pull failed" in (figures[0].reason or "")


def test_a_cell_with_no_image_is_every_figure_skipped_with_the_reason() -> None:
    runner = ms.CellRunner(REPO, SETTINGS, FakeRunner(), FixedClock(), "a test host", "arm64")
    partial = runner.run("arch", "aarch64")
    expected = ms.LinuxMatrix(SETTINGS).expected(ms.LinuxMatrix(SETTINGS).cell("arch", "aarch64"))
    assert {f.id for f in partial.figures} == {fid for fid, _, _ in expected}
    assert all(f.status == "skipped" and "amd64 only" in (f.reason or "") for f in partial.figures)


def test_merging_a_cell_touches_only_that_cell_and_every_cell_is_named() -> None:
    record = committed()
    other = "linux.fedora.aarch64.glibc"
    seeded = replace(record, figures=(*record.figures, measured(other, "2.42", "version")))
    seeded = replace(seeded, figures=tuple(f for f in seeded.figures if f.id != f"{UBUNTU}.glibc"))
    partial = ms.SpecsRecord(
        "2026-10-05T07:30:00.000Z",
        {"cell host": {}},
        (measured(f"{UBUNTU}.glibc", "2.39", "version"),),
    )
    merger = ms.CellMerger(SETTINGS, FixedClock())
    merged = merger.merge(seeded, [partial]).by_id()
    assert merged[f"{UBUNTU}.glibc"].value == "2.39"
    assert merged[other].status == "measured"  # another cell's figure is left alone
    assert merged["ram.minimum_gb"] == record.by_id()["ram.minimum_gb"]
    arm_arch = merged["linux.arch.aarch64.os_release"]
    assert arm_arch.status == "skipped" and "amd64 only" in (arm_arch.reason or "")
    # The workflow's merge: a cell that handed nothing over goes stale, and says so.
    complete = merger.merge(seeded, [partial], complete=True).by_id()
    assert complete[other].status == "stale"
    assert "handed over no record" in (complete[other].reason or "")
    assert complete[f"{UBUNTU}.glibc"].status == "measured"


def test_the_host_run_leaves_the_linux_matrix_as_it_was() -> None:
    record = committed()
    seeded = replace(
        record, figures=(*record.figures, measured("linux.fedora.aarch64.glibc", "2.42", "version"))
    )
    session = ms.MeasurementSession(
        REPO, SETTINGS, runner=FakeRunner(), clock=FixedClock(), environ={}, only=("declared",)
    )
    by = session.run(seeded).by_id()
    assert by["linux.fedora.aarch64.glibc"].status == "measured"  # not this run's to mark stale
    assert by["ollama.version"].status == "stale"  # a host figure it did not re-measure


def test_inside_a_cell_only_the_linux_probe_runs_and_only_its_cell_is_in_scope() -> None:
    environ = {
        ms.LinuxMatrix.CELL_ENV: "ubuntu-24.04/aarch64",
        ms.LinuxMatrix.HOST_ENV: "the cell's container",
    }
    session = ms.MeasurementSession(
        REPO, SETTINGS, runner=FakeRunner(), clock=FixedClock(), environ=environ
    )
    probes = list(session._probes(factory(), ms.Workspace(), []))
    assert [p.name for p in probes] == ["linux"]

    class OneFigure(ms.MeasurementSession):
        def _probes(self, figures: Any, ws: Any, holder: Any) -> Any:
            class Probe:
                name = "linux"

                def run(self) -> list[ms.Figure]:
                    return [
                        figures.measured(f"{UBUNTU}.glibc", "glibc", "2.39", "version", "confstr"),
                        figures.measured("disk.git_pack_mib", "git", 1.0, "MiB", "out of scope"),
                    ]

            yield Probe()

    record = OneFigure(
        REPO, SETTINGS, runner=FakeRunner(), clock=FixedClock(), environ=environ
    ).run(committed())
    by = record.by_id()
    assert by[f"{UBUNTU}.glibc"].host == "the cell's container"
    assert by["disk.git_pack_mib"] == committed().by_id()["disk.git_pack_mib"]  # dropped
    assert by["host.ram_bytes"] == committed().by_id()["host.ram_bytes"]  # the VM's is not recorded


class ScalingOllama(FakeOllama):
    """CPU-only generation that follows Amdahl's law in the thread count."""

    def call(self, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        reply = super().call(path, payload)
        threads = dict((payload or {}).get("options", {})).get("num_thread")
        if path == "/api/chat" and threads:
            rate = 0.9 / (0.05 + 0.95 / threads)
            reply["eval_count"] = 64
            reply["eval_duration"] = int(64 / rate * 1e9)
        return reply


def test_the_bench_sweeps_cpu_threads_and_skips_counts_above_the_hosts_cores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, log = empty_log(tmp_path)
    monkeypatch.setattr(ms.os, "cpu_count", lambda: 4)
    monkeypatch.setattr(ms.platform, "machine", lambda: "arm64")
    sweep_ = {**SMALL_SWEEP, "threads": [1, 2, 4, 8]}
    settings = bench_settings(
        contexts=[8192], depth_contexts=[], cpu_contexts=[], cpu_scaling=sweep_
    )
    by = {
        f.id: f
        for f in ms.ModelBench(settings, ScalingOllama(path), QuietGate(log), log, factory()).run()
    }  # type: ignore[arg-type]
    rates = {n: by[f"bench.{M}.cpu.aarch64.threads{n}.gen_tok_s"] for n in (1, 2, 4, 8)}
    assert rates[1].value == pytest.approx(0.9, abs=0.01)
    assert rates[4].value == pytest.approx(0.9 / (0.05 + 0.95 / 4), abs=0.01)
    assert rates[4].conditions["options"] == {"num_gpu": 0, "num_thread": 4}
    assert rates[8].status == "skipped" and "4 cores" in (rates[8].reason or "")


def test_the_linux_blocks_render_the_matrix_and_the_models() -> None:
    record = ms.RecordBuilder(SETTINGS, FixedClock()).rederive(
        replace(committed(), figures=tuple({**committed().by_id(), **cell_inputs()}.values()))
    )
    blocks = ms.DocsRenderer(SETTINGS).blocks(record)
    assert {"linux-floors", "linux-requirements", "linux-models"} <= set(blocks)
    assert "| Ubuntu 24.04 LTS | aarch64 |" in blocks["linux-requirements"]
    assert "not run: no official Arch Linux image" in blocks["linux-floors"]
    assert "M(c) = M₀ + k·c" in blocks["linux-models"] and "∫₀ᴴ" in blocks["linux-models"]
    assert "n* = (√(T₁·p/θ) − p)/(1 − p)" in blocks["linux-models"]
    paper = ms.PaperRenderer(SETTINGS).blocks(record)["linux-requirements"]
    assert paper.count(r"\label{tab:linux-requirements}") == 1
    assert "$M(c) = M_0 + kc$" in paper


def test_a_failed_linux_install_names_why_its_glibc_floor_was_not_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ms.platform, "system", lambda: "Linux")
    ws = ms.Workspace(tmp_path)
    ws.wheel_paths = {"vibey-engine": tmp_path / "e.whl", "krypton-app": tmp_path / "k.whl"}
    crash = ms.CommandResult(139, "", "qemu: uncaught target signal 11 (Segmentation fault)", 1)
    runner = FakeRunner({("uv", "venv"): ok(), ("uv", "pip", "install"): crash})
    builder = ms.PackageBuilder(tmp_path, SETTINGS, runner, ws)
    probe = ms.InstallFootprintProbe(
        SETTINGS,
        runner,
        builder,
        ws,
        ms.DirectorySize(runner),
        factory(),
        prefix=f"{UBUNTU}.install",
        only=["vibey-engine"],
    )
    floor = {f.id: f for f in probe.run()}[f"{UBUNTU}.install.glibc_floor"]
    assert floor.status == "skipped" and "signal 11" in (floor.reason or "")
