---
id: skill-12-data-i-o-and-units-4adaa9e87b
purpose: 12 data i o and units
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-statistics-performance-and-reproducibility/SKILL.md
requires: ["skill-11-performance-and-parallelism-36e18650e2"]
links: ["skill-13-testing-and-verification-a58519bdbd"]
---

## §12. Data, I/O, and Units

**Formats**: **HDF5** (⚠️ **the scientific standard — hierarchical, chunked, compressed,
parallel-capable**), **NetCDF** (climate and geoscience, built on HDF5), **Zarr**
(⚠️ **cloud-native chunked arrays — increasingly the default for large distributed data**),
**Parquet** for tabular, **FITS** in astronomy. ⚠️ **CSV for anything large is a mistake**
— slow, untyped, and lossy on floats unless you're careful with precision.

⚠️ **Float round-tripping**: use `repr`/`%.17g` or a binary format. **Writing floats to
text at 6 digits and reading them back is silent data loss**, and it happens constantly.

**[DURABLE] Units and dimensional analysis.** ⚠️ **The Mars Climate Orbiter was lost to a
pound-force-seconds versus newton-seconds mismatch.** Use a units library — **Pint**
(Python), **Unitful.jl**, **boost::units** — or at absolute minimum **encode units in
variable names and check dimensional consistency in your tests** (§13). **Non-
dimensionalize your equations** where you can; it improves conditioning too (§1.2 → `sci-floating-point-and-numerical-foundations`).

---
