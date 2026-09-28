---
id: skill-4-hash-tables-300dc0e57b
purpose: 4 hash tables
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-data-structures/SKILL.md
requires: ["skill-3-arrays-and-sequences-fb56bba55a"]
links: ["skill-5-trees-and-ordered-structures-804ed6ec93"]
---

## §4. Hash Tables

**[DURABLE] The most important data structure in practice**, and the one whose
implementation details most affect real performance.

### 4.1 Collision resolution

**Separate chaining** — buckets hold lists. Simple, degrades gracefully, ⚠️ **one pointer
chase per probe.**
**Open addressing** — everything in one array. **Far better cache behaviour**, and the
modern default. Variants: **linear probing** (best locality; suffers clustering),
**quadratic probing**, **double hashing**, **Robin Hood** (steal from the rich — bounds
variance in probe length), **hopscotch**, **cuckoo** (worst-case O(1) lookup, expensive
inserts).

**[VERSIONED] Swiss tables** (Google's `absl::flat_hash_map`, and the basis of Rust's
`HashMap` via `hashbrown`) are the current practical state of the art: **open addressing
plus a separate array of one-byte control values, scanned with SIMD** so one instruction
checks 16 slots. **If your language's hash map is modern, this is probably what it does.**

### 4.2 The things that actually bite

> **⚠️ GOTCHA — the hash table failure modes, roughly in order of how often they hurt:**
> - **Load factor.** Performance degrades sharply as the table fills; most implementations
>   resize around 0.7–0.9. **Resizing is an O(n) rehash — a latency spike.** Pre-size when
>   you can.
> - **Bad hash functions.** A hash that doesn't distribute causes clustering that looks
>   like an algorithmic problem. **Never use `hash(x) % n` with a weak hash and a power-of-2
>   n** — you're using only the low bits.
> - **⚠️ Hash-flooding DoS.** If keys come from untrusted input, an attacker who can predict
>   your hash can force every key into one bucket, turning O(1) into O(n). **This is why
>   SipHash and randomized seeds are the default in Python, Rust, and others** — and why
>   swapping in a "faster" non-cryptographic hash on user-controlled keys is a security
>   decision, not a performance one.
> - **Iteration order.** Unordered by definition, and **deliberately randomized in some
>   languages.** Depending on it is a bug that surfaces after an upgrade.
> - **Mutating a key after insertion.** Corrupts the table silently.
> - **Equality and hashing must agree.** `a == b` ⟹ `hash(a) == hash(b)`. Violating this
>   produces lookups that fail for keys that are present.

**Ordered variants**: `LinkedHashMap`, Python's dict (insertion-ordered since 3.7),
Rust's `IndexMap` — an array of entries plus a hash index. **Cheap, and worth defaulting to
when determinism helps debugging.**

### 4.3 The 2025 theory result, and its honest weight

**[VERSIONED]** In **January 2025**, Farach-Colton, Krapivin, and Kuszmaul published
*"Optimal Bounds for Open Addressing Without Reordering"*, which **disproved the central
conjecture from Andrew Yao's 1985 "Uniform Hashing is Optimal."** The result got wide
attention partly because Krapivin was an undergraduate who found it while tinkering,
unaware of the conjecture.

Two constructions: **funnel hashing** (greedy) achieves **O(log² δ⁻¹)** worst-case expected
probe complexity — where δ is the empty fraction — **disproving Yao's claim that Ω(δ⁻¹) was
optimal for greedy schemes**; and **elastic hashing** (non-greedy) achieves **O(1) amortized
expected** and **O(log δ⁻¹) worst-case expected** probes **without reordering**.
**All results come with matching lower bounds** — they didn't just refute the conjecture,
they settled the question.

> **⚠️ GOTCHA — read this correctly, because the popular coverage oversold it.** CACM's own
> reporting notes the caveats: **it disproved Yao's conjectures but not Ullman's**; **some
> non-open-addressing designs (e.g. Iceberg tables) are faster** than Krapivin's structure;
> and **the construction handles insertions only, not deletions** — where the earlier Tiny
> Pointers work covered both. The authors themselves "take a lower-key view."
>
> **The engineering translation: this is a genuine and beautiful theoretical result that
> settles a 40-year question. It is not a reason to replace your hash map.** Its practical
> relevance is to very-high-load-factor regimes; your Swiss table at 0.75 load is
> unaffected.

---
