// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Copies the built @vibey/core into out/node_modules, so the packaged extension carries it
// (ADR-0067). Compiled by `tsc -p tsconfig.tools.json`; run by `npm run compile` after the
// core is built.
import * as fs from 'node:fs';
import * as path from 'node:path';

const source = path.join(__dirname, '..', '..', '..', 'packages', 'vibey-core');
const target = path.join(__dirname, '..', 'out', 'node_modules', '@vibey', 'core');
if (!fs.existsSync(path.join(source, 'dist'))) {
  process.stderr.write('packages/vibey-core/dist is missing: build @vibey/core first (npm run core)\n');
  process.exit(1);
}
fs.rmSync(target, { recursive: true, force: true });
fs.mkdirSync(target, { recursive: true });
fs.copyFileSync(path.join(source, 'package.json'), path.join(target, 'package.json'));
fs.cpSync(path.join(source, 'dist'), path.join(target, 'dist'), { recursive: true });
