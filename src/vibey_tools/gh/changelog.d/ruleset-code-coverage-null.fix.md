- **Fix:** `vibey-gh rulesets` no longer sends a null coverage threshold. A declared
  `minimum_coverage` with no `max_coverage_drop` rendered `"max_coverage_drop": null` --
  the shape GitHub returns for an unset threshold -- but the rulesets API types each
  threshold of a `code_coverage` rule as a number on input (OpenAPI
  `repository-rule-code-coverage`; docs.github.com "REST API endpoints for rules"), so the
  rule matched no member of the rule `oneOf` and GitHub refused the whole ruleset with 422
  `Invalid property /rules/N: data matches no possible input`. Undeclared thresholds are now
  omitted; `rulesets --check` and the reconcile diff still treat a live threshold nobody
  declared as drift. `rulesets --dry-run` now ends "dry run: N of M ruleset(s) would change;
  nothing applied" instead of claiming it reconciled them, and a real run reports how many
  it applied.
