---
id: skill-part-4-phase-0-codebase-assessment-run-before-touching-anything-8b8d8c01be
purpose: part 4 phase 0 codebase assessment run before touching anything
source: src/vibey_tools/skills/plugins/security-first-dev/skills/codebase-modernization/SKILL.md
requires: ["skill-part-3-triage-priority-system-e89e7ec4d1"]
links: ["skill-part-5-phase-1-secrets-and-credentials-highest-priority-ac4986459e"]
---

## PART 4: PHASE 0 — CODEBASE ASSESSMENT (RUN BEFORE TOUCHING ANYTHING)

Run this assessment on every codebase you are asked to modernize. Produce a written finding
summary before writing a single line of migration code.

### 4.1 Secrets Scan — Run First, No Exceptions

```bash
# Full history scan — not just HEAD
gitleaks detect --source . --log-opts "--all" --report-format json --report-path gitleaks-report.json
# Current working tree
gitleaks detect --source . --report-format json --report-path gitleaks-current.json
# npm / pip dependency secrets
trufflehog filesystem . --json > trufflehog-report.json
```

If secrets are found: Stop. Do not proceed with any other migration work. Report to the human
immediately. Credentials must be rotated before the codebase is touched further.

### 4.2 Dependency Vulnerability Scan

```bash
dotnet list package --vulnerable --include-transitive > dotnet-vulns.txt
npm audit --json > npm-audit.json
pip install safety && safety check --json > safety-report.json
pip install bandit && bandit -r src/ -f json -o bandit-report.json
```

Categorize: CRITICAL (this sprint), HIGH (next sprint), MEDIUM/LOW (backlog).

### 4.3 Authentication Surface Map

For every .NET controller and every React/Blazor route, record:
```
Endpoint / Route | Auth required? | Current mechanism | Auth flow | Token storage | Notes
```

Flag any endpoint that:
- Has no `[Authorize]` decorator and serves non-public data
- Uses Implicit Grant flow
- Stores tokens in `localStorage`
- Uses a shared app registration across environments
- Has hardcoded `ClientSecret` in configuration

### 4.4 Authorization / BOLA Check

For every endpoint that returns or modifies user-owned data:
```
Endpoint | Returns user-owned data? | Ownership check present? | Where? (controller/service/none)
```

### 4.5 Database Query Safety Audit

```bash
# .NET — find raw SQL with string interpolation
grep -rn "FromSqlRaw\|ExecuteSqlRaw\|FromSqlInterpolated" src/ --include="*.cs"
grep -rn '"\s*SELECT\|"\s*INSERT\|"\s*UPDATE\|"\s*DELETE' src/ --include="*.cs"
# Python
grep -rn 'execute.*f"SELECT\|execute.*%.*SELECT' src/ --include="*.py"
```

### 4.6 Secrets in Configuration Files

```bash
grep -rn "Password=\|pwd=\|AccountKey=\|SharedAccessKey=" . \
  --include="*.json" --include="*.yaml" --include="*.yml" --include="*.env" \
  --exclude-dir=node_modules --exclude-dir=.git
```

### 4.7 Architecture Layer Violations (.NET)

```bash
# Business logic / DB in controllers
grep -rn "DbContext\|CosmosClient\|NpgsqlConnection" src/ --include="*.cs" | grep -i "controller"
# Repository calls from controllers
grep -rn "IRepository\|Repository" src/ --include="*.cs" | grep -i "controller"
```

### 4.8 Frontend Security Audit

```bash
grep -rn "localStorage" src/ --include="*.ts" --include="*.tsx" | grep -i "token\|auth\|jwt"
grep -rn "dangerouslySetInnerHTML" src/ --include="*.tsx" --include="*.jsx"
grep -rn "AllowAnyOrigin\|origin.*\*" . --include="*.ts" --include="*.json"
```

### 4.9 Assessment Report Template

```markdown
## Codebase Assessment — [Date] — [Repo Name]

### P0 Findings (Immediate)
- [ ] [Finding] — [File:Line] — [Impact]

### P1 Findings (This Sprint)
### P2 Findings (Next Sprint)
### P3 Findings (Backlog)

### Existing Test Coverage
- Overall: X%
- Security test coverage: X% (estimate)
- Integration tests present: yes/no

### Architecture Health
- Layer violations found: X
- Missing interfaces: X
- Controllers with direct DB access: X
```

Hand this to the human before writing any migration code. They scope the sprints; you execute.

---
