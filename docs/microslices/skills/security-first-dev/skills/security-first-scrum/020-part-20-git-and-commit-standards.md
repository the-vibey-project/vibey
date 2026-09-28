---
id: skill-part-20-git-and-commit-standards-495c54cdb6
purpose: part 20 git and commit standards
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-19-error-handling-standards-c0af1ae3f8"]
links: []
---

## PART 20: GIT AND COMMIT STANDARDS

### Conventional Commits Format

```
<type>(<scope>): <short summary>
Types: feat | fix | test | refactor | docs | chore | perf | ci | security
```

Use `security` type for any commit whose primary purpose is addressing a vulnerability.

### Commit Rules

- Every commit passes the pre-commit gate (format + lint + type-check + unit tests + semgrep)
- Test and implementation committed together — never implementation without test
- Each commit is atomic: one logical change, fully tested, not broken
- Never commit secrets — not even "temporary" or "test" commits. Git history is forever

### Branch Protection Requirements

Every PR into `main` requires:
- Linked work item (`AB#<WorkItemID>` in commit message)
- At least one reviewer (different from author)
- Passing build with all security gates
- Zero Semgrep / Gitleaks / Trivy findings
