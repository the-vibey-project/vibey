## Title
feat(gh): the hardware series — each estimate appends a pressure sample to the fit journal, and hardware stability and reliability are read from the rolling series

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *hardware*: "stability (paging pressure
and free-page series), reliability (thermal / CPU headroom, macOS and Arch Linux per 8.h)"; Scope 2:
"Stability and reliability are computed from series (variance, success rate), not from single
readings"; "Proposed child issues" 4: "keep a rolling series in the fit journal"). Sub-doctrines:
8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`), 7.c (`doctrines.md:82-91`: every
measurement is written as it happens, append-only), 10.f (`doctrines.md:419`: too short a series
is unknown, never a guess), 12.c (`doctrines.md:455`: the window and the minimum are keys).

Verified gap (integration clone): `hardware.stability` and `hardware.reliability` are always
"unmeasured" (`src/vibey_tools/gh/vibey_gh/feasibility.py:100-101`). The readings exist after
`roadmap-134-hardware-series-p1` (`vibey_gh/pressure.py`), the journal's one writer and reader
after `roadmap-134-hardware-series-p2` (`fitloop.FitJournal`), and the probe seam and composition
after `roadmap-134-software-probe-p1`/`-p3`. The journal the command already chooses
(`vibey_gh/cli.py:796-802`: `--journal`, else `--no-journal`, else `FitLoop.default_journal()`) is
where the series lives. Writing a *measurement* there is not writing the *estimate*: `recorded_observations`
reads only `kind == "observation"` (`vibey_gh/fitloop.py:97-98`), so a `hardware_sample` line can
never become a timing, and the estimator itself still writes nothing (its docstring, as corrected
by `roadmap-134-software-probe-p1`).

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **Configuration.** `EstimateConfig` (`vibey_gh/config.py`), appended after the fields and checks
   `roadmap-134-network-probe-p2` added:
   - fields: `hardware_window: int = 32` and `hardware_minimum: int = 3`, with the comment
     `# The hardware series: how many journal samples it keeps, and how many it needs to judge.`
   - docstring bullet: `- `hardware_window` (32) and `hardware_minimum` (3): the samples the hardware series judges, and the fewest it will judge.`
   - `__post_init__`, appended:
     ```python
             for name in ("hardware_window", "hardware_minimum"):
                 value = getattr(self, name)
                 if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                     raise ValueError(
                         f"estimate.{name} must be a whole number of at least 1: {value!r}"
                     )
             if self.hardware_minimum > self.hardware_window:
                 raise ValueError("estimate.hardware_minimum must not exceed estimate.hardware_window")
     ```
   - `from_table`, in `cls(...)` after `network_timeout_s=...`:
     `hardware_window=section.get("hardware_window", 32),` and
     `hardware_minimum=section.get("hardware_minimum", 3),`.
2. **New module `vibey_gh/hardware_series.py`** (provenance line 1 from `vibey_gh/fit.py:1`):
   - `HARDWARE_SAMPLE = "hardware_sample"` (the journal `kind`).
   - `class HardwareSeries(HardwareSeriesInterface)`:
     `__init__(self, journal: FitJournalInterface, *, sampler: PressureSamplerInterface | None = None, window: int = 32, minimum: int = 3) -> None`.
     `measure(self, stages: Sequence[Stage], *, offline: bool, at: float) -> tuple[Coordinate, Coordinate]`:
     ```python
             del stages, offline  # the machine is read whatever the path, and it never leaves it
             reading = (self._sampler or pressure_sampler()).sample()
             entry: dict[str, object] = {"kind": HARDWARE_SAMPLE, "at": at, **asdict(reading)}
             self._journal.append(entry)
             series = self._journal.entries(HARDWARE_SAMPLE, last=self._window)
             if not series or series[-1] != entry:
                 # No journal, or one that could not be written: this sample still counts.
                 series = [*series, entry][-self._window :]
             return self._stability(series, at), self._reliability(series, at)
     ```
   - `where` text (a private method): `f"in the fit journal ({self._journal.path})"` when
     `self._journal.path` is not `None`, else `"with no journal (--no-journal keeps no series)"`.
   - `_stability(series, at)` → `Coordinate("hardware", "stability", ...)`:
     1. `n = len(series)`; `n < minimum` → `None`, source
        `f"{n} hardware sample(s) {where}; stability is variance over a series and needs at least {minimum}"`.
     2. `free` = every `free_fraction` in the series that is a finite number (an `int` or `float`,
        not a `bool`); `len(free) < minimum` → `None`, source
        `f"this machine stated its free memory in {len(free)} of {n} sample(s); stability needs {minimum}"`.
     3. `mean = statistics.fmean(free)`, `spread = statistics.pstdev(free)`,
        `cv = spread / mean if mean > 0 else 1.0`; `parts = [max(0.0, 1.0 - cv)]`; text
        `f"over {n} samples free memory was {mean:.1%} ± {spread:.1%} (cv {cv:.3f})"`.
     4. Swap writes: for each consecutive pair whose `swapouts` are both `int` (not `bool`) and the
        later is not smaller (a smaller one is a counter reset by a reboot, not an interval), the
        step is `later - earlier`. With at least one step, `quiet = steps equal to 0`;
        `parts.append(quiet / len(steps))`; text += `f"; {quiet} of {len(steps)} interval(s) wrote nothing to swap"`.
        With none, text += `"; swap writes were not stated, so free memory alone is judged"`.
     5. Value `round(min(parts), 4)`.
   - `_reliability(series, at)` → `Coordinate("hardware", "reliability", ...)`:
     1. `n < minimum` → `None`, source
        `f"{n} hardware sample(s) {where}; reliability is the headroom held across a series and needs at least {minimum}"`.
     2. Per sample: `load_1m` and `cpus` finite numbers with `cpus > 0` give
        `min(max(1.0 - load_1m / cpus, 0.0), 1.0)`; a finite `thermal` gives
        `min(max(thermal, 0.0), 1.0)`; the sample's headroom is the smaller of those present, and a
        sample with neither is skipped. Fewer than `minimum` headrooms → `None`, source
        `f"CPU load and thermal state were stated in {len(values)} of {n} sample(s); reliability needs {minimum}"`.
     3. Value `round(statistics.fmean(values), 4)`; source
        `f"mean headroom {mean:.1%} over {len(values)} samples (CPU load against this machine's CPUs); {heat}"`
        where `heat` is `"thermal state not stated by this machine"` when no sample states one,
        `"never throttled"` when the least stated is `>= 1.0`, else
        `f"throttled to {least:.0%} at worst"`.
   - It never raises for a reading the machine would not give.
