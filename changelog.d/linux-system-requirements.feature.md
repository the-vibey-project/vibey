* **specs:** vibey's system requirements now cover Linux as a matrix: every distribution
  `[minimum_specs.linux]` declares (Ubuntu 24.04 and 26.04 LTS, Arch Linux, Fedora) on each
  declared architecture (x86_64, arm64), each cell measured inside that distribution's own
  container by `python scripts/minimum_specs.py cell`: the repository version behind each
  floor (kernel, Python, PostgreSQL, the desktop libraries), glibc against the newest
  `manylinux` floor of the installed wheels, the closure each package set adds as the
  package manager sizes it, and a cold uv install. The requirements are fitted, not read
  off one point (`scripts/requirements_math.py`): memory against context by least squares,
  M(c) = M0 + k*c, with R^2 and residuals; CPU generation against cores by Amdahl's law,
  with the recommended cores at the closed-form knee of dT/dn and the minimum solved
  against the minimum generation rate; and the append-only ledger's disk as the integral
  of its growth rate over a declared horizon. Thresholds, the headroom factor and the
  horizon are declared in TOML with their reasons. The weekly workflow runs every cell on a
  native GitHub-hosted runner of its architecture and folds them in with `merge --complete`,
  so a cell that reports nothing goes stale with the reason; an emulated cell keeps its
  sizes and refuses its timings; a cell with no image (Arch on arm64) is skipped, saying
  why. The host's weekly run now leaves the Linux figures alone instead of marking them
  stale, sweeps CPU-only generation across thread counts, and measures the database after
  one job. New generated blocks on the requirements page and in the paper.
