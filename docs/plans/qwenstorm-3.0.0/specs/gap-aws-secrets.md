## Title
feat(aws): AWS credentials come from SecretsPort, and a command executor hands exactly those to the child process

## Why
Gap C1 child 5 (`issue-audit/gaps.md:185`): an AWS adapter's credentials come from `SecretsPort`
(`src/vibey/application/interfaces/secrets.py:7-17`), whose sovereign default is self-hosted
OpenBao (`src/vibey/infrastructure/secrets/openbao.py`; 8.b, `src/vibey_tools/gh/docs/doctrines.md:147-150`
at `d3b4a388`) and whose in-memory implementation is `InMemorySecrets`
(`src/vibey/infrastructure/secrets/in_memory.py:9-21`). 10.e (`doctrines.md:417`): the family's
secrets surface is used, not a second store. SD-01 §2: the credentials in play must be the ones the
consent names — never whatever ambient `AWS_PROFILE` or key happens to be in the worker's
environment. 7.c (`doctrines.md:82-91`): a credential never reaches the ledger or an error message.

This half of the AWS adapter does not depend on the IaC ruling (`gap-ops-canon-rulings` item 5):
the `aws` CLI, OpenTofu's AWS provider and the CDK all read `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` from the environment. `CommandExecutor`
(`src/vibey/infrastructure/interfaces/__init__.py:72-73`) takes only an argv, so the environment
must be the executor's own job — the same shape as `CleanGitEnvSubprocessExecutor`
(`src/vibey/infrastructure/git/clean_env.py:23-38`). The adapter that uses both classes is
`gap-aws-cli-client`, a child of `gap-spike-aws-iac`; the `[deploy.aws]` keys that override the
secret names are `gap-aws-target`'s.

