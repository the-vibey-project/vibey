---
id: skill-graphql-90c2bd8eea
purpose: graphql
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-grpc-597c16112c"]
links: ["skill-websockets-real-time-f0b2ac45bc"]
---

## GraphQL
- Schema-first; queries, mutations, subscriptions
- **N+1 problem** solved with **DataLoader** batching
- **Federation** (Apollo Federation, schema stitching) composes a supergraph from subgraphs
- **Azure:** APIM supports GraphQL passthrough and **synthetic GraphQL** (resolvers over REST/SOAP backends), plus depth/complexity limiting policies
