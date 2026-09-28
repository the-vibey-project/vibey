---
id: skill-ai-assisted-development-2024-2026-2680760d69
purpose: ai assisted development 2024 2026
source: src/vibey_tools/skills/plugins/engineering-process/skills/sdlc-practices/SKILL.md
requires: ["skill-observability-c2dfad5042"]
links: ["skill-team-structures-82e9accd17"]
---

## AI-Assisted Development (2024–2026)

### Evidence Summary
The evidence is mixed and important — do not apply AI tooling uncritically.

| Study | Finding |
|---|---|
| **DORA 2024** | AI adoption correlated with −1.5% throughput, −7.2% stability per 25% adoption increase; larger batch sizes were the cause. |
| **DORA 2025** | AI now correlates positively with throughput (reversed), but instability remains negative. AI is a "mirror and multiplier" — amplifies existing strengths or dysfunctions. |
| **METR RCT (July 2025)** | Experienced developers were 19% *slower* with AI on familiar codebases, despite forecasting a 24% speedup. |
| **Veracode 2025** | 45% of AI-generated code introduced a detectable OWASP Top 10 vulnerability; XSS failed 86% of the time. |
| **Stack Overflow 2025** | 84% adoption; trust in AI accuracy *fell* from 40% to 29%. Biggest frustration (66%): "AI solutions that are almost right, but not quite." |

### DORA AI Capabilities Model (7 foundational capabilities)
1. Clear and communicated AI stance
2. Healthy data ecosystems
3. AI-accessible internal data
4. Strong version control practices
5. Working in small batches
6. User-centric focus
7. Quality internal platforms

### Production Guidance
- **Spec-driven development** (GitHub Spec-Kit, Amazon Kiro) has replaced "vibe coding" for production work.
- "Vibe coding" (Karpathy, Feb 2025) is appropriate for prototyping, dangerous for production.
- The "90% problem": AI reaches 90% quickly; the last 10% (debugging, integration, edge cases) is where human expertise is decisive.
- Gate AI-generated code through the same SAST/secrets/SCA pipeline as human-written code.
- Intensify (do not relax) testing when using AI-assisted development.
- **If instability/rework rate climbs after AI rollout**: slow AI adoption and fix the testing/review pipeline first.

### AI Code Review Tools
- **CodeRabbit**: breadth and precision.
- **Greptile**: deep-context recall (~82% catch rate in independent benchmark).
- **GitHub Copilot code review**: zero-friction GitHub integration.
- False positives remain the #1 complaint — tune aggressively for the "cry wolf" problem.

---
