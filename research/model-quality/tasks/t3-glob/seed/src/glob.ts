const SPECIAL = /[.+^${}()|[\]\\]/g;

/** Turn a wildcard pattern into a regular expression. */
export function globToRegExp(pattern: string): RegExp {
  let source = "";
  for (const ch of pattern) {
    if (ch === "*") {
      source += ".*";
    } else if (ch === "?") {
      source += ".";
    } else {
      source += ch.replace(SPECIAL, "\\$&");
    }
  }
  return new RegExp(source);
}

/** True when the whole name fits the pattern. */
export function matches(pattern: string, name: string): boolean {
  return globToRegExp(pattern).test(name);
}
