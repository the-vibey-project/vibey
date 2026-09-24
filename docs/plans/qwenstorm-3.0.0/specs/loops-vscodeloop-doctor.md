## Title
feat(vscodeloop): refuse a non-local provider and a non-OSS editor before any request leaves the machine

ADR-0046 lane L20i (slug `loops-vscodeloop-doctor`).

## Why
ADR-0046 §8 (`specs/ADR-two-loops.md:276`): for `vscode`, "its doctor refuses a provider host
that is not loopback, private or cluster-local. It also refuses an editor build that is not
Code - OSS, judged by the editor's `product.json` (verification owed)." *Security impact*
(`:392`): "A paid provider in a sovereign run is refused before any request leaves the machine."
Sub-doctrine 8.b: an adapter is sovereign only when both its model and its tool are free and run
on the operator's own hardware; the operator ruled that Microsoft's VS Code is `vscode-paid`
only (STORM-CONTEXT.md). V-VS5 (recorded by lane `loops-vscode-spike`) names the `product.json`
fields that tell the builds apart.

Today `vscodeloop doctor` (lane `loops-vscodeloop-cli`) checks only that settings resolve and the
editor answers `--version`; `run` checks neither rule.

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
   Copy the recorded V-VS5 rule (its fields and values) and the `product.json` paths per OS into
   the commit body.
1. **`vscodeloop/infrastructure/doctor.py`** (+ `infrastructure/interfaces/doctor_interface.py`):
   - `class ProviderHostPolicy`: `refusal(self, url: str) -> str | None` returns None when the
     URL's host is allowed, else `"provider host <host> is not loopback, private or cluster-local (ADR-0046 §8)"`.
     Allowed: an IP literal (v4 or v6, brackets stripped) with `is_loopback` or `is_private`;
     the name `localhost`; a single-label name (no dot — a Kubernetes Service in the same
     namespace, e.g. the chart's Ollama Service); a name ending in `.svc`, `.svc.cluster.local`
     or `.cluster.local`. Everything else is refused; names are never resolved through DNS (a
     resolution could be answered by anyone). A URL that is not `http`/`https`, or has no host,
     is refused with `"provider URL <url> is not an http(s) URL"`.
   - `class ProductJsonLocator(*, platform: str = sys.platform)`: `locate(self, editor_path: Path) -> Path | None`
     returns the recorded `product.json` for the resolved editor binary (macOS: walk up from the
     real path to the `*.app` bundle, then `Contents/Resources/app/product.json`; Linux: the
     recorded path for Arch's Code - OSS, e.g. `/usr/lib/code/product.json`, then
     `<realpath parent>/../resources/app/product.json`), or None.
   - `class OssBuildCheck`: `refusal(self, product: Mapping[str, object]) -> str | None` applies
     the recorded V-VS5 rule exactly; a Microsoft build → `"<editor> is Microsoft's VS Code build; the sovereign vscode adapter needs Code - OSS (VSCodium). Microsoft's build is vscode-paid (ADR-0046 §8)"`.
   - `class VscodeloopDoctor(*, host_policy, locator, oss_check, which, run_version, read_json)`:
     `check(self, *, paid: bool, environ: Mapping[str, str]) -> tuple[bool, tuple[str, ...]]`
     producing, in order, lines `settings: ok` / the DriverMisconfigured text; `editor: <path> <version>`;
     sovereign only: `build: Code - OSS (<nameShort>)` or the OSS refusal, and
     `provider: <base_url> (local)` or the host refusal; paid: `provider: <provider> model <model> (paid, declared)`.
     `ok` is True only when every line passed.
2. **`run` and `resume`** (`vscodeloop/cli/app.py`): in sovereign mode, after settings resolve
   and before the driver starts, a host refusal or an OSS refusal becomes
   `DriverMisconfigured(<refusal>)` through the CLI's existing `RaisingDriver` path (lane
   `loops-vscodeloop-cli`), so the run is recorded and exits 78 with no request sent.
3. **`doctor [--paid]`** prints `VscodeloopDoctor.check` lines and exits 0 when ok, 78 when a
   refusal is a misconfiguration (settings, host, build), 1 otherwise (editor not answering).
   `CliSeams` gains `doctor: Callable[[], VscodeloopDoctorInterface]` with the real default.

## Where to change
- New: `vscodeloop/infrastructure/doctor.py`, `infrastructure/interfaces/doctor_interface.py`,
  `tests/test_doctor.py` (+ `tests/data/product-oss.json` and `product-microsoft.json`, copied
  from the spike's `evidence/vscode/product-<os>-oss.json` / `-microsoft.json`).
- Edit: `vscodeloop/cli/app.py` (run/resume/doctor), `vscodeloop/cli/seams.py` (+ its interface).

## Acceptance criteria
- [ ] `127.0.0.1`, `[::1]`, `10.0.0.5`, `192.168.1.2`, `localhost`, `vibey-ollama`, `ollama.vibey.svc`, `ollama.vibey.svc.cluster.local` are allowed; `api.openai.com`, `8.8.8.8`, `ollama.example.com`, `file:///x` are refused with the messages above.
- [ ] The recorded OSS `product.json` passes and the Microsoft one is refused with the message naming `vscode-paid`.
- [ ] A sovereign `run` with `VSCODELOOP_BASE_URL=https://api.openai.com/v1` exits 78, `meta.json` is `failed`, and the fake driver's `starts` is empty (no request left the machine).
- [ ] `run --paid` does not apply the host rule (a declared paid provider).
- [ ] `doctor` exit codes: 0 all ok; 78 host/build/settings refusal; 1 editor not answering.
- [ ] Tenant suite at 100% branch coverage; mypy strict, lint-imports, bandit pass.

## Tests to write first (TDD)
`src/vibey_runners/vscode/tests/test_doctor.py`:
- `test_host_policy_allows_loopback_private_and_cluster_local` (parametrized)
- `test_host_policy_refuses_everything_else` (parametrized, incl. non-http URLs)
- `test_host_policy_never_resolves_names` (a `socket` lookup would be observable: the policy
  object has no resolver dependency; assert on a name that resolves publicly, e.g. `example.com`, being refused)
- `test_locator_finds_the_bundle_product_json_on_macos` (a fake `.app` tree in `tmp_path`, `platform="darwin"`)
- `test_locator_finds_the_linux_product_json` (`platform="linux"`)
- `test_oss_build_passes_and_microsoft_build_is_refused`
- `test_sovereign_run_with_a_remote_provider_is_refused_before_any_request`
- `test_paid_run_skips_the_host_rule`
- `test_doctor_lines_and_exit_codes` (parametrized)
- `test_doctor_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q -m "not integration"
    cd src/vibey_runners/vscode && mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- vibey's side (`loops-vscode-vibey-wiring`), and `vibey doctor`'s engine lines (it runs
  `vscodeloop doctor` through the adapter's preflight, unchanged).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscodeloop-oss-driver`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
