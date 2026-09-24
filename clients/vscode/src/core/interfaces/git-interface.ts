// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/** The git operations a run needs: a worktree of its own, its result committed, and merged back. */

export interface ChangedFile {
  /** git's status letter: A added, M modified, D deleted, R renamed, ... */
  readonly status: string;
  readonly path: string;
}

export interface CommitOutcome {
  /** A commit was made (false when there was nothing to commit, or the commit failed). */
  readonly committed: boolean;
  /** Why the commit failed (a hook refused it, no identity, ...), in git's own words. */
  readonly error?: string;
}

export type MergeOutcome =
  | { readonly ok: true; readonly output: string }
  | { readonly ok: false; readonly reason: 'dirty' | 'conflict' | 'failed'; readonly detail: string; readonly conflicts: readonly string[] };

export interface GitClientInterface {
  version(): Promise<string>;
  /** The top of the repository `directory` is in. */
  toplevel(directory: string): Promise<string>;
  /** The commit `ref` names, as a full SHA. */
  resolveCommit(repository: string, ref: string): Promise<string>;
  /** The commit checked out in `directory`. */
  head(directory: string): Promise<string>;
  /** Paths with changes not committed, leaving out the directories in `exclude`. */
  uncommitted(directory: string, exclude?: readonly string[]): Promise<readonly string[]>;
  /** The checked-out branch, or undefined when HEAD is detached. */
  currentBranch(repository: string): Promise<string | undefined>;
  addWorktree(repository: string, worktree: string, branch: string, base: string): Promise<void>;
  removeWorktree(repository: string, worktree: string): Promise<void>;
  deleteBranch(repository: string, branch: string): Promise<void>;
  branchExists(repository: string, branch: string): Promise<boolean>;
  /**
   * Stage everything but the directories in `exclude` (engines' run records, attachments),
   * and commit it if anything changed.
   */
  commitAll(worktree: string, message: string, exclude?: readonly string[]): Promise<CommitOutcome>;
  diffStat(repository: string, from: string, to: string): Promise<string>;
  changedFiles(repository: string, from: string, to: string): Promise<readonly ChangedFile[]>;
  diff(repository: string, from: string, to: string): Promise<string>;
  /** Merge `branch` into what `repository` has checked out; on conflict, undo and report. */
  merge(repository: string, branch: string, message: string): Promise<MergeOutcome>;
}
