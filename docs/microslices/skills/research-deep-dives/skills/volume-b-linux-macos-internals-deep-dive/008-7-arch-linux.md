---
id: skill-7-arch-linux-a2ca2ef159
purpose: 7 arch linux
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-6-fedora-3c2d3cbb02"]
links: ["skill-8-languages-and-toolchains-899c26e659"]
---

## 7. Arch Linux

Arch is a rolling distribution with a minimal default system, strong upstream alignment, extensive documentation and user-controlled composition. It has no conventional major releases; packages move through repositories as the system evolves. Freshness and control increase, but so does the need to read news, perform complete upgrades and understand dependencies.

Pacman installs and queries packages. Makepkg builds from PKGBUILD instructions. The Arch User Repository contains user-contributed recipes and requires review; an AUR recipe is not equivalent to an official signed binary package.

Arch lets the user choose bootloader, initramfs, kernel, filesystems, encryption, networking, desktop and services. This is flexible and educational but transfers integration and recovery responsibility to the user.

Sources: [Arch boot process](https://wiki.archlinux.org/title/Arch_boot_process), [Arch repositories](https://wiki.archlinux.org/title/Official_repositories), [pacman](https://wiki.archlinux.org/title/Pacman).
