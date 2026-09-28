---
id: skill-part-13-migration-execution-protocol-9-steps-5a5749d311
purpose: part 13 migration execution protocol 9 steps
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-12-phase-8-infrastructure-modernization-fcc20a52d3"]
links: ["skill-part-14-the-strangler-fig-pattern-10e8056681"]
---

## PART 13: MIGRATION EXECUTION PROTOCOL (9 STEPS)

For every migration task, follow this sequence. The codebase must be passing after every step.

```
STEP 1 — BASELINE
  Run existing tests. Record the pass/fail count.
  If tests were already failing: report to human before proceeding.
  Run the Phase 0 assessment grep commands relevant to this component.

STEP 2 — SCOPE CONFIRMATION
  State exactly what you are changing in this PR.
  State what you are NOT changing.
  If you discover P0 findings outside scope: log them; do not fix unilaterally.

STEP 3 — CHARACTERIZATION (if refactoring untested code)
  Write characterization tests that capture current behavior before changing anything.
  Run them. They must pass before you proceed.

STEP 4 — MAKE THE CHANGE
  Apply the migration change (one logical change per PR).
  Do not mix phases in a single PR.

STEP 5 — SECURITY TEST
  Write the adversarial test that proves the attack is now blocked.
  Write the positive test that proves the legitimate path still works.
  Run both. Both must pass.

STEP 6 — QUALITY GATE
  Run: format check → lint → type check → full test suite.
  Coverage must not decrease from baseline recorded in Step 1.

STEP 7 — SEMGREP SCAN
  semgrep scan --config p/secrets --config p/owasp-top-ten <changed_files>
  Zero medium+ findings. Fix any before committing.

STEP 8 — COMMIT
  Conventional Commits format. Use 'security' type for security fixes.
  One logical change per commit.
  No secrets: verify with: git diff --cached | grep -i "password\|secret\|key"

STEP 9 — DOCUMENT THE FINDING
  Update the migration log: what was found, what was fixed, what remains outstanding.
```

### Commit Message Conventions for Migration Work

```
# Security fixes
security(api): add BOLA ownership check to document retrieval
security(auth): migrate JWT validation to Microsoft.Identity.Web
security(config): replace Cosmos DB connection string with Managed Identity
security(react): migrate MSAL token storage from localStorage to sessionStorage

# Architecture migration
refactor(service): extract order business logic from OrdersController
refactor(repo): introduce IOrderRepository and Fake implementation
refactor(domain): define typed exception hierarchy

# Pipeline installation
ci: add Gitleaks secrets scan to PR gate
ci: add Semgrep OWASP SAST to PR gate
```

---
