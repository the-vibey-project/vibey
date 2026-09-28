---
id: skill-19-command-reference-2bc6732222
purpose: 19 command reference
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-reference/SKILL.md
requires: ["skill-18-books-59ff0a57ae"]
links: ["skill-20-method-a71adc6e9a"]
---

## §19. Command Reference

### 19.1 The fifteen that carry most of the load
```
systemctl status|list-units --failed|cat|edit      service truth
journalctl -u X -f | -p err -b | -b -1             log truth
ss -tulpn                                          what's listening
ip -br a · ip r get IP                             network truth
lsblk -f · df -h · df -i                           storage truth
du -xh --max-depth=1 /                             where did the space go
lsof +L1                                           ⚠️ deleted-but-open files
free -m                                            ⚠️ read "available"
vmstat 1 · iostat -xz 1 · mpstat -P ALL 1          saturation
dmesg -T | tail -50                                ⚠️ OOM, hardware, resets
ps auxf · pstree -p                                process tree
strace -f -p PID  /  execsnoop, opensnoop          ⚠️ what is it actually doing
ausearch -m avc -ts recent                         SELinux denials
nft list ruleset                                   firewall truth
find /etc -name '*.rpmnew' -o -name '*.dpkg-dist'  ⚠️ config drift after updates
```

### 19.2 First five minutes on an unfamiliar sick box
```
uptime; w                          load, who's on, how long up
systemctl list-units --failed      ⚠️ start here
journalctl -p err -b --no-pager | tail -50
dmesg -T | tail -50                ⚠️ OOM? disk errors? link flaps?
df -h; df -i                       ⚠️ both
free -m                            available, and swap activity
ss -tulpn                          expected listeners present?
vmstat 1 5; iostat -xz 1 5         where's the saturation
ip -br a; ip r                     network sane?
timedatectl                        ⚠️ clock right? NTP synced?
last -n 20; journalctl -u sshd | tail   who's been on
```

### 19.3 Pre-change checklist
- [ ] Do I know what this currently does, and have I captured it? (`systemctl cat`, backup the file)
- [ ] Is there a rollback, and can I execute it without network access? (§6.3 → `sysadmin-systemd-storage-and-networking`)
- [ ] Second SSH session open before touching sshd or the firewall? (§9.4 → `sysadmin-packages-boot-and-hardening`)
- [ ] `sshd -t` / `nft -c` / `visudo` / `mount -a` — syntax validated? (§5.3 → `sysadmin-systemd-storage-and-networking`, §9.4 → `sysadmin-packages-boot-and-hardening`)
- [ ] `daemon-reload` after unit changes? (§4.1 → `sysadmin-systemd-storage-and-networking`)
- [ ] Will config management revert this? (§11.2 → `sysadmin-observability-troubleshooting-and-operations`)
- [ ] Is this change in source control? (§13 → `sysadmin-observability-troubleshooting-and-operations`)
- [ ] Do I know how to tell whether it worked, and whether anything else broke?

---
