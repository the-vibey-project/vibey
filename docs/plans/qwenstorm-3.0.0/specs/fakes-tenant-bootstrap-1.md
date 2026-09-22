## Title
test(vibey-bootstrap): Key Vault and App Configuration clients come from injected factories, in-memory Azure fakes stand behind them, and the default run needs no emulator

## Why
vibey-bootstrap (`src/vibey_tools/bootstrap`) uses patching and mocks more than any other package:
- `patch` about 198 times, `Mock`/`MagicMock` about 414 times, `monkeypatch.setattr` about 122 times;
- the top two files are its repositories:
  - `test/repositories/test_enhanced_config_repository.py`: 50, patching
    `azure.appconfiguration.provider` ×28 and `azure.identity` ×14;
  - `test/repositories/test_secrets_repository.py`: 44, patching `azure.keyvault.secrets` ×12.

The cause is the source. `SecretsRepository.__init__` (`vibey_bootstrap/repositories/secrets_repository.py:40-75`)
imports and constructs `SecretClient(vault_url=..., credential=DefaultAzureCredential())`
inline. `EnhancedConfigRepository` (`enhanced_config_repository.py:60-111`) does the same with
`azure.appconfiguration.provider.load`.

**The default run is not service-free.** The `integration` marker ("Local I/O integration
tests (SQLite, mongomock, Azurite)", `pyproject.toml:266`) is deselected only by the CI
command (`-m "not integration"`), not by `addopts` (`:268-`). A plain `pytest` in the package
runs the Azurite tests, which probe `127.0.0.1:10000` and skip if nothing answers
(`test/integration/conftest.py:20-45`). Under the operator's standard, the opt-in tier must
be opt-in by default.

## Required behaviour
1. **Client factories as declared seams.** Put them in
   `vibey_bootstrap/repositories/interfaces/` (extend the existing package):
   - `SecretClientFactoryInterface`: `(vault_url: str) -> SecretClientInterface`, where the
     client interface has `get_secret(name)` and `set_secret(name, value)`, and whatever else
     the repository calls;
   - `ConfigProviderFactoryInterface`: `(endpoint: str | None, connection_string: str | None, **opts) -> ConfigProviderInterface`,
     where the provider interface is the `Mapping`-like surface the repository reads, plus `refresh()`.
   The production defaults are classes that do the current lazy imports. An `ImportError`
   behaves exactly as today (env-only mode).
2. **`SecretsRepository(vault_url=None, *, client_factory=AZURE_SECRET_CLIENTS)`** and
   **`EnhancedConfigRepository(..., provider_factory=AZURE_CONFIG_PROVIDERS)`** use them. The
   logs, the caching and the fallbacks do not change.
3. **`test/fakes/azure.py`** (new package `test/fakes/`):
   - `InMemoryKeyVault` is a secret client factory plus client. It holds a dict of secrets,
     versions each `set_secret`, and raises `azure.core.exceptions.ResourceNotFoundError` for a
     missing secret. Import it lazily, and fall back to a local exception class of the same
     name when `azure-core` is absent, so the fake works in a no-extras install. It can also
     raise a scripted auth failure on construction;
   - `InMemoryAppConfiguration` is a provider factory plus provider. It holds key, label and
     value entries, applies the selects and the key prefix trimming the repository requests,
     and makes `refresh()` pick up entries changed with `set(...)`.
4. **Switch the two repository test modules** onto these fakes. Every `patch("azure...` goes.
   Assert on the fakes' state, not on call counts.
5. **Opt-in by default.** Add `"-m", "not integration"` to `addopts`, which is a TOML list at
   `pyproject.toml:268`. The CI rows that already pass `-m "not integration"` keep passing.
   `test/integration/` still runs with `-m integration`.
6. **The tenant registry and ratchet.** `test/fakes/test_port_parity.py` registers the two
   fakes for the four interfaces. Add `test/test_patching_ratchet.py` and
   `test/patching_baseline.json` (today's counts minus this lane's).

## Where to change
- `vibey_bootstrap/repositories/secrets_repository.py`, `enhanced_config_repository.py`, `repositories/interfaces/`.
- New `test/fakes/{__init__,azure,test_port_parity,test_azure_fakes}.py`, `test/test_patching_ratchet.py`, `test/patching_baseline.json`.
- `test/repositories/test_secrets_repository.py`, `test/repositories/test_enhanced_config_repository.py`, `pyproject.toml` (`addopts`).

## Acceptance criteria
- [ ] `grep -c 'patch("azure' src/vibey_tools/bootstrap/test/repositories/*.py` prints `0` for both files.
- [ ] `(cd src/vibey_tools/bootstrap && pip install -e ../gh && pip install -e ".[test,all]" && pytest test/ --cov=vibey_bootstrap)` passes with no Azurite running, and deselects `integration` without a flag.
- [ ] The tenant's own floor and gates, as its CI row runs them, pass.

## Tests to write first (TDD)
`test/fakes/test_azure_fakes.py`:
- `test_key_vault_versions_secrets_and_404s_the_missing`
- `test_key_vault_can_fail_authentication_on_cue`
- `test_app_configuration_selects_by_label_and_trims_prefixes`
- `test_app_configuration_refresh_picks_up_changes`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/bootstrap && pytest test/ --cov=vibey_bootstrap --cov-report=term
    cd src/vibey_tools/bootstrap && pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- `services/application_bootstrap` (`fakes-tenant-bootstrap-2`). The transports and service
  bus (`fakes-tenant-bootstrap-3`). `vibey_bootstrap.amqp` (R04, T21).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry` (the pattern).
- **Files touched:** see *Where to change*.
- **Shares a file with:** `src/vibey_tools/bootstrap/pyproject.toml` (R03 and R04 add the AMQP
  extra; this lane changes `addopts` only).
- **Must keep passing unchanged:** `vibey_bootstrap.gh` re-export tests, the `integration` tier (opt-in), and the protected root tests.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a parameter with a production default. It never happens by patching an
    import. `monkeypatch.setenv` and `delenv` stay allowed.
  - The tenant keeps its own registry and parity test and its own patching ratchet
    (`test_patching_ratchet.py` plus `patching_baseline.json`) in its test directory. Lower
    the ratchet for every file you convert, and never raise it.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - Protected root tests are never edited. Change existing files with `edit_file`, and never
    rewrite an existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
