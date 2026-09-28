---
id: skill-7-arch-linux-d6adb95c1e
purpose: 7 arch linux
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-6-ubuntu-700fe1b587"]
links: ["skill-8-fedora-45ba7a30a8"]
---

## 7. Arch Linux

Arch is a rolling distribution emphasizing upstream-oriented packages, pacman, PKGBUILDs, systemd, and administrator control.

### pacman and PKGBUILD

A PKGBUILD is a Bash build recipe containing source retrieval, checksums, dependencies, build steps, and packaging. `makepkg` creates a compressed package; `pacman` installs and tracks it. Arch recommends clean chroots because dirty build environments can create unrepeatable dependencies and runtime behavior. [Arch Build System](https://wiki.archlinux.org/title/Arch_Build_System) and [Creating packages](https://wiki.archlinux.org/title/Creating_packages)

```sh
sudo pacman -S --needed base-devel git devtools
pkgctl repo clone --protocol=https package-name
cd package-name
makepkg --verifysource
makepkg -s
makepkg --clean
sudo pacman -U package-name-*.pkg.tar.zst
```

Read PKGBUILDs before execution: they run shell code. Build as a normal user. Use a clean chroot for reliable packages. Treat AUR recipes as code to audit, not as equivalent to signed official packages.

### Arch kernels and images

Arch can reuse the official Linux PKGBUILD, alter configuration or patches, build with makepkg, install kernel and headers, regenerate initramfs, and add bootloader entries. Arch warns custom kernels can cause instability or data loss. [Arch kernel build system](https://wiki.archlinux.org/title/Kernel/Arch_build_system)

Unified kernel images combine a UEFI stub, kernel, initramfs, and resources in a PE file. Boot configuration, microcode, initramfs generation, signing, and firmware behavior all matter.
