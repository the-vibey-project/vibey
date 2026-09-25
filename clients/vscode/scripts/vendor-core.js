// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// Copies the built @vibey/core into out/node_modules/@vibey/core, where Node finds it from
// out/extension/extension.js and out/cli.js. The .vsix is packaged with --no-dependencies, so
// this copy is how the shared core travels inside it: the extension still installs nothing at
// runtime (ADR-0059), and the core is the same build the unit suite tested (ADR-0067).
'use strict';
const fs = require('node:fs');
const path = require('node:path');

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
