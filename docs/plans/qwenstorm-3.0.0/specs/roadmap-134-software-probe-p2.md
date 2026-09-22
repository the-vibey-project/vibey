## Title
feat(gh): the software probe — declared pins against installed versions, and managed-automation drift as reliability

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *software*: "pins against installed
versions, runner health, config drift against `vibey-gh check`"; "Proposed child issues" 2: "Pins
against installed versions (reusing `installed_distributions_interface`), plus `vibey-gh check`
drift as reliability"). 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) requires the software
material to be measured; 10.f (`doctrines.md:419`) requires an unmeasurable coordinate to stay
unknown with its reason; 10.e (`doctrines.md:417`) requires the family's own readers; 12.c
(`doctrines.md:455`) requires which distributions are pinned to be declared, never hard-coded.

Verified gap (integration clone): `vibey-gh estimate` reads only software *availability*, from the
fit (`vibey_gh/operation_estimate.py:177-183`). `software.stability` and `software.reliability` are
always "unmeasured" (`vibey_gh/feasibility.py:105-106`). The two readers this probe needs already
exist and are reused, not copied: `InstalledDistributionsInterface`
(`vibey_gh/interfaces/installed_distributions_interface.py:18-39`, implemented by
`fallback_pin.InstalledDistributions`, `vibey_gh/fallback_pin.py:56-104`), and the drift half of
`vibey-gh check` — `install.installed(cfg, local=False, fallback_pin=pin)`
(`vibey_gh/install.py:620-701`; `local=False` is `check --ci`, `vibey_gh/cli.py:81`, and skips the
only subprocess, `install.py:688-699`). Both are local reads, so the estimate's offline switch never
withholds them. These are drift readings against a declared baseline, not a variance series; the
network and hardware lanes carry the series (#134 Scope 2).

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **Configuration (12.c).** `EstimateConfig` (`vibey_gh/config.py:1317-1466`):
   - new field, appended after `forecast_size_weights` (`:1360-1366`):
     `pins: tuple[tuple[str, str], ...] = ()` with the comment
     `# [estimate.pins]: distribution = "exact version". Empty pins nothing, so version drift is unknown.`
   - docstring: add the bullet
     `- `pins` (empty): `distribution = "version"` pairs the software probe compares with what is installed; a pin is exact.`
     after the `report_first` bullet (`:1335-1337`).
   - `__post_init__`, appended at its end (after `:1416`):
     ```python
             _unique_nonempty("estimate.pins", tuple(name for name, _ in self.pins))
             for name, version in self.pins:
                 if not isinstance(version, str) or not version.strip():
                     raise ValueError(
                         f"estimate.pins.{name} must be a non-empty version string: {version!r}"
                     )
     ```
   - `from_table`, after the `size_weights` check (`:1434-1435`):
     ```python
             pins = section.get("pins", {})
             if not isinstance(pins, dict):
                 raise TypeError('estimate.pins must be a table of distribution = "version"')
     ```
     and, as the last keyword of the `cls(...)` call (after `forecast_size_weights=...`,
     `:1459-1465`): `pins=tuple((str(name), version) for name, version in pins.items()),`.
2. **New module `vibey_gh/software_probe.py`** (provenance line 1 copied from
   `vibey_gh/fallback_pin.py:1`), module docstring stating what the two readings are and that
   nothing here leaves the machine. It holds:
   - Constants: `NO_PINS = "no pins declared: [estimate.pins] names no distribution, so version drift cannot be measured"`.
   - `class ManagedAutomationDrift(ManagedAutomationDriftInterface)`:
     `__init__(self, resolver: FallbackPinResolverInterface | None = None) -> None` storing it;
     `problems(self, cfg: GhConfig) -> tuple[str, ...]`:
     ```python
             pin = (self._resolver or FallbackPinResolver()).resolve(cfg)
             _, problems = install.installed(cfg, local=False, fallback_pin=pin)
             return tuple(problems)
     ```
   - `class SoftwareProbe(SoftwareProbeInterface)`:
     `__init__(self, cfg: GhConfig, *, pins: Sequence[tuple[str, str]] = (), distributions: InstalledDistributionsInterface | None = None, drift: ManagedAutomationDriftInterface | None = None) -> None`
     storing `cfg`, `tuple(pins)`, `InstalledDistributions()` when `distributions is None`, and
     `ManagedAutomationDrift()` when `drift is None`; a read-only property
     `pins -> tuple[tuple[str, str], ...]`; and
     `measure(self, stages: Sequence[Stage], *, offline: bool, at: float) -> tuple[Coordinate, Coordinate]`
     returning `(self._stability(at), self._reliability(at))`. `stages` and `offline` are unused
     (write `del stages, offline  # local reads: the path and the switch change nothing`).
   - `_stability(self, at)`: no pins → `Coordinate("software", "stability", None, NO_PINS, at)`.
     Otherwise, for each `(name, pinned)` in order: `installed = self._distributions.version(name)`;
     `installed == pinned` counts as held; `installed is None` records
     `f"{name} pinned {pinned}, not installed"`; any other value records
     `f"{name} pinned {pinned}, {installed} installed"`. Value
     `round(held / len(pins), 4)`; source
     `f"pins: {held} of {len(pins)} installed at the pinned version"`, followed, when any drifted,
     by `f" — drift: {'; '.join(drifted)}"`.
   - `_reliability(self, at)`: `problems = self._drift.problems(self._cfg)` inside
     `try/except (OSError, ValueError) as exc`, which returns
     `Coordinate("software", "reliability", None, f"the managed automation could not be compared with its configuration: {exc}", at)`.
     No problems → value `1.0`, source
     `"managed automation matches what the configuration renders (the drift `vibey-gh check --ci` reports)"`.
     Problems → value `0.0` (drift is a yes/no fact: the automation matches what the
     configuration renders, or it does not), source
     `f"managed automation drifted from its configuration ({len(problems)} problem(s)): {shown}"`
     where `shown` is the first three problems joined by `"; "`, followed by
     `f"; and {len(problems) - 3} more"` when there are more than three.
   - It never raises for a reading that failed, and it never reads the network.
3. **New interface file `vibey_gh/interfaces/software_probe_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`), declaring two Protocols, both
   `runtime_checkable`, with `GhConfig` imported under `TYPE_CHECKING`:
   - `ManagedAutomationDriftInterface` with
     `def problems(self, cfg: GhConfig) -> tuple[str, ...]:` — docstring: "What `vibey-gh check
     --ci` would report as drift between the managed automation and what `cfg` renders; empty
     when they match. May raise `OSError` or `ValueError` when it cannot compare."
   - `SoftwareProbeInterface(MaterialProbeInterface, Protocol)` with docstring "The software
     material: version drift against declared pins, and managed-automation drift." and a
     property `pins -> tuple[tuple[str, str], ...]`.
4. **Fakes** appended to `test/fakes.py`:
   ```python
   class ScriptedAutomationDrift:
       """An automation-drift check that answers scripted problems, or raises, and records
       each configuration it was asked about (#134)."""

       def __init__(self, *problems: str, error: Exception | None = None) -> None:
           self._problems = problems
           self._error = error
           self.calls: list[object] = []

       def problems(self, cfg: object) -> tuple[str, ...]:
           self.calls.append(cfg)
           if self._error is not None:
               raise self._error
           return self._problems


   class ScriptedDistributions:
       """Installed distributions stated exactly: `{name: version}`; anything else is not
       installed, and nothing is installed from source or owns any file (#134)."""

       def __init__(self, versions: Mapping[str, str] | None = None) -> None:
           self.versions = dict(versions or {})

       def version(self, distribution: str) -> str | None:
           return self.versions.get(distribution)

       def installed_from_source(self, distribution: str) -> bool:
           return False

       def installs(self, distribution: str, path: Path) -> bool:
           return False
   ```
   (add `Mapping` and `Path` imports to `test/fakes.py`'s import block if absent). Register
   `ManagedAutomationDriftInterface` → `ScriptedAutomationDrift` and
   `InstalledDistributionsInterface` → `ScriptedDistributions` in `test/test_port_parity.py` the
   way `ScriptedGitRunner` is registered, and add `SoftwareProbeInterface` to that file's
   `EXEMPT` with the reason `"class contract: SoftwareProbe; the seam it implements, MaterialProbeInterface, has ScriptedMaterialProbe"`.

## Where to change
- New: `vibey_gh/software_probe.py`, `vibey_gh/interfaces/software_probe_interface.py`,
  `test/test_software_probe.py`.
- Edit with `edit_file` (config.py is 1970 lines; read slices with `sed -n`): `vibey_gh/config.py`
  (behaviour 1); append to `test/fakes.py` and `test/test_fakes.py`; entries in
  `test/test_port_parity.py`.
- Patterns to copy: the `InstalledDistributionsInterface` seam in `FallbackPinResolver.__init__`
  (`vibey_gh/fallback_pin.py:108-117`); the `requirements`/`forecast` table checks in
  `EstimateConfig.from_table` (`config.py:1421-1435`).

## Acceptance criteria
- [ ] With `[estimate.pins]` empty, `software.stability` is unknown with exactly `NO_PINS` as source.
- [ ] A drifted or missing pin is named in the source and lowers the value.
- [ ] A repository whose hooks/workflows are missing reads `software.reliability` `0.0` with the
      problems named; an unreadable comparison is unknown, never zero.
- [ ] `grep -n "subprocess\|urllib\|socket" vibey_gh/software_probe.py` prints nothing.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_software_probe.py` (provenance line 1 copied from `test/test_fit.py:1`; import
`from fakes import ScriptedAutomationDrift, ScriptedDistributions`; `GhConfig(root=tmp_path)` for
every probe):
- `test_the_probe_declares_its_seams` — `SoftwareProbe(GhConfig(root=tmp_path))` is an instance of
  `SoftwareProbeInterface` and `MaterialProbeInterface`; `ManagedAutomationDrift()` of
  `ManagedAutomationDriftInterface`.
