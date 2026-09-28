---
id: skill-7-linux-setup-and-test-method-fe5478ce57
purpose: 7 linux setup and test method
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-6-gpu-vendor-and-api-considerations-d6ebf28be3"]
links: ["skill-8-macos-setup-and-test-method-ed9c28a504"]
---

## 7. Linux setup and test method

Before buying:

1. Identify the exact laptop, port, firmware, kernel family, distribution, desktop, and workload.
2. Confirm PCIe tunneling and eGPU reports for the host platform.
3. Check current kernel, Mesa, vendor-driver, firmware, and application support.
4. Verify enclosure controller, PSU, GPU dimensions, and cable.
5. Prefer a returnable purchase.

After installation:

1. Update firmware and fully update the system.
2. Record the baseline without the eGPU.
3. Connect with the system powered as documented by the enclosure/host vendor.
4. Confirm PCIe enumeration.
5. Confirm kernel module, firmware, DRM, Vulkan/OpenGL, and application visibility.
6. Test an external display directly on the GPU.
7. Test internal-display rendering if required.
8. Test suspend/resume, reboot, logout, multiple displays, hot-plug, and safe removal.
9. Benchmark real workloads repeatedly and record frame-time variance, not only averages.
10. Test failure recovery and decide whether the setup is reliable enough for work.

Do not repeatedly hot-unplug an active GPU without a documented safe-removal path. A successful first launch is not compatibility proof.
