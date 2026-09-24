// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import { describe, expect, it, vi } from 'vitest';
import { Emitter, HtmlText, RandomIds, SystemClock, TaskNaming } from '../../src/core/support';

describe('Emitter', () => {
  it('delivers to every listener until one is disposed', () => {
    const emitter = new Emitter<number>();
    const seen: number[] = [];
    const first = emitter.on((value) => seen.push(value));
    emitter.on((value) => seen.push(value * 10));
    emitter.fire(1);
    first.dispose();
    emitter.fire(2);
    expect(seen).toEqual([1, 10, 20]);
  });
});

describe('SystemClock', () => {
  it('tells the time, ticks, and sleeps', async () => {
    const clock = new SystemClock();
    expect(clock.now()).toBeInstanceOf(Date);
    const before = clock.monotonic();
    await clock.sleep(5);
    expect(clock.monotonic()).toBeGreaterThan(before);
    const callback = vi.fn();
    const timer = clock.every(1, callback);
    await clock.sleep(20);
    timer.dispose();
    expect(callback).toHaveBeenCalled();
  });
});

describe('RandomIds', () => {
  it('makes distinct UUIDs', () => {
    const ids = new RandomIds();
    expect(ids.uuid()).toMatch(/^[0-9a-f-]{36}$/);
    expect(ids.uuid()).not.toEqual(ids.uuid());
  });
});

describe('HtmlText', () => {
  it('turns every markup character into an entity, so model text can never become HTML', () => {
    const html = new HtmlText();
    const attack = `<script>alert("x")</script><img src=x onerror='alert(1)'>\`&/=`;
    const escaped = html.escape(attack);
    expect(escaped).not.toMatch(/[<>"'`]/);
    expect(escaped).toBe(
      '&lt;script&gt;alert(&quot;x&quot;)&lt;&#47;script&gt;&lt;img src&#61;x onerror&#61;&#39;alert(1)&#39;&gt;&#96;&amp;&#47;&#61;',
    );
    expect(html.escape('plain words')).toBe('plain words');
  });
});

describe('TaskNaming', () => {
  const naming = new TaskNaming();

  it('slugs a task into lower-case ASCII words', () => {
    expect(naming.slug('Add a README line!')).toBe('add-a-readme-line');
    expect(naming.slug('Café crème: déjà vu')).toBe('cafe-creme-deja-vu');
    expect(naming.slug('!!!')).toBe('task');
  });

  it('cuts a long slug at a word, and a single long word at the limit', () => {
    const slug = naming.slug('one two three four five six seven eight nine ten eleven twelve');
    expect(slug.length).toBeLessThanOrEqual(40);
    expect(slug.endsWith('-')).toBe(false);
    expect(naming.slug('x'.repeat(60))).toBe('x'.repeat(40));
    expect(new TaskNaming(5).slug('abcdefgh-ij')).toBe('abcde');
  });

  it('names the short id, branch and worktree', () => {
    expect(naming.shortId('1A2B3C4D-5e6f-7a8b-9c0d-0123456789ab')).toBe('1a2b3c4d');
    expect(naming.branch('add-readme', '1a2b3c4d')).toBe('vibey/add-readme-1a2b3c4d');
    expect(naming.worktreeName('/Users/me/git/Vibey', 'add-readme', '1a2b3c4d')).toBe('vscode-vibey-add-readme-1a2b3c4d');
    expect(naming.worktreeName('/', 'x', '1')).toBe('vscode-task-x-1');
    expect(naming.worktreeName('/', 'x', '1')).toMatch(/^[A-Za-z0-9][A-Za-z0-9._-]*$/);
  });

  it('titles a task by its first non-empty line, without a heading mark', () => {
    expect(naming.title('\n\n# Rewrite the README\nmore')).toBe('Rewrite the README');
    expect(naming.title('   \n')).toBe('Untitled task');
    expect(naming.title('y'.repeat(100))).toBe(`${'y'.repeat(79)}…`);
  });
});
