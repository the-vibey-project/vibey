---
id: skill-9-networking-591a6c17a0
purpose: 9 networking
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-interconnect-power-thermals-and-networking/SKILL.md
requires: ["skill-8-thermals-c3bcc151e5"]
links: []
---

## §9. Networking

**⚠️ Ethernet dominates** — ⚠️ **1/2.5/10/25/40/100 GbE and beyond; ⚠️ note that copper
distance falls sharply with speed, which is why fibre and DAC cables appear.**
**⚠️ Latency vs bandwidth** — ⚠️ **and for distributed workloads latency and TAIL latency
usually matter more than headline bandwidth.**
**⚠️ Wi-Fi** — ⚠️ **shared medium, half duplex, and real throughput is a fraction of the
advertised PHY rate; ⚠️ for anything latency-sensitive, use a cable.**
**⚠️ Offload** — ⚠️ **TSO/LRO, RDMA (RoCE, InfiniBand) which bypasses the kernel and is
standard in HPC and AI clusters, and SmartNIC/DPU offload of networking and storage from
the host CPU.**

---

# PART II — BUILDING AND RUNNING A MACHINE
