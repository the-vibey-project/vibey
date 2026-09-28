---
id: skill-semgrep-posttooluse-hook-for-real-time-scanning-f1f93ddada
purpose: semgrep posttooluse hook for real time scanning
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-job-by-job-breakdown-a1bcf6b459"]
links: ["skill-quality-gates-and-exception-process-bf37182081"]
---

## Semgrep PostToolUse Hook for Real-Time Scanning

Wire Semgrep to scan files immediately after Claude Code edits them:

```json
// .claude/settings.json
{
  "hooks": {
    "PostToolUse": {
      "Edit": "semgrep scan --config p/secrets --config p/owasp-top-ten --quiet ${CLAUDE_FILE_PATH}",
      "Write": "semgrep scan --config p/secrets --config p/owasp-top-ten --quiet ${CLAUDE_FILE_PATH}"
    }
  }
}
```

This catches AI-generated security anti-patterns immediately during development, before they reach CI:
- Hardcoded credentials (CWE-798)
- SQL injection via string interpolation (CWE-89)
- Missing authorization decorators (CWE-862)
- XSS in React via `dangerouslySetInnerHTML` (CWE-79)

---
