// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** Events, time, identifiers, HTML-safe text and task names. Declared by `interfaces/support-interface.ts`. */
import { randomUUID } from 'node:crypto';
import * as path from 'node:path';
import type {
  ClockInterface,
  Disposable,
  EmitterInterface,
  HtmlTextInterface,
  IdSourceInterface,
  TaskNamingInterface,
} from './interfaces/support-interface';

export class Emitter<T> implements EmitterInterface<T> {
  private readonly listeners = new Set<(value: T) => void>();

  on(listener: (value: T) => void): Disposable {
    this.listeners.add(listener);
    return { dispose: () => this.listeners.delete(listener) };
  }

  fire(value: T): void {
    for (const listener of [...this.listeners]) {
      listener(value);
    }
  }
}

export class SystemClock implements ClockInterface {
  now(): Date {
    return new Date();
  }

  monotonic(): number {
    return performance.now();
  }

  every(milliseconds: number, callback: () => void): Disposable {
    const timer = setInterval(callback, milliseconds);
    return { dispose: () => clearInterval(timer) };
  }

  sleep(milliseconds: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
  }
}

export class RandomIds implements IdSourceInterface {
  uuid(): string {
    return randomUUID();
  }
}

/**
 * Text made safe to place in HTML. Model output is untrusted: a model can write
 * `<script>`, and an event log can carry anything a tool printed. The webview renders
 * that text with `textContent` only; this is for the few strings the extension puts into
 * the page's HTML itself (titles), so neither path can turn text into markup.
 */
export class HtmlText implements HtmlTextInterface {
  private static readonly ENTITIES: Readonly<Record<string, string>> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '`': '&#96;',
    '/': '&#47;',
    '=': '&#61;',
  };

  escape(text: string): string {
    return text.replace(/[&<>"'`/=]/g, (character) => HtmlText.ENTITIES[character] as string);
  }
}

/** Names for a task's branch and worktree, from what the person typed. */
export class TaskNaming implements TaskNamingInterface {
  static readonly BRANCH_PREFIX = 'vibey/';
  static readonly WORKTREE_PREFIX = 'vscode';

  constructor(private readonly maxSlug = 40) {}

  /**
   * Lower-case ASCII words joined by `-`: `Add a README line!` becomes `add-a-readme-line`.
   * Text with no letters or digits at all becomes `fallback`.
   */
  slug(text: string, fallback = 'task'): string {
    const words = text
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
    let slug = '';
    for (const word of words.split('-')) {
      const next = slug ? `${slug}-${word}` : word;
      if (next.length > this.maxSlug) {
        break;
      }
      slug = next;
    }
    return slug || words.slice(0, this.maxSlug).replace(/-+$/, '') || fallback;
  }

  shortId(runId: string): string {
    return runId.replace(/[^0-9a-fA-F]/g, '').slice(0, 8).toLowerCase();
  }

  branch(slug: string, shortId: string): string {
    return `${TaskNaming.BRANCH_PREFIX}${slug}-${shortId}`;
  }

  /** One path component the storm's own WORKTREE_NAME pattern accepts: `^[A-Za-z0-9][A-Za-z0-9._-]*$`. */
  worktreeName(repository: string, slug: string, shortId: string): string {
    const repo = this.slug(path.basename(repository), 'repo');
    return `${TaskNaming.WORKTREE_PREFIX}-${repo}-${slug}-${shortId}`;
  }

  /** The first non-empty line, as a heading would show it, cut to 80 characters. */
  title(task: string): string {
    const first = task
      .split('\n')
      .map((line) => line.replace(/^#+\s*/, '').trim())
      .find((line) => line !== '');
    if (first === undefined) {
      return 'Untitled task';
    }
    return first.length > 80 ? `${first.slice(0, 79)}…` : first;
  }
}
