* **`vibey worker --auto-answer`:** a worker the operator starts with the flag answers its
  project's interview and retry gates itself, so an unattended local run is no longer stopped by
  gates that are not decisions. The DESIGN interview's questions get their own defaults;
  `escalation_exhausted` gets `{"max_attempts": 10}`, `verify_repair_exhausted` and
  `integrate_repair_exhausted` get `{"max_rounds": 6}`, and `delivery_exhausted` is delivered
  once more. A spending gate (`budget_exhausted`), `engine_misconfigured`, `research_evidence`,
  an approval and a review are never answered, and each sweep names the ones it left. The
  consent is the flag, for one worker and one project (`--all-projects` is refused) and nothing
  is stored, so silence is never read as consent (sub-doctrine 12.d). Answers stop after
  `--auto-answer-limit` (default 30), each is recorded on the ledger as `GateAnswered` by
  `auto-answer`, and a replayed sweep is a no-op. Before, the only way through was a shell loop
  around `vibey answer`.
