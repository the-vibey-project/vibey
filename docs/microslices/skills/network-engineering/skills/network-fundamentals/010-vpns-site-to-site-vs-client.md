---
id: skill-vpns-site-to-site-vs-client-5b81299002
purpose: vpns site to site vs client
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-network-devices-roles-and-layers-e7d53f5d8a"]
links: ["skill-data-center-networking-spine-leaf-0f660a8c73"]
---

## VPNs: site-to-site vs client

**Site-to-site VPN**: connects two entire networks (e.g., office to data center). Transparent to end users. Uses IPsec (tunnel or transport mode).

**Client VPN (remote access)**: individual device connects to corporate network. Options:
- **IPsec**: strong security, complex NAT traversal issues
- **OpenVPN**: TLS-based, runs over TCP or UDP, firewall-friendly
- **WireGuard**: modern, simple, high-performance, uses ChaCha20/Poly1305 cryptography

VPNs encrypt traffic and provide network-level access but grant broad network access upon authentication — a violation of least privilege. Zero Trust Network Access (ZTNA) is replacing VPNs for this reason.
