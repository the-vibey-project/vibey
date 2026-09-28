---
id: skill-known-limitations-and-gotchas-eea0d53e7f
purpose: known limitations and gotchas
source: src/vibey_tools/skills/plugins/devsecops-cicd/skills/bitbucket-azure/SKILL.md
requires: ["skill-comparison-bitbucket-vs-github-actions-vs-azure-devops-f249455729"]
links: ["skill-security-scanning-integration-3b88587eb7"]
---

## Known Limitations and Gotchas

1. **No OIDC to Azure** — the largest gap for Azure shops. No committed delivery from Atlassian.

2. **Hosted Linux only** — .NET Framework builds, Windows containers, iOS/macOS all require self-hosted runners.

3. **One YAML file per repo** — 30-workflow GitHub repos collapse into one potentially sprawling file.

4. **Docker service 1 GB memory cap** — independent of step `size:`. OOM in docker build does not respond to `size: 4x` alone — must also raise `definitions.services.docker.memory`.

5. **Docker cache limited to 1 GB** — modern images quickly exceed this. Use registry cache (`--cache-from`), self-hosted runners with disk, or Depot.

6. **Artifacts expire after 14 days** — manual gate steps become un-clickable if the gate is held longer than 2 weeks because input artifacts are gone.

7. **No matrix builds** — multi-runtime test matrices (Node 18×20×22 on Linux×Windows) that are one-liners in GHA require hand-expansion in Bitbucket.

8. **Parallel steps cannot reliably share artifacts** — only the first finishing step can write a given cache. Fan-out → fan-in patterns require careful design.

9. **IP allowlisting** — use `runtime.cloud.atlassian-ip-ranges: true` to constrain hosted runs to publishable IP ranges for Azure resources with IP restrictions.

10. **Pushing more than 5 tags/branches/bookmarks in one push skips pipeline runs entirely** — anti-runaway protection that can bite automation scripts.

11. **IPv4 only** — if your Azure landing zone requires IPv6, this is a blocker.

12. **Self-hosted runner pricing in flux** — the model changed significantly in early 2026; verify before any architectural commitment.

---
