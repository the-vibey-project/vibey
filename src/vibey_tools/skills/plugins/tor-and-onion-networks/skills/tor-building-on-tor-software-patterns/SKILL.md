---
name: tor-building-on-tor-software-patterns
description: "Use when writing code that talks to Tor — SOCKS with socks5h and stream isolation, the control port, ephemeral onion services via ADD_ONION or stem, long-lived onion services in torrc, client authorization v3, Onion-Location and Alt-Svc headers, torsocks and its limits, embedding Arti, testing against a private chutney network, and building your own private or custom onion-routing network. Covers §13.1–§13.4, §13.6 and handbook §1. Companion to the other Tor and onion-network skills."
---

# Building on Tor: Software Patterns

> **Part 7 of 8** of the *Tor and Onion Networks* reference (plugin `tor-and-onion-networks`),
> covering §13.1–§13.4, §13.6 and handbook §1. Sibling skills:
> `tor-protocol-circuits-and-cell-cryptography` (§1–§5),
> `tor-network-consensus-guards-and-paths` (§6–§7),
> `tor-onion-services-and-hardening` (§8–§9),
> `tor-censorship-circumvention-and-bridges` (§10),
> `tor-attack-literature-and-threat-model` (§11),
> `tor-ecosystem-alternatives-and-governance` (§12, §14–§16),
> `tor-running-relays-bridges-and-hardware` (§13.5 and handbook §2–§6).
> Section numbers are shared across the set; a reference written as §N → `skill` points into
> that sibling skill.
>
> **Currency:** compiled 16 September 2026. Config options checked against C tor **0.4.9.x**
> (stable since Feb 2026) and Arti **2.6.x** (Sept 2026). When in doubt: `man tor`,
> <https://community.torproject.org/>, <https://onionservices.torproject.org/>.

> **⚠️ Five patterns cover essentially all software built on Tor. Pick the one that matches
> your assurance requirement, not the one that is least work.**
>
> **⚠️ GOTCHA** boxes mark where the obvious approach silently leaks.
>
> **The three ideas that organize this document:**
> 1. **⚠️ `socks5h`, NOT `socks5`** (§13.1). **The `h` makes the *exit* resolve the hostname.
>    Without it you do a local DNS lookup for the destination you are trying to hide — the
>    single most common Tor-integration leak, and it fails silently.**
> 2. **⚠️ STREAM ISOLATION IS A PRODUCT DECISION, NOT A TUNING KNOB** (§13.1). **SOCKS
>    username/password pairs become isolation tokens, so distinct credentials get distinct
>    circuits. That is how you stop two tenants, or two identities, sharing an exit.**
> 3. **⚠️ EPHEMERAL SERVICES BEAT FILESYSTEM KEYS FOR MOST APPS** (§13.2). **`ADD_ONION
>    NEW:ED25519-V3 Flags=DiscardPK` keeps the key in memory only and dies with the process.
>    OnionShare, Ricochet Refresh and Briar all work this way — no key management, no torrc
>    edits, nothing on disk to seize.**

---

## §13. The five patterns

Conceptually, building on Tor falls into five patterns:

1. **SOCKS-integrated apps** — the minimal, safest pattern: point your app at tor's SocksPort
   (127.0.0.1:9050; 9150 for Tor Browser) using `socks5h` so DNS resolves *at the exit*. Add
   stream-isolation credentials per tenant/connection class.
2. **Ephemeral onion services** — your app speaks `ADD_ONION NEW:ED25519-V3` to the control
   port, publishes a one-shot service, and tears it down on exit.
3. **Long-lived onion services** — torrc `HiddenServiceDir`/`HiddenServicePort`, optionally
   client auth, offline master keys, PoW, Onionbalance backends, and Onion-Location/Alt-Svc on
   the clearnet twin.
4. **Embedding Tor** — ship tor/Arti as a library (arti-client crate, Tor.framework,
   IPtProxy/tor-android, onionmasq for VPN-style capture) inside your product.
5. **Network-layer building** — relays, bridges, exits, transparent-proxy gateways, two-box
   isolation. See §13.5 → `tor-running-relays-bridges-and-hardware`.

Building your *own* network — rather than building on Tor — is a different decision tree with
its own three options: §13.6.

