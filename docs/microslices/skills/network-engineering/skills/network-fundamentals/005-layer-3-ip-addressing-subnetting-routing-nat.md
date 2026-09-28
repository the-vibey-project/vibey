---
id: skill-layer-3-ip-addressing-subnetting-routing-nat-3ad0b83185
purpose: layer 3 ip addressing subnetting routing nat
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-layer-1-2-physical-media-ethernet-mac-addresses-switches-arp-vlans-6927395337"]
links: ["skill-layer-4-tcp-vs-udp-reliability-vs-speed-7f7ba1edb6"]
---

## Layer 3: IP addressing, subnetting, routing, NAT

**IPv4** (RFC 791, 1981) uses 32-bit addresses: `192.168.1.1`. 2³² = ~4.3 billion addresses. IANA exhausted them on February 3, 2011. RFC 1918 private ranges: `10.0.0.0/8` (~16.7M), `172.16.0.0/12` (~1M), `192.168.0.0/16` (~65K). These cannot appear on the public Internet.

**IPv6** (RFC 8200) uses 128-bit addresses: `2001:0db8:85a3::8a2e:0370:7334`. 2¹²⁸ ≈ 3.4 × 10³⁸ addresses — enough to assign trillions to every grain of sand on Earth.

**CIDR subnetting** (RFC 4632): a subnet mask divides an IP address into network bits (left) and host bits (right). CIDR notation appends the network bit count: `/24` = 24 network bits, 8 host bits, 2⁸−2 = **254 usable hosts**.

Quick reference:
| CIDR | Hosts | Usable | Example |
|------|-------|--------|---------|
| /8 | 16,777,216 | 16,777,214 | 10.0.0.0/8 |
| /16 | 65,536 | 65,534 | 172.16.0.0/16 |
| /24 | 256 | 254 | 192.168.1.0/24 |
| /25 | 128 | 126 | 192.168.1.0/25 |
| /26 | 64 | 62 | 192.168.1.0/26 |
| /27 | 32 | 30 | 192.168.1.0/27 |
| /28 | 16 | 14 | 192.168.1.0/28 |
| /30 | 4 | 2 | point-to-point links |

**Subnetting example**: Divide `192.168.1.0/24` into four equal subnets. Need 2 extra bits (2²=4), making /26. Each /26 has 62 usable hosts:
- `192.168.1.0/26` — hosts .1 to .62
- `192.168.1.64/26` — hosts .65 to .126
- `192.168.1.128/26` — hosts .129 to .190
- `192.168.1.192/26` — hosts .193 to .254

**NAT (RFC 3022)** lets many internal devices share a single public IP using port numbers (PAT). Device `10.0.0.10:3017` → NAT rewrites source to `203.0.113.1:1024` → records mapping → translates responses back. One public IP supports ~65,000 concurrent connections. NAT breaks end-to-end principle and complicates peer-to-peer, VoIP, and IPsec. CGNAT (100.64.0.0/10, RFC 6598) adds a second NAT layer at ISPs.

**Routing tables** use longest prefix match — the most specific matching entry always wins. When multiple protocols advertise the same prefix, administrative distance (AD) determines trust: Connected=0, Static=1, eBGP=20, OSPF=110, iBGP=200.
