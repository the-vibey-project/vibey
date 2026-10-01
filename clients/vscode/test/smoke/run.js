// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The smoke test: start a real VS Code with the extension, in a scratch git repository, and
// run suite.js inside it. CI downloads VS Code; set VSCODE_EXECUTABLE to use an installed one.
//
// A launch that dies before the suite starts is retried, up to VIBEY_SMOKE_LAUNCH_ATTEMPTS
// (default 3) times; a failure after the suite started never is. On a GPU-less virtual display
// VS Code 1.140's window can hang at start ("CodeWindow: detected unresponsive") and exit
// before any test runs -- two of three develop runs on 2026-10-01 (#1318). The suite writes a
// marker as its first act, so a retry can only ever repeat a launch, never a test.
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
  const started = path.join(workspace, '.git', 'vibey-smoke-started');
  const attempts = Math.max(1, Number.parseInt(process.env.VIBEY_SMOKE_LAUNCH_ATTEMPTS ?? '3', 10) || 1);
  for (let attempt = 1; ; attempt += 1) {
    try {
      await runTests({
        extensionDevelopmentPath: path.resolve(__dirname, '..', '..'),
        extensionTestsPath: path.resolve(__dirname, 'suite.js'),
        launchArgs: [
          workspace,
          '--disable-extensions',
          '--disable-workspace-trust',
          '--skip-welcome',
          '--skip-release-notes',
          '--disable-gpu',
        ],
        ...(process.env.VSCODE_EXECUTABLE ? { vscodeExecutablePath: process.env.VSCODE_EXECUTABLE } : {}),
        extensionTestsEnv: { VIBEY_SMOKE: '1', VIBEY_SMOKE_STARTED: started },
      });
      return;
    } catch (error) {
      if (fs.existsSync(started) || attempt >= attempts) throw error;
      const note = `VS Code exited before the smoke suite started (launch ${attempt} of ${attempts}); launching again`;
      console.log(process.env.GITHUB_ACTIONS ? `::warning::${note}` : note);
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
