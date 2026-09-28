---
id: skill-troubleshooting-toolkit-755d8d90b7
purpose: troubleshooting toolkit
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-performance-metrics-b09b968337"]
links: ["skill-the-thread-connecting-everything-5cb90e2f0a"]
---

## Troubleshooting toolkit

| Tool | What it does | Example |
|------|-------------|---------|
| `ping` | Tests reachability (ICMP echo) | `ping 8.8.8.8` |
| `traceroute`/`tracert` | Shows hop-by-hop path | `traceroute google.com` |
| `nslookup`/`dig` | DNS queries | `dig +short example.com A` |
| `netstat`/`ss` | Shows active connections, listening ports | `ss -tulnp` |
| `tcpdump` | Captures packets on Linux | `tcpdump -i eth0 port 80` |
| `Wireshark` | GUI packet analysis | Filter: `tcp.port == 443` |
| `nmap` | Network scanning | `nmap -sV -p 1-1000 host` |
| `ip route` | Show routing table | `ip route show` |
| `arp -a` | Show ARP cache | Local MAC→IP mappings |

**Troubleshooting methodology — work the OSI stack**:
1. L1: Is the cable connected? Link lights on?
2. L2: ARP resolving? Any duplicate MACs? VLAN misconfiguration?
3. L3: Can you ping the default gateway? Is routing correct? NAT configured?
4. L4: Is the service listening on the right port? (`netstat`/`ss`)
5. L7: DNS resolving? TLS certificate valid? Application responding?
