import type { Params } from "./router.ts";

function segments(path: string): string[] {
  const trimmed = path.endsWith("/") ? path.slice(0, -1) : path;
  return trimmed === "" ? [] : trimmed.slice(1).split("/");
}

export function matchPath(pattern: string, path: string): Params | null {
  const want = segments(pattern);
  const have = segments(path);
  const params: Params = {};
  for (let i = 0; i < want.length; i += 1) {
    const part = want[i] as string;
    if (part === "*" && i === want.length - 1) {
      if (have.length <= i) {
        return null;
      }
      params["*"] = have.slice(i).join("/");
      return params;
    }
    const actual = have[i];
    if (actual === undefined) {
      return null;
    }
    if (part.startsWith(":")) {
      if (actual === "") {
        return null;
      }
      try {
        params[part.slice(1)] = decodeURIComponent(actual);
      } catch {
        return null;
      }
    } else if (part !== actual) {
      return null;
    }
  }
  return have.length === want.length ? params : null;
}
