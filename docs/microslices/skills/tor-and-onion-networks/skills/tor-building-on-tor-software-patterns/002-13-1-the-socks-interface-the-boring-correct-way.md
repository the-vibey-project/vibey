---
id: skill-13-1-the-socks-interface-the-boring-correct-way-23c7b573ee
purpose: 13 1 the socks interface the boring correct way
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-the-five-patterns-88cbb20373"]
links: ["skill-13-2-the-control-port-and-ephemeral-onion-services-de20ae4049"]
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
