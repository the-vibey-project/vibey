<!-- split of #383: child 3 of 6; audit: issue-audit/updates/383.md -->

## Title
feat(runners-common): one memory probe for the family

## Why
qwenloop must choose its default model by the machine's memory (8.d,
`src/vibey_tools/gh/docs/doctrines.md:236-269`), and the family already reads physical memory:
vibey-gh's fit calculus runs `sysctl -n hw.memsize` on macOS
(`src/vibey_tools/gh/vibey_gh/fit.py:271-275`) and parses `MemTotal` from `/proc/meminfo` on Linux
(`fit.py:388-390`, `:431-447`). Sub-doctrine 10.e (`doctrines.md:417`) forbids a second
implementation, and a runner should not import release tooling, so the physical-memory reading
moves into the dependency-free family package `src/vibey_runners/common` as one class,
`MemoryProbe`, with its interface; vibey-gh's two samplers then read their totals through it. 8.h
(`doctrines.md:326-333`) makes Arch Linux and macOS the two platforms every change is proven on,
and 9.b (`doctrines.md:349`) puts the command runner and the file reader behind declared seams, so
no test patches `subprocess`, `platform` or a module attribute.

## Required behaviour
Paths under `src/vibey_runners/common/` are the family package (import name `vibey_runners.common`,
`requires-python >=3.12`, `dependencies = []`); paths under `src/vibey_tools/gh/` are vibey-gh.

1. **The probe.** New `src/vibey_runners/common/src/vibey_runners/common/infrastructure/memory_probe.py`
   holds exactly this (provenance line first; keep the docstrings and comments):
   ```python
   """The family's one reading of how much physical memory this machine has (#383).

   vibey-gh's fit calculus and qwenloop's default-model selection both need it, so it lives
   here once (sub-doctrine 10.e). Arch Linux states it in /proc/meminfo and macOS answers
   `sysctl -n hw.memsize` (sub-doctrine 8.h). The command runner and the file reader are
   declared seams (9.b): a test hands in exact output instead of patching anything.
   """

   from __future__ import annotations

   import subprocess  # nosec B404 - one fixed argv, below
   import sys
   from collections.abc import Callable

   from vibey_runners.common.infrastructure.interfaces.memory_probe_interface import (
       MemoryProbeInterface,
   )

   #: Where Linux states its memory. A default, not a constant (12.c).
   LINUX_MEMINFO_PATH = "/proc/meminfo"
   #: How macOS states its memory, in bytes.
   DARWIN_MEMSIZE_ARGV: tuple[str, ...] = ("sysctl", "-n", "hw.memsize")
   #: How long that command may take before the machine counts as unreadable.
   DEFAULT_COMMAND_TIMEOUT_SECONDS = 20.0


   class MemoryProbe(MemoryProbeInterface):
       """Reads this machine's physical memory, or says it could not (None, never a guess)."""

       def __init__(
           self,
           *,
           platform_name: str = "",
           runner: Callable[[tuple[str, ...]], str] | None = None,
           reader: Callable[[str], str | None] | None = None,
           meminfo_path: str = LINUX_MEMINFO_PATH,
           command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
       ) -> None:
           self._platform = platform_name or sys.platform
           self._runner = self._run_command if runner is None else runner
           self._reader = self._read_text if reader is None else reader
           self._meminfo_path = meminfo_path
           self._timeout = command_timeout_seconds

       def total_bytes(self) -> int | None:
           if self._platform.startswith("linux"):
               return self._linux_total()
           if self._platform == "darwin":
               return self._darwin_total()
           return None

       def _darwin_total(self) -> int | None:
           raw = self._runner(DARWIN_MEMSIZE_ARGV).strip()
           if not raw.isdigit() or int(raw) <= 0:
               return None
           return int(raw)

       def _linux_total(self) -> int | None:
           text = self._reader(self._meminfo_path)
           if text is None:
               return None
           for line in text.splitlines():
               key, _, rest = line.partition(":")
               if key.strip() != "MemTotal":
                   continue
               parts = rest.split()
               if not parts or not parts[0].isdigit():
                   return None
               value = int(parts[0])
               if len(parts) > 1 and parts[1].lower() == "kb":
                   value *= 1024
               return value if value > 0 else None
           return None

       def _run_command(self, argv: tuple[str, ...]) -> str:
           """stdout of a finished command, or "" for any failure (never raises)."""
           try:
               completed = subprocess.run(  # nosec B603 - fixed argv, no shell
                   list(argv),
                   capture_output=True,
                   text=True,
                   timeout=self._timeout,
                   check=False,
               )
           except (OSError, subprocess.TimeoutExpired):
               return ""
           return completed.stdout if completed.returncode == 0 else ""

       @staticmethod
       def _read_text(path: str) -> str | None:
           """The whole file, or None when this machine has no such file."""
           try:
               with open(path, encoding="utf-8") as handle:
                   return handle.read()
           except OSError:
               return None
   ```
