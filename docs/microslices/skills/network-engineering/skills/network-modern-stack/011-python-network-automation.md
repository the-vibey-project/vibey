---
id: skill-python-network-automation-379d08f99d
purpose: python network automation
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-chaos-engineering-for-networks-7918e2f652"]
links: ["skill-the-five-convergent-gold-standards-for-2026-26a4a36d16"]
---

## Python network automation

### The essential toolkit (2026 versions)

**Nornir 3.5.0** (Python 3.9+): pure-Python automation framework. Benchmarks at roughly **100× faster than Ansible** for network device operations, using multi-threaded task execution with plugin architecture (nornir-netmiko, nornir-scrapli, nornir-napalm).

**Scapy 2.7.0**: gold standard for packet crafting, analysis, and protocol research. Replaces ~85% of nmap, hping, arpspoof, and tcpdump functionality in a single library.

**Netmiko 4.6.0**: supports ~80 device types across Cisco, Arista, Juniper, Nokia, Fortinet, Palo Alto. Abstracts SSH through Paramiko.

**NAPALM ~5.0.0**: vendor-neutral API for configuration management — diff, rollback, validation — across Cisco IOS/IOS-XR/NX-OS, Arista EOS, Juniper Junos.

**AsyncSSH 2.22.0** / **Scrapli**: use for managing hundreds to thousands of concurrent connections. Use Paramiko/Netmiko for standard device automation; use AsyncSSH or Scrapli for massive concurrency.

**pygnmi 0.8.15**: gNMI Get/Set/Subscribe for streaming telemetry subscriptions.

### Async automation pipeline for 1000+ devices

The gold-standard four-stage pattern: Inventory (NetBox API) → Dispatcher (Nornir filtering by site/role) → Workers (ThreadPoolRunner with 50-100 threads) → Aggregator (structured JSON/DB results with validation).

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio

sem = asyncio.Semaphore(50)  # Max 50 concurrent connections

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
async def configure_device(device):
    async with sem:
        async with asyncssh.connect(device['host']) as conn:
            result = await conn.run('show version')
            return result.stdout
```

Rate limiting uses `asyncio.Semaphore`. Error handling uses **tenacity** with exponential backoff. Python 3.11+'s `asyncio.TaskGroup` enables structured concurrency with `except*` for handling multiple failures.

### CI/CD validation pipeline

**Batfish**: gold standard for offline network configuration validation. Builds mathematical models from device configs and validates BGP sessions, ACL rules, and routing behavior without touching live devices.

Pipeline: Git push → lint configs → Batfish pre-deployment validation → deploy to staging via Nornir → pytest network assertions → production deploy with approval gate.
