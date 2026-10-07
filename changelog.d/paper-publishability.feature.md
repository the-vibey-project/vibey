* **paper:** `scripts/paper_publishability.py` judges `docs/paper.md` and `CITATION.cff` against
  the mechanical half of the `journal-publishability-criteria` skill -- a contribution statement,
  the abstract's length, the four declarations, an AI disclosure that names its tools and no AI
  author, a citation record that agrees with the paper, references with a year and a locator, a
  named evidence cutoff, no pending markers, no self-promotion, located registrations and
  complete intervals -- with every threshold, heading, phrase and path declared in
  `scripts/paper_publishability.toml`, and prints the reviewer's rubric for the judgment half
  beside the rows. `report` prints the evaluation and `check` exits 1 naming each failure and
  its line. It gates every pull request (`tests/meta/test_paper_publishability.py`) and every
  publication (`release-surfaces.yml`, as the `[documentation] paper_gate` the repository
  declares), and the review lane now loads `writing-craft@vibey-skills` and applies the rubric
  to any change to the paper.
