---
id: skill-13-2-the-control-port-and-ephemeral-onion-services-de20ae4049
purpose: 13 2 the control port and ephemeral onion services
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-1-the-socks-interface-the-boring-correct-way-23c7b573ee"]
links: ["skill-13-3-long-lived-onion-services-torrc-e06d718545"]
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
