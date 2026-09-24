// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Clears the durable scratch space before the suite and after it, so it never grows. */
import * as fs from 'node:fs';
import * as path from 'node:path';

const DURABLE_SCRATCH = path.join(__dirname, '..', '..', '.test-scratch');

export function setup(): () => void {
  fs.rmSync(DURABLE_SCRATCH, { recursive: true, force: true });
  return () => fs.rmSync(DURABLE_SCRATCH, { recursive: true, force: true });
}
