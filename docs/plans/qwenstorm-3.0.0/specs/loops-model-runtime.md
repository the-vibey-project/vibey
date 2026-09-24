## Title
feat(loop-service): the loop reads which models Ollama holds, and unloads one on a switch
ADR-0046 lane L26 (slug `loops-model-runtime`).

## Why
Draft ADR-0046 §4 (`STORM/specs/ADR-two-loops.md:193-222`) keeps one local model resident: on a laptop a 24 GB machine holds one model at a time (*Context*, lines 60–69), and "on a switch the loop … unloads the old model through the runtime: Ollama `keep_alive: 0`". The resident schedule (lane `loops-resident-schedule`) also needs to know, at start, which declared model is already loaded. The superseded R27 residency had no unload (`issue-audit/updates/374.md`: "a behaviour this lane did not have"). ADR-0046 *Verification owed* V-OLL1 asks this lane to prove `GET /api/ps` lists loaded models and `POST /api/generate {"model": M, "keep_alive": 0}` unloads M.

Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`) and ADR-0046's non-negotiable 5 say "the Ollama HTTP transport is the one `ollama_chat.py` already has, extended with `get_json`". Today `UrllibOllamaTransport` (`src/vibey/infrastructure/engines/ollama_chat.py:45-74` at integration `d3b4a388`) only POSTs, through `_send` (`:59-74`), which checks the scheme at the point of use. Decision D1 of the design sheet: a seat host starts without a runtime, so this class never raises for an unreachable Ollama; `loaded()` answers `None`.

The GET is declared on a **new sub-protocol**, `OllamaJsonTransportInterface(OllamaTransportInterface)`, rather than added to `OllamaTransportInterface` (`src/vibey/infrastructure/engines/interfaces/ollama_chat_interface.py:12-20`): the chat client needs only the POST, and every existing POST-only transport double (`tests/infrastructure/engines/test_ollama_chat.py:27-36`, `tests/infrastructure/test_qwenloop_design.py:70`, and any `ScriptedOllamaTransport` lane `fakes-http-transport` registers) keeps satisfying the chat client's seam unchanged.

## Required behaviour
1. **`ollama_chat_interface.py`** gains, after `OllamaTransportInterface`:
   ```python
   @runtime_checkable
   class OllamaJsonTransportInterface(OllamaTransportInterface, Protocol):
       """The chat transport plus a GET, which the loop's model runtime needs to ask Ollama
       which models are resident (ADR-0046 §4)."""

       async def get_json(self, url: str, *, timeout: int) -> dict[str, object]:
           """Raises ValueError for a non-HTTP(S) URL or a body that is not a JSON object."""
           ...
   ```
   `OllamaTransportInterface` itself is unchanged.
2. **`UrllibOllamaTransport`** gains `get_json`, and `_send` takes an optional payload (a `None` payload is a GET with no body and no `Content-Type`). `post_json` still calls `self._send(url, payload, timeout)` and behaves byte for byte as today:
   ```python
   async def get_json(self, url: str, *, timeout: int) -> dict[str, object]:
       # The loop's model runtime asks Ollama which models are resident (ADR-0046 §4).
       return await asyncio.to_thread(self._send, url, None, timeout)

   def _send(
       self, url: str, payload: Mapping[str, object] | None, timeout: int
   ) -> dict[str, object]:
       # (the existing comment and scheme check, unchanged)
       request = urllib.request.Request(  # nosec B310 - scheme checked above
           url,
           data=None if payload is None else json.dumps(dict(payload)).encode(),
           headers={} if payload is None else {"Content-Type": "application/json"},
       )
       # (the rest unchanged)
   ```
3. **`UrllibOllamaTransportInterface`** (`src/vibey/infrastructure/interfaces/class_contracts.py:169-170`), the ADR-0016 mirror of that class, now extends `OllamaJsonTransportInterface`, so the mirror declares the new method too.
4. **`class OllamaModelRuntime`** in `src/vibey/infrastructure/loop_service/model_runtime.py`, built as `OllamaModelRuntime(*, base_url: str, transport: OllamaJsonTransportInterface | None = None, timeout: int = 10, logger: Logger | None = None)`:
   - The endpoint is validated and normalised by the chat client's one rule, reused rather than copied (10.e): `self._base_url = OllamaChatClient(base_url=base_url).base_url` (a non-HTTP(S) URL or one without a host raises `ConfigError`; a trailing `/` is dropped). `transport` defaults to `UrllibOllamaTransport()`; `logger` to `structlog.get_logger(__name__)`.
   - Property `base_url -> str`.
   - `async loaded(self) -> tuple[str, ...] | None`:
     ```python
     try:
         body = await self._transport.get_json(f"{self._base_url}/api/ps", timeout=self._timeout)
     except (OSError, ValueError) as exc:
         self._log.warning("model_runtime_unreachable", url=self._base_url, error=str(exc))
         return None
     models = body.get("models")
     if not isinstance(models, list):
         self._log.warning("model_runtime_unreadable", url=self._base_url)
         return None
     return tuple(
         item["name"]
         for item in models
         if isinstance(item, dict) and isinstance(item.get("name"), str)
     )
     ```
     `None` means "unreachable or not Ollama"; `()` means "reachable, nothing loaded". `OSError` covers `urllib.error.URLError`, `HTTPError` and timeouts.
   - `async unload(self, model: str) -> bool`: `await self._transport.post_json(f"{self._base_url}/api/generate", {"model": model, "keep_alive": 0}, timeout=self._timeout)`; on `(OSError, ValueError)` log `warning("model_unload_failed", url=self._base_url, model=model, error=str(exc))` and return `False`; otherwise log `info("model_unloaded", url=self._base_url, model=model)` and return `True`.
5. **Interface** `src/vibey/infrastructure/loop_service/interfaces/model_runtime_interface.py`: `@runtime_checkable class ModelRuntimeInterface(Protocol)` with the property `base_url -> str`, `async loaded(self) -> tuple[str, ...] | None` and `async unload(self, model: str) -> bool`, each with a one-line docstring (the `None` meaning, and "True when the runtime accepted the unload").
6. **In-memory fakes**, appended to `tests/fakes/loops.py`:
   ```python
   class FakeModelRuntime:
       """ModelRuntimeInterface in memory: `loaded=None` is an unreachable runtime. A
       successful unload removes the model from what is loaded."""

       def __init__(
           self,
           loaded: tuple[str, ...] | None = (),
           *,
           base_url: str = "http://127.0.0.1:11434",
           unload_result: bool = True,
       ) -> None:
           self.resident = loaded
           self._base_url = base_url
           self.unload_result = unload_result
           self.unloads: list[str] = []

       @property
       def base_url(self) -> str:
           return self._base_url

       async def loaded(self) -> tuple[str, ...] | None:
           return self.resident

       async def unload(self, model: str) -> bool:
           self.unloads.append(model)
           if self.unload_result and self.resident is not None:
               self.resident = tuple(name for name in self.resident if name != model)
           return self.unload_result


   class FakeOllamaJsonTransport:
       """OllamaJsonTransportInterface in memory: answers by URL. An Exception answer is
       raised; a URL with no answer is unreachable (OSError)."""

       def __init__(self, answers: Mapping[str, dict[str, object] | Exception] | None = None) -> None:
           self.answers = dict(answers or {})
           self.calls: list[tuple[str, str, dict[str, object] | None, int]] = []

       async def post_json(
           self, url: str, payload: Mapping[str, object], *, timeout: int
       ) -> dict[str, object]:
           self.calls.append(("POST", url, dict(payload), timeout))
           return self._answer(url)

       async def get_json(self, url: str, *, timeout: int) -> dict[str, object]:
           self.calls.append(("GET", url, None, timeout))
           return self._answer(url)

       def _answer(self, url: str) -> dict[str, object]:
           answer = self.answers.get(url, OSError(f"connection refused: {url}"))
           if isinstance(answer, Exception):
               raise answer
           return answer
   ```
7. **Registry**: `ModelRuntimeInterface` and `OllamaJsonTransportInterface` are appended to `DRIVER_SEAMS`; `REGISTRY` gains `FakeRegistration(port=ModelRuntimeInterface, build=FakeModelRuntime)` and `FakeRegistration(port=OllamaJsonTransportInterface, build=FakeOllamaJsonTransport)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/engines/ollama_chat.py`.

Several small edits, because the transport is the family's one Ollama client (10.e):
- `src/vibey/infrastructure/engines/interfaces/ollama_chat_interface.py` (39 lines): insert the class of behaviour 1 between `OllamaTransportInterface` and `OllamaChatClientInterface` with `edit_file`. Do not edit `interfaces/__init__.py`.
- `src/vibey/infrastructure/engines/ollama_chat.py` (188 lines, `edit_file` only): add `get_json` right after `post_json` (`:53-57`), and change `_send` (`:59-74`) as in behaviour 2. Anchor on the text `    def _send(self, url: str, payload: Mapping[str, object], timeout: int) -> dict[str, object]:` and on the `request = urllib.request.Request(` block, not on line numbers (lane `fakes-http-transport` may have retyped the `opener` line above them). Keep every existing comment.
- `src/vibey/infrastructure/interfaces/class_contracts.py` (209 lines, `edit_file` only): replace the line `from vibey.infrastructure.engines.interfaces import OllamaTransportInterface` (`:35`) with `from vibey.infrastructure.engines.interfaces.ollama_chat_interface import OllamaJsonTransportInterface`, and the line `class UrllibOllamaTransportInterface(OllamaTransportInterface, Protocol):` (`:169`) with `class UrllibOllamaTransportInterface(OllamaJsonTransportInterface, Protocol):`. `grep -n "OllamaTransportInterface" src/vibey/infrastructure/interfaces/class_contracts.py` must then show no bare `OllamaTransportInterface` use.
- **New** `src/vibey/infrastructure/loop_service/model_runtime.py`. Imports: `structlog`, `from vibey.application.interfaces import Logger`, `from vibey.infrastructure.engines.interfaces.ollama_chat_interface import OllamaJsonTransportInterface`, `from vibey.infrastructure.engines.ollama_chat import OllamaChatClient, UrllibOllamaTransport`. `__all__ = ["OllamaModelRuntime"]`. Module docstring: ADR-0046 §4's runtime seam; never raises for an unreachable runtime (D1).
- **New** `src/vibey/infrastructure/loop_service/interfaces/model_runtime_interface.py` (behaviour 5), in the style of `src/vibey/infrastructure/process/interfaces/reaper_interface.py`.
- **`tests/fakes/loops.py`**: add `from collections.abc import Mapping` if missing, with `edit_file`; append the two classes of behaviour 6 at the end with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import FakeModelRuntime, FakeOllamaJsonTransport",
      "from vibey.infrastructure.engines.interfaces.ollama_chat_interface import OllamaJsonTransportInterface",
      "from vibey.infrastructure.loop_service.interfaces.model_runtime_interface import ModelRuntimeInterface",
  ]
  SEAMS = ["ModelRuntimeInterface", "OllamaJsonTransportInterface"]
  ENTRIES = [
      "FakeRegistration(port=ModelRuntimeInterface, build=FakeModelRuntime)",
      "FakeRegistration(port=OllamaJsonTransportInterface, build=FakeOllamaJsonTransport)",
  ]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on every file this lane touched.
- **New** `tests/infrastructure/loop_service/test_model_runtime.py`.

## Acceptance criteria
- [ ] `tests/infrastructure/engines/test_ollama_chat.py` and `tests/infrastructure/test_qwenloop_design.py` pass **unedited** (`git diff --stat HEAD~1 -- tests/infrastructure/engines/test_ollama_chat.py tests/infrastructure/test_qwenloop_design.py` prints nothing after the commit).
- [ ] `isinstance(UrllibOllamaTransport(), OllamaJsonTransportInterface)` and `isinstance(UrllibOllamaTransport(), UrllibOllamaTransportInterface)` hold.
- [ ] An unreachable runtime never raises out of `OllamaModelRuntime`.
- [ ] The integration test runs only when `VIBEY_TEST_OLLAMA_URL` is set; the default run needs no Ollama and no network.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_model_runtime.py`, with `BASE = "http://gpu-box:11434"`. Logs are read with `structlog.testing.capture_logs()`.
- `test_loaded_lists_the_resident_models`: `FakeOllamaJsonTransport({f"{BASE}/api/ps": {"models": [{"name": "gpt-oss:20b", "size": 13}, {"name": 7}, "junk"]}})`; `await OllamaModelRuntime(base_url=BASE + "/", transport=t).loaded() == ("gpt-oss:20b",)`; the one call is `("GET", f"{BASE}/api/ps", None, 10)`.
- `test_nothing_loaded_is_an_empty_tuple`: `{"models": []}` → `()`.
- `test_an_unreachable_runtime_reads_as_none`: no answer (the fake raises `OSError`) → `None` and one `model_runtime_unreachable` warning with `url == BASE`; a `ValueError("not an object")` answer → `None`.
- `test_a_body_without_a_model_list_reads_as_none`: `{"models": "x"}` → `None` and one `model_runtime_unreadable` warning.
- `test_unload_posts_keep_alive_zero`: `{f"{BASE}/api/generate": {"done": True, "done_reason": "unload"}}` → `await runtime.unload("gpt-oss:20b") is True`; the call is `("POST", f"{BASE}/api/generate", {"model": "gpt-oss:20b", "keep_alive": 0}, 10)`; one `model_unloaded` info line.
- `test_a_failed_unload_is_false_and_logged`: no answer → `False` and one `model_unload_failed` warning naming the model.
- `test_the_endpoint_is_validated_by_the_chat_clients_rule`: `OllamaModelRuntime(base_url="http://gpu:11434/").base_url == "http://gpu:11434"`; `OllamaModelRuntime(base_url="file:///etc")` raises `ConfigError`.
- `test_the_urllib_transport_gets_and_posts_json`: an opener double defined in the test (a function that records the `urllib.request.Request` it is given and returns a small context-manager response class whose `read()` returns `b'{"models": []}'`), passed as `UrllibOllamaTransport(opener=opener)`. `await t.get_json(f"{BASE}/api/ps", timeout=3) == {"models": []}`, with the recorded request's `get_method() == "GET"`, `data is None` and no `Content-type` header; `await t.post_json(f"{BASE}/api/generate", {"a": 1}, timeout=3)` records `get_method() == "POST"`, `data == b'{"a": 1}'` and `get_header("Content-type") == "application/json"`; `get_json("file:///etc/passwd", timeout=1)` raises `ValueError`; a `read()` of `b"[1]"` raises `ValueError`.
- `test_classes_and_fakes_satisfy_their_interfaces`: `isinstance` of `OllamaModelRuntime(base_url=BASE)` and `FakeModelRuntime()` against `ModelRuntimeInterface`; of `UrllibOllamaTransport()` and `FakeOllamaJsonTransport()` against `OllamaJsonTransportInterface`; of `UrllibOllamaTransport()` against `UrllibOllamaTransportInterface`. `FakeModelRuntime(("a", "b"))`: after `await unload("a")`, `await loaded() == ("b",)` and `unloads == ["a"]`; `FakeModelRuntime(None)` stays `None` after an unload.
- `test_ollama_lists_and_unloads_resident_models` (V-OLL1), decorated `@pytest.mark.integration` and `@pytest.mark.skipif(not os.environ.get("VIBEY_TEST_OLLAMA_URL"), reason="set VIBEY_TEST_OLLAMA_URL to run against a real Ollama")`: `runtime = OllamaModelRuntime(base_url=os.environ["VIBEY_TEST_OLLAMA_URL"], timeout=30)`; `models = await runtime.loaded()` is a `tuple`; when it is empty, `pytest.skip("no model is resident to unload")`; otherwise `await runtime.unload(models[0]) is True`, then poll `loaded()` every 0.5 s for at most 30 s until `models[0]` is gone, and assert it is gone.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines tests/infrastructure/test_qwenloop_design.py tests/fakes tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
# after the local commit, this must print nothing:
git diff --stat HEAD~1 -- tests/infrastructure/engines/test_ollama_chat.py tests/infrastructure/test_qwenloop_design.py
# optional, with a local Ollama (Arch Linux and macOS alike):
VIBEY_TEST_OLLAMA_URL=http://127.0.0.1:11434 uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/loop_service/test_model_runtime.py
```

## Out of scope
- Choosing or switching the resident model (lane `loops-resident-schedule`), and logging `seat_runtime_unreachable` at process start (D1; lanes `loops-service-process`, `loops-bootstrap-loop-service`).
- Converting the existing Ollama tests to fakes (lane `fakes-http-transport`).
- The DESIGN/DECOMPOSE providers' own Ollama calls (ADR-0046 §4 "Flag": a follow-up).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-result-store`
- `loops-result-store`: the `loop_service` package, its `.importlinter` entry, the loop fakes module and the registration script.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
