// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import * as fs from 'node:fs';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { TaskFileError, TaskFileParser, TaskFolder, YamlScalar } from '../../src/core/task-file';
import { scratch } from './helpers';

describe('YamlScalar', () => {
  it('reads a double-quoted value with ": " inside, as the docs batch writes its titles', () => {
    expect(YamlScalar.read('"docs(readme): a short, beginner-first front page that keeps every fact"')).toBe(
      'docs(readme): a short, beginner-first front page that keeps every fact',
    );
  });

  it('unescapes double-quoted escapes', () => {
    expect(YamlScalar.read('"say \\"hi\\" \\\\ back\\tthen\\n\\u00e9\\x41\\U0001F600\\/\\ \\0\\a\\b\\v\\f\\r\\e\\N\\_\\L\\P"')).toBe(
      'say "hi" \\ back\tthen\né' + 'A' + '😀/ \0\x07\b\v\f\r\x1b\u0085   ',
    );
    expect(YamlScalar.read('"tab\\\tthere"')).toBe('tab\tthere');
  });

  it('refuses a bad escape, a short hex escape, and an unterminated value', () => {
    expect(() => YamlScalar.read('"\\q"')).toThrow('unknown escape \\q');
    expect(() => YamlScalar.read('"\\uZZZZ"')).toThrow('unknown escape \\u');
    expect(() => YamlScalar.read('"\\u12"')).toThrow('unknown escape \\u');
    expect(() => YamlScalar.read('"open')).toThrow('unterminated double-quoted');
  });

  it("reads single-quoted values, where '' is a quote", () => {
    expect(YamlScalar.read("'it''s: fine'")).toBe("it's: fine");
    expect(() => YamlScalar.read("'open")).toThrow('unterminated single-quoted');
  });

  it('allows only a comment after a closing quote', () => {
    expect(YamlScalar.read('"x"   # a note')).toBe('x');
    expect(YamlScalar.read("'x' ")).toBe('x');
    expect(() => YamlScalar.read('"x" y')).toThrow('unexpected text after a quoted value: y');
  });

  it('reads plain values, where " #" starts a comment', () => {
    expect(YamlScalar.read('  65536  # the sweep window')).toBe('65536');
    expect(YamlScalar.read('a#b')).toBe('a#b');
  });
});

