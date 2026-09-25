// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** JSON-lines text into records: the parsing the extension's tail and journal share, with no file access. */
/** Parsing shared by the tail and the journal. */
export class JsonlParse {
  static lines(text: string): { records: unknown[]; malformed: number } {
    const records: unknown[] = [];
    let malformed = 0;
    for (const line of text.split('\n')) {
      if (!line.trim()) {
        continue;
      }
      try {
        records.push(JSON.parse(line));
      } catch {
        malformed += 1;
      }
    }
    return { records, malformed };
  }
}
