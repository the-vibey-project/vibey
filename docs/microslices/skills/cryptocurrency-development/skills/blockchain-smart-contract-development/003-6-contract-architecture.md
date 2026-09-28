---
id: skill-6-contract-architecture-6e0a379add
purpose: 6 contract architecture
source: src/vibey_tools/skills/plugins/cryptocurrency-development/skills/blockchain-smart-contract-development/SKILL.md
requires: ["skill-5-solidity-and-the-contract-languages-3b618ce5a9"]
links: ["skill-7-standards-c0759fdcf2"]
---

## §6. Contract Architecture

### 6.1 Upgradeability

**[CONTESTED, and it's the most consequential architectural decision you'll make.]**
*For upgradeability*: bugs are otherwise unfixable, requirements change, and migrations are
brutal for users. *Against*: it reintroduces trust, adds a large attack surface, and
**upgrade keys are themselves a top-tier target.**

**The patterns:**
```
Transparent Proxy    proxy DELEGATECALLs to impl; admin calls handled at proxy
UUPS (EIP-1822)      upgrade logic lives in the IMPLEMENTATION — cheaper,
                     ⚠️ but you can brick it by deploying an impl without upgrade logic
Beacon               many proxies read one beacon → upgrade all at once
Diamond (EIP-2535)   multi-facet routing; powerful, complex, contested
Immutable            no upgrade path. The safest and least forgiving option
```
> **⚠️ GOTCHA — the proxy failure modes, all of which have caused real losses:**
> 1. **Storage collisions.** The implementation's storage layout must be append-only across
>    upgrades. Reordering or inserting a variable corrupts state. Use **namespaced storage
>    (ERC-7201)** or storage gaps.
> 2. **Uninitialized implementation contracts.** The logic contract must have its
>    initializer disabled (`_disableInitializers()`), or someone else initializes it and,
>    with UUPS, can `selfdestruct`/brick it.
> 3. **Constructors don't run** in proxy context. Use `initialize()` with an
>    initializer guard.
> 4. **`immutable` and constructor-set state** live in the implementation's code, not the
>    proxy's storage — a frequent source of subtle wrongness.
> 5. **The upgrade key is the whole security model.** A timelock plus a multisig is the
>    minimum for anything holding real value.

### 6.2 Access control

**[DURABLE] This is the highest-value section in the document, because access control is
the single largest category of on-chain loss (§10.1 → `blockchain-security-testing-and-ops`).**

Patterns: `Ownable` (simple, single point of failure), `Ownable2Step` (**use this instead** —
transfer requires acceptance, preventing a typo'd address from permanently orphaning the
contract), `AccessControl` (role-based), timelocks (mandatory delay on privileged actions,
giving users time to exit), and multisig (Safe is the standard) or full DAO governance.

**The checklist for every privileged function**: is it actually restricted? Is the modifier
present on *every* path including the initializer and the upgrade function? Can it be
called before initialization? Is the role transferable, and safely? Is there a timelock on
anything that can drain or brick the system?

### 6.3 Design principles

**[DURABLE]** **Checks-Effects-Interactions** — validate, then update your state, *then*
make external calls. This ordering alone prevents most reentrancy. **Pull over push** for
payments — let users withdraw rather than pushing funds, so one reverting recipient can't
block everyone. **Fail loudly** — revert with custom errors rather than returning false.
**Minimize privileged surface.** **Emit events for everything** an off-chain system needs
(§13.4 → `blockchain-security-testing-and-ops`). **Bound every loop.** **Handle the ERC-20 misbehaviours** in §7.1.

---
