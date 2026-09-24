// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** A task file: a markdown plan, with an optional front-matter block the plan never sees. */

export interface TaskMetadata {
  readonly title?: string;
  readonly commitMessage?: string;
  readonly contextWindow?: number;
  readonly maxTurns?: number;
  readonly effort?: string;
}

export interface TaskFile {
  /** The file's name, which orders the batch: `01-quickstart.md`. */
  readonly name: string;
  /** The name without `.md`, used for the branch and as the fallback commit subject. */
  readonly stem: string;
  /** sha256 of the file's bytes: with the name, the task's identity in the journal. */
  readonly sha256: string;
  readonly metadata: TaskMetadata;
  /** What qwenloop is given: the file without its front matter. */
  readonly plan: string;
  /** The front matter's title, else the plan's first line. */
  readonly title: string;
}

export interface TaskFileParserInterface {
  parse(name: string, text: string): TaskFile;
}

export interface TaskFolderInterface {
  /** Every `*.md` file directly in `directory`, in filename order. */
  load(directory: string): readonly TaskFile[];
}