2. **Its interface.** New
   `src/vibey_runners/common/src/vibey_runners/common/infrastructure/interfaces/memory_probe_interface.py`:
   ```python
   """The seam for the family's physical-memory reading (ADR-0016, #383)."""

   from __future__ import annotations

   from typing import Protocol, runtime_checkable


   @runtime_checkable
   class MemoryProbeInterface(Protocol):
       """How much physical memory this machine has."""

       def total_bytes(self) -> int | None:
           """This machine's physical memory in bytes, or None when it will not say."""
           ...
   ```
   Two new package files, each a provenance line plus a one-line docstring:
   `.../common/infrastructure/__init__.py` (`"""The family's shared infrastructure: the memory probe (#383)."""`)
   and `.../common/infrastructure/interfaces/__init__.py`, which also re-exports:
   `from vibey_runners.common.infrastructure.interfaces.memory_probe_interface import MemoryProbeInterface`
   and `__all__ = ["MemoryProbeInterface"]`.
3. **Rules the probe keeps.** `platform_name` defaults to `sys.platform`; `linux*` reads
   `meminfo_path`'s `MemTotal` line (`kB` multiplied by 1024, a unit-less number taken as bytes,
   exactly as `fit.py:431-447` reads it); `darwin` runs `("sysctl", "-n", "hw.memsize")`; any other
   platform, an unreadable file, a missing or non-numeric `MemTotal`, a failed or empty command, or a
   zero total answers `None`. It never raises.
4. **vibey-gh reads through it**, in `src/vibey_tools/gh/vibey_gh/fit.py`, and nothing else in that
   module changes:
   - `DarwinMemorySampler` gains
     `def __init__(self, probe: MemoryProbeInterface | None = None) -> None: self._probe = probe`
     and a method
     ```python
     def _physical_total(self) -> int:
         """Bytes of physical memory, read by the family probe (#383, sub-doctrine 10.e)."""
         probe = self._probe
         if probe is None:
             # Imported here, not at the top: `import vibey_gh.cli` must keep working with only
             # this package on PYTHONPATH -- the self-hosted pre-push hook runs exactly that
             # (vibey_gh/templates/githooks/pre-push, `vibey_gh_self`).
             from vibey_runners.common.infrastructure.memory_probe import MemoryProbe

             # `_run` is looked up per call, so the fit's own command seam still reaches it.
             probe = MemoryProbe(platform_name="darwin", runner=lambda argv: _run(*argv))
         return probe.total_bytes() or 0
     ```
     In `sample()`, the four lines `total_bytes = 0`, `raw = _run("sysctl", "-n", "hw.memsize").strip()`,
     `if raw.isdigit():`, `total_bytes = int(raw)` (`fit.py:272-275`) become
     `total_bytes = self._physical_total()`.
   - `LinuxMemorySampler.__init__` (`fit.py:332-358`) gains a last keyword parameter
     `probe: MemoryProbeInterface | None = None`, stored as `self._probe = probe`, and a method
     ```python
     def _physical_total(self) -> int:
         """The host's physical memory, read by the family probe (#383, sub-doctrine 10.e)
         through this sampler's own reader and path, so a cgroup limit still overrides it."""
         probe = self._probe
         if probe is None:
             # Imported here for the reason DarwinMemorySampler._physical_total gives.
             from vibey_runners.common.infrastructure.memory_probe import MemoryProbe

             probe = MemoryProbe(
                 platform_name="linux", reader=self._reader.read, meminfo_path=self._meminfo_path
             )
         return probe.total_bytes() or 0
     ```
     In `sample()`, `total = fields.get("MemTotal", 0)` (`fit.py:390`) becomes
     `total = self._physical_total()`. The cgroup logic, `_meminfo`, `_MEMINFO_KEYS` and every
     other line stay as they are.
   - The annotation-only import goes in the existing `from __future__ import annotations` module:
     add `from typing import TYPE_CHECKING` to the imports and, after the `vibey_gh` imports,
     `if TYPE_CHECKING:` / `from vibey_runners.common.infrastructure.interfaces.memory_probe_interface import MemoryProbeInterface`.
   - Every existing `test/test_fit.py` test keeps passing unedited: the Darwin tests patch `fit._run`
     (reached through the lambda) and the Linux tests hand `FakeFiles` whose `read` the probe uses.
