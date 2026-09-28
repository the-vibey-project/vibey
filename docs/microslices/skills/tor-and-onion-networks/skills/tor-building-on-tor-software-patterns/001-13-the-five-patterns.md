---
id: skill-13-the-five-patterns-88cbb20373
purpose: 13 the five patterns
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: []
links: ["skill-13-1-the-socks-interface-the-boring-correct-way-23c7b573ee"]
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
