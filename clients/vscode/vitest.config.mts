// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// The unit suite covers src/core, the part of the extension that never imports `vscode`,
// and holds it to 100% of lines, branches, functions and statements: the same floor the
// Python layers carry (ADR-0023). The editor layer is exercised by the smoke test instead.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['test/unit/**/*.test.ts'],
    globalSetup: ['test/unit/global-setup.ts'],
    environment: 'node',
    testTimeout: 20000,
    coverage: {
      provider: 'v8',
      include: ['src/core/**/*.ts'],
      exclude: ['src/core/interfaces/**'],
      reporter: ['text', 'text-summary'],
      thresholds: {
        lines: 100,
        branches: 100,
        functions: 100,
        statements: 100,
      },
    },
  },
});
