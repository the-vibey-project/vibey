---
id: skill-generative-ai-across-modalities-0275672725
purpose: generative ai across modalities
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-agent-stack-mcp-ed82f9638f"]
links: ["skill-mlops-infrastructure-65bf7541d8"]
---

## Generative AI Across Modalities

### Image
- GANs and VAEs gave way to **diffusion** (DDPM→DDIM→Latent Diffusion = Stable Diffusion)
- Now **flow matching / rectified flow** (backbone of SD3, FLUX)
- Classifier-free guidance, ControlNet (pose/depth/edge conditioning), LoRA/DreamBooth personalization are standard
- FLUX (Black Forest Labs): open-weight image generation leader in 2026

### Video
- Standardized on **diffusion transformers (DiT) over spacetime patches** (Sora, Veo, Kling, Seedance, WAN, Hunyuan)
- By early 2026: 8–25s clips at native resolution with synchronized audio and plausible physics
- Weaknesses: long-range temporal coherence and quadratic attention cost

### Audio
- TTS: Tacotron→FastSpeech→VITS→XTTS/F5-TTS/Kokoro; ElevenLabs leads commercial quality
- ASR: Whisper dominates
- Discrete audio tokens: EnCodec/DAC

### Multimodal/VLMs
- Vision encoders trend SigLIP over CLIP, with tile-based high-res
- Open options: LLaVA, Qwen-VL, InternVL, Molmo, Pixtral

---