- `test_pins_held_at_their_version_are_stable` — pins `(("vibey", "3.0.0"), ("ruff", "0.16.3"))`,
  `ScriptedDistributions({"vibey": "3.0.0", "ruff": "0.16.3"})`, `drift=ScriptedAutomationDrift()`:
  `measure((), offline=True, at=5.0)[0]` has value `1.0`, `measured_at == 5.0`, source
  `"pins: 2 of 2 installed at the pinned version"`.
- `test_drifted_and_missing_pins_are_named` — same pins, `ScriptedDistributions({"vibey": "2.1.0"})`:
  value `0.0`; source contains `"vibey pinned 3.0.0, 2.1.0 installed"` and
  `"ruff pinned 0.16.3, not installed"`. With `{"vibey": "3.0.0"}`: value `0.5`.
- `test_no_pins_is_unknown_and_says_why` — value `None`, source `== NO_PINS`.
- `test_matching_automation_is_reliable_and_drift_is_named` — `ScriptedAutomationDrift()` → `[1]`
  value `1.0`; `ScriptedAutomationDrift("a is missing", "b is out of date", "c", "d")` → value
  `0.0`, source contains `"(4 problem(s)): a is missing; b is out of date; c; and 1 more"`; the
  fake's `calls` holds the probe's `GhConfig`.
