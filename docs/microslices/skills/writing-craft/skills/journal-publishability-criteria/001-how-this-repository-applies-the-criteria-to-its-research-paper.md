---
id: skill-how-this-repository-applies-the-criteria-to-its-research-paper-27c7c8e2e6
purpose: how this repository applies the criteria to its research paper
source: src/vibey_tools/skills/plugins/writing-craft/skills/journal-publishability-criteria/SKILL.md
requires: []
links: ["skill-1-the-editor-s-first-screen-desk-rejection-5a2ebc8108"]
---

## How this repository applies the criteria to its research paper

The criteria below split into two halves, and this repository holds `docs/paper.md` to both of them every time it tries to publish an update.

The **mechanical criteria** are checked by `python scripts/paper_publishability.py check` (thresholds, headings, phrase lists and paths declared in `scripts/paper_publishability.toml`). It runs on every pull request through `tests/meta/test_paper_publishability.py`, and again in `release-surfaces.yml` before the paper is rendered and published, as the `[documentation] paper_gate` declared in `.vibey-gh.toml`; a paper that fails it is not published. The required checks are: a contribution statement in the abstract and the introduction (§1); an abstract within the venue's length (§1); a `## Declarations` section before the references carrying *Data and code availability*, *Use of generative AI*, *Authorship, funding and competing interests* and *Reporting guidelines and registrations* (§4, §5); an AI disclosure that names its tools and says the author remains responsible (§4); no AI tool among the authors in `CITATION.cff`, and a citation title that matches the paper's (§4); references that each carry a year and a locator (§1, the checklist); a named evidence cutoff; no pending markers; no self-promotion in place of a stated contribution (§1); every mention of a preregistration naming where the registration is (§4, §5); and every reported confidence interval carrying both its bounds (§2). An ORCID iD and a DOI or preprint identifier are recommended and reported, never failed.

The **judgment criteria** are a rubric that a reviewer, human or the review lane, applies to any change to `docs/paper.md`, reporting each unmet criterion as a finding: scope and novelty, stated and judged from the abstract, introduction and conclusion alone (§1); methodological soundness (§2); claims the evidence can carry (§2); estimates reported with intervals and null results reported (§2); reproducible methods (§5); and text recycled from the repository's own documentation cited as such (§4). `python scripts/paper_publishability.py report` prints this rubric beside the mechanical rows, and `--json` carries it under `reviewer`. The review lane loads this skill (`writing-craft@vibey-skills` in `[pr_automation] plugins`) so the rubric is in front of it when the diff touches the paper.

Computer-science systems papers run through conference review, not the health-science journal pipeline, so the EQUATOR table below does not apply to this paper; the paper says so in its Declarations under *Reporting guidelines and registrations* rather than claiming a checklist it did not complete.

---
