## Title
feat(engines): choose the local context window from measured host memory, not a constant

## Why
Sub-doctrine **8.g — always measured** (`src/vibey_tools/gh/docs/doctrines.md:336-344`):
"rotation weights, model residency, lane capacity and **defaults** are chosen from live
evidence, never from assumption." Sub-doctrine **12.c** (`doctrines.md:493`): "a hard-coded
value that could have been a key is a decision taken away from the next human adopter,
silently. A default is configurability with an opinion; a constant is not." Sub-doctrine
**8.h** (`doctrines.md:346-353`): Arch Linux and macOS both, or it is not done.

The context window a local engine runs at is, today, four unrelated constants and no
measurement at all:

- `src/vibey/domain/config.py:35` — `DEFAULT_LOCAL_CONTEXT_WINDOW = 32_768`, the default of
  `ClaudeloopLocalConfig.context_window` (`config.py:85`).
- `src/vibey/domain/config.py:191` — `QwenloopConfig.context_window: int = 32_768`.
- `src/vibey/infrastructure/engines/ollama_chat.py:86` — `OllamaChatClient.CONTEXT_CEILING =
  32768`, a **class attribute** with no constructor parameter, so the `num_ctx` every
  sovereign DESIGN and DECOMPOSE request is sent with (`ollama_chat.py:162`) can never exceed
  it, on any host.
- `src/vibey/infrastructure/engines/descriptors.py:285,313` — `context_window=32_768` on both
  the OPENCODE and QWENLOOP descriptors.

Nothing in `src/vibey/` reads host memory. `grep -rn "meminfo\|hw.memsize\|vm_stat\|swapusage\|psutil"
src/vibey/` returns nothing; the only platform dispatch in the tree is
`postgres.py:154` and `notify/desktop.py:21`, and neither looks at memory.

Two measurements taken on 2026-09-22 say both halves of that constant are wrong, in opposite
directions. They are recorded in `docs/plans/qwenstorm-3.0.0/bench/host-tuning.toml`:

1. **The host was being destroyed by a window nobody was using.** On a 24 GB machine,
   `llama-server` serving `gpt-oss:20b` at `context_window = 131072` held **14.93 GB RSS —
   62% of all RAM** — with swap at **17.0 / 18.4 GB used**, 4,569 pages free and 10.6M
   swapouts (`host-tuning.toml:18-35`). A model reserves KV cache in proportion to its
   context window, and that reservation was eating the machine.
