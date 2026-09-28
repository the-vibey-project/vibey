---
id: skill-2-writing-kernel-code-edeffd33b4
purpose: 2 writing kernel code
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-architecture-and-code/SKILL.md
requires: ["skill-1-kernel-architecture-23112f1bb4"]
links: ["skill-3-concurrency-in-the-kernel-842823dc4c"]
---

## §2. Writing Kernel Code

### 2.1 The kernel is not C as you know it

**[DURABLE] What you do not have:**
- **No libc.** No `printf`, `malloc`, `strcpy` in the userspace sense. The kernel has its
  own: `printk`/`pr_*`, `kmalloc`, `strscpy`, `kstrtoint`.
- **No floating point** (without `kernel_fpu_begin/end`, and you almost certainly
  shouldn't). The FPU state isn't saved across kernel entry.
- **A tiny, fixed stack** — typically **16 KB** on x86-64 (`THREAD_SIZE`), shared with
  interrupt frames on some configs. **No large stack arrays, no deep recursion, no
  variable-length arrays.** `CONFIG_FRAME_WARN` yells at ~1–2 KB per frame.
- **No exceptions and no unwinding.** Errors are `int` return codes: `0` on success,
  **negative errno** (`-ENOMEM`, `-EINVAL`, `-EIO`) on failure. `ERR_PTR()`/`IS_ERR()`/
  `PTR_ERR()` encode errors in pointer returns.
- **No memory protection.** A bad pointer corrupts unrelated subsystems. The symptom
  appears far from the cause. This is why KASAN exists (§12.3 → `linux-kernel-debugging-process-and-hardening`).
- **Preemption and concurrency everywhere.** Your function can be entered on every CPU
  simultaneously, and preempted mid-way. Assume it.

**Kernel C dialect:** GNU C (not ISO), currently gnu11-ish with strong movement toward
newer standards; `__attribute__`s, statement expressions, `typeof`, and inline asm are
normal. `-fno-strict-aliasing` and `-fno-delete-null-pointer-checks` are on, which is why
some UB that would bite userspace doesn't bite here — do not rely on that.

**The idioms you will read constantly:**
```c
/* Error handling with goto — the canonical single-exit cleanup ladder.
   MISRA-style "no goto" rules do not apply here; this IS the kernel style. */
static int foo_probe(struct platform_device *pdev)
{
        struct foo *f;
        int ret;

        f = devm_kzalloc(&pdev->dev, sizeof(*f), GFP_KERNEL);
        if (!f)
                return -ENOMEM;                    /* devm_ = auto-freed. Prefer it. */

        f->clk = devm_clk_get(&pdev->dev, NULL);
        if (IS_ERR(f->clk))
                return dev_err_probe(&pdev->dev, PTR_ERR(f->clk), "no clock\n");
                /* dev_err_probe handles -EPROBE_DEFER quietly. Use it. */

        ret = clk_prepare_enable(f->clk);
        if (ret)
                return ret;

        ret = foo_hw_init(f);
        if (ret)
                goto err_clk;                      /* unwind in reverse order */

        platform_set_drvdata(pdev, f);
        return 0;

err_clk:
        clk_disable_unprepare(f->clk);
        return ret;
}

/* container_of — how the kernel does "inheritance" without inheritance.
   Given a pointer to an embedded member, recover the enclosing struct. */
struct my_dev { int id; struct device dev; };
static struct my_dev *to_my_dev(struct device *d)
{ return container_of(d, struct my_dev, dev); }

/* Intrusive linked lists — the node lives IN your struct, no allocation. */
struct my_item { struct list_head list; int value; };
LIST_HEAD(items);
list_add_tail(&item->list, &items);
list_for_each_entry(item, &items, list) { ... }
list_for_each_entry_safe(item, tmp, &items, list) { list_del(&item->list); kfree(item); }
```

### 2.2 The rules that get patches rejected

**[DURABLE, and enforced socially as much as technically]:**
1. **Follow `Documentation/process/coding-style.rst`.** Tabs of 8. 80 columns is a
   soft limit (100 tolerated). Braces K&R-ish. `checkpatch.pl --strict` before sending.
2. **One logical change per patch.** A series that mixes a cleanup with a fix will be
   asked to be split.
3. **`Signed-off-by:` is a legal statement** (the Developer Certificate of Origin), not
   a formality.
4. **Never break userspace.** §4 → `linux-syscalls-ebpf-boot-and-init`. This is the one rule Linus enforces personally and
   loudly.
5. **No new `/proc` files** for arbitrary data; use sysfs (one value per file) or debugfs
   (unstable, debug-only) as appropriate. sysfs has an ABI stability expectation.
6. **Document your locking.** A comment saying which lock protects which field is
   expected. `lockdep` (§12.2 → `linux-kernel-debugging-process-and-hardening`) will verify it.
7. **`__user` annotations and `copy_from_user`/`copy_to_user`** for every userspace
   pointer. Sparse (`make C=1`) checks this. Dereferencing a `__user` pointer directly
   is both a bug and a security hole.
8. **Check every return value.** `__must_check` exists.

### 2.3 A minimal module, and why each line is there

```c
// SPDX-License-Identifier: GPL-2.0        /* Required. Machine-checkable. */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>

static int __init hello_init(void)         /* __init: freed after boot */
{
        pr_info("hello: loaded\n");        /* pr_* honours the module prefix */
        return 0;                          /* nonzero = module load fails */
}

static void __exit hello_exit(void)        /* __exit: dropped if built-in */
{
        pr_info("hello: unloaded\n");
}

module_init(hello_init);
module_exit(hello_exit);

MODULE_LICENSE("GPL");    /* Non-GPL taints the kernel and loses EXPORT_SYMBOL_GPL */
MODULE_AUTHOR("...");
MODULE_DESCRIPTION("...");
```
Build out-of-tree against the running kernel's headers:
```makefile
obj-m += hello.o
all:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
clean:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
```

> **⚠️ GOTCHA — there is no stable in-kernel ABI, deliberately.** A module built for
> 6.18.40 will not load on 6.18.41 if the relevant symbols' CRCs changed. This is policy,
> not oversight: the kernel reserves the right to change internal interfaces, and the
> cost of that policy is borne by out-of-tree modules. The consequences: DKMS rebuilds on
> every kernel update, `MODULE_VERSION`/`modversions` mismatches, and the reason vendors
> push hard to get drivers upstream. **Getting your driver merged is the only durable
> maintenance strategy.**

### 2.4 Driver model and devicetree

Modern drivers plug into the **driver model**: a `struct device` bound to a `struct
device_driver` by a **bus** (platform, PCI, USB, I2C, SPI). The bus matches by
compatible string (devicetree), ACPI ID, or vendor/device ID, then calls `probe()`.

```c
static const struct of_device_id foo_of_match[] = {
        { .compatible = "vendor,foo-v2" },
        { }
};
MODULE_DEVICE_TABLE(of, foo_of_match);   /* enables autoloading via modalias */

static struct platform_driver foo_driver = {
        .probe  = foo_probe,
        .remove = foo_remove,
        .driver = {
                .name           = "foo",
                .of_match_table = foo_of_match,
                .pm             = &foo_pm_ops,
        },
};
module_platform_driver(foo_driver);
```
**Devicetree** describes non-discoverable hardware (most ARM/RISC-V embedded); ACPI does
the same job on x86 servers. `-EPROBE_DEFER` is the mechanism for "my dependency isn't
ready yet, retry later" — return it, don't spin.

**Use the `devm_` (device-managed) API for everything you can.** Resources are released
automatically on probe failure and on detach, which eliminates the single largest source
of driver leak bugs.

### 2.5 Userspace-facing interfaces

| Interface | Stability | Use for |
|---|---|---|
| **syscall** | Forever (§4 → `linux-syscalls-ebpf-boot-and-init`) | Fundamental new capability. Very high bar |
| **ioctl** | Per-driver, versioned | Device-specific commands. **Design the struct with padding and a size/version field from day one** |
| **sysfs** (`/sys`) | ABI-stable, documented in `Documentation/ABI/` | One value per file, text |
| **debugfs** (`/sys/kernel/debug`) | **None** | Debugging only. Never rely on it in production tooling |
| **procfs** (`/proc`) | Legacy stable | Process info. Don't add new non-process files |
| **netlink** | Stable | Structured, async, multicast config (networking, but not only) |
| **char device** | Per-driver | Streaming data |
| **BPF** | Stable-ish | Programmable hooks (§5 → `linux-syscalls-ebpf-boot-and-init`) |

### 2.6 Rust in the kernel

**[VERSIONED — this changed materially in 2026.]** Rust support landed experimentally in
6.1; **Linux 7.0 (12 April 2026) removed the experimental designation, making Rust a
first-class kernel language.** The "Rust experiment" was formally concluded at the 2025
Kernel Maintainers Summit in Tokyo with an explicit coexistence policy: **Rust for new
code, C for existing subsystems, no forced migrations.** Kernel builds now require only
stable Rust releases (minimum anchored to the Debian stable toolchain, ~1.93 at the time
of the 7.0 release). Reported at Open Source Summit India in July 2026: some subsystems —
**graphics notably** — intend to accept only Rust for *new* drivers going forward.

**What exists:** the `kernel` crate with abstractions over PCI device enumeration,
interrupt handling, DMA mapping, platform device registration, `dev_printk` on all device
types, and generic I/O back-ends. Real drivers: Android's **ashmem** shipped in Rust on
kernel 6.12 (putting Rust kernel code on hundreds of millions of devices), NVIDIA's
**Nova** DRM driver for Turing-era hardware, Rust NVMe work, and PuzzleFS.

**What's actually hard about it** [the honest list]:
- **No `std`.** You get `core`, `alloc`, and the kernel's own `kernel` crate.
- **Fallible allocation everywhere.** `Box::new` can't panic in the kernel, so you use
  the kernel's fallible variants and handle `-ENOMEM` explicitly.
- **Toolchain management overhead** — a specific minimum Rust version, and some carefully
  used unstable features.
- **Two skill sets.** You need kernel programming *and* Rust; the intersection is small.
- **Documentation lags** the C side substantially.
- Abstractions for a subsystem may simply not exist yet, in which case you write them —
  which is a much bigger job than writing the driver.

**[CONTESTED] Rust in the kernel.** The disagreement is real, public, and has cost
maintainers. *For:* memory-safety bugs are the dominant kernel CVE class and Rust
eliminates them by construction; Google reports zero memory-safety bugs in production
from its Rust Android driver code where equivalent C drivers had CVEs. *Against (the
strongest version):* a second language doubles the maintenance surface for subsystem
maintainers who must now review both; refactoring a C interface now requires fixing Rust
bindings maintained by someone else; and the kernel's rule that C changes shouldn't be
blocked by Rust breakage is easier to state than to live with. One maintainer publicly
resigned over this. **Both the technical case and the social cost are real; the policy
question is settled, the friction is not.**

---
