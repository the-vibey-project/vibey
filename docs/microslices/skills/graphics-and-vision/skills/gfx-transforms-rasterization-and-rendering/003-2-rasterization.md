---
id: skill-2-rasterization-330f988324
purpose: 2 rasterization
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-transforms-rasterization-and-rendering/SKILL.md
requires: ["skill-1-transforms-and-projective-geometry-13dcf23f1f"]
links: ["skill-3-shading-and-pbr-9a061209f6"]
---

## §2. Rasterization

```
Vertex data → vertex shader → [optional tessellation, geometry]
  → clipping → perspective divide → viewport transform
    → triangle setup → RASTERIZE → early-Z → fragment shader
      → depth/stencil test → blend → framebuffer
```

**Rasterization** determines coverage: for each pixel, is its centre inside the triangle?
**Edge functions** (Pineda) give this as three sign tests, and ⚠️ **they're incrementally
evaluable, which is why hardware does it this way.**

**⚠️ Perspective-correct interpolation is essential and non-obvious**: interpolating an
attribute linearly in screen space is wrong under perspective. **Interpolate `attr/w` and
`1/w` linearly, then divide.** ⚠️ **Getting this wrong produces the classic warped-texture
artifact of early 3D hardware.**

**Depth**: the Z-buffer. ⚠️ **Depth precision is non-linearly distributed** — most
precision sits near the near plane, so **z-fighting at distance is caused by a near plane
that is too close, far more often than by a far plane that is too far.** **Reversed-Z with
a floating-point depth buffer** largely fixes this and is the modern default.

**Culling**: backface (winding order), frustum, occlusion, and **early-Z** — ⚠️ **which is
disabled if the fragment shader writes depth or uses `discard`, and that is a common
silent performance cliff.**

**Texturing**: UV mapping, filtering (nearest, bilinear, trilinear, **anisotropic**),
**mipmaps** (⚠️ **not an optimization — they're antialiasing in the texture domain, and
without them minified textures shimmer**), wrap modes, and compressed formats (BC/DXT,
ASTC, ETC).

---
