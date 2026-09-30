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
    host = next(iter(record.hosts))
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


def test_install_probe_measures_each_target_from_a_cold_cache(tmp_path: Path) -> None:
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


def bench_settings(**bench: Any) -> ms.SpecsSettings:
    return replace(SETTINGS, bench={**SETTINGS.bench, "runs": 2, **bench})


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
