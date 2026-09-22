## Title
feat(engines): vscode joins sovereignloop's always-on pool; vscode-paid runs when declared

ADR-0046 lane L20j (slug `loops-vscode-vibey-wiring`).

## Why
Sub-doctrine 8.b (amended by #392): engines default to `sovereignloop`, which drives this era's
default model "and **VS Code** when its provider is local — always on, never needing
declaration"; "VS Code on a paid provider" is a declared-only paidloop adapter. ADR-0046 §8
(`specs/ADR-two-loops.md:276-277`) gives the runner the local endpoint and the model for
`vscode`, and `[engines.vscode_paid] provider` and `model` for `vscode-paid`. The runner reads
them from `VSCODELOOP_BASE_URL`, `VSCODELOOP_MODEL` and `VSCODELOOP_PROVIDER` (lane
`loops-vscodeloop-cli`). The one operator setting for a local endpoint is `VIBEY_OLLAMA_URL`
(CLAUDE.md "Engines"), turned into each engine's own names by `LocalEndpointEnvironment`
(`src/vibey/infrastructure/engines/local_engines.py:158-188` at integration `d3b4a388`;
renamed to `SOVEREIGNLOOP_*` by lane `loops-vibey-local-engine-names`).

Only now, after the spike, the runner, the driver and the doctor, can `vscode` be always on:
ADR-0046 §8 keeps it off if the verification diverges (CDD, 9.c).

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
1. **Overlay** — `LocalEndpointEnvironment.overlay_for` (`local_engines.py`):
   - `EngineId.VSCODE`: when `VIBEY_OLLAMA_URL` is set, `VSCODELOOP_BASE_URL = <client.base_url>/v1`
     and `VSCODELOOP_MODEL = client.model` (the same `OllamaChatClient.from_environment` read the
     sovereignloop branch uses), each only when that key is not already set — the rule the
     sovereignloop branch follows.
   - New constants `VSCODELOOP_BASE_URL_ENV`, `VSCODELOOP_MODEL_ENV`, `VSCODELOOP_PROVIDER_ENV`
     in `__all__`.
   - New method `model_env_for(self, engine_id: EngineId) -> str | None`: `SOVEREIGNLOOP_MODEL_ENV`
     for `SOVEREIGNLOOP`, `VSCODELOOP_MODEL_ENV` for `VSCODE`, else None. Declare it on
     `LocalEndpointEnvironmentInterface`. (The seat host forces the seat's model through this key;
     if `src/vibey/infrastructure/loop_service/seat_host.py` already exists and names
     `SOVEREIGNLOOP_MODEL_ENV` directly, replace that with `endpoint.model_env_for(engine)` in the
     same lane and keep its tests passing.)
2. **Paid overlay** — `LocalEngineSettings` gains `vscode_paid_overlay(self) -> dict[str, str]`:
   `{VSCODELOOP_PROVIDER_ENV: cfg.provider, VSCODELOOP_MODEL_ENV: cfg.model}` from the project's
   `engines.vscode_paid` table (parsed with `VscodePaidConfig.from_table`, lane
   `loops-vscode-paid-config`; a list-shaped `engines` (CR) or a missing table gives `{}`).
   `adapter(EngineId.VSCODE_PAID, endpoint, ...)` uses this overlay.
3. **Pool** — `vscode` is always on, like `sovereignloop`:
   - `src/vibey/domain/config.py`: `DEFAULT_ENGINES = ("sovereignloop", "vscode")` with the comment
     "sovereignloop's always-on adapters (8.b): its native agent and Code - OSS on a local model";
     `_parse_engines` force-appends both.
   - `LocalEngineSettings.enabled(EngineId.VSCODE)` is True whatever the config says;
     `enabled(EngineId.VSCODE_PAID)` is True only when the config declares it (the same
     declared-engine check lane `loops-claudeloop-local-paid` added for `claudeloop-local`).
     Both appear in `enabled_engines` in that order after `sovereignloop`, so `adapters()` builds them.
   - `src/vibey/infrastructure/engines/engine_pool.py` (lane `engines-pool`): the always-on part
     of the pool is `(sovereignloop, vscode)`; `vscode-paid` joins as a declared paid engine.
4. Selection is otherwise unchanged: `vscode` is LOCAL, so it is preferred with sovereignloop and
   rotates with it by SWRR; recorded conformance is still required before it is selected, so an
   operator without Code - OSS installed sees `vscode NOT INSTALLED` in `vibey doctor` and the
   engine is simply never eligible. Verify independence (ADR-0038 §3) now has two sovereign
   harnesses (ADR-0046 §9's recorded cost ends here).

## Where to change
- `src/vibey/infrastructure/engines/local_engines.py` (+ `interfaces/local_engines_interface.py`).
- `src/vibey/domain/config.py` (edit_file; two lines and a comment).
- `src/vibey/infrastructure/engines/engine_pool.py`.
- Possibly `src/vibey/infrastructure/loop_service/seat_host.py` (behaviour 1, last clause).
- New test: `tests/infrastructure/engines/test_vscode_wiring.py`.
- Existing assertions that a default pool is exactly `("sovereignloop",)` become
  `("sovereignloop", "vscode")`: update only those, and list them in the commit body.

## Acceptance criteria
- [ ] With `VIBEY_OLLAMA_URL=http://127.0.0.1:11434` and nothing else, `overlay_for(EngineId.VSCODE) == {"VSCODELOOP_BASE_URL": "http://127.0.0.1:11434/v1", "VSCODELOOP_MODEL": "gpt-oss:20b"}`.
- [ ] A preset `VSCODELOOP_MODEL` is kept.
- [ ] `parse_config({"project": {"name": "x"}}).engines.enabled == ("sovereignloop", "vscode")`.
- [ ] A project with no engines config gets a pool containing `sovereignloop` and `vscode`; one declaring `vscode-paid` with its table also gets `vscode-paid`, whose adapter overlay carries the provider and model.
- [ ] `model_env_for` answers for both sovereign adapters and None for paid ones.
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_vscode_wiring.py` (plain `environ` dicts and config mappings;
no patching):
- `test_vscode_overlay_derives_from_vibey_ollama_url`
- `test_vscode_overlay_keeps_operator_values`
- `test_vscode_paid_overlay_comes_from_the_declared_table`
- `test_vscode_is_always_on_and_vscode_paid_only_when_declared`
- `test_default_engines_are_both_sovereign_adapters`
- `test_model_env_for_each_engine`
- `test_pool_holds_vscode_by_default`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/domain/test_config.py tests/cli tests/infrastructure/loop_service tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Retiring OpenCode (`loops-retire-opencode-*`), which waits for live conformance evidence.
- The chart (a follow-up adds `vscode` to the sovereign seat hosts' image and environment).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject; add a
  `BREAKING CHANGE:` footer: "vscode (Code - OSS on the local model) is always on in sovereignloop".

**Depends on:** `loops-vscodeloop-doctor`, `loops-vscode-paid-config`, `loops-vibey-local-engine-names`, `loops-seat-host-core`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
