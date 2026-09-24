## Title
test(fakes): the webhook's resolver and pinned connection, and Redis's socket, become declared seams with in-memory peers

## Why
Two infrastructure adapters speak to the network below `urllib`, and their tests reach in by
patching:
- **The webhook publisher** (`src/vibey/infrastructure/notify/webhook.py`). It resolves the
  host with `socket.getaddrinfo` (`:88`), refuses private addresses (SSRF), then connects to
  the pinned IP through a dynamic `http.client` subclass (`_pinned_connection_class`, `:26-58`).
  `tests/infrastructure/notify/test_publishers.py` patches
  `vibey.infrastructure.notify.webhook.socket.getaddrinfo`,
  `vibey.infrastructure.notify.webhook._pinned_connection_class`,
  `socket.create_connection` and `WebhookPublisher._sync_post`: 12 `monkeypatch.setattr` calls
  (`:32-279`).
- **The Redis cache** (`src/vibey/infrastructure/cache/redis.py`) opens
  `socket.create_connection((host, port), timeout=...)` (`:66`) and speaks RESP.
  `tests/infrastructure/test_sovereign_surfaces.py:924-1030` runs `_FakeRedisServer`, a
  `socketserver` on a loopback port. It is in-process, but it binds a real TCP port.

## Required behaviour
1. **Webhook seams.** In `webhook.py`, `WebhookPublisher.__init__` gains two keyword arguments:
   - `resolver: AddressResolverInterface = SYSTEM_RESOLVER`. The resolver's
     `getaddrinfo(host, port, *, type) -> list[tuple]` has the stdlib's signature and shape.
     `SYSTEM_RESOLVER` is a stateless class instance that calls `socket.getaddrinfo`;
   - `connections: PinnedConnectionFactoryInterface = PINNED_CONNECTIONS`. Its
     `connection(scheme: str, host: str, port: int, ip: str, timeout: float) -> http.client.HTTPConnection`
     wraps today's `_pinned_connection_class`.
   - `_resolve_safe_target` becomes a method that uses `self._resolver`. `_sync_post` uses
     `self._connections`.
   - Both interfaces live in `src/vibey/infrastructure/notify/interfaces/webhook_interface.py`
     (ADR-0016), and both go in `DRIVER_SEAMS`.
   - The SSRF rules and the returned booleans do not change.
2. **Redis seam.** `RedisCacheAdapter.__init__(self, *, url, timeout=5, connect: SocketConnectorInterface = TCP_CONNECTOR)`,
   where `connect(host, port, timeout) -> socket.socket`. `TCP_CONNECTOR` calls
   `socket.create_connection`. The interface lives in
   `src/vibey/infrastructure/cache/interfaces/redis_interface.py` (extend the existing file),
   and goes in `DRIVER_SEAMS`.
3. **`tests/fakes/sockets.py`**:
   - `StaticResolver(answers: Mapping[str, list[str]] | None = None, *, fail: BaseException | None = None)`.
     It returns `getaddrinfo`-shaped tuples, or raises `fail`, and records its queries. An
     unknown host raises `socket.gaierror`.
   - `InMemoryHttpConnection` is an `http.client.HTTPConnection`-shaped peer. `request(...)`
     records the method, path, body and headers, and `getresponse()` returns an object with
     `status` and `read()`. `InMemoryPinnedConnections(status=200, fail: BaseException | None = None)`
     builds them, and records every `(scheme, host, port, ip)` so tests can assert the pin.
   - `InMemoryRedis` is a RESP peer served over `socket.socketpair()`: no port and no loopback.
     `connector()` returns a `SocketConnectorInterface` that hands the adapter one end, while
     a thread serves the other. It supports what `_FakeRedisServer` supports today:
     `AUTH` (`password=`), `SELECT`, `GET`, `SET` with `EX`, `DEL`, and `garbage_once`. Move
     the protocol logic from `_FakeRedisServer`; do not reinvent it.
4. **Switch the tests:**
   - `test_publishers.py` passes `resolver=` and `connections=`, with no `monkeypatch.setattr`
     left. The test that spies on `socket.create_connection` to prove the pin becomes an
     assertion on `InMemoryPinnedConnections.pins`;
   - the Redis tests in `test_sovereign_surfaces.py` use `InMemoryRedis().connector()`, and
     `_FakeRedisServer` is deleted.
   Lower the baseline for both files.

## Where to change
- `src/vibey/infrastructure/notify/webhook.py`, a new `src/vibey/infrastructure/notify/interfaces/`
  directory (with `__init__.py`), `src/vibey/infrastructure/cache/redis.py` and its interface file,
  and `.importlinter` (one line).
- New `tests/fakes/sockets.py`, `tests/fakes/test_fake_sockets.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/infrastructure/notify/test_publishers.py`, `tests/infrastructure/test_sovereign_surfaces.py` (the Redis tests only).

## Acceptance criteria
- [ ] `grep -c "monkeypatch.setattr" tests/infrastructure/notify/test_publishers.py` prints `0`.
- [ ] `grep -n "_FakeRedisServer\|socketserver" tests/infrastructure/test_sovereign_surfaces.py` prints nothing.
- [ ] The SSRF tests still refuse private, loopback and link-local answers.
- [ ] 100% `infrastructure/` coverage. `.importlinter`'s interfaces contract passes.

## Tests to write first (TDD)
`tests/fakes/test_fake_sockets.py`:
- `test_static_resolver_answers_records_and_fails_on_cue`
- `test_pinned_connections_record_the_pin_and_the_request`
- `test_in_memory_redis_serves_get_set_del_over_a_socketpair`
- `test_in_memory_redis_auth_and_select`
- `test_system_resolver_and_tcp_connector_satisfy_their_seams` (`isinstance` only; no network)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure/notify tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The desktop notifier's subprocess (`fakes-process-executor`).
- The urllib adapters (`fakes-http-transport`, `fakes-sovereign-http`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-http-transport`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/notify/test_notifications.py` and the protected tests.
- **Shares a file with:** `.importlinter`. Append the line `vibey.infrastructure.notify.interfaces`
  at the end of `infrastructure-interfaces-declare-only`'s `source_modules` (`.importlinter:108-136`),
  the same way T05 appends its own line.
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

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
