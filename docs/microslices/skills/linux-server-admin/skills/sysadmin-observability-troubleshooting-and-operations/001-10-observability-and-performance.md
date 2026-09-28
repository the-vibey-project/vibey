---
id: skill-10-observability-and-performance-603b4f80c2
purpose: 10 observability and performance
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-observability-troubleshooting-and-operations/SKILL.md
requires: []
links: ["skill-11-troubleshooting-methodology-97d77938b6"]
---

## §10. Observability and Performance

### 10.1 The method, not the tools
**⚠️ Brendan Gregg's USE method**, applied to every resource (CPU, memory, disk, network):
```
Utilization   — how busy
Saturation    — ⚠️ queued work; usually the number that actually matters
Errors        — ⚠️ check these FIRST; they're cheap and often decisive
```
**And the 60-second triage:**
```
uptime              load trend
dmesg -T | tail     ⚠️ OOM kills, hardware errors, resets
vmstat 1            r, b, si/so (⚠️ swap!), us/sy/id/wa
mpstat -P ALL 1     ⚠️ per-CPU — one hot core is a different problem
pidstat 1           per-process CPU
iostat -xz 1        await, aqu-sz, %util
free -m             ⚠️ read "available", not "free"
sar -n DEV 1        network throughput
sar -n TCP,ETCP 1   retransmits, errors
top / htop
```

### 10.2 Memory, read correctly
> **⚠️ GOTCHA — "free" memory is not the number you want.** Linux uses free RAM for page
> cache deliberately. **A healthy busy server shows very little free memory and that is
> correct.** **Read `available`** — it accounts for reclaimable cache.
> ⚠️ **Panicking about low "free" and adding RAM is the most common false diagnosis in
> Linux administration.**

**Real pressure signals**: **swap in/out activity** (`si`/`so` in vmstat — ⚠️ **not swap
*used*, which can be stale and harmless**), **OOM kills in dmesg**, and
**PSI** — `cat /proc/pressure/{cpu,memory,io}` — ⚠️ **which is the modern, direct measure
of contention and is far better than inferring from utilization.**

### 10.3 CPU and profiling
`perf top`, `perf record -F 99 -g -p PID -- sleep 30` then `perf report`.
**Flame graphs** for stack aggregation. ⚠️ **`%steal` in a VM means the hypervisor is
taking your CPU — no amount of guest tuning fixes it.**

### 10.4 eBPF — the modern layer
**⚠️ Why it displaced the older tools**: `strace` uses ptrace and **stops the process on
every syscall** — profiling a high-throughput service with it is an incident waiting to
happen. **eBPF runs verified, sandboxed programs inside the kernel with near-zero
overhead, no module loading, no reboots.** SystemTap needed debug symbols and compiled
kernel modules; **eBPF with CO-RE (Compile Once, Run Everywhere) is portable.**

```
# BCC tools (apt install bpfcc-tools / dnf install bcc-tools) — 80+ ready scripts
execsnoop      ⚠️ every process exec — brilliant for "what keeps spawning?"
opensnoop      file opens — "which config is it ACTUALLY reading?"
biosnoop       block I/O with latency per operation
biolatency     I/O latency histogram
tcplife        TCP sessions with duration and bytes
tcpconnect / tcpaccept / tcpretrans
runqlat        ⚠️ scheduler run-queue latency — CPU saturation without high utilization
cachestat      page cache hit ratio
memleak        outstanding allocations
profile        CPU stack sampling
```
```
# bpftrace — awk for the kernel
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'
bpftrace -e 'tracepoint:syscalls:sys_enter_read /comm=="nginx"/ { @ = hist(args->count); }'
bpftrace -l 'tracepoint:syscalls:*'     ⚠️ list available probes
```
**⚠️ Two cautions**: overhead is low but **not zero — tracing every scheduler context
switch on a busy box will hurt**; filter or sample. And **kprobes attach to kernel
internals that can change between versions** — ⚠️ **prefer tracepoints (stable API) over
kprobes where one exists.**

**Adjacent**: **Cilium/Hubble** (Kubernetes networking and observability), **Falco**
(runtime security), **Pixie**, **Inspektor Gadget**.

### 10.5 Metrics and logs
**Prometheus + node_exporter + Grafana** is the default stack; **Loki** or the
**ELK/OpenSearch** stack for logs; **OpenTelemetry** for traces.
**⚠️ Alert on symptoms users feel** (latency, error rate, saturation), **not on causes**
(CPU 80%). **Every alert should have a runbook, and an alert nobody acts on should be
deleted.**

---
