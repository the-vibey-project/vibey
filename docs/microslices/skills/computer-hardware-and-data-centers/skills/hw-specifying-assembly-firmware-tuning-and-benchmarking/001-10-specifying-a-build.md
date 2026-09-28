---
id: skill-10-specifying-a-build-f9e914e585
purpose: 10 specifying a build
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-specifying-assembly-firmware-tuning-and-benchmarking/SKILL.md
requires: []
links: ["skill-11-assembly-3a83a71026"]
---

## §10. Specifying a Build

> **⚠️ Start from the WORKLOAD, not from a parts list. Almost every wasted pound in a
> custom build comes from balancing the machine wrong.**
```
⚠️ MATCH THE COMPONENT TO THE BOTTLENECK (§1)
   ⚠️ Gaming  ⚠️ GPU-dominant; CPU matters at high frame rates and
      low resolution; ⚠️ VRAM capacity increasingly binding
   ⚠️ Content creation  cores, RAM CAPACITY, fast storage
   ⚠️ Software development  ⚠️ single-thread speed for many tools,
      cores for compilation, RAM for containers and VMs
   ⚠️ ML  ⚠️ VRAM CAPACITY FIRST — a model that doesn't fit doesn't
      run — then bandwidth, then compute
   ⚠️ Workstation/CAD  certified drivers, ECC where correctness matters
   ⚠️ Home server/NAS  ⚠️ reliability, ECC, drive bays, low idle power
⚠️ THE BALANCE PRINCIPLE  ⚠️ a top GPU with an inadequate CPU or
   insufficient RAM wastes most of what you paid for
⚠️ WHERE MONEY IS USUALLY WASTED  ⚠️ oversized PSU (§7) · RGB ·
   marginal RAM speed · exotic cooling for a part that isn't
   thermally limited · high-end board features you'll never use
⚠️ WHERE IT IS USUALLY WELL SPENT  ⚠️ a good PSU · adequate RAM
   capacity · a decent monitor (⚠️ which outlasts the whole build)
   · quiet cooling · a case you can work in
```

---
