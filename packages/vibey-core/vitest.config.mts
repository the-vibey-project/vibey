// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
// @vibey/core is held to 100% of lines, branches, functions and statements, the floor the
// extension's core carried before it moved here and the Python layers carry (ADR-0023). The
// generated design tokens it re-exports are counted too: their helpers are code every client runs.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['test/unit/**/*.test.ts'],
    environment: 'node',
    testTimeout: 20000,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts', '../../design/dist/ts/tokens.ts'],
      exclude: ['src/interfaces/**', 'src/index.ts'],
      allowExternal: true,
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
