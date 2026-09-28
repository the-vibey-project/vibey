---
id: skill-platform-engineering-and-internal-developer-platforms-c5e6326e9d
purpose: platform engineering and internal developer platforms
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/cicd-field-guide/SKILL.md
requires: ["skill-ai-assisted-ci-cd-5e66af1cce"]
links: ["skill-iac-in-pipelines-3b733bb3b9"]
---

## Platform Engineering and Internal Developer Platforms

### Backstage vs Commercial IDPs

**Backstage (Spotify, CNCF):**
- 89% market share vs SaaS competitors (DX March 2025); 67% overall penetration; 3,400+ orgs
- **Heavy warning:** "average Backstage adoption rate is stuck at 10%"; requires 3–5 dedicated engineers including React/TypeScript skills; Gartner reports 12+ month setup times for large enterprises
- Use only with committed staffing and maximum extensibility requirement

**Commercial alternatives:** Port, Cortex, OpsLevel, Roadie (managed Backstage, ~$35/dev/mo), Spotify Portal SaaS (~$84K/yr for 200 engineers)
- Trade flexibility for faster time-to-value
- Gartner's 2025 guidance now favors turnkey IDPs
- Use when you need fast ROI without a dedicated platform team

**Decision rule:** if Backstage adoption stalls near ~10% or your platform team spends most time maintaining the portal, switch to managed/commercial.

---
