---
id: skill-15-programming-workflows-521e5ba9a5
purpose: 15 programming workflows
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-14-creating-a-new-os-cb0f6986ba"]
links: ["skill-16-reproducibility-and-release-engineering-0d47221884"]
---

## 15. Programming workflows

### User-space utility

Use standard streams and exit codes; handle permissions, signals, malformed input, temporary files, locale, and interruption. Unit-test logic, integration-test syscalls, package it for target distributions, and trace it in each launch context.

### Network service

Define protocol, authentication, authorization, timeouts, backpressure, logging, metrics, TLS, resource limits, systemd/launchd integration, upgrade, and recovery. Test packet loss, slow clients, malformed requests, partial writes, restart, clock skew, and credential rotation.

### Filesystem/storage tool

Define crash consistency, fsync, atomicity, permissions, xattrs, sparse files, quotas, encryption, snapshots, case sensitivity, and recovery. Test power loss with loopback images and fault injection.

### Driver/system extension

Document hardware protocol, interrupts/DMA, power states, hotplug, reset, concurrency, firmware, user API, entitlements, security boundaries, and recovery. Test disconnects, suspend/resume, resource exhaustion, concurrent opens, malformed devices, and no-network conditions.

### GUI application

Separate UI, model, I/O, and privileged operations. Test accessibility, localization, scaling, multiple displays, sleep/wake, sandbox/privacy prompts, corrupted data, crash recovery, update, and uninstall.
