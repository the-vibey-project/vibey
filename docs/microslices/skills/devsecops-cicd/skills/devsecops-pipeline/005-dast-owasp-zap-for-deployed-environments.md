---
id: skill-dast-owasp-zap-for-deployed-environments-367c40e4c3
purpose: dast owasp zap for deployed environments
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/devsecops-pipeline/SKILL.md
requires: ["skill-quality-gates-and-exception-process-bf37182081"]
links: ["skill-secrets-management-no-hardcoded-credentials-121c3aa354"]
---

## DAST: OWASP ZAP for Deployed Environments

Run DAST against a deployed staging environment (not in the main PR pipeline — deploy first):

```yaml
dast-zap:
  name: DAST (OWASP ZAP)
  needs: [deploy-staging]
  runs-on: ubuntu-latest
  steps:
    - name: ZAP Baseline Scan
      uses: zaproxy/action-baseline@v0.10.0
      with:
        target: 'https://staging.myapp.example.com'
        rules_file_name: '.zap/rules.tsv'
        cmd_options: '-a'    # Include alpha passive scan rules

    - name: ZAP Full Scan (weekly only)
      if: github.event_name == 'schedule'
      uses: zaproxy/action-full-scan@v0.10.0
      with:
        target: 'https://staging.myapp.example.com'
        rules_file_name: '.zap/rules.tsv'
```

ZAP rules file to suppress known false positives:
```tsv
# .zap/rules.tsv
10035	IGNORE	(Strict-Transport-Security Header Not Set)
10038	IGNORE	(Content Security Policy Header Not Set)
```

---
