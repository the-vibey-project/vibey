## Title
feat(gh): the agency probe — merge rights on the integration and release branches, ruleset bypass and token scopes, read through the forge adapter behind the offline switch

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *agency*: "merge rights and token scopes
through the forge adapter (#138), ruleset bypass"; Scope 5: "Agency shortfalls come first, and an
impossible job names its coordinate immediately"; "Proposed child issues" 1). Sub-doctrines: 10
(`src/vibey_tools/gh/docs/doctrines.md:371-383`: fail loudly at the floor, naming it) and 10.d
(`doctrines.md:395-410`: clearance is re-verified at every transition, naming what is missing),
10.f (`doctrines.md:419`: what cannot be read is unknown), 12.c (`doctrines.md:455`: which stage
merges into which branch, and which scopes a run needs, are declared).

Verified gap (integration clone): `agency.availability` is required at six of the nine default
stages (`src/vibey_tools/gh/vibey_gh/feasibility.py:253-321`: install, feature-branch, develop,
develop-deployment, main, main-deployment) and is never measured, so every default estimate is
`UNKNOWN` at best — the very coordinate the evaluator reports first
(`feasibility.py:88`, `:504-506`). The forge verbs it needs exist after
`roadmap-134-agency-probe-p1` (`branch_access`) and `-p2` (`token_scopes`). Paid credit is **not**
read here: `MEASURED_BY` counts it as agency (`feasibility.py:113-116`), but it is the conductor's
engine-health record, measured by the conductor-bridge lane `roadmap-134-agent-information-probes`;
this probe's source says so, so a `1.0` here is never mistaken for "credit available".

The switch is today's, exactly (`vibey_gh/operation_estimate.py:106-117`, `:128`;
`vibey_gh/cli.py:806`): a forge on this machine (a loopback `[platform] host`) is asked even offline;
any other forge only with `--online` or `[estimate] offline = false`. #134 open question 2 ("Agency
probes need network and credentials, while `vibey-gh doctor` is deliberately offline. Is it
acceptable that `estimate` goes online only behind `--online` / `[estimate] offline = false`, as
today?") is **recorded, not answered**: this lane keeps today's gate, which is what the question
proposes; if the operator answers otherwise, only the gate changes.

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **Configuration.** `EstimateConfig` (`vibey_gh/config.py`), appended after the fields and checks
   `roadmap-134-hardware-series-p3` added:
   - fields:
     ```python
         # [estimate.merge_stages]: stage = "integration" | "release" -- the branch a stage merges
         # into ([branches]). The defaults are the shipped stages' own summaries (feasibility.py).
         merge_stages: tuple[tuple[str, str], ...] = (("develop", "integration"), ("main", "release"))
         # Scopes the calling token must hold; empty requires none.
         required_token_scopes: tuple[str, ...] = ()
     ```
   - docstring bullet: `- `merge_stages` ({develop = "integration", main = "release"}) and `required_token_scopes` (empty): what the agency probe asks the forge.`
   - `__post_init__`, appended:
     ```python
             _unique_nonempty("estimate.merge_stages", tuple(stage for stage, _ in self.merge_stages))
             for stage, role in self.merge_stages:
                 if role not in ("integration", "release"):
                     raise ValueError(
                         f"estimate.merge_stages.{stage} must be 'integration' or 'release': {role!r}"
                     )
             _unique_nonempty("estimate.required_token_scopes", self.required_token_scopes)
     ```
   - `from_table`: after the `endpoints` check,
     ```python
             merge_stages = section.get("merge_stages", {"develop": "integration", "main": "release"})
             if not isinstance(merge_stages, dict):
                 raise TypeError('estimate.merge_stages must be a table of stage = "integration" | "release"')
     ```
     and in `cls(...)`, after `hardware_minimum=...`:
     `merge_stages=tuple((str(stage), role) for stage, role in merge_stages.items()),` and
     `required_token_scopes=tuple(section.get("required_token_scopes", ())),`.
