// Semantic version helpers. A version looks like "1.2.3", "v1.2.3", "1.2.3-rc.1" or "1.2.3+build7".

const PATTERN = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/;

export function cmp(a: string, b: string): number {
  const ma = PATTERN.exec(a);
  const mb = PATTERN.exec(b);
  if (ma === null) throw new Error("invalid version: " + a);
  if (mb === null) throw new Error("invalid version: " + b);
  for (let k = 1; k <= 3; k++) {
    const x = Number(ma[k]);
    const y = Number(mb[k]);
    if (x !== y) return x < y ? -1 : 1;
  }
  const pa = ma[4] === undefined ? [] : ma[4].split(".");
  const pb = mb[4] === undefined ? [] : mb[4].split(".");
  if (pa.length === 0 && pb.length === 0) return 0;
  if (pa.length === 0) return 1;
  if (pb.length === 0) return -1;
  const n = Math.min(pa.length, pb.length);
  for (let k = 0; k < n; k++) {
    const x = pa[k] as string;
    const y = pb[k] as string;
    if (x === y) continue;
    const xn = /^\d+$/.test(x);
    const yn = /^\d+$/.test(y);
    if (xn && yn) return Number(x) < Number(y) ? -1 : 1;
    if (xn) return -1;
    if (yn) return 1;
    return x < y ? -1 : 1;
  }
  if (pa.length === pb.length) return 0;
  return pa.length < pb.length ? -1 : 1;
}

export function bump(v: string, kind: string): string {
  const m = PATTERN.exec(v);
  if (m === null) throw new Error("invalid version: " + v);
  let major = Number(m[1]);
  let minor = Number(m[2]);
  let patch = Number(m[3]);
  let pre = m[4] === undefined ? [] : m[4].split(".");
  if (kind === "major") {
    major += 1;
    minor = 0;
    patch = 0;
    pre = [];
  } else if (kind === "minor") {
    minor += 1;
    patch = 0;
    pre = [];
  } else if (kind === "patch") {
    // A prerelease becomes its release without a number change: 1.2.3-rc.1 -> 1.2.3.
    if (pre.length === 0) patch += 1;
    pre = [];
  } else if (kind === "prerelease") {
    if (pre.length === 0) {
      patch += 1;
      pre = ["rc", "0"];
    } else {
      const last = pre[pre.length - 1] as string;
      if (/^\d+$/.test(last)) pre[pre.length - 1] = String(Number(last) + 1);
      else pre.push("0");
    }
  } else {
    throw new Error("unknown bump kind: " + kind);
  }
  const core = major + "." + minor + "." + patch;
  return pre.length === 0 ? core : core + "-" + pre.join(".");
}
