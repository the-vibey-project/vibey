const UNITS = ["B", "KiB", "MiB", "GiB", "TiB"];

export function formatBytes(n: number): string {
  if (!Number.isInteger(n) || n < 0) {
    throw new RangeError(`invalid byte count: ${n}`);
  }
  if (n < 1024) {
    return `${n} B`;
  }
  let unit = 0;
  let value = n;
  while (value >= 1024 && unit < UNITS.length - 1) {
    value /= 1024;
    unit += 1;
  }
  let rounded = Math.round(value * 10) / 10;
  if (rounded >= 1024 && unit < UNITS.length - 1) {
    rounded = Math.round((rounded / 1024) * 10) / 10;
    unit += 1;
  }
  return `${rounded} ${UNITS[unit]}`;
}
