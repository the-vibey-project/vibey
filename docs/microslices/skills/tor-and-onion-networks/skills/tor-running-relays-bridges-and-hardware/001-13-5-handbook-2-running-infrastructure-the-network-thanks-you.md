---
id: skill-13-5-handbook-2-running-infrastructure-the-network-thanks-you-7acb76ec1f
purpose: 13 5 handbook 2 running infrastructure the network thanks you
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-running-relays-bridges-and-hardware/SKILL.md
requires: []
links: ["skill-handbook-3-networking-patterns-048535e438"]
---

## §13.5 / Handbook §2. Running infrastructure (the network thanks you)

Decision tree: **home line** → bridge or Snowflake proxy. **VPS/colo with clean IP +
abuse-tolerant host** → middle/guard relay. **Dedicated IP, hostile-abuse-tolerant host,
willingness to do paperwork** → exit. Consult the community portal's good/bad-ISP list before
buying anything.

### §2.1 Middle relay (Debian/Ubuntu)

```bash
# Use Tor Project's own repo, not the distro's (fresher; 0.4.9.x as of 2026):
#   https://community.torproject.org/relay/setup/guard/debian-ubuntu/
sudo apt install tor nyx
```

```
# /etc/tor/torrc — middle/guard relay
ORPort 443
Nickname PickSomethingUnique
ContactInfo your-email@example.org
ExitRelay 0                 # default, stated to be explicit
BandwidthRate 20 MBytes
BandwidthBurst 25 MBytes
AccountingMax 4 TBytes      # cap monthly traffic if your host meters
AccountingStart month 1 0:00
MetricsPort 127.0.0.1:9035
MetricsPortPolicy accept 127.0.0.1
```

- Relay appears on [Relay Search](https://metrics.torproject.org/rs.html) within a few hours;
  flags (Fast/Guard/HSDir) accrue over days–weeks of uptime.
- Identity hygiene: `OfflineMasterKey 1` after moving `ed25519_master_id_secret_key` off the
  box (keep `ed25519_master_id_public_key` present).
- 0.4.9-era families: publish a **family key** (`tor --keygen-family`, proposal 321) *and* keep
  the legacy `MyFamily` cross-listing until client adoption saturates (§7.3 →
  `tor-network-consensus-guards-and-paths`).

> **⚠️ GOTCHA:** relays ramp **slowly**. First-month traffic is a trickle. That is
> consensus-weight design (§6.1 → `tor-network-consensus-guards-and-paths`), not
> misconfiguration — do not go chasing a bug that isn't there.

### §2.2 obfs4 bridge (the highest-value home contribution)

```
BridgeRelay 1
ORPort 9001
ServerTransportPlugin obfs4 exec /usr/bin/obfs4proxy
ServerTransportListenAddr obfs4 0.0.0.0:8443
ExtORPort auto
ContactInfo your-email@example.org
```

The complete `Bridge obfs4 ...` line (with cert + iat-mode) lands in
`/var/lib/tor/pt_state/obfs4_bridgeline.txt` — that's what a censored user pastes into Tor
Browser; you don't have to distribute it yourself (BridgeDB pulls bridges automatically).
Docker alternative: `thetorproject/obfs4-bridge`. Bridges want stable IPs; **the address *is*
the secret** (§10.2 → `tor-censorship-circumvention-and-bridges`).

### §2.3 WebTunnel bridge

Co-locates with a real HTTPS site on your host (WebSocket-like upgrade path shared between a
reverse proxy and the bridge). Guide: `community.torproject.org/relay/setup/webtunnel/`. As of
March 2026 the official Docker image lagged; operators were advised to build from source —
check the guide's current note. Value: works in protocol-allowlist networks where obfs4's
random-looking bytes get killed by default.

### §2.4 Snowflake proxy (the zero-hassle contribution)

```bash
docker run -d --network host thetorproject/snowflake-proxy:latest
# or: standalone binary; or just leave the Tor Browser add-on enabled in a pinned tab
```

A few Mbps, NAT-friendly by WebRTC design, runs anywhere. Because Russia began DTLS-fingerprint
blocking in March 2026, run the current standalone proxy (**≥ v2.13.1**, which ships the
covert-dtls mimicry — §10.3 → `tor-censorship-circumvention-and-bridges`). Your proxy IP is
never published; the broker matches clients to proxies.

### §2.5 Exit relay (read twice, run once)

```
ExitRelay 1
ReducedExitPolicy 1        # sane port set; blocks 25 and usual abuse ports
                           # (0.4.9 added Monero ports to this policy)
```

Mandatory homework first:

1. **A reverse-DNS + web notice.** Serve the Tor Project's `tor-exit-notice.html`
   (`contrib/operator-tools/tor-exit-notice.html`) on port 80 of your exit IP and set PTR to
   something unambiguous. This single artifact quietly resolves most complaints.
2. **A dedicated IP** (not shared with anything you care about) and an abuse-tolerant host.
3. **An abuse mailbox you actually answer** (auto-reply pointing to ExoneraTor and the exit
   list resolves most tickets; see §6).
4. **Never run an exit on a residential line; never run one at work.**
5. Consider 0.4.9 features: `ReevaluateExitPolicy` and the new `DoSStream*` token-bucket
   limiters for stream/resolve floods.

### §2.6 Running a private Tor network

If you have decided you need your own network rather than onion services on the public one
(§13.6 → `tor-building-on-tor-software-patterns`), this is the operator checklist:

1. **At least 3 directory authorities**, run on different infrastructure, in different
   locations, under different administrators — they are the trust root (see the gotcha
   below).
2. **Size the relay set to the deployment; there is no protocol-level relay-count minimum.**
   Three distinct relays is the floor for building a three-hop circuit at all, a test or
   permissioned deployment sized to its own known traffic can be legitimately small, and a
   public-facing service needs enough to carry peak load with capacity left over when some
   are down. Size against **bandwidth** (peak throughput plus headroom, remembering every
   circuit spends that capacity at three relays); **failure tolerance** (how many relays can
   drop before circuits fail or capacity does); **path diversity** (enough distinct
   operators, subnets and providers that the no-shared-operator and no-shared-subnet
   constraints still leave usable paths); and the **anonymity set** you intend to offer — a
   network small enough that a relay operator can guess who is talking provides no anonymity
   at any relay count. Pick the target from those four, write down the reasoning, and
   re-derive it when traffic or the threat model changes.
3. **Custom consensus parameters** configured, and **client software pointing at your
   authorities**, not the public ones.
4. **Chutney for testing before deployment** (§13.4c →
   `tor-building-on-tor-software-patterns`).
5. **Network monitoring and relay health checks** — nyx locally, MetricsPort/Prometheus
   externally (handbook §5, check 3).
6. **A plan for Sybil resistance.** Your network is smaller than public Tor and therefore
   cheaper to attack: consider requiring relay operators to be known, or running a
   **permissioned** model outright.
7. **Physical diversity of infrastructure**, and **NTP-disciplined clocks on every node** —
   anonymity systems are clock-sensitive (handbook §5, check 5).

> **⚠️ GOTCHA:** the authorities *are* the trust root (§6.2 →
> `tor-network-consensus-guards-and-paths`). Three of them on one provider, in one rack, under
> one administrator is not a trust root — it is a single point of compromise wearing a
> consensus protocol. Public Tor's nine are run by nine named people in different
> organizations and jurisdictions for exactly this reason, and a private network that skips
> that property has skipped the point.

---
