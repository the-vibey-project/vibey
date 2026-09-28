---
id: skill-3-linux-architecture-7725430551
purpose: 3 linux architecture
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-2-interface-and-enclosure-constraints-ab596c36d6"]
links: ["skill-4-macos-compatibility-22054ec87f"]
---

## 3. Linux architecture

Linux graphics normally uses DRM/KMS in the kernel, Mesa and userspace APIs for open drivers, vendor components where applicable, and display/session layers such as Wayland or X11. AMDGPU support is documented in the kernel DRM subsystem and covers AMD Radeon architectures. [Linux AMDGPU documentation](https://docs.kernel.org/gpu/amdgpu/index.html).

An eGPU may appear as another PCIe GPU. The system must handle PCIe hotplug, runtime power, DRM device discovery, udev, firmware, kernel modules, display providers, compositor selection, and application device selection.

Common Linux concerns:

- whether the kernel sees the PCIe device;
- whether the driver and firmware load;
- whether DRM/KMS exposes the GPU;
- whether Mesa or vendor libraries select it;
- whether the compositor can render or scan out through it;
- whether applications can choose it;
- whether suspend, hot-unplug, and reboot are safe;
- whether the distribution’s kernel and graphics stack are compatible.

Useful inspection includes lspci, journalctl, dmesg, lsmod, modinfo, vulkaninfo, glxinfo, wlr-randr or xrandr, vendor utilities, and application-specific logs. Record kernel, Mesa, firmware, desktop environment, display server, GPU, enclosure controller, cable, and exact port.

AMD often has the smoothest open Linux path because kernel and Mesa support are integrated. NVIDIA may require proprietary drivers, kernel-module matching, Wayland/X11 configuration, and application-specific CUDA or Vulkan behavior. Intel external graphics and newer architectures require release-specific verification. “Works on Linux” must name distribution, kernel, driver, API, and workload.
