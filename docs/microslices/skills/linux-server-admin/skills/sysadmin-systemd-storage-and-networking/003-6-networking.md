---
id: skill-6-networking-bda8ff045c
purpose: 6 networking
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-systemd-storage-and-networking/SKILL.md
requires: ["skill-5-storage-94c4fefc3f"]
links: []
---

## §6. Networking

### 6.1 The modern commands
**⚠️ `ifconfig`, `netstat`, `route` and `arp` are deprecated. Learn `ip` and `ss`.**
```
ip a · ip -br a                  ⚠️ -br is the readable one
ip r · ip r get 8.8.8.8          ⚠️ shows which route/interface a dest actually uses
ip -s link                       per-interface error/drop counters
ip neigh                         ARP/NDP table
ss -tulpn                        ⚠️ listening TCP/UDP with process — replaces netstat
ss -s                            socket summary
ss -tan state time-wait | wc -l  TIME_WAIT count
```

### 6.2 Diagnosis, in order
```
ip a                    do I have an address?
ip r                    do I have a route?
ping -c3 <gateway>      is L2/L3 up locally?
ping -c3 1.1.1.1        is routing working? (⚠️ ICMP may be filtered — not proof of down)
dig @1.1.1.1 example.com   is DNS working, bypassing local resolver?
dig example.com         does the SYSTEM resolver work?  ⚠️ compare with the above
curl -v https://host/   does the application layer work?
mtr -rwc100 host        ⚠️ where is loss/latency introduced, per hop
ss -tulpn               am I actually listening, and on which address?
tcpdump -ni any port 443 -c 50   what's on the wire
```
**⚠️ The single most common network "outage" is DNS**, and the second most common is a
service listening on `127.0.0.1` instead of `0.0.0.0`. **`ss -tulpn` distinguishes them
instantly.**

**⚠️ Resolution on modern systems**: `/etc/resolv.conf` may be a symlink managed by
`systemd-resolved` — **use `resolvectl status` and `resolvectl query name`**, because
editing `/etc/resolv.conf` directly gets silently overwritten.

### 6.3 Firewalling
**⚠️ `nftables` is the modern backend; `iptables` commands are usually a shim onto it.**
```
nft list ruleset                        ⚠️ the source of truth
firewall-cmd --list-all                 (RHEL family)
firewall-cmd --permanent --add-service=https && firewall-cmd --reload
ufw status verbose · ufw allow 443/tcp  (Debian/Ubuntu)
```
**⚠️ Two rules that prevent lockouts**: **allow SSH before enabling any firewall**, and
**when changing rules remotely, schedule a rollback first** —
`echo "nft flush ruleset" | at now + 5 minutes` or a `systemd-run --on-active=5m` revert.
Cancel it once you've confirmed you're still connected.

### 6.4 Tuning that actually matters
```
net.core.somaxconn = 4096              ⚠️ listen backlog cap — raise for busy servers
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.ip_local_port_range = 10240 65535    ⚠️ ephemeral port exhaustion
net.ipv4.tcp_tw_reuse = 1              ⚠️ safe; tcp_tw_recycle was REMOVED — never use it
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr   ⚠️ notably better on lossy/long-fat links
fs.file-max / nofile limits            for high connection counts
```
**⚠️ Apply via `/etc/sysctl.d/*.conf` and `sysctl --system`**, not by editing
`/etc/sysctl.conf` — packaging and ordering are cleaner.