5. **vibey-gh's declaration.** `src/vibey_tools/gh/pyproject.toml` keeps `dependencies = []`
   (ADR-0037: a family package is never named there; it ships in the same wheel and is installed
   from the tree). The comment above it (the three lines starting `# Deliberately empty`) gains one
   sentence at its end: `# The fit's physical-memory reading is the family probe in
   vibey-runners-common, imported where it is used so that `import vibey_gh.cli` stays stdlib-only.`
   (as a fourth comment line).
6. **The family package's gates.** `src/vibey_runners/common/pyproject.toml`'s contract
   `Interfaces declare seams, never consume them` becomes:
   ```toml
   source_modules = [
       "vibey_runners.common.application.interfaces",
       "vibey_runners.common.infrastructure.interfaces",
   ]
   forbidden_modules = [
       "vibey_runners.common.application.usecases",
       "vibey_runners.common.infrastructure.memory_probe",
   ]
   ```
   Nothing else in that file changes.
7. **CI runs it** (`.github/workflows/ci.yml`; 12.c, the pipeline is declared):
   - the three `vibey-runners-common` rows (`ci.yml:321-335`) each gain
     `test: 'python -m pytest -q -p no:cacheprovider --cov=vibey_runners.common.infrastructure --cov-branch --cov-report=term-missing --cov-fail-under=100'`
     (a suite now exists, so `tests/meta/test_tools_matrix_covers_every_package.py` demands it),
     and the comment above them (`ci.yml:317-320`, `# vibey-runners-common ships no suite, ...`)
     becomes: `# vibey-runners-common's suite covers its one infrastructure module, the family`
     / `# memory probe (#383), at a 100% branch floor. Its static gate runs a strict mypy and`
     / `# its two import contracts.`;
   - the three `vibey-gh` rows (`ci.yml:236-243`): `install: 'pip install -e ".[dev]"'` becomes
     `install: 'pip install -e ../../vibey_runners/common && pip install -e ".[dev]"'`;
   - the `tools-lint` step `vibey-gh - black, isort, mypy` (`ci.yml:699-705`) gains the line
     `python -m pip install --quiet -e ../../vibey_runners/common` directly above
     `python -m pip install --quiet -e ".[dev]"`.

## Where to change
New files (line 1 of each is the provenance comment copied byte for byte from line 1 of
`src/vibey_runners/common/src/vibey_runners/common/application/interfaces/system.py`):
- `src/vibey_runners/common/src/vibey_runners/common/infrastructure/__init__.py`
- `src/vibey_runners/common/src/vibey_runners/common/infrastructure/memory_probe.py`
- `src/vibey_runners/common/src/vibey_runners/common/infrastructure/interfaces/__init__.py`
- `src/vibey_runners/common/src/vibey_runners/common/infrastructure/interfaces/memory_probe_interface.py`
- `src/vibey_runners/common/tests/test_memory_probe.py`

Edited files (always `edit_file`, never a rewrite; all are far over 100 lines except the common
pyproject):
- `src/vibey_runners/common/pyproject.toml` — behaviour 6;
- `src/vibey_tools/gh/vibey_gh/fit.py` — behaviour 4 (853 lines: read slices with `sed -n`);
- `src/vibey_tools/gh/test/test_fit.py` — append the tests below;
- `src/vibey_tools/gh/pyproject.toml` — behaviour 5;
- `.github/workflows/ci.yml` — behaviour 7.

Why this spans two tenants and CI: moving the reading (not copying it) is the lane (10.e), vibey-gh
is its current owner, and plain-pip CI rows only see a family package that is installed first.

## Acceptance criteria
- [ ] The common suite passes at 100% branch coverage of `vibey_runners.common.infrastructure`;
      `mypy --strict src/vibey_runners/common` and `lint-imports` are clean.
- [ ] `vibey-gh`'s whole suite passes (100% line and branch of `vibey_gh`), with every existing
      `test/test_fit.py` test unedited; black, isort and mypy are clean.
