---
id: skill-websockets-real-time-f0b2ac45bc
purpose: websockets real time
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-graphql-90c2bd8eea"]
links: ["skill-message-queues-d9471f62fa"]
---

## WebSockets & Real-Time
- **Azure Web PubSub**: WebSocket-native pub/sub, high fan-out
- **Azure SignalR Service**: SignalR protocol with transport negotiation (WebSockets → SSE → long-poll)
- Choose Web PubSub for raw WebSocket scale; SignalR when using the .NET SignalR model
