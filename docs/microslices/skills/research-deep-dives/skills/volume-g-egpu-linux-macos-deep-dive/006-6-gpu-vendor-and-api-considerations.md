---
id: skill-6-gpu-vendor-and-api-considerations-d6ebf28be3
purpose: 6 gpu vendor and api considerations
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-5-workload-fit-007396fc70"]
links: ["skill-7-linux-setup-and-test-method-fe5478ce57"]
---

## 6. GPU vendor and API considerations

AMD commonly integrates with open Linux kernel and Mesa stacks and is relevant for Linux eGPU deployments. NVIDIA offers a large CUDA ecosystem and strong vendor tooling on Linux, but driver packaging and kernel integration require attention. Intel graphics support varies by generation and workload.

APIs include Vulkan, OpenGL, OpenCL, CUDA, HIP, ROCm, Metal, DirectX through compatibility layers, and application-specific renderers. An API is a software contract; a card’s silicon capability is not enough if the host OS, driver, compiler, runtime, or application does not support it.

For machine learning, check framework support, accelerator backend, VRAM, precision formats, driver/runtime compatibility, memory transfer cost, and whether the model fits. For video, check codec hardware support, application integration, color pipeline, capture/display routing, and export behavior.
