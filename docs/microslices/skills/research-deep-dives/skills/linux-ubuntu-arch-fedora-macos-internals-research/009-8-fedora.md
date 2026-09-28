---
id: skill-8-fedora-45ba7a30a8
purpose: 8 fedora
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-7-arch-linux-d6adb95c1e"]
links: ["skill-9-shared-linux-testing-b7f5917393"]
---

## 8. Fedora

Fedora is an upstream-oriented distribution ecosystem with RPM, DNF, systemd, SELinux, signed packages, rapid releases, Workstation/Server/IoT and image variants.

### RPM/DNF

RPM packages contain metadata, payloads, dependencies, scripts, and signatures. Spec files describe source, build, files, dependencies, and scriptlets. `rpmbuild`, `rpmdevtools`, `mock`, `fedpkg`, and DNF are central tools.

```sh
sudo dnf install rpmdevtools rpm-build
rpmdev-setuptree
rpmbuild -ba SPECS/example.spec
rpm -qpi RPMS/.../example.rpm
rpm -qpl RPMS/.../example.rpm
```

Use clean mock or Fedora build infrastructure; do not build packages as root. Test upgrades, scriptlets, SELinux labels, systemd activation, and file ownership.

### Kernel and images

Fedora’s custom-kernel workflow uses Fedora source/spec trees, `fedpkg`, build dependencies, `pesign`, and `grubby`; official builds are signed through controlled infrastructure. [Fedora custom kernel](https://fedoraproject.org/wiki/Docs/CustomKernel)

Fedora image workflows produce ISOs, QCOW2, raw images, OSTree commits, or root filesystems using tools including KIWI, image-builder, mkosi, and lorax depending on the variant. [Building Fedora](https://fedoraproject.org/wiki/Building_a_Fedora)

### SELinux

SELinux enforces policy through labels, domains, types, transitions, and allowed operations.

```sh
getenforce
ausearch -m AVC -ts recent
ls -Z path
restorecon -Rv path
```

Do not blindly paste `audit2allow` output. Understand the denied operation, correct labels and service design, and write the narrowest policy needed.
