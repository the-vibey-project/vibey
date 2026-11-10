Create src/bytes.ts exporting a function formatBytes(n: number): string that formats a byte count
as human-readable text using binary (1024-based) units: B, KiB, MiB, GiB, TiB.

- n must be a finite, non-negative integer. Otherwise (negative, NaN, Infinity, or a fraction such as
  1.5) throw a RangeError.
- Below 1024 print the plain integer and "B": formatBytes(0) is "0 B", formatBytes(1023) is "1023 B".
- From 1024 up, pick the largest unit that keeps the value at least 1, divide, and round to one
  decimal place. A trailing ".0" is dropped: formatBytes(1024) is "1 KiB", formatBytes(1536) is
  "1.5 KiB", formatBytes(1500) is "1.5 KiB", formatBytes(1048576) is "1 MiB".
- If rounding makes the value reach 1024 of its unit, move up to the next unit instead, so
  formatBytes(1048575) is "1 MiB" (not "1024 KiB") and formatBytes(1048064) is "1023.5 KiB".
- TiB is the largest unit; larger values stay in TiB, so formatBytes(1024 ** 5) is "1024 TiB".
Do not import any modules. Use only erasable TypeScript (no enums, namespaces or parameter properties).