---

## §13.1 The SOCKS interface (the boring, correct way)

- C tor default: `127.0.0.1:9050`. Tor Browser: `9150`.
- **Always use `socks5h` / `--socks5-hostname`** so name resolution happens *at the exit* —
  otherwise you resolve DNS locally and leak the destination.

```bash
# Verify egress + get your exit IP (official oracle):
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip
# → {"IsTor":true,"IP":"<exit-address>"}

# Per-connection stream isolation: SOCKS username/password become isolation tokens
# (IsolateSOCKSAuth is default). Two different credentials → two different circuits.
curl --socks5 127.0.0.1:9050 --proxy-user tenant-a:pw https://example.org
curl --socks5 127.0.0.1:9050 --proxy-user tenant-b:pw https://example.org
```

```python
# Python; needs requests[socks]
import requests
s = requests.Session()
s.proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
print(s.get("https://check.torproject.org/api/ip").json())
```

Stream isolation flags you should know (apply per `SocksPort` line):

```
SocksPort 9050 IsolateDestAddr IsolateDestPort   # one circuit per destination host+port
SocksPort 9062                                    # dedicated port for one app = hard isolation
```

### Per-site circuits in your own tooling

Tor Browser isolates streams per first-party domain. Replicate the idea in services: distinct
SOCKS credentials per logical tenant, or `NEWNYM`-driven circuit freshening via the control
port for long batch jobs.

> **⚠️ GOTCHA:** `SIGNAL NEWNYM` is rate-limited to roughly once per 10 seconds, and **it does
> not reset your guards** (by design — see §7.1 → `tor-network-consensus-guards-and-paths`).
> Use isolation credentials when you can; NEWNYM is the blunt instrument.

---

## §13.2 The control port and ephemeral onion services

Enable the controller (Debian/Ubuntu pattern):

```
ControlPort 9051
CookieAuthentication 1
CookieAuthFileGroupReadable 1     # then: sudo usermod -aG debian-tor youruser
```

**Ephemeral onion service** — no torrc edits, keys live only in memory (this is the
OnionShare / Ricochet Refresh pattern). With **stem** (`pip install stem`; unmaintained since
~2020 but still the canonical library — see §12.3 →
`tor-ecosystem-alternatives-and-governance`):

```python
from stem.control import Controller

with Controller.from_port(port=9051) as ctl:
    ctl.authenticate()  # reads the cookie automatically
    svc = ctl.create_ephemeral_hidden_service(
        {80: ("127.0.0.1", 8000)},   # onion :80 -> local 8000
        await_publication=True,
    )
    print(f"http://{svc.service_id}.onion")
    # keep the controller connection open; the service dies when it closes
    input("Serving. Press enter to tear down.\n")
```

Raw protocol equivalent (useful when porting to other languages — spec: `control-spec.txt`):

```
AUTHENTICATE <cookie-hex>
ADD_ONION NEW:ED25519-V3 Flags=DiscardPK Port=80,127.0.0.1:8000
```

`Flags=DiscardPK` tells tor *not* to return the private key (service unrecoverable by design).
Async alternatives: **txtorcon** (Twisted, most battle-tested for services), **aiostem**
(asyncio).

---

## §13.3 Long-lived onion services (torrc)

```
HiddenServiceDir /var/lib/tor/mysvc/
HiddenServiceNumIntroductionPoints 3
HiddenServicePort 80 127.0.0.1:8080        # onion :80 -> local web app
#HiddenServicePort 443 unix:/run/mysvc.sock # unix sockets supported
```

- Address and keys appear under `HiddenServiceDir` (`hostname` file holds the 56-char
  address). Permissions must be `0700`, owned by the tor user.
- **Offline master keys**: generate the `hs_ed25519_secret_key` on an offline machine
  (`tor --keygen` in a scratch datadir), archive the encrypted master, and deploy only the
  signing material — a box compromise then doesn't compromise the address permanently.
- **DoS hardening** (PoW, requires tor built with `--enable-gpl` for Equi-X/HashX):

```
HiddenServicePoWDefensesEnabled 1
HiddenServicePoWQueueRate 250
HiddenServicePoWQueueBurst 2500
MetricsPort 127.0.0.1:9035
MetricsPortPolicy accept 127.0.0.1    # scrape tor_hs_pow_* with Prometheus
```

