---
id: skill-6-ubuntu-700fe1b587
purpose: 6 ubuntu
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-5-linux-filesystems-devices-security-and-containers-c89caa2e52"]
links: ["skill-7-arch-linux-d6adb95c1e"]
---

## 6. Ubuntu

Ubuntu combines upstream Linux with Debian-derived packaging, Canonical integration, release engineering, installers, security maintenance, and distribution defaults. Official architectures include amd64, arm64, armhf, ppc64el, s390x, and riscv64, with release-specific support. [Ubuntu supported architectures](https://ubuntu.com/project/docs/how-ubuntu-is-made/concepts/supported-architectures/)

### APT/dpkg

Ubuntu primarily uses Debian packages. APT resolves repository metadata and dependencies; dpkg unpacks/configures individual packages.

```sh
apt update
apt policy package
apt show package
apt install package
apt source package
apt build-dep package
dpkg -L package
dpkg -S /path/to/file
```

Repository metadata and source configuration are version-sensitive; modern Ubuntu releases use deb822 sources in `/etc/apt/sources.list.d/*.sources`. [Ubuntu package management](https://ubuntu.com/server/docs/how-to/software/package-management/)

Snaps are a separate package/distribution mechanism with revisions, channels, confinement, and transactional refresh behavior. A deb, Snap, container, and source build have different integration and update semantics.

### Ubuntu kernel and package development

Canonical maintains multiple kernel trees and variants. The Ubuntu `linux` source can produce differently configured binaries such as generic and low-latency kernels. Canonical documents source access, builds, module rebuilds, testing, and kernel-team workflows. [Ubuntu kernel variants](https://ubuntu.com/kernel/docs/reference/ubuntu-kernels/) and [Ubuntu kernel how-to guides](https://ubuntu.com/kernel/docs/how-to/)

For packages use source packages, `debuild`/dpkg-buildpackage, clean `sbuild`-style environments, autopkgtest, linting, upgrade tests, systemd units, documentation, and explicit removal/conffile behavior.

Boot commonly involves UEFI, a signed shim or equivalent, GRUB or a unified kernel image, kernel, initramfs, and root filesystem. Secure Boot, AppArmor, systemd, capabilities, namespaces, and seccomp form overlapping security layers.
