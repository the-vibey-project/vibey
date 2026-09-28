---
id: skill-4-kernel-programming-b1694a8ab6
purpose: 4 kernel programming
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-3-linux-languages-and-programming-68a24d3393"]
links: ["skill-5-linux-filesystems-devices-security-and-containers-c89caa2e52"]
---

## 4. Kernel programming

Kernel code must obey context and lifetime rules: interrupt versus process context, sleeping versus atomic context, locking order, memory barriers, RCU, reference counting, user-copy validation, DMA, cache coherence, and resource cleanup. There is no ordinary floating point in normal kernel paths.

A minimal educational module:

```c
#include <linux/init.h>
#include <linux/module.h>
static int __init example_init(void) { pr_info("loaded\\n"); return 0; }
static void __exit example_exit(void) { pr_info("unloaded\\n"); }
module_init(example_init);
module_exit(example_exit);
MODULE_LICENSE("GPL");
```

Build against the target kernel’s build tree using kbuild; test in a VM; inspect with `modinfo`, `dmesg`, `journalctl -k`, and `lsmod`. Modules depend on kernel configuration, compiler ABI, symbol versions, architecture, signing, lockdown, and distribution policy.

### Kernel source workflow

```sh
git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
cd linux
make mrproper
make O=../linux-build olddefconfig
make O=../linux-build -j"$(nproc)"
make O=../linux-build modules
```

Use a known distribution configuration when testing hardware. Verify kernel, modules, initramfs, boot entry, signatures, and rollback before rebooting.

Kernel testing includes KUnit, kselftest, LTP, syzkaller, lockdep, KASAN, KMSAN, UBSAN, KFENCE, kmemleak, fault injection, stress, QEMU/KVM, performance regression, and real-hardware testing. A booting kernel is not necessarily a correct kernel.
