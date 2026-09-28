---
id: skill-part-9-distributed-debugging-f5a7245715
purpose: part 9 distributed debugging
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-8-error-handling-design-and-patterns-8d895d7b4d"]
links: ["skill-part-10-ai-debugging-limitations-564d034c46"]
---

## Part 9 — Distributed Debugging

### Why Distributed Debugging Is Hard

The **fallacies of distributed computing** each create a debugging challenge: network is reliable, latency is zero, bandwidth is infinite, network is secure, topology is static, one administrator, transport cost is zero, network is homogeneous.

**Partial failures** (a service that is up but slow, degraded, or returning wrong answers) are harder than binary up/down. **Clock skew** means timestamps from different services can't be totally ordered without vector clocks or hybrid logical clocks. Delivery semantics (at-most-once / at-least-once / exactly-once) determine retry safety.

### Debugging Microservices

- Service dependency maps (Istio/Linkerd mesh observability, APM-generated maps)
- Distributed tracing as the critical RCA tool ("the trace shows you exactly where a request failed")
- Event-driven debugging via message correlation IDs and dead-letter-queue analysis (Kafka, RabbitMQ, Service Bus)
- gRPC status codes and `google.rpc.Status` error details

### Production Debugging Techniques

- Feature flags to isolate code paths
- Canary/dark launches as controlled experiments
- Trace-ID correlation to find the *source* vs. *amplifier* of a failure
- Log-based event reconstruction
- Correlating error spikes with deploys/config/traffic

**Profiling tools:**
- Heap dumps: Eclipse MAT (JVM), dotMemory (.NET)
- Thread dumps: jstack (deadlock/starvation)
- CPU profiling: async-profiler (JVM), py-spy (Python), pprof (Go), perf (Linux)
- Network: tcpdump, Wireshark

**Kubernetes:** `kubectl exec`, **ephemeral debug containers** (`kubectl debug`), pod describe/events, cross-pod log streaming.

### Chaos Engineering

Chaos engineering as proactive debugging — built on **Netflix's Chaos Monkey** (invented 2011, open-sourced 2012, Apache 2.0). The Simian Army extended it: Latency Monkey injects network latency, Chaos Gorilla simulates AZ failure, Chaos Kong a whole Region.

**Principles of Chaos Engineering** (principlesofchaos.org):
1. Build a hypothesis around steady-state behavior
2. Vary real-world events
3. Run experiments in production
4. Automate to run continuously
5. **Minimize blast radius**

**Tools:**
- **AWS Fault Injection Service (FIS)** — managed, real fault injection with CloudWatch-alarm stop conditions and auto-rollback
- **Azure Chaos Studio** — GA at Ignite November 2023; service-direct and agent-based faults
- **Gremlin** — enterprise platform with granular blast-radius control, safe halt/rollback, reliability scoring

---
