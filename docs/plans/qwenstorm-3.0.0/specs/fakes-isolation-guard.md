## Title
test(harness): a default-tier test that reaches an outside service fails at the attempt, naming it

## Why
"No outside thing is ever needed in order to run tests" must be enforced, not remembered.
CLAUDE.md enforces its non-negotiables with tests: domain purity is enforced by an AST walk
(`tests/domain/test_domain_purity.py`) and the onion by `import-linter`.

After `fakes-harness-decouple`, a test that is not marked `integration` can still quietly
open a socket to PostgreSQL, a broker or a model server, or spawn `docker`, `ollama` or an
engine CLI. It passes on the operator's laptop, where those run, and fails in a clean clone.

Python's audit hooks (`sys.addaudithook`, PEP 578) see every `socket.connect` and every
`subprocess.Popen` without patching any module. The guard uses them to make the attempt
itself fail, with a message that names the test, the target and the remedy.

## Required behaviour
1. **`tests/isolation.py`** (new) holds `class OutsideServiceGuard`.
   - `__init__(self, *, forbidden_executables: frozenset[str], forbidden_unix_socket_names: tuple[str, ...])`.
   - `install(self) -> None` calls `sys.addaudithook(self._hook)` once. A second call does
     nothing.
   - `armed(self, nodeid: str) -> contextlib.AbstractContextManager[None]` sets
     `self._armed_for = nodeid` for the duration of the `with` block. It resets it to `None`
     on exit, even when the test fails.
   - `_hook(self, event: str, args: tuple[object, ...]) -> None` returns at once unless
     `self._armed_for` is set and `event` is `"socket.connect"` or `"subprocess.Popen"`. It
     must stay cheap, because it runs for every audited event.
     - **`socket.connect`** (args: `sock, address`). With an `AF_INET` or `AF_INET6`
       address, raise `OutsideServiceBlocked` unless the host is loopback
       (`ipaddress.ip_address(host).is_loopback`). Loopback stays allowed, because
       in-process fake servers are in memory. With an `AF_UNIX` path, raise when its base
       name starts with one of `forbidden_unix_socket_names` (default `(".s.PGSQL.",)`).
     - **`subprocess.Popen`** (args: `executable, args, cwd, env`). Raise when
       `Path(str(executable or args[0])).name` is in `forbidden_executables`.
   - `class OutsideServiceBlocked(RuntimeError)`. Its message is:
     `f"{nodeid} reached {target} in the default tier: use the fake from tests/fakes (see tests/fakes/registry.py), or mark the test integration"`.
2. **The configuration is a key, not a constant (12.c).** It lives in `pyproject.toml`
   `[tool.vibey.test_isolation]`:
   - `forbidden_executables`: `["docker", "podman", "psql", "pg_ctl", "pg_ctlcluster", "initdb", "postgres", "ollama", "llama-server", "vllm", "claude", "codex", "cursor-agent", "gemini", "agy", "az", "kubectl", "helm", "minikube", "rabbitmqctl", "redis-server"]`;
   - `forbidden_unix_socket_names`: `[".s.PGSQL."]`.
   `tests/isolation.py` reads it with `tomllib` from the repository root
   (`Path(__file__).resolve().parents[1] / "pyproject.toml"`).
   The in-tree loop binaries (`claudeloop`, `codexloop`, `qwenloop` and so on) are not
   listed. They are this repository's own code, and the faked-mode `live` tests run them.
3. **`tests/conftest.py`**:
   - `pytest_configure` builds the guard from the configuration and calls `install()`.
   - An autouse fixture `_outside_service_guard(request)` does `with GUARD.armed(request.node.nodeid): yield`
     when `request.node.get_closest_marker("integration") is None` and
     `request.node.get_closest_marker("paid") is None`. Otherwise it yields unarmed.
4. **Every default-tier test that fails under the guard is dealt with.** Run
   `uv run pytest -q -p no:cacheprovider -m "not integration and not paid"`. For each
   `OutsideServiceBlocked`:
   - if the test genuinely needs the service, mark it `integration`;
   - otherwise stop and name it in the commit body, with the lane that owns its fake (see
     `PENDING` in `tests/fakes/registry.py`).
   Do not weaken the guard to make a test pass.

## Where to change
- New `tests/isolation.py` and `tests/test_isolation.py`.
- `tests/conftest.py`: one line in `pytest_configure`, and the fixture.
- `pyproject.toml`: the new `[tool.vibey.test_isolation]` table, placed after
  `[tool.pytest.ini_options]`.

## Acceptance criteria
- [ ] A default-tier test that connects to `10.255.255.1:5432` fails with `OutsideServiceBlocked` naming itself.
- [ ] The same test marked `integration` is not blocked. It fails or skips on its own terms.
- [ ] A test that spawns `sys.executable -c "print(1)"` passes. One that spawns `docker --version` is blocked.
- [ ] A loopback connection to a socket the test itself opened with `socket.create_server(("127.0.0.1", 0))` passes.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid"` passes with PostgreSQL stopped.

## Tests to write first (TDD)
`tests/test_isolation.py`. Each test builds its own `OutsideServiceGuard`; none of them
arms the session's guard:
- `test_a_non_loopback_connect_is_blocked_while_armed`
- `test_nothing_is_blocked_while_disarmed`
- `test_loopback_is_allowed`
- `test_a_postgres_unix_socket_is_blocked` (it connects an `AF_UNIX` socket to
  `tmp_path / ".s.PGSQL.5432"` and expects `OutsideServiceBlocked` before `FileNotFoundError`)
- `test_a_forbidden_executable_is_blocked_and_the_interpreter_is_not`
- `test_the_message_names_the_test_and_the_remedy`
- `test_the_configuration_is_read_from_pyproject`
- `test_disarm_happens_even_when_the_body_raises`

Because an audit hook cannot be removed, each test installs a fresh guard and leaves it
disarmed on exit.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_isolation.py tests/meta
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=

## Out of scope
- Tenant suites. Each tenant lane decides whether to copy the guard.
- Blocking loopback (in-process fakes use it; `fakes-sockets` moves the Redis fake to
  `socket.socketpair`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-harness-decouple`.
- **Files touched:** `tests/isolation.py` (new), `tests/test_isolation.py` (new),
  `tests/conftest.py`, `pyproject.toml`.
- **Shares a file with:** `pyproject.toml` (R03, T07 and T28 edit other tables);
  `tests/conftest.py` (after `fakes-harness-decouple`).
- **Must keep passing unchanged:** the protected tests. `tests/live/**` runs the in-tree
  loop binaries, which are allowed.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).
- **The test harness:** a routed run (T07 `locked`, T17 `queue`) executes the same pytest in
  a child process, and the guard arms inside that child. Harness tests that spawn
  `sys.executable` or `git` are allowed.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
