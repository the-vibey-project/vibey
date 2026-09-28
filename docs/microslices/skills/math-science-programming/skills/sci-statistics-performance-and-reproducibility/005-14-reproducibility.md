---
id: skill-14-reproducibility-793922bcb7
purpose: 14 reproducibility
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-statistics-performance-and-reproducibility/SKILL.md
requires: ["skill-13-testing-and-verification-a58519bdbd"]
links: []
---

## §14. Reproducibility

**[VERSIONED in the specifics, DURABLE in the practice.]**

**⚠️ The context is a genuine, measured crisis.** Surveys indicate **over 70% of
researchers have failed to reproduce another group's findings**; large-scale replication
efforts in life sciences report **only 10–25% of studies or effects reproducing robustly**;
and Nature's 2026 reproducibility special issue reported a multi-team meta-research effort
finding **only about half of published behavioural-science claims could be replicated.**
⚠️ **Computational reproducibility — same data, same code, same answer — is the easiest
kind, and it still frequently fails.**

**[DURABLE] What actually to do, roughly in order of payoff:**
1. **Version control everything**, code and analysis scripts alike. Non-negotiable.
2. **⚠️ Pin your environment exactly** — `conda-lock`, `uv.lock`, `renv`, Julia's
   `Manifest.toml`, or a container. **"requirements.txt with no versions" is not an
   environment.** Version drift is the single most common reproduction failure.
3. **Containerize** for anything you want reproducible in five years — Docker, Apptainer/
   Singularity (⚠️ **the HPC-friendly one**).
4. **⚠️ Record random seeds**, and record them *in the output*, not only in the script.
5. **Record the full provenance**: code version, data version, parameters, environment,
   hardware. ⚠️ **Ideally emit it into the result file itself**, so an orphaned output can
   still be traced.
6. **Separate code from data from results**; make the pipeline re-runnable end to end
   (Snakemake, Nextflow, Make).
7. **Archive with a DOI** — Zenodo, Software Heritage. **A GitHub URL is not an archive.**
8. **Publish the code.** ⚠️ **"Available on request" is empirically equivalent to
   unavailable.**

**⚠️ The numerical caveat specific to this domain**: **bitwise reproducibility across
different hardware, thread counts, BLAS implementations, or compiler flags is often
impossible** (§1.1 → `sci-floating-point-and-numerical-foundations`, §11). **The honest target is reproducibility to a stated tolerance,
with the tolerance justified** — not bit-identity. ⚠️ **Say which you're claiming.**
