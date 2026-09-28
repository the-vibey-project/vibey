---
id: skill-4-networking-and-security-d52cd9dfc8
purpose: 4 networking and security
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-3-processes-services-and-ipc-e1d6858daf"]
links: ["skill-5-ubuntu-29ae4479f8"]
---

## 4. Networking and security

Linux networking moves from userspace configuration through netlink to kernel interfaces, addresses, routes, neighbors, sockets, firewall hooks and traffic control. NetworkManager, systemd-networkd and distribution tools are policy layers.

Security layers include Unix permissions, capabilities, namespaces, cgroups, seccomp, Linux Security Modules, cryptographic verification, secure boot where deployed, sandboxing, patching and supply-chain controls. Fedora strongly integrates SELinux; Ubuntu commonly uses AppArmor. These controls supplement rather than replace least privilege, patching, safe parsing, authentication, backups and incident response.
