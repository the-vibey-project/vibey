## Title
feat(gh): the network probe — declared endpoints per stage, sampled for reachability, loss and latency steadiness behind the offline switch

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *network*: "reachability, latency and
loss to each required endpoint (declared per stage in `[estimate]`)"; Scope 2: "Stability and
reliability are computed from series (variance, success rate), not from single readings";
"Proposed child issues" 3). Sub-doctrines: 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`),
10.f (`doctrines.md:419`: missing evidence is reported as unknown), 12.c (`doctrines.md:455`: the
endpoints are declared, and a default never invents an operator decision).

Verified gap (integration clone): all three network coordinates are always "unmeasured"
(`src/vibey_tools/gh/vibey_gh/feasibility.py:94-96`), yet the default path requires
`network.availability` at seven of its nine stages (`feasibility.py:253-321`). `[estimate]` has no
endpoints key (`vibey_gh/config.py:1344-1366`). Which endpoints each stage needs is #134 open
question 3 ("Which endpoints define "network" for each stage (forge, package index, model runner,
bus)? Should they be declared per adopter?"). This lane **records it and does not answer it**: the
default is empty, so the network coordinates stay `unknown` with the reason "no endpoints
declared", and nothing here names a host. The offline switch is today's, exactly: a runner on this
machine is read even offline, anything else only with `--online` or `[estimate] offline = false`
(`vibey_gh/operation_estimate.py:106-117`, `:128`; `vibey_gh/cli.py:806`), and the same rule is
applied to each endpoint through `OperationEstimator.is_local`.

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **Configuration.** `EstimateConfig` (`vibey_gh/config.py`), each addition appended after the
   `pins` field and its checks that `roadmap-134-software-probe-p2` added:
   - fields:
     ```python
         # [estimate.endpoints]: stage = ["tcp://host:port", "https://host/path", ...]. Empty by
         # default: which endpoints a stage needs is the operator's to declare (#134 question 3).
         endpoints: tuple[tuple[str, tuple[str, ...]], ...] = ()
         network_samples: int = 3
         network_timeout_s: float = 5.0
     ```
   - docstring bullets after the `pins` bullet:
     `- `endpoints` (empty): per stage, the endpoints the network probe samples; empty leaves the network unknown.`
     and `- `network_samples` (3) and `network_timeout_s` (5.0): attempts per endpoint, and seconds each may take.`
   - `__post_init__`, appended at its end:
     ```python
             _unique_nonempty("estimate.endpoints", tuple(stage for stage, _ in self.endpoints))
             for stage, declared in self.endpoints:
                 if not declared or any(not isinstance(e, str) or not e.strip() for e in declared):
                     raise ValueError(
                         f"estimate.endpoints.{stage} must be a non-empty list of endpoint strings"
                     )
             samples = self.network_samples
             if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
                 raise ValueError(
                     f"estimate.network_samples must be a whole number of at least 1: {samples!r}"
                 )
             timeout = _finite_forecast_number("estimate.network_timeout_s", self.network_timeout_s)
             if timeout <= 0:
                 raise ValueError("estimate.network_timeout_s must be a positive number of seconds")
     ```
   - `from_table`, after the `pins` check:
     ```python
             endpoints = section.get("endpoints", {})
             if not isinstance(endpoints, dict) or not all(
                 isinstance(declared, list) for declared in endpoints.values()
             ):
                 raise TypeError(
                     'estimate.endpoints must be a table of stage = ["tcp://host:port", ...]'
                 )
     ```
     and, after `pins=...` in the `cls(...)` call:
     ```python
                 endpoints=tuple(
                     (str(stage), tuple(declared)) for stage, declared in endpoints.items()
                 ),
                 network_samples=section.get("network_samples", 3),
                 network_timeout_s=_finite_forecast_number(
                     "estimate.network_timeout_s", section.get("network_timeout_s", 5.0)
                 ),
     ```
2. **New module `vibey_gh/network_probe.py`** (provenance line 1 from `vibey_gh/fit.py:1`), with
   `class NetworkProbe(NetworkProbeInterface)`:
   - `__init__(self, endpoints: Sequence[tuple[str, Sequence[str]]] = (), *, connector: EndpointConnectorInterface | None = None, samples: int = 3, timeout_s: float = 5.0) -> None`:
     `self._endpoints = {stage: tuple(declared) for stage, declared in endpoints}`,
     `EndpointConnector()` when `connector is None`, and the two numbers.
   - `@classmethod from_config(cls, config: EstimateConfig, stage_names: Sequence[str], *, connector: EndpointConnectorInterface | None = None) -> NetworkProbe`:
     `stray = sorted({stage for stage, _ in config.endpoints} - set(stage_names))`; non-empty →
     `ValueError(f"[estimate.endpoints] names stage(s) the pipeline never reaches: {stray}")`.
     Then for every declared endpoint whose `EndpointConnector.parse(endpoint) is None` →
     `ValueError(f"[estimate.endpoints] {stage}: {endpoint!r} is not tcp://host:port, http://host[:port][/path] or https://host[:port][/path]")`.
     Otherwise `cls(config.endpoints, connector=connector, samples=config.network_samples, timeout_s=config.network_timeout_s)`.
   - `measure(self, stages: Sequence[Stage], *, offline: bool, at: float) -> tuple[Coordinate, Coordinate, Coordinate]`
     returns `(availability, stability, reliability)`, in that order:
     1. `wanted`: every endpoint declared for each stage of `stages`, in path order, each once.
     2. None wanted → all three `value=None` with source
        `f"no endpoints declared for {', '.join(s.name for s in stages)}: [estimate.endpoints] names none, and which endpoints a stage needs is the operator's to declare"`.
        The connector is not called.
     3. `remote = [e for e in wanted if not OperationEstimator.is_local(e)]`. When `offline` and
        `remote` → all three `None` with source
        `f"not probed: {len(remote)} of {len(wanted)} declared endpoint(s) are not on this machine and the estimate is offline (pass --online, or set [estimate] offline = false)"`.
        The connector is not called.
     4. Otherwise each wanted endpoint is attempted `samples` times,
        `connector.attempt(endpoint, timeout_s=timeout_s)`; `answers[e]` is the list of non-`None`
        results.
     5. **availability** = `round(reached / len(wanted), 4)` where `reached` counts endpoints with at
        least one answer; source
        `f"{reached} of {len(wanted)} declared endpoint(s) answered: " + ", ".join(f"{e} {len(answers[e])}/{samples}" for e in wanted)`.
     6. **reliability** (loss) = `round(answered / attempted, 4)` over every attempt; source
        `f"{answered} of {attempted} attempt(s) answered, loss {1 - answered / attempted:.0%}"`.
     7. **stability** (latency steadiness over the samples, a series): consider only reached
        endpoints. None reached → `None`, source
        `"no endpoint answered, so latency has no variance to measure"`. Any reached endpoint with
        fewer than two answers → `None`, source
        `f"latency variance needs two answers from each endpoint; {e} gave {len(answers[e])} of {samples}"`
        (the first such `e`). Otherwise each endpoint's coefficient of variation is
        `statistics.pstdev(a) / statistics.fmean(a)` (`0.0` when the mean is `0`); the worst (largest,
        first on ties) sets the value `round(max(0.0, 1.0 - cv), 4)`, source
        `f"latency steadiness over {samples} sample(s) each: worst coefficient of variation {cv:.3f} at {e}"`.
     Every coordinate is stamped `at`. It never raises for a failed attempt.
   - Imports: `statistics`; `Sequence`; `Coordinate`, `Stage` from `vibey_gh.feasibility`;
     `EstimateConfig` from `vibey_gh.config`; `EndpointConnector`; the interfaces;
     `OperationEstimator` from `vibey_gh.operation_estimate` (for `is_local`, reused, 10.e).
3. **New interface `vibey_gh/interfaces/network_probe_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`):
   `NetworkProbeInterface(MaterialProbeInterface, Protocol)`, `runtime_checkable`, docstring "The
   network material: declared endpoints sampled for reachability, loss and latency steadiness."
   Add it to `EXEMPT` in `test/test_port_parity.py` with the reason
   `"class contract: NetworkProbe; the seam it implements, MaterialProbeInterface, has ScriptedMaterialProbe"`.
4. **The composition.** `EstimateProbes.build` (`vibey_gh/estimate_probes.py`, from
   `roadmap-134-software-probe-p3`) returns
   `(SoftwareProbe(cfg, pins=cfg.estimate.pins), NetworkProbe.from_config(cfg.estimate, stage_names))`;
   `stage_names` is no longer in its `del` line. A stray stage or an unparsable endpoint is then a
   `ValueError` the command already reports as a usage error (exit 2).

## Where to change
- New: `vibey_gh/network_probe.py`, `vibey_gh/interfaces/network_probe_interface.py`,
  `test/test_network_probe.py`.
- Edit with `edit_file`: `vibey_gh/config.py` (behaviour 1; 1970+ lines, read slices with
  `sed -n`), `vibey_gh/estimate_probes.py` (behaviour 4); one `EXEMPT` entry in
  `test/test_port_parity.py`.
- Patterns to copy: the stray-stage refusal in `Pipeline.from_config`
  (`vibey_gh/feasibility.py:418-422`); the `forecast` number checks in `EstimateConfig`
  (`config.py:1392-1409`).

## Acceptance criteria
- [ ] With no `[estimate.endpoints]`, all three network coordinates are unknown with the "no
      endpoints declared" reason, and the connector is never called.
- [ ] Offline, a remote endpoint is never attempted; a loopback endpoint is.
- [ ] Availability, loss and latency steadiness come from the samples as specified; a stage whose
      endpoint never answers is a measured network shortfall.
- [ ] A stray stage or an unparsable endpoint in `[estimate.endpoints]` is refused by name.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_network_probe.py` (provenance line 1 from `test/test_fit.py:1`; import
`from fakes import ScriptedEndpointConnector`; `DEFAULT_STAGES`, `STAGE_NAMES`, `Pipeline` from
`vibey_gh.feasibility`, with `FeasibilityEvaluator` and `StateVector`). Unless stated, every
endpoint is declared for the stage `develop`, the path is `Pipeline().path("develop", "develop")`,
`offline=False`, `connector = ScriptedEndpointConnector({...})` and
`NetworkProbe(endpoints, connector=connector, samples=3, timeout_s=2.0)`:
- `test_the_probe_declares_its_seams` — instance of `NetworkProbeInterface` and `MaterialProbeInterface`.
- `test_no_declared_endpoints_leaves_the_network_unknown_and_says_so` —
  `NetworkProbe(connector=connector).measure(DEFAULT_STAGES[:4], offline=False, at=5.0)`: three
  coordinates named `network.availability`, `network.stability`, `network.reliability`, all
  `value is None`, each `source` starting
  `"no endpoints declared for install, interview, feature-branch, develop: "`; `connector.calls == []`.
