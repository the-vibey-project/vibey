import { compareVersions } from "./version.ts";

/** A new array of the versions, oldest first. */
export function sortVersions(versions: string[]): string[] {
  return [...versions].sort(compareVersions);
}

/** The newest version, or undefined when there are none. */
export function latest(versions: string[]): string | undefined {
  return sortVersions(versions).at(-1);
}
