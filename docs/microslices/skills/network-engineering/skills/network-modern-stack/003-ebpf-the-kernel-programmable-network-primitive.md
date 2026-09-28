---
id: skill-ebpf-the-kernel-programmable-network-primitive-58e3bd207f
purpose: ebpf the kernel programmable network primitive
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-spine-leaf-dominance-and-east-west-traffic-4fa9b06328"]
links: ["skill-cilium-the-production-kubernetes-networking-standard-e4f4f44786"]
---

## eBPF: the kernel-programmable network primitive

**eBPF (extended Berkeley Packet Filter) is the most consequential networking technology of the decade.** It allows sandboxed programs to execute inside the Linux kernel without modifying kernel source or loading modules. Programs are written in restricted C, verified for safety by an in-kernel verifier, and JIT-compiled to native instructions.

### Three hook points that matter for networking

**XDP (eXpress Data Path)**: operates at the NIC driver level before socket buffer allocation — the earliest possible interception point. Achieves **~194 Gbps throughput**, roughly **12.4× iptables performance**. Best for: DDoS mitigation at line rate, L4 load balancing, packet filtering at wire speed. Cloudflare auto-mitigated a record 3.8 Tbps DDoS attack using XDP-based filtering at ~10 million packets/second per core.

**TC (Traffic Control)**: hooks after socket buffer creation, supporting both ingress and egress with full conntrack integration. This is Cilium's primary enforcement point. Enables more complex processing with access to full kernel metadata.

**Socket-level programs**: enable custom load balancing (SO_REUSEPORT) and socket-to-socket shortcuts that bypass the entire network stack — Cilium's kube-proxy replacement intercepts connections at the `connect()` syscall.

### Production deployments

**Meta's Katran**: XDP-based L4 load balancer processing all facebook.com traffic. 3× more packets with 7× less CPU than its IPVS predecessor, using modified Maglev consistent hashing with DSR.

**Cloudflare's Unimog**: edge load balancing at under 1% CPU utilization.

**Tetragon / Falco**: runtime security monitoring via eBPF.

**Hubble**: deep network observability without sidecars or instrumentation.