- `test_automation_that_cannot_be_compared_is_unknown` —
  `ScriptedAutomationDrift(error=OSError("denied"))` → value `None`, source ends with `"denied"`.
- `test_the_probe_never_leaves_the_machine_so_offline_changes_nothing` — the same probe's
  `measure(..., offline=True, at=1.0)` equals its `measure(..., offline=False, at=1.0)`.
- `test_the_real_drift_check_reads_the_repository` — an in-test resolver class whose
  `resolve(cfg)` returns `FallbackPin(None)` (from
  `vibey_gh.interfaces.fallback_pin_resolver_interface`) and records `cfg`;
  `ManagedAutomationDrift(resolver).problems(GhConfig(root=tmp_path))` on an empty `tmp_path`
  is non-empty, contains `".githooks/commit-msg is missing"` (`install.py:34-35`, `:637-638`), and
  the resolver recorded that config. `ManagedAutomationDrift()` (default resolver) on the same
  root also returns a non-empty tuple.
- `test_the_pins_are_configuration` — `.vibey-gh.toml` = `[estimate.pins]\nvibey = "3.0.0"\n`;
  `load_config(tmp_path).estimate.pins == (("vibey", "3.0.0"),)`; `EstimateConfig().pins == ()`;
  `EstimateConfig(pins=(("vibey", " "),))` raises `ValueError` matching `"non-empty version string"`;
  `EstimateConfig(pins=(("", "1"),))` → `"estimate.pins entries must be non-empty"`;
  `EstimateConfig(pins=(("a", "1"), ("a", "2")))` → `"entries must be unique"`;
  `EstimateConfig.from_table({"pins": "vibey"})` raises `TypeError` matching `"estimate.pins must be a table"`.

Append to `test/test_fakes.py`:
- `test_automation_drift_fake_answers_raises_and_records` and
  `test_distributions_fake_states_exact_versions_only`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_software_probe.py test/test_fakes.py test/test_port_parity.py test/test_delivery_config.py test/test_feasibility.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- Wiring the probe into `vibey-gh estimate` (`roadmap-134-software-probe-p3`); `vibey_gh/cli.py`;
  `vibey_gh/operation_estimate.py`.
- Runner health (the conductor-bridge lane `roadmap-134-agent-information-probes` owns engine
  health); the fingerprint, documentation and marketplace halves of `vibey-gh check`.
- `vibey_gh/feasibility.py`'s `MEASURED_BY` texts.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
