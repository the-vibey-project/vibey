* **documentation:** `[documentation] paper_gate` declares a command that `release-surfaces.yml`
  runs from the repository root before the paper's figures are rendered and the paper is
  published, whenever `generate_paper` is on and `docs/paper.md` exists. A gate that fails
  fails the docs job, so the paper is not published; an empty gate, the default, is said out
  loud as a notice rather than passed over. The exact-head review prompt now asks the
  reviewer to apply the reviewer rubric of the `journal-publishability-criteria` skill to any
  change to `docs/paper.md` and to report each unmet criterion as a finding.