describe('TaskFileParser', () => {
  const parser = new TaskFileParser();

  it('takes a file with no front matter as the plan, titled by its first line', () => {
    const task = parser.parse('01-readme.md', '# Rewrite the README\n\nKeep it short.\n');
    expect(task.stem).toBe('01-readme');
    expect(task.plan).toBe('# Rewrite the README\n\nKeep it short.\n');
    expect(task.title).toBe('Rewrite the README');
    expect(task.metadata).toEqual({});
    expect(task.sha256).toMatch(/^[0-9a-f]{64}$/);
  });

  it('strips front matter from the plan and reads every key', () => {
    const task = parser.parse(
      '02-install.MD',
      [
        '---',
        'title: "docs(install): a step-by-step guide: for complete beginners"',
        '# a comment line',
        '',
        "commit_message: 'docs(install): rewrite the guide'",
        'context_window: 65536',
        'max_turns: 60',
        'effort: high',
        '---',
        '',
        'Write the guide.',
      ].join('\n'),
    );
    expect(task.stem).toBe('02-install');
    expect(task.plan).toBe('Write the guide.');
    expect(task.title).toBe('docs(install): a step-by-step guide: for complete beginners');
    expect(task.metadata).toEqual({
      title: 'docs(install): a step-by-step guide: for complete beginners',
      commitMessage: 'docs(install): rewrite the guide',
      contextWindow: 65536,
      maxTurns: 60,
      effort: 'HIGH',
    });
  });

  it('reads paths as a flow list or a block list of globs', () => {
    expect(parser.parse('a.md', '---\npaths: ["docs/guides/install.md", \'docs/a, b.md\', docs/*.md]  # the scope\n---\nx').metadata).toEqual({
      paths: ['docs/guides/install.md', 'docs/a, b.md', 'docs/*.md'],
    });
    expect(parser.parse('a.md', '---\ntitle: t\npaths:\n  - docs/guides/install.md\n  - "docs/reference/*.md"\neffort: low\n---\nx').metadata).toEqual({
      title: 't',
      paths: ['docs/guides/install.md', 'docs/reference/*.md'],
      effort: 'LOW',
    });
    expect(parser.parse('a.md', '---\npaths: [ "a\\"b.md" ]\n---\nx').metadata.paths).toEqual(['a"b.md']);
  });

  it.each([
    ['---\npaths: []\n---\nx', 'name at least one path'],
    ['---\npaths:\n---\nx', 'name at least one path'],
    ['---\npaths: docs/a.md\n---\nx', 'expected a list like'],
    ['---\npaths: ["a", ]\n---\nx', 'an empty item'],
    ['---\npaths: [, "a"]\n---\nx', 'an empty item'],
    ['---\npaths: ["a"\n---\nx', 'unterminated list'],
    ['---\npaths: ["a"] extra\n---\nx', 'unexpected text after a quoted value'],
    ['---\npaths: ["/etc/passwd"]\n---\nx', 'is not a path inside the repository'],
    ['---\npaths: ["docs/../../x"]\n---\nx', 'is not a path inside the repository'],
    ['---\npaths: ["C:/x"]\n---\nx', 'is not a path inside the repository'],
    ['---\npaths: ["  "]\n---\nx', 'is not a path inside the repository'],
    ['---\npaths: ["a"]\npaths: ["b"]\n---\nx', 'given twice'],
  ])('refuses paths %j', (text, message) => {
    expect(() => parser.parse('bad.md', text)).toThrow(message);
  });

  it('reads effort auto, and ignores an empty value', () => {
    expect(parser.parse('a.md', '---\neffort: auto\ntitle: ""\n---\nx').metadata).toEqual({ effort: 'auto' });
    expect(parser.parse('a.md', '---\neffort:\n---\nx').metadata).toEqual({});
  });

  it.each([
    ['---\ntitle: x\nplan', 'no closing --- line'],
    ['---\nflavour: sweet\n---\nx', 'unknown front matter key "flavour"'],
    ['---\ntitle: a\ntitle: b\n---\nx', 'given twice'],
    ['---\ntitle:no-space\n---\nx', 'is not "key: value"'],
    ['---\ncontext_window: 100\n---\nx', 'context_window must be a whole number of at least 1024'],
    ['---\nmax_turns: many\n---\nx', 'max_turns must be a whole number of at least 1'],
    ['---\neffort: extreme\n---\nx', 'effort must be auto or one of'],
    ['---\ntitle: "unterminated\n---\nx', 'title: unterminated double-quoted'],
    ['---\ntitle: x\n---\n   \n', 'the task is empty'],
  ])('refuses %j', (text, message) => {
    expect(() => parser.parse('bad.md', text)).toThrow(TaskFileError);
    expect(() => parser.parse('bad.md', text)).toThrow(message);
  });
});

describe('TaskFolder', () => {
  it('loads the .md files in name order, skipping hidden files and others', () => {
    const directory = scratch();
    fs.writeFileSync(path.join(directory, '02-second.md'), 'second');
    fs.writeFileSync(path.join(directory, '01-first.md'), 'first');
    fs.writeFileSync(path.join(directory, '.hidden.md'), 'hidden');
    fs.writeFileSync(path.join(directory, 'notes.txt'), 'not a task');
    fs.mkdirSync(path.join(directory, '03-dir.md'));
    const tasks = new TaskFolder().load(directory);
    expect(tasks.map((task) => task.name)).toEqual(['01-first.md', '02-second.md']);
  });
});
