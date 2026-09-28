---
id: skill-13-comparative-architecture-463771aae3
purpose: 13 comparative architecture
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-12-macos-system-extensions-security-and-testing-ffe1d44418"]
links: ["skill-14-creating-a-new-os-cb0f6986ba"]
---

## 13. Comparative architecture

| Area | Ubuntu/Arch/Fedora | macOS |
|---|---|---|
| Kernel | Upstream Linux plus distro configuration/patches | XNU: Mach/BSD/I/O Kit and Apple components |
| Public source | Broad upstream and distribution trees | Darwin/XNU portions; proprietary layers remain |
| Executable | ELF | Mach-O |
| Packages | deb/APT, Arch packages/pacman, RPM/DNF | App bundles, installer packages, Mac App Store |
| Services | Usually systemd | launchd and Apple service frameworks |
| Mandatory policy | SELinux/AppArmor/LSM, capabilities, namespaces, seccomp | SIP, TCC, sandbox, entitlements, signatures |
| Drivers | Kernel modules and Linux device subsystems | DriverKit/system extensions preferred; kexts restricted |
| Custom kernel | Normal but risky and distro-specific | Not a general supported replacement path |
| GUI | X11/Wayland plus GTK/Qt/etc. | Quartz/WindowServer/AppKit/SwiftUI |
| Update authority | Distribution repositories and administrator | Apple update/signing/notarization ecosystem |
