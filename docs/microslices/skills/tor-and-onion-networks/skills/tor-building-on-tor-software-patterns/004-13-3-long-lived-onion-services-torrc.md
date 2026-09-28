---
id: skill-13-3-long-lived-onion-services-torrc-e06d718545
purpose: 13 3 long lived onion services torrc
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-2-the-control-port-and-ephemeral-onion-services-de20ae4049"]
links: ["skill-13-4-advertising-the-onion-from-your-clearnet-site-f40ed58b4e"]
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
