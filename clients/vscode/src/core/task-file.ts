// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Task files for a batch: each `*.md` in a folder is one complete qwenloop plan, run in
 * filename order (`01-…`, `02-…`). An optional front-matter block at the very top sets
 * per-task values and is removed before the plan reaches qwenloop:
 *
 *   ---
 *   title: "docs(readme): a short, beginner-first front page"
 *   commit_message: "docs(readme): rewrite the front page"
 *   context_window: 65536
 *   max_turns: 60
 *   effort: standard
 *   ---
 *
 * Values follow YAML's scalar rules for the forms front matter uses: plain (a ` #` starts
 * a comment), 'single-quoted' ('' is a quote), and "double-quoted" (backslash escapes).
 * An unknown key is refused rather than ignored, so a typo cannot silently drop a setting.
 * Declared by `interfaces/task-file-interface.ts`.
 */
import { createHash } from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import type {
  TaskFile,
  TaskFileParserInterface,
  TaskFolderInterface,
  TaskMetadata,
} from './interfaces/task-file-interface';
import { Efforts } from './catalogue';
import type { EffortSetting } from './interfaces/catalogue-interface';
import { TaskNaming } from './support';

export class TaskFileError extends Error {
  constructor(file: string, detail: string) {
    super(`${file}: ${detail}`);
    this.name = 'TaskFileError';
  }
}

/** The scalar forms front matter uses, read the way YAML reads them. */
export class YamlScalar {
  private static readonly ESCAPES: Readonly<Record<string, string>> = {
    '0': '\0',
    a: '\x07',
    b: '\b',
    t: '\t',
    '\t': '\t',
    n: '\n',
    v: '\v',
    f: '\f',
    r: '\r',
    e: '\x1b',
    ' ': ' ',
    '"': '"',
    '/': '/',
    '\\': '\\',
    N: '\u0085',
    _: '\u00a0',
    L: '\u2028',
    P: '\u2029',
  };
  private static readonly HEX_LENGTH: Readonly<Record<string, number>> = { x: 2, u: 4, U: 8 };

  static read(raw: string): string {
    const text = raw.trim();
    if (text.startsWith('"')) {
      return YamlScalar.doubleQuoted(text);
    }
    if (text.startsWith("'")) {
      return YamlScalar.singleQuoted(text);
    }
    const comment = text.search(/\s#/);
    return (comment >= 0 ? text.slice(0, comment) : text).trim();
  }

  private static doubleQuoted(text: string): string {
    let value = '';
    let index = 1;
    while (index < text.length) {
      const character = text.charAt(index);
      if (character === '"') {
        YamlScalar.onlyComment(text.slice(index + 1));
        return value;
      }
      if (character !== '\\') {
        value += character;
        index += 1;
        continue;
      }
      const escape = text.charAt(index + 1);
      const simple = YamlScalar.ESCAPES[escape];
      if (simple !== undefined) {
        value += simple;
        index += 2;
        continue;
      }
      const length = YamlScalar.HEX_LENGTH[escape];
      const digits = length === undefined ? '' : text.slice(index + 2, index + 2 + length);
      if (length === undefined || !/^[0-9A-Fa-f]+$/.test(digits) || digits.length !== length) {
        throw new Error(`unknown escape \\${escape} in ${text}`);
      }
      value += String.fromCodePoint(Number.parseInt(digits, 16));
      index += 2 + length;
    }
    throw new Error(`unterminated double-quoted value ${text}`);
  }

  private static singleQuoted(text: string): string {
    let value = '';
    let index = 1;
    while (index < text.length) {
      const character = text.charAt(index);
      if (character === "'") {
        if (text.charAt(index + 1) === "'") {
          value += "'";
          index += 2;
          continue;
        }
        YamlScalar.onlyComment(text.slice(index + 1));
        return value;
      }
      value += character;
      index += 1;
    }
    throw new Error(`unterminated single-quoted value ${text}`);
  }

  /** After a closing quote only whitespace and a comment may follow. */
  private static onlyComment(rest: string): void {
    if (rest.trim() !== '' && !/^\s+#/.test(rest)) {
      throw new Error(`unexpected text after a quoted value: ${rest.trim()}`);
    }
  }
}

export class TaskFileParser implements TaskFileParserInterface {
  private static readonly KEYS = new Set(['title', 'commit_message', 'context_window', 'max_turns', 'effort']);
  private readonly naming = new TaskNaming();