3. **New interface `vibey_gh/interfaces/hardware_series_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`): `HardwareSeriesInterface(MaterialProbeInterface, Protocol)`,
   `runtime_checkable`, docstring "The hardware material's stability and reliability, judged over
   the rolling series of pressure samples kept in the fit journal." Add it to `EXEMPT` in
   `test/test_port_parity.py` with the reason
   `"class contract: HardwareSeries; the seam it implements, MaterialProbeInterface, has ScriptedMaterialProbe"`.
4. **The composition.** `EstimateProbes.build` (`vibey_gh/estimate_probes.py`) appends
   `HardwareSeries(FitJournal(journal), window=cfg.estimate.hardware_window, minimum=cfg.estimate.hardware_minimum)`
   after the network probe; `journal` leaves its `del` line (delete the line if nothing is left in it).
5. **The command's help** (`vibey_gh/cli.py:1687-1697`), with `edit_file`: the `--journal` help
   becomes `"the fit journal: its observations inform the duration, and each estimate appends one hardware sample to it for the hardware series (default: $VIBEY_GH_FIT_JOURNAL, else ~/.local/state/vibey-gh/fit.jsonl)"`
   (split across string lines the way the current help is); the `--no-journal` help becomes
   `"read and append nothing: the duration is unknown, and the hardware series is this one sample"`.

## Where to change
- New: `vibey_gh/hardware_series.py`, `vibey_gh/interfaces/hardware_series_interface.py`,
  `test/test_hardware_series.py`.
- Edit with `edit_file`: `vibey_gh/config.py` (behaviour 1), `vibey_gh/estimate_probes.py`
  (behaviour 4), `vibey_gh/cli.py` (behaviour 5 only, two help strings); one `EXEMPT` entry in
  `test/test_port_parity.py`.
- Pattern to copy: `FitLoop.replay` reading a bounded window from the journal
  (`vibey_gh/fitloop.py:180-194`).

## Acceptance criteria
- [ ] Each `measure` appends exactly one `hardware_sample` line; `recorded_observations` never
      returns it.
- [ ] Fewer than `hardware_minimum` samples leave both coordinates unknown, saying how many there
      are and how many are needed.
- [ ] Stability is variance over the series (free memory and swap-write intervals), reliability the
      mean headroom across it, with the arithmetic in each source.
