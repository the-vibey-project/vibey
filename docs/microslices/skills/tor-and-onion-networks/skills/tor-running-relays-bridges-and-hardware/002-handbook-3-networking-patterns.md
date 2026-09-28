---
id: skill-handbook-3-networking-patterns-048535e438
purpose: handbook 3 networking patterns
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-running-relays-bridges-and-hardware/SKILL.md
requires: ["skill-13-5-handbook-2-running-infrastructure-the-network-thanks-you-7acb76ec1f"]
links: ["skill-handbook-4-hardware-builds-e0052f71ac"]
---

## Handbook §3. Networking patterns

### §3.1 Selective app routing without touching the app

Give the app its own `SocksPort` (isolation by construction), or a `TransPort`+`DNSPort` pair
bound to a dedicated local subnet. Prefer SocksPort whenever the app cooperates (§13.1 →
`tor-building-on-tor-software-patterns`).

### §3.2 DNS without leaks

- In-app: `socks5h`. Command-line resolve through Tor: `tor-resolve`.
- Whole-machine: `DNSPort 5353` + firewall redirect (§3.3). Tor resolves via exit-side streams;
  TTLs are clipped to 60s in 0.4.9 (cache-oracle mitigation).

### §3.3 Transparent proxy gateway (Tor router)

```
VirtualAddrNetworkIPv4 10.192.0.0/10
AutomapHostsOnResolve 1
TransPort 192.168.42.1:9040
DNSPort  192.168.42.1:5353
```

Then redirect transit traffic (nftables sketch — adapt to your host; **the tor daemon's uid
must be exempt or it eats its own traffic**):

```
nft add table ip tor
nft 'add chain ip tor prerouting { type nat hook prerouting priority dstnat; }'
nft add rule ip tor prerouting iifname "lan0" meta l4proto tcp dnat to 192.168.42.1:9040
nft add rule ip tor prerouting iifname "lan0" udp dport 53 dnat to 192.168.42.1:5353
```

> **⚠️ GOTCHA — honest limits of transparent proxying:** UDP-only apps fail or must be blocked
> (block them — silently is fine); apps pinning certificates/keys may break; and "the gateway
> saw everything" metadata still exists on the LAN side. For assurance use two boxes (§4.4):
> the Tor box is the *only* route out, full stop.

---
