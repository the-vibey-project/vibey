## Title
feat(gh): pressure samplers for Arch Linux and macOS — free memory, swap writes, load, CPUs and thermal throttling, read through the fit's own seams

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *hardware*: "stability (paging pressure
and free-page series), reliability (thermal / CPU headroom, macOS and Arch Linux per 8.h)";
"Proposed child issues" 4: "Sample paging pressure and thermal/CPU headroom (macOS
`vm_stat`/`sysctl`, Linux `/proc` + cgroup) ... Tests with recorded samples"). Sub-doctrine 8.h
(`src/vibey_tools/gh/docs/doctrines.md:326-333`): Arch Linux and macOS, both, proven by tests on
both. 10.e (`doctrines.md:417`): the fit calculus already reads this machine, so its readers are
reused, never copied — `TextFileReader` (`src/vibey_tools/gh/vibey_gh/fit.py:247-260`), the memory
samplers and their selection (`fit.py:263-310`, `:313-477`, `machine_sampler` at `:480-493`), and
its command runner (`fit._run`, `:239-244`). 9.b (`doctrines.md:349`): each reading goes through an
injected reader or runner, so a test hands in recorded text and patches nothing.

Verified gap (integration clone): the fit reads memory size, free memory and swap *totals*
(`fit.Machine`, `fit.py:156-175`) but nothing reads swap *writes*, load, CPU count or thermal
state, and `hardware.stability` / `hardware.reliability` are always "unmeasured"
(`vibey_gh/feasibility.py:100-101`). This lane adds the readings only; keeping them as a series in
the fit journal and turning the series into coordinates are `roadmap-134-hardware-series-p2` and
`-p3`.

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **New module `vibey_gh/pressure.py`** (provenance line 1 from `vibey_gh/fit.py:1`), module
   docstring: what each field is, that every source path and command is a default a caller may
   replace (12.c, as `fit.py:86-93` says of its own paths), and that a field the machine will not
   state is `None`, never a guess. Contents:
   - Constants (defaults, not law):
     ```python
     LINUX_VMSTAT_PATH = "/proc/vmstat"
     LINUX_LOADAVG_PATH = "/proc/loadavg"
     LINUX_CPU_ONLINE_PATH = "/sys/devices/system/cpu/online"
     LINUX_CGROUP_CPU_MAX_PATH = "/sys/fs/cgroup/cpu.max"  # cgroup v2; a container's own under cgroupns
     LINUX_THERMAL_ZONE = "/sys/class/thermal/thermal_zone0"
     DARWIN_VM_STAT: tuple[str, ...] = ("vm_stat",)
     DARWIN_LOADAVG: tuple[str, ...] = ("sysctl", "-n", "vm.loadavg")
     DARWIN_LOGICAL_CPUS: tuple[str, ...] = ("sysctl", "-n", "hw.logicalcpu")
     DARWIN_THERMAL: tuple[str, ...] = ("pmset", "-g", "therm")
     ```
   - `@dataclass(frozen=True) class PressureReading:` fields, each with a one-line comment:
     `free_fraction: float | None` (what a new process could get over the machine's or cgroup's
     total), `swapouts: int | None` (pages written to swap since boot, a counter),
     `load_1m: float | None`, `cpus: float | None` (logical CPUs this process may use; a cgroup
     quota can make it fractional), `thermal: float | None` (1.0 unthrottled down to 0.0, the
     operating system's own statement), `platform: str`. And:
     ```python
         @staticmethod
         def free_of(machine: Machine) -> float | None:
             """What a new process could get over the total, or `None` when the machine would
             not state its size (the fit's own `readable`, `fit.py:164-169`)."""
             if not machine.readable or machine.total_gb <= 0:
                 return None
             return round(min(max(machine.free_gb / machine.total_gb, 0.0), 1.0), 4)
     ```
   - `class LinuxPressureSampler(LinuxPressureSamplerInterface)`:
     `__init__(self, reader: TextFileReaderInterface | None = None, *, machine_sampler: MemorySamplerInterface | None = None, vmstat_path: str = LINUX_VMSTAT_PATH, loadavg_path: str = LINUX_LOADAVG_PATH, cpu_online_path: str = LINUX_CPU_ONLINE_PATH, cgroup_cpu_max_path: str = LINUX_CGROUP_CPU_MAX_PATH, thermal_zone: str = LINUX_THERMAL_ZONE) -> None`;
     `self._reader = fit.TextFileReader() if reader is None else reader`;
     `self._machines = fit.LinuxMemorySampler(self._reader) if machine_sampler is None else machine_sampler`
     (so free memory is the fit's own cgroup-aware reading). `sample()` returns
     `PressureReading(free_fraction=PressureReading.free_of(self._machines.sample()), swapouts=..., load_1m=..., cpus=..., thermal=..., platform="linux")` where:
     - `swapouts`: the line of `vmstat_path` whose two whitespace-separated fields are
       `pswpout` and digits → that `int`; else `None`.
     - `load_1m`: the first whitespace-separated token of `loadavg_path` as `float`; unreadable,
       empty or not a number → `None`.
     - `cpus`: `online` = the count `cpu_online_path` states (comma-separated parts, each `N` or
       `N-M` with `M >= N`; any other part, or an empty file, → `None`); `quota` = for
       `cgroup_cpu_max_path` holding exactly two digit fields `Q P` with `P > 0`,
       `round(Q / P, 4)`; `max P` or anything else → `None`. Result: `quota` when it is not
       `None` and (`online is None` or `quota < online`); else `float(online)` or `None`.
     - `thermal`: `f"{thermal_zone}/temp"` and `f"{thermal_zone}/trip_point_0_temp"`, both digits
       after `strip()` → `1.0` when the temperature is below the kernel's first trip point,
       `0.0` at or above it; either unreadable → `None`.
   - `class DarwinPressureSampler(DarwinPressureSamplerInterface)`:
     `__init__(self, runner: Callable[[tuple[str, ...]], str] | None = None, *, machine_sampler: MemorySamplerInterface | None = None) -> None`;
     `self._runner = self._run_through_fit if runner is None else runner`;
     `self._machines = fit.DarwinMemorySampler() if machine_sampler is None else machine_sampler`.
     ```python
         @staticmethod
         def _run_through_fit(argv: tuple[str, ...]) -> str:
             """stdout of `argv`, or "" -- the fit calculus's own command runner (10.e)."""
             return fit._run(*argv)
     ```
     (Today `fit._run` is `fit.py:239-244`. If `fakes-tenant-gh-3` has replaced it with an
     injected runner object, call that object exactly the way `fit.DarwinMemorySampler`'s
     default calls it after that lane; do not write a second subprocess runner.)
     `sample()` returns `PressureReading(free_fraction=PressureReading.free_of(self._machines.sample()), ..., platform="darwin")` where:
     - `swapouts`: the `vm_stat` line whose key (before `:`) is `Swapouts`, value stripped of a
       trailing `.` and digits → `int`; else `None`.
     - `load_1m`: `vm.loadavg` text with `{` and `}` replaced by spaces, first token as `float`;
       else `None`.
     - `cpus`: `hw.logicalcpu` stripped digits greater than zero → `float`; else `None`.
     - `thermal`: the `pmset -g therm` line whose key (before `=`) is `CPU_Speed_Limit` with
       digits → `round(min(value, 100) / 100, 4)`; no such line (Apple silicon prints only
       `Note:` lines) → `None`.
   - ```python
     def pressure_sampler(platform_name: str = "") -> PressureSamplerInterface:
         """The pressure sampler that can read this machine, over the same memory sampler
         `fit.machine_sampler` chooses (sub-doctrine 10.e).

         Module-level for the reason `fit.machine_sampler` gives (`fit.py:480-489`): it is the
         selection itself, kept nameable so the choice can be asserted directly.
         """
         # No name means this interpreter's own platform, exactly as `fit.machine_sampler()`
         # decides it when called with no argument.
         machine = fit.machine_sampler(platform_name) if platform_name else fit.machine_sampler()
         if isinstance(machine, fit.LinuxMemorySampler):
             return LinuxPressureSampler(machine_sampler=machine)
         return DarwinPressureSampler(machine_sampler=machine)
     ```
   - Imports: `from collections.abc import Callable`, `from dataclasses import dataclass`,
     `from vibey_gh import fit`, `from vibey_gh.fit import Machine`, and the three interfaces.
2. **New interface `vibey_gh/interfaces/pressure_sampler_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`; copy that file's structure, `:14-33`), with
   `PressureReading` imported under `TYPE_CHECKING`:
   - `PressureSamplerInterface(Protocol)`, `runtime_checkable`,
     `def sample(self) -> PressureReading:` — "One reading of how hard this machine is working.
     A field it will not state is `None`, never a guess."
   - `LinuxPressureSamplerInterface(PressureSamplerInterface, Protocol)` and
     `DarwinPressureSamplerInterface(PressureSamplerInterface, Protocol)`, each `runtime_checkable`
     with a one-line docstring (as `class_contracts.py:624-631` does for the memory samplers).
3. **Fake** appended to `test/fakes.py`:
   ```python
   class ScriptedPressureSampler:
       """A pressure sampler that states scripted readings in order, repeating the last, and
       counts how often it was asked (#134)."""

       def __init__(self, first: PressureReading, *rest: PressureReading) -> None:
           self._readings = [first, *rest]
           self.calls = 0

       def sample(self) -> PressureReading:
           self.calls += 1
           if len(self._readings) > 1:
               return self._readings.pop(0)
           return self._readings[0]
   ```
   Register `PressureSamplerInterface` → `ScriptedPressureSampler` in `test/test_port_parity.py`
   the way `ScriptedGitRunner` is registered; add `LinuxPressureSamplerInterface` and
   `DarwinPressureSamplerInterface` to its `EXEMPT` with the reason
   `"class contract: its seam, PressureSamplerInterface, has ScriptedPressureSampler"`.

## Where to change
- New: `vibey_gh/pressure.py`, `vibey_gh/interfaces/pressure_sampler_interface.py`,
  `test/test_pressure.py`.
- Append to `test/fakes.py` and `test/test_fakes.py`; entries in `test/test_port_parity.py`.
- Do **not** edit `vibey_gh/fit.py` (`split-383-3-memory-probe` and `fakes-tenant-gh-3` own it).
- Patterns to copy: `LinuxMemorySampler`'s injected paths and reader (`fit.py:332-358`), the
  `FakeFiles` reader in `test/test_fit.py:313-320`, and `vm_stat` parsing (`fit.py:278-293`).

## Acceptance criteria
- [ ] The recorded macOS sample and the Linux kernel-format sample below each produce exactly the
      readings stated; missing files and silent commands give `None` fields, never zeros.
- [ ] `grep -n "subprocess" vibey_gh/pressure.py` prints nothing (commands go through `fit._run`).
- [ ] No test patches anything: every reading enters through `reader=`, `runner=` or `machine_sampler=`.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_pressure.py` (provenance line 1 from `test/test_fit.py:1`; import
`from fakes import ScriptedPressureSampler`). Helpers in the file:
```python
class FakeFiles:
    """The read seam, given exact contents. A file not in the mapping does not exist."""

    def __init__(self, files: dict[str, str]) -> None:
        self.files = files

    def read(self, path: str) -> str | None:
        return self.files.get(path)


class RecordedCommands:
    """The command seam, given exact output per argv. Any other command prints nothing."""

    def __init__(self, outputs: dict[tuple[str, ...], str]) -> None:
        self.outputs = outputs
        self.asked: list[tuple[str, ...]] = []

    def __call__(self, argv: tuple[str, ...]) -> str:
        self.asked.append(argv)
        return self.outputs.get(argv, "")


class FixedMachine:
    """A memory sampler that states one machine."""

    def __init__(self, machine: Machine) -> None:
        self.machine = machine

    def sample(self) -> Machine:
        return self.machine
```
Recorded samples (constants in the test file). **macOS**, recorded 2026-09-22 on an arm64 Mac
running macOS 26.6.2 (`vm_stat`, `sysctl -n vm.loadavg`, `sysctl -n hw.logicalcpu`,
`pmset -g therm`), verbatim:
```python
DARWIN_VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                   187161.
Pages active:                                 538410.
Pages inactive:                               522804.
Pages speculative:                             17000.
Pages throttled:                                   0.
Pages wired down:                             189546.
Pages purgeable:                                1722.
"Translation faults":                     3035804666.
Pages copy-on-write:                       250964102.
Pages zero filled:                        1221554261.
Pages reactivated:                         385926885.
Pages purged:                               26124677.
File-backed pages:                            203350.
Anonymous pages:                              874864.
Pages stored in compressor:                  1098728.
Pages occupied by compressor:                  60412.
Decompressions:                            552331508.
Compressions:                              601961380.
Pageins:                                    80488109.
Pageouts:                                     421167.
Swapins:                                    33787095.
Swapouts:                                   38466088.
Pages tagged:                                 106823.
Pages tagged resident:                         97938.
Pages tagged compressed:                        8885.
Pages tag-storage:                             49152.
Pages tag-storage holding tags:                 4242.
Pages tag-storage free:                         1161.
Pages tag-storage non-tag pageable:            43716.
Pages tag-storage non-tag wired:                  33.
Bytes of compressed tags:                    1302848.
Tagged compressions:                        11427044.
Tagged decompressions:                      11267980.
"""
DARWIN_LOADAVG = "{ 2.78 3.45 3.39 }\n"
DARWIN_LOGICAL_CPUS = "10\n"
DARWIN_PMSET_APPLE_SILICON = (
    "Note: No thermal warning level has been recorded\n"
    "Note: No performance warning level has been recorded\n"
    "Note: No CPU power status has been recorded\n"
)
# The form Intel Macs print (not recorded on the arm64 host above).
DARWIN_PMSET_INTEL = "CPU_Scheduler_Limit \t= 100\nCPU_Available_CPUs \t= 8\nCPU_Speed_Limit \t= 70\n"
```
**Linux**, in the exact formats the kernel writes (proc(5); cgroup v2 `cpu.max`; the thermal sysfs
zone) — no Arch host was available to record from; the reviewer re-records them on Arch as 8.h
evidence at batch review:
```python
LINUX_VMSTAT = "nr_free_pages 1995413\npgpgin 9123456\npgpgout 4567890\npswpin 1024\npswpout 2048\npgmajfault 3141\n"
LINUX_LOADAVG = "0.52 0.58 0.59 2/1203 45123\n"
LINUX_FILES = {
    "/proc/vmstat": LINUX_VMSTAT,
    "/proc/loadavg": LINUX_LOADAVG,
    "/sys/devices/system/cpu/online": "0-15\n",
    "/sys/fs/cgroup/cpu.max": "max 100000\n",
    "/sys/class/thermal/thermal_zone0/temp": "45000\n",
    "/sys/class/thermal/thermal_zone0/trip_point_0_temp": "100000\n",
}
```
(Wrap the long `LINUX_VMSTAT` literal as a parenthesised sequence of one-line strings if black and
ruff disagree about it.) Tests:
- `test_the_samplers_declare_their_seams` — `LinuxPressureSampler(FakeFiles({}), machine_sampler=FixedMachine(...))`
  is a `LinuxPressureSamplerInterface` and a `PressureSamplerInterface`; the Darwin one likewise.
- `test_macos_reads_the_recorded_sample` — `DarwinPressureSampler(RecordedCommands({("vm_stat",): DARWIN_VM_STAT, ("sysctl", "-n", "vm.loadavg"): DARWIN_LOADAVG, ("sysctl", "-n", "hw.logicalcpu"): DARWIN_LOGICAL_CPUS, ("pmset", "-g", "therm"): DARWIN_PMSET_APPLE_SILICON}), machine_sampler=FixedMachine(Machine(total_gb=25.77, free_gb=11.63, swap_used_gb=0.0, swap_total_gb=0.0))).sample()
  == PressureReading(free_fraction=0.4513, swapouts=38466088, load_1m=2.78, cpus=10.0, thermal=None, platform="darwin")`,
  and the runner was asked exactly the four argv constants.
- `test_an_intel_mac_states_its_speed_limit` — the same with `DARWIN_PMSET_INTEL`: `thermal == 0.7`.
- `test_a_mac_that_answers_nothing_states_nothing` — `RecordedCommands({})` and an unreadable
  machine (`Machine(0.0, 0.0, 0.0, 0.0, readable=False)`): every field `None`, `platform == "darwin"`.
- `test_arch_linux_reads_its_kernel_files` — `LinuxPressureSampler(FakeFiles(LINUX_FILES), machine_sampler=FixedMachine(Machine(total_gb=32.77, free_gb=8.19, swap_used_gb=0.0, swap_total_gb=2.15))).sample()
  == PressureReading(free_fraction=0.2499, swapouts=2048, load_1m=0.52, cpus=16.0, thermal=1.0, platform="linux")`.
- `test_a_cgroup_quota_below_the_online_cpus_wins` — `cpu.max` `"200000 100000\n"` → `cpus == 2.0`;
  `"400000 100000\n"` with online `"0-1\n"` → `2.0` (online is smaller);
  `"garbage\n"` → `16.0`; online missing and quota `"150000 100000\n"` → `1.5`.
- `test_online_cpu_ranges_are_counted_or_refused` (parametrised, cpu.max missing) — `"0-3,6,8-9\n"`
  → `7.0`; `"3-1\n"`, `"x\n"`, `"\n"` → `None`.
- `test_a_zone_at_its_trip_point_is_throttled` — temp `"101000\n"` → `thermal == 0.0`; temp
  missing → `None`.
- `test_linux_files_that_state_nothing_give_none` — `FakeFiles({"/proc/vmstat": "pgpgin 1\n", "/proc/loadavg": "\n"})`:
  `swapouts`, `load_1m`, `cpus`, `thermal` are `None`.
- `test_linux_free_memory_is_the_fits_own_reading` — no `machine_sampler`:
  `LinuxPressureSampler(FakeFiles({fit.LINUX_MEMINFO_PATH: "MemTotal: 32000000 kB\nMemAvailable: 8000000 kB\n"})).sample().free_fraction == 0.2499`.
- `test_the_default_seams_are_the_fits` — `LinuxPressureSampler()` and
  `DarwinPressureSampler(RecordedCommands({}))` construct without error (neither samples);
  `DarwinPressureSampler._run_through_fit((sys.executable, "-c", "print(7)")) == "7\n"`.
- `test_the_sampler_is_the_one_that_can_read_this_kind_of_machine` —
  `pressure_sampler("linux")` is a `LinuxPressureSampler`, `pressure_sampler("darwin")` a
  `DarwinPressureSampler`, `pressure_sampler()` one of the two.

Append to `test/test_fakes.py`:
- `test_pressure_sampler_fake_states_readings_in_order_and_repeats_the_last`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_pressure.py test/test_fit.py test/test_fakes.py test/test_port_parity.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- `vibey_gh/fit.py` and its samplers; the fit journal and the series
  (`roadmap-134-hardware-series-p2`, `-p3`); `[estimate]` keys; `vibey_gh/cli.py`.
- Thermal zones other than the configured one, GPU or disk readings.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
