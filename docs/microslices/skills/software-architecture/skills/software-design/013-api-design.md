---
id: skill-api-design-a88fb9e9ea
purpose: api design
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-design/SKILL.md
requires: ["skill-fitness-functions-and-automated-governance-e5fe64ec6f"]
links: ["skill-non-functional-design-b8a23c6331"]
---

## API Design

### Right Protocol per Boundary (2024–2026 Consensus)
There is no single winner; match protocol to context:

| Protocol | Best For | Key Trade-Off |
|---|---|---|
| **REST** | Public/third-party APIs | Simplicity, HTTP caching, ubiquity |
| **gRPC** | Internal service-to-service | ~3–10× faster, 60–80% smaller than JSON (Protobuf) |
| **GraphQL** | Client-driven / BFF data needs | Solves over/under-fetching; N+1 requires DataLoader |
| **tRPC** | End-to-end TypeScript | Full type safety; TypeScript-only |
| **MCP** | AI-tool interaction | JSON-RPC-based; Anthropic standard |

### Core Disciplines
- **API-first:** OpenAPI or .proto as the design artifact — written before implementation
- **Consumer-driven contracts (Pact):** Tests that verify provider behavior matches consumer expectations
- **Expand-and-contract:** The standard pattern for backward-compatible API evolution

---
