---
id: skill-part-6-ebpf-for-production-debugging-02daf74bfc
purpose: part 6 ebpf for production debugging
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-5-the-four-observability-signals-cd3a363134"]
links: ["skill-part-7-slo-based-burn-rate-alerting-040b76deff"]
---

## Part 6 — eBPF for Production Debugging

eBPF runs sandboxed programs in the Linux kernel for observability without kernel-module changes or app instrumentation — **"zero-instrumentation observability."**

**Key tools:**
- **Pixie** (CNCF) — auto-captures HTTP/gRPC/DNS/MySQL/Postgres/Redis without instrumentation libraries
- **Cilium Hubble** — network observability
- **Tetragon** (Cilium sub-project, CNCF) — security observability and kernel-level runtime enforcement; typically <1% overhead
- **bpftrace** — scripting interface for ad-hoc eBPF programs
- **kubectl-trace** — run bpftrace programs on Kubernetes nodes

In 2025, AWS EKS adopted Cilium as a default CNI. The OTel eBPF profiling agent (donated by Elastic) brought whole-system continuous profiling.

**Limitations:** Linux-only, kernel-version requirements, steep expertise curve.

---
