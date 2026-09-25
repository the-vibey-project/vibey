// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * git, run with argv and an environment stripped of git plumbing (GIT_DIR, GIT_INDEX_FILE,
 * ...), which a hook may have exported and which would point a child at the wrong
 * repository (vibey #212). Hooks always run: a commit or merge a hook refuses is reported,
 * never forced (no `--no-verify`, sub-doctrine 12.d). Declared by
 * `interfaces/git-interface.ts`.
 */
import type {
  ChangedFile,
  CommitOutcome,
  GitClientInterface,
  MergeOutcome,
} from './interfaces/git-interface';
import type { CompletedProcess, Environment, ProcessRunnerInterface } from './interfaces/process-runner-interface';
import { LocalRunners } from './local-runner';
import { PathScope } from './path-scope';

export class GitError extends Error {
  constructor(
    readonly args: readonly string[],
    readonly result: CompletedProcess,
  ) {
    super(`git ${args.join(' ')} failed: ${(result.stderr || result.error || `exit ${result.code}`).trim()}`);
    this.name = 'GitError';
  }
}

export class GitClient implements GitClientInterface {
  /**
   * Where the local runner keeps its run records, in the worktree it runs in: never the work.
   * gptossloop and qwenloop share it (ADR-0064).
   */
  static readonly RUN_RECORDS = LocalRunners.PROTOCOL.stateDir;

  constructor(
    private readonly runner: ProcessRunnerInterface,
    private readonly executable: string,
    private readonly environment: Environment,
  ) {}

  async version(): Promise<string> {
    return (await this.must(['--version'])).trim();
  }

  async toplevel(directory: string): Promise<string> {
    return (await this.must(['-C', directory, 'rev-parse', '--show-toplevel'])).trim();
  }

  async resolveCommit(repository: string, ref: string): Promise<string> {
    return (await this.must(['-C', repository, 'rev-parse', '--verify', '--quiet', `${ref}^{commit}`])).trim();
  }

  async head(directory: string): Promise<string> {
    return (await this.must(['-C', directory, 'rev-parse', 'HEAD'])).trim();
  }

  async uncommitted(directory: string, exclude: readonly string[] = [GitClient.RUN_RECORDS]): Promise<readonly string[]> {
    const output = await this.must(['-C', directory, 'status', '--porcelain', '-z', '--untracked-files=all']);
    const paths: string[] = [];
    const fields = output.split('\0').filter((field) => field !== '');
    for (let index = 0; index < fields.length; index += 1) {
      const entry = fields[index] as string;
      const where = entry.slice(3);
      if (!exclude.some((directory) => where === directory || where.startsWith(`${directory}/`))) {
        paths.push(where);
      }
      // A rename's entry is followed by the path it had before, which is not a change of its own.
      if (/^[RC]/.test(entry)) {
        index += 1;
      }
    }
    return paths;
  }

  async currentBranch(repository: string): Promise<string | undefined> {
    const result = await this.git(['-C', repository, 'symbolic-ref', '--quiet', '--short', 'HEAD']);
    return result.code === 0 ? result.stdout.trim() : undefined;
  }

  async addWorktree(repository: string, worktree: string, branch: string, base: string): Promise<void> {
    await this.must(['-C', repository, 'worktree', 'add', '-b', branch, worktree, base]);
  }

  async removeWorktree(repository: string, worktree: string): Promise<void> {
    await this.must(['-C', repository, 'worktree', 'remove', '--force', worktree]);
  }

  async deleteBranch(repository: string, branch: string): Promise<void> {
    await this.must(['-C', repository, 'branch', '-D', branch]);
  }

  async branchExists(repository: string, branch: string): Promise<boolean> {
    const result = await this.git(['-C', repository, 'rev-parse', '--verify', '--quiet', `refs/heads/${branch}`]);
    return result.code === 0;
  }

  async commitAll(
    worktree: string,
    message: string,
    exclude: readonly string[] = [GitClient.RUN_RECORDS],
    paths?: readonly string[],
  ): Promise<CommitOutcome> {
    // Twice at most: a formatting hook that rewrites files fails the first commit and
    // leaves its fixes unstaged, which is what a person would stage and commit again.
    // Anything a hook still refuses the second time is reported, not bypassed.
    let error: string | undefined;
    let outOfScope: readonly string[] = [];
    for (let attempt = 0; attempt < 2; attempt += 1) {
      // Everything .gitignore allows. An ignored path is never named in an `add` pathspec:
      // git refuses one even inside :(exclude), and a repository that ignores `.qwenloop/`
      // would then commit nothing at all.
      await this.must(['-C', worktree, 'add', '-A']);
      // The runners' records stay out whether or not the repository ignores them. An empty
      // pathspec would reset the whole index, so an empty list resets nothing.
      if (exclude.length > 0) {
        await this.must(['-C', worktree, 'reset', '-q', '--', ...exclude]);
      }
      if (paths !== undefined) {
        outOfScope = await this.keepInScope(worktree, new PathScope(paths));
      }
      const scope = outOfScope.length === 0 ? {} : { outOfScope };
      const staged = await this.git(['-C', worktree, 'diff', '--cached', '--quiet']);
      if (staged.code === 0) {
        return { committed: false, ...(error === undefined ? {} : { error }), ...scope };
      }
      const commit = await this.git(['-C', worktree, 'commit', '-q', '-m', message]);
      if (commit.code === 0) {
        return { committed: true, ...scope };
      }
      error = `${commit.stdout}\n${commit.stderr}`.trim() || commit.error || `exit ${commit.code}`;
    }
    // Only two refused commits reach this line, so there is always an error to report.
    return { committed: false, error: error as string, ...(outOfScope.length === 0 ? {} : { outOfScope }) };
  }

  /** Unstage every staged path outside the scope; the paths it left out. */
  private async keepInScope(worktree: string, scope: PathScope): Promise<readonly string[]> {
    const staged = (await this.must(['-C', worktree, 'diff', '--cached', '--name-only', '--no-renames', '-z'])).split('\0').filter((file) => file !== '');
    const outside = staged.filter((file) => !scope.matches(file));
    if (outside.length > 0) {
      // Literal pathspecs: a file named like a glob (`notes[1].md`) is that file and no other.
      await this.must(['--literal-pathspecs', '-C', worktree, 'reset', '-q', '--', ...outside]);
    }
    return outside;
  }

  async diffStat(repository: string, from: string, to: string): Promise<string> {
    return (await this.must(['-C', repository, 'diff', '--stat', from, to])).trimEnd();
  }

  async changedFiles(repository: string, from: string, to: string): Promise<readonly ChangedFile[]> {
    const output = await this.must(['-C', repository, 'diff', '--name-status', '-z', from, to]);
    const fields = output.split('\0').filter((field) => field !== '');
    const files: ChangedFile[] = [];
    let index = 0;
    while (index < fields.length) {
      const status = fields[index] as string;
      // A rename or copy names two paths: where it was, then where it is now.
      const paths = /^[RC]/.test(status) ? 2 : 1;
      const where = fields[index + paths];
      if (where !== undefined) {
        files.push({ status: status.charAt(0), path: where });
      }
      index += paths + 1;
    }
    return files;
  }

  async diff(repository: string, from: string, to: string): Promise<string> {
    return this.must(['-C', repository, 'diff', from, to]);
  }

  async merge(repository: string, branch: string, message: string): Promise<MergeOutcome> {
    const status = await this.must(['-C', repository, 'status', '--porcelain', '--untracked-files=no']);
    if (status.trim() !== '') {
      return {
        ok: false,
        reason: 'dirty',
        detail: 'Your branch has uncommitted changes. Commit or stash them, then apply again.',
        conflicts: [],
      };
    }
    const merged = await this.git(['-C', repository, 'merge', '--no-edit', '-m', message, branch]);
    if (merged.code === 0) {
      return { ok: true, output: merged.stdout.trim() };
    }
    const conflicted = await this.git(['-C', repository, 'diff', '--name-only', '--diff-filter=U']);
    const conflicts = conflicted.stdout.split('\n').map((line) => line.trim()).filter((line) => line !== '');
    const inProgress = await this.git(['-C', repository, 'rev-parse', '--verify', '--quiet', 'MERGE_HEAD']);
    if (inProgress.code === 0) {
      await this.must(['-C', repository, 'merge', '--abort']);
    }
    return {
      ok: false,
      reason: conflicts.length > 0 ? 'conflict' : 'failed',
      detail: `${merged.stdout}\n${merged.stderr}`.trim() || merged.error || `exit ${merged.code}`,
      conflicts,
    };
  }

  private git(args: readonly string[]): Promise<CompletedProcess> {
    return this.runner.run(this.executable, args, { env: this.environment, timeoutMs: 120_000 });
  }

  private async must(args: readonly string[]): Promise<string> {
    const result = await this.git(args);
    if (result.code !== 0) {
      throw new GitError(args, result);
    }
    return result.stdout;
  }
}
