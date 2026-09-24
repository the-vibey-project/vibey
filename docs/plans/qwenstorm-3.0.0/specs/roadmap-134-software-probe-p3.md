## Title
feat(gh): `vibey-gh estimate` runs the configured probes, starting with the software probe

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Acceptance: "`vibey-gh estimate --json` shows
18/18 coordinates measured on a machine where every probe can look. Each `unknown` names its
missing source"). `roadmap-134-software-probe-p1` gave `OperationEstimator` a `probes` seam and
`roadmap-134-software-probe-p2` built the first probe, but the command still constructs the
estimator with no probes (`src/vibey_tools/gh/vibey_gh/cli.py:803-810`), so nothing new reaches the
report. Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`: every measurement runs,
always) and 9.b (`doctrines.md:349`: the composition is a class behind a declared seam, so a test
states exactly which probes run instead of patching the handler) bind this lane. It adds one
composition class, `EstimateProbes`, whose `build()` the handler calls; the network, hardware and
agency lanes each add their probe to `build()` and never edit the handler again. 12.c
(`doctrines.md:455`): every probe is built from `[estimate]`.

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **New module `vibey_gh/estimate_probes.py`** (provenance line 1 from
   `vibey_gh/operation_estimate.py:1`):
   ```python
   """The probes `vibey-gh estimate` runs, built from `[estimate]` (#134).

   One place names every probe the command runs, in the order they run, so the handler never
   changes when a probe is added and a test can state exactly which probes run. Building a
   probe reads nothing: every probe looks only when the estimate asks it to measure. A
   configuration a probe cannot be built from is a `ValueError` naming what is wrong, which
   the command reports as a usage error.
   """

   from __future__ import annotations

   from collections.abc import Sequence
   from pathlib import Path

   from vibey_gh.config import GhConfig
   from vibey_gh.interfaces.estimate_probes_interface import EstimateProbesInterface
   from vibey_gh.interfaces.material_probe_interface import MaterialProbeInterface
   from vibey_gh.software_probe import SoftwareProbe


   class EstimateProbes(EstimateProbesInterface):
       """The default probes, in the order `vibey-gh estimate` runs them."""

       def build(
           self, cfg: GhConfig, *, stage_names: Sequence[str], journal: Path | None
       ) -> tuple[MaterialProbeInterface, ...]:
           del stage_names, journal  # read by probes later lanes add (network, hardware)
           return (SoftwareProbe(cfg, pins=cfg.estimate.pins),)
   ```
2. **New interface `vibey_gh/interfaces/estimate_probes_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`): a `runtime_checkable`
   `EstimateProbesInterface(Protocol)` declaring the same `build` signature, with `GhConfig`,
   `Path` and `MaterialProbeInterface` imported only under `TYPE_CHECKING` (plus
   `from collections.abc import Sequence`), and the docstring: "The probes an estimate runs,
   built from the configuration without reading anything. A configuration a probe cannot be
   built from is a `ValueError` naming what is wrong."
3. **The handler.** `_estimate` in `vibey_gh/cli.py` (`:774-822`):
   - gains a keyword parameter `probes: EstimateProbesInterface | None = None`, placed last among
     its parameters (after any keyword parameters it already has);
   - adds `from vibey_gh.estimate_probes import EstimateProbes` to its local imports (`:778-780`);
   - after the journal block (`:796-802`, ending `journal = FitLoop.default_journal()`) inserts:
     ```python
         try:
             measured_by = (probes or EstimateProbes()).build(
                 cfg, stage_names=pipeline.names, journal=journal
             )
         except ValueError as exc:
             print(f"vibey-gh estimate: {exc}", file=sys.stderr)
             return 2
     ```
   - passes `probes=measured_by,` as the last keyword of the `operation_estimate.OperationEstimator(...)`
     call (`:803-810`).
   - At module top, `from vibey_gh.interfaces.estimate_probes_interface import EstimateProbesInterface`
     joins the other `vibey_gh.interfaces` imports (`cli.py:35-36`), in alphabetical position.
4. **Fake** appended to `test/fakes.py`:
   ```python
   class FixedProbeSet:
       """A probe composition that hands back the probes it was given, or raises, and records
       every build as `(cfg, stage_names, journal)` (#134)."""

       def __init__(self, *probes: object, error: Exception | None = None) -> None:
           self._probes = probes
           self._error = error
           self.calls: list[tuple[object, tuple[str, ...], object]] = []

       def build(self, cfg: object, *, stage_names: Sequence[str], journal: object) -> tuple[Any, ...]:
           self.calls.append((cfg, tuple(stage_names), journal))
           if self._error is not None:
               raise self._error
           return self._probes
   ```
   (add `Any` to the `typing` import of `test/fakes.py` if absent). Register
   `EstimateProbesInterface` → `FixedProbeSet` in `test/test_port_parity.py` the way
   `ScriptedGitRunner` is registered.

## Where to change
- New: `vibey_gh/estimate_probes.py`, `vibey_gh/interfaces/estimate_probes_interface.py`.
- Edit with `edit_file` (`cli.py` is 1887 lines; read `sed -n '770,825p' vibey_gh/cli.py` and
  `sed -n '1,40p'` first): `vibey_gh/cli.py` (behaviour 3 only).
- Tests: append to `test/test_operation_estimate.py` (it holds the `repo` fixture,
  `:325-336`, that makes `vibey-gh estimate` hermetic); append to `test/fakes.py` and
  `test/test_fakes.py`; one entry in `test/test_port_parity.py`.
- Pattern to copy for a handler seam with a production default: `_check(args, resolver=...)`
  (`cli.py:77-80`), exercised by `test/test_gh_cli.py:108`.

## Acceptance criteria
- [ ] `vibey-gh estimate --json` on a repository that pins a distribution which is not installed
      reports `software.stability` `0.0` naming it (`test_the_command_runs_the_configured_probes`).
- [ ] A probe that cannot be built from the configuration is a usage error (exit 2) naming why.
- [ ] Every existing `test/test_operation_estimate.py` and `test/test_gh_cli.py` test passes unmodified.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
Append to `test/test_operation_estimate.py` (add `import argparse`,
`from vibey_gh.cli import _estimate` (merge into the existing `from vibey_gh.cli import main`),
`from vibey_gh.config import EstimateConfig, GhConfig`,
`from vibey_gh.estimate_probes import EstimateProbes`,
`from vibey_gh.feasibility import STAGE_NAMES` (merge into the existing `vibey_gh.feasibility`
import), `from vibey_gh.interfaces.estimate_probes_interface import EstimateProbesInterface`,
`from vibey_gh.software_probe import SoftwareProbe`, and `FixedProbeSet` to the `from fakes import`
line, all in the top import block; run `isort` on the file once):
- `test_the_probe_composition_declares_its_seam` — `isinstance(EstimateProbes(), EstimateProbesInterface)`.
- `test_the_default_probes_are_built_from_the_configuration` —
  `cfg = GhConfig(root=tmp_path, estimate=EstimateConfig(pins=(("vibey", "3.0.0"),)))`;
  `probes = EstimateProbes().build(cfg, stage_names=STAGE_NAMES, journal=None)`;
  `len(probes) == 1`, `isinstance(probes[0], SoftwareProbe)` and `probes[0].pins == (("vibey", "3.0.0"),)`.
- `test_the_command_runs_the_configured_probes(repo, capsys)` — uses this module's `repo` fixture
  exactly as `test_the_command_speaks_json` (`:360-363`) does. Write
  `'[estimate.pins]\n"no-such-distribution-vibey-gh-tests" = "1.0"\n'` to `root / ".vibey-gh.toml"`
  (the name `test/test_fallback_pin.py:284` already relies on never being installed); run
  `main(["estimate", "--operation", "develop", "--json"])`; in the JSON `state`, the
  `software.stability` row has `value == 0.0` and its `source` contains
  `"no-such-distribution-vibey-gh-tests pinned 1.0, not installed"`, and the
  `software.reliability` row has `value == 0.0` and `"drifted from its configuration"` in its
  `source` (the test repository has no hooks).
- `test_a_probe_that_cannot_be_built_is_a_usage_error(repo, capsys)` — call
  `_estimate(argparse.Namespace(operation="develop", start=None, json=False, model="", base_url="", payload_bytes=8192, online=False, journal=None, no_journal=True), probes=FixedProbeSet(error=ValueError("bad probe")))`
  directly; it returns `2`, stderr contains `"vibey-gh estimate: bad probe"`, and the set's
  `calls[0][1]` equals the default pipeline's stage names (`STAGE_NAMES`) and `calls[0][2] is None`.
  (It returns before the estimator is built, so no sampler is reached.)

Append to `test/test_fakes.py`:
- `test_probe_set_fake_hands_back_its_probes_or_raises` — `FixedProbeSet("p").build(None, stage_names=["a"], journal=None) == ("p",)` with `calls == [(None, ("a",), None)]`; with `error=ValueError("x")` it raises.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_operation_estimate.py test/test_gh_cli.py test/test_fakes.py test/test_port_parity.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    cd src/vibey_tools/gh && PYTHONSAFEPATH=1 PYTHONPATH="$PWD" python3 -S -c "import vibey_gh.cli"   # the self-hosted hook's stdlib-only import
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- The network, hardware and agency probes (each adds itself to `EstimateProbes.build` in its own
  lane); `vibey_gh/operation_estimate.py`; `vibey_gh/config.py`.
- The `--journal` help text (`roadmap-134-hardware-series-p3` changes it when the series appends).
- Reading the billing ledger in `_estimate` or `OperationEstimator` (`roadmap-134-cost-integral-p4`);
  if that lane has landed, its lines in `_estimate` stay exactly as they are, and `probes=` is added
  beside whatever keywords the estimator call already passes.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