- [ ] Every existing `vibey-gh estimate` command test (`test/test_operation_estimate.py`, the `repo`
      fixture) passes unmodified. Those tests now reach the default series through
      `EstimateProbes`, which reads this machine's own statements (kernel files on Linux;
      `vm_stat`, `sysctl` and `pmset` on macOS) into the test's own journal (`JOURNAL_ENV` points
      into `tmp_path`, `test_operation_estimate.py:331`); none of their assertions depends on those
      readings, and a test that needs exact readings injects probes through `_estimate(..., probes=...)`.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_hardware_series.py` (provenance line 1 from `test/test_fit.py:1`; import
`from fakes import InMemoryFitJournal, ScriptedPressureSampler`). A helper
`def reading(free=0.25, swapouts=100, load=2.0, cpus=8.0, thermal=None) -> PressureReading`
builds `PressureReading(free, swapouts, load, cpus, thermal, "linux")`. Unless stated,
`journal = InMemoryFitJournal(Path("fit.jsonl"))` and `window=32, minimum=3`; `measure` is called
with `(), offline=True` and `at` 1.0, 2.0, 3.0 … in turn:
- `test_the_series_declares_its_seams` — instance of `HardwareSeriesInterface` and `MaterialProbeInterface`.
- `test_each_estimate_appends_one_hardware_sample` — one `measure(at=7.0)`: `journal.lines == [{"kind": "hardware_sample", "at": 7.0, "free_fraction": 0.25, "swapouts": 100, "load_1m": 2.0, "cpus": 8.0, "thermal": None, "platform": "linux"}]`.
- `test_a_short_series_leaves_both_unknown` — two samples: both values `None`; the stability
  source is `"2 hardware sample(s) in the fit journal (fit.jsonl); stability is variance over a series and needs at least 3"`.
- `test_a_steady_machine_is_stable` — three identical readings: stability `1.0`, source contains
  `"(cv 0.000)"` and `"2 of 2 interval(s) wrote nothing to swap"`.
- `test_swinging_memory_and_swap_writes_lower_stability` — free `0.1`, `0.3`, `0.2` and swapouts
  `100`, `150`, `150`: stability `0.5` (free part `0.5918`, swap part `0.5`, the smaller wins).
- `test_a_reset_swap_counter_is_not_an_interval` — swapouts `500`, `10`, `10`, free steady: the
  source says `"1 of 1 interval(s) wrote nothing to swap"` and stability `1.0`.
- `test_unstated_swap_leaves_free_memory_to_judge` — swapouts `None` ×3, free steady: stability
  `1.0`, source contains `"swap writes were not stated"`.
- `test_unstated_free_memory_leaves_stability_unknown` — free `None` ×3: stability `None`, source
  contains `"free memory in 0 of 3 sample(s)"`.
- `test_reliability_is_the_headroom_held_across_the_series` — load `2.0`, cpus `8.0` ×3 with
  thermal `None`, `None`, `0.7`: reliability `0.7333`, source contains `"throttled to 70% at worst"`;
  with thermal `1.0` ×3 and the same load, reliability `0.75` and `"never throttled"`; with thermal
  `None` ×3, `"thermal state not stated by this machine"`.
- `test_unstated_load_and_heat_leave_reliability_unknown` — load, cpus and thermal `None` ×3:
  reliability `None`, source contains `"stated in 0 of 3 sample(s)"`.
- `test_the_window_bounds_the_series` — `window=3`: five samples, the first two with free `0.9` and
  the last three with free `0.25`: stability `1.0` (only the last three are judged).
- `test_without_a_journal_the_series_is_this_sample` — `HardwareSeries(FitJournal(None), sampler=...)`:
  both `None`, and the source says `"1 hardware sample(s) with no journal (--no-journal keeps no series)"`.
- `test_the_series_is_kept_in_the_real_fit_journal` — a file first holding one
  `{"kind": "observation", "payload_bytes": 1024, "elapsed_s": 60.0, "concurrent": 1, "model": "m"}`
  line; `HardwareSeries(FitJournal(path), sampler=ScriptedPressureSampler(reading()))` measured three
  times: the third result's stability is `1.0`; the file has four lines, three of kind
  `hardware_sample`; `recorded_observations(path, "m")` still returns exactly the one observation.
- `test_the_hardware_bounds_are_configuration` — `.vibey-gh.toml` =
  `"[estimate]\nhardware_window = 10\nhardware_minimum = 4\n"` loads both; defaults are `32` and
  `3`; `EstimateConfig(hardware_window=0)` → `"at least 1"`; `(hardware_minimum=True)` →
  `"at least 1"`; `(hardware_window=2, hardware_minimum=3)` → `"must not exceed"`.
- `test_the_composition_keeps_the_hardware_series` —
  `EstimateProbes().build(GhConfig(root=tmp_path), stage_names=STAGE_NAMES, journal=tmp_path / "fit.jsonl")`
  holds one `HardwareSeries` (build reads nothing; nothing is sampled).

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_hardware_series.py test/test_operation_estimate.py test/test_fitloop.py test/test_delivery_config.py test/test_feasibility.py test/test_port_parity.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- `vibey_gh/pressure.py`, `vibey_gh/fitloop.py`, `vibey_gh/fit.py` (earlier lanes and other owners).
- `vibey-gh fit` appending samples too (a later lane may; this one keeps to the estimate).
- `hardware.availability` (the fit's, unchanged).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
