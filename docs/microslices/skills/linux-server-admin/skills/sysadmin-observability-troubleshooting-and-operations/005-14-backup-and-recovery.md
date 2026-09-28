---
id: skill-14-backup-and-recovery-ac96ca6797
purpose: 14 backup and recovery
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-observability-troubleshooting-and-operations/SKILL.md
requires: ["skill-13-automation-and-configuration-management-e8adcfc970"]
links: []
---

## §14. Backup and Recovery

**⚠️ 3-2-1: three copies, two media, one offsite — and now "one offline or immutable,"
because ransomware targets the backup server first.**

**Tools**: `restic` and `borg` (⚠️ **deduplicating, encrypted, and the sane defaults for
most people**), `rsync` (⚠️ **`--link-dest` for hardlinked incrementals**), `zfs
send`/`btrfs send` for filesystem-native, `tar` for archives.

> **⚠️ GOTCHA — an untested backup is not a backup.** **Schedule restores.** The
> recurring failure modes are: backups silently stopped weeks ago, the encryption key was
> only on the machine that died, the restore takes 40 hours and RTO is 4, and the database
> backup is a file copy of a running database and is therefore corrupt.
> **⚠️ Databases need their own consistent dump or snapshot mechanism** — `pg_dump`,
> `mysqldump --single-transaction`, or a filesystem snapshot with the DB quiesced.

**Document and test**: RPO (how much data can you lose), RTO (how fast must you be back),
and ⚠️ **a written recovery procedure someone who isn't you can follow at 3am.**
