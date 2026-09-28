---
id: skill-10-debugging-training-ecd081429a
purpose: 10 debugging training
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-evaluation-serving-mlops-and-safety/SKILL.md
requires: ["skill-9-evaluation-bfbd2388f7"]
links: ["skill-11-inference-and-serving-9ddb9438ae"]
---

## §10. Debugging Training

**[DURABLE] A systematic ladder, in order. Skipping steps is what makes debugging take
weeks.**

1. **Overfit a single batch.** Train on 2–10 examples until loss ≈ 0. **If you can't, you
   have a bug, not a learning-rate problem.** This is the single most valuable diagnostic in
   deep learning and takes two minutes.
2. **Check shapes and the data.** Print them. Visualize an actual batch after
   augmentation. **⚠️ Silent broadcasting bugs are endemic** — a `(B,1)` vs. `(B,)` mismatch
   produces a `(B,B)` tensor and a loss that trains to something meaningless.
3. **Verify the loss at initialization.** Cross-entropy on k balanced classes should start
   near `ln(k)`. If it doesn't, your labels, logits, or reduction are wrong.
4. **Check the label pipeline end-to-end.** Off-by-one, shuffled labels, wrong mapping.
5. **Watch gradient norms.** Zero → disconnected graph or dead activations. Exploding →
   clip, lower the LR, check normalization.
6. **Sweep the learning rate** over orders of magnitude before touching anything else.
7. **Compare train vs. validation curves**: both high = underfitting (bigger model, train
   longer, better features); train low + val high = overfitting (more data, more
   regularization, augmentation); **val better than train** = a bug, or dropout/BN
   train-mode artifacts.
8. **Turn off tricks** — augmentation, scheduler, mixed precision, `torch.compile` — and
   reintroduce them one at a time.

| Symptom | Likely cause |
|---|---|
| Loss is NaN | LR too high; log(0)/div-by-zero; fp16 overflow (**use bf16**); bad input data |
| Loss flat from step 0 | LR too low; frozen params; disconnected graph; `optimizer.zero_grad()` misplaced |
| Loss decreases then explodes | LR too high; missing gradient clipping; a bad batch |
| Great train, terrible val | Overfitting, or **leakage in reverse** (val is harder/different) |
| Great val, terrible production | **Distribution shift, or leakage** (§2.1 → `ml-framing-data-and-classical`). Check the leakage list first |
| Works in eager, breaks compiled | Graph breaks, dynamic shapes, or a numerics difference |
| Non-deterministic across runs | Expected — see §12.1. Report variance |
| Slower than expected on GPU | Dataloader-bound (check GPU utilization), small batches, unnecessary syncs, `.item()` in the loop |

---
