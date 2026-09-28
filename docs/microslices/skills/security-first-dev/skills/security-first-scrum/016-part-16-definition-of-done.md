---
id: skill-part-16-definition-of-done-d3955a0697
purpose: part 16 definition of done
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-15-agentic-execution-protocol-9-steps-ae97cf7181"]
links: ["skill-part-17-anti-patterns-never-do-these-3768dcb030"]
---

## PART 16: DEFINITION OF DONE

A feature is DONE only when ALL of the following are true.

### Code Completeness

- [ ] Spec / acceptance criteria written and referenced (with Security Considerations section)
- [ ] Interface(s) defined and documented (with security preconditions)
- [ ] No TODOs, stubs, or unimplemented bodies in production code paths
- [ ] All public APIs have complete XML doc comments / docstrings

### Testing

- [ ] Contract / schema tests passing
- [ ] Unit tests passing — all happy paths + all error paths
- [ ] Security unit tests passing — positive + adversarial for every security control
- [ ] Integration tests passing (if I/O involved)
- [ ] Coverage >= 80% overall; >= 85% new code; >= 90% service layer; **100% security-critical paths**

### Security

- [ ] Zero Semgrep findings (medium+) on all modified files
- [ ] Zero secrets in code, tests, or commit history
- [ ] All endpoints have explicit `[Authorize(Policy = "...")]` or documented `[AllowAnonymous]`
- [ ] Input validated with FluentValidation / model binding on all public inputs
- [ ] All Azure service connections use Managed Identity
- [ ] BOLA / resource ownership check implemented for all user-owned data endpoints
- [ ] Rate limiting applied to all public-facing endpoints
- [ ] Security headers middleware in place
- [ ] No PII or credentials in log messages
- [ ] Swagger blocked in non-Development environments

### Code Quality

- [ ] Zero linting errors
- [ ] Zero type errors (nullable enabled in .NET; strict in TypeScript; mypy strict in Python)
- [ ] Structured logging at all required events
- [ ] Error handling follows the retry / no-retry policy
- [ ] Mock/fake implementation updated to match interface changes

### Process

- [ ] CI pipeline green — all security gates passed
- [ ] Branch protection requirements satisfied (linked work item, reviewer, all checks)
- [ ] Commit messages follow Conventional Commits format
- [ ] PR description references the sprint story and security considerations

---
