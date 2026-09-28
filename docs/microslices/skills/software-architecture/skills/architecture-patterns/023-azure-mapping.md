---
id: skill-azure-mapping-994a1e3674
purpose: azure mapping
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-three-pillars-one-05092001b0"]
links: ["skill-zero-trust-f3cb1ecbee"]
---

## Azure Mapping
- **Azure Monitor**: metrics
- **Log Analytics**: logs + KQL
- **Application Insights**: APM — distributed tracing, dependency map, live metrics, sampling
- **Azure Managed Grafana**: dashboards
- **Azure Monitor OpenTelemetry Distro**: recommended path for new apps — one-line export to App Insights, simultaneously exports to any OTLP endpoint

**Production gotcha:** Incomplete distributed traces usually come from inconsistent sampling across nodes — if one service applies head-based sampling without propagating the decision via W3C headers, downstream spans get dropped. In Azure Functions, don't run the Azure Monitor distro in the isolated worker if the host already instruments — duplicate telemetry.

---

# PART 10: SECURITY ARCHITECTURE
