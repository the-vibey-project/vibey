// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it } from 'vitest';
import { PathScope } from '../../src/core/path-scope';

describe('PathScope', () => {
  it('matches a named file, or a directory and everything in it', () => {
    const scope = new PathScope(['docs/guides/install.md', 'docs/reference/', 'src/app']);
    expect(scope.globs).toEqual(['docs/guides/install.md', 'docs/reference/', 'src/app']);
    expect(scope.matches('docs/guides/install.md')).toBe(true);
    expect(scope.matches('./docs/guides/install.md')).toBe(true);
    expect(scope.matches('docs/guides/install.md.bak')).toBe(false);
    expect(scope.matches('docs/reference/cli.md')).toBe(true);
    expect(scope.matches('docs/reference')).toBe(true);
    expect(scope.matches('src/app/main.py')).toBe(true);
    expect(scope.matches('src/application.py')).toBe(false);
    expect(scope.matches('pyproject.toml')).toBe(false);
  });

  it('reads * within a segment, ? as one character, and ** across segments', () => {
    const scope = new PathScope(['docs/*.md', 'src/**/test_?.py', '**/README.md', 'notes/**']);
    expect(scope.matches('docs/index.md')).toBe(true);
    expect(scope.matches('docs/guides/install.md')).toBe(false);
    expect(scope.matches('src/test_a.py')).toBe(true);
    expect(scope.matches('src/pkg/sub/test_b.py')).toBe(true);
    expect(scope.matches('src/pkg/test_ab.py')).toBe(false);
    expect(scope.matches('README.md')).toBe(true);
    expect(scope.matches('clients/vscode/README.md')).toBe(true);
    expect(scope.matches('notes/a/b.txt')).toBe(true);
    expect(scope.matches('notes')).toBe(false);
  });

  it('takes regular-expression characters in a glob literally, and Windows separators as /', () => {
    const scope = new PathScope(['docs/a+b (1).md', 'data\\*.csv']);
    expect(scope.matches('docs/a+b (1).md')).toBe(true);
    expect(scope.matches('docs/aab (1).md')).toBe(false);
    expect(scope.matches('data/x.csv')).toBe(true);
    expect(scope.matches('data\\y.csv')).toBe(true);
    expect(PathScope.pattern('a.b').test('axb')).toBe(false);
  });
});