2. **New module `vibey_gh/agency_probe.py`** (provenance line 1 from `vibey_gh/fit.py:1`) with
   `class AgencyProbe(AgencyProbeInterface)`:
   - `__init__(self, cfg: GhConfig, *, forge: ForgeAdapterInterface | None = None) -> None`,
     storing both. Construction reads nothing and selects no forge.
   - `measure(self, stages: Sequence[Stage], *, offline: bool, at: float) -> tuple[Coordinate, ...]`:
     1. `needing` = the stages with a requirement `material == "agency"` and
        `prop == "availability"`. None → return `()`.
     2. `roles = dict(cfg.estimate.merge_stages)`; `merging` = names in `needing` that are keys of
        `roles`, in path order; `others` = the rest of `needing`.
     3. `host = cfg.platform.host`; `local = bool(host) and OperationEstimator.is_local(f"https://{host}")`.
        When `offline and not local`: return one coordinate `agency.availability`, `None`, source
        `f"not read: the forge ({cfg.platform.kind} at {host or 'its default host'}) is not on this machine and the estimate is offline (pass --online, or set [estimate] offline = false)"`.
     4. No `merging`: return `agency.availability` `None`, source
        `f"no merge stage on this path; {', '.join(others)} need agency vibey-gh does not read (push, deployment credentials, local write)"`.
     5. `forge = self._forge if self._forge is not None else ForgeSelector().select(cfg)`.
        `branches`: for each merging stage, `cfg.integration_branch` when its role is
        `"integration"`, else `cfg.release_branch`, each branch once, in path order.
     6. For each branch, `access, problem = forge.branch_access(branch)`: a problem → unread
        `f"{branch}: {problem}"`; `access is None` → unread `f"{branch}: the forge has no such branch"`;
        `access.can_merge is True` → held; `False` → missing; `None` → unread
        `f"{branch}: the forge did not say whether this identity may merge"`. For each `access`
        that is not `None`, a bypass note (static method `bypass_note(access) -> str`):
        `rules_apply is False` → `f"no rules govern {branch}"`; `can_bypass is True` →
        `f"ruleset bypass present on {branch}"`; `can_bypass is False` →
        `f"rules on {branch} can refuse a merge this identity cannot bypass"`; otherwise
        `f"bypass on {branch} not stated ({access.basis})"`.
     7. `scopes, scope_problem = forge.token_scopes()`; scope text: a problem →
        `f"token scopes not read: {scope_problem}"`; `None` → `"the token publishes no scope list"`;
        else `f"token scopes: {', '.join(sorted(scopes)) or 'none'}"`.
        `required = cfg.estimate.required_token_scopes`; `lacking = sorted(set(required) - scopes)`
        when `required` and `scopes is not None` and no scope problem, else `[]`;
        `scopes_unread = bool(required) and (bool(scope_problem) or scopes is None)`.
     8. Value, first match wins: `lacking` → `0.0`; `missing` → `round(len(held) / len(branches), 4)`;
        `unread` or `scopes_unread` → `None`; `others` → `None`; otherwise `1.0`.
     9. Source: these parts joined by `"; "` — when `lacking`,
        `f"the token lacks required scope(s) {', '.join(lacking)}"` first; then
        `f"merge rights held on {', '.join(held) or 'no branch'}"`; when `missing`,
        `f"absent on {', '.join(missing)}"`; each unread entry prefixed `"not read: "`; when
        `scopes_unread`, `"required scopes could not be checked"`; only when the value was set by
        the `others` rule of step 8,
        `f"{', '.join(others)} also need agency vibey-gh does not read (push, deployment credentials, local write)"`;
        each bypass note; the scope text; and last
        `"paid credit is read by the conductor's preflight, not by vibey-gh"`.
     The one coordinate returned is `Coordinate("agency", "availability", value, source, at)`.
     It never raises for an answer the forge could not give.
   - Imports: `Sequence`; `GhConfig`; `BranchAccess` from `vibey_gh.forge`; `Coordinate`, `Stage`
     from `vibey_gh.feasibility`; `ForgeSelector` from `vibey_gh.forge_selector`;
     `ForgeAdapterInterface`; `OperationEstimator` (for `is_local`, reused, 10.e); the interface.
