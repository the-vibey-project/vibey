<!-- split of #332: child 1 of 4; audit: issue-audit/updates/332.md -->

## Title
feat(gh): forge transports read an empty 2xx answer, time out, and take an injected opener; add NotSupported

## Why
Sub-doctrine 8.b makes self-hosted Forgejo the default forge, with GitHub and GitLab declared-only
(`src/vibey_tools/gh/docs/doctrines.md:138`), and every surface speaks one vibey-owned protocol,
which for the forge is `ForgeAdapterInterface` (`docs/doctrines.md:168-176`); vibey-gh's own
default is `[platform] kind = "forgejo"` (`vibey_gh/config.py:288`). The two HTTP transports
under the Forgejo and GitLab adapters have three defects the rest of the wave depends on:

1. **An empty 2xx body is reported as a failure.** `ForgejoTransport.survey` runs `json.loads` on
   the body (`vibey_gh/forgejo_transport.py:67-72`). A `204 No Content` (every DELETE, many
   PATCHes) raises `ValueError`, and `:75-76` reports `"Forgejo transport failure: <the JSON error>"`, so every
   successful delete reads as refused. `vibey_gh/gitlab_transport.py:72-81` has the same defect.
2. **There is no timeout.** `urllib.request.urlopen(req)` (`forgejo_transport.py:67`,
   `gitlab_transport.py:72`) waits forever, so one hung forge hangs the command.
3. **The only test substitutes by patching an import.** `test/test_forge_adapters.py:483-519`
   calls `monkeypatch.setattr("urllib.request.urlopen", <fake>)` seven times (lines 495, 501, 503,
   506, 508-510, 512-514, 516-518). Sub-doctrine 9.b (`docs/doctrines.md:349`): "Substitution
   happens at the declared seam, never by patching an import". The transports need a declared
   seam: an injected `opener`.

Later lanes also need a record for "this forge has no equivalent for this verb" (vibey-gh ADR
0001: every adapter verb answers `(value, problem)` and never raises). That record is
`NotSupported`, added here because it is pure data.

