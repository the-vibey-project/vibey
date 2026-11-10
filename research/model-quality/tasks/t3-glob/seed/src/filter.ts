import { matches } from "./glob.ts";

/** The names that fit the pattern, in their original order. */
export function filterNames(pattern: string, names: string[]): string[] {
  return names.filter((name) => matches(pattern, name));
}