3. **New interface `vibey_gh/interfaces/agency_probe_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`): `AgencyProbeInterface(MaterialProbeInterface, Protocol)`,
   `runtime_checkable`, docstring "The agency material as the forge states it: merge rights on the
   integration and release branches, ruleset bypass, and the token's scopes." Add it to `EXEMPT`
   in `test/test_port_parity.py` with the reason
   `"class contract: AgencyProbe; the seam it implements, MaterialProbeInterface, has ScriptedMaterialProbe"`.
4. **The composition.** `EstimateProbes.build` (`vibey_gh/estimate_probes.py`) appends
   `AgencyProbe(cfg)` last (after the hardware series).

## Where to change
- New: `vibey_gh/agency_probe.py`, `vibey_gh/interfaces/agency_probe_interface.py`,
  `test/test_agency_probe.py`.
- Edit with `edit_file`: `vibey_gh/config.py` (behaviour 1), `vibey_gh/estimate_probes.py`
  (behaviour 4); one `EXEMPT` entry in `test/test_port_parity.py`.
- Patterns to copy: `OperationEstimator`'s offline rule (`operation_estimate.py:128`, `:165-170`);
  a public function taking an injected forge with a production default (`specs/forge-adapter.md` C6).

## Acceptance criteria
- [ ] Offline, a remote forge is never asked (`RecordingForge.calls == []`) and the coordinate says
      how to go online.
- [ ] Merge rights absent on the release branch make `agency.availability` a measured shortfall, and
      the evaluator then blocks the path at the first stage needing agency, agency reported first.
