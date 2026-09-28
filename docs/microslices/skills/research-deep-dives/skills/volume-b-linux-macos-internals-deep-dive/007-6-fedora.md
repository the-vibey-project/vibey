---
id: skill-6-fedora-3c2d3cbb02
purpose: 6 fedora
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-5-ubuntu-29ae4479f8"]
links: ["skill-7-arch-linux-a2ca2ef159"]
---

## 6. Fedora

Fedora is a fast-moving community distribution with strong upstream integration. It commonly uses RPM packages and DNF transactions. Fedora emphasizes SELinux, systemd, contemporary toolchains and Wayland-based desktop configurations, with both traditional and image-based variants.

RPM metadata covers dependencies, scripts, file ownership, signatures and package identity. DNF should perform coherent repository transactions. Fedora’s release cadence makes lifecycle-aware testing important.

SELinux troubleshooting means reading AVC denials, understanding labels and policy, and fixing the service or policy issue. Disabling enforcement can hide the underlying error and should not be the default solution.

Sources: [Fedora documentation](https://docs.fedoraproject.org/), [Fedora packages](https://packages.fedoraproject.org/), [SELinux project](https://selinuxproject.org/).
