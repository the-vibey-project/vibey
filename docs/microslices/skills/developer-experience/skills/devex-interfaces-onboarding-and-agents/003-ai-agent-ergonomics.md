---
id: skill-ai-agent-ergonomics-0c1fe09f24
purpose: ai agent ergonomics
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-interfaces-onboarding-and-agents/SKILL.md
requires: ["skill-onboarding-and-open-source-contribution-8bad7cb779"]
links: []
---

## AI-agent ergonomics

Coding agents now read your repository, so treat them as a second class of user. Evidence is practitioner-level and changing fast.

- **AGENTS.md** at the repo root: build and test commands, code style, project layout, and gotchas, kept short. Adoption counts conflict between sources (over 20,000 versus over 60,000 repositories), so treat both as rough.
- **llms.txt** for docs sites: a curated markdown index of key pages (see [Cloudinary's](https://cloudinary.com/documentation/llms.txt) as an example, and append `.md` to page URLs where you can serve markdown). No confirmed search-ranking effect, but coding tools do read it.
- **MCP servers:** every tool definition costs context tokens. Keep the tool count low, name tools by the job, return paginated results with a token budget, and consider code-execution patterns for heavy data work. Compact formats such as YAML can cost fewer tokens than JSON.
- **Deterministic interfaces:** JSON output, stable exit codes and no prompts let agents run your CLI safely.
- **Guard rails:** dry-run modes, scoped credentials and readable audit logs matter more when the caller is automated.
- **Do not assume speedups.** The METR trial found experienced developers 19% slower with AI in one narrow setting, so measure the effect on your own team.
