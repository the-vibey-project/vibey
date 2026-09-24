## Title
feat(install): a sysfs GPU probe names the display GPUs' vendors, behind a declared seam

## Why
`gap-install-ollama-gpu-1` chooses the Arch Ollama package from the GPU vendors. This lane
reads them on Linux without a subprocess: each PCI device under `/sys/bus/pci/devices/*/` has
a `class` file (display controllers are `0x03xxxx`) and a `vendor` file (`0x10de` is NVIDIA,
`0x1002` is AMD, `0x8086` is Intel). The root path is injected, so tests use a temporary tree,
never the host's `/sys` (9.b; the fakes standard).

## Required behaviour
1. New module `src/vibey/infrastructure/gpu_probe.py` (provenance header):
   - `class SysfsGpuProbe` with `__init__(self, *, root: Path = Path("/"))` and
     `vendors(self) -> tuple[GpuVendor, ...]`:
     - For each directory in `sorted((root / "sys/bus/pci/devices").glob("*"))`, read `class`
       and `vendor`, stripped and lowercased.
     - Skip a device whose class does not start with `0x03`, or whose files are missing or
       unreadable (`OSError` is caught per device).
     - Map `0x10de` to NVIDIA, `0x1002` to AMD and `0x8086` to INTEL; any other display vendor
       is UNKNOWN.
     - Return the distinct vendors in first-seen order. With no display device, return `(GpuVendor.NONE,)`.
       With no `sys/bus/pci/devices` directory (macOS, or a container without sysfs), return
       `(GpuVendor.UNKNOWN,)`.
2. New interface `src/vibey/infrastructure/interfaces/gpu_probe_interface.py`: a
   `@runtime_checkable` Protocol `GpuProbeInterface` with `vendors`. Export it from
   `src/vibey/infrastructure/interfaces/__init__.py`.
3. Add an in-memory fake `FixedGpuProbe(vendors)` to `tests/fakes/`, in the module the fakes
   registry uses for installer seams: read `tests/fakes/registry.py`, which `fakes-registry`
   created. Add `GpuProbeInterface` to `DRIVER_SEAMS` with that fake registered, following the
   registry's rules (`specs/fakes-registry.md:88-91`).

## Where to change
- New: `src/vibey/infrastructure/gpu_probe.py`, `src/vibey/infrastructure/interfaces/gpu_probe_interface.py`.
- `src/vibey/infrastructure/interfaces/__init__.py` (export).
- `tests/fakes/` (the fake) and `tests/fakes/registry.py` (the registration).
- New test `tests/infrastructure/test_gpu_probe.py`, which builds sysfs trees under `tmp_path`.

## Acceptance criteria
- [ ] A tree with one NVIDIA display device (`class 0x030000`, `vendor 0x10de`) gives `(NVIDIA,)`.
- [ ] An NVIDIA device plus an Intel display device gives `(NVIDIA, INTEL)`, in sorted-path order.
- [ ] A non-display NVIDIA device (`class 0x020000`) is ignored, giving `(NONE,)`.
- [ ] An unreadable `vendor` file is skipped, and no exception escapes.
- [ ] No sysfs directory gives `(UNKNOWN,)`.
- [ ] The fakes registry meta-tests pass with the new seam.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/test_gpu_probe.py`:
- `test_one_nvidia_display`
- `test_multiple_display_vendors_in_order`
- `test_non_display_devices_are_ignored`
- `test_unreadable_device_is_skipped`
- `test_no_sysfs_is_unknown`
- `test_probe_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_gpu_probe.py tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Using the probe (`-3`), macOS (no probe needed), and docs.

Commit as `feat(install): a sysfs GPU vendor probe`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
