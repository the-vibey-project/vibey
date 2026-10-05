* **delegated approver:** `[[unattended_approval.lanes]]` lets the approver also approve the
  draft pull requests an automated lane opened (the weekly continuation lane), inside a bound
  the lane declares: a head-branch glob and a hierarchy of path tiers, first match wins, each
  with its own `max_files` and `paired_tests`. A file in no tier, or a head on a fork, refuses
  the whole pull request, and a lane only adds refusals: forbidden paths, author, green gates
  and the approver's independence still apply. No lanes, no change.
