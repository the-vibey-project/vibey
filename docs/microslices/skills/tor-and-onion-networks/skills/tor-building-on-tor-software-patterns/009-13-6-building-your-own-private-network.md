---
id: skill-13-6-building-your-own-private-network-3d617c4fc3
purpose: 13 6 building your own private network
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-4c-developing-against-a-test-network-chutney-51d284581b"]
links: ["skill-where-to-go-next-d07a74871b"]
---

## §13.6 Building your own private network

"I want a private network" almost always resolves to one of three architectures, separated by
two orders of magnitude of effort. Pick before you build.

| Option | What it is | When it is right |
|---|---|---|
| **A — public Tor + v3 onion services with client authorization** | Your services are onion services on the public network; only holders of a client key can see them | Almost every real case: organizational privacy, private infrastructure, SecureDrop- and OnionShare-style deployments |
| **B — your own Tor network** | Your own directory authorities, relays and clients, isolated from public Tor | Testing, research, or a closed organizational network that must not touch public Tor at all |
| **C — a custom onion routing network** | Tor-like software of your own, with different trade-offs | Research, or a genuinely different threat model (§13.6.3) |

### §13.6.1 Option A — use the public Tor network (the right answer for most cases)

Run a tor client on your server, configure a `HiddenServiceDir` with client authorization
(§13.3), distribute `.auth_private` files to your authorized users, and let them connect via
Tor Browser or a Tor-integrated application. The service is invisible to anyone without a
client key. You get location-anonymous hosting, encryption by construction, authentication of
*both* directions, and the whole public relay set — without operating any of it. Add PoW for
DoS resistance and vanguards for guard-discovery resistance (§9 →
`tor-onion-services-and-hardening`). This is what SecureDrop and OnionShare do.

> **⚠️ GOTCHA:** running your own network *reduces* your anonymity set. On public Tor your
> traffic hides among several million daily users; on a twenty-relay private network,
> "someone used the network" is a much smaller set, and its operator knows who the
> participants are. Isolation from public Tor is an availability and control property, not an
> anonymity upgrade — choose B or C because you need control, never because you want more
> anonymity than A gives you.

### §13.6.2 Option B — run your own Tor network (chutney, and past it)

Chutney is not only a test harness (§13.4c). `networks/basic` is a complete miniature Tor —
**3 directory authorities plus relays and clients** — and a custom network definition is how
you grow one:

```bash
./chutney configure networks/basic   # 3 authorities + relays + clients
# For a larger private network, write a custom network definition with your own
# authorities, relays and exits. Each node gets its own torrc and data directory.
```

For a *production* private network you need: **at least 3 directory authorities**, run on
different infrastructure in different locations; a sufficient number of relays for bandwidth
and redundancy; your own consensus process (your authorities vote hourly exactly as public
Tor's nine do — §6.2 → `tor-network-consensus-guards-and-paths`); and client software
configured to use *your* authorities instead of the public ones. It is a substantial
undertaking, and what it buys is complete control over who participates. Operator mechanics
and the verification checklist: handbook §2 and §5 →
`tor-running-relays-bridges-and-hardware`.

### §13.6.3 Option C — build a custom onion routing network

If you want something Tor-like with different trade-offs — different circuit lengths, guard
strategies, crypto — four core components have to exist; onion services are optional:

1. **Relay software.** Authenticates to neighbours (ed25519 identities), accepts
   circuit-building commands, performs onion encryption/decryption on relay cells (§3 →
   `tor-protocol-circuits-and-cell-cryptography`).
2. **Directory system.** Some mechanism for clients to discover relays — Tor's nine
   hourly-voting authorities, a single trusted directory server, a threshold-signature scheme,
   a DHT, a blockchain. The two properties that matter whatever you pick: **clients must get a
   consistent view of the relay set**, and **an attacker must not be able to inject relays
   cheaply**.
3. **Path selection.** Three relays subject to constraints (no shared operator, no shared
   subnet, exit policy permits the destination), guards pinned for months (§7 →
   `tor-network-consensus-guards-and-paths`). The algorithm *is* the anonymity property.
4. **Client software.** Telescoping circuit construction, guard state, a SOCKS interface,
   stream isolation (§13.1).
5. **Onion services (optional).** Introduction points, descriptor publication to HSDirs,
   rendezvous points, client authorization, and a key-derived self-authenticating address
   (§8 → `tor-onion-services-and-hardening`).

> **⚠️ KEY DESIGN PARAMETERS.** Circuit length (3 is standard; more hops raise latency and
> the attacker's cost together). Guard rotation period (months is standard; shorter raises
> exposure probability). Directory trust model (authorities vs. DHT vs. blockchain). Crypto
> primitives (ntor for the handshake; CGO or an AEAD for cells). Whether to support onion
> services. Whether to support pluggable transports. Whether the network is **open** (anyone
> joins) or **closed** (known participants only). These seven choices determine what your
> network is; everything else is implementation.

Implementation checklist:

- **Use vetted cryptographic libraries** (libsodium, libsecp256k1) — never implement
  primitives yourself.
- **ntor or X25519 for the handshake** (§4.1 → `tor-protocol-circuits-and-cell-cryptography`).
- **An AEAD for cell crypto** (ChaCha20-Poly1305 or AES-GCM). **Do not use CTR mode without
  authentication** — malleability is exactly what enables tagging attacks (§4.2 →
  `tor-protocol-circuits-and-cell-cryptography`). Note that Tor's own CGO is *not* a stock
  AEAD: it needs a rugged PRP because relays must transform cells through a deliberately
  malleable decrypt path. Reach for CGO only if you have that same constraint; otherwise a
  standard AEAD per hop is the safer build.
- **Guard pinning from day one** and **path restrictions (family, subnet) from day one** —
  both are far harder to retrofit than to build in.
- **Test against chutney-style adversarial scenarios** (§13.4c).
- **Have a plan for relay discovery and Sybil resistance** before you have relays.
- **Consider using Arti as a foundation rather than starting from zero** (§12.1 →
  `tor-ecosystem-alternatives-and-governance`).

---
