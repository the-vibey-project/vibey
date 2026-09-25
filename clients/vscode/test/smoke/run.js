// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The smoke test: start a real VS Code with the extension, in a scratch git repository, and
// run suite.js inside it. CI downloads VS Code; set VSCODE_EXECUTABLE to use an installed one.
'use strict';
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { runTests } = require('@vscode/test-electron');

async function main() {
  // Started from a VS Code terminal, this process inherits the flag that makes Electron run
  // as plain Node; the VS Code under test must start as itself.
  delete process.env.ELECTRON_RUN_AS_NODE;
  const workspace = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'vibey-smoke-')));
  const git = (...args) => execFileSync('git', ['-C', workspace, ...args], { stdio: 'ignore' });
  git('init', '-q', '-b', 'main');
  fs.writeFileSync(path.join(workspace, 'README.md'), '# Smoke\n');
  git('add', 'README.md');
  git('-c', 'user.name=Vibey Smoke', '-c', 'user.email=smoke@example.invalid', 'commit', '-q', '-m', 'chore: start');
  await runTests({
    extensionDevelopmentPath: path.resolve(__dirname, '..', '..'),
    extensionTestsPath: path.resolve(__dirname, 'suite.js'),
    launchArgs: [workspace, '--disable-extensions', '--disable-workspace-trust', '--skip-welcome', '--skip-release-notes'],
    ...(process.env.VSCODE_EXECUTABLE ? { vscodeExecutablePath: process.env.VSCODE_EXECUTABLE } : {}),
    extensionTestsEnv: { VIBEY_SMOKE: '1' },
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