## Required behaviour
1. `vibey_gh/forge.py` gains, appended after `ProtectedRef` (the file's last class, lines 159-164):
   ```python
   @dataclass(frozen=True)
   class NotSupported:
       """A verb this forge has no equivalent for, and why (vibey-gh ADR 0001)."""

       kind: ForgeKind
       verb: str
       reason: str

       @property
       def problem(self) -> str:
           return f"{self.kind.value} does not support {self.verb}: {self.reason}"
   ```
   Add `"NotSupported"` to `__all__` (lines 25-37), between `"ForgeUser"` and `"ProtectedRef"`.
   Example: `NotSupported(ForgeKind.GITLAB, "subject_facts", "numbers collide").problem ==
   "gitlab does not support subject_facts: numbers collide"`. `forge.py` stays pure data: it
   imports nothing from `vibey_gh`, and `NotSupported` does not subclass its interface (none of
   the nouns in this module do).
2. `vibey_gh/interfaces/class_contracts.py` gains `NotSupportedInterface`, directly after
   `ProtectedRefInterface` (lines 167-170), written like `ForgeRepositoryInterface` (lines 41-56):
   ```python
   @runtime_checkable
   class NotSupportedInterface(Protocol):
       @property
       def kind(self) -> ForgeKindInterface: ...

       @property
       def verb(self) -> str: ...

       @property
       def reason(self) -> str: ...

       @property
       def problem(self) -> str: ...
   ```
   Export it from `vibey_gh/interfaces/__init__.py` in the same two places as
   `ProtectedRefInterface`: in the `from vibey_gh.interfaces.class_contracts import (...)` block
   between `ModelInterface,` (line 58) and `ObservationInterface,` (line 59), and in `__all__`
   between `"NavReaderInterface",` (line 188) and `"ObservationInterface",` (line 189).
3. `ForgejoTransport` and `GitLabTransport` each gain two dataclass fields after `token`:
   ```python
   timeout: float = 30.0
   opener: Callable[..., Any] = field(default=urllib.request.urlopen, repr=False, compare=False)
   ```
   `survey` calls `self.opener(req, timeout=self.timeout)` in place of `urllib.request.urlopen(req)`.
   With `compare=False`, two transports that differ only in `opener` still compare equal, so
   `test/test_platform.py:192-198` passes unmodified. With `repr=False`, `repr()` never shows it.
   Imports in both files become `from collections.abc import Callable, Sequence` and
   `from dataclasses import dataclass, field` (`json`, `urllib.error`, `urllib.request`, `Any`
   stay).
4. In both transports, a response the opener returns (every 2xx; `urlopen` raises `HTTPError` for
   the rest) whose decoded body is empty or only whitespace answers `({}, "")`. Put the decoded
   response text in a new local called `text`; do not reuse `data`, which already holds the request
   bytes. Every other path is unchanged:
   - JSON list or object → `(value, "")`;
   - other JSON → `([], "Forgejo API returned JSON that is neither a list nor an object")` (GitLab:
     `"GitLab API returned JSON that is neither a list nor an object"`);
   - `urllib.error.HTTPError` → `([], f"Forgejo API error {e.code}: {e.reason}")` (GitLab:
     `f"GitLab API error {e.code}: {e.reason}"`);
   - `OSError`, `TimeoutError`, `ValueError` → `([], f"Forgejo transport failure: {error!s}")`
     (GitLab: `f"GitLab transport failure: {error!s}"`).

   The Forgejo `try` block becomes:
   ```python
           try:
               with self.opener(req, timeout=self.timeout) as resp:
                   text = resp.read().decode("utf-8")
                   if not text.strip():
                       return {}, ""
                   value = json.loads(text)
                   if isinstance(value, (list, dict)):
                       return value, ""
                   return [], "Forgejo API returned JSON that is neither a list nor an object"
           except urllib.error.HTTPError as e:
               return [], f"Forgejo API error {e.code}: {e.reason}"
           except (OSError, TimeoutError, ValueError) as error:
               return [], f"Forgejo transport failure: {error!s}"
   ```
   and the GitLab one is the same with "GitLab".
5. `vibey_gh/interfaces/class_contracts.py`: `ForgejoTransportInterface` and
   `GitLabTransportInterface` (lines 193-201) each declare `timeout` as a read-only property, below
   their docstring:
   ```python
       @property
       def timeout(self) -> float: ...
   ```
6. No other module changes. The adapters, the selector and every consumer are untouched.

## Where to change
Every path in this spec is relative to `src/vibey_tools/gh/` (the vibey-gh tenant, package
`vibey_gh`) unless it starts with `src/` or `.github/`; the check block starts with
`cd src/vibey_tools/gh`. Every `file:line` anchor was checked against the storm integration branch
at `4317cff6`.

- `vibey_gh/forge.py`: append `NotSupported` after line 164; add `"NotSupported"` to `__all__`.
- `vibey_gh/interfaces/class_contracts.py`: `NotSupportedInterface` after line 170; the `timeout`
  property on `ForgejoTransportInterface` (lines 193-196) and `GitLabTransportInterface`
  (lines 198-201).
- `vibey_gh/interfaces/__init__.py`: export `NotSupportedInterface` (lines 58-59 and 188-189).
- `vibey_gh/forgejo_transport.py` (lines 14-15 imports, 21-30 fields, 66-76 `try`) and
  `vibey_gh/gitlab_transport.py` (lines 14-15, 21-30, 71-81): fields, `opener` call, empty body.
- Tests: `test/test_forge_foundation.py` (new) and `test/test_forge_adapters.py:1-21` (add
  `import dataclasses`) plus `:465-519` (the `urlopen` test converted, below).
- Every file you create starts with the provenance header line, copied byte for byte from
  `vibey_gh/forge.py:1`:
  `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
- Only if it exists when you start (another storm lane adds the tenant's patching ratchet,
  `test/test_patching_ratchet.py` with `test/patching_baseline.json`): in
  `test/patching_baseline.json`, lower `test/test_forge_adapters.py`'s `monkeypatch.setattr`
  count by 7, the patches this lane removes. The ratchet fails when a count differs from the
  baseline, so a removal must be written down. If the files do not exist, skip this.

## Acceptance criteria
- [ ] `python -m pytest -q` (run in `src/vibey_tools/gh`) passes with 100% line and branch
      coverage of `vibey_gh`.
- [ ] `grep -rn '"urllib.request.urlopen"' test/` finds nothing (all seven patches are gone; the
      count only goes down).
- [ ] `test/test_platform.py::test_the_default_sovereign_selection_is_the_self_hosted_forgejo`
      passes unmodified: `ForgeSelector().select(GhConfig(root=tmp))` still equals
      `ForgejoForge(root=tmp, transport=ForgejoTransport(host="forgejo.local", token=""))`.
- [ ] `test/test_forge_foundation.py::test_transports_compare_equal_whatever_their_opener` passes
      (`repr(ForgejoTransport())` does not mention `opener`).
- [ ] black, isort, mypy, ruff check and ruff format --check are clean (the check block below).

## Tests to write first (TDD)
Substitution is at the declared seam only: construct the transport with `opener=<fake>` (or
`dataclasses.replace(transport, opener=<fake>)`). Never patch `urllib.request`, never use
`mock.patch`, `MagicMock` or `monkeypatch.setattr` on a module or class attribute. A fake opener
is a plain function `def opener(request, timeout)` that returns an object with
`__enter__`/`__exit__`/`read()`, like `_HttpResponse` at `test/test_forge_adapters.py:465-476`.
Copy that class into the new file; do not import it from another test module.

New file `test/test_forge_foundation.py` (header line, then this):
```python
"""The forge-adapter foundation: `NotSupported`, and the seams of the two HTTP transports."""

from __future__ import annotations

import dataclasses
import urllib.request

import pytest

from vibey_gh.forge import ForgeKind, NotSupported
from vibey_gh.forgejo_transport import ForgejoTransport
from vibey_gh.gitlab_transport import GitLabTransport
from vibey_gh.interfaces import (
    ForgejoTransportInterface,
    GitLabTransportInterface,
    NotSupportedInterface,
)


class _HttpResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload.encode()
```
and these tests:
- `test_not_supported_names_the_forge_the_verb_and_the_reason`: builds
  `NotSupported(ForgeKind.GITLAB, "subject_facts", "numbers collide")`; asserts `.problem ==
  "gitlab does not support subject_facts: numbers collide"`; asserts
  `isinstance(record, NotSupportedInterface)`; and asserts that `record.verb = "other"` raises
  `dataclasses.FrozenInstanceError` (inside `with pytest.raises(...)`).
- `test_transports_read_an_empty_success_as_an_empty_object`: parametrised over
  `transport_type in (ForgejoTransport, GitLabTransport)` and `body in ("", "  \n")`. The opener
  returns `_HttpResponse(body)`; `transport_type(opener=opener).survey(["repos/o/r/branches/x",
  "DELETE", ""])` answers `({}, "")` (bind the answer to a local, then assert).
- `test_transports_pass_their_timeout_to_the_opener`: parametrised over the two transport types.
  The opener appends its `timeout` argument to a list and returns `_HttpResponse("[]")`.
  `transport_type(opener=opener).survey(["one"]) == ([], "")` and
  `transport_type(timeout=5.0, opener=opener).survey(["one"]) == ([], "")`; the list is then
  `[30.0, 5.0]`, and `transport_type().timeout == 30.0`.
- `test_transports_compare_equal_whatever_their_opener`: with a local opener `f`,
  `ForgejoTransport(opener=f) == ForgejoTransport()`, `GitLabTransport(opener=f) ==
  GitLabTransport()`, `"opener" not in repr(ForgejoTransport(opener=f))` and the same for GitLab,
  `ForgejoTransport().opener is urllib.request.urlopen` and the same for GitLab, and
  `isinstance(ForgejoTransport(), ForgejoTransportInterface)` and
  `isinstance(GitLabTransport(), GitLabTransportInterface)`.

Convert `test/test_forge_adapters.py:479-519` (`test_http_transports_cover_success_and_failures`).
Drop its `monkeypatch` parameter. Every `monkeypatch.setattr("urllib.request.urlopen", X)`
becomes a transport built with the opener: `dataclasses.replace(transport, opener=X)` or
`transport_type(host="forge.example", token="secret", opener=X)`. Every fake takes
`(request, timeout)`. Keep every existing assertion and its expected text. Add
`import dataclasses` above `import json` at the top of the file, and add this helper directly
after the `_HttpResponse` class (module level, like the file's other helpers):
```python
def _raising(error: Exception):
    def opener(request, timeout):
        raise error

    return opener
```
The converted test reads:
```python
@pytest.mark.parametrize(
    "transport_type, header",
    [(GitLabTransport, "PRIVATE-TOKEN"), (ForgejoTransport, "Authorization")],
)
def test_http_transports_cover_success_and_failures(transport_type, header):
    transport = transport_type(host="forge.example", token="secret")
    assert isinstance(transport, ForgeTransportInterface)
    assert transport.executable.startswith("http")
    assert transport.run([])[0] is False
    assert transport.survey([]) == ([], "No API path provided")
    seen = {}

    def success(request, timeout):
        seen.update({key.lower(): value for key, value in request.header_items()})
        return _HttpResponse(json.dumps([{"id": 1}]))

    answering = dataclasses.replace(transport, opener=success)
    assert answering.survey(["projects/1/issues"])[0] == [{"id": 1}]
    assert seen[header.lower()] in {"secret", "token secret"}
    assert answering.survey(["projects/1/issues", "POST", '{"body":"x"}'])[0] == [{"id": 1}]
    assert seen["content-type"] == "application/json"

    def answer(opener):
        return dataclasses.replace(transport, opener=opener).survey(["one"])

    ok = answer(lambda request, timeout: _HttpResponse('{"ok": true}'))
    assert ok[0] == {"ok": True}
    scalar = answer(lambda request, timeout: _HttpResponse('"scalar"'))
    assert "neither a list nor an object" in scalar[1]
    error = urllib.error.HTTPError("https://forge.example", 401, "Unauthorized", {}, None)
    assert "API error 401" in answer(_raising(error))[1]
    assert "transport failure: offline" in answer(_raising(OSError("offline")))[1]
    assert "transport failure: late" in answer(_raising(TimeoutError("late")))[1]
    assert "transport failure: bad json" in answer(_raising(ValueError("bad json")))[1]
```

## Checks the lane must run (all must pass)
```bash
cd src/vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q --no-cov test/test_forge_foundation.py test/test_forge_adapters.py test/test_platform.py
python -m pytest -q                                   # whole suite, 100% line+branch of vibey_gh
python -m black --line-length 100 --check vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
git diff --stat   # only the files named under "Where to change"
git status --short   # the one new file, test/test_forge_foundation.py, and nothing else new
```
If black or isort reports a file you touched, run `python -m black --line-length 100 <file>` and
`isort <file>` on that file only, then run the whole block again.

## Out of scope
- The adapters (`vibey_gh/forge_github.py`, `vibey_gh/forge_forgejo.py`,
  `vibey_gh/forge_gitlab.py`), `vibey_gh/forge_selector.py` and every consuming module: child
  lanes 2-4 and the later forge lanes own them.
- `test/conftest.py`, `test/test_platform.py`, and every other test file not named above.
- `test/test_sovereign_first.py:569` assigns `local_review.urllib.request.urlopen`; it belongs to
  another module and is not this lane's.
- The repository's `[platform] kind = "github"` declaration in the root `.vibey-gh.toml`
  (lines 18-19): never write or change it.
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or skill trees: the docs
  wave owns those.
- Do not push, open PRs, or change git remotes. Commit locally with a Conventional Commit message
  when done.

## Conventions this lane relies on (everything needed is here)
- **Coverage floor.** The tenant's floor is 100% line and branch coverage of all of `vibey_gh`
  (`pyproject.toml:64-71`: `--cov=vibey_gh --cov-branch --cov-fail-under=100`). A focused run of a
  few test files needs `--no-cov`, or it fails the floor; the whole-suite run must pass without it.
  Protocol classes are excluded from coverage (`pyproject.toml` `exclude_lines` has
  `class .*\bProtocol\):`), so interface bodies need no tests.
- **The declared seam (9.b).** Tests substitute only through a constructor argument or dataclass
  field that the production code declares (here: `opener`). No `monkeypatch.setattr` of an import
  or of a module or class attribute, no `mock.patch`, no `MagicMock`/`AsyncMock`.
- **The formatter trap.** The tenant is checked by both `black --line-length 100` + `isort`
  (profile black, `combine_as_imports`; CI job `tools-lint`, `.github/workflows/ci.yml:699-705`)
  and the root `ruff format --check .` (line length 100). They disagree on some wraps, so write
  lines neither wants to rewrap:
  - keep every line at or under 100 columns, and at or under 95 for anything with nested calls;
  - bind a long comparison or expected value to a local before the `assert`;
  - never use implicit string concatenation; use one literal, or an f-string built from locals;
  - write multi-line calls with one argument per line and a trailing comma;
  - never use backslash continuations.

  If the two formatters fight over a line, restructure the line. Never alternate between them.
- **Platforms (8.h).** The suite must pass on Arch Linux and macOS: no GNU-only tools in tests, and
  compare paths through `Path.resolve()` (macOS puts `tmp_path` behind a `/private` symlink).

**Depends on:** none
- This is the first lane of the forge-adapter wave. Land it before child lanes 2-4 of #332 and
  before any lane of #333.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