- [ ] A token lacking a declared scope reads `0.0` naming the scope; anything unread is unknown.
- [ ] Bypass is reported in the source and never changes the number; paid credit is named as not read.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_agency_probe.py` (provenance line 1 from `test/test_fit.py:1`;
`from forge_doubles import RecordingForge`; `BranchAccess` from `vibey_gh.forge`;
`FeasibilityEvaluator`, `Pipeline`, `StateVector`, `STAGE_NAMES` from `vibey_gh.feasibility`).
Helpers: `def access(branch, merge=True, rules=True, bypass=None) -> BranchAccess` returning
`BranchAccess(branch, merge, rules, bypass, "stated by the test")`, and
`def forge(**by_branch) -> RecordingForge` returning
`RecordingForge(branch_access=lambda branch: (by_branch.get(branch), ""), token_scopes=(frozenset({"repo", "workflow"}), ""))`.
`cfg = GhConfig(root=tmp_path)` unless stated (forgejo, no host, `develop`/`main`):
- `test_the_probe_declares_its_seams` — instance of `AgencyProbeInterface` and `MaterialProbeInterface`.
- `test_a_path_that_needs_no_agency_says_nothing` — `Pipeline().path("interview", "interview")` → `()`.
- `test_offline_never_asks_a_remote_forge` — `AgencyProbe(cfg, forge=f).measure(Pipeline().path("main", "main"), offline=True, at=1.0)`:
  value `None`, source `"not read: the forge (forgejo at its default host) is not on this machine and the estimate is offline (pass --online, or set [estimate] offline = false)"`;
  `f.calls == []`.
- `test_a_forge_on_this_machine_is_asked_even_offline` — `cfg` with
  `platform=PlatformConfig(kind="forgejo", host="localhost:3000")`: `offline=True` asks the forge
  (`("branch_access", "main")` is in `f.calls`).
- `test_merge_rights_on_every_merge_branch_make_agency_available` — `offline=False`, path
  `Pipeline().path("main", "main")`, `forge(main=access("main", bypass=True))`: value `1.0`;
  source contains `"merge rights held on main"`, `"ruleset bypass present on main"`,
  `"token scopes: repo, workflow"` and ends with
  `"paid credit is read by the conductor's preflight, not by vibey-gh"`.
- `test_a_missing_merge_right_blocks_the_path_and_is_reported_first` — path
  `Pipeline().path("main", "develop")`, `forge(develop=access("develop"), main=access("main", merge=False, bypass=False))`,
  `offline=False`: the one coordinate has value `0.5` and a source containing
  `"absent on main"` and `"rules on main can refuse a merge this identity cannot bypass"`; then
  `FeasibilityEvaluator().evaluate(StateVector.unknown().with_measurements(coords), Pipeline().path("main", "develop"))`
  has verdict `"no"`, `blocked_at == "develop"` and `shortfalls[0].name == "agency.availability"`.
- `test_other_agency_stages_leave_it_unknown_even_when_every_right_is_held` — path
  `Pipeline().path("develop-deployment", "develop")` with develop held: value `None`, source
  contains `"develop-deployment also need agency vibey-gh does not read"`.
- `test_what_the_forge_could_not_say_is_unknown` — `branch_access` answering `(None, "boom")`
  → `None` with `"not read: main: boom"`; answering `(None, "")` → `"the forge has no such branch"`;
  `access("main", merge=None)` → `"did not say whether this identity may merge"`.
- `test_a_token_lacking_a_required_scope_reads_zero` — `cfg` with
  `estimate=EstimateConfig(required_token_scopes=("repo", "admin:org"))`, every right held:
  value `0.0`, source starts with `"the token lacks required scope(s) admin:org"`; with
  `token_scopes=(None, "")` → `None` and `"required scopes could not be checked"`; with
  `token_scopes=(None, "forgejo does not support token_scopes: x")` the source contains
  `"token scopes not read: forgejo does not support token_scopes: x"`.
- `test_bypass_is_reported_but_never_invented` — `AgencyProbe.bypass_note` over
  `access("b", rules=False)`, `bypass=True`, `bypass=False` and `bypass=None` gives the four texts
  of behaviour 2.6 (the last includes `"(stated by the test)"`).
- `test_an_unreachable_forge_on_this_machine_is_unknown` — no injected forge:
  `cfg = GhConfig(root=tmp_path, platform=PlatformConfig(kind="forgejo", host="127.0.0.1:9", repository="o/r"))`,
  `AgencyProbe(cfg).measure(Pipeline().path("main", "main"), offline=True, at=1.0)`: value `None`
  and the source contains `"not read: main: Forgejo transport failure"` (a loopback port nothing
  listens on; the request never leaves the machine).
- `test_the_merge_stages_and_scopes_are_configuration` — `.vibey-gh.toml` =
  `'[estimate]\nrequired_token_scopes = ["repo"]\n[estimate.merge_stages]\ndevelop = "integration"\nrelease-candidate = "release"\n'`
  loads `merge_stages == (("develop", "integration"), ("release-candidate", "release"))` and
  `required_token_scopes == ("repo",)`; `EstimateConfig().merge_stages == (("develop", "integration"), ("main", "release"))`;
  `EstimateConfig(merge_stages=(("develop", "trunk"),))` → `ValueError` matching
  `"must be 'integration' or 'release'"`; `EstimateConfig.from_table({"merge_stages": "x"})` →
  `TypeError`; `EstimateConfig(required_token_scopes=("repo", "repo"))` → `"entries must be unique"`.
- `test_the_composition_asks_the_forge_last` —
  `EstimateProbes().build(GhConfig(root=tmp_path), stage_names=STAGE_NAMES, journal=None)[-1]` is an
  `AgencyProbe`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_agency_probe.py test/test_operation_estimate.py test/test_delivery_config.py test/test_feasibility.py test/test_port_parity.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- Paid credit balance and engine health (`roadmap-134-agent-information-probes`, the conductor bridge).
- `agency.stability` (revocation risk) and `agency.reliability` (grants honoured when exercised):
  both need a series of exercised permissions, which the #134 validation harness records; they
  stay "unmeasured" here.
- Answering #134 open question 2; changing `vibey-gh doctor`'s offline promise; `vibey_gh/cli.py`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
