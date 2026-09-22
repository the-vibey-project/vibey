## Title
test(fakes): the HTTP opener becomes a declared seam with an in-memory server behind it, for blob, bus, SIEM and Ollama

## Why
Every stdlib HTTP adapter already takes an `opener` keyword that defaults to
`urllib.request.urlopen`:
- `blob/garage.py:62`, `bus/rabbitmq.py:33`, `siem/wazuh.py:30`;
- `config_store/infisical.py:24`, `docs/bookstack.py:25`, `files/nextcloud.py:19`,
  `secrets/openbao.py:27`, `sms/kannel.py:30`, `tracker/plane.py:25`;
- `engines/ollama_chat.py:48`.

So the substitution point exists. But it is typed four different ways (`Any`,
`object | None`, `Callable[..., Any]`), which is no seam at all: the adapters call it with
`# type: ignore[operator]`. It is fed `MagicMock`s. `tests/infrastructure/test_sovereign_surfaces.py`
alone builds openers from `MagicMock` about 40 times (`_mock_response`, `_raising_opener`,
`:202-460`). `tests/infrastructure/engines/test_ollama_chat.py:27-60` hand-rolls
`FakeTransport` and `FakeResponse`.

A `MagicMock` opener answers any request with anything. It cannot notice a wrong method, a
missing header or a mistyped path. This lane declares the seam and gives it one honest fake:
an in-memory HTTP server with routes. The sovereign adapters follow in `fakes-sovereign-http`.

## Required behaviour
1. **`src/vibey/infrastructure/interfaces/http_interface.py`** (new; export from
   `vibey.infrastructure.interfaces`):
   - `@runtime_checkable class HttpResponseInterface(Protocol)`: `status: int`, `read(self) -> bytes`,
     `__enter__` and `__exit__`;
   - `@runtime_checkable class UrlOpener(Protocol)`:
     `def __call__(self, request: urllib.request.Request, timeout: float | None = None) -> HttpResponseInterface`.
     Its docstring says that `urllib.request.urlopen` satisfies it, that errors are
     `urllib.error.HTTPError` (a status) and `urllib.error.URLError` (no answer), and that
     this is the contract every stdlib HTTP adapter is declared over.
2. **Retype `opener: UrlOpener = urllib.request.urlopen`** in `blob/garage.py`,
   `bus/rabbitmq.py`, `siem/wazuh.py` and `engines/ollama_chat.py` (`UrllibOllamaTransport`).
   Remove each `# type: ignore[operator]` this makes unnecessary. Do not change the sovereign
   adapters here: they await `sovereign-surfaces-ports`.
3. **`tests/fakes/http.py` — `class InMemoryHttpServer`** implements `UrlOpener`:
   - `route(method: str, url: str, *, status: int = 200, body: bytes | str | Mapping = b"", headers: Mapping[str, str] | None = None) -> None`.
     A `Mapping` body is JSON-encoded. The same route may be registered several times; the
     answers are consumed in order, and the last one repeats.
   - `route_prefix(method, url_prefix, ...)` matches any URL that starts with the prefix. An
     exact route wins over a prefix route.
   - `handler(method, url, fn: Callable[[RecordedRequest], tuple[int, bytes]])` builds a
     dynamic answer, for example an in-memory S3 bucket.
   - `unreachable(url_prefix, reason="connection refused")` makes matching requests raise
     `urllib.error.URLError(reason)`.
   - `__call__(request, timeout=None)` records a frozen `RecordedRequest`:
     - `method`, which is `request.get_method()`;
     - `url`, which is `request.full_url`;
     - `headers`, as a dict with lower-cased names;
     - `body`, as bytes or `None`;
     - `timeout`.
     A status of 400 or more raises `urllib.error.HTTPError(url, status, reason, hdrs, io.BytesIO(body))`,
     with the reason from `http.HTTPStatus`. A request that matches no route raises
     `urllib.error.URLError(f"no route for {method} {url}")`. Otherwise it returns an
     `InMemoryHttpResponse` context manager with `status`, `read()` and `headers`.
   - `requests: list[RecordedRequest]`, plus `json(i) -> object`, which decodes request
     `i`'s body.
4. **Registry.** Register `UrlOpener → InMemoryHttpServer()` and add `UrlOpener` to `DRIVER_SEAMS`.
5. **Switch the non-sovereign HTTP tests:**
   - the Garage (blob), RabbitMQ-management (bus) and Wazuh (SIEM) tests in
     `tests/infrastructure/test_sovereign_surfaces.py`: every `MagicMock` opener becomes an
     `InMemoryHttpServer` with routes, and every `opener.call_args[0][0]` inspection becomes
     `server.requests[i]`. `_mock_response` and `_raising_opener` stay only for the sovereign
     tests that `fakes-sovereign-http` converts;
   - `tests/infrastructure/engines/test_ollama_chat.py`: `FakeResponse` and the opener-level
     doubles become `InMemoryHttpServer`. `FakeTransport` fakes `OllamaTransport`, a different
     seam; move it to `tests/fakes/http.py` as `ScriptedOllamaTransport`, registered for
     `OllamaTransport` if that is a declared Protocol. Check `ollama_chat.py`, and list it in
     `DRIVER_SEAMS` when it is;
   - `tests/infrastructure/test_qwenloop_design.py`'s `FakeTransport`: the same.
6. Lower the baseline for every converted file.

## Where to change
- New `src/vibey/infrastructure/interfaces/http_interface.py`; `src/vibey/infrastructure/interfaces/__init__.py`.
- `src/vibey/infrastructure/blob/garage.py`, `bus/rabbitmq.py`, `siem/wazuh.py`, `engines/ollama_chat.py` (annotations only).
- New `tests/fakes/http.py`, `tests/fakes/test_fake_http.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/infrastructure/test_sovereign_surfaces.py` (the blob, bus and SIEM tests only),
  `tests/infrastructure/engines/test_ollama_chat.py`, `tests/infrastructure/test_qwenloop_design.py`.

## Acceptance criteria
- [ ] `urllib.request.urlopen` satisfies `UrlOpener` (`isinstance`, and mypy through the defaults).
- [ ] `grep -n "MagicMock" tests/infrastructure/engines/test_ollama_chat.py` prints nothing. The blob, bus and SIEM tests use no `MagicMock`.
- [ ] A wrong path in the Garage adapter now fails its test with "no route".
- [ ] 100% `infrastructure/` coverage.

## Tests to write first (TDD)
`tests/fakes/test_fake_http.py`:
- `test_exact_route_answers_and_records_the_request`
- `test_answers_are_consumed_in_order_and_the_last_repeats`
- `test_prefix_route_and_exact_precedence`
- `test_status_4xx_raises_http_error_with_the_body`
- `test_unrouted_and_unreachable_raise_url_error`
- `test_mapping_body_is_json`
- `test_urlopen_satisfies_the_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/infrastructure
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The eight sovereign adapters (`fakes-sovereign-http`, after `sovereign-surfaces-ports`).
- Redis's socket client and the webhook publisher (`fakes-sockets`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`.
- **Files touched:** see *Where to change*.
- **Shares a file with:** `tests/infrastructure/test_sovereign_surfaces.py` (`fakes-sovereign-http`,
  `fakes-sovereign-smtp`, `fakes-sockets` and `fakes-bootstrap-seam` edit other tests in it; land in queue order).
- **Must keep passing unchanged:** the protected tests.
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
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
