---
id: skill-part-15-agentic-execution-protocol-9-steps-ae97cf7181
purpose: part 15 agentic execution protocol 9 steps
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-14-ai-self-governance-89f0b0cc43"]
links: ["skill-part-16-definition-of-done-d3955a0697"]
---

## PART 15: AGENTIC EXECUTION PROTOCOL (9 STEPS)

Follow this exact sequence for every task. The codebase must be passing after every step.

```
STEP 1 — UNDERSTAND
  Read spec / acceptance criteria and Security Considerations section.
  Identify architectural layers and security controls required.
  State the threat model before writing any code.

STEP 2 — INTERFACE FIRST
  Define or verify the C# interface (or Python ABC).
  Define input/output contracts. Include security preconditions in docstring.

STEP 3 — TEST (RED)
  Write unit tests: happy path, 401, 403, BOLA 403, input rejection, failure modes.
  Run tests. Confirm they fail for the right reason.

STEP 4 — IMPLEMENT (GREEN)
  Minimum secure code to pass the tests.
  Apply every security control from the Security Considerations section.

STEP 5 — SECURITY SCAN
  semgrep scan --config p/secrets --config p/owasp-top-ten <modified_files>
  Zero findings required. Fix any before proceeding.

STEP 6 — QUALITY GATE
  format → lint → type-check → test (with coverage). All must pass.

STEP 7 — REFACTOR
  Improve clarity without changing behavior. Re-run quality gate + security scan.

STEP 8 — INTEGRATION
  Write / run integration tests if external I/O is involved.
  Verify Managed Identity — no connection strings with keys.

STEP 9 — REVIEW CHECKLIST
  All tests pass. Coverage >= threshold (100% on security-critical paths).
  Zero linting or type errors. Zero Semgrep findings.
  Zero secrets in code or tests. XML doc comments complete.
  Required log events present. Error handling follows retry / no-retry policy.
  No TODOs without ticket ID. Conventional Commits message. Self-review complete.
```

---
