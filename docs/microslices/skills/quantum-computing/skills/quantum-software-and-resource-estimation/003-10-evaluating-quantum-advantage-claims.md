---
id: skill-10-evaluating-quantum-advantage-claims-4efbd999e4
purpose: 10 evaluating quantum advantage claims
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-software-and-resource-estimation/SKILL.md
requires: ["skill-9-resource-estimation-70f570ca43"]
links: []
---

## §10. Evaluating Quantum Advantage Claims

### 10.1 The vocabulary

- **Quantum supremacy / advantage** — outperforming the best classical approach on *some*
  well-defined task, useful or not.
- **Quantum utility** — practical usefulness; the emphasis shifts from beating classical
  to delivering value.
- **Verifiable advantage** — advantage where the answer's correctness can actually be
  checked. **[DURABLE]** This is the crux (§10.2).

### 10.2 The verification problem

**[DURABLE] This is the field's deepest methodological difficulty**: if no classical
computer can perform the calculation, how do you know the quantum answer is right? The
approaches:
- **Simulate smaller instances** and extrapolate — indirect, and the basis of most early
  claims.
- **Complexity-theoretic hardness arguments** plus a device-dependent fidelity certificate.
- **Peaked circuits** — circuits whose output concentrates on a single known bitstring, so
  correctness is checkable by comparison.
- **Structural verification** — problems where checking is easier than solving.

There is a serious argument, made in the applications literature, that **verifiability is a
necessary (though insufficient) condition for a quantum algorithm to be useful** — which
would rule out advantage claims based purely on sampling from a scrambled quantum state.
The reasoning: if you can efficiently spoof the output with no detectable performance
change, spoofing is easier than building the computer.

### 10.3 Dequantization — the pattern to watch for

**[DURABLE] Multiple proposed quantum advantages have been eliminated by improved classical
algorithms**, and this has happened often enough to be the default hypothesis rather than a
surprise. The history: **Google's 2019 Sycamore supremacy claim** (200 seconds vs. an
estimated 10,000 classical years) was followed by **years of improved classical simulation
partially closing the gap**; boson-sampling claims from USTC and Xanadu met the same
tug-of-war. **Ewin Tang's dequantization results** removed the claimed exponential speedup
from a family of quantum recommendation and machine-learning algorithms outright.

**A 2026 example of the pattern in real time**: a heuristic quantum advantage claim using
**peaked circuits on Quantinuum's 56-qubit H2** (October 2025, with estimated classical
runtimes of years for the largest instances) was followed in **April 2026 by an IBM Quantum
paper demonstrating efficient classical simulation of those same circuits**. The claim and
the refutation came from within the field, six months apart.

**⚠️ The checklist for any advantage claim:**
1. **Is the task useful, or contrived for the demonstration?**
2. **Is the result verifiable, and how?**
3. **What is it compared against — the best classical algorithm, or a convenient one?**
4. **Have classical researchers had time to attempt a match?** (Give it 6–18 months.)
5. **Peer-reviewed, or a press release timed to an earnings call?**
6. **Does the claim survive if you use a GPU cluster and a good tensor-network method?**

### 10.4 The 2026 state of the debate

**[VERSIONED and [CONTESTED].]** On **30 July 2026, IBM coordinated three announcements**
around arXiv preprints, presenting them collectively as evidence that quantum computing had
entered "the quantum advantage era," with IBM Research director Jay Gambetta using that
phrase. The three results addressed the same problem — how to trust output no classical
machine can check — from different directions, and **critically, they do not carry equal
evidentiary weight**: the IBM/University of Chicago paper makes an explicit advantage claim
backed by complexity-theoretic hardness arguments and a device-dependent fidelity
certificate, while the Qedma and Algorithmiq papers make **more empirical claims about
regimes where tested classical methods become unreliable**. One result ran an encoded
circuit using **70 logical qubits through thousands of logical operations with a logical
error rate roughly 10× lower than the underlying physical rate**, finishing in about 15
minutes.

**The fair reading**: the verification advances are real and substantive. Whether three
results at three different evidentiary levels justify declaring an era is a separate
question, and reasonable people in the field answer it differently. **The broader 2026
consensus is roughly: advantage on contrived tasks has likely been achieved; the live
argument is over whether usefulness should be a requirement for the term at all.**
