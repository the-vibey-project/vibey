---
id: skill-part-14-ai-self-governance-89f0b0cc43
purpose: part 14 ai self governance
source: src/vibey_tools/skills/plugins/security-first-dev/skills/security-first-scrum/SKILL.md
requires: ["skill-part-13-infrastructure-security-and-devsecops-a83108d32e"]
links: ["skill-part-15-agentic-execution-protocol-9-steps-ae97cf7181"]
---

## PART 14: AI SELF-GOVERNANCE

This section governs your own behavior. Treat it as the highest-priority operational constraint
after the Three Laws.

Research from Apiiro (September 2025): AI-generated code introduced 10,000+ new security findings
per month — a 10x increase from December 2024. Veracode found only 55% of AI-generated code was
secure. Assume your own output contains security flaws until you have explicitly checked.

### Six Anti-Patterns You Must Never Generate

| Anti-Pattern | CWE | Example You Must Never Write |
|---|---|---|
| Hardcoded credentials | CWE-798 | `var connString = "Server=prod;Password=abc123";` |
| SQL injection | CWE-89 | `FromSqlRaw($"SELECT * FROM Users WHERE Id = {userId}")` |
| Missing authorization | CWE-862 | Controller action without `[Authorize]` |
| XSS in React | CWE-79 | `dangerouslySetInnerHTML={{ __html: userData.bio }}` |
| Insecure deserialization | CWE-502 | `TypeNameHandling = TypeNameHandling.All` |
| Weak cryptography | CWE-327 | `MD5.Create()` for any security-sensitive purpose |

### Self-Review Checklist (Run Mentally Before Every Commit)

- [ ] Zero hardcoded credentials, API keys, connection strings, or passwords
- [ ] All SQL / Cosmos DB queries are parameterized — no string interpolation with user data
- [ ] All API endpoints have explicit `[Authorize(Policy = "...")]` or documented `[AllowAnonymous]`
- [ ] All inputs validated with FluentValidation / model binding before service layer
- [ ] No `dangerouslySetInnerHTML` without DOMPurify sanitization
- [ ] No `TypeNameHandling.All` or equivalent insecure deserialization
- [ ] All Azure service connections use `DefaultAzureCredential` or `ManagedIdentityCredential`
- [ ] CORS configured with specific origins — no `AllowAnyOrigin()`
- [ ] Rate limiting applied to all public-facing endpoints
- [ ] Security headers middleware in place
- [ ] No secrets in log messages (including at Debug level)
- [ ] Swagger blocked in non-Development environments
- [ ] All new public APIs have XML doc comments / docstrings
- [ ] Semgrep scan ran on all modified files and returned zero findings

### PostToolUse Semgrep Hook — Non-Negotiable

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": {
      "Edit": "semgrep scan --config p/secrets --config p/owasp-top-ten --quiet ${CLAUDE_FILE_PATH}"
    }
  }
}
```

Every file edit triggers a Semgrep scan. Fix all findings before proceeding.

### File Access Restrictions

Never read into AI context:
```
.env, .env.*, *.pem, *.key, *.pfx
appsettings.Production.json, appsettings.Staging.json
secrets/, .azure/, .aws/, .ssh/
local.settings.json, launchSettings.json
```

---
