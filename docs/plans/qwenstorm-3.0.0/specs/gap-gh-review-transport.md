## Title
refactor(gh): vibey-gh's local review and triage ask their model through a declared transport, with the constrained-decoding schemas unchanged

## Why
Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:204`) says vibey's workers, storms and
command line put work on the loop's queue, and nothing spawns a loop directly; 10.e
(`doctrines.md:417`) holds that "in CI, and in operations". vibey-gh's sovereign review and
triage each open their own path to Ollama instead, and do it twice:
`call_ollama` (`src/vibey_tools/gh/vibey_gh/local_review.py:128-171`) and
`call_ollama_triage` (`:277-311`) each build the same `/api/chat` request and post it through
`_post` (`:114-125`). There is no seam a sovereignloop route could stand behind.

This lane only makes the seam; it changes no behaviour. The HTTP exchange moves into one
`OllamaReviewTransport` behind a declared `ReviewTransportInterface`, and a `LocalReviewer`
class asks through whichever transport it is given (9.b, `doctrines.md:349`). The request body
stays byte-for-byte what it is today, including the constrained-decoding `format` schemas
(`REVIEW_SCHEMA` at `:38`, `TRIAGE_SCHEMA` at `:224`) and `temperature: 0`. Lane
`gap-gh-review-via-sovereignloop-1` then adds the second transport. The model default
(`gpt-oss:20b`, `vibey_gh/config.py:502`) is `default-model-p3`'s and is not touched.

`fit.py:123`'s `DEFAULT_OLLAMA_URL` stays direct and out of scope: `OllamaModelSampler` reads
only `/api/ps`, `/api/tags` and `/api/show` (`fit.py:559-571`), which load no model and so
cannot contend with the resident one.

## Required behaviour
1. New `src/vibey_tools/gh/vibey_gh/interfaces/local_review_interface.py` (provenance line 1,
   copied from `vibey_gh/interfaces/context_sizer_interface.py:1`) declares:
   - `@dataclass(frozen=True) class ReviewAnswer` with `verdict: dict`, `route: str`,
     `detail: str` (the model's JSON object; which route answered; a human-readable line
     naming where, e.g. the endpoint or the loop seat).
   - `@runtime_checkable class ReviewTransportInterface(Protocol)` with
     `@property def route(self) -> str: ...` and
     `def ask(self, *, system: str, user: str, schema: dict, model: str, num_ctx: int, timeout: int) -> ReviewAnswer: ...`.
     Docstring: raises `OSError`/`TimeoutError` when the model cannot be reached,
     `json.JSONDecodeError`/`KeyError` for an unusable reply, `TypeError` when the answer is
     not a JSON object -- exactly the errors `review()` and `triage()` already catch
     (`local_review.py:205-210`, `:346-351`).
   - `@runtime_checkable class LocalReviewerInterface(Protocol)` with `review` and `triage`
     (signatures in 3).
2. In `local_review.py`, new `class OllamaReviewTransport`:
   - `ROUTE = "direct-ollama"`; `route` property returns it.
   - `__init__(self, base_url: str, *, opener: UrlOpener = urllib.request.urlopen) -> None`,
     where `UrlOpener` is the interface `fakes-tenant-gh-3` declares in
     `vibey_gh/interfaces/url_opener_interface.py`. If that lane threaded an `opener` into
     `_post`, `call_ollama` or `call_ollama_triage`, those parameters keep working by being
     passed into this constructor.
   - `ask(...)` builds exactly today's payload, key order included:
     `{"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "format": schema, "stream": False, "options": {"temperature": 0, "num_ctx": num_ctx}}`,
     posts it to `f"{base_url.rstrip('/')}/api/chat"` with the header
     `{"Content-Type": "application/json"}` through the non-HTTP refusal that `_post` holds
     today (move `_post`'s body into a method `_post`; keep its docstring and its
     `# nosec B310`), reads `json.loads(body["message"]["content"])`, raises
     `TypeError(f"expected a JSON object, got {type(verdict).__name__}")` for a non-object,
     and returns `ReviewAnswer(verdict, self.ROUTE, f"direct Ollama at {base_url.rstrip('/')}")`.
3. In `local_review.py`, new `class LocalReviewer`:
   - `__init__(self, transport: ReviewTransportInterface, *, sizer: ContextSizerInterface | None = None) -> None`
     (`None` means `CONTEXT_SIZER`, `:71`).
   - `review(self, diff: str, *, model: str, max_chars: int, timeout: int) -> ReviewAnswer`:
     `prompt = build_prompt(diff, max_chars)`; returns
     `transport.ask(system=SYSTEM_PROMPT, user=prompt, schema=REVIEW_SCHEMA, model=model, num_ctx=sizer.num_ctx(len(prompt)), timeout=timeout)`.
   - `triage(self, issue_text: str, *, model: str, max_chars: int, timeout: int) -> ReviewAnswer`:
     the same with `build_triage_prompt`, `TRIAGE_SYSTEM_PROMPT` and `TRIAGE_SCHEMA`.
4. `call_ollama(base_url, model, diff, max_chars, timeout, *, sizer=None, transport=None)` and
   `call_ollama_triage(...)` keep their names, positional parameters and return type (the
   verdict `dict`). Each gains `transport: ReviewTransportInterface | None = None` (`None`
   means `OllamaReviewTransport(base_url)`) and becomes one line:
   `return LocalReviewer(transport or OllamaReviewTransport(base_url), sizer=sizer).review(diff, model=model, max_chars=max_chars, timeout=timeout).verdict`
   (triage likewise). Each carries the written reason 9.b asks of a module function:
   "kept because `review()`, `triage()` and their tests call it by name; the work is `LocalReviewer`'s".
5. `review()` and `triage()` behave exactly as today: same output, same exit codes, same labels.

## Where to change
- `src/vibey_tools/gh/vibey_gh/local_review.py` (edit_file only; 365 lines).
- New `src/vibey_tools/gh/vibey_gh/interfaces/local_review_interface.py`.
- `src/vibey_tools/gh/test/fakes.py` (lane `fakes-tenant-gh-1`): append
  `class ScriptedReviewTransport` (implements `ReviewTransportInterface`; constructor takes a
  list of verdict dicts and a `route` string, default `"scripted"`; records every `ask` call's
  keyword arguments in `calls`; returns `ReviewAnswer(next verdict, route, "scripted")`;
  raises `OSError("no scripted verdict left")` when empty).
- `src/vibey_tools/gh/test/test_port_parity.py`: register `ScriptedReviewTransport` for
  `ReviewTransportInterface`; list `LocalReviewerInterface` in `EXEMPT` as a class contract.
- New `src/vibey_tools/gh/test/test_local_review_transport.py`.

## Acceptance criteria
- [ ] `src/vibey_tools/gh/test/test_local_review.py` passes with no edit (`git diff --stat` shows it untouched).
- [ ] The posted body for a review and for a triage equals, as parsed JSON, the body built by
      the code at `d3b4a388` for the same inputs (test below).
- [ ] `grep -c "/api/chat" src/vibey_tools/gh/vibey_gh/local_review.py` prints `1`.
- [ ] vibey-gh's suite passes at its floor; black, isort and mypy pass; the patching ratchet
      baseline is not raised.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_local_review_transport.py`:
- `test_direct_transport_posts_todays_review_body` -- through `InMemoryUrlOpener`, one POST to `http://h:1/api/chat` whose JSON is exactly `{"model": "m", "messages": [system, user], "format": REVIEW_SCHEMA, "stream": False, "options": {"temperature": 0, "num_ctx": <sizer value>}}`.
- `test_direct_transport_posts_todays_triage_body` -- the same with `TRIAGE_SCHEMA` and `TRIAGE_SYSTEM_PROMPT`.
- `test_direct_transport_refuses_a_non_http_endpoint` -- `file:///x` raises `ValueError` naming the URL; the opener saw nothing.
- `test_a_non_object_answer_is_a_type_error` -- content `"[1]"` raises `TypeError`.
- `test_the_answer_names_its_route` -- `route == "direct-ollama"`, `detail == "direct Ollama at http://h:1"`.
- `test_reviewer_asks_through_the_injected_transport` -- `LocalReviewer(ScriptedReviewTransport([{"pass": True}]))` returns that verdict; the fake saw `schema is REVIEW_SCHEMA`, `system == SYSTEM_PROMPT` and the sizer's `num_ctx`.
- `test_call_ollama_keeps_its_contract` -- `call_ollama("http://h:1", "m", "diff", 1000, 30, transport=ScriptedReviewTransport([{"pass": False}]))` returns `{"pass": False}`; `call_ollama_triage` likewise.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The sovereignloop transport (`gap-gh-review-via-sovereignloop-1`) and choosing between
  routes (`gap-gh-review-via-sovereignloop-2`).
- `fit.py` (loads no model; see Why), `review_contract.py`, the managed workflow templates.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `refactor(gh): local review and triage ask through a declared transport`. Do not push.

## Lane card
- **Depends on:** `default-model-p3` (the model default this lane leaves alone),
  `fakes-tenant-gh-3` (the lane that gives `local_review` its injected opener and converts
  `test_local_review.py`; this lane builds on its post-state).
- **Standing constraints:** vibey-gh stays dependency-free (`dependencies = []`); it never
  imports `vibey`. A fake is a plain class with real behaviour. Substitution only at a
  declared seam; `monkeypatch.setenv`/`delenv` stay allowed. Never raise the ratchet.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
