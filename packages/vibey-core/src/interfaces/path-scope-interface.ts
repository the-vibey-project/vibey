// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The files a task may change, as a task file's `paths:` globs name them. */

export interface PathScopeInterface {
  /** Whether a repository-relative path (`docs/guides/install.md`) is in scope. */
  matches(file: string): boolean;
  /** The globs, as given. */
  readonly globs: readonly string[];
}
