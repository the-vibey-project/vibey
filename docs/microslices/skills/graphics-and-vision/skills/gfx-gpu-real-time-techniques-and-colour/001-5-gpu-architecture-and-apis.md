---
id: skill-5-gpu-architecture-and-apis-1a0f2e48ff
purpose: 5 gpu architecture and apis
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-gpu-real-time-techniques-and-colour/SKILL.md
requires: []
links: ["skill-6-real-time-techniques-597f5adbcd"]
---

## §5. GPU Architecture and APIs

**The execution model that explains most performance behaviour**: **SIMT** — threads run in
**warps (32, NVIDIA) or wavefronts (32/64, AMD)** in lockstep.
> **⚠️ GOTCHA — divergence is the cost you can't see in the source.** If threads in a warp
> take different branches, **both paths execute with the inactive lanes masked off.** A
> branch that splits a warp costs the sum of both sides. ⚠️ **This is why "avoid branches
> in shaders" is advice, and why the real rule is "avoid branches that diverge *within a
> warp*"** — a branch on a uniform value is free.

**Memory hierarchy**: registers → shared/LDS → L1 → L2 → VRAM. ⚠️ **Coalesced access —
adjacent threads reading adjacent addresses — is the difference between full bandwidth and
a fraction of it.** **Occupancy** (warps in flight) hides latency, and ⚠️ **register
pressure limits occupancy, so a shader that uses too many registers runs slower even if it
does less work.**

**APIs**: **Vulkan / D3D12 / Metal** — explicit, low-overhead, you manage synchronization
and memory. **OpenGL / D3D11** — legacy, driver-managed. **WebGPU** (⚠️ **the modern
browser target, and a genuinely reasonable API to learn first — it's Vulkan's model with
the sharp edges removed**). **CUDA / OpenCL / SYCL** for compute.
**Shading languages**: GLSL, HLSL, MSL, **WGSL**, **Slang** (⚠️ **increasingly the
cross-compilation target of choice**).

**⚠️ The explicit-API burden that surprises people**: pipeline state objects, descriptor
sets, command buffers, and **barriers and layout transitions** — ⚠️ **incorrect barriers
produce races that manifest as flickering or corruption on one vendor's driver and not
another's.** **Use the validation layers; they exist for exactly this.**

---
