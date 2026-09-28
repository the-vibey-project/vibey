---
id: skill-2-medical-imaging-31b02283f5
purpose: 2 medical imaging
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-signals-and-medical-imaging/SKILL.md
requires: ["skill-1-physiological-signal-processing-0db3a4c8cd"]
links: []
---

## §2. Medical Imaging

### 2.1 Modality physics

| Modality | Physics | Resolution | ⚠️ Constraint |
|---|---|---|---|
| **CT** | X-ray attenuation, filtered backprojection or iterative recon | 0.5–1 mm | ⚠️ **Ionizing dose; ALARA** |
| **MRI** | Nuclear magnetic resonance, T1/T2 relaxation | 1 mm | Long acquisition; ⚠️ **field is a physical hazard** |
| **Ultrasound** | Acoustic reflection, ~1–15 MHz | 0.3–2 mm | ⚠️ **Operator-dependent; acoustic shadowing** |
| **PET** | Positron annihilation, 511 keV coincidence | 4–5 mm | ⚠️ **Functional, not anatomical; needs CT for attenuation correction** |
| **SPECT** | Single-photon gamma | 8–10 mm | Lower resolution than PET |
| **OCT** | Low-coherence interferometry | ⚠️ **1–15 µm** | Penetration only ~1–2 mm |
| **Digital pathology** | Whole-slide scanning | 0.25 µm/px | ⚠️ **Gigapixel — pyramidal tiling mandatory** |

**CT numbers** are in **Hounsfield units**: `HU = 1000 × (µ − µ_water)/µ_water`.
⚠️ **Water = 0, air = −1000, dense bone ≈ +1000 to +3000.** Fixed and physical, which is
why CT is quantitative and MRI intensity is not.

**MRI contrast** comes from **TR and TE**: T1-weighted (short TR/TE — fat bright, fluid
dark), T2-weighted (long TR/TE — ⚠️ **fluid bright, which is why pathology shows**), FLAIR
(T2 with CSF suppressed), DWI/ADC (diffusion — ⚠️ **restricted diffusion in acute stroke
within minutes**), and functional/BOLD.

> **⚠️ GOTCHA — MRI intensity has no absolute meaning.** Unlike CT's Hounsfield units, MRI
> signal depends on scanner, coil, sequence, and shim. **Intensity values are not
> comparable across scans without normalization** (histogram matching, z-scoring within a
> tissue mask, or N4 bias-field correction first). **Training an ML model on raw MRI
> intensities across sites is a well-known way to learn the scanner instead of the
> disease.**

### 2.2 ⚠️ DICOM internals that produce silent errors

**Hierarchy**: Patient → Study → Series → Instance, identified by **UIDs**.
⚠️ **UIDs must be globally unique; generating them incorrectly corrupts archives
irreversibly.** Use a registered root plus a unique suffix.

**The specific traps:**
- **⚠️ Rescale.** `HU = pixel_value × RescaleSlope + RescaleIntercept`. **Stored pixels are
  not HU.** Skipping this is the most common CT bug and produces confidently wrong
  measurements.
- **⚠️ Photometric interpretation.** `MONOCHROME1` = minimum is white; `MONOCHROME2` =
  minimum is black. **Getting it wrong inverts the image** and a radiologist will notice
  but a model won't.
- **⚠️ Orientation.** `ImageOrientationPatient` (two direction cosine vectors) and
  `ImagePositionPatient` define anatomical space. **Left/right confusion means the wrong
  side, and wrong-side surgery is a real event class.** Always derive laterality from the
  geometry, never from the display convention.
- **Slice spacing ≠ slice thickness.** `SliceThickness` is the acquisition; spacing must be
  computed from consecutive `ImagePositionPatient` values. ⚠️ **They disagree with gaps or
  overlap**, and using the wrong one distorts volumes.
- **Window/level** (`WindowCenter`, `WindowWidth`) is display only — ⚠️ **never bake it
  into stored data you intend to analyse.**
- **Multi-frame and enhanced DICOM** put per-frame attributes in functional group
  sequences, not at the top level.

**⚠️ De-identification is harder than stripping tags.** PHI hides in **private tags**,
**burned-in pixel annotation**, `StudyDescription` free text, and ⚠️ **the face itself —
facial reconstruction from head CT/MRI is demonstrated, so "defacing" is a genuine
requirement for shared neuroimaging.**

### 2.3 Reconstruction
**Filtered backprojection** — the Radon transform inverted, with a **ramp filter** in
frequency (⚠️ **the ramp amplifies high-frequency noise; apodize with Shepp-Logan or
Hann**). **Iterative reconstruction** (ART, SART, MBIR) is slower and permits substantially
lower dose. **⚠️ Undersampling produces streak artifacts**; compressed sensing exploits
sparsity to recover from fewer projections, which is what makes fast MRI possible.

### 2.4 Registration and segmentation

**Registration** = find the transform aligning two images:
```
T* = argmin_T  S(I_fixed, T(I_moving)) + λR(T)
```
**Transform models**: rigid (6 DOF) → affine (12) → **deformable** (B-spline free-form,
diffeomorphic/LDDMM, Demons).
**Similarity metrics**: SSD (⚠️ **same modality only**), normalized cross-correlation, and
⚠️ **mutual information — the standard for multimodal (CT↔MRI), because it makes no
assumption about intensity relationship, only statistical dependence.**
```
MI(A,B) = H(A) + H(B) − H(A,B)
```
**⚠️ Practical requirements**: multi-resolution pyramids (avoids local minima), and
**regularization to keep the deformation invertible** — an unregularized deformable
registration will happily fold tissue through itself.

**Segmentation**: thresholding → region growing → **level sets / active contours** →
**atlas-based** → **deep learning**.
⚠️ **nnU-Net remains the strong baseline that beats most novel architectures on medical
segmentation** — its contribution is automated configuration of preprocessing, patch size,
and augmentation, which matters more than architecture.
**Metrics**: **Dice** `2|A∩B|/(|A|+|B|)`, **IoU**, **Hausdorff distance** (⚠️ **worst-case
boundary error — the one that matters clinically, because Dice is insensitive to a small
but catastrophic boundary error**), and **surface Dice**.

**⚠️ Class imbalance is severe** — a lesion may be 0.1% of voxels. **Dice loss or
Tversky loss rather than cross-entropy**, and patch sampling biased toward foreground.

**Toolkits**: ITK/SimpleITK, ANTs (registration), 3D Slicer, MONAI, nnU-Net, FSL and
FreeSurfer (neuro), pydicom, dcm4che, OHIF, OpenSlide (pathology).
