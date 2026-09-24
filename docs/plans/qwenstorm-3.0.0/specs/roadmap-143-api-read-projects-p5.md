## Title
feat(config): an `[api]` table declares where `vibey server` listens and which variable holds its token, loopback only

## Why
Issue #143 (rewrite: `issue-audit/updates/143.md`, Scope 1 "token auth, loopback-bound by default";
"Proposed child issues" 1 "Token auth, bound to 127.0.0.1"). Sub-doctrine 12.c
(`src/vibey_tools/gh/docs/doctrines.md:455`): "a hard-coded value that could have been a key is a
decision taken away from the next human adopter" — so the address, port, token variable, page size
and stream pace are keys, each with a default. The coordinator's ruling for this wave is one
operator on loopback; whether the API may serve other hosts or users is #143's open question 1
("Single operator or many users?"), so this table accepts only loopback addresses and says why,
rather than answering that question. The token itself is a secret and never sits in `vibey.toml`:
the table names the environment variable that holds it, the shape #297's rewrite proposes for
`[openclaw] token_env` (`issue-audit/updates/297.md`, "Proposed child issues" 2).
The existing tables are the pattern: frozen dataclasses (`src/vibey/domain/config.py:283-316`),
`_optional` readers (`:358-364`), one parse function per table (`:616-649`), and `parse_config`
(`:652-720`). The module is pure (`:1-7`).

## Required behaviour
1. `src/vibey/domain/config.py`:
   - `import re` with the other stdlib imports (`:9-11`).
   - After `SiemConfig` (`:308-316`), add `LOOPBACK_BINDS: Final = ("127.0.0.1", "::1")` (import
     `Final` from `typing`) and
     ```python
     @dataclass(frozen=True, slots=True)
     class ApiConfig:
         """`[api]`: `vibey server`, the conductor's HTTP API (#143).

         One operator on one machine: `bind` is a loopback address, and the token is read from
         the environment variable `token_env` names, never from this file. `page_size` bounds
         every listing; with `stream_poll_seconds` it also paces the ledger stream that the API's
         event route and `vibey watch`'s log screen read.
         """

         bind: str = "127.0.0.1"
         port: int = 8765
         token_env: str = "VIBEY_API_TOKEN"
         page_size: int = 50
         stream_poll_seconds: float = 1.0
     ```
   - `VibeyConfig` (`:319-342`) gains `api: ApiConfig = field(default_factory=ApiConfig)` after `siem`.
   - After `_parse_siem` (`:642-649`), a **public** `def parse_api(data: dict[str, Any]) -> ApiConfig:`
     (public because `vibey server` reads `[api]` from a `vibey.toml` that may have no `[project]`
     table, and `parse_config` requires one, `:367-370`):
     - `table = _optional(data, "api", "api", dict, {})`;
     - `bind = _optional(table, "bind", "api.bind", str, "127.0.0.1")`; not in `LOOPBACK_BINDS` raises
       `ConfigError("api.bind", "must be a loopback address (127.0.0.1 or ::1); serving other hosts is #143's open question 1")`;
     - `port = _optional(table, "port", "api.port", int, 8765)`; outside `1..65535` raises
       `ConfigError("api.port", "must be between 1 and 65535")`;
     - `token_env = _optional(table, "token_env", "api.token_env", str, "VIBEY_API_TOKEN")`; unless
       `re.fullmatch(r"[A-Z_][A-Z0-9_]*", token_env)` it raises
       `ConfigError("api.token_env", "must be an environment variable name like VIBEY_API_TOKEN")`;
     - `page_size = _optional(table, "page_size", "api.page_size", int, 50)`; below 1 raises
       `ConfigError("api.page_size", "must be at least 1")`;
     - `stream_poll_seconds = _optional(table, "stream_poll_seconds", "api.stream_poll_seconds", float, 1.0)`;
       `<= 0` raises `ConfigError("api.stream_poll_seconds", "must be greater than 0")`;
     - returns the `ApiConfig`.
   - `parse_config` passes `api=parse_api(data),` after `siem=_parse_siem(data),` (`:719`).
2. `src/vibey/domain/interfaces/config_interface.py`: append
   `@runtime_checkable class ApiConfigInterface(Protocol)` with one read-only `@property` per field
   (`bind: str`, `port: int`, `token_env: str`, `page_size: int`, `stream_poll_seconds: float`),
   in the file's existing style (`:9-36`).

## Where to change
- `src/vibey/domain/config.py`, `src/vibey/domain/interfaces/config_interface.py` (both with `edit_file`).
- Append tests to `tests/domain/test_config.py`.

## Acceptance criteria
- [ ] A `vibey.toml` with no `[api]` table yields `ApiConfig()`: `127.0.0.1`, `8765`, `VIBEY_API_TOKEN`, `50`, `1.0`.
- [ ] `0.0.0.0`, `localhost` and any other non-loopback `bind` are refused with the `api.bind` message.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
Append to `tests/domain/test_config.py` (import `ApiConfig`, `parse_api` and
`ApiConfigInterface`; a minimal document is `[project]\nname = "x"\n`):
- `test_the_api_table_defaults_to_one_operator_on_loopback` — the five defaults.
- `test_the_api_table_reads_every_key` — `bind = "::1"`, `port = 9001`, `token_env = "MY_VIBEY_TOKEN"`,
  `page_size = 5`, `stream_poll_seconds = 0.25` all read back.
- `test_the_api_table_refuses_what_it_cannot_serve` — parametrized `(toml_line, match)`:
  `bind = "0.0.0.0"` and `bind = "localhost"` -> `"api.bind: must be a loopback address"`;
  `port = 0` and `port = 70000` -> `"api.port: must be between 1 and 65535"`;
  `token_env = "vibey token"` -> `"api.token_env: must be an environment variable name"`;
  `page_size = 0` -> `"api.page_size: must be at least 1"`;
  `stream_poll_seconds = 0.0` -> `"api.stream_poll_seconds: must be greater than 0"`;
  `stream_poll_seconds = 2` -> `"'stream_poll_seconds' must be a float, got int"`. Each raises `ConfigError`.
- `test_parse_api_needs_no_project_table` — `parse_api({}) == ApiConfig()`;
  `parse_api({"api": {"port": 9001}}).port == 9001`.
- `test_the_api_config_satisfies_its_interface` — `isinstance(ApiConfig(), ApiConfigInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_config.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Reading the table from disk and serving (`roadmap-143-api-read-projects-p7`).
- A non-loopback `bind`, TLS, several tokens, token scopes (#143 open question 1).
- The `[openclaw]` table (#297 child 2, waits on this API and an OpenClaw-Matrix verification).
- `docs/reference/configuration.md` (the docs wave), CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the agent-surface trees. Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
