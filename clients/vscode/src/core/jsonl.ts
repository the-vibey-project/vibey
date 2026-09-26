// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * JSON-lines files read by position and written durably.
 *
 * A reader of a growing record reads everything written since its last read, and the
 * watermark is a byte offset, never a timestamp (sub-doctrine 10.g): lines that share an
 * instant, or arrive late, cannot fall through a byte count. The offset moves only past a
 * complete line, so a line an engine is still writing (a torn last line) is read next time,
 * whole. Writers append one line and fsync it before anything else happens, so a crash
 * loses at most the line being written and never reorders what was recorded. Declared by
 * `interfaces/jsonl-interface.ts`.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import type {
  JournalContents,
  JsonlJournalInterface,
  JsonlTailInterface,
  TailChunk,
} from '@vibey/core';
import { JsonlParse } from '@vibey/core';

export { JsonlParse };

const NEWLINE = 0x0a;

export class JsonlTail implements JsonlTailInterface {
  constructor(private readonly chunkBytes = 1 << 20) {}

  read(file: string, offset: number): TailChunk {
    let descriptor: number;
    try {
      descriptor = fs.openSync(file, 'r');
    } catch {
      return { records: [], malformed: 0, nextOffset: 0, missing: true, restarted: false };
    }
    try {
      const size = fs.fstatSync(descriptor).size;
      const restarted = size < offset;
      const start = restarted ? 0 : offset;
      const buffer = Buffer.alloc(Math.max(0, size - start));
      // Read to the size fstat saw, a chunk at a time; a read of 0 means the file ended
      // sooner (it was truncated meanwhile), and what was read is still used.
      let filled = 0;
      let read = -1;
      while (filled < buffer.length && read !== 0) {
        read = fs.readSync(
          descriptor,
          buffer,
          filled,
          Math.min(this.chunkBytes, buffer.length - filled),
          start + filled,
        );
        filled += read;
      }
      const lastNewline = buffer.subarray(0, filled).lastIndexOf(NEWLINE);
      if (lastNewline < 0) {
        return { records: [], malformed: 0, nextOffset: start, missing: false, restarted };
      }
      // Split on the newline byte before decoding: 0x0a never occurs inside a multi-byte
      // UTF-8 sequence, so every complete line decodes whole.
      const parsed = JsonlParse.lines(buffer.subarray(0, lastNewline).toString('utf8'));
      return { ...parsed, nextOffset: start + lastNewline + 1, missing: false, restarted };
    } finally {
      fs.closeSync(descriptor);
    }
  }
}

export class JsonlJournal implements JsonlJournalInterface {
  constructor(readonly file: string) {}

  append(record: Readonly<Record<string, unknown>>): void {
    const created = !fs.existsSync(this.file);
    if (created) {
      fs.mkdirSync(path.dirname(this.file), { recursive: true });
    }
    const descriptor = fs.openSync(this.file, 'a+');
    try {
      const size = fs.fstatSync(descriptor).size;
      let prefix = '';
      if (size > 0) {
        const last = Buffer.alloc(1);
        fs.readSync(descriptor, last, 0, 1, size - 1);
        // A crash mid-write leaves a torn line. It is ended, never cut: the fragment stays
        // as a malformed line readers skip and count, and this record starts on its own.
        prefix = last[0] === NEWLINE ? '' : '\n';
      }
      fs.writeSync(descriptor, `${prefix}${JSON.stringify(record)}\n`);
      fs.fsyncSync(descriptor);
    } finally {
      fs.closeSync(descriptor);
    }
    if (created) {
      JsonlJournal.syncDirectory(path.dirname(this.file));
    }
  }

  readAll(): JournalContents {
    let text: string;
    try {
      text = fs.readFileSync(this.file, 'utf8');
    } catch {
      return { records: [], malformed: 0 };
    }
    const parsed = JsonlParse.lines(text);
    const records = parsed.records.filter(
      (record): record is Record<string, unknown> =>
        typeof record === 'object' && record !== null && !Array.isArray(record),
    );
    return { records, malformed: parsed.malformed + parsed.records.length - records.length };
  }

  /** A new file's directory entry is durable only once the directory itself is synced. */
  private static syncDirectory(directory: string): void {
    const descriptor = fs.openSync(directory, 'r');
    try {
      fs.fsyncSync(descriptor);
    } finally {
      fs.closeSync(descriptor);
    }
  }
}