- `test_offline_never_reaches_a_remote_endpoint` — `(("develop", ("https://git.example",)),)`,
  `offline=True`: all `None`, source contains
  `"1 of 1 declared endpoint(s) are not on this machine and the estimate is offline"`;
  `connector.calls == []`.
- `test_a_local_endpoint_is_probed_even_offline` — `"tcp://127.0.0.1:11434"` scripted
  `[0.010, 0.012, 0.011]`, `offline=True`: availability `1.0`; `len(connector.calls) == 3`, each
  with `timeout_s == 2.0`.
- `test_each_endpoint_on_the_path_is_sampled_once_per_sample` — develop and main both declare
  `"tcp://127.0.0.1:1"`, main also `"tcp://127.0.0.1:2"`; over `Pipeline().path("main", "develop")`
  with `offline=False` the calls are three for each of the two endpoints (six in all).
- `test_availability_loss_and_steadiness_come_from_the_samples` — `"tcp://127.0.0.1:1"` scripted
  `[0.1, 0.1, 0.1]`, `"tcp://127.0.0.1:2"` scripted `[0.1, 0.3, None]` (the fake repeats the last,
  so give it exactly three): availability `1.0`, reliability `0.8333` with source
  `"5 of 6 attempt(s) answered, loss 17%"`, stability `0.5` (cv `0.5` at `tcp://127.0.0.1:2`, which
  the source names).
