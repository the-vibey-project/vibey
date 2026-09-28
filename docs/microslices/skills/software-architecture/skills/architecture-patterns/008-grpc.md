---
id: skill-grpc-597c16112c
purpose: grpc
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-rest-101447aef9"]
links: ["skill-graphql-90c2bd8eea"]
---

## gRPC
- Protocol Buffers IDL, binary serialization, four call types (unary, server/client/bidirectional streaming)
- Wins for internal, performance-critical, strongly-typed service-to-service
- **Azure ACA**: supports gRPC (HTTP/2). On **AKS**: need an L7 gRPC-aware ingress (NGINX or Traefik) for per-method routing and TLS — a plain L4 LB won't route
- **APIM** has added gRPC passthrough support
- **Critical:** Validate end-to-end HTTP/2 from client through ingress to pod; a single HTTP/1.1 hop breaks streaming
