---
id: skill-6-developing-on-monero-02ab03f199
purpose: 6 developing on monero
source: src/vibey_tools/skills/plugins/money-on-the-internet/skills/money-monero/SKILL.md
requires: ["skill-5-using-monero-in-2026-access-is-the-hard-part-a1ba946370"]
links: ["skill-7-assessment-contested-by-nature-613787c9a3"]
---

## 6. Developing on Monero

Monero dev ≠ Bitcoin dev. **There is no public address to watch, no script system, no tokens, no smart contracts.** Integration is daemon + wallet-RPC + proof machinery.

### The stack
- **`monerod`** — the daemon (P2P + consensus). RPC on port 18081: `get_info`, `get_block`, `send_raw_transaction`, fee estimates, `hard_fork_info`.
- **`monero-wallet-rpc`** — the wallet interface (JSON-RPC, port 18082): `create_wallet`, `get_address`, `make_integrated_address` (legacy), `create_account`/`create_address` (subaddresses), `transfer`, `transfer_split`, `get_balance`, `incoming_transfers`, `get_tx_key`, `check_tx_proof`, `sign`/`verify`, `export_view_key`, multisig RPCs.
- Libraries: **monero-cpp**, **monero-ts** (formerly monero-javascript — a full WASM wallet stack usable headless in Node), plus community Python/Go RPC wrappers.
- Networks: **mainnet / stagenet / testnet** — use stagenet for integration tests.
- Advanced: **BTC↔XMR atomic-swap protocol** (COMIT/UnstoppableSwap) — worth studying as the most production-real cross-chain primitive touching XMR; **M-of-N multisig** exists (threshold via multi-round key ceremony, no scripting).

### Canonical integration flows
```bash
# Watch-only audit wallet: view key + address, no spend key
monero-wallet-cli --generate-from-view-key audit.wallet

# Merchant-style receive: one subaddress per invoice
monero-wallet-rpc --daemon-address node.moneroworld.com:18089 ...
curl -X POST http://127.0.0.1:18082/json_rpc -d '{
  "jsonrpc":"2.0","id":"0","method":"create_address",
  "params":{"account_index":0,"label":"invoice-1042"}}'
# then poll incoming_transfers by subaddress_indices, enforce >=10 confs
```

```json
// Prove a payment was made (sender provides tx_key; recipient/checker verifies):
{"jsonrpc":"2.0","id":"0","method":"check_tx_proof",
 "params":{"txid":"…","address":"recipient-main-or-subaddress","signature":"InTxV1…/tx_key proof"}}
```

### Monero-dev gotchas
- ⚠️ **Balance scanning requires downloading and trial-decrypting every output with the view key** — "balance lookup by address" via a public explorer does not exist. Index your own incoming transfers; restore height matters (a wallet restored from seed only sees outputs after its creation unless you scan from genesis).
- **10-block output lock** and reorg handling: treat <10-conf receipts as provisional in application logic.
- **Payment proofs are per-tx and selective** — build your support flow around `get_tx_proof`/`check_tx_proof`, since no block explorer can adjudicate "did you pay me?"
- **Multisig is interactive and sessionful** (M-of-N rounds), unlike Bitcoin's script template; plan the UX accordingly.
- **Don't use `unlock_time`** for new logic — deprecated ahead of FCMP++ (May 2026 announcement).
- **Forward-compatibility**: after FCMP++, ring-size assumptions, decoy selection and some wallet-RPC internals change; CARROT addresses remain backward compatible, but keep RPC version pinning and test against the alpha stressnet if you maintain infrastructure.
- Mining: **RandomX is deliberately CPU-only economics** — a RandomX miner (XMRig) doubles as a stress tester; don't bother trying to GPU/ASIC it.

---