## Required behaviour
1. New `src/vibey/infrastructure/aws/credentials.py` declares:
   - `class AwsCredentialsUnavailable(VibeyError)` (no interface: an exception, as
     `az_cli.py:36-44`). Its message is
     `f"AWS credentials unavailable: secret {key!r} is not in the secrets store"` — the key's
     name, never a value.
   - `class AwsCredentialSource`:
     - class constants `ACCESS_KEY_ID_SECRET: ClassVar[str] = "aws/access_key_id"`,
       `SECRET_ACCESS_KEY_SECRET: ClassVar[str] = "aws/secret_access_key"`,
       `SESSION_TOKEN_SECRET: ClassVar[str] = "aws/session_token"` (the defaults 12.c states;
       `gap-aws-target` feeds overrides);
     - `__init__(self, secrets: SecretsPort, *, access_key_id_secret: str = ACCESS_KEY_ID_SECRET, secret_access_key_secret: str = SECRET_ACCESS_KEY_SECRET, session_token_secret: str | None = SESSION_TOKEN_SECRET)`;
     - property `secret_keys -> tuple[str, ...]`: the names it reads, in order, the session-token
       name last and omitted when it is `None` (for doctor lines; names only);
     - `async def environment(self) -> dict[str, str]`: reads the access-key id and the secret
       key; a `KeyError` from `SecretsPort.get_secret` becomes `AwsCredentialsUnavailable(key)`
       raised `from None` (so the lookup's own text is dropped). Returns
       `{"AWS_ACCESS_KEY_ID": ..., "AWS_SECRET_ACCESS_KEY": ...}` plus `"AWS_SESSION_TOKEN"` when a
       session-token name is set and the secret exists; a missing session token is not an error
       (a long-lived key pair has none). Any other exception from the store propagates unchanged.
   - `class AwsCredentialedExecutor` (a `CommandExecutor`):
     - `__init__(self, credentials: AwsCredentialSourceInterface, *, environ: Mapping[str, str] | None = None)`;
       `None` means `os.environ`, read at each `execute`;
     - `async def execute(self, argv: tuple[str, ...]) -> CommandResult`: builds the child's
       environment as every variable of the base environment whose name does **not** start with
       `AWS_`, then the credential overlay from `await credentials.environment()`; runs
       `asyncio.create_subprocess_exec(*argv, stdout=PIPE, stderr=PIPE, env=env)`; on
       `asyncio.CancelledError` terminates and waits for the child and re-raises (copy
       `clean_env.py:26-37`); returns `CommandResult(process.returncode or 0, stdout.decode(), stderr.decode())`
       (`CommandResult` from `vibey.infrastructure.engines.claudeloop_process`).
       `AwsCredentialsUnavailable` propagates before any process starts.
2. New interface file `src/vibey/infrastructure/aws/interfaces/credentials_interface.py`:
   `AwsCredentialSourceInterface` (`secret_keys` property, `environment`) and
   `AwsCredentialedExecutorInterface(CommandExecutor, Protocol)`, both `@runtime_checkable`, copying
   `src/vibey/infrastructure/secrets/interfaces/openbao_interface.py:1-15`'s shape.
3. `src/vibey/infrastructure/aws/__init__.py` (a docstring naming 8.b's paid default and exporting
   the three names) and `src/vibey/infrastructure/aws/interfaces/__init__.py` (docstring
   `"""Seams the AWS adapter declares. Interfaces declare; they never consume."""` and both
   Protocols), following `src/vibey/infrastructure/secrets/interfaces/__init__.py`.
4. `.importlinter`: add `    vibey.infrastructure.aws.interfaces` to the
   `infrastructure-interfaces-declare-only` source list (`:111-129`), as its last entry before
   `forbidden_modules =` (after `vibey.infrastructure.openstack.interfaces` if lane
   `openstack-client-p2` has added it).
5. Nothing logs, records or formats a credential value anywhere.

## Where to change
- New `src/vibey/infrastructure/aws/__init__.py`, `credentials.py`,
  `interfaces/__init__.py`, `interfaces/credentials_interface.py`. Line 1 of each is the provenance
  header copied byte-for-byte from line 1 of `src/vibey/infrastructure/azure/az_cli.py`.
- `.importlinter` (one line).
- New `tests/infrastructure/aws/__init__.py` (the header line only, as
  `tests/infrastructure/deploy/__init__.py`) and `tests/infrastructure/aws/test_credentials.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/infrastructure/aws` passes with no network and no `aws` binary.
- [ ] `uv run lint-imports` reports `infrastructure-interfaces-declare-only` KEPT with the new package, and
      `uv run pytest -q -p no:cacheprovider tests/meta/test_import_contracts_bind.py` passes.
- [ ] `grep -rn "logger\|logging\|print(" src/vibey/infrastructure/aws/` prints nothing (no credential can be logged).
- [ ] `src/vibey/infrastructure/*` keeps 100% branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/aws/test_credentials.py` — no patching; the store is `InMemorySecrets`
seeded with `await store.set_secret(...)`; the executor runs this test's own interpreter
(`sys.executable`), which is not an outside service.
- `test_environment_reads_the_key_pair_and_session_token` — seeded `aws/access_key_id`,
  `aws/secret_access_key`, `aws/session_token` → exactly the three `AWS_*` entries.
- `test_a_missing_session_token_is_a_long_lived_pair` — no token seeded → two entries.
- `test_no_session_token_name_reads_none` — `session_token_secret=None` with the token seeded → two
  entries, and `secret_keys` has two names.
- `test_a_missing_key_names_the_key_never_a_value` — only the secret key seeded →
  `AwsCredentialsUnavailable` whose message is exactly
  `"AWS credentials unavailable: secret 'aws/access_key_id' is not in the secrets store"` and whose
  `__cause__` is `None`.
- `test_secret_names_are_configurable` — custom names (`"prod/aws/id"`, `"prod/aws/key"`) are the
  ones read, and `secret_keys == ("prod/aws/id", "prod/aws/key", "aws/session_token")`.
- `test_the_child_sees_only_the_declared_credentials` — `AwsCredentialedExecutor(source, environ={"AWS_PROFILE": "ambient", "AWS_ACCESS_KEY_ID": "AMBIENT", "PATH": os.environ["PATH"], "KEEP": "1"})`
  runs `(sys.executable, "-c", "import json, os; print(json.dumps({k: v for k, v in os.environ.items() if k.startswith('AWS_') or k == 'KEEP'}, sort_keys=True))")`;
  the parsed stdout equals the seeded `AWS_*` pair plus `{"KEEP": "1"}` (no `AWS_PROFILE`, no ambient key).
- `test_exit_code_and_streams_are_returned` — `(sys.executable, "-c", "import sys; print('o'); print('e', file=sys.stderr); sys.exit(3)")`
  → `CommandResult(3, "o\n", "e\n")`.
- `test_unavailable_credentials_start_no_process` — an empty store; `execute` raises
  `AwsCredentialsUnavailable`, and a marker file the argv would create
  (`(sys.executable, "-c", f"open({str(marker)!r}, 'w').close()")`) does not exist.
- `test_the_classes_satisfy_their_interfaces` — `isinstance` against both interfaces and
  `CommandExecutor`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/aws tests/meta/test_import_contracts_bind.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

One coverage run at a time.

## Out of scope
- The AWS client, its command table and IaC (`gap-spike-aws-iac` and its children), the
  `[deploy.aws]` config keys (`gap-aws-target`), doctor lines (`gap-aws-doctor`).
- Ambient-credential (profile/SSO) support: `gap-spike-aws-iac` question 6 decides it.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(aws): AWS credentials come from SecretsPort through a credentialed executor`. Do not push.

## Lane card
- **Depends on:** nothing.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/secrets`, `tests/meta/test_import_contracts_bind.py`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
