/** Compare two dotted version strings: negative, 0 or positive. */
export function compareVersions(a: string, b: string): number {
  const left = a.split(".");
  const right = b.split(".");
  const length = Math.max(left.length, right.length);
  for (let i = 0; i < length; i++) {
    const x = left[i] ?? "0";
    const y = right[i] ?? "0";
    if (x !== y) {
      return x < y ? -1 : 1;
    }
  }
  return 0;
}
