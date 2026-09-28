---
id: skill-13-automation-and-configuration-management-e8adcfc970
purpose: 13 automation and configuration management
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-observability-troubleshooting-and-operations/SKILL.md
requires: ["skill-12-containers-and-namespaces-f5fa36b2a7"]
links: ["skill-14-backup-and-recovery-ac96ca6797"]
---

## §13. Automation and Configuration Management

**⚠️ The principle: the box is disposable, the source of truth is the repo.**
**Ansible** (agentless over SSH, ⚠️ **the low-friction default**), **Puppet/Chef/Salt**
(agent-based, stronger for continuous enforcement), **Terraform/OpenTofu** for
infrastructure, **cloud-init** for first boot, **Packer** for images.

**⚠️ Idempotence is the property that matters** — running twice must equal running once.
**Test with `--check --diff` before applying.**

**Immutable infrastructure** — build an image, deploy it, ⚠️ **never patch in place;
replace.** **Reduces drift to zero, at the cost of build pipeline complexity.**

**⚠️ Practical discipline that pays for itself**: everything in git including `/etc`
(consider `etckeeper`), **change one thing at a time**, **stage before production**, and
**a documented rollback for anything you can't undo in five minutes.**

---
