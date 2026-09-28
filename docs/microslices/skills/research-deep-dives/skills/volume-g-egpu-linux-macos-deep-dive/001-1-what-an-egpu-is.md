---
id: skill-1-what-an-egpu-is-52de06731c
purpose: 1 what an egpu is
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: []
links: ["skill-2-interface-and-enclosure-constraints-ab596c36d6"]
---

## 1. What an eGPU is

An external GPU system combines a discrete graphics card, enclosure power and cooling, a PCIe-to-Thunderbolt or USB4 transport path, firmware, operating-system drivers, display routing, and application support.

The path is not equivalent to installing a GPU directly in a desktop. Data crosses an external link with higher latency and lower effective bandwidth than an internal PCIe slot. Performance depends on workload, resolution, frame pacing, CPU limitation, display location, memory transfers, driver, enclosure controller, cable, and operating system.

An eGPU can provide graphics acceleration, external display outputs, compute, video processing, or a way to reuse a desktop GPU with a laptop. It can be a poor purchase if the workload is bandwidth-bound, the host has a fast integrated GPU, the OS lacks drivers, or the application cannot select the external device.