- `test_an_endpoint_that_never_answers_is_a_measured_shortfall` — `"tcp://127.0.0.1:1"` unscripted
  (lost), `"tcp://127.0.0.1:2"` `[0.1]`: availability `0.5`, reliability `0.5`, stability `1.0`; and
  `FeasibilityEvaluator().evaluate(StateVector.unknown().with_measurements(coords), Pipeline().path("develop", "develop"))`
  has a shortfall named `network.availability`.
- `test_nothing_answering_leaves_stability_unknown` — every endpoint lost: availability `0.0`,
  reliability `0.0`, stability `None` with `"no endpoint answered"` in its source.
- `test_one_sample_cannot_show_variance` — `samples=1`, answers `[0.1]`: stability `None`, source
  contains `"needs two answers from each endpoint"`.
- `test_the_endpoints_are_configuration` — `.vibey-gh.toml` =
  `'[estimate]\nnetwork_samples = 5\nnetwork_timeout_s = 2.5\n[estimate.endpoints]\ndevelop = ["https://git.example", "tcp://127.0.0.1:5432"]\n'`:
  `load_config(tmp_path).estimate` has `endpoints == (("develop", ("https://git.example", "tcp://127.0.0.1:5432")),)`,
  `network_samples == 5`, `network_timeout_s == 2.5`; `EstimateConfig()` has `endpoints == ()`,
  `3`, `5.0`. Refusals: `EstimateConfig(network_samples=0)` and `(network_samples=True)` →
  `"at least 1"`; `(network_timeout_s=0.0)` → `"positive number of seconds"`;
  `(endpoints=(("develop", ()),))` → `"non-empty list"`;
  `EstimateConfig.from_table({"endpoints": {"develop": "x"}})` → `TypeError` matching
  `"estimate.endpoints must be a table"`.
- `test_from_config_refuses_a_stray_stage_or_an_unreadable_endpoint` —
  `NetworkProbe.from_config(EstimateConfig(endpoints=(("canary", ("tcp://h:1",)),)), STAGE_NAMES)`
  raises `ValueError` matching `"never reaches: \['canary'\]"`; with `(("develop", ("tcp://h",)),)`
  it raises matching `"is not tcp://host:port"`.
- `test_the_composition_now_samples_the_network` —
  `EstimateProbes().build(GhConfig(root=tmp_path), stage_names=STAGE_NAMES, journal=None)` holds a
  `NetworkProbe`; with `GhConfig(root=tmp_path, estimate=EstimateConfig(endpoints=(("canary", ("tcp://h:1",)),)))`
  `build` raises `ValueError`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_network_probe.py test/test_operation_estimate.py test/test_delivery_config.py test/test_feasibility.py test/test_port_parity.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- Declaring any endpoint in this repository's `.vibey-gh.toml`: #134 open question 3 is recorded
  here, not answered.
- `vibey_gh/cli.py` (the composition carries the probe), `vibey_gh/endpoint_connector.py`.
- A network series across estimates (this lane's series is the samples of one estimate).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
