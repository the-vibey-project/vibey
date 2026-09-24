// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** What a child process may see of the editor's environment. */

export type SourceEnvironment = Readonly<Record<string, string | undefined>>;

export interface ForbiddenEnvironmentInterface {
  forbids(name: string): boolean;
  /** Whether a declared prefix could admit a forbidden name. */
  forbidsPrefix(prefix: string): boolean;
}

export interface EnvironmentAllowListInterface {
  readonly forbidden: ForbiddenEnvironmentInterface;
  admits(name: string): boolean;
  /** This list plus `entries` (names, or prefixes ending in `*`), checked the same way. */
  extended(entries: readonly string[], where: string): EnvironmentAllowListInterface;
}

export interface ChildEnvironmentInterface {
  /** The allow-listed part of `source`, with the overlay laid over it last. */
  build(source: SourceEnvironment): Record<string, string>;
}
