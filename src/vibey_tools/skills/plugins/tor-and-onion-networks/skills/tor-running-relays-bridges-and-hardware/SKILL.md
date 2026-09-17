---
name: tor-running-relays-bridges-and-hardware
description: "Use when running Tor infrastructure — middle and guard relays, obfs4 and WebTunnel bridges, Snowflake proxies, exit relays and their prerequisites, transparent-proxy gateways, DNS-leak prevention, Raspberry Pi and travel-router builds, two-box isolation, the SecureDrop architecture, the operator checklist for running a private Tor network, verification checklists, and legal and abuse handling. Covers §13.5 and handbook §2–§6. Companion to the other Tor and onion-network skills."
---

# Running Tor Infrastructure: Relays, Bridges, Gateways, Hardware

> **Part 8 of 8** of the *Tor and Onion Networks* reference (plugin `tor-and-onion-networks`),
> covering §13.5 and handbook §2–§6. Sibling skills:
> `tor-protocol-circuits-and-cell-cryptography` (§1–§5),
> `tor-network-consensus-guards-and-paths` (§6–§7),
> `tor-onion-services-and-hardening` (§8–§9),
> `tor-censorship-circumvention-and-bridges` (§10),
> `tor-attack-literature-and-threat-model` (§11),
> `tor-ecosystem-alternatives-and-governance` (§12, §14–§16),
> `tor-building-on-tor-software-patterns` (§13.1–§13.4 and handbook §1).
> Section numbers are shared across the set; a reference written as §N → `skill` points into
> that sibling skill.
>
> **Currency:** compiled 16 September 2026. Config checked against C tor **0.4.9.x**. Consult
> `man tor` and <https://community.torproject.org/> — especially the good/bad-ISP list —
> before buying hosting.
>
> **Scope note:** nothing here routes around the law. Relays, bridges and onion services are
> legal in most jurisdictions and abused in the same way roads are — run them openly, with
> notices, and handle abuse like an adult (§6).

> **⚠️ Choose by what your IP can absorb: home line → bridge or Snowflake. Clean VPS →
> middle/guard. Dedicated IP + abuse-tolerant host + paperwork → exit.**
>
> **⚠️ GOTCHA** boxes mark where an operator's reasonable assumption produces a leak, a dead
> SD card, or an abuse complaint they cannot answer.
>
> **The three ideas that organize this document:**
> 1. **⚠️ BRIDGES ARE THE HIGHEST-VALUE HOME CONTRIBUTION** (§2.2, §2.4). **A home IP is bad
>    for an exit and perfect for a bridge — residential, stable addresses are exactly what
>    censored users need, and bridges attract essentially no abuse mail.**
> 2. **⚠️ TRANSPARENT PROXYING IS CONVENIENCE, TWO BOXES ARE ASSURANCE** (§3.3, §4.4).
>    **A gateway that shares a machine with the thing it protects can be bypassed by whatever
>    roots that machine. When the Tor box is the *only* route out, a fully compromised
>    workstation still cannot learn the public IP.**
> 3. **⚠️ THE EXIT'S REAL PREREQUISITE IS A MAILBOX YOU ANSWER** (§2.5, §6). **The technical
>    configuration is four lines. The operational commitment is reverse DNS, an exit notice,
>    a dedicated IP, and replying to abuse — the volunteer network's social license depends
>    on operators who do that.**

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

2. **Size the relay set for bandwidth, failure tolerance, and the intended anonymity set** — there is no protocol-level relay-count minimum; production targets should be justified for the specific deployment.
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

## Handbook §4. Hardware builds

### §4.1 Raspberry Pi middle relay (the classic)

**BOM**: Pi 4/5 (2–4 GB), decent SD or USB SSD, 5 V/3 A PSU. All-in ≈ $75; ~5 W always-on.

- 64-bit Raspberry Pi OS Lite; the Cortex-A72/A76 have ARMv8 crypto extensions, so AES/POLYVAL
  paths are hardware-assisted (§4.2 → `tor-protocol-circuits-and-cell-cryptography`) — expect
  tens of Mbps of relayed throughput, uplink-willing.
- Use deb.torproject.org apt; set `MaxAdvertisedBandwidth` to ~70% of your real uplink; add
  `AvoidDiskWrites 1` or move to SSD — **SD cards die of log+descriptor churn**.
- Do **not** make it an exit (your home IP takes the abuse mail) — middle or obfs4 bridge.

### §4.2 Travel-router Tor gateway

GL.iNet Mango/Slate/Beryl-class OpenWrt boxes: install `tor` + the §3.3 transparent-proxy
config, or use models/3rd-party firmware with built-in Tor modes (InvizBox sells this
pre-canned).