2. **The workload never came close to either number.** Across **838 real recorded turns**
   (each run's `.qwenloop/runs/*/events.jsonl`, `input_tokens + output_tokens` per turn):
   p50 20,070 / p90 32,026 / p99 42,979 / **max 49,118**, and **zero turns over 64k**
   (`host-tuning.toml:40-48`). So 32768 — the number this repository actually ships — would
   have truncated **71 turns (8.5%)**, and trimming a transcript mid-lane costs the model the
   evidence it is reasoning from. 65536 covers every turn ever recorded with a third again as
   headroom, and halves the KV reservation against 131072.

**There is no swap lever on macOS.** No `swapon`, no swappiness, no swap partition;
`dynamic_pager` does not run on a modern system, and the kernel grows swapfiles into free disk
on demand — with 498 GB free it takes more whenever it wants, so the 18.4 GB total observed is
what it had taken, never a ceiling (`host-tuning.toml:12-17`). Adding swap is not a lever on
the default paid operating system. **The lever is not needing it**, which means sizing the
reservation. This lane must therefore never try to configure swap anywhere; on Linux swap *is*
configurable, and that is a different lane's business.

This lane makes the number evidence-bounded and declared:

- **`domain/` decides, `infrastructure/` measures.** The choice — given these host facts and
  this recorded peak, this window and this is why — is arithmetic over values: it is pure, it
  belongs in `domain/`, and `tests/domain/test_domain_purity.py` walks the AST to keep it
  there. Reading `/proc/meminfo` or shelling out to `sysctl` is I/O: it belongs in
  `infrastructure/`. That split is the whole point of the lane. A policy that shells out is
  untestable without a host; a reader that decides is untestable without a decision.
- **Every number is a key (12.c).** The ladder, the headroom, the floor, the ceiling, the
  thresholds and the recorded peak are all declared in `[local_context]`, and an operator's
  `window` beats every measurement, unconditionally.
- **It is visible (10.f).** `vibey doctor` reports the number *with its evidence* — never a
  bare number — next to the engine lines it already prints.

## Required behaviour
Every path is relative to the repository root. The engine is `gpt-oss:20b` on Ollama (8.d),
but nothing below names a model: the ladder and the peak are the operator's declaration.

1. **`HostMemory` is a value, not a reading.** A frozen dataclass in `domain/`, carrying
   `total_bytes`, `available_bytes`, `swap_total_bytes`, `swap_used_bytes` and a `source`
   string naming where the numbers came from. Its derived facts are `measured`
   (`total_bytes > 0`), `total_gib` (floor division by 1 GiB), `available_percent` and
   `swap_used_percent` — each integer, each **0 when its denominator is 0**, because a host
   with no swap file (a common Arch install) is not a host that is swapping, and an unmeasured
   host is not a host at 0% free.
2. **The workload ceiling is the recorded peak plus declared headroom, rounded up to a power
   of two.** `observed_peak_tokens * (100 + headroom_percent) // 100`, then the next power of
   two at or above it. Integer arithmetic throughout — no floats, so the number is the same on
   every machine. With the defaults: `49118 * 133 // 100 = 65326`, and the next power of two
   is **65536**. `observed_peak_tokens = 0` means "nothing recorded yet", and the workload
   ceiling is then the declared `ceiling`.
3. **The host ceiling is a declared ladder rung.** The last rung whose `min_ram_gib` is at or
   below the host's `total_gib` wins. A host below every rung gets `floor`. An **unmeasured**
   host gets `ceiling` and rung `0`: 10.f forbids lowering a number on evidence nobody has,
   and the workload ceiling still applies.
4. **The rungs are declared just below the nominal sizes, and this is not a typo.** Linux's
   `MemTotal` excludes firmware-reserved memory, so a 16 GB machine reports about 15.3 GiB
   while the same hardware on macOS reports `hw.memsize = 17179869184` — exactly 16 GiB. A
   rung declared at `16` would put the two default operating systems on different rungs for
   identical hardware, which 8.h forbids. So the shipped ladder is
   `15 -> 32768`, `23 -> 65536`, `46 -> 131072`, and behaviour 3's test proves the two agree at
   the 8, 16, 32 and 64 GB classes.
   Provenance of each rung, written into the docstring: the 15 GiB rung is the window this
   repository already declares for that class of host
   (`docs/guides/local-models-ollama.md:24,83`, `deploy/helm/vibey/values.yaml:129`); the
   23 GiB rung is **measured** — 2026-09-22, 24 GB Apple Silicon, `host-tuning.toml`; the
   46 GiB rung is the model's own published window, not a measurement here — 14.93 GB is 62%
   of 24 GiB, so for the same footprint to sit under 40% of RAM the host needs about 37 GiB,
   and 46 is the next conventional size above it. Raise a rung only on a measurement, never on
   a hunch and never because a lane failed for some other reason (`host-tuning.toml:59-62`).
5. **The chosen window is the smallest of the three bounds, then the floor.** The bounds are
   considered in the order `("host", host_ceiling)`, `("workload", workload_ceiling)`,
   `("ceiling", declared ceiling)` and the first minimum wins — a tie names **host**, because a
   tie means the constraint that cannot be relaxed by measuring more is the one to report. If
   the winner is below `floor`, the answer is `floor` and `bound_by` is `"floor"`.
6. **An operator's `window` beats every measurement (12.c).** When `local_context.window` is
   set, that is the answer and `bound_by` is `"operator"` — it is **not** clamped by the
   ladder, the ceiling or even the floor. An override that is not honoured is not an override.
   The measured ceilings are still carried on the result so the operator can see what the
   measurement said, and when the declared window is above what the host measured, that gap is
   added to `notes`.
7. **Pressure is reported as measured numbers, never as a verdict.** When the host is measured,
   `notes` gains one entry per breached threshold, each naming the measured value *and* the
   declared threshold: `available_percent < min_available_percent`, and
   `swap_used_percent > max_swap_used_percent`. Nothing about pressure changes the chosen
   number — shrinking a reservation does not un-swap a running server — it changes what a
   person is told. An unmeasured host gets no pressure notes at all.
8. **New `[local_context]` table**, loaded into `VibeyConfig.local_context` as a frozen
   `LocalContextConfig`, every key validated at load and named in the error:
   - `window: int | None = None` — the operator override; positive when present.
   - `observed_peak_tokens: int = 49118` — the recorded peak (`host-tuning.toml:46`); ≥ 0.
   - `headroom_percent: int = 33` — ≥ 0 (`host-tuning.toml:52`: 16,418 tokens, 33% over).
   - `floor: int = 8192`, `ceiling: int = 131072` — both positive, `floor <= ceiling`.
   - `min_available_percent: int = 20` — 0..100 (`host-tuning.toml:68`).
   - `max_swap_used_percent: int = 75` — 0..100 (`host-tuning.toml:69`, `0.75`).
   - `ladder: tuple[ContextRung, ...]` — the three rungs above, sorted ascending by
     `min_ram_gib` at load. Both TOML spellings parse, because both are a list of tables:
     `[[local_context.ladder]]` and
     `ladder = [{ min_ram_gib = 15, max_window = 32768 }]`. An **explicitly empty** list is an
     operator's declaration that there is no ladder (every host falls to `floor`), not a
     missing one; only an absent key takes the default.
9. **The reader works on both default operating systems and degrades everywhere else.**
   - Linux (`sys.platform.startswith("linux")`): parse `/proc/meminfo`, whose values are in
     **kB meaning 1024 bytes**. `MemTotal`, `MemAvailable`, `SwapTotal`, `SwapFree`;
     `swap_used = SwapTotal - SwapFree`. `source = "/proc/meminfo"`.
   - macOS (`sys.platform == "darwin"`): `sysctl -n hw.memsize` (bytes), `sysctl -n
     vm.swapusage` (`total = 18432.00M  used = 17042.19M  free = 1389.81M`, where `M` is
     **MiB**), and `vm_stat` for `(free + inactive + speculative) * page_size`.
     `source = "sysctl + vm_stat"`.
   - **The page size is read from `vm_stat`'s own header, never assumed.** Its first line is
     `Mach Virtual Memory Statistics: (page size of 16384 bytes)` on Apple Silicon and
     `4096` on Intel. This is not hypothetical: the bench record itself reads as though 4096
     had been assumed — `pages_free = 4569 # ~18 MB genuinely free`
     (`host-tuning.toml:22`), which is 4569 x 4096; the machine it was taken on reports a
     16384-byte page, so that line understates free memory four-fold. Assume the page size and
     you ship that error.
   - Any other platform, an `OSError` reading `/proc/meminfo`, a `/proc/meminfo` with no
     `MemTotal`, a refused or unparseable `sysctl -n hw.memsize`: an **unmeasured**
     `HostMemory` whose `source` says which, and **never** an exception. `vibey doctor` must
     not die because a host cannot be read. This is not theoretical either: inside a sandbox
     `sysctl` returns non-zero with `sysctl: sysctl fmt -1 1024 1: Operation not permitted`
     while `vm_stat` succeeds, so the refusal path is the one a developer hits first.
   - A refused `vm_stat` or `vm.swapusage` on a host whose `hw.memsize` *did* answer leaves
     that field at 0 and keeps `measured` true: a partial reading is better than none, and the
     zeroes are inert by behaviour 1.
10. **`vibey doctor` reports it, with its evidence.** One line in the same compact style as the
    engine lines (`cli/main.py:1299`) and the postgres line (`cli/main.py:279`), followed by
    one `  detail: ` line per note — the shape `cli/main.py:1301-1302` already uses. It is
    printed unconditionally, immediately before the postgres line, for every non-`--cluster`
    run. Unconditional on purpose: it costs one branch fewer, and the sovereign DESIGN and
    DECOMPOSE providers talk to Ollama whether or not the `qwenloop` *engine* switch is on.
11. **Nothing else changes behaviour.** No existing constant is deleted, no existing default
    moves, and no engine yet runs at the chosen number. This lane makes vibey able to say what
    the window should be and why; the lanes that make each consumer *use* it are named under
    "Out of scope".

## Where to change

### Create `src/vibey/domain/interfaces/local_context_interface.py`
Provenance header copied from `src/vibey/domain/interfaces/plan_interface.py:1`. Interfaces
declare and never consume (ADR-0016), so this file must **not** import
`vibey.domain.local_context`; it imports `typing` and nothing else.

```python
# Made with ❤️ by [Vibey](...), Developed by [Adam Matthew Steinberger](...).
"""The contracts for sizing a local engine's context window from host evidence."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class HostMemoryInterface(Protocol):
    """What one host has, as read by infrastructure and judged by the domain."""

    @property
    def total_bytes(self) -> int: ...

    @property
    def available_bytes(self) -> int: ...

    @property
    def swap_total_bytes(self) -> int: ...

    @property
    def swap_used_bytes(self) -> int: ...

    @property
    def source(self) -> str:
        """Where these numbers came from, or why there are none."""
        ...

    @property
    def measured(self) -> bool:
        """False when nothing could be read; a number nobody measured is not a zero."""
        ...

    @property
    def total_gib(self) -> int: ...

    @property
    def available_percent(self) -> int: ...

    @property
    def swap_used_percent(self) -> int: ...


@runtime_checkable
class ContextWindowChoiceInterface(Protocol):
    """A context window with the evidence that chose it -- never a bare number (10.f)."""

    @property
    def tokens(self) -> int: ...

    @property
    def bound_by(self) -> str:
        """Which constraint decided: operator, host, workload, ceiling or floor."""
        ...

    @property
    def host(self) -> HostMemoryInterface: ...

    @property
    def host_ceiling(self) -> int: ...

    @property
    def workload_ceiling(self) -> int: ...

    @property
    def rung_gib(self) -> int:
        """The ladder rung that applied; 0 when the host sat below every declared rung."""
        ...

    @property
    def observed_peak_tokens(self) -> int: ...

    @property
    def headroom_percent(self) -> int: ...

    @property
    def ceiling(self) -> int: ...

    @property
    def notes(self) -> tuple[str, ...]:
        """Every measured fact that qualifies this number; empty means nothing to say."""
        ...

    def report(self) -> str:
        """One line naming the number's evidence: the host, the rung, the peak, the
        headroom, the ceiling, and where the host facts were read."""
        ...


@runtime_checkable
class HostContextPolicyInterface(Protocol):
    """Chooses a context window from host facts and a declared workload. Pure."""

    def choose(self, memory: HostMemoryInterface) -> ContextWindowChoiceInterface:
        """The window this host may carry, with its evidence. Never raises: an
        unmeasured host is answered, not refused."""
        ...
```

### Create `src/vibey/domain/local_context.py`
Provenance header copied from `src/vibey/domain/rotation.py:1`. Pure: no I/O, no async, no
clock, no network — `tests/domain/test_domain_purity.py` walks the AST of every file under
`domain/` and this one is no exception. It imports `vibey.domain.config` and its own interface
module; nothing else.

```python
from dataclasses import dataclass

from vibey.domain.config import LocalContextConfig
from vibey.domain.interfaces.local_context_interface import (
    ContextWindowChoiceInterface,
    HostMemoryInterface,
)

#: One binary gibibyte. The ladder is declared in GiB because that is the unit both
#: `/proc/meminfo` and `sysctl hw.memsize` report in, once converted.
GIB = 1024**3


@dataclass(frozen=True, slots=True)
class HostMemory:
    """Implements `HostMemoryInterface`. What one host has, as a value.

    Every derived percentage is integer and returns 0 when its denominator is 0: a host
    with no swap file (a common Arch install) is not a host that is swapping, and a host
    nobody could read is not a host at 0% free -- `measured` is how you tell those apart.
    """

    total_bytes: int = 0
    available_bytes: int = 0
    swap_total_bytes: int = 0
    swap_used_bytes: int = 0
    source: str = "unmeasured"

    @property
    def measured(self) -> bool:
        return self.total_bytes > 0

    @property
    def total_gib(self) -> int:
        return self.total_bytes // GIB

    @property
    def available_percent(self) -> int:
        if self.total_bytes <= 0:
            return 0
        return self.available_bytes * 100 // self.total_bytes

    @property
    def swap_used_percent(self) -> int:
        if self.swap_total_bytes <= 0:
            return 0
        return self.swap_used_bytes * 100 // self.swap_total_bytes


@dataclass(frozen=True, slots=True)
class ContextWindowChoice:
    """Implements `ContextWindowChoiceInterface`. A value, like `rotation.Selection`
    (rotation.py:61-64): the number AND everything that chose it, so `doctor` can report a
    number with its evidence rather than a number (10.f)."""

    tokens: int
    bound_by: str
    host: HostMemoryInterface
    host_ceiling: int
    workload_ceiling: int
    rung_gib: int
    observed_peak_tokens: int
    headroom_percent: int
    ceiling: int
    notes: tuple[str, ...] = ()

    def report(self) -> str:
        if not self.host.measured:
            where = f"host memory not measured ({self.host.source})"
        else:
            rung = f"the {self.rung_gib} GiB rung" if self.rung_gib else "below every rung"
            where = (
                f"{self.host.total_gib} GiB host -> {self.host_ceiling} ({rung}, "
                f"read from {self.host.source})"
            )
        return (
            f"{where}; peak {self.observed_peak_tokens} +{self.headroom_percent}% -> "
            f"{self.workload_ceiling}; ceiling {self.ceiling}"
        )


class HostContextPolicy:
    """Implements `HostContextPolicyInterface`.

    A class, not a function (ADR-0016): it carries the operator's declaration and there is
    a second implementation waiting -- the lane that feeds `observed_peak_tokens` from the
    ledger's own turns (8.g) substitutes at this seam rather than editing this rule.
    """

    def __init__(self, config: LocalContextConfig) -> None:
        self._config = config

    def choose(self, memory: HostMemoryInterface) -> ContextWindowChoice:
        cfg = self._config
        host_ceiling, rung_gib = self._rung(memory)
        workload_ceiling = self._workload_ceiling()
        notes = self._pressure(memory)
        if cfg.window is not None:
            # 12.c: an override that is clamped is not an override. Not the ladder, not
            # the ceiling and not even the floor narrows it -- but the measurement is
            # still carried, and the gap is said out loud.
            if cfg.window > min(host_ceiling, workload_ceiling):
                notes = (
                    *notes,
                    f"the declared window {cfg.window} is above what the evidence "
                    f"supports (host {host_ceiling}, workload {workload_ceiling})",
                )
            return self._choice(cfg.window, "operator", memory, host_ceiling,
                                workload_ceiling, rung_gib, notes)
        bounds: tuple[tuple[str, int], ...] = (
            ("host", host_ceiling),
            ("workload", workload_ceiling),
            ("ceiling", cfg.ceiling),
        )
        # `min` returns the FIRST minimum, so a tie names the host: a tie means the
        # constraint you cannot relax by measuring more is the one to report.
        bound_by, tokens = min(bounds, key=lambda bound: bound[1])
        if tokens < cfg.floor:
            bound_by, tokens = "floor", cfg.floor
        return self._choice(tokens, bound_by, memory, host_ceiling, workload_ceiling,
                            rung_gib, notes)
```

Plus three private helpers and one assembler, each with the docstring the behaviour above
gives it:

- `_rung(self, memory) -> tuple[int, int]` — `(self._config.ceiling, 0)` when
  `not memory.measured`; otherwise start at `(self._config.floor, 0)` and walk the
  ascending ladder, keeping the last rung whose `min_ram_gib <= memory.total_gib`.
- `_workload_ceiling(self) -> int` — `self._config.ceiling` when
  `observed_peak_tokens <= 0`; otherwise
  `wanted = observed_peak_tokens * (100 + headroom_percent) // 100` and
  `return 1 << (wanted - 1).bit_length()` (which maps an exact power of two to itself).
- `_pressure(self, memory) -> tuple[str, ...]` — `()` when not measured; otherwise one
  string per breach, each naming the measured value and the declared threshold.
- `_choice(...) -> ContextWindowChoice` — one place that fills the ten fields, so the two
  return paths in `choose` cannot drift.

`__all__ = ["GIB", "ContextWindowChoice", "HostContextPolicy", "HostMemory"]`.

### Edit `src/vibey/domain/config.py`
- Beside `DEFAULT_LOCAL_CONTEXT_WINDOW` (`config.py:35`), add the defaults as named
  constants with their provenance in a comment pointing at
  `docs/plans/qwenstorm-3.0.0/bench/host-tuning.toml`:
  `DEFAULT_OBSERVED_PEAK_TOKENS = 49_118`, `DEFAULT_CONTEXT_HEADROOM_PERCENT = 33`,
  `DEFAULT_CONTEXT_FLOOR = 8_192`, `DEFAULT_CONTEXT_CEILING = 131_072`,
  `DEFAULT_MIN_AVAILABLE_PERCENT = 20`, `DEFAULT_MAX_SWAP_USED_PERCENT = 75`.
- Beside `_optional` (`config.py:357-363`), one new module-level helper — module-level for
  the same reason `_optional` is, and say so at the definition: it validates one scalar,
  has no state, and has no second implementation to substitute.
  ```python
  def _bounded_int(
      table: dict[str, Any],
      key: str,
      path: str,
      default: int,
      *,
      minimum: int,
      maximum: int | None = None,
  ) -> int:
      """One integer key inside its declared bounds. `isinstance(True, int)` is True in
      Python, so `bool` is rejected explicitly, the way `config.py:99` already does."""
      value = _optional(table, key, path, int, default)
      if isinstance(value, bool) or value < minimum or (maximum is not None and value > maximum):
          bound = f"between {minimum} and {maximum}" if maximum is not None else f"at least {minimum}"
          raise ConfigError(path, f"must be an integer {bound}")
      return value
  ```
- Two new frozen dataclasses, placed immediately after `QwenloopConfig` (`config.py:184-191`),
  whose shape and `from_table` classmethod they copy from `ClaudeloopLocalConfig`
  (`config.py:69-107`):
  ```python
  @dataclass(frozen=True, slots=True)
  class ContextRung:
      """One rung of the ladder: a host at least this big may carry this window."""

      min_ram_gib: int
      max_window: int

      @classmethod
      def from_table(cls, table: dict[str, Any], path: str) -> "ContextRung": ...


  #: The shipped ladder. Declared JUST BELOW each nominal size on purpose: Linux's
  #: `MemTotal` excludes firmware-reserved memory, so a 16 GB machine reports about
  #: 15.3 GiB while the same hardware on macOS reports `hw.memsize` = exactly 16 GiB. A
  #: rung at 16 would put the two default operating systems (8.h) on different rungs for
  #: identical hardware. Provenance: 15 -> what this repository already declares for that
  #: class of host (docs/guides/local-models-ollama.md:24,83); 23 -> MEASURED on 2026-09-22,
  #: 24 GB Apple Silicon (docs/plans/qwenstorm-3.0.0/bench/host-tuning.toml); 46 -> the
  #: model's own published window, not a measurement here. Raise a rung on a measurement
  #: and on nothing else (host-tuning.toml:59-62).
  DEFAULT_CONTEXT_LADDER: tuple[ContextRung, ...] = (
      ContextRung(min_ram_gib=15, max_window=32_768),
      ContextRung(min_ram_gib=23, max_window=65_536),
      ContextRung(min_ram_gib=46, max_window=131_072),
  )


  @dataclass(frozen=True, slots=True)
  class LocalContextConfig:
      """`[local_context]`: the window a local engine runs at, chosen from evidence.

      Keys rather than constants (12.c): a 96 GiB Arch workstation and a 16 GB laptop are
      not the same machine, and this package may not decide for either. `window` is the
      operator's override and beats every measurement, unconditionally --  the ladder,
      the ceiling and the floor all stand aside for it, because an override that is
      clamped is not an override.
      """

      window: int | None = None
      observed_peak_tokens: int = DEFAULT_OBSERVED_PEAK_TOKENS
      headroom_percent: int = DEFAULT_CONTEXT_HEADROOM_PERCENT
      floor: int = DEFAULT_CONTEXT_FLOOR
      ceiling: int = DEFAULT_CONTEXT_CEILING
      min_available_percent: int = DEFAULT_MIN_AVAILABLE_PERCENT
      max_swap_used_percent: int = DEFAULT_MAX_SWAP_USED_PERCENT
      ladder: tuple[ContextRung, ...] = DEFAULT_CONTEXT_LADDER

      @classmethod
      def from_table(cls, table: dict[str, Any], path: str) -> "LocalContextConfig": ...
  ```
  `LocalContextConfig.from_table` validates each key with `_bounded_int` per behaviour 8,
  raises `ConfigError(f"{path}.floor", "must not exceed local_context.ceiling")` when
  `floor > ceiling`, reads `raw = table.get("ladder")`, keeps `DEFAULT_CONTEXT_LADDER` only
  when `raw is None`, refuses a `ladder` that is not a list and a rung that is not a table
  (`ConfigError(f"{path}.ladder", "must be a list of tables")`), and returns the rungs
  `tuple(sorted(..., key=lambda rung: rung.min_ram_gib))` so the policy can walk them
  ascending without sorting.
- `VibeyConfig`: add `local_context: LocalContextConfig = field(default_factory=LocalContextConfig)`
  directly after `qwenloop: QwenloopConfig = ...` (`config.py:330`).
- Between `_parse_qwenloop` (`config.py:505-531`) and `_parse_tracker` (`config.py:533`), add:
  ```python
  def _parse_local_context(data: dict[str, Any]) -> LocalContextConfig:
      table = _optional(data, "local_context", "local_context", dict, {})
      return LocalContextConfig.from_table(table, "local_context")
  ```
  and add `local_context=_parse_local_context(data),` to the `return VibeyConfig(...)` call
  immediately after `qwenloop=_parse_qwenloop(data),` (`config.py:707`).

### Edit `src/vibey/domain/interfaces/__init__.py`
Add the import block in isort order — `ledger_tier_interface`, then
`local_context_interface`, then `phase_timing_interface`:
```python
from vibey.domain.interfaces.local_context_interface import (
    ContextWindowChoiceInterface,
    HostContextPolicyInterface,
    HostMemoryInterface,
)
```
and add `"ContextWindowChoiceInterface"`, `"HostContextPolicyInterface"` and
`"HostMemoryInterface"` to `__all__`, each in the position the surrounding list already
sorts by.

### Create `src/vibey/infrastructure/interfaces/host_memory_interface.py`
Copy `src/vibey/infrastructure/interfaces/postgres_interface.py` exactly — including its
`from __future__ import annotations` and its `TYPE_CHECKING` import of the concrete result
type, which is how that file names `PostgresStatus` without importing the module that makes
it.

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.local_context import HostMemory


@runtime_checkable
class HostMemoryReaderInterface(Protocol):
    """Reads this host's memory facts. macOS and Arch Linux both (8.h)."""

    def read(self) -> HostMemory:
        """What this host has. Never raises: a host that cannot be read comes back
        unmeasured, with `source` saying why, because `vibey doctor` must not die
        because `sysctl` was refused."""
        ...
```

### Edit `src/vibey/infrastructure/interfaces/__init__.py`
Add, in isort order between the `cluster_preflight_interface` and `logging_interface` blocks:
```python
from vibey.infrastructure.interfaces.host_memory_interface import HostMemoryReaderInterface
```
and `"HostMemoryReaderInterface"` to `__all__`, after `"EngineAuthCheckInterface"`.

### Create `src/vibey/infrastructure/host_memory.py`
Provenance header copied from `src/vibey/infrastructure/postgres.py:1`. This file is the
mirror of `postgres.py`: same `sys.platform` seam, same fixed-argv `subprocess.run` with the
same `# nosec` comments, same "a failed command is a result, not an exception" rule.

```python
from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argv, never shell=True
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vibey.domain.local_context import HostMemory

MEMINFO_PATH: Final = "/proc/meminfo"
_COMMAND_TIMEOUT_SECONDS: Final = 10.0
_KIB: Final = 1024
_MIB: Final = 1024 * 1024

# `/proc/meminfo` reports in kB meaning 1024 bytes, not 1000.
_MEMINFO = re.compile(r"^(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+(\d+) kB", re.MULTILINE)
# `sysctl -n vm.swapusage` -> `total = 18432.00M  used = 17042.19M  free = 1389.81M`
# where M is MiB.
_SWAPUSAGE = re.compile(r"total\s*=\s*([\d.]+)M\s+used\s*=\s*([\d.]+)M")
# vm_stat's own header: `(page size of 16384 bytes)` on Apple Silicon, 4096 on Intel.
_VM_STAT_PAGE_SIZE = re.compile(r"page size of (\d+) bytes")
_VM_STAT_PAGES = re.compile(r"^Pages (?:free|inactive|speculative):\s+(\d+)\.", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class HostCommandResult:
    """The small subprocess result shape this reader needs.

    Shaped like `postgres.PostgresCommandResult` (postgres.py:78-88) and deliberately not
    imported from it: that type is named for its own module and its runner `_run_command`
    is private. `infrastructure/process/` has no generic fixed-argv synchronous runner to
    reuse (`reaper.py` is async kill-and-reap, `python_env.py` reads the environment), so
    there is nothing of ours to dogfood here yet (10.e). Converging the two behind one
    `infrastructure/process` seam is worth doing and is not this lane.
    """

    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[tuple[str, ...]], HostCommandResult]
TextReader = Callable[[str], str]


def _run_command(argv: tuple[str, ...]) -> HostCommandResult: ...
def _read_text(path: str) -> str: ...


class HostMemoryReader:
    """Implements `HostMemoryReaderInterface`."""

    def __init__(
        self,
        *,
        platform: str | None = None,
        command_runner: CommandRunner | None = None,
        read_text: TextReader | None = None,
    ) -> None:
        # Seams, not settings: a test hands in a double instead of patching `subprocess`
        # or the filesystem (ADR-0016), the way `postgres.PostgresLocalService.__init__`
        # (postgres.py:145-158) takes its `command_runner`, `which` and `platform`.
        self._platform = platform if platform is not None else sys.platform
        self._run = command_runner if command_runner is not None else _run_command
        self._read_text = read_text if read_text is not None else _read_text

    def read(self) -> HostMemory: ...
```

`_run_command` copies `postgres.py:115-131` verbatim apart from the result type: fixed argv,
`capture_output=True`, `check=False`, `text=True`, `timeout=_COMMAND_TIMEOUT_SECONDS`, and
`except (OSError, subprocess.TimeoutExpired) as exc: return HostCommandResult(returncode=1,
stderr=str(exc))`, carrying the same `# nosec B603 B607 - fixed argv, never shell=True`.
`_read_text` is `return Path(path).read_text(encoding="utf-8")`.

`read()` dispatches per behaviour 9 to `_linux()` or `_macos()`, and otherwise returns
`HostMemory(source=f"unmeasured: no reader for {self._platform!r}")` **without running any
command**. `_macos()` uses three helpers — `_sysctl_int(name) -> int | None`,
`_vm_stat_available() -> int` and `_swapusage() -> tuple[int, int]` — each returning a
neutral value on a non-zero exit or an output that does not parse, never raising. There is
no third OS branch beyond the fallback, and **nothing anywhere in this file touches swap
configuration**: macOS has no swap knob to touch (behaviour rationale above), and Linux's is
not vibey's to set.

`__all__ = ["MEMINFO_PATH", "CommandRunner", "HostCommandResult", "HostMemoryReader", "TextReader"]`.

### Edit `src/vibey/cli/main.py`
- Imports, in isort order. `from vibey.domain.config import ConfigError, LocalContextConfig,
  parse_toml_string` goes **before** `from vibey.domain.engine import EngineId`
  (`main.py:39`); `from vibey.domain.local_context import ContextWindowChoice,
  HostContextPolicy` goes between `ledger_query` (`main.py:48`) and `phase` (`main.py:49`);
  `from vibey.infrastructure.host_memory import HostMemoryReader` goes between
  `engines.scripted_visual` (`main.py:75`) and `logging` (`main.py:76`).
- Two module-level functions, placed immediately after `_postgres_status_line`
  (`main.py:268-279`), which is the precedent for both: a renderer the CLI tests call
  directly (`tests/cli/test_operational_commands.py:911-922`), so the branchy part is not
  trapped inside an async command body.
  `ConfigError` is added to the `from vibey.domain.config import ...` line for the
  `except` clause below.
  ```python
  def _local_context_from_toml(root: Path | None = None) -> LocalContextConfig:
      """The `[local_context]` table `vibey doctor` reads: `./vibey.toml`, and the
      declared defaults when the file is missing or malformed -- the same rule
      `LocalEngineSettings.from_toml` follows (local_engines.py:88-97), so one broken
      file reports defaults rather than taking the health check down."""
      try:
          data = parse_toml_string(((root or Path.cwd()) / "vibey.toml").read_text(encoding="utf-8"))
          table = data.get("local_context")
          return LocalContextConfig.from_table(
              dict(table) if isinstance(table, dict) else {}, "local_context"
          )
      except (OSError, ValueError, ConfigError):
          return LocalContextConfig()


  def _local_context_lines(choice: ContextWindowChoice) -> tuple[str, ...]:
      """The doctor lines for the chosen local context window: the number, then the
      evidence behind it, then every measured note -- the same compact shape as the
      engine lines above (main.py:1299-1302). A number without its evidence is not a
      report (10.f)."""
      state = f"{choice.tokens} tokens"
      bound = f"bound by {choice.bound_by}"
      lines = [f"local context   {state:<14} {bound:<22} {choice.report()}"]
      lines.extend(f"  detail: {note}" for note in choice.notes)
      return tuple(lines)
  ```
- `run_doctor`, immediately before `typer.echo(_postgres_status_line(local_postgres_status))`
  (`main.py:1341`), at the same indentation:
  ```python
        choice = HostContextPolicy(_local_context_from_toml()).choose(HostMemoryReader().read())
        for line in _local_context_lines(choice):
            typer.echo(line)
  ```
  Nothing else in `doctor` changes, and `run_cluster_doctor` is not touched: an in-cluster
  preflight answers about the cluster, not about the node's page cache.

## Acceptance criteria
- [ ] `uv run python -c 'import vibey.domain.local_context, vibey.domain.interfaces.local_context_interface, vibey.infrastructure.host_memory, vibey.infrastructure.interfaces.host_memory_interface, vibey.cli.main; print("ok")'` prints `ok`.
- [ ] `grep -c "vibey.domain.local_context" src/vibey/domain/interfaces/local_context_interface.py` prints 0 — an interface declares, it never consumes (ADR-0016).
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_domain_purity.py` passes: `domain/local_context.py` opens no file, runs no process and reads no clock.
- [ ] `uv run lint-imports` passes, including `domain-independence` and `interfaces-declare-only`.
- [ ] On the shipped defaults with a healthy 24 GiB host, `choose(...)` returns `tokens == 65536`, `bound_by == "host"`, `rung_gib == 23`, `workload_ceiling == 65536` (the `python -c` line in the check block prints exactly this).
- [ ] On the shipped defaults with a healthy 64 GiB host, `host_ceiling == 131072` and `tokens == 65536` with `bound_by == "workload"` — more RAM buys no window the workload has never used.
- [ ] `HostMemoryReader().read()` on this machine returns without raising and `source` is one of `/proc/meminfo`, `sysctl + vm_stat`, or a string beginning `unmeasured:`.
- [ ] `vibey doctor` prints a line beginning `local context   ` and that line contains the token count, `bound by `, and the evidence.
- [ ] `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests` followed by the three `coverage report --fail-under=100` lines passes for `domain/`, `infrastructure/` and `cli/`.
- [ ] `uv run mypy --strict src/vibey`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run bandit -q -r src/vibey` are all clean.
- [ ] `git diff --name-only` lists exactly: `src/vibey/domain/config.py`, `src/vibey/domain/local_context.py`, `src/vibey/domain/interfaces/__init__.py`, `src/vibey/domain/interfaces/local_context_interface.py`, `src/vibey/infrastructure/host_memory.py`, `src/vibey/infrastructure/interfaces/__init__.py`, `src/vibey/infrastructure/interfaces/host_memory_interface.py`, `src/vibey/cli/main.py`, `tests/domain/test_local_context.py`, `tests/domain/test_config.py`, `tests/infrastructure/test_host_memory.py`, `tests/cli/test_operational_commands.py`. Nothing under `docs/`, `deploy/`, `.github/`, and no `CHANGELOG.md`.
- [ ] `git diff --stat` shows `tests/domain/test_config.py` and `tests/cli/test_operational_commands.py` only GAINING lines.
- [ ] `grep -rn "swapon\|swappiness\|dynamic_pager" src/vibey` prints nothing.

## Tests to write first (TDD)
Write these first, watch them fail, then make them pass. `domain/`, `infrastructure/` and
`cli/` each fail the build under 100% **branch** coverage, so an implementation without its
tests cannot merge and the lane has achieved nothing.

Seams are substituted by construction, never by patching an import: `HostMemoryReader` takes
`platform`, `command_runner` and `read_text`, and `HostContextPolicy` takes its config. The
**one** exception is the module-level `_run_command`, whose only seam is stdlib
`subprocess.run` itself — the outermost process boundary, not a declared port — and the
repository already covers its twin exactly this way at
`tests/infrastructure/test_postgres_local.py:569-593`. Copy that shape and nothing else from it.

### New file `tests/domain/test_local_context.py`
Provenance header copied from `tests/domain/test_config.py:1`. Module constants:
`GIB = 1024**3`; `PRESSED = HostMemory(total_bytes=24 * GIB, available_bytes=2 * GIB,
swap_total_bytes=18 * GIB, swap_used_bytes=17 * GIB, source="sysctl + vm_stat")` (the machine
`host-tuning.toml` was taken on); `HEALTHY = HostMemory(total_bytes=24 * GIB,
available_bytes=12 * GIB, swap_total_bytes=18 * GIB, swap_used_bytes=1 * GIB,
source="/proc/meminfo")`; and a helper `def host(gib: int) -> HostMemory` returning a healthy
host of that many GiB (`available_bytes = gib * GIB // 2`, no swap used).

- `test_the_measured_host_and_the_measured_workload_both_land_on_65536` — the whole lane in
  one assertion. `HostContextPolicy(LocalContextConfig()).choose(HEALTHY)` has
  `tokens == 65536`, `bound_by == "host"` (the documented tie rule), `host_ceiling == 65536`,
  `rung_gib == 23`, `workload_ceiling == 65536`, `observed_peak_tokens == 49118`,
  `ceiling == 131072`, `notes == ()`.
- `test_a_smaller_host_is_held_to_its_rung` — `choose(host(16))` gives `tokens == 32768`,
  `rung_gib == 15`, `bound_by == "host"`.
- `test_a_larger_host_is_held_by_the_workload_it_actually_has` — `choose(host(64))` gives
  `host_ceiling == 131072`, `rung_gib == 46`, `workload_ceiling == 65536`, `tokens == 65536`,
  `bound_by == "workload"`. Docstring: 131072 bought nothing and cost roughly half the
  machine (`host-tuning.toml:53-58`); RAM is permission, not a reason.
- `test_a_host_below_every_rung_gets_the_floor` — `choose(host(8))` gives `host_ceiling == 8192`,
  `rung_gib == 0`, `tokens == 8192`, `bound_by == "host"`, and
  `"below every rung" in choice.report()`.
- `test_the_two_default_operating_systems_land_on_the_same_rung` — 8.h, parametrized over
  `(linux_total_bytes, macos_total_bytes)`:
  `(8_047_012 * 1024, 8 * GIB)`, `(16_207_664 * 1024, 16 * GIB)`,
  `(32_695_636 * 1024, 32 * GIB)`, `(65_608_432 * 1024, 64 * GIB)` — real `MemTotal` values
  against the `hw.memsize` the same hardware reports. Build both hosts healthy — half their
  total available, no swap used — so the only thing the comparison can be measuring is the
  rung. For each pair assert the two choices agree on `tokens`, `host_ceiling` and
  `rung_gib`, and that the 64 GB pair agrees on `host_ceiling == 131072` (the rung itself,
  not just the window the workload then caps to 65536). Docstring: `MemTotal` excludes
  firmware-reserved memory, so the Linux side reports 7, 15, 31 and 62 GiB against macOS's 8,
  16, 32 and 64 — which is exactly why the shipped rungs are 15/23/46 and not 16/24/48.
- `test_the_floor_is_never_crossed_downwards` — `LocalContextConfig(floor=32768,
  observed_peak_tokens=1000)` with `host(16)` gives `bound_by == "floor"`, `tokens == 32768`,
  and `workload_ceiling == 2048`.
- `test_an_unmeasured_host_is_not_lowered_by_evidence_nobody_has` — 10.f.
  `choose(HostMemory(source="unmeasured: no reader for 'win32'"))` gives
  `host.measured is False`, `host_ceiling == 131072`, `rung_gib == 0`, `tokens == 65536`,
  `bound_by == "workload"`, `notes == ()`, and
  `"host memory not measured" in choice.report()`.
- `test_an_operator_window_beats_every_measurement` — 12.c.
  `LocalContextConfig(window=131072)` on `PRESSED` gives `tokens == 131072`,
  `bound_by == "operator"`, `host_ceiling == 65536` still reported, and exactly one note
  matching `"the declared window 131072 is above what the evidence supports"`.
- `test_an_operator_window_is_not_even_clamped_by_the_floor` —
  `LocalContextConfig(window=4096).choose(host(64))` gives `tokens == 4096` and
  `bound_by == "operator"`. An override that is clamped is not an override.
- `test_an_operator_window_inside_the_evidence_earns_no_note` —
  `LocalContextConfig(window=16384).choose(HEALTHY)` gives `tokens == 16384`,
  `bound_by == "operator"` and `notes == ()` (the other arc of that branch).
- `test_an_unmeasured_workload_leaves_the_ceiling_in_charge` —
  `LocalContextConfig(observed_peak_tokens=0).choose(host(64))` gives
  `workload_ceiling == 131072`, `tokens == 131072`, `bound_by == "host"`.
- `test_the_headroom_is_a_declared_percentage_over_the_recorded_peak` — parametrized
  `(peak, headroom, expected_workload_ceiling)`: `(49118, 33, 65536)` — the recorded peak,
  which is the shipped default; `(49118, 0, 65536)`; `(24637, 33, 32768)`;
  `(24638, 33, 32768)` — `24638 * 133 // 100` is exactly 32768, and a value that is already
  a power of two maps to itself; `(24639, 33, 65536)` — the first peak that crosses, one
  token later. Assert `workload_ceiling` against a 64 GiB host so the ladder cannot mask it.
- `test_memory_pressure_is_reported_as_measured_numbers_not_a_verdict` — `choose(PRESSED)`
  has `len(notes) == 2`; the first contains `"8%"`, `"24 GiB"` and `"20%"`; the second
  contains `"94%"` and `"75%"`; and `tokens == 65536` — unchanged, because shrinking a
  reservation does not un-swap a running server.
- `test_a_host_with_no_swap_is_not_a_host_that_is_swapping` — `HostMemory(total_bytes=32 * GIB,
  available_bytes=20 * GIB, swap_total_bytes=0, swap_used_bytes=0, source="/proc/meminfo")`
  has `swap_used_percent == 0` and yields `notes == ()`. A common Arch install (8.h).
- `test_an_unmeasured_host_reports_zero_rather_than_dividing_by_zero` — `HostMemory()` has
  `measured is False`, `total_gib == 0`, `available_percent == 0`, `swap_used_percent == 0`,
  `source == "unmeasured"`.
- `test_the_choice_reports_the_number_and_the_evidence_behind_it` — 10.f. For
  `HostContextPolicy(LocalContextConfig()).choose(HEALTHY).report()`, assert every one of
  `"24 GiB"`, `"65536"`, `"23 GiB rung"`, `"49118"`, `"+33%"`, `"131072"` and
  `"/proc/meminfo"` is in the string.
- `test_the_policy_and_its_values_answer_their_declared_interfaces` — ADR-0016, the shape
  `tests/infrastructure/engines/test_local_engines.py:11-14` already uses:
  `isinstance(HEALTHY, HostMemoryInterface)`,
  `isinstance(HostContextPolicy(LocalContextConfig()), HostContextPolicyInterface)`, and
  `isinstance(choice, ContextWindowChoiceInterface)`, importing all three from
  `vibey.domain.interfaces`.
- `test_an_operator_who_declares_no_ladder_gets_no_ladder` —
  `LocalContextConfig(ladder=()).choose(host(64))` gives `host_ceiling == 8192` and
  `rung_gib == 0`: an empty ladder is a declaration, not a missing one.

### New file `tests/infrastructure/test_host_memory.py`
Provenance header copied from `tests/infrastructure/test_postgres_local.py:1`. A module-level
fake for the command seam — a class, registered by construction, never a monkeypatch:

```python
class _Commands:
    """The command seam, answered from a table. `calls` is the evidence that a platform
    branch ran nothing at all."""

    def __init__(self, table: dict[tuple[str, ...], HostCommandResult]) -> None:
        self._table = table
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: tuple[str, ...]) -> HostCommandResult:
        self.calls.append(argv)
        return self._table.get(argv, HostCommandResult(returncode=1, stderr="not configured"))
```

Module constants: `MEMINFO` — a realistic `/proc/meminfo` excerpt with `MemTotal: 32695636 kB`,
`MemFree: 1234567 kB`, `MemAvailable: 20000000 kB`, `SwapTotal: 8388604 kB`,
`SwapFree: 4194304 kB`; `VM_STAT` — the real header
`Mach Virtual Memory Statistics: (page size of 16384 bytes)` followed by
`Pages free: 3930.`, `Pages active: 51564.`, `Pages inactive: 45792.`,
`Pages speculative: 4749.`, `Pages wired down: 1261486.`; `SWAPUSAGE = "total = 18432.00M
used = 17042.19M  free = 1389.81M  (encrypted)\n"`; and `MIB = 1024 * 1024`.

- `test_linux_reads_proc_meminfo` — `HostMemoryReader(platform="linux",
  read_text=lambda _path: MEMINFO)` gives `total_bytes == 32695636 * 1024`,
  `available_bytes == 20000000 * 1024`, `swap_total_bytes == 8388604 * 1024`,
  `swap_used_bytes == (8388604 - 4194304) * 1024`, `source == "/proc/meminfo"`,
  `measured is True`, and `total_gib == 31`. Also assert the reader was handed
  `MEMINFO_PATH` by capturing the path the fake was called with.
- `test_a_linux_host_with_no_swap_reads_zero` — `MemTotal` plus `SwapTotal: 0 kB` and
  `SwapFree: 0 kB` gives `swap_total_bytes == 0` and `swap_used_bytes == 0`.
- `test_a_proc_meminfo_that_cannot_be_read_is_unmeasured_rather_than_a_crash` — a `read_text`
  that raises `OSError("no such file")` gives `measured is False` and `"meminfo"` in `source`.
- `test_a_proc_meminfo_without_memtotal_is_unmeasured` — `read_text` returning
  `"Committed_AS:   12 kB\n"` gives `measured is False` and `"MemTotal"` in `source`.
- `test_macos_reads_sysctl_and_vm_stat` — a `_Commands` answering
  `("sysctl", "-n", "hw.memsize")` with `"25769803776\n"`, `("sysctl", "-n", "vm.swapusage")`
  with `SWAPUSAGE` and `("vm_stat",)` with `VM_STAT`. Assert
  `total_bytes == 25769803776`, `total_gib == 24`,
  `available_bytes == (3930 + 45792 + 4749) * 16384` — free + inactive + speculative, and
  **not** active or wired — `swap_total_bytes == 18432 * MIB` (the `M` is MiB),
  `round(swap_used_bytes / MIB, 2) == 17042.19`, and `source == "sysctl + vm_stat"`.
- `test_the_page_size_comes_from_vm_stat_not_from_an_assumption` — the same table with the
  header rewritten to `page size of 4096 bytes` gives
  `available_bytes == (3930 + 45792 + 4749) * 4096`. Docstring: Apple Silicon reports 16384
  and Intel 4096; `host-tuning.toml:22` reads as though 4096 had been assumed on a machine
  that reports 16384, which understates free memory four-fold. Assume it and you ship that.
- `test_a_refused_sysctl_is_unmeasured_rather_than_a_crash` — `hw.memsize` answered with
  `HostCommandResult(returncode=1, stderr="sysctl: sysctl fmt -1 1024 1: Operation not
  permitted")` gives `measured is False` and `"hw.memsize"` in `source`. This is the sandbox
  case, and it is the first one a developer hits.
- `test_unparseable_sysctl_output_is_unmeasured` — `hw.memsize` answered `"banana\n"` with
  `returncode=0` gives `measured is False`.
- `test_a_refused_vm_stat_leaves_available_at_zero_without_losing_the_total` — `vm_stat`
  answered with `returncode=1` gives `measured is True`, `total_gib == 24`,
  `available_bytes == 0`. A partial reading beats none.
- `test_vm_stat_without_its_header_reports_zero_available` — `VM_STAT` with the first line
  removed gives `available_bytes == 0`.
- `test_a_refused_swapusage_reports_no_swap` — `vm.swapusage` answered `returncode=1` gives
  `swap_total_bytes == 0` and `swap_used_bytes == 0`.
- `test_swapusage_that_does_not_parse_reports_no_swap` — `vm.swapusage` answered
  `"nonsense\n"` with `returncode=0` gives `swap_total_bytes == 0`.
- `test_an_unsupported_platform_is_unmeasured_and_runs_nothing` — `platform="win32"` with a
  `_Commands({})` gives `measured is False`, `"win32" in source`, and `commands.calls == []`.
- `test_the_reader_answers_its_declared_interface` —
  `isinstance(HostMemoryReader(platform="win32"), HostMemoryReaderInterface)`, importing the
  protocol from `vibey.infrastructure.interfaces`.
- `test_the_text_reader_reads_a_real_file(tmp_path)` — writes `"MemTotal: 1 kB\n"` to
  `tmp_path / "meminfo"` and asserts `_read_text(str(...))` returns it; covers the default
  seam without needing `/proc` to exist.
- `test_the_subprocess_runner_handles_success_oserror_and_timeout(monkeypatch)` — the only
  `monkeypatch` in this lane, and only because the thing substituted is stdlib
  `subprocess.run`. Copy the three-arc shape of
  `tests/infrastructure/test_postgres_local.py:569-593` exactly: a `CompletedProcess` with
  `stdout="ok"`, then a callable raising `OSError`, then one raising
  `subprocess.TimeoutExpired`, asserting `stdout == "ok"` and `returncode == 1` twice.

### Appended to `tests/domain/test_config.py` (append only; never rewrite this file)
Extend the existing `from vibey.domain.config import ...` line with
`DEFAULT_CONTEXT_LADDER`, `ContextRung` and `LocalContextConfig`.

- `test_the_local_context_table_round_trips` — `load_config_from_string` over a document with
  `[project] name = "x"`, a full `[local_context]` table (`window = 12345`,
  `observed_peak_tokens = 100`, `headroom_percent = 10`, `floor = 1024`, `ceiling = 200000`,
  `min_available_percent = 5`, `max_swap_used_percent = 90`) and two
  `[[local_context.ladder]]` rungs; assert all eight fields, including
  `ladder == (ContextRung(4, 4096), ContextRung(8, 16384))`.
- `test_the_ladder_also_parses_as_an_inline_array_of_tables` — the same two rungs written
  `ladder = [{ min_ram_gib = 4, max_window = 4096 }, { min_ram_gib = 8, max_window = 16384 }]`
  produce the identical tuple. Both spellings are a list of tables in TOML.
- `test_the_ladder_is_sorted_by_the_host_size_it_names` — rungs declared 46, 15, 23 come back
  ascending, so the policy may walk them without sorting.
- `test_an_omitted_table_is_the_measured_default` — `load_config_from_string('[project]\nname
  = "x"\n').local_context == LocalContextConfig()`, and `LocalContextConfig().ladder ==
  DEFAULT_CONTEXT_LADDER`, and that ladder is exactly
  `(ContextRung(15, 32768), ContextRung(23, 65536), ContextRung(46, 131072))` — the rungs are
  pinned so a later edit cannot move them back to 16/24/48 without a failing test and a
  measurement.
- `test_an_empty_ladder_is_an_operators_declaration_not_a_missing_one` — `ladder = []` gives
  `ladder == ()`, not the default.
- `test_an_invalid_local_context_table_is_refused` — parametrized `(table, match)` in the
  style of `test_an_invalid_claudeloop_local_table_is_refused` (`test_config.py:312-323`):
  `("window = 0", "at least 1")`, `("window = true", "at least 1")`,
  `("floor = 0", "at least 1")`, `("ceiling = -1", "at least 1")`,
  `("observed_peak_tokens = -1", "at least 0")`,
  `("min_available_percent = 101", "between 0 and 100")`,
  `("max_swap_used_percent = -1", "between 0 and 100")`,
  `('headroom_percent = "33"', "must be a int")`,
  `("floor = 70000\nceiling = 60000", "must not exceed")`,
  `('ladder = "wide"', "must be a list of tables")`,
  `("ladder = [1]", "must be a list of tables")`,
  `("ladder = [{ min_ram_gib = 0, max_window = 4096 }]", "at least 1")`.
  Each raises `ConfigError` whose message matches, and the raised `ConfigError.path` begins
  `local_context`.

### Appended to `tests/cli/test_operational_commands.py` (append only; never rewrite this file)
- `test_local_context_line_reports_the_number_and_its_evidence` — build a
  `ContextWindowChoice` directly (no CLI), call `_local_context_lines`, assert exactly one
  line, that it starts `"local context   "`, and that it contains `"65536 tokens"`,
  `"bound by workload"` and the text of `choice.report()`.
- `test_local_context_lines_carry_every_measured_note_as_a_detail_line` — a choice with two
  notes yields three lines and lines 2 and 3 each start `"  detail: "`.
- `test_doctor_reports_the_local_context_window` — `runner.invoke(app, ["doctor", "--engine",
  "claudeloop"])` exits 0 and `"local context"` is in `res.output`.
- `test_the_local_context_table_is_read_from_the_working_directory(tmp_path)` — write
  `'[local_context]\nwindow = 12345\n'` to `tmp_path / "vibey.toml"`; assert
  `_local_context_from_toml(tmp_path).window == 12345`.
- `test_a_missing_vibey_toml_leaves_the_local_context_defaults_standing(tmp_path)` —
  `_local_context_from_toml(tmp_path) == LocalContextConfig()`.
- `test_a_broken_vibey_toml_leaves_the_local_context_defaults_standing(tmp_path)` — write
  `"not toml ["`; the defaults stand rather than the health check dying.
- `test_a_local_context_table_that_fails_validation_leaves_the_defaults_standing(tmp_path)` —
  write `'[local_context]\nfloor = 0\n'`; the defaults stand.
- `test_a_local_context_key_that_is_not_a_table_is_ignored(tmp_path)` — write
  `'local_context = "wide"\n'`; the defaults stand (the `isinstance(table, dict)` arc).

## Checks the lane must run (all must pass)
There is no shell: each line below is one `create_subprocess_exec(*argv)` from the worktree
root. Run every line and read every exit code.

```
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run python -c 'import vibey.domain.local_context, vibey.domain.interfaces.local_context_interface, vibey.infrastructure.host_memory, vibey.infrastructure.interfaces.host_memory_interface, vibey.cli.main; print("imports ok")'
uv run pytest -q -p no:cacheprovider tests/domain/test_local_context.py
uv run pytest -q -p no:cacheprovider tests/domain/test_config.py
uv run pytest -q -p no:cacheprovider tests/domain/test_domain_purity.py
uv run pytest -q -p no:cacheprovider tests/infrastructure/test_host_memory.py
uv run pytest -q -p no:cacheprovider tests/cli/test_operational_commands.py
uv run python -c 'from vibey.domain.config import LocalContextConfig; from vibey.domain.local_context import GIB, HostContextPolicy, HostMemory; h = HostMemory(total_bytes=24 * GIB, available_bytes=12 * GIB, swap_total_bytes=18 * GIB, swap_used_bytes=GIB, source="check"); c = HostContextPolicy(LocalContextConfig()).choose(h); print(c.tokens, c.bound_by, c.rung_gib, c.report()); assert (c.tokens, c.bound_by, c.rung_gib) == (65536, "host", 23), c'
uv run python -c 'from vibey.domain.config import LocalContextConfig; from vibey.domain.local_context import GIB, HostContextPolicy, HostMemory; h = HostMemory(total_bytes=64 * GIB, available_bytes=32 * GIB, source="check"); c = HostContextPolicy(LocalContextConfig()).choose(h); print(c.tokens, c.bound_by, c.host_ceiling); assert (c.tokens, c.bound_by, c.host_ceiling) == (65536, "workload", 131072), c'
uv run python -c 'from vibey.infrastructure.host_memory import HostMemoryReader; m = HostMemoryReader().read(); print(m.source, m.total_gib, m.available_percent, m.swap_used_percent)'
uv run python -c 'from typer.testing import CliRunner; from vibey.cli.main import app; r = CliRunner().invoke(app, ["doctor", "--engine", "claudeloop"]); print(r.output); assert r.exit_code == 0, r.output; assert "local context" in r.output, r.output'
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests
uv run coverage report --include=src/vibey/domain/* --fail-under=100
uv run coverage report --include=src/vibey/application/* --fail-under=100
uv run coverage report --include=src/vibey/infrastructure/* --fail-under=100
uv run coverage report --include=src/vibey/cli/* --fail-under=100
git status --porcelain docs deploy .github
git diff --stat
```

Notes on that block, each of which has cost a lane before:

- **`coverage report --include=...` needs no shell.** `coverage` globs the pattern itself, so
  `--include=src/vibey/domain/*` is correct as one literal argv element. Do not quote it.
- **Run the four `coverage report` lines only after the single full `pytest --cov` line
  above them**, and never run two coverage runs at once: concurrent runs clobber `.coverage`
  and the failure looks like a missing branch that is in fact covered.
- `git status --porcelain docs deploy .github` must print **nothing**. This lane records the
  measurement in code and touches no document; `docs/reference/configuration.md` and
  `docs/guides/local-models-ollama.md` owe a `[local_context]` row and the docs wave owns
  them.
- The `HostMemoryReader().read()` line is a **smoke check, not an assertion about this
  machine**: it must return, and it may legitimately print `unmeasured: sysctl ...` inside a
  sandbox that refuses `sysctl`. A traceback there is a failure; an `unmeasured:` source is
  not.
- 8.h: run the whole block on macOS **and** on Arch Linux. Every test above is
  platform-independent by construction (the reader's platform is a constructor argument), so
  a difference between the two runs is a real defect, not an environment quirk.

### The formatter trap
`ruff format --check` and `ruff check` both run at `line-length = 100`, `target-version =
"py312"` (`pyproject.toml:272-274`). Keep every line at or under 100 columns, bind long
expressions to a local before asserting, use one argument per line with a trailing comma in
multi-line calls, and never a backslash continuation. Format once when the edits are done —
`uv run ruff format src/vibey tests` — and then run the block.

### Two traps specific to this lane
1. **`isinstance(True, int)` is `True`.** `window = true` in TOML must be refused, and only
   the explicit `isinstance(value, bool)` guard in `_bounded_int` refuses it. `config.py:99`
   already carries the same guard for the same reason.
2. **Do not delete or change any existing constant.** `DEFAULT_LOCAL_CONTEXT_WINDOW`
   (`config.py:35`), `QwenloopConfig.context_window` (`config.py:191`),
   `OllamaChatClient.CONTEXT_CEILING` (`ollama_chat.py:86`) and the two
   `descriptors.py:285,313` windows all stay exactly as they are. Touching one changes what
   engines actually run at and breaks tests this lane does not own; wiring them up is the
   next lane's work, listed below.

## Out of scope
Every item here is a named follow-up, not an omission.

- **Wiring the chosen number into the consumers.** `OllamaChatClient.CONTEXT_CEILING` becoming
  a constructor parameter fed from `LocalContextConfig`; `QwenloopConfig.context_window` and
  `ClaudeloopLocalConfig.context_window` defaulting from the policy; the qwenloop endpoint
  overlay (`local_engines.py:180-188`) carrying it; and `OLLAMA_CONTEXT_LENGTH` in
  `deploy/helm/vibey/templates/ollama.yaml:98` and
  `deploy/helm/golden/ollama-gpu-qwenloop.yaml:111`. Each has its own blast radius and its own
  tests. This lane deliberately computes and reports, and changes no engine's behaviour.
- **Feeding `observed_peak_tokens` from the ledger (8.g).** The 49,118 shipped here is a
  *recorded* measurement of 838 real turns, declared as a key; the lane that reads
  `input_tokens + output_tokens` off the live ledger and keeps that key current is the one
  that closes 8.g's "continuously and in real time". `HostContextPolicy` is a class with an
  interface so that lane substitutes at the seam instead of editing this rule.
- **An `enabled` switch on `[local_context]`.** Nothing consumes the number yet, so a switch
  would be a branch with no meaning. It belongs with the wiring lane.
- **The `loops-*` workstream's `ModelDeclaration(context_window=...)`, `min_context` and
  `MODEL_CONTEXT_DEFAULTS`** (`docs/plans/qwenstorm-3.0.0/specs/loops-residency-policy.md`,
  `loops-config-loop-services.md`, `loops-router-routing.md`). Those describe what a *model*
  declares; this describes what a *host* can carry. They meet in the wiring lane, not here.
  Do not edit them and do not import from them.
- **Any swap configuration, on any operating system.** macOS has no swap knob to turn
  (`host-tuning.toml:12-17`) and Linux's is the operator's, not vibey's. No `swapon`, no
  `swappiness`, no `dynamic_pager`, no advice printed about any of them.
- **GPU and unified-memory accounting.** The ladder is host RAM. A discrete-VRAM Arch box is a
  different memory model and a different ladder; it needs its own measurement first (8.g).
- **`tui/`, the worker, the queue, the chart, and every engine adapter.** Untouched.
- **Documentation.** `docs/reference/configuration.md` owes a `[local_context]` row and
  `docs/guides/local-models-ollama.md` owes the ladder; the docs wave owns both. Do not edit
  `CHANGELOG.md`, `docs/`, ADRs, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `deploy/` or any skill
  tree.
- Do not push, open pull requests, or change git remotes. Commit locally with
  `feat(engines): choose the local context window from measured host memory`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

**Depends on:** none
