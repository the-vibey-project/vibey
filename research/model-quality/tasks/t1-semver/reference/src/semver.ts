interface Parsed {
  core: number[];
  pre: string[];
}

const PATTERN = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

function parse(text: string): Parsed {
  const match = PATTERN.exec(text);
  if (match === null) {
    throw new Error(`invalid version: ${text}`);
  }
  const pre = match[4];
  return {
    core: [Number(match[1]), Number(match[2]), Number(match[3])],
    pre: pre === undefined ? [] : pre.split("."),
  };
}

function sign(n: number): -1 | 0 | 1 {
  return n < 0 ? -1 : n > 0 ? 1 : 0;
}

function compareIdentifier(a: string, b: string): -1 | 0 | 1 {
  const aNum = /^[0-9]+$/.test(a);
  const bNum = /^[0-9]+$/.test(b);
  if (aNum && bNum) {
    return sign(Number(a) - Number(b));
  }
  if (aNum) {
    return -1;
  }
  if (bNum) {
    return 1;
  }
  return a < b ? -1 : a > b ? 1 : 0;
}

export function compareVersions(a: string, b: string): -1 | 0 | 1 {
  const left = parse(a);
  const right = parse(b);
  for (let i = 0; i < 3; i++) {
    const diff = sign((left.core[i] ?? 0) - (right.core[i] ?? 0));
    if (diff !== 0) {
      return diff;
    }
  }
  if (left.pre.length === 0 && right.pre.length === 0) {
    return 0;
  }
  if (left.pre.length === 0) {
    return 1;
  }
  if (right.pre.length === 0) {
    return -1;
  }
  const shared = Math.min(left.pre.length, right.pre.length);
  for (let i = 0; i < shared; i++) {
    const diff = compareIdentifier(left.pre[i] ?? "", right.pre[i] ?? "");
    if (diff !== 0) {
      return diff;
    }
  }
  return sign(left.pre.length - right.pre.length);
}
