---
id: skill-part-10-ai-debugging-limitations-564d034c46
purpose: part 10 ai debugging limitations
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-9-distributed-debugging-f5a7245715"]
links: ["skill-part-11-language-specific-debugging-patterns-c92bdf3bc2"]
---

## Part 10 — AI Debugging Limitations

### OpenRCA Benchmark (The Hard Evidence)

**OpenRCA benchmark** (ICLR 2025, Microsoft/Tsinghua — 335 real failure cases across three enterprise systems with 68+ GB of telemetry):
- Best model at publication (Claude 3.5): solved only **11.34%** of failure cases
- Best model by 2026 (Claude Opus 4.6): approximately **36%**

This is real progress but remains far below human reliability and far below coding benchmarks.

### Security Risks

**Veracode's 2025 GenAI Code Security Report** tested 100+ LLMs across 80 tasks:
- **45% of AI-generated code introduced an OWASP Top 10 vulnerability**
- Failure rates: 86% for XSS (CWE-80), 88% for log injection (CWE-117); Java worst at 72%
- "Increasing the scale of the model does not improve security" — a structural problem
- CodeRabbit's analysis found AI-produced code carries a **2.74× higher vulnerability rate** than human-written code

### What AI Is Good For

- Log summarization and triage
- Error localization
- Rubber-ducking (explaining code)
- First-draft fixes for well-understood bug classes
- Autofix of scanning alerts (GitHub Copilot Autofix, Sentry Seer)

### What AI Misses

- Context-dependent bugs
- Distributed and timing bugs
- Hardware-level bugs
- Security-sensitive code paths (especially authentication, cryptography, input handling, data access)

### Safe AI Debugging Practices

- Gate all AI-generated fixes behind tests and human review
- Mandate SAST, dependency, and secret scanning on every commit *at the point of code generation*
- Never merge AI-generated security-adjacent code without mandatory human security review regardless of confidence score
- Treat vendor-reported accuracy metrics (Sentry's "94.5% accuracy", GitHub Copilot's "two-thirds remediated") as directional, not audited

---