- **Client authorization v3** (private services): the server keeps an `authorized_clients/`
  directory inside `HiddenServiceDir`, one `<name>.auth` file per client containing
  `descriptor:x25519:<base32-pubkey-no-padding>`; each client adds a `<56chars>.auth_private`
  file (`<addr>.onion:descriptor:x25519:<base32-priv>`) to its `ClientOnionAuthDir`. Generate
  x25519 pairs with any standard crypto library and base32-encode the raw 32-byte keys per
  `rend-spec-v3`.
- **Load balancing**: run `HiddenServiceOnionbalanceInstance 1` on each backend pointing at
  the Onionbalance master.

> **⚠️ GOTCHA (as of 2026): PoW and Onionbalance don't mix.** Choose per threat model — DoS
> resistance on a single instance, or horizontal scale across backends. See §9.2–§9.3 →
> `tor-onion-services-and-hardening`.

---

## §13.4 Advertising the onion from your clearnet site

```nginx
# nginx — Tor users get the ".onion available" pill (Tor Browser ≥ 9.5)
add_header Onion-Location http://<your56>.onion$request_uri;

# transparent variant: Tor-capable clients switch to onion silently
add_header Alt-Svc 'h2="<your56>.onion:443"; ma=86400';
```

Serve these over HTTPS from the clearnet origin only (**never** from the onion itself).

---

## §13.4a Non-SOCKS apps: torsocks and its honest limits

```
torsocks curl https://check.torproject.org/api/ip
```

torsocks is `LD_PRELOAD` shimming: TCP only, breaks on apps using raw syscalls, no UDP, and it
*silently* does nothing for apps that bypass libc (statically linked Go/Rust binaries).

> **⚠️ GOTCHA — this is the dangerous one.** A statically linked binary under `torsocks`
> connects **directly**, with no error and no warning. Rule of thumb: **torsocks for
> convenience, never for high-stakes assurance.** For assurance, use app-native SOCKS or a
> fail-closed network sandbox (§13.5 → `tor-running-relays-bridges-and-hardware`, §4.3–4.4).
> `proxychains` shares the architecture *and* the caveats, with worse defaults.

---

## §13.4b Arti as a library and daemon

Arti (Rust) is the future embedding path: no fork of an external process, memory safety, and —
since 1.8.0 (Dec 2025) — production-grade onion services with native vanguards.

```toml
# ~/.config/arti/arti.toml  (minimal client)
[proxy]
socks_listen = "127.0.0.1:9150"
dns_listen = "127.0.0.1:15354"
```

```rust
// embedding: arti-client = "0..." (API churned through 2.x — pin + read changelog)
use arti_client::{TorClient, TorClientConfig};

let tor = TorClient::create_bootstrapped(TorClientConfig::default()).await?;
let stream = tor.connect(("check.torproject.org", 443)).await?;
```

C-tor → Arti service migration: `arti hsc ctor-migrate` (2.x) ports hidden-service keys. Watch
the `arti hss` tooling and Arti RPC — both are the fast-moving surface in 2026. **onionmasq**
(from the Tor VPN project) gives you a userspace TUN interface over Arti: route whole
applications without them knowing.

---

## §13.4c Developing against a test network: chutney

**Never integration-test against the production network.** Chutney runs a private mini-Tor on
localhost:

```bash
git clone https://gitlab.torproject.org/tpo/core/chutney.git
cd chutney
./chutney configure networks/basic
./chutney start    networks/basic
./chutney verify   networks/basic
./chutney status   networks/basic   # shows per-node SOCKS/Control ports to point tests at
```

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

## Where to go next

- Relays, bridges, exits, transparent proxies, hardware builds, verification and abuse
  handling: §13.5 → `tor-running-relays-bridges-and-hardware`.
- What a v3 onion service is actually doing underneath this configuration: §8 →
  `tor-onion-services-and-hardening`.
- Why `socks5h` matters — where the anonymity boundary actually sits: §3.3 →
  `tor-protocol-circuits-and-cell-cryptography`.
- Library and implementation choices: §12 → `tor-ecosystem-alternatives-and-governance`.
