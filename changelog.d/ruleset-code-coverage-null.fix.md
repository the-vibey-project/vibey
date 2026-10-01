* **gh:** the declared 100% coverage floor reaches the forge, and the "Repository profile"
  workflow goes green again. Every reconcile since #1277 was refused with `Invalid property
  /rules/6: data matches no possible input (HTTP 422)`: vibey-gh sent the `code_coverage`
  rule with `"max_coverage_drop": null`, copied from how GitHub *echoes* an unset threshold,
  but GitHub's rule input types both thresholds as plain numbers (OpenAPI
  `repository-rule-code-coverage`), so the null matched no rule type and the whole ruleset
  PUT failed, leaving the floor off both declared rulesets. An unset threshold is now left
  out of the payload, and a threshold set by hand that nobody declared is still reported as
  drift. `vibey-gh rulesets --dry-run` no longer prints "reconciled" when it applied nothing.
