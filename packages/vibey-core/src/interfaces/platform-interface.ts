// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * The few platform types the core names, written out so it compiles against no platform at all.
 * Node's, a browser's and React Native's own types all fit them.
 */

/** The part of an `AbortSignal` the core and its adapters use. */
export interface AbortSignalLike {
  readonly aborted: boolean;
  addEventListener(type: 'abort', listener: () => void, options?: { readonly once?: boolean }): void;
  removeEventListener(type: 'abort', listener: () => void): void;
}

/** A POSIX signal by name, as a process runner's `kill` takes it: `SIGTERM`, `SIGKILL`. */
export type SignalName = `SIG${string}`;
