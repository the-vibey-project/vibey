---
id: skill-3-processes-services-and-ipc-e1d6858daf
purpose: 3 processes services and ipc
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-2-linux-kernel-e506b9d569"]
links: ["skill-4-networking-and-security-d52cd9dfc8"]
---

## 3. Processes, services and IPC

Linux programs communicate through pipes, Unix sockets, TCP/UDP, signals, shared memory, futexes, files, dbus and RPC. Namespaces isolate process IDs, mounts, networking, users, IPC, hostnames and time. Cgroups control and account for resource use and are foundational to containers and service management.

systemd commonly acts as PID 1. It manages units, dependencies, sockets, mounts, timers, devices, scopes, user services, logging and supervision. It is a dependency and service-management system, not merely an old init-script runner. A service definition should specify identity, privileges, dependencies, readiness, restart policy, limits, logs, secrets and shutdown behavior.

Source: [systemd documentation](https://www.freedesktop.org/software/systemd/man/latest/).
