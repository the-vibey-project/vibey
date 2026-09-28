---
id: skill-11-the-userland-80595ea51a
purpose: 11 the userland
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-shell-scripting-and-userland/SKILL.md
requires: ["skill-10-defensive-shell-scripting-de9ddb6b03"]
links: []
---

## §11. The Userland

### 11.1 Tools worth genuinely knowing

| Domain | Tools |
|---|---|
| Text | `grep`(`-r -n -F -w -o -P`), `sed`, `awk`, `cut`, `tr`, `sort`(`-u -n -k -t`), `uniq -c`, `join`, `comm`, `paste`, `column -t`, `fmt` |
| Structured | **`jq`** (JSON), `yq`, `xmlstarlet`, `csvkit`, `miller`(mlr) |
| Files | `find`(`-print0 -exec +`), `xargs -0 -P`, `rsync -aHAX --delete`, `stat`, `install`, `readlink -f` |
| Processes | `ps aux`, `pgrep/pkill`, `kill -l`, `nohup`, `setsid`, `timeout`, `nice`, `ionice`, `taskset`, `chrt` |
| Observability | `top`/`htop`/`btop`, `iostat`, `vmstat`, `mpstat`, `pidstat`, `sar`, **`ss`** (not `netstat`), **`ip`** (not `ifconfig`), `lsof`, `fuser`, `dstat` |
| Introspection | `strace`, `ltrace`, `perf`, `bpftrace`, `/proc/PID/{maps,status,fd,stack,limits}` |
| Disks | `lsblk`, `blkid`, `df -h`, `du -sh`, `ncdu`, `smartctl`, `fio`, `badblocks` |
| Build/pack | `make`, `ninja`, `meson`, `cmake`, `pkg-config`, `dpkg/rpm`, `ldd`, `objdump`, `readelf`, `nm`, `strings` |
| Modern rewrites | `rg`(ripgrep), `fd`, `bat`, `eza`, `delta`, `zoxide`, `atuin`, `starship`, `dust`, `sd` |

**[DURABLE] The pipeline idioms that never stop being useful:**
```bash
sort | uniq -c | sort -rn | head          # frequency ranking. Works on anything.
awk '{s+=$3} END {print s}'               # sum a column
awk -F: '$3 >= 1000 {print $1}' /etc/passwd
find . -type f -print0 | xargs -0 -P"$(nproc)" -n1 process   # parallel over files
comm -13 <(sort a) <(sort b)              # lines in b not in a (process substitution)
```

**⚠️ GNU vs BSD vs busybox.** `sed -i` takes an argument on macOS/BSD and not on GNU;
`date` options differ completely; `readlink -f` doesn't exist on old macOS. **Test the
target's userland, or install GNU coreutils, or stay strictly POSIX.** Note also that
Ubuntu has begun shipping **uutils** (a Rust coreutils reimplementation) — behavioural
differences from GNU coreutils are a new source of surprises.
