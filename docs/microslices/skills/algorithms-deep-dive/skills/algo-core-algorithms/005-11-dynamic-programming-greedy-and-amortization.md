---
id: skill-11-dynamic-programming-greedy-and-amortization-931fdeef9d
purpose: 11 dynamic programming greedy and amortization
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-core-algorithms/SKILL.md
requires: ["skill-10-strings-and-text-3706ed1403"]
links: []
---

## §11. Dynamic Programming, Greedy, and Amortization

### 11.1 Dynamic programming

**[DURABLE] The recognition test: optimal substructure plus overlapping subproblems.**
If a problem's optimal solution is built from optimal solutions to subproblems, and those
subproblems repeat, it's DP.

**Top-down (memoization)** is easier to write and follows the recursion naturally;
**bottom-up (tabulation)** avoids recursion overhead and enables **space optimization** —
**⚠️ most DP tables only need the last row or two, turning O(n·m) space into O(m)**, which
is frequently the difference between fitting in cache and not.

**The classic patterns worth recognizing**: knapsack, LCS/edit distance, longest increasing
subsequence (**⚠️ the O(n log n) patience-sorting version, not the O(n²) one**), matrix
chain, interval scheduling, coin change, and DP over subsets/bitmasks (2ⁿ·n — fine for
n ≤ 20).

### 11.2 Greedy

Works when the **greedy choice property** holds — a locally optimal choice is globally
safe. **⚠️ Greedy is right far less often than it looks right, and the failure is silent:**
you get a plausible suboptimal answer, not an error. **Either prove the exchange argument
or test against brute force on small inputs.**

### 11.3 Divide and conquer
Mergesort, quicksort, FFT, Karatsuba, Strassen, closest pair. **The Master Theorem** gives
the complexity for the standard recurrence shapes.

### 11.4 Amortized analysis

**[DURABLE] Amortized O(1) means "cheap on average across a sequence," not "cheap every
time."** Dynamic array growth, hash table resize, union-find with path compression, and
splay trees are all amortized.

**⚠️ This is a latency-tail issue, and it's the most under-appreciated point here.**
Amortized-cheap structures have **occasional expensive operations**, and if you have a p99
latency budget, that occasional O(n) resize is exactly what shows up there. **For strict
latency bounds, prefer structures with good worst-case behaviour, or pre-size to avoid the
resize entirely.**
