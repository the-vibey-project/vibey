---
id: skill-11-decision-matrix-ff18b33204
purpose: 11 decision matrix
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-10-security-and-maintenance-c340490a33"]
links: ["skill-12-sources-2bc0b162f6"]
---

## 11. Decision matrix

Choose an eGPU only when all are true:

- the host exposes a supported external PCIe path;
- the operating system has a current driver/API path;
- the application can use the GPU;
- the enclosure supplies adequate power and cooling;
- the performance gain matters for the actual workload;
- display routing and sleep/recovery behavior are acceptable;
- total cost is better than alternatives;
- you can return or replace incompatible hardware.

For Linux, AMD open-stack solutions are often the lowest-friction starting point, while NVIDIA may be preferable for CUDA-specific workloads if the driver stack is validated. For macOS, Intel Macs with explicitly supported AMD eGPU configurations are the relevant category; Apple-silicon buyers should not assume external graphics support.
