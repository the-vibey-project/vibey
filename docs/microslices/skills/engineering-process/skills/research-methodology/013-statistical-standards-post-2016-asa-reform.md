---
id: skill-statistical-standards-post-2016-asa-reform-e27769d1df
purpose: statistical standards post 2016 asa reform
source: src/vibey_tools/skills/plugins/engineering-process/skills/research-methodology/SKILL.md
requires: ["skill-data-collection-and-analysis-00eff202f2"]
links: ["skill-open-science-movement-bc23b83d76"]
---

## Statistical Standards (Post-2016 ASA Reform)

### The ASA Statement (Wasserstein & Lazar, *The American Statistician*, 2016)
Six principles verbatim:
1. P-values can indicate how incompatible the data are with a specified statistical model.
2. P-values do not measure the probability that the studied hypothesis is true, or that the data were produced by random chance alone.
3. Scientific conclusions and business or policy decisions should not be based only on whether a p-value passes a specific threshold.
4. Proper inference requires full reporting and transparency.
5. A p-value does not measure the size of an effect or the importance of a result.
6. By itself, a p-value does not provide a good measure of evidence regarding a model or hypothesis.

### Practical Implications
- **Never** base a conclusion solely on p < 0.05; 0.049 vs. 0.051 should not flip a conclusion.
- "Non-significant" ≠ "no effect" — it may mean an underpowered study.
- **Report the triplet**: point estimate + **confidence interval** + **effect size** in subject-matter units (mean difference, odds ratio, Cohen's d). This conveys magnitude, precision, and direction.
- A 95% confidence interval means: if you repeated the procedure many times, 95% of such intervals would capture the true value — NOT "there is a 95% probability the true value is in this interval."
- Conduct **a priori power analysis** to size the sample and reduce Type I/II error risk.
- Report non-significant results — selective reporting feeds the file-drawer problem.

### Note
The journal *Basic and Applied Social Psychology* banned null-hypothesis significance testing in 2015, but the mainstream position is reform and contextualization, not abandonment.

---
