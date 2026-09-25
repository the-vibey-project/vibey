// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** A check of every piece the extension needs, in words a beginner can act on. */

export type CheckStatus = 'pass' | 'warn' | 'fail' | 'info';

export interface DoctorCheck {
  readonly name: string;
  readonly status: CheckStatus;
  readonly detail: string;
  /** What to do about it, one step per line. */
  readonly fix?: readonly string[];
}

export interface DoctorInterface {
  run(): Promise<readonly DoctorCheck[]>;
}
