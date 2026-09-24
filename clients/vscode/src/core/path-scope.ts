// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * A task's scope: the repository-relative paths it may change, as globs. `*` is any run of
 * characters within one path segment, `?` one such character, and `**` any number of whole
 * segments; a glob with none of those names a file, or a directory and everything in it. It
 * decides what a task's commit may hold (sub-doctrine 12.d: a lane's authority is the work
 * named). Node's own `path.matchesGlob` is not in the Node the editor runs, hence this.
 * Declared by `interfaces/path-scope-interface.ts`.
 */
import type { PathScopeInterface } from './interfaces/path-scope-interface';

export class PathScope implements PathScopeInterface {
  private readonly patterns: readonly RegExp[];

  constructor(readonly globs: readonly string[]) {
    this.patterns = globs.map((glob) => PathScope.pattern(glob));
  }

  matches(file: string): boolean {
    const normal = file.replace(/\\/g, '/').replace(/^\.\//, '');
    return this.patterns.some((pattern) => pattern.test(normal));
  }

  /** A glob as a regular expression over the whole path. */
  static pattern(glob: string): RegExp {
    const normal = glob.replace(/\\/g, '/').replace(/^\.\//, '');
    if (!/[*?]/.test(normal)) {
      const literal = PathScope.escape(normal.replace(/\/+$/, ''));
      return new RegExp(`^${literal}(?:/.*)?$`);
    }
    let source = '';
    for (let index = 0; index < normal.length; index += 1) {
      const character = normal.charAt(index);
      if (character === '*' && normal.charAt(index + 1) === '*') {
        const slash = normal.charAt(index + 2) === '/';
        source += slash ? '(?:.*/)?' : '.*';
        index += slash ? 2 : 1;
      } else if (character === '*') {
        source += '[^/]*';
      } else if (character === '?') {
        source += '[^/]';
      } else {
        source += PathScope.escape(character);
      }
    }
    return new RegExp(`^${source}$`);
  }

  private static escape(text: string): string {
    return text.replace(/[.+^${}()|[\]\\]/g, '\\$&');
  }
}