- [ ] `test_both_samplers_read_physical_memory_through_the_family_probe` passes.
- [ ] With only the gh directory on the path and no site-packages,
      `python3 -S -c "import vibey_gh.cli"` succeeds (the self-hosted hook's import).
- [ ] `tests/meta/test_tools_matrix_covers_every_package.py` and
      `tests/meta/test_import_contracts_bind.py` pass from the repository root.
- [ ] No test patches `subprocess`, `sys.platform`, `platform` or any module attribute.
- [ ] `git diff --stat` lists exactly the ten files named under "Where to change".

## Tests to write first (TDD)
New `src/vibey_runners/common/tests/test_memory_probe.py` (seams only: `runner=`, `reader=`,
`platform_name=`, `meminfo_path=`; real files under `tmp_path`; real harmless subprocesses of
`sys.executable`; nothing patched):
- `test_arch_linux_reads_memtotal_in_kib` — `reader` returns
  `"MemTotal:       32793692 kB\nMemAvailable:    8000000 kB\n"` for `/proc/meminfo`;
  `MemoryProbe(platform_name="linux", reader=...).total_bytes() == 32793692 * 1024`; and the reader
  was asked for exactly `"/proc/meminfo"`.
- `test_a_unitless_memtotal_is_bytes` — `"MemTotal: 2048\n"` → `2048`.
- `test_linux_that_states_no_usable_total_is_none` — parametrised over `None` (no file),
  `"MemAvailable: 1 kB\n"` (no MemTotal line), `"MemTotal:\n"`, `"MemTotal: lots kB\n"`,
  `"MemTotal: 0 kB\n"` → `None`.
- `test_macos_asks_sysctl_for_hw_memsize` — a `runner` recording its argv answers
  `"25769803776\n"`; `MemoryProbe(platform_name="darwin", runner=...).total_bytes() == 25769803776`
  and the argv was `("sysctl", "-n", "hw.memsize")`.
- `test_macos_that_answers_nothing_usable_is_none` — parametrised runner outputs `""`, `"n/a\n"`,
  `"0\n"` → `None`.
- `test_another_platform_is_none_without_asking` — `platform_name="win32"` with a runner and a
  reader that fail the test if called → `None`.
- `test_the_default_reader_reads_a_real_file` — write `tmp_path / "meminfo"` with
  `"MemTotal: 1000 kB\n"`; `MemoryProbe(platform_name="linux", meminfo_path=str(that)).total_bytes() == 1024000`;
  a `meminfo_path` that does not exist gives `None`.
- `test_the_default_runner_never_raises` — on `probe = MemoryProbe(platform_name="darwin", command_timeout_seconds=30)`:
  `probe._run_command((sys.executable, "-c", "print(42)")) == "42\n"`;
  `probe._run_command((sys.executable, "-c", "raise SystemExit(3)")) == ""`;
  `probe._run_command((str(tmp_path / "no-such-binary"),)) == ""`. Then, on a second probe with
  `command_timeout_seconds=0.5`,
  `_run_command((sys.executable, "-c", "import time; time.sleep(5)")) == ""` (the timeout).
- `test_the_default_platform_is_this_interpreters` — `MemoryProbe(runner=lambda argv: "", reader=lambda path: None).total_bytes() is None`
  (whatever `sys.platform` is, those seams state nothing).
- `test_the_probe_satisfies_its_interface` — `isinstance(MemoryProbe(), MemoryProbeInterface)`,
  importing the interface from `vibey_runners.common.infrastructure.interfaces`.

Append to `src/vibey_tools/gh/test/test_fit.py` (add `from vibey_runners.common.infrastructure.memory_probe import MemoryProbe`
to the file's top import block with `edit_file` if a test needs it; never an import below code):
- a small class `FixedProbe` with `__init__(self, total: int | None)` and `total_bytes(self)`
  returning it;
- `test_both_samplers_read_physical_memory_through_the_family_probe` —
  `LinuxMemorySampler(FakeFiles({}), probe=FixedProbe(8 * 1024**3)).sample()` has
  `total_gb == 8.59` and `readable`; `LinuxMemorySampler(FakeFiles({}), probe=FixedProbe(None)).sample()`
  is not `readable`; `DarwinMemorySampler(probe=FixedProbe(25769803776)).sample().total_gb == 25.77`
  (its `vm_stat` and swap reads run for real and are not asserted).
- `test_the_linux_default_probe_reads_through_the_samplers_own_reader` —
  `LinuxMemorySampler(FakeFiles({fit.LINUX_MEMINFO_PATH: "MemTotal: 4000000 kB\n"})).sample().total_gb == 4.1`.

## Checks the lane must run (all must pass)
```bash
# the family package
cd src/vibey_runners/common
python -c "import vibey_runners.common, pytest_cov" || python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider --cov=vibey_runners.common.infrastructure --cov-branch --cov-report=term-missing --cov-fail-under=100
python -m mypy --strict src/vibey_runners/common
lint-imports
# vibey-gh
cd ../../vibey_tools/gh
python -c "import vibey_gh" || python -m pip install -e ".[dev]"
python -m pytest -q -p no:cacheprovider --no-cov test/test_fit.py test/test_fitloop.py test/test_operation_estimate.py
python -m pytest -q -p no:cacheprovider          # whole suite, 100% line+branch of vibey_gh
python -m black --check --line-length 100 vibey_gh test
isort --check-only vibey_gh test
python -m mypy vibey_gh
PYTHONSAFEPATH=1 PYTHONPATH="$PWD" python3 -S -c "import vibey_gh.cli"   # the self-hosted hook's import
# the repository
cd ../../..
UV_CACHE_DIR=$TMPDIR/uvcache uv run pytest -q -p no:cacheprovider tests/meta/test_tools_matrix_covers_every_package.py tests/meta/test_import_contracts_bind.py
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff check .
UV_CACHE_DIR=$TMPDIR/uvcache uv run ruff format --check .
UV_CACHE_DIR=$TMPDIR/uvcache uv lock --check
git diff --stat   # exactly the ten files named under "Where to change"
```

## Out of scope
- qwenloop: it adopts the probe in split-383-4-ram-tier-selection (its CI rows then install
  `../common`). Do not touch `src/vibey_runners/qwen/`.
- The fit's free-memory, swap and cgroup readings (`vm_stat`, `vm.swapusage`, the cgroup files,
  `MemAvailable`): they stay in `fit.py`, unchanged. Only the physical total moves.
- `DarwinMemorySamplerInterface` / `LinuxMemorySamplerInterface` (`vibey_gh/interfaces/class_contracts.py:625-631`),
  `machine_sampler`, `sample_machine`, `operation_estimate.py`, `fitloop.py`, `cli.py`.
- vibey-bootstrap: nothing in its suite samples memory, so its rows keep their installs.
- Naming `vibey-runners-common` in any `dependencies` list (ADR-0037 forbids it; see
  `src/vibey_runners/claude/pyproject.toml:53-56`), and the common README.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs, or change git remotes. Commit locally as this spec's title.

## Conventions this lane relies on (everything needed is here)
**C1, seams (9.b).** Substitute only at declared seams — here the probe's `runner=`, `reader=`,
`platform_name=` and `meminfo_path=` keywords, and the samplers' `probe=` keyword. Never
`monkeypatch.setattr` an import or a module/class attribute (new tests only: the existing
`test_fit.py` tests that patch `fit._run` are left exactly as they are), never `mock.patch`,
`MagicMock` or `AsyncMock`. No test touches the network.

**C2, vibey-gh's formatter trap.** `black --line-length 100` + `isort` (CI `tools-lint`) and the
root `ruff format` must both be clean on `fit.py` and `test_fit.py`, and they disagree on some
wraps. Keep lines at or under 100 columns, one argument per line with a trailing comma in a
multi-line call, no backslash continuations, no implicit string concatenation. If they fight over a
line, restructure it; never alternate between them.

**C3, the family package's floor.** Its CI row now runs a suite, so every branch of
`memory_probe.py` needs a test. A Protocol's docstring-and-`...` body is not counted by coverage.

**C4, why the import is inside the method.** The self-hosted pre-push hook
(`src/vibey_tools/gh/vibey_gh/templates/githooks/pre-push:58-72`) runs
`PYTHONSAFEPATH=1 PYTHONPATH=<gh dir> python3 -c "import vibey_gh.cli"` with nothing else
installed. `vibey_gh.cli` imports `operation_estimate`, which imports `fit`; a top-level import of
`vibey_runners.common` there would make that fail and the hook fall back to an installed copy.

**Depends on:** none
- none: the probe is new, and vibey-gh's samplers are on integration today.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
