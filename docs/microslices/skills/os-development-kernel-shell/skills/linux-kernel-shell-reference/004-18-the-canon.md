---
id: skill-18-the-canon-9b5a2f6566
purpose: 18 the canon
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-shell-reference/SKILL.md
requires: ["skill-17-currency-snapshot-verified-august-2026-2d5bd2992a"]
links: ["skill-19-quick-reference-2dd61e90a8"]
---

## §18. The Canon

### 18.1 Primary sources — prefer these over everything else

- **`Documentation/` in the kernel tree** and **docs.kernel.org**. Specifically:
  `process/submitting-patches.rst`, `process/coding-style.rst`,
  `process/stable-api-nonsense.rst`, `process/volatile-considered-harmful.rst`,
  **`memory-barriers.txt`**, `RCU/`, `scheduler/sched-ext.rst`, `bpf/`, `process/cve.rst`.
- **The source itself.** `git log -p <file>` and `git blame` answer questions no
  documentation will. **Bootlin's Elixir** (`elixir.bootlin.com`) is the best
  cross-referenced browser.
- **LWN.net** — the single most valuable ongoing source on kernel development. The weekly
  Kernel Page, the merge-window summaries, and Jonathan Corbet's architecture articles are
  effectively the kernel's journal of record. **Subscribe.**
- **`man7.org`** (Michael Kerrisk) — the definitive Linux man pages, especially section 2
  and 7.
- **The Open Group Base Specifications Issue 8** (`pubs.opengroup.org`) — POSIX itself,
  free online. The shell grammar chapter is the answer to every "why does the shell do
  that" question.
- **GNU Bash Reference Manual** and **`bash-hackers`-style references**; **BashFAQ** and
  **BashPitfalls** on `mywiki.wooledge.org` — the latter is the best shell-bug catalogue
  in existence.
- **kernelnewbies.org**, the **KernelNewbies mailing list**, and the **KVM/Plumbers/LSFMM
  conference materials**.
- **ebpf.io** / **docs.ebpf.io**, and **Brendan Gregg's** site.

### 18.2 Books

| Author | Work | Why |
|---|---|---|
| **Robert Love** | *Linux Kernel Development* (3e) | Still the best readable introduction to kernel concepts, even though the code has moved on |
| **Bovet & Cesati** | *Understanding the Linux Kernel* | Deep, structural, dated (2.6) but conceptually intact |
| **Corbet, Rubini & Kroah-Hartman** | *Linux Device Drivers* (3e) | The classic driver text. **Very** dated in API, still correct in model |
| **Kerrisk** | ***The Linux Programming Interface*** | **The single best book on the Linux userspace API.** If you buy one book, this one |
| **Stevens & Rago** | *Advanced Programming in the UNIX Environment* | The other one |
| **Stevens** | *UNIX Network Programming*, *TCP/IP Illustrated* | Sockets and the wire |
| **Brendan Gregg** | ***Systems Performance***, ***BPF Performance Tools*** | The performance and observability canon. USE method, flame graphs, the whole toolkit |
| **Kaiwan Billimoria** | *Linux Kernel Programming* / *…Part 2* | The most current practical kernel-programming books |
| **Bhattacharjee & Lustig** | *Architectural and OS Support for Virtual Memory* | Memory management depth |
| **Cooper & many** | *Advanced Bash-Scripting Guide* | Comprehensive, uneven — cross-check against BashFAQ |
| **Robbins & Beebe** | *Classic Shell Scripting* | The disciplined, portable approach |
| **Newham** | *Learning the bash Shell* | The O'Reilly standard |
| **Silberschatz et al.** | *Operating System Concepts* | The academic foundation, if you want theory |
| **Arpaci-Dusseau** | ***Operating Systems: Three Easy Pieces*** | **Free online**, and the best modern OS textbook |

### 18.3 People and channels
Jonathan Corbet (LWN), Greg Kroah-Hartman (stable, CVEs — `kroah.com/log`), Linus
Torvalds (the LKML archives are a genuine education in engineering judgment, and
occasionally in what not to do), Michael Kerrisk (man-pages), Brendan Gregg
(performance), Miguel Ojeda (Rust for Linux), Tejun Heo (cgroups, sched_ext), Jens Axboe
(block, io_uring), Chet Ramey (bash, since 1990), Phoronix (news and benchmarks — treat
benchmarks with normal caution), `lore.kernel.org` for every mailing list ever.

---
