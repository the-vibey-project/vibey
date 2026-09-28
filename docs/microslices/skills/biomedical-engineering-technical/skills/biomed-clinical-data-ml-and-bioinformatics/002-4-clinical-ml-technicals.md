---
id: skill-4-clinical-ml-technicals-ae0529a008
purpose: 4 clinical ml technicals
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-clinical-data-ml-and-bioinformatics/SKILL.md
requires: ["skill-3-clinical-data-structures-b716fe480d"]
links: ["skill-5-bioinformatics-5e53cd6565"]
---

## §4. Clinical ML Technicals

### 4.1 ⚠️ The prevalence problem

**Sensitivity and specificity are properties of a test. PPV is a property of a test in a
population.**
```
PPV = (Sens × Prev) / (Sens × Prev + (1−Spec) × (1−Prev))
```
**Worked — a genuinely good test in a screening setting:**
```
Sens 95%, Spec 95%, Prevalence 1%
  PPV = (0.95 × 0.01) / (0.95×0.01 + 0.05×0.99)
      = 0.0095 / (0.0095 + 0.0495) = 16.1%     ⚠️
```
**⚠️ 84% of positives are false, with a 95/95 test.** Move prevalence to 20% (a referral
population) and PPV becomes 82.6%. **Same test. Nothing changed but the population.**

**⚠️ Consequences**: **accuracy is meaningless at low prevalence** (99% by always saying
no); **AUROC is prevalence-independent and therefore hides this**; **use AUPRC for
imbalanced problems**, whose baseline is the prevalence itself.

### 4.2 ⚠️ Calibration, not just discrimination

**Discrimination** (AUROC) asks whether ranking is correct. **Calibration** asks whether
"70%" means 70%. **For decision support, calibration is what the clinician acts on.**
- **Calibration curve** (predicted vs observed in bins), **calibration slope and
  intercept**, **Brier score** `(1/N)Σ(p_i − y_i)²`.
- ⚠️ **Modern neural networks are systematically overconfident.** **Temperature scaling**,
  Platt scaling, or isotonic regression on a held-out set.
- **⚠️ Calibration does not transfer across sites**, because prevalence differs (§4.1).
  **Recalibration at deployment site is usually necessary.**

**Decision curve analysis** — net benefit across threshold probabilities. ⚠️ **The metric
that actually answers "is this useful," and it's underused.**

### 4.3 ⚠️ Where clinical models learn the wrong thing

- **Shortcut features.** Documented: models keying on **chest-drain markers to predict
  pneumothorax**, **rulers in dermatology images to predict melanoma**, and **scanner or
  hospital identity** rather than pathology.
- **⚠️ Label leakage from the future.** *"Was a troponin ordered"* predicts myocardial
  infarction — because the clinician already suspected it. **Any feature downstream of
  clinical suspicion leaks.**
- **⚠️ Missingness is informative.** A missing lab is a decision not to order it.
  **Imputing it as MAR destroys signal and introduces bias simultaneously.** Model
  missingness explicitly (indicator variables) or use methods that handle it natively.
- **Treatment in the features** — confounding by indication.
- **Proxy targets encode system bias.** ⚠️ **A widely-deployed care-management algorithm
  used healthcare *spending* as a proxy for health *need*, thereby encoding unequal access
  as lower need.** The general lesson: **the target variable is a modelling choice with
  consequences.**
- **⚠️ Distribution shift** — scanner, protocol, coding practice, population, season.

### 4.4 The validation ladder
```
Internal (CV, holdout)     ⚠️ necessary, never sufficient
Temporal (train past, test future)   catches drift and leakage
External (different sites/scanners)  ⚠️ where performance typically drops
Prospective (real workflow, real time)
Outcome trial              ⚠️ does it change outcomes, not just AUROC?
```
**⚠️ Group-aware splitting is mandatory**: split by *patient*, not by image or record.
**A patient with 40 slices in both train and test leaks.**

**Reporting**: TRIPOD+AI, CONSORT-AI, SPIRIT-AI, STARD-AI.

---