  parse(name: string, text: string): TaskFile {
    const sha256 = createHash('sha256').update(text, 'utf8').digest('hex');
    const stem = name.replace(/\.md$/i, '');
    const lines = text.split(/\r?\n/);
    let metadata: TaskMetadata = {};
    let plan = text;
    // Splitting any string yields at least one line.
    if ((lines[0] as string).trim() === '---') {
      const end = lines.findIndex((line, index) => index > 0 && line.trim() === '---');
      if (end < 0) {
        throw new TaskFileError(name, 'the front matter that starts on line 1 has no closing --- line');
      }
      metadata = this.metadata(name, lines.slice(1, end));
      plan = lines.slice(end + 1).join('\n').replace(/^\s*\n/, '');
    }
    if (!plan.trim()) {
      throw new TaskFileError(name, 'the task is empty: there is nothing for the model to do');
    }
    return {
      name,
      stem,
      sha256,
      metadata,
      plan,
      title: metadata.title ?? this.naming.title(plan),
    };
  }

  private metadata(name: string, lines: readonly string[]): TaskMetadata {
    const found: Record<string, string> = {};
    for (const [offset, line] of lines.entries()) {
      if (!line.trim() || line.trim().startsWith('#')) {
        continue;
      }
      const match = /^([A-Za-z_][A-Za-z0-9_]*)\s*:(?:\s+(.*)|\s*)$/.exec(line);
      if (match === null) {
        throw new TaskFileError(name, `front matter line ${offset + 2} is not "key: value": ${line}`);
      }
      const key = match[1] as string;
      if (!TaskFileParser.KEYS.has(key)) {
        throw new TaskFileError(
          name,
          `unknown front matter key "${key}"; the keys are ${[...TaskFileParser.KEYS].join(', ')}`,
        );
      }
      if (key in found) {
        throw new TaskFileError(name, `front matter key "${key}" is given twice`);
      }
      try {
        found[key] = YamlScalar.read(match[2] ?? '');
      } catch (error) {
        throw new TaskFileError(name, `${key}: ${(error as Error).message}`);
      }
    }
    return {
      ...TaskFileParser.text(found, 'title', 'title'),
      ...TaskFileParser.text(found, 'commit_message', 'commitMessage'),
      ...TaskFileParser.effort(name, found),
      ...TaskFileParser.count(name, found, 'context_window', 'contextWindow', 1024),
      ...TaskFileParser.count(name, found, 'max_turns', 'maxTurns', 1),
    };
  }

  private static text(found: Record<string, string>, key: string, field: string): Record<string, string> {
    const value = found[key];
    return value === undefined || value === '' ? {} : { [field]: value };
  }

  private static effort(name: string, found: Record<string, string>): { effort?: EffortSetting } {
    const value = found.effort;
    if (value === undefined || value === '') {
      return {};
    }
    const upper = value === 'auto' ? 'auto' : value.toUpperCase();
    if (upper !== 'auto' && !Efforts.is(upper)) {
      throw new TaskFileError(name, `effort must be auto or one of ${Efforts.ALL.join(', ')}, not ${JSON.stringify(value)}`);
    }
    return { effort: upper };
  }

  private static count(
    name: string,
    found: Record<string, string>,
    key: string,
    field: string,
    minimum: number,
  ): Record<string, number> {
    const value = found[key];
    if (value === undefined) {
      return {};
    }
    if (!/^\d+$/.test(value) || Number(value) < minimum) {
      throw new TaskFileError(name, `${key} must be a whole number of at least ${minimum}, not ${JSON.stringify(value)}`);
    }
    return { [field]: Number(value) };
  }
}

export class TaskFolder implements TaskFolderInterface {
  constructor(private readonly parser: TaskFileParserInterface = new TaskFileParser()) {}

  load(directory: string): readonly TaskFile[] {
    const names = fs
      .readdirSync(directory, { withFileTypes: true })
      .filter((entry) => entry.isFile() && /\.md$/i.test(entry.name) && !entry.name.startsWith('.'))
      .map((entry) => entry.name)
      .sort();
    return names.map((name) => this.parser.parse(name, fs.readFileSync(path.join(directory, name), 'utf8')));
  }
}
