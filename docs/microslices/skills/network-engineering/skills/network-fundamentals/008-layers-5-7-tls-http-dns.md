---
id: skill-layers-5-7-tls-http-dns-d019076848
purpose: layers 5 7 tls http dns
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-the-tcp-three-way-handshake-129c809616"]
links: ["skill-network-devices-roles-and-layers-e7d53f5d8a"]
---

## Layers 5-7: TLS, HTTP, DNS

**TLS 1.3 handshake** (RFC 8446) completes in a single round trip: client sends supported cipher suites and key share in ClientHello; server responds with its key share, certificate, and verification — everything after ServerHello is encrypted. Both sides derive symmetric session keys. Only ephemeral key exchanges (ECDHE) are permitted, guaranteeing **forward secrecy** — compromising a server's long-term key cannot decrypt past sessions.

**HTTP versions**:
- HTTP/1.1: text-based, one request per connection (pipelining was unreliable)
- HTTP/2 (RFC 9113): binary framing, multiplexing — multiple requests over one TCP connection
- HTTP/3 (RFC 9114): uses QUIC (UDP), eliminates head-of-line blocking, 1-RTT connection setup (0-RTT for resumed)

HTTP status codes: 2xx success (200 OK, 201 Created), 3xx redirect (301 Permanent, 304 Not Modified), 4xx client error (400 Bad Request, 403 Forbidden, 404 Not Found), 5xx server error (500 Internal, 503 Unavailable).

**DNS resolution** when you visit `www.example.com`:
1. Browser checks cache → empty
2. Asks recursive resolver (ISP DNS or 8.8.8.8)
3. Resolver asks root server: "Where is .com?" → returns TLD server addresses
4. Resolver asks .com TLD: "Where is example.com?" → returns authoritative nameserver
5. Resolver asks authoritative server: "What is www.example.com?" → returns A record: `93.184.216.34`
6. Result cached for TTL duration (minutes to hours)

Key DNS record types: **A** (→IPv4), **AAAA** (→IPv6), **CNAME** (alias), **MX** (mail), **NS** (nameserver), **TXT** (SPF, DKIM, verification).

**DHCP DORA process**: Discover (client broadcasts from 0.0.0.0 to 255.255.255.255) → Offer (server proposes IP, subnet, gateway, DNS) → Request (client accepts) → Acknowledge (server confirms). Lease duration: typically 8 hours to 8 days. Client renews at 50% of lease.
