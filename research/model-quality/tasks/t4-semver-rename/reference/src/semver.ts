// Semantic version helpers. A version looks like "1.2.3", "v1.2.3", "1.2.3-rc.1" or "1.2.3+build7".

export interface Version {
  major: number;
  minor: number;
  patch: number;
  prerelease: string[];
}

const PATTERN = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/;

export function parseVersion(v: string): Version {
  const m = PATTERN.exec(v);
  if (m === null) throw new Error("invalid version: " + v);
  return {
    major: Number(m[1]),
    minor: Number(m[2]),
    patch: Number(m[3]),
    prerelease: m[4] === undefined ? [] : m[4].split("."),
  };
}

export function formatVersion(v: Version): string {
  const core = v.major + "." + v.minor + "." + v.patch;
  return v.prerelease.length === 0 ? core : core + "-" + v.prerelease.join(".");
}

function comparePrerelease(pa: string[], pb: string[]): number {
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

export function compareVersions(a: string, b: string): number {
  const va = parseVersion(a);
  const vb = parseVersion(b);
  if (va.major !== vb.major) return va.major < vb.major ? -1 : 1;
  if (va.minor !== vb.minor) return va.minor < vb.minor ? -1 : 1;
  if (va.patch !== vb.patch) return va.patch < vb.patch ? -1 : 1;
  return comparePrerelease(va.prerelease, vb.prerelease);
}

export function bumpVersion(v: string, kind: string): string {
  const next = parseVersion(v);
  if (kind === "major") {
    next.major += 1;
    next.minor = 0;
    next.patch = 0;
    next.prerelease = [];
  } else if (kind === "minor") {
    next.minor += 1;
    next.patch = 0;
    next.prerelease = [];
  } else if (kind === "patch") {
    // A prerelease becomes its release without a number change: 1.2.3-rc.1 -> 1.2.3.
    if (next.prerelease.length === 0) next.patch += 1;
    next.prerelease = [];
  } else if (kind === "prerelease") {
    if (next.prerelease.length === 0) {
      next.patch += 1;
      next.prerelease = ["rc", "0"];
    } else {
      const last = next.prerelease[next.prerelease.length - 1] as string;
      if (/^\d+$/.test(last)) next.prerelease[next.prerelease.length - 1] = String(Number(last) + 1);
      else next.prerelease.push("0");
    }
  } else {
    throw new Error("unknown bump kind: " + kind);
  }
  return formatVersion(next);
}

export function cmp(a: string, b: string): number {
  return compareVersions(a, b);
}

export function bump(v: string, kind: string): string {
  return bumpVersion(v, kind);
}
