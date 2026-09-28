---
id: skill-domain-5-ai-tool-security-claude-code-and-cursor-96de2a1c8a
purpose: domain 5 ai tool security claude code and cursor
source: src/vibey_tools/skills/plugins/security-first-dev/skills/cybersecurity-implementation/SKILL.md
requires: ["skill-domain-4-data-layer-security-cosmosdb-postgresql-databricks-156b32d5f8"]
links: ["skill-domain-6-azure-infrastructure-and-devsecops-c998879c2a"]
---

## DOMAIN 5: AI TOOL SECURITY (CLAUDE CODE AND CURSOR)

### Foundational — The Threat Model Every Team Must Understand

AI coding tools introduce five systemic risks:
1. **Data exfiltration** — code sent to external APIs may include secrets
2. **Prompt injection** via malicious context (doc strings, comments, file names)
3. **Model hallucination** of insecure patterns
4. **Intellectual property exposure**
5. **Compliance gaps** — 63% of breached organizations lacked AI tool governance

Research from Apiiro (September 2025): AI-generated code introduced **10,000+ new security
findings per month** — a 10x increase from December 2024. Veracode found only **55% of
AI-generated code was secure** across 100+ LLMs.

**Most common security anti-patterns AI tools generate:**
- **CWE-798 Hardcoded credentials:** `var connString = "Server=prod;Password=abc123";`
- **CWE-89 SQL injection:** `FromSqlRaw($"SELECT * FROM Users WHERE Id = {userId}")`
- **CWE-862 Missing authorization:** Controller actions without `[Authorize]`
- **CWE-79 XSS in React:** `dangerouslySetInnerHTML={{ __html: userData.bio }}`
- **CWE-502 Insecure deserialization:** `TypeNameHandling = TypeNameHandling.All`
- **CWE-327 Weak cryptography:** `MD5.Create()` for password hashing

Treat all AI-generated code as an untrusted pull request from a junior developer.

### Intermediate — Claude Code and Cursor Enterprise Configuration

**Claude Code settings hierarchy** (highest to lowest precedence):
1. Enterprise `managed-settings.json` (cannot be overridden by users)
2. CLI arguments
3. `.claude/settings.local.json`
4. `.claude/settings.json` (committed to repository)
5. User settings

**Enterprise-managed configuration — deploy this to every developer machine:**
```json
// Linux:   /etc/claude-code/managed-settings.json
// macOS:   /Library/Application Support/ClaudeCode/managed-settings.json
// Windows: %ALLUSERSPROFILE%\ClaudeCode\managed-settings.json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./appsettings.*.json)",
      "Read(~/.aws/**)",
      "Read(~/.ssh/**)",
      "Read(~/.azure/**)",
      "Bash(curl:*)",
      "Bash(wget:*)",
      "Bash(nc:*)"
    ],
    "disableBypassPermissionsMode": "disable",
    "defaultMode": "ask"
  },
  "sandbox": { "enabled": true, "allowUnsandboxedCommands": false },
  "enableAllProjectMcpServers": false,
  "forceLoginMethod": "console",
  "forceLoginOrgUUID": "YOUR-ORG-UUID"
}
```

**Cursor privacy and file exclusions:**
- Enable Privacy Mode: Settings → General → Privacy Mode (enforces zero data retention)
- Create `.cursorignore` in every repository:
```
.env
.env.*
*.pem
*.key
*.pfx
appsettings.Production.json
appsettings.Staging.json
secrets/
.azure/
.aws/
.ssh/
local.settings.json
launchSettings.json
```

**Known limitation:** `.cursorignore` blocks the agent from reading files but does not prevent
it from suggesting code that references those files by name. CVE-2025-59944 demonstrated a
filename case bypass on Windows/macOS. Do not rely on `.cursorignore` as the sole control.

**Certifications:** Claude Code has SOC 2 Type II, ISO 27001:2022, and ISO/IEC 42001:2023.
Cursor has SOC 2 Type II. Both offer zero-retention agreements for enterprise/team plans. Code
is **not used for training** under commercial terms.

### Advanced — PostToolUse Semgrep Hook, Security-First Prompting, Org Policy

**PostToolUse Semgrep hook — wire this in every project's `.claude/settings.json`:**
```json
{
  "hooks": {
    "PostToolUse": {
      "Edit": "semgrep scan --config p/secrets --config p/owasp-top-ten --quiet ${CLAUDE_FILE_PATH}"
    }
  }
}
```

This runs Semgrep on every file edit automatically. If Semgrep finds an issue, fix it before
proceeding — never move to the next step with an open finding.

**Claude Code Security Review GitHub Action:**
```yaml
- uses: anthropics/claude-code-security-review@main
  with:
    comment-pr: true
    claude-api-key: ${{ secrets.CLAUDE_API_KEY }}
```

**Security-first prompting template:**
```
Create a .NET 8 Web API endpoint for user registration.
THREAT MODEL: Public-facing, potential credential stuffing.
SECURITY REQUIREMENTS:
  - Authentication: [Authorize(Policy = "WriterOrAdmin")]
  - Authorization: no user-owned data, standard RBAC
  - Input validation: FluentValidation with email, name, password complexity
  - Rate limiting: 5 requests/min per IP
  - Logging: log attempt with userId, never log password
  - Error messages: generic (no account enumeration)
```

**Organizational AI security policy elements:**
- Approved tool list (e.g., Claude Code + Cursor only, with enterprise configs deployed)
- Data classification rules: PHI/PCI/credentials never enter AI context
- Mandatory human security review for all AI-generated code before merging
- Immediate credential rotation if an AI tool reads a secrets file
- Annual AI security awareness training

---
