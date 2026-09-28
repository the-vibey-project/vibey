---
id: skill-4-macos-compatibility-22054ec87f
purpose: 4 macos compatibility
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-3-linux-architecture-7725430551"]
links: ["skill-5-workload-fit-007396fc70"]
---

## 4. macOS compatibility

Apple documents external GPU selection for Intel-based Macs, including Thunderbolt-connected external GPUs on supported macOS versions. Apple’s Metal documentation identifies external GPU devices on Intel systems. [Apple multiple GPUs](https://developer.apple.com/documentation/metal/finding-multiple-gpus-on-an-intel-based-mac).

Apple silicon Macs use an integrated system GPU architecture with shared CPU/GPU memory. Apple’s documentation states that external GPU device location is not applicable on Apple silicon in the relevant Metal API. This means an eGPU purchase for modern Apple-silicon macOS should not be assumed to work as a general-purpose external GPU solution. [Apple Silicon porting](https://developer.apple.com/documentation/Apple-Silicon/porting-your-macos-apps-to-apple-silicon); [Metal device location](https://developer.apple.com/documentation/metal/mtldevicelocation/external).

For Intel Macs, compatibility still depends on macOS version, supported AMD card families, enclosure, Thunderbolt path, application API, display routing, and driver support. NVIDIA eGPU support on macOS is not equivalent to Linux or Windows support. Apple does not provide a general third-party driver model for every current GPU.

Apple applications can enumerate and choose Metal devices. Developers should account for removable GPUs, external displays, device removal notifications, low-power and external device properties, and workload characteristics. External GPUs have lower bandwidth than internal or integrated paths and are better suited to workloads tolerant of that limitation. [Apple GPU selection](https://developer.apple.com/documentation/metal/selecting-device-objects-for-graphics-rendering).
