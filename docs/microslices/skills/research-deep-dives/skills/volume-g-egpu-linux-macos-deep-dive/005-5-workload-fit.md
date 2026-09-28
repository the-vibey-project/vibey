---
id: skill-5-workload-fit-007396fc70
purpose: 5 workload fit
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-4-macos-compatibility-22054ec87f"]
links: ["skill-6-gpu-vendor-and-api-considerations-d6ebf28be3"]
---

## 5. Workload fit

### Strong candidates

- rendering to an external display attached directly to the eGPU;
- GPU compute with large arithmetic intensity and limited host-device transfer;
- 3D rendering, some video effects, and offline workloads;
- a laptop whose internal GPU is clearly the bottleneck;
- a Linux workstation where the exact driver and API stack is validated.

### Weak candidates

- workloads that repeatedly transfer large datasets over the link;
- latency-sensitive games on the internal laptop display;
- applications that cannot select the external device;
- software requiring CUDA on an unsupported macOS environment;
- CPU-bound workloads;
- applications whose plugins or renderers only use the integrated GPU;
- systems where sleep, hot unplug, or multi-monitor behavior is mission-critical and untested.

Benchmark the real application. Synthetic GPU scores, peak TFLOPS, and VRAM capacity do not predict every workload.