> **⚠️ GOTCHA:** MIPS/ARM SoCs without crypto extensions cap out in the low tens of Mbps.
> Treat these as *convenience* devices for untrusted Wi-Fi, not high-assurance rigs — the
> network layer is enforced, but endpoint hygiene still lives on your laptop (§11.8 →
> `tor-attack-literature-and-threat-model`).

### §4.3 The Snowflake/bridge headless mini-box

Any idle SBC or old laptop + §2.4 (Snowflake) or §2.2 (obfs4 bridge). This is the cheapest real
help you can give censored users; bridges want residential-looking, stable IPs, so a quiet home
box is *better* than a datacenter for this role.

### §4.4 Two-box isolation gateway (physical Whonix)

Pattern (Whonix's model, in hardware): **Box A** (gateway) — tor + TransPort/DNSPort +
fail-closed nftables; it is the *only* device with a route to the internet. **Box B**
(workstation) — single ethernet link to A, no Wi-Fi, no other interfaces; all its traffic
transits Tor **by physics, not by configuration discipline**. A root-level compromise of B
still can't learn the public IP. Qubes 4.3 + Whonix 18 virtualizes the same topology on one
well-supported machine (§12.2 → `tor-ecosystem-alternatives-and-governance`).

### §4.5 Vault-grade: the SecureDrop architecture (study this even if you never run one)

The reference "serious hardware" onion deployment (docs.securedrop.org):

- **App + Monitor servers** behind dedicated firewall, FDE (LUKS), onion service only — no
  clearnet exposure at all.
- **Air-gapped Secure Viewing Station**: Tails on a machine that *never* networks; submissions
  cross the air gap on dedicated transfer media after decryption on the SVS.
- Admin/journalist Tails sticks with persistence isolated per role; v3 client auth on the onion
  interfaces so the services are invisible without keys.

The transferable lessons for any high-stakes build: **separate the *viewing* environment from
the *receiving* environment by an air gap; authenticate the service itself, not just its users;
FDE + offline identity keys; and assume the box will eventually be seized or rooted — design so
that's survivable.**

---

## Handbook §5. Verification & monitoring checklist

1. **Egress identity**: `https://check.torproject.org/api/ip` from every path you claim is
   Tor-routed; confirm the reported IP is a current exit on Relay Search / ExoneraTor.
2. **DNS**: tcpdump the physical interface while the app resolves — you should see *no*
   upstream queries except the tor process's own.
3. **Relay health**: nyx locally; Relay Search + MetricsPort/Prometheus externally; first flags
   within days, Guard eligibility after ~weeks of stability, HSDir after Fast+Stable.
4. **Onion service**: fetch the descriptor via a second tor instance
   (`torsocks curl http://<addr>.onion`), watch `hs_pow_*` metrics under load-test, confirm
   offline-master rotation procedure on a staging service first.
5. **Time**: anonymity systems are clock-sensitive (consensus validity, blinded-key periods).
   Disciplined NTP on everything. (Over Tor? NTP is UDP — use chrony over clearnet on gateway
   boxes; the risk model allows it.)

---

## Handbook §6. Legal, ethical & abuse-handling box

- Running relays, bridges, exits, and onion services is legal in the US, EU, and most
  democracies; *usage of them* is regulated like any internet use. A handful of states block or
  restrict Tor — that's censorship of users, not generally criminalization of operators. The
  EFF's *Tor Legal FAQ* and the Tor Project's abuse templates are the two documents to read
  before plugging anything in.
- **Middle relays** and **bridges** attract essentially no complaints; their IPs never touch
  destination servers. **Exits** attract automated abuse mail regularly — answer it with the
  standard response (point to ExoneraTor + exit docs, confirm no logging), and keep
  `ReducedExitPolicy` unless you know why you're widening it.
- Don't run exits from home or work IPs; **don't log user traffic** (it adds liability, not
  protection); don't run services whose purpose is harm — the volunteer network's social
  license is the thin thing standing between this infrastructure and legislated blocking, and
  operators are its custodians.
- Censorship-circumvention tooling (bridges, Snowflake, PTs) exists for the users the Tor
  Project names: dissidents, journalists, abuse survivors, ordinary people behind hostile
  networks. Build accordingly.

---

## Where to go next

- Writing code that talks to Tor: §13.1–§13.4 → `tor-building-on-tor-software-patterns`.
- What the flags, weights and consensus your relay is joining actually are: §6 →
  `tor-network-consensus-guards-and-paths`.
- Which transport to run, and what censors are currently blocking: §10 →
  `tor-censorship-circumvention-and-bridges`.
- Hardening an onion service you host on this hardware: §9 →
  `tor-onion-services-and-hardening`.
