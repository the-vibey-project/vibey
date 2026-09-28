---
id: skill-12-containers-and-namespaces-f5fa36b2a7
purpose: 12 containers and namespaces
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-observability-troubleshooting-and-operations/SKILL.md
requires: ["skill-11-troubleshooting-methodology-97d77938b6"]
links: ["skill-13-automation-and-configuration-management-e8adcfc970"]
---

## §12. Containers and Namespaces

**⚠️ A container is not a VM.** It is a normal process with restricted visibility, built
from kernel primitives:
```
Namespaces  mnt, pid, net, ipc, uts, user, cgroup, time   ⚠️ WHAT IT CAN SEE
cgroups v2  cpu, memory, io, pids                          ⚠️ WHAT IT CAN USE
capabilities, seccomp, LSM (SELinux/AppArmor)              ⚠️ WHAT IT CAN DO
overlayfs                                                  layered images
```
```
lsns · nsenter -t PID -n ip a          ⚠️ enter a container's netns from the host
systemd-cgls · systemd-cgtop           cgroup tree and live resource use
cat /proc/PID/cgroup                   which cgroup is this process in
podman / docker / nerdctl · crictl     runtimes
```
**⚠️ The security consequence**: the kernel is **shared**. A kernel vulnerability crosses
the container boundary. **Run rootless (podman, or userns-remap), drop capabilities, apply
seccomp, and never `--privileged` in production.**

**⚠️ Systemd and containers overlap deliberately** — `systemd-nspawn`, and `Delegate=yes`
for cgroup delegation. **A hardened systemd unit (§4.3 → `sysadmin-systemd-storage-and-networking`) gives you most of a container's
isolation without the image.**

---
